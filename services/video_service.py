"""Platform-agnostic video delivery workflow.

deliver_video() runs the shared "download -> send -> clean up" sequence
for any platform. It knows nothing about Telegram, yt-dlp, Instagram or
YouTube: callers pass in what to do as two callables, and get back a
DeliveryOutcome to map onto translated user-facing messages.

    download_fn(request_dir) -> str
        Synchronous (yt-dlp is blocking). Must download into
        `request_dir` and return the path of the resulting file. Run in
        a worker thread so the event loop stays free.
    send_fn(path) -> Awaitable[None]
        Async. Delivers the file at `path` (e.g. via Telegram).

Every call gets its own request directory (see file_service). It is
deleted afterwards on every path - except when KEEP_DOWNLOADS is on
(settings.keep_downloads) and the download itself succeeded: then the
directory is kept whether or not sending worked, so e.g. a video too
large for Telegram's bot upload limit is still available locally.
A failed download is always cleaned up (only partial junk would remain).

Scope (Rule 3/7): no size checks, no retries, no concurrency control.
Those belong to later phases (Phase 2/3).
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import Awaitable, Callable, Optional

from config.settings import settings
from services.file_service import cleanup, create_request_dir

logger = logging.getLogger(__name__)


class DeliveryOutcome(Enum):
    SENT = "sent"
    DOWNLOAD_FAILED = "download_failed"
    SEND_FAILED = "send_failed"


async def deliver_video(
    download_fn: Callable[[str], str],
    send_fn: Callable[[str], Awaitable[None]],
) -> DeliveryOutcome:
    """Download via `download_fn`, send via `send_fn`, then clean up.

    Failures are logged and reported through the returned outcome
    instead of being raised, so a failed download can never crash the
    handler. Task cancellation is not swallowed.
    """
    request_dir: Optional[str] = None
    keep = False
    try:
        try:
            request_dir = create_request_dir()
            path = await asyncio.to_thread(download_fn, request_dir)
        except Exception:
            logger.warning("Download failed", exc_info=True)
            return DeliveryOutcome.DOWNLOAD_FAILED

        keep = settings.keep_downloads

        try:
            await send_fn(path)
        except Exception:
            logger.warning("Sending failed for %r", path, exc_info=True)
            return DeliveryOutcome.SEND_FAILED

        return DeliveryOutcome.SENT
    finally:
        if request_dir is not None:
            if keep:
                logger.info("KEEP_DOWNLOADS is on; keeping files in %s", request_dir)
            else:
                cleanup(request_dir)
