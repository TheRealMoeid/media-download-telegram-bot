from unittest.mock import AsyncMock, MagicMock

import pytest

import bot.handlers as handlers_module
from bot.handlers import handle_language_selection, start
from services.translations import translate


def make_update_for_start(user_id: int = 111) -> MagicMock:
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
async def test_start_first_time_user_sends_welcome_then_language_prompt(monkeypatch):
    monkeypatch.setattr(handlers_module, "has_saved_language", lambda user_id: False)

    update = make_update_for_start()
    context = MagicMock()

    await start(update, context)

    assert update.message.reply_text.await_count == 2

    first_call_args = update.message.reply_text.await_args_list[0]
    second_call_args = update.message.reply_text.await_args_list[1]

    assert first_call_args.args[0] == translate("welcome", "en")
    assert "reply_markup" not in first_call_args.kwargs

    assert second_call_args.args[0] == translate("choose_language", "en")
    assert "reply_markup" in second_call_args.kwargs


@pytest.mark.asyncio
async def test_start_returning_user_sends_single_welcome_back_in_saved_language(monkeypatch):
    monkeypatch.setattr(handlers_module, "has_saved_language", lambda user_id: True)
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "fa")

    update = make_update_for_start()
    context = MagicMock()

    await start(update, context)

    update.message.reply_text.assert_awaited_once_with(translate("welcome_back", "fa"))


@pytest.mark.asyncio
async def test_language_selection_saves_choice_and_confirms_in_new_language(monkeypatch):
    set_language_mock = MagicMock()
    monkeypatch.setattr(handlers_module, "set_language", set_language_mock)

    update = make_update_for_callback(user_id=222, lang="en", chat_id=555)
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    await handle_language_selection(update, context)

    update.callback_query.answer.assert_awaited_once()
    set_language_mock.assert_called_once_with(222, "en")
    context.bot.send_message.assert_awaited_once_with(
        chat_id=555, text=translate("language_set", "en")
    )


@pytest.mark.asyncio
async def test_language_selection_saves_before_confirming(monkeypatch):
    """set_language must be called before the confirmation is sent."""
    call_order = []

    def fake_set_language(user_id, lang):
        call_order.append("set_language")

    async def fake_send_message(**kwargs):
        call_order.append("send_message")

    monkeypatch.setattr(handlers_module, "set_language", fake_set_language)

    update = make_update_for_callback(user_id=333, lang="fa")
    context = MagicMock()
    context.bot.send_message = fake_send_message

    await handle_language_selection(update, context)

    assert call_order == ["set_language", "send_message"]
