"""Throwaway manual diagnostic for downloader/youtube.py's anonymous
extraction fallback chain (default -> android -> ios -> tv).

NOT part of the automated test suite. Real-world extraction correctness
is checked here, once, against a live URL - never inside pytest, which
must never make real network calls (same convention already documented
in CLAUDE.md for manual_test_instagram.py).

Usage:
    python manual_test_youtube_fallback.py "<a public, non-age-restricted YouTube URL>"

Prints only sanitized diagnostic info: which client succeeded (or that
none did), how many qualities were found, and their labels, plus a
truncated error message if every client failed. No cookies or auth of
any kind are used anywhere in this path, so there's nothing secret to
leak - the output is kept short and structured so it's safe to paste
directly into chat.

Delete this file once you're done with it - it's scratch, not part of
the repo.
"""

from __future__ import annotations

import sys

from downloader.youtube import YouTubeExtractionError, get_available_qualities


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python manual_test_youtube_fallback.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Testing anonymous extraction fallback chain against:\n  {url}")
    print("Order: default -> android -> ios -> tv\n")

    try:
        options = get_available_qualities(url)
    except YouTubeExtractionError as exc:
        underlying_type = type(exc.__cause__).__name__ if exc.__cause__ else "n/a"
        print("RESULT: all anonymous clients failed.")
        print(f"Underlying yt-dlp exception type: {underlying_type}")
        print(f"Error message (truncated to 200 chars): {str(exc)[:200]}")
        sys.exit(1)

    winning_client = options[0].client if options else None
    print(f"RESULT: succeeded using client = {winning_client!r}")
    print(f"Qualities found ({len(options)}): {[o.label for o in options]}")


if __name__ == "__main__":
    main()
