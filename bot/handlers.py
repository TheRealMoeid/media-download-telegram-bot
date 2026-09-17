"""Telegram command and callback handlers.

Handlers never manage storage, translation lookups, or platform-detection
logic directly - they go through services/language_service.py,
services/translations.py, and downloader/manager.py.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.keyboards import LANGUAGE_CALLBACK_PREFIX, language_selection_keyboard
from downloader.manager import Platform, detect_platform
from services.language_service import get_language, has_saved_language, set_language
from services.translations import translate

logger = logging.getLogger(__name__)

_DEFAULT_LANGUAGE = "en"

_PLATFORM_TRANSLATION_KEYS = {
    Platform.YOUTUBE: "url.detected_youtube",
    Platform.INSTAGRAM: "url.detected_instagram",
    Platform.UNKNOWN: "url.unsupported",
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start.

    Returning users (a saved language already exists) get a single
    "Welcome back!" message in their saved language.

    First-time users get two separate messages: a plain welcome (no
    keyboard), followed by the language-selection prompt with the
    inline keyboard attached. Before any choice is saved, this is
    always rendered in English.
    """
    user_id = update.effective_user.id

    if has_saved_language(user_id):
        lang = get_language(user_id)
        await update.message.reply_text(translate("welcome_back", lang))
        return

    await update.message.reply_text(translate("welcome", _DEFAULT_LANGUAGE))
    await update.message.reply_text(
        translate("choose_language", _DEFAULT_LANGUAGE),
        reply_markup=language_selection_keyboard(),
    )


async def handle_language_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle a tap on one of the language-selection buttons.

    Saves the choice first, then sends the confirmation in the
    newly-selected language (never in whatever language was active
    before).
    """
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    lang = query.data.removeprefix(LANGUAGE_CALLBACK_PREFIX)

    set_language(user_id, lang)

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=translate("language_set", lang),
    )


async def handle_url_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle a plain text message, treating it as a possible video URL.

    Detects the platform via downloader.manager.detect_platform() and
    replies in the user's saved language. This does not download
    anything yet - downloader/youtube.py and downloader/instagram.py
    are still empty stubs (Phase 1, next steps). This only closes the
    detection loop end-to-end so the user gets a clear response either
    way, instead of silence.
    """
    user_id = update.effective_user.id
    lang = get_language(user_id)

    url_text = update.message.text
    platform = detect_platform(url_text)

    translation_key = _PLATFORM_TRANSLATION_KEYS[platform]
    await update.message.reply_text(translate(translation_key, lang))


def register_handlers(application: Application) -> None:
    """Register all handlers defined in this module on `application`."""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        CallbackQueryHandler(
            handle_language_selection, pattern=f"^{LANGUAGE_CALLBACK_PREFIX}"
        )
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url_message)
    )