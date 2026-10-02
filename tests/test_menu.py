"""Tests for the main menu -> Settings -> Language flow.

Keyboard-layout tests are pure. Handler tests mock get_language (same
style as test_handlers.py). The last two tests are the real-integration
tier: real language_service against a tmp SQLite file, no storage mocks.
"""

import types
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, CommandHandler

import bot.handlers as handlers_module
import services.language_service as language_service_module
from bot.handlers import (
    handle_language_selection,
    handle_menu_navigation,
    menu,
    register_handlers,
)
from bot.keyboards import (
    language_selection_keyboard,
    main_menu_keyboard,
    settings_keyboard,
)
from services.language_service import get_language
from services.translations import translate


def rows(markup):
    return [[(b.text, b.callback_data) for b in row] for row in markup.inline_keyboard]


def make_menu_update(user_id=111):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    return update


def make_nav_update(action, user_id=111, chat_id=999):
    update = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.from_user.id = user_id
    update.callback_query.data = f"menu:{action}"
    update.callback_query.message.chat_id = chat_id
    return update


def make_lang_update(user_id, lang, chat_id=999):
    update = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.from_user.id = user_id
    update.callback_query.data = f"set_lang:{lang}"
    update.callback_query.message.chat_id = chat_id
    return update


# --- keyboards ---------------------------------------------------------


@pytest.mark.parametrize("lang", ["en", "fa"])
def test_main_menu_has_single_settings_button(lang):
    assert rows(main_menu_keyboard(lang)) == [
        [(translate("menu.settings_button", lang), "menu:settings")]
    ]


@pytest.mark.parametrize("lang", ["en", "fa"])
def test_settings_keyboard_has_language_then_back(lang):
    assert rows(settings_keyboard(lang)) == [
        [(translate("menu.language_button", lang), "menu:language")],
        [(translate("menu.back_button", lang), "menu:back")],
    ]


def test_plain_language_keyboard_is_unchanged_for_start():
    assert rows(language_selection_keyboard()) == [
        [
            ("\U0001F1EE\U0001F1F7 \u0641\u0627\u0631\u0633\u06CC", "set_lang:fa"),
            ("\U0001F1FA\U0001F1F8 English", "set_lang:en"),
        ]
    ]


def test_language_keyboard_with_back_adds_a_back_row_to_settings():
    r = rows(language_selection_keyboard(back_label="Back"))
    assert len(r) == 2
    assert [cb for _, cb in r[0]] == ["set_lang:fa", "set_lang:en"]
    assert r[1] == [("Back", "menu:settings")]


# --- /menu -------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("lang", ["en", "fa"])
async def test_menu_command_shows_main_menu_in_saved_language(monkeypatch, lang):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: lang)
    update = make_menu_update()

    await menu(update, MagicMock())

    update.message.reply_text.assert_awaited_once()
    call = update.message.reply_text.await_args
    assert call.args[0] == translate("menu.title", lang)
    assert rows(call.kwargs["reply_markup"]) == rows(main_menu_keyboard(lang))


# --- navigation --------------------------------------------------------


