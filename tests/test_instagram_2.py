"""Tests for downloader/instagram.py's download_instagram_video().

download_instagram_video() is tested against a fake yt_dlp.YoutubeDL -
no real network calls or real yt-dlp extraction happen here, per the
project's "no real network calls in the standard test suite" policy
(PROJECT_ROADMAP.md, Phase 0).

The module's `settings` reference is replaced with a SimpleNamespace
pointed at a tmp_path directory - the same pattern used in
tests/test_handlers_integration.py for services/language_service.py's
settings dependency (Settings is a frozen dataclass, so individual
fields can't be monkeypatched directly; the whole object reference the
module holds is swapped out instead).
"""

from __future__ import annotations

import os
import types

import pytest
import yt_dlp

import downloader.instagram as instagram_module
from downloader.instagram import InstagramDownloadError, download_instagram_video


class _FakeYoutubeDL:
    """Minimal stand-in for yt_dlp.YoutubeDL.

    Only implements the surface download_instagram_video() actually
    uses: use as a context manager, extract_info(), prepare_filename().
    Configured per-test via subclassing in _install_fake_ydl() rather
    than a full mocking framework, since the real interface exercised
    here is small.
    """

    #: Set on construction; read back in tests to assert on the options
    #: yt-dlp was configured with and how it was called.
    last_instance: "_FakeYoutubeDL | None" = None

    _info_result: dict = {}
    _prepare_filename_result = "/fake/path/video.mp4"
    _raises = None

    def __init__(self, opts):
        self.opts = opts
        self.extract_info_calls = []
        type(self).last_instance = self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def extract_info(self, url, download=True):
        self.extract_info_calls.append((url, download))
        if self._raises is not None:
            raise self._raises
        return self._info_result

    def prepare_filename(self, info):
        return self._prepare_filename_result


def _install_fake_ydl(monkeypatch, info_result=None, prepare_filename_result=None, raises=None):
    """Patch downloader.instagram.yt_dlp.YoutubeDL with a configured fake.

    Returns the fake class so tests can inspect
    FakeClass.last_instance.opts / .extract_info_calls after calling
    download_instagram_video().
    """

    class ConfiguredFakeYoutubeDL(_FakeYoutubeDL):
        _info_result = info_result if info_result is not None else {"id": "x"}
        _prepare_filename_result = prepare_filename_result or "/fake/path/video.mp4"
        _raises = raises

    monkeypatch.setattr(instagram_module.yt_dlp, "YoutubeDL", ConfiguredFakeYoutubeDL)
    return ConfiguredFakeYoutubeDL


@pytest.fixture
def download_dir(tmp_path):
    return str(tmp_path / "downloads")


@pytest.fixture(autouse=True)
def patched_settings(monkeypatch, download_dir):
    """Point downloader.instagram at test-local settings for every test."""
    monkeypatch.setattr(
        instagram_module,
        "settings",
        types.SimpleNamespace(download_dir=download_dir, ffmpeg_path="ffmpeg"),
    )


# ---------------------------------------------------------------------------
# Happy path / return value resolution
# ---------------------------------------------------------------------------


def test_returns_requested_downloads_filepath_when_present(monkeypatch):
    info = {
        "id": "abc123",
        "requested_downloads": [{"filepath": "/fake/merged/abc123.mp4"}],
    }
    _install_fake_ydl(monkeypatch, info_result=info)

    result = download_instagram_video("https://instagram.com/reel/abc123/")

    assert result == "/fake/merged/abc123.mp4"


def test_falls_back_to_prepare_filename_when_no_requested_downloads(monkeypatch):
    _install_fake_ydl(
        monkeypatch,
        info_result={"id": "abc123"},
        prepare_filename_result="/fake/path/abc123.mp4",
    )

    result = download_instagram_video("https://instagram.com/p/abc123/")

    assert result == "/fake/path/abc123.mp4"


def test_falls_back_to_prepare_filename_when_requested_downloads_empty(monkeypatch):
    _install_fake_ydl(
        monkeypatch,
        info_result={"id": "abc123", "requested_downloads": []},
        prepare_filename_result="/fake/path/abc123.mp4",
    )

    result = download_instagram_video("https://instagram.com/p/abc123/")

    assert result == "/fake/path/abc123.mp4"


