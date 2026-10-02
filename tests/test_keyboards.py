"""Tests for bot/keyboards.py's YouTube quality keyboard and size formatting."""

import pytest

from bot.keyboards import format_size, youtube_quality_keyboard
from downloader.youtube import QualityOption

MB = 1024 * 1024


@pytest.mark.parametrize(
    "size_bytes, expected",
    [
        (200 * 1024, "<1 MB"),
        (1 * MB, "1 MB"),
        (int(84.6 * MB), "85 MB"),
        (900 * MB, "900 MB"),
        (int(1.25 * 1024 * MB), "1.2 GB"),
        (3 * 1024 * MB, "3.0 GB"),
    ],
)
def test_format_size(size_bytes, expected):
    assert format_size(size_bytes) == expected


def test_button_shows_approximate_size_when_known():
    options = [QualityOption("137", "1080p", 1080, filesize=85 * MB)]

    keyboard = youtube_quality_keyboard("tok", options)

    assert keyboard.inline_keyboard[0][0].text == "1080p (~85 MB)"


def test_button_shows_only_label_when_size_unknown():
    options = [QualityOption("22", "720p", 720, filesize=None)]

    keyboard = youtube_quality_keyboard("tok", options)

    assert keyboard.inline_keyboard[0][0].text == "720p"


def test_callback_data_is_unchanged_by_sizes():
    options = [
        QualityOption("137", "1080p", 1080, filesize=85 * MB),
        QualityOption("22", "720p", 720),
    ]

    keyboard = youtube_quality_keyboard("tok", options)

    assert [row[0].callback_data for row in keyboard.inline_keyboard] == [
        "yt_quality:tok:0",
        "yt_quality:tok:1",
    ]
