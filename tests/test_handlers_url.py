"""Tests for bot/handlers.py's handle_url_message() - unsupported-link path.

Mocks get_language and detect_platform (service/manager layer), same
style as the existing language-selection tests in test_handlers.py -
fast, isolated, no real detection or storage logic exercised here.

YouTube URLs trigger the quality-selection flow (see
tests/test_handlers_youtube.py); Instagram URLs trigger download +
delivery (see tests/test_handlers_instagram.py).
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
