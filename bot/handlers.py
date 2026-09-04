"""Telegram command and callback handlers.

Handlers never manage storage or translation lookups directly - they go
through services/language_service.py and services/translations.py.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from bot.keyboards import LANGUAGE_CALLBACK_PREFIX, language_selection_keyboard
from services.language_service import get_language, has_saved_language, set_language
from services.translations import translate

logger = logging.getLogger(__name__)

_DEFAULT_LANGUAGE = "en"


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


def register_handlers(application: Application) -> None:
    """Register all handlers defined in this module on `application`."""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        CallbackQueryHandler(
            handle_language_selection, pattern=f"^{LANGUAGE_CALLBACK_PREFIX}"
        )
    )
