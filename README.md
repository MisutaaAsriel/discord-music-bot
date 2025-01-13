## Quick Navigation
- [Commands](#commands)
- [Notes](#notes)
- [Installation](#Install)
- [Changelog](#changelog)
- [Terms](#terms)

## <a id="commands"></a>Commands
- Play: The play command takes a YouTube URL as an argument and plays the song in the voice channel that the bot is connected to.
- Skip: The skip command skips the current song.
- Stop: Stops the current playback in the connected channel and disconnects.

## <a id="notes"></a>Notes
The bot will automatically delete the cached file of a played song after it ends. This is to prevent the file from taking up too much space on the bot's hard drive.

## <a id="Install"></a>Installation

### Intents

Please make sure that the following intents are enabled under `Bot` settings in the discord developer portal for your application:
- Presence
- Server Members
- Message Content 

### System Requirements
- Python 3.11 or newer
- FFMPEG

### Dependencies

To install dependencies, use the following command:
```py
pip install -r requirements.txt
```

### Setup

1. Set the environment variable `DISCORD_TOKEN` to your bot token:
```sh
DISCORD_TOKEN="your token here"
```
2. Run the bot with:
```sh
python bot.py
```

## <a id="changelog"></a>Changelog
- 1.0.0: Initial release.
- 1.0.1: Added the ability to skip songs.
- 1.0.2: Added the ability to delete files after songs end.
- 1.0.3:
  - Added new `stop` command & command descriptions
  - Improved YT-DLP options for greater stability.
  - Disabled playlists from attempting to queue everything at once, which breaks the bot.
- 1.0.4: Added new bot status messages, combined `disconnect` with `stop`.
- 1.0.5:
  - Fixed some race conditions, skip command, and command layout.
  - Added more error handling, & status improvements.

## <a id="terms"></a>Terms
This script is for educational purposes only. Use it at your own risk. The developer is not responsible for any damage caused by the misuse of this script.

