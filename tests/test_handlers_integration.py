"""Integration test for bot/handlers.py + services/language_service.py.

Unlike tests/test_handlers.py (which mocks the service layer for fast,
isolated unit tests), this test exercises the real language_service
functions against a temporary SQLite database - no mocking of storage,
no mocking of language logic. It only points language_service at a
tmp_path DB file instead of the real settings.db_path, so the standard
suite still performs no network calls and leaves no files behind.
"""

import types
from unittest.mock import AsyncMock, MagicMock

import pytest

import services.language_service as language_service_module
from bot.handlers import handle_language_selection, start
from services.language_service import get_language, has_saved_language
from services.translations import translate


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Point language_service's default db_path at a temp SQLite file."""
    db_path = str(tmp_path / "integration_test.db")
    monkeypatch.setattr(
        language_service_module, "settings", types.SimpleNamespace(db_path=db_path)
    )
    return db_path


def make_update_for_start(user_id: int) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


def make_update_for_callback(user_id: int, lang: str, chat_id: int = 999) -> MagicMock:
    update = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.from_user.id = user_id
    update.callback_query.data = f"set_lang:{lang}"
    update.callback_query.message.chat_id = chat_id
    return update


@pytest.mark.asyncio
async def test_full_first_time_flow_persists_to_real_db(tmp_db):
    """
    /start (no saved language) -> welcome + language prompt
      -> user taps فارسی -> real DB row written, confirmation sent in fa
      -> /start again -> single "welcome back" message in fa, no keyboard
    """
    user_id = 424242
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    # Nothing saved yet.
    assert has_saved_language(user_id) is False

    # 1. First /start: two messages, no DB row yet.
    first_update = make_update_for_start(user_id)
    await start(first_update, context)

    assert first_update.message.reply_text.await_count == 2
    assert first_update.message.reply_text.await_args_list[0].args[0] == translate(
        "welcome", "en"
    )
    assert first_update.message.reply_text.await_args_list[1].args[0] == translate(
        "choose_language", "en"
    )
    assert has_saved_language(user_id) is False

    # 2. User taps فارسی: real set_language() runs against the tmp DB.
    callback_update = make_update_for_callback(user_id, "fa")
    await handle_language_selection(callback_update, context)

    assert has_saved_language(user_id) is True
    assert get_language(user_id) == "fa"
    context.bot.send_message.assert_awaited_once_with(
        chat_id=999, text=translate("language_set", "fa")
    )

    # 3. /start again: now a returning user, saved language is respected.
    second_update = make_update_for_start(user_id)
    await start(second_update, context)

    second_update.message.reply_text.assert_awaited_once_with(
        translate("welcome_back", "fa")
    )


@pytest.mark.asyncio
async def test_language_preference_is_independent_per_user(tmp_db):
    """Setting one user's language must not affect another user's."""
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    user_a, user_b = 111, 222

    await handle_language_selection(make_update_for_callback(user_a, "en"), context)
    await handle_language_selection(make_update_for_callback(user_b, "fa"), context)

    assert get_language(user_a) == "en"
    assert get_language(user_b) == "fa"
