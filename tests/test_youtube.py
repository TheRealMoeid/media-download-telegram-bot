"""Tests for downloader/youtube.py.

All tests fake yt_dlp.YoutubeDL entirely - no real network calls, no
real yt-dlp extraction, matching the pattern already established for
downloader/instagram.py (see CLAUDE.md, Step 6 / tests/test_instagram.py).
Real-world correctness belongs to a throwaway manual script run once
against a live URL, never the pytest suite.

FakeYoutubeDL.script is a FIFO queue of outcomes (a dict = a successful
`info` result, an Exception instance = what extract_info() raises),
consumed one per extract_info() call. This lets a single test express
"the first attempt is blocked, the second succeeds" the same way the
real fallback loop in downloader/youtube.py experiences it: one
YoutubeDL instance per client attempt.
"""

from __future__ import annotations

import os

import pytest
import yt_dlp

import downloader.youtube as youtube_module
from downloader.youtube import (
    QualityOption,
    YouTubeDownloadError,
    YouTubeExtractionError,
    download_youtube_video,
    get_available_qualities,
)


# ---------------------------------------------------------------------------
# Fake yt_dlp.YoutubeDL
# ---------------------------------------------------------------------------


class FakeYoutubeDL:
    """A minimal stand-in for yt_dlp.YoutubeDL.

    `script` is consumed FIFO, one entry per extract_info() call across
    every instance created during a test - mirroring how the real
    fallback loop constructs a fresh YoutubeDL per client attempt.
    """

    script: list = []
    instances: list["FakeYoutubeDL"] = []

    def __init__(self, opts):
        self.opts = opts
        self.extract_info_calls: list[tuple[str, bool]] = []
        FakeYoutubeDL.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def extract_info(self, url, download=False):
        self.extract_info_calls.append((url, download))

        outcome = FakeYoutubeDL.script.pop(0)
        if isinstance(outcome, Exception):
            raise outcome

        info = dict(outcome)

        if download:
            outtmpl = self.opts.get("outtmpl", "%(id)s.%(ext)s")
            video_id = info.get("id", "video")
            ext = info.get("ext", "mp4")
            filepath = outtmpl % {"id": video_id, "ext": ext}
            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
            with open(filepath, "wb"):
                pass
            info.setdefault("_resolved_filepath", filepath)

        return info

    def prepare_filename(self, info):
        return info["_resolved_filepath"]


@pytest.fixture(autouse=True)
def fake_yt_dlp(monkeypatch):
    """Point downloader.youtube's yt_dlp.YoutubeDL at the fake class."""
    FakeYoutubeDL.script = []
    FakeYoutubeDL.instances = []
    monkeypatch.setattr(youtube_module.yt_dlp, "YoutubeDL", FakeYoutubeDL)
    yield
    FakeYoutubeDL.script = []
    FakeYoutubeDL.instances = []


def make_format(
    format_id, height, vcodec="avc1", acodec="mp4a", tbr=None, filesize=None
):
    return {
        "format_id": format_id,
        "height": height,
        "vcodec": vcodec,
        "acodec": acodec,
        "tbr": tbr,
        "filesize": filesize,
    }


def bot_check_error(message="Sign in to confirm you're not a bot"):
    return yt_dlp.utils.DownloadError(message)


URL = "https://youtube.com/watch?v=abc"


# ---------------------------------------------------------------------------
# get_available_qualities() - dedup/normalization logic (single attempt)
# ---------------------------------------------------------------------------


def test_returns_one_option_per_distinct_height_sorted_descending():
    FakeYoutubeDL.script = [
        {
            "formats": [
                make_format("136", 720, tbr=1500),
                make_format("137", 1080, tbr=4000),
                make_format("160", 144, tbr=100),
            ]
        }
    ]

    options = get_available_qualities(URL)

    assert [o.height for o in options] == [1080, 720, 144]
    assert [o.label for o in options] == ["1080p", "720p", "144p"]


