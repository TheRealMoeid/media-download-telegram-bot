"""YouTube format inspection and quality-selected downloading.

Mirrors the design already established by downloader/instagram.py
(see CLAUDE.md, Step 6):
    - Anonymous yt-dlp extraction/downloading only - no login, cookies,
      or session state (Phase 0 decision). Nothing in this module ever
      sets cookiefile, cookiesfrombrowser, username, password, or any
      other authentication-related yt-dlp option. Any future cookie/
      session support is a separate, explicit architectural decision
      for a later phase, not something to slip in here.
    - `settings.ffmpeg_path` is passed to yt-dlp explicitly rather than
      letting yt-dlp fall back to searching PATH itself, so it stays
      consistent with the same path run.py's startup check validates.
    - `download_dir` is an optional override of `settings.download_dir`,
      purely for testability - same pattern as `db_path` in
      services/language_service.py and `download_dir` in
      downloader/instagram.py. Production code never passes it.
    - All yt-dlp failures are wrapped into a small set of module-specific
      exceptions, chained via `from exc`, so callers only need to handle
      one exception family regardless of the underlying yt-dlp failure.

Anonymous bot-check fallback (added after real-world testing hit
YouTube's "Sign in to confirm you're not a bot" rejection on the plain
default client - see CLAUDE.md):
    - get_available_qualities() tries yt-dlp's own default anonymous
      behavior first, since it typically exposes the richest format
      list. Only if that is blocked by what looks like YouTube's
      anonymous bot-check, or exposes no usable video formats, does it
      step through a short, fixed, internal list of alternate anonymous
      "player client" identifiers (_FALLBACK_CLIENTS) - still no login,
      still no cookies, just a different anonymous client identity
      yt-dlp presents itself as. The first client that returns a usable
      result wins; formats from different clients are never merged.
    - Whichever client succeeded is recorded on every QualityOption
      returned (the `client` field). download_youtube_video() reuses
      that exact client for the actual download and makes exactly one
      attempt - it does not re-run the fallback chain - so the format
      menu and the eventual download can never disagree about which
      client's view of the video they're based on.
    - Client identifiers are never exposed outside this module: they
      don't appear in bot/handlers.py, bot/keyboards.py, translation
      keys, or anything shown to the user. Callers only ever see
      QualityOption objects and pass them back opaquely.

Scope (Rule 3 / Rule 7): this module inspects the real formats available
for a specific video, normalizes/deduplicates them into presentable
quality options, and downloads one selected option to disk. It has no
knowledge of Telegram, callback data, keyboards, or translations - that
wiring lives in bot/handlers.py and bot/keyboards.py. It also does not
send anything back through Telegram or clean up files - that is the
separate "Delivery" work in PROJECT_ROADMAP.md, shared with Instagram.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yt_dlp

from config.settings import settings


class YouTubeError(Exception):
    """Base class for all YouTube-downloader errors."""


class YouTubeExtractionError(YouTubeError):
    """Raised when yt-dlp fails to inspect/extract info for a URL.

    Raised either when every anonymous client attempt fails outright,
    or when every attempt "succeeds" but exposes no usable video
    formats at all.
    """


class YouTubeDownloadError(YouTubeError):
    """Raised when yt-dlp fails to download a previously-selected format."""


@dataclass(frozen=True)
class QualityOption:
    """A single user-presentable YouTube quality choice.

    `format_id` is a yt-dlp format *selector* string already prepared by
    get_available_qualities() - e.g. "137+bestaudio/best" for a
    video-only stream that needs an audio track merged in, or a plain
    format id when the format already includes audio. Callers
    (bot/handlers.py) should treat this as an opaque token to pass back
    into download_youtube_video(); they should not parse or rebuild it.

    `label` is what a quality-selection button should display, e.g.
    "1080p". `height` is the raw vertical resolution, kept for sorting
    and for tests - not intended for display.

    `client` records which anonymous yt-dlp "player client" produced
    this option during extraction (None means yt-dlp's own default,
    otherwise one of _FALLBACK_CLIENTS). Callers outside this module
    should treat it as an opaque part of the option, never inspect or
    branch on it - its only job is letting download_youtube_video()
    reuse the exact same successful context that built the menu.
    """

    format_id: str
    label: str
    height: int
    client: Optional[str] = None


# Short, fixed, anonymous-only fallback chain for YouTube's "Sign in to
# confirm you're not a bot" rejection on the plain default client.
# Deliberately kept small (Rule 3/7): these three are the commonly
# documented anonymous workarounds for this specific error. Not a
# general client-enumeration strategy - if one of these ever proves
# unreliable, replace it, but keep the list this short.
_FALLBACK_CLIENTS: tuple[str, ...] = ("android", "ios", "tv")

_BOT_CHECK_MARKERS = ("sign in to confirm", "not a bot")


def _is_bot_check_error(exc: Exception) -> bool:
    """True if `exc` looks like YouTube's anonymous bot-check rejection.

    Only errors matching this heuristic trigger a fallback-client retry.
    Anything else (a private/deleted/region-locked video, a network
    failure, etc.) is a real failure that no alternate anonymous client
    would fix, so it's raised immediately instead of burning through
    three more attempts for no benefit.
    """
    text = str(exc).lower()
    return any(marker in text for marker in _BOT_CHECK_MARKERS)


def _has_usable_video_formats(info: dict) -> bool:
    formats = info.get("formats") or []
    return any(
        fmt.get("height") and fmt.get("vcodec") not in (None, "none")
        for fmt in formats
    )


def _build_ydl_opts(client: Optional[str] = None, **overrides: object) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "ffmpeg_location": settings.ffmpeg_path,
    }
    if client is not None:
        opts["extractor_args"] = {"youtube": {"player_client": [client]}}
    opts.update(overrides)
    return opts


def _run_single_extraction(url: str, client: Optional[str]) -> dict:
    """One inspect-only (download=False) attempt using a given client.

    `client=None` means yt-dlp's own default anonymous behavior; any
    other value overrides the "player_client" extractor arg. Raises
    yt_dlp.utils.DownloadError unwrapped - the fallback loop in
    _extract_info_with_fallback() decides what to do with it.
    """
    ydl_opts = _build_ydl_opts(client=client)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


def _extract_info_with_fallback(url: str) -> tuple[dict, Optional[str]]:
    """Inspect `url`, trying the default anonymous client first and
    falling back to a short fixed list of alternate anonymous clients
    only if the default is blocked or exposes no usable formats.

    Returns (info, client): `client` is whichever one produced the
    usable result (None for the plain default). Callers must hang onto
    this and reuse it for the eventual download - see
    download_youtube_video() - rather than recomputing or guessing it.

    Formats are never merged across clients; the first client with at
    least one usable video format wins outright and the loop stops.

    Raises:
        YouTubeExtractionError: if every attempt fails, or every
            attempt succeeds but exposes zero usable video formats.
    """
    last_exc: Optional[Exception] = None

    for client in (None, *_FALLBACK_CLIENTS):
        try:
            info = _run_single_extraction(url, client)
        except yt_dlp.utils.DownloadError as exc:
            if _is_bot_check_error(exc):
                last_exc = exc
                continue
            raise YouTubeExtractionError(
                f"Failed to extract info for YouTube URL {url!r}: {exc}"
            ) from exc

        if _has_usable_video_formats(info):
            return info, client

        last_exc = None  # this client "worked" but exposed nothing usable

    if last_exc is not None:
        raise YouTubeExtractionError(
            f"Failed to extract info for YouTube URL {url!r} after "
            f"trying all anonymous clients: {last_exc}"
        ) from last_exc

    raise YouTubeExtractionError(
        f"YouTube URL {url!r} returned no usable video formats from "
        f"any anonymous client."
    )


def _format_rank(fmt: dict) -> tuple:
    """Sort key used to pick the "best" format at a given resolution.

    YouTube commonly exposes more than one encode at the same height
    (e.g. two different 1080p streams). Total bitrate (tbr) is the
    primary quality signal; filesize is a fallback for the rare case
    where tbr is missing, so ties aren't resolved arbitrarily.
    """
    tbr = fmt.get("tbr") or 0
    filesize = fmt.get("filesize") or fmt.get("filesize_approx") or 0
    return (tbr, filesize)


def get_available_qualities(url: str) -> list[QualityOption]:
    """Return the deduplicated, user-presentable qualities for `url`.

    Inspects the real formats yt-dlp reports for this specific video
    (Rule 5 - YouTube quality is always inspected per video, never
    assumed), using the default-first/fallback-client strategy
    described in the module docstring. Only formats with an actual
    video stream (vcodec not "none") are considered; audio-only formats
    are never surfaced as a "quality" choice, since the matching audio
    track is attached automatically at download time when a video-only
    stream is chosen.

    Deduplicates by height: when multiple formats share the same
    resolution, the highest-ranked one (see _format_rank) is kept, so
    the resulting menu never shows two buttons that look identical.

    Returns options sorted from highest to lowest resolution, each
    tagged with whichever client produced this result (see
    QualityOption.client) so a later download can reuse it exactly.

    Raises:
        YouTubeExtractionError: see _extract_info_with_fallback().
    """
    info, client = _extract_info_with_fallback(url)
    formats = info.get("formats") or []

    best_by_height: dict[int, dict] = {}
    for fmt in formats:
        height = fmt.get("height")
        vcodec = fmt.get("vcodec")
        if not height or vcodec in (None, "none"):
            continue

        current_best = best_by_height.get(height)
        if current_best is None or _format_rank(fmt) > _format_rank(current_best):
            best_by_height[height] = fmt

    options = []
    for height, fmt in best_by_height.items():
        format_id = fmt["format_id"]
        needs_audio = fmt.get("acodec") in (None, "none")
        selector = f"{format_id}+bestaudio/best" if needs_audio else format_id
        options.append(
            QualityOption(
                format_id=selector, label=f"{height}p", height=height, client=client
            )
        )

    options.sort(key=lambda option: option.height, reverse=True)
    return options


def download_youtube_video(
    url: str, option: QualityOption, download_dir: Optional[str] = None
) -> str:
    """Download `url` using the exact client and format selector already
    recorded on `option` (from get_available_qualities()).

    Makes exactly one attempt - no fallback loop here. `option.client`
    already proved it can extract this specific video during the
    extraction step; if the same client now fails, that's a genuine
    download failure worth surfacing as YouTubeDownloadError, not a
    client mismatch to silently paper over by trying something else.
    This is what guarantees the quality menu and the actual download
    never disagree about which anonymous client's view of the video
    they're using.

    Returns the path to the downloaded file on disk. Does not send the
    file anywhere or delete it afterwards - see module docstring.

    Raises:
        YouTubeDownloadError: if yt-dlp fails for any reason.
    """
    resolved_dir = download_dir if download_dir is not None else settings.download_dir
    os.makedirs(resolved_dir, exist_ok=True)

    ydl_opts = _build_ydl_opts(
        client=option.client,
        format=option.format_id,
        merge_output_format="mp4",
        outtmpl=os.path.join(resolved_dir, "%(id)s.%(ext)s"),
    )

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as exc:
        raise YouTubeDownloadError(
            f"Failed to download YouTube URL {url!r} at format "
            f"{option.format_id!r} (client={option.client!r}): {exc}"
        ) from exc

    requested_downloads = info.get("requested_downloads")
    if requested_downloads:
        return requested_downloads[0]["filepath"]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.prepare_filename(info)