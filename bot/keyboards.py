"""Inline keyboards used by bot/handlers.py.

This module only builds keyboard layouts from data it is handed - it
never decides *what* qualities exist (that's downloader/youtube.py) and
never validates or interprets a tap afterwards (that's bot/handlers.py).
"""

from __future__ import annotations

from typing import Optional, Sequence

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from downloader.youtube import QualityOption
from services.translations import translate

LANGUAGE_CALLBACK_PREFIX = "set_lang:"
YOUTUBE_QUALITY_CALLBACK_PREFIX = "yt_quality:"
MENU_CALLBACK_PREFIX = "menu:"

# Actions carried after MENU_CALLBACK_PREFIX. Navigation only - they never
# change stored state (language is saved by the existing set_lang: flow).
MENU_ACTION_SETTINGS = "settings"
MENU_ACTION_LANGUAGE = "language"
MENU_ACTION_BACK = "back"

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


def language_selection_keyboard(
    back_label: Optional[str] = None,
) -> InlineKeyboardMarkup:
    """Build the Persian / English language-selection inline keyboard.

    With no argument this is exactly the keyboard /start shows. When
    `back_label` is given (the in-menu picker), a second row with a Back
    button is added that returns to the Settings screen.
    """
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
    if back_label is not None:
        buttons.append(
            [
                InlineKeyboardButton(
                    back_label,
                    callback_data=f"{MENU_CALLBACK_PREFIX}{MENU_ACTION_SETTINGS}",
                )
            ]
        )
    return InlineKeyboardMarkup(buttons)


def main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Main menu: a single Settings button, labelled in `lang`."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    translate("menu.settings_button", lang),
                    callback_data=f"{MENU_CALLBACK_PREFIX}{MENU_ACTION_SETTINGS}",
                )
            ]
        ]
    )


def settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Settings screen: Language, then Back to the main menu."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    translate("menu.language_button", lang),
                    callback_data=f"{MENU_CALLBACK_PREFIX}{MENU_ACTION_LANGUAGE}",
                )
            ],
            [
                InlineKeyboardButton(
                    translate("menu.back_button", lang),
                    callback_data=f"{MENU_CALLBACK_PREFIX}{MENU_ACTION_BACK}",
                )
            ],
        ]
    )


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