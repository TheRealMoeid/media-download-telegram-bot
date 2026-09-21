"""Instagram video downloading via yt-dlp (anonymous extraction).

Per PROJECT_ROADMAP.md / CLAUDE.md, Instagram always auto-downloads the
best available quality - there is no user-facing quality menu (contrast
with downloader/youtube.py, which will inspect formats and let the user
choose). This module implements that policy using yt-dlp's built-in
Instagram extractor, anonymously: no login, session, or cookies are used
or required (Phase 0 decision: "Instagram authentication - Phase 1 uses
anonymous yt-dlp extraction only").

Scope note (Rule 3/7): this module only downloads a single Instagram
post/reel URL to a file on disk and returns its path. It does not send
anything to Telegram and does not delete the file afterwards - that is
services/video_service.py and services/file_service.py's job (still
empty stubs; wiring this into the bot's delivery flow is later Phase 1
work, tracked separately from "Instagram downloading" itself in
PROJECT_ROADMAP.md's Phase 1 task list).

The architecture leaves room for cookie/session-based authentication to
be added in a later phase (see _build_ydl_opts) without changing this
module's public function signature.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import yt_dlp

from config.settings import settings

logger = logging.getLogger(__name__)


class InstagramDownloadError(Exception):
    """Raised when an Instagram post/reel cannot be extracted or downloaded.

    Wraps whatever yt-dlp raised internally (chained via `from exc`) so
    callers only need to handle one exception type regardless of the
    underlying failure (network error, private/unavailable post,
    unsupported content, FFmpeg merge failure, etc.).
    """


def _build_ydl_opts(download_dir: str, ffmpeg_path: str) -> dict[str, Any]:
    """Build the yt-dlp options used for Instagram downloads.

    format="bestvideo+bestaudio/best" is what "best available quality,
    never intentionally reduced" means in practice: always prefer the
    highest-quality video and audio streams yt-dlp can find, merging
    them via FFmpeg when Instagram exposes them separately, and falling
    back to the best single combined stream when it doesn't.

    ffmpeg_location is passed explicitly (rather than letting yt-dlp
    fall back to searching PATH itself) so this module honors the same
    configured FFMPEG_PATH that run.py's startup check already
    validates, instead of silently relying on a second, potentially
    different resolution of "ffmpeg".

    Anonymous by design - no cookies/session options are set here (see
    module docstring). A later phase can extend this dict (e.g. a
    "cookiefile" key) to add optional authentication without changing
    download_instagram_video()'s public interface.
    """
    return {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(download_dir, "%(id)s.%(ext)s"),
        "ffmpeg_location": ffmpeg_path,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }


def _resolve_downloaded_filepath(ydl: "yt_dlp.YoutubeDL", info: dict[str, Any]) -> str:
    """Resolve the actual downloaded file path from yt-dlp's result info.

    Prefers info["requested_downloads"][0]["filepath"], which reflects
    the final path after any FFmpeg merge/remux (e.g. when
    merge_output_format changes the file extension). Falls back to
    ydl.prepare_filename(info) for result shapes that don't include
    requested_downloads.
    """
    requested_downloads = info.get("requested_downloads") or []
    if requested_downloads and requested_downloads[0].get("filepath"):
        return requested_downloads[0]["filepath"]
    return ydl.prepare_filename(info)


def download_instagram_video(url: str, download_dir: Optional[str] = None) -> str:
    """Download an Instagram post/reel at the best available quality.

    Uses yt-dlp's Instagram extractor anonymously - no login or session
    is used or required (Phase 1 scope; see module docstring).

    Args:
        url: An Instagram post/reel URL. Callers are expected to have
            already confirmed this is an Instagram URL via
            downloader.manager.detect_platform() - this function does
            not re-validate the platform.
        download_dir: Optional override of settings.download_dir, for
            testability. Mirrors the db_path override pattern used in
            services/language_service.py.

    Returns:
        The path to the downloaded video file on disk.

    Raises:
        InstagramDownloadError: if extraction or download fails for any
            reason (network failure, private/unavailable post,
            unsupported content, FFmpeg merge failure, etc.).
    """
    resolved_dir = download_dir if download_dir is not None else settings.download_dir
    os.makedirs(resolved_dir, exist_ok=True)

    ydl_opts = _build_ydl_opts(resolved_dir, settings.ffmpeg_path)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = _resolve_downloaded_filepath(ydl, info)
    except yt_dlp.utils.DownloadError as exc:
        logger.error("Instagram download failed for %s: %s", url, exc)
        raise InstagramDownloadError(
            f"Could not download Instagram media from {url!r}: {exc}"
        ) from exc

    return filepath