def test_audio_only_formats_are_never_surfaced_as_qualities():
    FakeYoutubeDL.script = [
        {
            "formats": [
                make_format("140", None, vcodec="none", acodec="mp4a"),
                make_format("137", 1080, tbr=4000),
            ]
        }
    ]

    options = get_available_qualities(URL)

    assert [o.height for o in options] == [1080]


def test_formats_missing_height_are_ignored():
    FakeYoutubeDL.script = [
        {
            "formats": [
                make_format("999", None, tbr=9999),
                make_format("137", 1080, tbr=4000),
            ]
        }
    ]

    options = get_available_qualities(URL)

    assert [o.height for o in options] == [1080]


def test_duplicate_heights_keep_only_the_highest_bitrate_format():
    FakeYoutubeDL.script = [
        {
            "formats": [
                make_format("A", 1080, tbr=2000),
                make_format("B", 1080, tbr=5000),  # should win
                make_format("C", 1080, tbr=3000),
            ]
        }
    ]

    options = get_available_qualities(URL)

    assert len(options) == 1
    assert options[0].format_id.startswith("B")


def test_duplicate_heights_fall_back_to_filesize_when_tbr_missing():
    FakeYoutubeDL.script = [
        {
            "formats": [
                make_format("A", 1080, tbr=None, filesize=1000),
                make_format("B", 1080, tbr=None, filesize=5000),  # should win
            ]
        }
    ]

    options = get_available_qualities(URL)

    assert options[0].format_id.startswith("B")


def test_video_only_format_gets_bestaudio_selector_appended():
    FakeYoutubeDL.script = [{"formats": [make_format("137", 1080, acodec="none")]}]

    options = get_available_qualities(URL)

    assert options[0].format_id == "137+bestaudio/best"


def test_format_with_audio_already_included_has_plain_format_id():
    FakeYoutubeDL.script = [{"formats": [make_format("22", 720, acodec="mp4a")]}]

    options = get_available_qualities(URL)

    assert options[0].format_id == "22"


def test_quality_option_is_a_frozen_dataclass():
    option = QualityOption(format_id="137", label="1080p", height=1080)

    with pytest.raises(Exception):
        option.height = 720


def test_quality_option_client_defaults_to_none():
    option = QualityOption(format_id="137", label="1080p", height=1080)

    assert option.client is None


# ---------------------------------------------------------------------------
# get_available_qualities() - default-first / fallback-client behavior
# ---------------------------------------------------------------------------


def test_default_client_succeeds_without_any_fallback_attempts():
    FakeYoutubeDL.script = [{"formats": [make_format("137", 1080, tbr=4000)]}]

    options = get_available_qualities(URL)

    assert len(FakeYoutubeDL.instances) == 1
    assert "extractor_args" not in FakeYoutubeDL.instances[0].opts
    assert options[0].client is None


def test_falls_back_to_android_after_bot_check_error_on_default():
    FakeYoutubeDL.script = [
        bot_check_error(),
        {"formats": [make_format("137", 1080, tbr=4000)]},
    ]

    options = get_available_qualities(URL)

    assert len(FakeYoutubeDL.instances) == 2
    assert "extractor_args" not in FakeYoutubeDL.instances[0].opts
    assert FakeYoutubeDL.instances[1].opts["extractor_args"] == {
        "youtube": {"player_client": ["android"]}
    }
    assert options[0].client == "android"


def test_falls_back_when_default_has_no_usable_formats_even_without_error():
    FakeYoutubeDL.script = [
        {"formats": []},  # default "succeeds" but exposes nothing usable
        {"formats": [make_format("137", 1080, tbr=4000)]},
    ]

    options = get_available_qualities(URL)

    assert len(FakeYoutubeDL.instances) == 2
    assert options[0].client == "android"


