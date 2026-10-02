"""Inline keyboards used by bot/handlers.py.

This module only builds keyboard layouts from data it is handed - it
never decides *what* qualities exist (that's downloader/youtube.py) and
never validates or interprets a tap afterwards (that's bot/handlers.py).
"""

from __future__ import annotations

from typing import Sequence

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from downloader.youtube import QualityOption

LANGUAGE_CALLBACK_PREFIX = "set_lang:"
YOUTUBE_QUALITY_CALLBACK_PREFIX = "yt_quality:"

_MB = 1024 * 1024


def format_size(size_bytes: int) -> str:
    """Human-readable size for a button, e.g. "85 MB" or "1.2 GB"."""
    mb = size_bytes / _MB
    if mb < 1:
        return "<1 MB"
    if round(mb) >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{round(mb)} MB"


def _quality_button_text(option: QualityOption) -> str:
    """Button text: the label, plus an approximate size when known."""
    if option.filesize:
        return f"{option.label} (~{format_size(option.filesize)})"
    return option.label


def language_selection_keyboard() -> InlineKeyboardMarkup:
    """Build the Persian / English language-selection inline keyboard."""
    buttons = [
        [
            InlineKeyboardButton(
                "\U0001F1EE\U0001F1F7 \u0641\u0627\u0631\u0633\u06CC",
                callback_data=f"{LANGUAGE_CALLBACK_PREFIX}fa",
            ),
            InlineKeyboardButton(
                "\U0001F1FA\U0001F1F8 English",
                callback_data=f"{LANGUAGE_CALLBACK_PREFIX}en",
            ),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


def youtube_quality_keyboard(
    token: str, options: Sequence[QualityOption]
) -> InlineKeyboardMarkup:
    """Build a one-button-per-row keyboard from real available qualities.

    `token` identifies the pending selection this menu belongs to (see
    bot/handlers.py's pending-selection tracking); `options` is exactly
    what downloader.youtube.get_available_qualities() returned for this
    specific video - this function never invents or assumes qualities.

    Each button shows the quality label and, when known, an approximate
    file size (e.g. "1080p (~85 MB)"). Each button's callback_data
    encodes only the token and the option's position in `options`
    (e.g. "yt_quality:AbC123:0") - never the raw URL or yt-dlp format
    id, so handlers.py can validate the tap against the still-pending
    selection before trusting anything in it.
    """
    buttons = [
        [
            InlineKeyboardButton(
                _quality_button_text(option),
                callback_data=f"{YOUTUBE_QUALITY_CALLBACK_PREFIX}{token}:{index}",
            )
        ]
        for index, option in enumerate(options)
    ]
    return InlineKeyboardMarkup(buttons)