import discord
from discord.ext import commands
import yt_dlp
import os
import asyncio
import concurrent.futures
import string
import random
import atexit

TOKEN = os.environ["DISCORD_TOKEN"]

disconnect = 0
intents = discord.Intents.all()
intents.voice_states = True

queue_inPreparation = False

bot = commands.Bot(command_prefix='!', intents=intents)
song_queue = asyncio.Queue()

@bot.event
async def on_ready():
    await bot.tree.sync()
    await bot.change_presence(status=discord.Status.idle, activity=discord.Game('that old record on the shelf'))

@bot.event
async def on_voice_state_update(member, before, after):
    voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)
    
    if voice_client and voice_client.channel:
        if len(voice_client.channel.members) == 1 and voice_client.channel.members[0].id == bot.user.id:
            global song_queue
            song_queue = asyncio.Queue()
            voice_client.stop()

            for filename in os.listdir('downloads'):
                file_path = os.path.join('downloads', filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"Removing {file_path} as part of voice_state_update.")
                except OSError as e:
                    print(f"Failed to delete {file_path}: {e}")

            await voice_client.disconnect()

def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

ydl_opts = {
    'noplaylist': True,
    'playlist_items': 1,
    'format': 'bestaudio/best[ext=webm]/best',
    'outtmpl': f'downloads/%(id)s_{generate_random_string(5)}.%(ext)s',
    'extractor_args': {
        'youtube': {
            'player_client': ['tv']
        }
    },
    'youtube_include_hls_manifest': True,
    'check_formats': 'selected',
}

def download_and_convert(url):
    global queue_inPreparation
    queue_inPreparation = True
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except Exception as e:
            queue_inPreparation = False
            print(f"Error: {e}")
            return
        audio_file = ydl.prepare_filename(info)

        info_text = f"Title: {info.get('title', 'Unknown')}\n" \
                    f"Creator: {info.get('uploader', 'Unknown')}\n" \
                    f"Duration: {info.get('duration', 0):.0f} seconds\n" \
                    f"Views: {info.get('view_count', 'Unknown')}\n" \
                    f"Upload Date: {info.get('upload_date', 'Unknown')}\n" \
                    f"Original URL: {url}\n" \
                    f"Thumbnail: {info.get('thumbnail', 'Unknown')}\n"

        info_file = f'{audio_file}.txt'
        with open(info_file, 'w') as f:
            f.write(info_text)

    return audio_file, info_file

@bot.tree.command(
    name="play",
    description="Adds an item to the queue.")
async def play(interaction: discord.Interaction, url: str):
    global disconnect
    global queue_inPreparation
    disconnect = 0

    if not interaction.user.voice:
        await interaction.response.send_message(embed=discord.Embed(description="You are not connected to any voice channel.", color=discord.Color.red()))
        return

    voice_channel = interaction.user.voice.channel

    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if voice_client is None:
        voice_client = await voice_channel.connect()
    else:
        voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    await bot.change_presence(status=discord.Status.online, activity=discord.Game('a song in #'+voice_channel.name))

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
    if voice_client.is_playing() or not song_queue.empty():
        try:
            await interaction.response.send_message(embed=discord.Embed(description="Adding music to queue.", color=discord.Color.blue()))
            audio_file_info = await asyncio.get_event_loop().run_in_executor(
                executor, download_and_convert, url
            )
            await song_queue.put(audio_file_info)
            queue_inPreparation = False
        except any as e:
            await interaction.response.send_message(embed=discord.Embed(description="Error adding music to queue. Please try again.", color=discord.Color.red()))
            print(f'Error: {e}')
            return
    elif voice_client.is_connected():
        queue_inPreparation = True
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                queue_inPreparation = False
                print(f"Error: {e}")
                return
            embed = discord.Embed(
                title="Up Next:",
                description=f"**Title:** {info.get('title', 'Unknown')}\n"
                            f"**Creator:** {info.get('uploader', 'Unknown')}\n"
                            f"**Duration:** {info.get('duration', 0):.0f} seconds\n"
                            f"**Views:** {info.get('view_count', 'Unknown')}\n"
                            f"**Upload Date:** {info.get('upload_date', 'Unknown')}\n\n"
                            f"**URL:** [__**Orignal Link ➜**__](<{url}>)\n",
                color=discord.Color.blue()
            )
            if info.get('thumbnail'):
                embed.set_image(url=info['thumbnail'])
            await interaction.response.send_message(embed=embed)
            await bot.change_presence(status=discord.Status.online, activity=discord.Game(f'{info.get("title", "Unknown")} in {voice_channel.name}'))

            try:
                audio_file_info = await asyncio.get_event_loop().run_in_executor(
                    executor, download_and_convert, url
                )

                await song_queue.put(audio_file_info) 
                queue_inPreparation = False

                if not voice_client.is_playing() and voice_client.is_connected():
                    await play_next(interaction)
            except Exception as e:
                print(f'Error: {e}')