def test_stops_at_first_successful_fallback_client_tries_no_further():
    FakeYoutubeDL.script = [
        bot_check_error(),  # default blocked
        {"formats": [make_format("137", 1080, tbr=4000)]},  # android succeeds
    ]

    get_available_qualities(URL)

    # Only default + android were attempted - ios/tv never touched.
    assert len(FakeYoutubeDL.instances) == 2


def test_tries_android_then_ios_then_tv_in_order_before_giving_up():
    FakeYoutubeDL.script = [
        bot_check_error(),
        bot_check_error(),
        bot_check_error(),
        bot_check_error(),
    ]

    with pytest.raises(YouTubeExtractionError):
        get_available_qualities(URL)

    assert len(FakeYoutubeDL.instances) == 4
    client_args = [i.opts.get("extractor_args") for i in FakeYoutubeDL.instances]
    assert client_args == [
        None,
        {"youtube": {"player_client": ["android"]}},
        {"youtube": {"player_client": ["ios"]}},
        {"youtube": {"player_client": ["tv"]}},
    ]


def test_non_bot_check_error_raises_immediately_without_any_fallback():
    FakeYoutubeDL.script = [
        yt_dlp.utils.DownloadError(
            "Video unavailable. This video has been removed by the uploader"
        )
    ]

    with pytest.raises(YouTubeExtractionError):
        get_available_qualities(URL)

    # No fallback attempts for an error no alternate client would fix.
    assert len(FakeYoutubeDL.instances) == 1


def test_extraction_error_is_chained_from_the_underlying_yt_dlp_error():
    underlying = bot_check_error()
    FakeYoutubeDL.script = [underlying, underlying, underlying, underlying]

    with pytest.raises(YouTubeExtractionError) as exc_info:
        get_available_qualities(URL)

    assert exc_info.value.__cause__ is underlying


def test_all_clients_exposing_no_usable_formats_raises_extraction_error():
    FakeYoutubeDL.script = [
        {"formats": []},
        {"formats": []},
        {"formats": []},
        {"formats": []},
    ]

    with pytest.raises(YouTubeExtractionError):
        get_available_qualities(URL)

    assert len(FakeYoutubeDL.instances) == 4


def test_default_extraction_passes_ffmpeg_location_and_download_false(monkeypatch):
    import types

    monkeypatch.setattr(
        youtube_module,
        "settings",
        types.SimpleNamespace(ffmpeg_path="/opt/ffmpeg", download_dir="downloads/"),
    )
    FakeYoutubeDL.script = [{"formats": [make_format("137", 1080, tbr=4000)]}]

    get_available_qualities(URL)

    instance = FakeYoutubeDL.instances[0]
    assert instance.opts["ffmpeg_location"] == "/opt/ffmpeg"
    assert instance.extract_info_calls == [(URL, False)]


# ---------------------------------------------------------------------------
# download_youtube_video() - uses the recorded client, single attempt
# ---------------------------------------------------------------------------


def test_download_with_default_client_option_has_no_extractor_args(tmp_path):
    option = QualityOption(format_id="22", label="720p", height=720, client=None)
    FakeYoutubeDL.script = [{"id": "abc", "ext": "mp4"}]

    download_youtube_video(URL, option, download_dir=str(tmp_path))

    assert "extractor_args" not in FakeYoutubeDL.instances[0].opts


def test_download_reuses_the_recorded_fallback_client(tmp_path):
    option = QualityOption(
        format_id="137+bestaudio/best", label="1080p", height=1080, client="android"
    )
    FakeYoutubeDL.script = [{"id": "abc123", "ext": "mp4"}]

    download_youtube_video(URL, option, download_dir=str(tmp_path))

    instance = FakeYoutubeDL.instances[0]
    assert instance.opts["extractor_args"] == {
        "youtube": {"player_client": ["android"]}
    }
    assert instance.opts["format"] == "137+bestaudio/best"


