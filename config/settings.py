"""Application configuration for the Telegram Video Downloader Bot.

This module owns configuration *loading* and *validation* only. It does not
perform any external/operational checks - e.g. it does not verify that the
FFmpeg binary is actually installed and executable. That is a separate
startup-time concern (see run.py) and deliberately lives outside Settings,
since "is FFMPEG_PATH configured?" and "can the OS actually run FFmpeg?"
are two different questions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional

from dotenv import load_dotenv

# Populate os.environ from a local .env file, if one is present. This is a
# side effect intentionally isolated to import time so that from_env()
# itself stays a pure function of whatever mapping it is given.
load_dotenv()


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    """Immutable application configuration.

    Normal application code should use the module-level `settings`
    instance below. Tests should construct their own instance via
    `Settings.from_env(env={...})` instead of relying on real process
    environment variables.
    """

    bot_token: str
    download_dir: str
    db_path: str
    ffmpeg_path: str

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "Settings":
        """Build a Settings instance from an environment mapping.

        Args:
            env: Mapping of environment variable names to values.
                Defaults to `os.environ`. Passing an explicit mapping
                (e.g. a plain dict) lets tests exercise configuration
                loading without touching real environment variables.

        Raises:
            ConfigurationError: if a required variable is missing or blank.
        """
        env = os.environ if env is None else env

        bot_token = (env.get("BOT_TOKEN") or "").strip()
        if not bot_token:
            raise ConfigurationError(
                "BOT_TOKEN is required but was not set. "
                "Copy .env.example to .env and fill in your bot token."
            )

        download_dir = (env.get("DOWNLOAD_DIR") or "downloads/").strip()
        db_path = (env.get("DB_PATH") or "bot.db").strip()
        ffmpeg_path = (env.get("FFMPEG_PATH") or "ffmpeg").strip()

        return cls(
            bot_token=bot_token,
            download_dir=download_dir,
            db_path=db_path,
            ffmpeg_path=ffmpeg_path,
        )


# Default instance for normal application use, e.g.:
#   from config.settings import settings
#   settings.db_path
settings = Settings.from_env()
