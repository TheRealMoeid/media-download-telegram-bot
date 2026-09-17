"""Platform detection and downloader selection.

Per PROJECT_ROADMAP.md / CLAUDE.md, this module is responsible for
selecting the appropriate platform downloader. The first piece of that
responsibility - detecting *which* platform a given URL belongs to - is
implemented here as a small, pure, standalone function so it can be
tested in isolation from Telegram, yt-dlp, and everything else.

Scope note (Rule 3 / Rule 7): this only detects the platform. It does not
call yt-dlp, does not perform network requests, and does not select or
invoke a downloader implementation yet - downloader/youtube.py and
downloader/instagram.py are still empty stubs. That wiring is later
Phase 1 work.
"""

from __future__ import annotations

from enum import Enum
from urllib.parse import urlparse

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

INSTAGRAM_HOSTS = {
    "instagram.com",
    "www.instagram.com",
}


class Platform(Enum):
    """The set of platforms this bot can recognize a URL as belonging to."""

    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    UNKNOWN = "unknown"


def detect_platform(url: str) -> Platform:
    """Detect which supported platform, if any, `url` belongs to.

    Validates general URL shape (must parse to a scheme + netloc) and
    then matches the host against known YouTube/Instagram domains.

    Returns Platform.UNKNOWN for:
        - malformed input (not a string, empty, or missing scheme/netloc)
        - well-formed URLs whose host isn't a recognized platform domain

    Never raises on bad input - detection failure is a normal, expected
    outcome (the user may paste anything), not an error condition.
    """
    if not isinstance(url, str):
        return Platform.UNKNOWN

    url = url.strip()
    if not url:
        return Platform.UNKNOWN

    try:
        parsed = urlparse(url)
    except ValueError:
        return Platform.UNKNOWN

    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return Platform.UNKNOWN

    host = parsed.hostname or ""
    host = host.lower()

    if host in YOUTUBE_HOSTS:
        return Platform.YOUTUBE
    if host in INSTAGRAM_HOSTS:
        return Platform.INSTAGRAM

    return Platform.UNKNOWN