def test_download_passes_format_merge_format_and_ffmpeg_location(
    tmp_path, monkeypatch
):
    import types

    monkeypatch.setattr(
        youtube_module,
        "settings",
        types.SimpleNamespace(ffmpeg_path="/opt/ffmpeg", download_dir="downloads/"),
    )
    option = QualityOption(
        format_id="137+bestaudio/best", label="1080p", height=1080, client="ios"
    )
    FakeYoutubeDL.script = [{"id": "abc123", "ext": "mp4"}]

    download_youtube_video(URL, option, download_dir=str(tmp_path))

    instance = FakeYoutubeDL.instances[0]
    assert instance.opts["format"] == "137+bestaudio/best"
    assert instance.opts["merge_output_format"] == "mp4"
    assert instance.opts["ffmpeg_location"] == "/opt/ffmpeg"
    assert instance.extract_info_calls == [(URL, True)]


def test_download_resolves_filepath_from_requested_downloads(tmp_path):
    expected_path = str(tmp_path / "abc123.mp4")
    option = QualityOption(format_id="137", label="1080p", height=1080)
    FakeYoutubeDL.script = [
        {
            "id": "abc123",
            "ext": "mp4",
            "requested_downloads": [{"filepath": expected_path}],
        }
    ]

    result = download_youtube_video(URL, option, download_dir=str(tmp_path))

    assert result == expected_path


def test_download_falls_back_to_prepare_filename_when_no_requested_downloads(
    tmp_path,
):
    option = QualityOption(format_id="22", label="720p", height=720)
    FakeYoutubeDL.script = [{"id": "xyz789", "ext": "mp4"}]

    result = download_youtube_video(URL, option, download_dir=str(tmp_path))

    assert result == str(tmp_path / "xyz789.mp4")


def test_download_creates_download_dir_if_missing(tmp_path):
    target_dir = tmp_path / "nested" / "downloads"
    option = QualityOption(format_id="22", label="720p", height=720)
    FakeYoutubeDL.script = [{"id": "abc", "ext": "mp4"}]

    download_youtube_video(URL, option, download_dir=str(target_dir))

    assert target_dir.is_dir()


def test_download_uses_settings_download_dir_by_default(monkeypatch, tmp_path):
    import types

    monkeypatch.setattr(
        youtube_module,
        "settings",
        types.SimpleNamespace(ffmpeg_path="ffmpeg", download_dir=str(tmp_path)),
    )
    option = QualityOption(format_id="22", label="720p", height=720)
    FakeYoutubeDL.script = [{"id": "abc", "ext": "mp4"}]

    result = download_youtube_video(URL, option)

    assert result == str(tmp_path / "abc.mp4")


def test_download_failure_raises_wrapped_error_with_a_single_attempt(tmp_path):
    option = QualityOption(
        format_id="137", label="1080p", height=1080, client="tv"
    )
    underlying = yt_dlp.utils.DownloadError("network died")
    FakeYoutubeDL.script = [underlying]

    with pytest.raises(YouTubeDownloadError) as exc_info:
        download_youtube_video(URL, option, download_dir=str(tmp_path))

    assert exc_info.value.__cause__ is underlying
    # Exactly one attempt - download never retries across clients.
    assert len(FakeYoutubeDL.instances) == 1


# ---------------------------------------------------------------------------
# No authentication options are ever introduced
# ---------------------------------------------------------------------------


_FORBIDDEN_AUTH_KEYS = {
    "cookiefile",
    "cookiesfrombrowser",
    "username",
    "password",
    "videopassword",
    "usenetrc",
}


def test_no_authentication_options_appear_during_a_full_fallback_run(tmp_path):
    FakeYoutubeDL.script = [
        bot_check_error(),
        bot_check_error(),
        {"formats": [make_format("137", 1080, tbr=4000)]},
    ]

    options = get_available_qualities(URL)

    FakeYoutubeDL.script = [{"id": "abc", "ext": "mp4"}]
    download_youtube_video(URL, options[0], download_dir=str(tmp_path))

    for instance in FakeYoutubeDL.instances:
        assert not (_FORBIDDEN_AUTH_KEYS & instance.opts.keys())
