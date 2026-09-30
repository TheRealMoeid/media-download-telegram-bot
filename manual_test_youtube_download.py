"""
manual_test_youtube_download.py

Throwaway diagnostic script for Issue #5 - NOT part of the pytest suite,
and intentionally hits the real network AND writes a real file to disk.

Unlike manual_test_youtube_proxy.py (which only inspects available
formats via skip_download=True), this script performs an actual
download, mirroring what downloader/youtube.py's fallback chain does:
try clients in order, stop at the FIRST one that produces usable
formats, then download+merge with that same client.

Does NOT import any project code (config/settings.py, downloader/*), so
it has no BOT_TOKEN or other config dependency - it runs completely
standalone against yt-dlp directly.

Usage:
    python manual_test_youtube_download.py
    python manual_test_youtube_download.py --direct   (forces proxy="")
    python manual_test_youtube_download.py --url https://youtu.be/SOME_ID

The downloaded file is written to ./manual_download_test/ (created if
needed) - delete that folder afterward, it's not part of the repo.
"""

import argparse
import os

import yt_dlp

DEFAULT_URL = "https://youtu.be/JcYMtYbNUhU?si=XdwrK0TLytSHQono"
OUTPUT_DIR = "manual_download_test"

# Same order as downloader/youtube.py's fallback chain: try yt-dlp's own
# default first, then the configured fallback clients, in order. Stop at
# the first one that actually succeeds - this mirrors real bot behavior,
# not the "try everything regardless" diagnostic style of the other script.
CLIENTS_TO_TRY = [None, "android", "ios", "tv"]

FFMPEG_PATH = r"D:\Program Files\ffmpeg-2026-08-30_full_build\bin\ffmpeg.exe"


def try_download(url: str, client: str | None, direct: bool) -> str | None:
    label = client or "(yt-dlp default)"
    print(f"\n=== Trying client: {label} ===")

    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "ffmpeg_location": FFMPEG_PATH,
        "outtmpl": os.path.join(OUTPUT_DIR, "%(id)s.%(ext)s"),
        "quiet": False,
        "noplaylist": True,
    }
    if direct:
        ydl_opts["proxy"] = ""
    if client is not None:
        ydl_opts["extractor_args"] = {"youtube": {"player_client": [client]}}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as exc:
        print(f"RESULT: FAILED - client={label} - {type(exc).__name__}: {exc}")
        return None

    # Prefer the resolved post-merge path when yt-dlp reports one (same
    # resolution approach as downloader/youtube.py and
    # downloader/instagram.py), falling back to prepare_filename().
    try:
        filepath = info["requested_downloads"][0]["filepath"]
    except (KeyError, IndexError, TypeError):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            filepath = ydl.prepare_filename(info)

    print(f"RESULT: SUCCESS - client={label}")
    return filepath


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direct", action="store_true", help="Force proxy='' (bypass env/system proxy).")
    parser.add_argument("--url", default=DEFAULT_URL, help="YouTube URL to download.")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Mode: {'--direct (proxy=\"\")' if args.direct else 'default (system/env proxy resolution)'}")
    print(f"URL: {args.url}")

    result_path = None
    for client in CLIENTS_TO_TRY:
        result_path = try_download(args.url, client, args.direct)
        if result_path is not None:
            break

    if result_path is None:
        print("\n=== ALL CLIENTS FAILED. No file downloaded. ===")
    else:
        size_mb = os.path.getsize(result_path) / (1024 * 1024)
        print(f"\n=== DONE. Downloaded to: {result_path} ({size_mb:.1f} MB) ===")
        print("Play it to confirm it's a real, watchable video before trusting this result.")