def test_creates_download_dir_if_missing(download_dir, monkeypatch):
    assert not os.path.isdir(download_dir)
    _install_fake_ydl(monkeypatch)

    download_instagram_video("https://instagram.com/reel/x/")

    assert os.path.isdir(download_dir)


def test_explicit_download_dir_overrides_settings(monkeypatch, tmp_path):
    override_dir = str(tmp_path / "explicit_override")
    fake_cls = _install_fake_ydl(monkeypatch)

    download_instagram_video("https://instagram.com/reel/x/", download_dir=override_dir)

    assert os.path.isdir(override_dir)
    assert override_dir in fake_cls.last_instance.opts["outtmpl"]


# ---------------------------------------------------------------------------
# yt-dlp options: "best available quality, never intentionally reduced"
# ---------------------------------------------------------------------------


def test_uses_best_video_plus_best_audio_format(monkeypatch):
    fake_cls = _install_fake_ydl(monkeypatch)

    download_instagram_video("https://instagram.com/reel/x/")

    assert fake_cls.last_instance.opts["format"] == "bestvideo+bestaudio/best"


def test_merges_to_mp4(monkeypatch):
    fake_cls = _install_fake_ydl(monkeypatch)

    download_instagram_video("https://instagram.com/reel/x/")

    assert fake_cls.last_instance.opts["merge_output_format"] == "mp4"


def test_passes_configured_ffmpeg_path(monkeypatch, download_dir):
    monkeypatch.setattr(
        instagram_module,
        "settings",
        types.SimpleNamespace(download_dir=download_dir, ffmpeg_path="/custom/ffmpeg"),
    )
    fake_cls = _install_fake_ydl(monkeypatch)

    download_instagram_video("https://instagram.com/reel/x/")

    assert fake_cls.last_instance.opts["ffmpeg_location"] == "/custom/ffmpeg"


def test_disables_playlist_handling(monkeypatch):
    fake_cls = _install_fake_ydl(monkeypatch)

    download_instagram_video("https://instagram.com/reel/x/")

    assert fake_cls.last_instance.opts["noplaylist"] is True


def test_extract_info_called_with_download_true(monkeypatch):
    fake_cls = _install_fake_ydl(monkeypatch)

    url = "https://instagram.com/reel/x/"
    download_instagram_video(url)

    assert fake_cls.last_instance.extract_info_calls == [(url, True)]


def test_no_cookie_or_session_options_are_set(monkeypatch):
    """Anonymous-only in Phase 1 - no cookiefile/cookiesfrombrowser keys."""
    fake_cls = _install_fake_ydl(monkeypatch)

    download_instagram_video("https://instagram.com/reel/x/")

    opts = fake_cls.last_instance.opts
    assert "cookiefile" not in opts
    assert "cookiesfrombrowser" not in opts


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------


def test_yt_dlp_download_error_raises_instagram_download_error(monkeypatch):
    _install_fake_ydl(monkeypatch, raises=yt_dlp.utils.DownloadError("boom"))

    with pytest.raises(InstagramDownloadError):
        download_instagram_video("https://instagram.com/reel/x/")


def test_error_message_includes_the_failing_url(monkeypatch):
    _install_fake_ydl(monkeypatch, raises=yt_dlp.utils.DownloadError("boom"))

    url = "https://instagram.com/reel/private-post/"
    with pytest.raises(InstagramDownloadError, match="private-post"):
        download_instagram_video(url)


def test_instagram_download_error_chains_the_original_exception(monkeypatch):
    original = yt_dlp.utils.DownloadError("boom")
    _install_fake_ydl(monkeypatch, raises=original)

    with pytest.raises(InstagramDownloadError) as exc_info:
        download_instagram_video("https://instagram.com/reel/x/")

    assert exc_info.value.__cause__ is original


def test_instagram_download_error_is_its_own_exception_type():
    assert issubclass(InstagramDownloadError, Exception)
    assert not issubclass(InstagramDownloadError, yt_dlp.utils.DownloadError)
