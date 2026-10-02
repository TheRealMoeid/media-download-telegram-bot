"""Tests for bot/handlers.py's Instagram download + delivery flow.

Two styles, matching the rest of the suite:
  - the download->send->cleanup path runs the REAL deliver_video() and
    file_service against tmp_path, with only yt-dlp (the downloader
    function) and Telegram (context.bot.send_video) faked;
  - failure-message mapping mocks deliver_video() to return each outcome.
"""

from __future__ import annotations

import os
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

import bot.handlers as handlers_module
import services.file_service as file_service_module
from bot.handlers import handle_url_message
from downloader.manager import Platform
from services.translations import translate
from services.video_service import DeliveryOutcome

URL = "https://www.instagram.com/reel/abc123/"


def make_update(user_id: int = 111, text: str = URL, chat_id: int = 555) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.text = text
    update.message.chat_id = chat_id
    update.message.reply_text = AsyncMock()
    return update


def make_context() -> MagicMock:
    context = MagicMock()
    context.user_data = {}
    context.bot.send_video = AsyncMock()
    return context


@pytest.fixture(autouse=True)
def common_patches(monkeypatch, tmp_path):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "en")
    monkeypatch.setattr(
        handlers_module, "detect_platform", lambda url: Platform.INSTAGRAM
    )
    monkeypatch.setattr(
        file_service_module,
        "settings",
        types.SimpleNamespace(download_dir=str(tmp_path)),
    )
    return tmp_path


@pytest.mark.asyncio
async def test_success_sends_video_and_leaves_no_files_behind(monkeypatch, tmp_path):
    captured = {}

    def fake_download(url, download_dir):
        captured["url"] = url
        captured["dir"] = download_dir
        path = os.path.join(download_dir, "abc123.mp4")
        with open(path, "wb") as f:
            f.write(b"fake-video-bytes")
        return path

    monkeypatch.setattr(handlers_module, "download_instagram_video", fake_download)

    async def fake_send_video(**kwargs):
        # Read while the file is still expected to exist and be open.
        captured["sent_bytes"] = kwargs["video"].read()
        captured["kwargs"] = kwargs

    update, context = make_update(), make_context()
    context.bot.send_video = fake_send_video

    await handle_url_message(update, context)

    assert captured["url"] == URL
    assert os.path.dirname(captured["dir"]) == str(tmp_path)
    assert captured["sent_bytes"] == b"fake-video-bytes"
    assert captured["kwargs"]["chat_id"] == 555
    assert captured["kwargs"]["supports_streaming"] is True
    assert captured["kwargs"]["write_timeout"] == 300
    assert captured["kwargs"]["read_timeout"] == 60
    assert captured["kwargs"]["connect_timeout"] == 30

    # Only the "downloading" notice - no success text, no error text.
    update.message.reply_text.assert_awaited_once_with(
        translate("instagram.downloading", "en")
    )
    # Request directory was removed.
    assert os.listdir(tmp_path) == []


@pytest.mark.asyncio
async def test_download_failure_replies_with_translated_error_and_cleans_up(
    monkeypatch, tmp_path
):
    def failing_download(url, download_dir):
        with open(os.path.join(download_dir, "x.mp4.part"), "wb"):
            pass
        raise RuntimeError("boom")

    monkeypatch.setattr(handlers_module, "download_instagram_video", failing_download)

    update, context = make_update(), make_context()

    await handle_url_message(update, context)

    context.bot.send_video.assert_not_awaited()
    assert update.message.reply_text.await_args_list[-1].args[0] == translate(
        "instagram.download_failed", "en"
    )
    assert os.listdir(tmp_path) == []


@pytest.mark.asyncio
async def test_send_failure_replies_with_translated_error_and_cleans_up(
    monkeypatch, tmp_path
):
    def fake_download(url, download_dir):
        path = os.path.join(download_dir, "abc123.mp4")
        with open(path, "wb"):
            pass
        return path

    monkeypatch.setattr(handlers_module, "download_instagram_video", fake_download)

    update, context = make_update(), make_context()
    context.bot.send_video = AsyncMock(side_effect=RuntimeError("too large"))

    await handle_url_message(update, context)

    assert update.message.reply_text.await_args_list[-1].args[0] == translate(
        "delivery.send_failed", "en"
    )
    assert os.listdir(tmp_path) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "outcome, key",
    [
        (DeliveryOutcome.DOWNLOAD_FAILED, "instagram.download_failed"),
        (DeliveryOutcome.SEND_FAILED, "delivery.send_failed"),
    ],
)
async def test_each_failed_outcome_maps_to_its_own_message(monkeypatch, outcome, key):
    monkeypatch.setattr(
        handlers_module, "deliver_video", AsyncMock(return_value=outcome)
    )
    update, context = make_update(), make_context()

    await handle_url_message(update, context)

    assert update.message.reply_text.await_count == 2
    assert update.message.reply_text.await_args_list[-1].args[0] == translate(
        key, "en"
    )


@pytest.mark.asyncio
async def test_sent_outcome_sends_no_extra_message(monkeypatch):
    monkeypatch.setattr(
        handlers_module,
        "deliver_video",
        AsyncMock(return_value=DeliveryOutcome.SENT),
    )
    update, context = make_update(), make_context()

    await handle_url_message(update, context)

    update.message.reply_text.assert_awaited_once_with(
        translate("instagram.downloading", "en")
    )


@pytest.mark.asyncio
async def test_messages_use_the_users_saved_language(monkeypatch):
    monkeypatch.setattr(handlers_module, "get_language", lambda user_id: "fa")
    monkeypatch.setattr(
        handlers_module,
        "deliver_video",
        AsyncMock(return_value=DeliveryOutcome.DOWNLOAD_FAILED),
    )
    update, context = make_update(), make_context()

    await handle_url_message(update, context)

    assert update.message.reply_text.await_args_list[0].args[0] == translate(
        "instagram.downloading", "fa"
    )
    assert update.message.reply_text.await_args_list[1].args[0] == translate(
        "instagram.download_failed", "fa"
    )