@bot.tree.command(
    name="skip",
    description="Skips the current item in queue.")
async def skip(interaction: discord.Interaction):
    global queue_inPreparation
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    
    if voice_client:

        if queue_inPreparation:
            await interaction.response.send_message(embed=discord.Embed(description="Currently modifying queue. Please wait and try again.", color=discord.Color.red()))
            return
        
        if song_queue.empty():
            await interaction.response.send_message(embed=discord.Embed(description="Skipping current item.", color=discord.Color.orange()))
        else:
            await interaction.response.send_message(embed=discord.Embed(description="Preparing next item in queue.", color=discord.Color.blue()))
        voice_client.stop()
    else:
        await interaction.response.send_message(embed=discord.Embed(description="This bot is not connected to a voice channel.", color=discord.Color.red()))

@bot.tree.command(
    name="stop",
    description="Stops all currently playing music and disconnects.")
async def disconnect(interaction: discord.Interaction):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    
    if interaction.user.voice and voice_client:
        global song_queue
        song_queue = asyncio.Queue()
        voice_client.stop()
        await voice_client.disconnect()
        await song_queue.join()

        for filename in os.listdir('downloads'):
            file_path = os.path.join('downloads', filename)
            try:
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                        print(f"Removing {file_path} as part of disconnect.")
                    except OSError as e:
                        if e.errno == 2:
                            print(f"{file_path}: {e} has already been deleted.")
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")

        await interaction.response.send_message(embed=discord.Embed(description="Playback has been stopped and the queue has been cleared.", color=discord.Color.orange()))
        await bot.change_presence(status=discord.Status.idle, activity=discord.Game('that old record on the shelf'))
    else:
        await interaction.response.send_message(embed=discord.Embed(description="You must be connected to a voice channel first.", color=discord.Color.red()))
    global disconnect
    disconnect = 1

async def play_next(interaction: discord.Interaction):
    if disconnect == 1:
        return
    
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    
    if not voice_client: 
        return 

    if song_queue.empty():
        await bot.change_presence(status=discord.Status.idle, activity=discord.Game('that old record on the shelf'))
        return

    audio_file_info = await song_queue.get()
    audio_file = audio_file_info[0]
    info_file = audio_file_info[1]

    with open(info_file, 'r') as f:
        info_lines = f.readlines()
    next_song_title = info_lines[0].strip().split(':', 1)[1]
    next_song_creator = info_lines[1].strip().split(':', 1)[1]
    next_song_dureation = info_lines[2].strip().split(':', 1)[1]
    next_song_views = info_lines[3].strip().split(':', 1)[1]
    next_song_date = info_lines[4].strip().split(':', 1)[1]
    next_song_url = info_lines[5].strip().split(':', 1)[1]
    next_song_thumbnail = info_lines[6].strip().split(':', 1)[1]

    embed = discord.Embed(
        title="Now Playing:",
        description=f"**Title:** {next_song_title}\n"
                            f"**Creator:** {next_song_creator}\n"
                            f"**Duration:** {next_song_dureation} seconds\n"
                            f"**Views:** {next_song_views}\n"
                            f"**Upload Date:** {next_song_date}\n\n"
                            f"**URL:** [__**Orignal Link ➜**__](<{next_song_url.lstrip()}>)\n",
        color=discord.Color.blue()
    )
    if next_song_thumbnail != 'Unknown':
        embed.set_image(url=next_song_thumbnail.lstrip())
    await interaction.followup.send(embed=embed)


    if voice_client.is_connected():
        voice_client.play(discord.FFmpegPCMAudio(audio_file))
    else:
        return

    while voice_client.is_playing():
        await asyncio.sleep(1)

    try:
        os.remove(audio_file)
        print(f"Removing {audio_file} as part of play_next")
    except OSError as e:
        if e.errno == 2:
            print(f"{audio_file} has already been deleted. Error: {e}")
            return
    try:    
        os.remove(info_file)
        print(f"Removing {info_file} as part of play_next")
    except OSError as e:
        if e.errno == 2:
            print(f"{info_file} has already been deleted. Error: {e}")
            return

    await play_next(interaction)

bot.run(TOKEN)
