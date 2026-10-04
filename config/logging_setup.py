"""Logging configuration with secret redaction (Phase 2A).

Two layers protect the bot token:

1. Noisy libraries are silenced. python-telegram-bot talks to Telegram
   through httpx, which logs every request URL at INFO - and Telegram
   API URLs contain the bot token (.../bot<TOKEN>/getUpdates). httpx
   and httpcore are pinned to WARNING so those routine lines are never
   emitted at all.
2. Everything that IS emitted passes through RedactingFormatter, which
   scrubs the token from the *final formatted text* (message and
   traceback). This is the safety net for any other logger, or an
   error message that happens to embed a Telegram URL.

This module deliberately does not import config.settings (which needs
BOT_TOKEN at import time): callers pass the token in, which also keeps
it trivially testable.
"""

from __future__ import annotations

import logging
import os
import re
from logging.handlers import RotatingFileHandler
from typing import Optional

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LOG_FILE = os.path.join("logs", "bot.log")
DEFAULT_MAX_BYTES = 1_000_000  # 1 MB
DEFAULT_BACKUP_COUNT = 3

_REDACTED = "<redacted>"
_NOISY_LOGGERS = ("httpx", "httpcore")

# Matches the token as it appears in a Telegram API URL: /bot<id>:<secret>
_TOKEN_IN_URL = re.compile(r"/bot\d+:[A-Za-z0-9_-]+")

# Marks handlers installed by configure_logging() so a second call
# replaces them instead of duplicating every log line.
_HANDLER_MARKER = "_bot_logging_handler"


class RedactingFormatter(logging.Formatter):
    """Formatter that masks the bot token in the fully formatted output."""

    def __init__(self, token: Optional[str], fmt: str = LOG_FORMAT) -> None:
        super().__init__(fmt)
        self._token = token or ""

    def redact(self, text: str) -> str:
        if self._token:
            text = text.replace(self._token, _REDACTED)
        return _TOKEN_IN_URL.sub("/bot" + _REDACTED, text)

    def format(self, record: logging.LogRecord) -> str:
        return self.redact(super().format(record))


def configure_logging(
    token: Optional[str],
    level: str = "INFO",
    log_file: str = DEFAULT_LOG_FILE,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> None:
    """Set up console + rotating-file logging with token redaction.

    Safe to call more than once: handlers from a previous call are
    removed first.
    """
    root = logging.getLogger()

    for handler in list(root.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            root.removeHandler(handler)
            handler.close()

    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    formatter = RedactingFormatter(token)
    handlers = [
        logging.StreamHandler(),
        RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        ),
    ]
    for handler in handlers:
        handler.setFormatter(formatter)
        setattr(handler, _HANDLER_MARKER, True)
        root.addHandler(handler)

    root.setLevel(level.upper())

    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
