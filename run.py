"""Application entry point."""

from __future__ import annotations

import logging
import shutil

from telegram.ext import Application

from bot.handlers import register_handlers
from config.settings import settings

logger = logging.getLogger(__name__)


def check_ffmpeg(ffmpeg_path: str) -> None:
    """Verify FFmpeg is available on PATH; fail fast if it isn't.

    Kept as a small, directly-testable helper in run.py rather than a
    separate module - FFmpeg-related configuration (the path itself)
    lives in config/settings.py, but the startup validation is a
    run.py concern.
    """
    if shutil.which(ffmpeg_path) is None:
        raise RuntimeError(
            f"FFmpeg was not found on PATH (looked for '{ffmpeg_path}'). "
            "Install FFmpeg and make sure it is on PATH before starting the bot."
        )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    check_ffmpeg(settings.ffmpeg_path)

    application = Application.builder().token(settings.bot_token).build()
    register_handlers(application)

    logger.info("Starting bot polling...")
    application.run_polling()


if __name__ == "__main__":
    main()
