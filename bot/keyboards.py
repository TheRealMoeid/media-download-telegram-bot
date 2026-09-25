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

    Each button's callback_data encodes only the token and the option's
    position in `options` (e.g. "yt_quality:AbC123:0") - never the raw
    URL or yt-dlp format id, so handlers.py can validate the tap against
    the still-pending selection before trusting anything in it.
    """
    buttons = [
        [
            InlineKeyboardButton(
                option.label,
                callback_data=f"{YOUTUBE_QUALITY_CALLBACK_PREFIX}{token}:{index}",
            )
        ]
        for index, option in enumerate(options)
    ]
    return InlineKeyboardMarkup(buttons)