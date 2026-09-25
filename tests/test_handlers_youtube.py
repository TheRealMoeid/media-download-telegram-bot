"""Tests for bot/handlers.py's YouTube quality-selection flow.

Mocks the downloader layer (get_available_qualities, download_youtube_video)
and get_language, same style as test_handlers.py / test_handlers_url.py -
fast, isolated, no real yt-dlp or storage. context.user_data is a real
plain dict on the MagicMock context (python-telegram-bot's own
ContextTypes.DEFAULT_TYPE.user_data is just a dict-like object), so the
pending-selection logic itself is exercised for real, not mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

import bot.handlers as handlers_module
from bot.handlers import (
    _PENDING_YOUTUBE_KEY,
    handle_url_message,
    handle_youtube_quality_selection,
)
from downloader.manager import Platform
from downloader.youtube import (
    QualityOption,
    YouTubeDownloadError,
    YouTubeExtractionError,
)
from services.translations import translate


def make_context() -> MagicMock:
    context = MagicMock()
    context.user_data = {}
    context.bot.send_message = AsyncMock()
    return context


def make_update_for_message(user_id: int, text: str) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def make_update_for_quality_callback(
    user_id: int, callback_data: str, chat_id: int = 999
) -> MagicMock:
    update = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.from_user.id = user_id
    update.callback_query.data = callback_data
    update.callback_query.message.chat_id = chat_id
    return update


# ---------------------------------------------------------------------------
# Single-quality auto-download path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_quality_auto_downloads_and_notifies(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    monkeypatch.setattr(handlers_module, "detect_platform", lambda url: Platform.YOUTUBE)
    only_option = QualityOption(format_id="22", label="720p", height=720)
    monkeypatch.setattr(
        handlers_module, "get_available_qualities", lambda url: [only_option]
    )
    download_mock = MagicMock(return_value="/tmp/video.mp4")
    monkeypatch.setattr(handlers_module, "download_youtube_video", download_mock)

    update = make_update_for_message(111, "https://youtube.com/watch?v=abc")
    context = make_context()

    await handle_url_message(update, context)

    download_mock.assert_called_once_with(
        "https://youtube.com/watch?v=abc", only_option
    )
    assert update.message.reply_text.await_count == 2
    assert update.message.reply_text.await_args_list[0].args[0] == translate(
        "youtube.single_quality_auto", "en", quality="720p"
    )
    assert update.message.reply_text.await_args_list[1].args[0] == translate(
        "youtube.download_complete", "en", quality="720p"
    )
    # No menu is left pending after an auto-download.
    assert _PENDING_YOUTUBE_KEY not in context.user_data


@pytest.mark.asyncio
async def test_single_quality_download_failure_reports_error(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    monkeypatch.setattr(handlers_module, "detect_platform", lambda url: Platform.YOUTUBE)
    only_option = QualityOption(format_id="22", label="720p", height=720)
    monkeypatch.setattr(
        handlers_module, "get_available_qualities", lambda url: [only_option]
    )

    def raise_download_error(url, format_id):
        raise YouTubeDownloadError("boom")

    monkeypatch.setattr(
        handlers_module, "download_youtube_video", raise_download_error
    )

    update = make_update_for_message(111, "https://youtube.com/watch?v=abc")
    context = make_context()

    await handle_url_message(update, context)

    assert update.message.reply_text.await_args_list[-1].args[0] == translate(
        "youtube.download_failed", "en"
    )


# ---------------------------------------------------------------------------
# Extraction failure / no usable formats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extraction_failure_replies_with_translated_error(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "fa")
    monkeypatch.setattr(handlers_module, "detect_platform", lambda url: Platform.YOUTUBE)

    def raise_extraction_error(url):
        raise YouTubeExtractionError("boom")

    monkeypatch.setattr(
        handlers_module, "get_available_qualities", raise_extraction_error
    )

    update = make_update_for_message(111, "https://youtube.com/watch?v=abc")
    context = make_context()

    await handle_url_message(update, context)

    update.message.reply_text.assert_awaited_once_with(
        translate("youtube.extraction_failed", "fa")
    )
    assert _PENDING_YOUTUBE_KEY not in context.user_data


@pytest.mark.asyncio
async def test_no_usable_formats_replies_with_translated_error(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    monkeypatch.setattr(handlers_module, "detect_platform", lambda url: Platform.YOUTUBE)
    monkeypatch.setattr(handlers_module, "get_available_qualities", lambda url: [])

    update = make_update_for_message(111, "https://youtube.com/watch?v=abc")
    context = make_context()

    await handle_url_message(update, context)

    update.message.reply_text.assert_awaited_once_with(
        translate("youtube.extraction_failed", "en")
    )


# ---------------------------------------------------------------------------
# Multi-quality menu
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_quality_shows_menu_and_stores_pending_selection(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    monkeypatch.setattr(handlers_module, "detect_platform", lambda url: Platform.YOUTUBE)
    options = [
        QualityOption(format_id="137+bestaudio/best", label="1080p", height=1080),
        QualityOption(format_id="22", label="720p", height=720),
    ]
    monkeypatch.setattr(handlers_module, "get_available_qualities", lambda url: options)

    update = make_update_for_message(111, "https://youtube.com/watch?v=abc")
    context = make_context()

    await handle_url_message(update, context)

    update.message.reply_text.assert_awaited_once()
    call = update.message.reply_text.await_args
    assert call.args[0] == translate("youtube.choose_quality", "en")
    assert "reply_markup" in call.kwargs

    pending = context.user_data[_PENDING_YOUTUBE_KEY]
    assert pending["url"] == "https://youtube.com/watch?v=abc"
    assert pending["options"] == options
    assert isinstance(pending["token"], str) and pending["token"]


@pytest.mark.asyncio
async def test_a_new_youtube_url_invalidates_a_previous_pending_menu(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    monkeypatch.setattr(handlers_module, "detect_platform", lambda url: Platform.YOUTUBE)
    options = [
        QualityOption(format_id="137", label="1080p", height=1080),
        QualityOption(format_id="22", label="720p", height=720),
    ]
    monkeypatch.setattr(handlers_module, "get_available_qualities", lambda url: options)

    context = make_context()

    first_update = make_update_for_message(111, "https://youtube.com/watch?v=first")
    await handle_url_message(first_update, context)
    old_token = context.user_data[_PENDING_YOUTUBE_KEY]["token"]

    second_update = make_update_for_message(111, "https://youtube.com/watch?v=second")
    await handle_url_message(second_update, context)
    new_token = context.user_data[_PENDING_YOUTUBE_KEY]["token"]

    assert old_token != new_token
    assert context.user_data[_PENDING_YOUTUBE_KEY]["url"] == (
        "https://youtube.com/watch?v=second"
    )


# ---------------------------------------------------------------------------
# Quality-selection callback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_selection_downloads_the_tapped_quality(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    options = [
        QualityOption(format_id="137+bestaudio/best", label="1080p", height=1080),
        QualityOption(format_id="22", label="720p", height=720),
    ]
    download_mock = MagicMock(return_value="/tmp/video.mp4")
    monkeypatch.setattr(handlers_module, "download_youtube_video", download_mock)

    context = make_context()
    context.user_data[_PENDING_YOUTUBE_KEY] = {
        "token": "tok123",
        "url": "https://youtube.com/watch?v=abc",
        "options": options,
    }

    update = make_update_for_quality_callback(111, "yt_quality:tok123:0", chat_id=777)

    await handle_youtube_quality_selection(update, context)

    update.callback_query.answer.assert_awaited_once()
    download_mock.assert_called_once_with(
        "https://youtube.com/watch?v=abc", options[0]
    )
    assert context.bot.send_message.await_args_list[0].kwargs == {
        "chat_id": 777,
        "text": translate("youtube.download_started", "en", quality="1080p"),
    }
    assert context.bot.send_message.await_args_list[1].kwargs == {
        "chat_id": 777,
        "text": translate("youtube.download_complete", "en", quality="1080p"),
    }
    # Pending selection is consumed.
    assert _PENDING_YOUTUBE_KEY not in context.user_data


@pytest.mark.asyncio
async def test_selection_download_failure_reports_error(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    options = [QualityOption(format_id="22", label="720p", height=720)]

    def raise_download_error(url, format_id):
        raise YouTubeDownloadError("boom")

    monkeypatch.setattr(
        handlers_module, "download_youtube_video", raise_download_error
    )

    context = make_context()
    context.user_data[_PENDING_YOUTUBE_KEY] = {
        "token": "tok123",
        "url": "https://youtube.com/watch?v=abc",
        "options": options,
    }
    update = make_update_for_quality_callback(111, "yt_quality:tok123:0")

    await handle_youtube_quality_selection(update, context)

    last_call = context.bot.send_message.await_args_list[-1]
    assert last_call.kwargs["text"] == translate("youtube.download_failed", "en")


@pytest.mark.asyncio
async def test_mismatched_token_replies_expired_and_does_not_download(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    download_mock = MagicMock()
    monkeypatch.setattr(handlers_module, "download_youtube_video", download_mock)

    context = make_context()
    context.user_data[_PENDING_YOUTUBE_KEY] = {
        "token": "current-token",
        "url": "https://youtube.com/watch?v=abc",
        "options": [QualityOption(format_id="22", label="720p", height=720)],
    }
    # Callback carries a stale token from an earlier, superseded menu.
    update = make_update_for_quality_callback(111, "yt_quality:stale-token:0", chat_id=42)

    await handle_youtube_quality_selection(update, context)

    download_mock.assert_not_called()
    context.bot.send_message.assert_awaited_once_with(
        chat_id=42, text=translate("youtube.selection_expired", "en")
    )
    # The still-current pending selection must be left untouched.
    assert context.user_data[_PENDING_YOUTUBE_KEY]["token"] == "current-token"


@pytest.mark.asyncio
async def test_double_tap_only_downloads_once(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    options = [QualityOption(format_id="22", label="720p", height=720)]
    download_mock = MagicMock(return_value="/tmp/video.mp4")
    monkeypatch.setattr(handlers_module, "download_youtube_video", download_mock)

    context = make_context()
    context.user_data[_PENDING_YOUTUBE_KEY] = {
        "token": "tok123",
        "url": "https://youtube.com/watch?v=abc",
        "options": options,
    }

    first_tap = make_update_for_quality_callback(111, "yt_quality:tok123:0")
    await handle_youtube_quality_selection(first_tap, context)

    second_tap = make_update_for_quality_callback(111, "yt_quality:tok123:0")
    await handle_youtube_quality_selection(second_tap, context)

    download_mock.assert_called_once()
    assert context.bot.send_message.await_args_list[-1].kwargs["text"] == translate(
        "youtube.selection_expired", "en"
    )


@pytest.mark.asyncio
async def test_missing_pending_selection_replies_expired_without_crashing(monkeypatch):
    """Simulates a bot restart: user_data has nothing pending at all."""
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    download_mock = MagicMock()
    monkeypatch.setattr(handlers_module, "download_youtube_video", download_mock)

    context = make_context()  # empty user_data - nothing pending
    update = make_update_for_quality_callback(111, "yt_quality:some-token:0", chat_id=5)

    await handle_youtube_quality_selection(update, context)

    download_mock.assert_not_called()
    context.bot.send_message.assert_awaited_once_with(
        chat_id=5, text=translate("youtube.selection_expired", "en")
    )


@pytest.mark.asyncio
async def test_out_of_range_index_replies_expired_and_clears_pending(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    download_mock = MagicMock()
    monkeypatch.setattr(handlers_module, "download_youtube_video", download_mock)

    context = make_context()
    context.user_data[_PENDING_YOUTUBE_KEY] = {
        "token": "tok123",
        "url": "https://youtube.com/watch?v=abc",
        "options": [QualityOption(format_id="22", label="720p", height=720)],
    }
    # Index 5 doesn't exist in a one-item options list.
    update = make_update_for_quality_callback(111, "yt_quality:tok123:5")

    await handle_youtube_quality_selection(update, context)

    download_mock.assert_not_called()
    assert context.bot.send_message.await_args_list[-1].kwargs["text"] == translate(
        "youtube.selection_expired", "en"
    )
    assert _PENDING_YOUTUBE_KEY not in context.user_data


@pytest.mark.asyncio
async def test_selection_is_scoped_per_user_via_user_data(monkeypatch):
    """context.user_data is already per-user in python-telegram-bot, so
    this mainly documents/locks in that the handler relies on that
    scoping rather than a global dict keyed by user id itself."""
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    options = [QualityOption(format_id="22", label="720p", height=720)]
    download_mock = MagicMock(return_value="/tmp/video.mp4")
    monkeypatch.setattr(handlers_module, "download_youtube_video", download_mock)

    context_a = make_context()
    context_a.user_data[_PENDING_YOUTUBE_KEY] = {
        "token": "tok-a",
        "url": "https://youtube.com/watch?v=a",
        "options": options,
    }
    context_b = make_context()  # a different user's context/user_data

    update_b = make_update_for_quality_callback(222, "yt_quality:tok-a:0")
    await handle_youtube_quality_selection(update_b, context_b)

    download_mock.assert_not_called()
    context_b.bot.send_message.assert_awaited_once_with(
        chat_id=999, text=translate("youtube.selection_expired", "en")
    )
