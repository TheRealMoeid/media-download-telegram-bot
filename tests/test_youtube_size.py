"""Tests for the estimated-filesize logic in downloader/youtube.py.

Bypasses the yt-dlp fallback machinery entirely by patching
_extract_info_with_fallback(), so these tests only exercise how a
given `info` dict turns into QualityOption.filesize values.
"""

import pytest

import downloader.youtube as youtube_module
from downloader.youtube import get_available_qualities

URL = "https://youtube.com/watch?v=abc"


def fmt(format_id, height=None, vcodec="avc1", acodec="none", **extra):
    return {
        "format_id": format_id,
        "height": height,
        "vcodec": vcodec,
        "acodec": acodec,
        **extra,
    }


def audio(format_id, **extra):
    return fmt(format_id, height=None, vcodec="none", acodec="mp4a", **extra)


def run(monkeypatch, formats, duration=None):
    info = {"formats": formats}
    if duration is not None:
        info["duration"] = duration
    monkeypatch.setattr(
        youtube_module, "_extract_info_with_fallback", lambda url: (info, None)
    )
    return get_available_qualities(URL)


def test_uses_exact_filesize_when_present(monkeypatch):
    options = run(monkeypatch, [fmt("22", 720, acodec="mp4a", filesize=50_000_000)])

    assert options[0].filesize == 50_000_000


def test_falls_back_to_filesize_approx(monkeypatch):
    options = run(
        monkeypatch, [fmt("22", 720, acodec="mp4a", filesize_approx=40_000_000)]
    )

    assert options[0].filesize == 40_000_000


def test_falls_back_to_bitrate_times_duration(monkeypatch):
    # 800 kbit/s for 100 s = 800*1000/8*100 = 10,000,000 bytes
    options = run(
        monkeypatch, [fmt("22", 720, acodec="mp4a", tbr=800)], duration=100
    )

    assert options[0].filesize == 10_000_000


def test_unknown_size_is_none_not_guessed(monkeypatch):
    options = run(monkeypatch, [fmt("22", 720, acodec="mp4a")])

    assert options[0].filesize is None


def test_bitrate_without_duration_is_unknown(monkeypatch):
    options = run(monkeypatch, [fmt("22", 720, acodec="mp4a", tbr=800)])

    assert options[0].filesize is None


def test_video_only_format_includes_best_audio_size(monkeypatch):
    options = run(
        monkeypatch,
        [
            fmt("137", 1080, filesize=80_000_000),
            audio("139", abr=48, filesize=1_000_000),
            audio("140", abr=128, filesize=5_000_000),  # best audio wins
        ],
    )

    assert options[0].filesize == 85_000_000


def test_format_with_audio_already_included_gets_no_audio_added(monkeypatch):
    options = run(
        monkeypatch,
        [
            fmt("22", 720, acodec="mp4a", filesize=50_000_000),
            audio("140", abr=128, filesize=5_000_000),
        ],
    )

    assert options[0].filesize == 50_000_000


def test_video_only_with_no_audio_formats_uses_video_size_alone(monkeypatch):
    options = run(monkeypatch, [fmt("137", 1080, filesize=80_000_000)])

    assert options[0].filesize == 80_000_000


def test_video_only_with_unknown_video_size_stays_none(monkeypatch):
    options = run(
        monkeypatch,
        [fmt("137", 1080), audio("140", abr=128, filesize=5_000_000)],
    )

    assert options[0].filesize is None


def test_sizes_do_not_change_label_or_selector(monkeypatch):
    options = run(monkeypatch, [fmt("137", 1080, filesize=80_000_000)])

    assert options[0].label == "1080p"
    assert options[0].format_id == "137+bestaudio/best"
