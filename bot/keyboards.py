"""Inline keyboards used by bot/handlers.py."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

LANGUAGE_CALLBACK_PREFIX = "set_lang:"


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
