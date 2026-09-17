"""Tests for downloader/manager.py's detect_platform().

Pure-function tests - no Telegram, no yt-dlp, no I/O. Covers valid
YouTube/Instagram URLs across host variants, malformed input, and
unsupported domains.
"""

import pytest

from downloader.manager import Platform, detect_platform


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "http://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtu.be/dQw4w9WgXcQ",
        "https://YOUTUBE.COM/watch?v=dQw4w9WgXcQ",
    ],
)
def test_detects_youtube_urls(url):
    assert detect_platform(url) == Platform.YOUTUBE


@pytest.mark.parametrize(
    "url",
    [
        "https://www.instagram.com/reel/Cxxxxxxx/",
        "https://instagram.com/reel/Cxxxxxxx/",
        "http://instagram.com/p/Cxxxxxxx/",
        "https://INSTAGRAM.com/p/Cxxxxxxx/",
    ],
)
def test_detects_instagram_urls(url):
    assert detect_platform(url) == Platform.INSTAGRAM


@pytest.mark.parametrize(
    "url",
    [
        "https://www.tiktok.com/@user/video/12345",
        "https://vimeo.com/12345",
        "https://example.com",
        "https://facebook.com/watch?v=12345",
    ],
)
def test_unsupported_domains_return_unknown(url):
    assert detect_platform(url) == Platform.UNKNOWN


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "not a url at all",
        "youtube.com/watch?v=dQw4w9WgXcQ",  # missing scheme
        "ftp://youtube.com/watch?v=dQw4w9WgXcQ",  # unsupported scheme
        "https://",  # scheme with no netloc
        "just some random text a user might send",
    ],
)
def test_malformed_or_non_url_input_returns_unknown(url):
    assert detect_platform(url) == Platform.UNKNOWN


def test_non_string_input_returns_unknown_instead_of_raising():
    assert detect_platform(None) == Platform.UNKNOWN
    assert detect_platform(12345) == Platform.UNKNOWN


def test_url_with_leading_trailing_whitespace_is_still_detected():
    assert detect_platform("  https://youtube.com/watch?v=abc  ") == Platform.YOUTUBE


def test_platform_enum_has_exactly_three_members():
    assert {p.name for p in Platform} == {"YOUTUBE", "INSTAGRAM", "UNKNOWN"}