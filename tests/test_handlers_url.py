"""Tests for bot/handlers.py's handle_url_message().

Mocks get_language and detect_platform (service/manager layer), same
style as the existing language-selection tests in test_handlers.py -
fast, isolated, no real detection or storage logic exercised here.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

import bot.handlers as handlers_module
from bot.handlers import handle_url_message
from downloader.manager import Platform
from services.translations import translate


def make_update_for_message(user_id: int, text: str) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_youtube_url_gets_youtube_reply_in_users_language(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "fa")
    monkeypatch.setattr(
        handlers_module, "detect_platform", lambda url: Platform.YOUTUBE
    )

    update = make_update_for_message(111, "https://youtube.com/watch?v=abc")
    context = MagicMock()

    await handle_url_message(update, context)

    update.message.reply_text.assert_awaited_once_with(
        translate("url.detected_youtube", "fa")
    )


@pytest.mark.asyncio
async def test_instagram_url_gets_instagram_reply(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    monkeypatch.setattr(
        handlers_module, "detect_platform", lambda url: Platform.INSTAGRAM
    )

    update = make_update_for_message(222, "https://instagram.com/p/abc")
    context = MagicMock()

    await handle_url_message(update, context)

    update.message.reply_text.assert_awaited_once_with(
        translate("url.detected_instagram", "en")
    )


@pytest.mark.asyncio
async def test_unrecognized_text_gets_unsupported_reply(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    monkeypatch.setattr(
        handlers_module, "detect_platform", lambda url: Platform.UNKNOWN
    )

    update = make_update_for_message(333, "hello there")
    context = MagicMock()

    await handle_url_message(update, context)

    update.message.reply_text.assert_awaited_once_with(
        translate("url.unsupported", "en")
    )


@pytest.mark.asyncio
async def test_detect_platform_is_called_with_the_message_text(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    detect_mock = MagicMock(return_value=Platform.UNKNOWN)
    monkeypatch.setattr(handlers_module, "detect_platform", detect_mock)

    update = make_update_for_message(444, "some raw text")
    context = MagicMock()

    await handle_url_message(update, context)

    detect_mock.assert_called_once_with("some raw text")
