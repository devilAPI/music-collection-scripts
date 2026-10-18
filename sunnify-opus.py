#!/opt/sunnify/venv/bin/python
"""Sunnify CLI with tagging for Opus files and a wider YouTube search.

Sunnify writes tags and cover art for mp3/m4a/flac only and leaves .opus
files untagged, and its search query (title + every artist + "audio") often
returns nothing for tracks that are on YouTube. This registers an Opus
writer and a search fallback, then hands over to the normal CLI, so all
arguments are the ones of `sunnify`.
"""
import base64
import os
import re
import sys
from urllib.parse import quote

# Sunnify imports PyQt6 even for headless runs
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import Spotify_Downloader as app  # noqa: E402
import spotifydown_api  # noqa: E402
import sunnify_cli  # noqa: E402


def write_metadata_opus(filename, tags, cover_bytes):
    from mutagen.flac import Picture
    from mutagen.oggopus import OggOpus

    audio = OggOpus(filename)
    audio["title"] = tags.get("title", "")
    audio["artist"] = tags.get("artists", "")
    audio["album"] = tags.get("album", "")
    date = tags.get("releaseDate", "")
    if date:
        audio["date"] = date
    track_num = tags.get("trackNumber") or 0
    if track_num:
        audio["tracknumber"] = str(track_num)
    if cover_bytes:
        pic = Picture()
        pic.type = 3  # Front cover
        pic.mime = app._detect_image_mime(cover_bytes)
        pic.desc = "Cover"
        pic.data = cover_bytes
        audio["metadata_block_picture"] = [base64.b64encode(pic.write()).decode("ascii")]
    audio.save()


app._METADATA_WRITERS[".opus"] = write_metadata_opus


_FLAT_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "extract_flat": True,
    "ignoreerrors": True,
    "playlistend": 5,
    "socket_timeout": 15,
}
_FULL_OPTS = {**_FLAT_OPTS, "extract_flat": False}

_select_youtube_match = app.MusicScraper._select_youtube_match
_fallback_results = {}


def _ytmusic_match(scraper, terms, expected_duration_s, expected_title, first_artist):
    """Pick a YouTube Music song for `terms`, or None.

    Song titles there carry no artist and the search result has no duration,
    so each title match is looked up in full and has to agree on the artist
    and on the length before it is accepted.
    """
    url = "https://music.youtube.com/search?q=" + quote(terms) + "#songs"
    try:
        with app.YoutubeDL(_FLAT_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        app.log.warning("yt music search raised %s: %s", type(exc).__name__, str(exc)[:300])
        return None
    entries = [e for e in (info or {}).get("entries", []) if e and e.get("id")]
    candidates = [
        e for e in entries if scraper._title_plausibly_matches(e.get("title"), expected_title)
    ]

    artist = scraper._normalize_title(first_artist)
    for entry in candidates[:3]:
        video_url = f"https://www.youtube.com/watch?v={entry['id']}"
        try:
            with app.YoutubeDL(_FULL_OPTS) as ydl:
                video = ydl.extract_info(video_url, download=False)
        except Exception:
            video = None
        if not video:
            continue
        credited = " ".join(
            str(video.get(key) or "") for key in ("artist", "channel", "uploader", "title")
        )
        if artist and artist not in scraper._normalize_title(credited):
            continue
        duration = video.get("duration")
        if expected_duration_s and (
            not duration or abs(duration - expected_duration_s) > scraper._DURATION_TOLERANCE_S
        ):
            continue
        app.log.info("yt music fallback matched %s for %r", entry["id"], terms)
        return video_url
    return None


def select_youtube_match_with_fallback(
    self, search_query, expected_duration_s, expected_title=None, expected_artists=None
):
    video_url = _select_youtube_match(
        self, search_query, expected_duration_s, expected_title, expected_artists
    )
    if video_url or not expected_title or not expected_artists:
        return video_url

    # Sunnify asks once per query variant, the fallback is the same for all of them
    key = (expected_title, expected_artists)
    if key not in _fallback_results:
        first_artist = re.split(r"[,&]", expected_artists)[0].strip()
        terms = f"{first_artist} {expected_title}"
        _fallback_results[key] = _select_youtube_match(
            self, f"ytsearch5:{terms}", expected_duration_s, expected_title, expected_artists
        ) or _ytmusic_match(self, terms, expected_duration_s, expected_title, first_artist)
    return _fallback_results[key]


app.MusicScraper._select_youtube_match = select_youtube_match_with_fallback


# For a single track URL Sunnify searches without telling the matcher which
# title and artists to expect, so it takes the top hit and the fallback above
# never runs. Remember the track it looked up and pass both along.
_get_track = spotifydown_api.PlaylistClient.get_track
_download_track_audio = app.MusicScraper.download_track_audio
_last_track = None


def get_track_and_remember(self, track_id):
    global _last_track
    _last_track = _get_track(self, track_id)
    return _last_track


def download_track_audio_with_expectations(
    self,
    search_query,
    destination,
    expected_duration_s=None,
    expected_title=None,
    expected_artists=None,
):
    if expected_title is None and _last_track is not None:
        expected_title = _last_track.title
        expected_artists = _last_track.artists
    return _download_track_audio(
        self, search_query, destination, expected_duration_s, expected_title, expected_artists
    )


spotifydown_api.PlaylistClient.get_track = get_track_and_remember
app.MusicScraper.download_track_audio = download_track_audio_with_expectations

if __name__ == "__main__":
    sys.exit(sunnify_cli.main())
