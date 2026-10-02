"""Temporary file management for per-request download directories.

Each download request gets its own fresh directory under
settings.download_dir, so two requests for the same video can never
share (or delete) each other's files. Cleanup removes the whole
directory, which also clears .part files and leftover merge fragments
from failed downloads.

Scope (Rule 3/7): directory creation and cleanup only. No Telegram, no
yt-dlp, no knowledge of which platform produced the files.

Both functions take an optional `base_dir` override, purely for
testability - same pattern as `db_path` in language_service.py.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)

_REQUEST_DIR_PREFIX = "req_"


def _resolve_base_dir(base_dir: Optional[str]) -> str:
    return os.path.abspath(base_dir if base_dir is not None else settings.download_dir)


def create_request_dir(base_dir: Optional[str] = None) -> str:
    """Create and return a fresh, unique directory under the base download dir."""
    resolved = _resolve_base_dir(base_dir)
    os.makedirs(resolved, exist_ok=True)
    return tempfile.mkdtemp(prefix=_REQUEST_DIR_PREFIX, dir=resolved)


def cleanup(path: str, base_dir: Optional[str] = None) -> None:
    """Delete a request directory. Never raises.

    Safety guard: refuses to delete anything that is not strictly
    inside the base download dir (including the base dir itself), so a
    bug elsewhere can't turn this into an arbitrary-delete.
    """
    try:
        base = os.path.realpath(_resolve_base_dir(base_dir))
        target = os.path.realpath(path)
        if target == base or os.path.commonpath([base, target]) != base:
            logger.error("Refusing to delete %r: outside %r", path, base)
            return
        shutil.rmtree(target, ignore_errors=True)
    except Exception:
        logger.warning("Cleanup failed for %r", path, exc_info=True)