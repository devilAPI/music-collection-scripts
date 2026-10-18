# music-collection-scripts

Bash & Python scripts to download liked/saved music from Spotify, SoundCloud, and YouTube, then sync the collection to an iPod (Rockbox), a remote server (SFTP), or both.

## What it does

`main.sh` is the single entry point. It reads `.env` to decide which steps to run:

| Step | Toggle | What happens |
|---|---|---|
| **Spotify sync** | `ENABLE_SPOTIFY_LIKED_SYNC` | Mirrors your Liked Songs into a public/private playlist, then downloads each track as Opus via [Sunnify](https://github.com/AlirezaF80/Sunnify) (YouTube search + Spotify metadata) |
| **SoundCloud sync** | `ENABLE_SOUNDCLOUD_SYNC` | Downloads your SoundCloud likes (or a playlist) with `yt-dlp` |
| **YouTube sync** | `ENABLE_YOUTUBE_SYNC` | Downloads a YouTube playlist with `yt-dlp` |
| **Cover fix** | `ENABLE_COVER_FIX` | Crops wide (16:9) cover art embedded in `.opus` files to 1:1 |
| **iPod sync** | `ENABLE_IPOD_SYNC` | `rsync` to a mounted Rockbox iPod |
| **SFTP sync** | `ENABLE_SFTP_SYNC` | `lftp mirror` to a remote server |

## Requirements

- bash, curl, jq
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (SoundCloud & YouTube)
- [Sunnify](https://github.com/AlirezaF80/Sunnify) (Spotify download — the `sunnify-opus.py` wrapper expects it installed at `/opt/sunnify`)
- Python 3 with `mutagen` and `Pillow` (cover fix)
- rsync (iPod sync)
- lftp (SFTP sync)

## Setup

1. Copy `.env.example` to `.env` and fill in your values (see the section below).
2. Run `chmod +x main.sh`.
3. Run `./main.sh`.

### Spotify OAuth (first-time only)

1. Create an app at https://developer.spotify.com/dashboard.
2. Set the redirect URI to `http://127.0.0.1:9090`.
3. Put `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIFY_REDIRECT_URI` in `.env`.
4. Run `bash build-url.sh` — it prints an authorization URL. Open it in a browser and grab the `code` parameter from the redirect.
5. Run `bash refresh-token.sh` with the code to exchange it for a refresh token. Put the `refresh_token` value in `.env` as `SPOTIFY_REFRESH_TOKEN`.

### `.env` reference

```
# Toggles
ENABLE_SPOTIFY_LIKED_SYNC=true
ENABLE_SOUNDCLOUD_SYNC=true
ENABLE_YOUTUBE_SYNC=true
ENABLE_COVER_FIX=true
ENABLE_IPOD_SYNC=false
ENABLE_SFTP_SYNC=false

# Sources
SOUNDCLOUD_LIKES_URL="https://soundcloud.com/you/likes"
YOUTUBE_PLAYLIST_URL="https://youtube.com/playlist?list=..."

# Spotify
SPOTIFY_CLIENT_ID=""
SPOTIFY_CLIENT_SECRET=""
SPOTIFY_REFRESH_TOKEN=""
SPOTIFY_REDIRECT_URI="http://127.0.0.1:9090"
SPOTIFY_SCOPES="user-library-read playlist-modify-private playlist-modify-public playlist-read-private"
SPOTIFY_PLAYLIST_NAME="Liked Songs (Mirror)"

# Output
OUTPUT_FOLDER="/path/to/music"

# iPod (Rockbox)
IPOD_OUT="/mnt/iPod/Sync/"

# SFTP
SFTP_HOST="example.com"
SFTP_USER=""
SFTP_PASS=""
SFTP_DIR="/remote/path/"
SFTP_PORT=22
```

## Files

| File | Purpose |
|---|---|
| `main.sh` | Orchestrator — runs enabled steps in order |
| `spotify-likes-sync.sh` | Spotify liked songs mirror + download |
| `soundcloud-likes-sync.sh` | SoundCloud likes download via yt-dlp |
| `youtube-sync.sh` | YouTube playlist download via yt-dlp |
| `sunnify-opus.py` | Sunnify wrapper — adds Opus tagging and a YouTube Music search fallback |
| `fix_covers.py` | Crops wide cover art in .opus files to square |
| `build-url.sh` | Prints the Spotify OAuth authorization URL |
| `refresh-token.sh` | Exchanges a Spotify auth code for a refresh token |

## License

Do whatever you want with it.