@pytest.mark.asyncio
async def test_settings_action_edits_message_to_settings_screen(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    update = make_nav_update("settings")

    await handle_menu_navigation(update, MagicMock())

    update.callback_query.answer.assert_awaited_once()
    call = update.callback_query.edit_message_text.await_args
    assert call.args[0] == translate("menu.settings_title", "en")
    assert rows(call.kwargs["reply_markup"]) == rows(settings_keyboard("en"))


@pytest.mark.asyncio
async def test_language_action_shows_picker_with_back_in_users_language(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "fa")
    update = make_nav_update("language")

    await handle_menu_navigation(update, MagicMock())

    call = update.callback_query.edit_message_text.await_args
    assert call.args[0] == translate("choose_language", "fa")
    r = rows(call.kwargs["reply_markup"])
    assert [cb for _, cb in r[0]] == ["set_lang:fa", "set_lang:en"]
    assert r[1] == [(translate("menu.back_button", "fa"), "menu:settings")]


@pytest.mark.asyncio
async def test_back_action_returns_to_main_menu(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    update = make_nav_update("back")

    await handle_menu_navigation(update, MagicMock())

    call = update.callback_query.edit_message_text.await_args
    assert call.args[0] == translate("menu.title", "en")
    assert rows(call.kwargs["reply_markup"]) == rows(main_menu_keyboard("en"))


@pytest.mark.asyncio
async def test_unknown_action_is_ignored_without_editing(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    update = make_nav_update("bogus")

    await handle_menu_navigation(update, MagicMock())

    update.callback_query.answer.assert_awaited_once()
    update.callback_query.edit_message_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_not_modified_error_on_repeat_tap_is_swallowed(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    update = make_nav_update("settings")
    update.callback_query.edit_message_text = AsyncMock(
        side_effect=BadRequest("Message is not modified")
    )

    await handle_menu_navigation(update, MagicMock())  # must not raise


@pytest.mark.asyncio
async def test_navigation_never_saves_a_language(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    set_mock = MagicMock()
    monkeypatch.setattr(handlers_module, "set_language", set_mock)

    for action in ("settings", "language", "back"):
        await handle_menu_navigation(make_nav_update(action), MagicMock())

    set_mock.assert_not_called()


# --- registration ------------------------------------------------------


def test_register_handlers_adds_menu_command_and_distinct_menu_prefix():
    app = MagicMock()
    register_handlers(app)
    handlers = [c.args[0] for c in app.add_handler.call_args_list]

    commands = [h for h in handlers if isinstance(h, CommandHandler)]
    assert any("menu" in h.commands for h in commands)
    assert any("start" in h.commands for h in commands)

    patterns = [h.pattern for h in handlers if isinstance(h, CallbackQueryHandler)]

    def matchers(data):
        return [p for p in patterns if p.match(data)]

    for data in ("menu:settings", "menu:language", "menu:back"):
        assert len(matchers(data)) == 1
    assert len(matchers("set_lang:fa")) == 1
    assert len(matchers("yt_quality:tok:0")) == 1
    assert not matchers("menu:settings")[0].match("set_lang:fa")


# --- real-integration tier (real language_service, tmp SQLite) ---------


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "menu_integration.db")
    monkeypatch.setattr(
        language_service_module, "settings", types.SimpleNamespace(db_path=db_path)
    )
    return db_path


@pytest.mark.asyncio
async def test_full_flow_changes_language_via_menu_and_menu_follows(tmp_db):
    user_id = 424242
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    # Existing English user opens /menu -> Settings -> Language.
    language_service_module.set_language(user_id, "en")
    first = make_menu_update(user_id)
    await menu(first, context)
    assert first.message.reply_text.await_args.args[0] == translate("menu.title", "en")

    await handle_menu_navigation(make_nav_update("settings", user_id), context)
    lang_screen = make_nav_update("language", user_id)
    await handle_menu_navigation(lang_screen, context)
    assert lang_screen.callback_query.edit_message_text.await_args.args[0] == translate(
        "choose_language", "en"
    )

    # Taps فارسی: the existing set_lang: handler saves and confirms.
    await handle_language_selection(make_lang_update(user_id, "fa", chat_id=7), context)
    assert get_language(user_id) == "fa"
    context.bot.send_message.assert_awaited_once_with(
        chat_id=7, text=translate("language_set", "fa")
    )

    # Next /menu is now in Persian.
    second = make_menu_update(user_id)
    await menu(second, context)
    assert second.message.reply_text.await_args.args[0] == translate("menu.title", "fa")


@pytest.mark.asyncio
async def test_menu_language_change_is_independent_per_user(tmp_db):
    context = MagicMock()
    context.bot.send_message = AsyncMock()
    language_service_module.set_language(1, "en")
    language_service_module.set_language(2, "en")

    await handle_language_selection(make_lang_update(1, "fa"), context)

    assert get_language(1) == "fa"
    assert get_language(2) == "en"
