"""Tests for services/video_service.py.

Uses the real file_service against pytest's tmp_path (no mocking of
directory handling), with fake download/send callables.
"""

import os
import threading
import types

import pytest

import services.file_service as file_service_module
from services.video_service import DeliveryOutcome, deliver_video


@pytest.fixture(autouse=True)
def base_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        file_service_module,
        "settings",
        types.SimpleNamespace(download_dir=str(tmp_path)),
    )
    return tmp_path


def make_download_fn(record=None):
    def download_fn(request_dir):
        if record is not None:
            record["dir"] = request_dir
            record["thread"] = threading.get_ident()
        path = os.path.join(request_dir, "video.mp4")
        with open(path, "wb") as f:
            f.write(b"data")
        return path

    return download_fn


def remaining_dirs(base):
    return [p for p in os.listdir(base)]


@pytest.mark.asyncio
async def test_success_returns_sent_and_send_receives_downloaded_path(base_dir):
    sent = {}

    async def send_fn(path):
        sent["path"] = path
        sent["existed"] = os.path.exists(path)

    outcome = await deliver_video(make_download_fn(), send_fn)

    assert outcome is DeliveryOutcome.SENT
    assert sent["path"].endswith("video.mp4")
    assert sent["existed"] is True


@pytest.mark.asyncio
async def test_download_fn_gets_a_fresh_dir_inside_base_dir(base_dir):
    record = {}

    async def send_fn(path):
        pass

    await deliver_video(make_download_fn(record), send_fn)

    assert os.path.dirname(record["dir"]) == str(base_dir)


@pytest.mark.asyncio
async def test_download_runs_in_a_worker_thread_not_the_event_loop_thread():
    record = {}

    async def send_fn(path):
        pass

    await deliver_video(make_download_fn(record), send_fn)

    assert record["thread"] != threading.get_ident()


@pytest.mark.asyncio
async def test_directory_is_cleaned_up_after_success(base_dir):
    async def send_fn(path):
        pass

    await deliver_video(make_download_fn(), send_fn)

    assert remaining_dirs(base_dir) == []


@pytest.mark.asyncio
async def test_download_failure_returns_download_failed_and_skips_send(base_dir):
    send_calls = []

    def failing_download(request_dir):
        with open(os.path.join(request_dir, "video.mp4.part"), "wb"):
            pass
        raise RuntimeError("boom")

    async def send_fn(path):
        send_calls.append(path)

    outcome = await deliver_video(failing_download, send_fn)

    assert outcome is DeliveryOutcome.DOWNLOAD_FAILED
    assert send_calls == []
    assert remaining_dirs(base_dir) == []  # leftover .part removed too


@pytest.mark.asyncio
async def test_send_failure_returns_send_failed_and_still_cleans_up(base_dir):
    async def failing_send(path):
        raise RuntimeError("upload failed")

    outcome = await deliver_video(make_download_fn(), failing_send)

    assert outcome is DeliveryOutcome.SEND_FAILED
    assert remaining_dirs(base_dir) == []


@pytest.mark.asyncio
async def test_each_call_uses_its_own_directory():
    dirs = []

    def download_fn(request_dir):
        dirs.append(request_dir)
        return make_download_fn()(request_dir)

    async def send_fn(path):
        pass

    await deliver_video(download_fn, send_fn)
    await deliver_video(download_fn, send_fn)

    assert dirs[0] != dirs[1]


@pytest.mark.asyncio
async def test_failure_to_create_request_dir_is_reported_as_download_failed(
    monkeypatch,
):
    import services.video_service as vs

    def broken_create():
        raise OSError("disk full")

    monkeypatch.setattr(vs, "create_request_dir", broken_create)

    async def send_fn(path):
        raise AssertionError("send must not be called")

    outcome = await deliver_video(make_download_fn(), send_fn)

    assert outcome is DeliveryOutcome.DOWNLOAD_FAILED


# ---------------------------------------------------------------------------
# KEEP_DOWNLOADS
# ---------------------------------------------------------------------------


@pytest.fixture
def keep_downloads(monkeypatch):
    import services.video_service as vs

    monkeypatch.setattr(vs, "settings", types.SimpleNamespace(keep_downloads=True))


@pytest.mark.asyncio
async def test_keep_downloads_keeps_the_file_after_success(base_dir, keep_downloads):
    async def send_fn(path):
        pass

    outcome = await deliver_video(make_download_fn(), send_fn)

    assert outcome is DeliveryOutcome.SENT
    kept = remaining_dirs(base_dir)
    assert len(kept) == 1
    assert os.path.exists(os.path.join(base_dir, kept[0], "video.mp4"))


@pytest.mark.asyncio
async def test_keep_downloads_also_keeps_the_file_when_sending_fails(
    base_dir, keep_downloads
):
    async def failing_send(path):
        raise RuntimeError("too large")

    outcome = await deliver_video(make_download_fn(), failing_send)

    assert outcome is DeliveryOutcome.SEND_FAILED
    kept = remaining_dirs(base_dir)
    assert len(kept) == 1
    assert os.path.exists(os.path.join(base_dir, kept[0], "video.mp4"))


@pytest.mark.asyncio
async def test_keep_downloads_still_cleans_up_a_failed_download(
    base_dir, keep_downloads
):
    def failing_download(request_dir):
        with open(os.path.join(request_dir, "video.mp4.part"), "wb"):
            pass
        raise RuntimeError("boom")

    async def send_fn(path):
        pass

    outcome = await deliver_video(failing_download, send_fn)

    assert outcome is DeliveryOutcome.DOWNLOAD_FAILED
    assert remaining_dirs(base_dir) == []
