"""Throwaway manual test for downloader/instagram.py.

Not part of the pytest suite - this hits the real network and real
Instagram, which the project's automated tests intentionally never do.

Usage:
    python manual_test_instagram.py "https://www.instagram.com/reel/XXXXXXXXXXX/"

Run from the repo root with your venv active and FFmpeg on PATH (same
requirements as run.py). Delete this file whenever you're done with it -
it's not meant to be committed.
"""

import sys

from downloader.instagram import InstagramDownloadError, download_instagram_video


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python manual_test_instagram.py <instagram-url>")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Attempting to download: {url}")

    try:
        filepath = download_instagram_video(url)
    except InstagramDownloadError as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)

    print(f"SUCCESS: downloaded to {filepath}")


if __name__ == "__main__":
    main()
