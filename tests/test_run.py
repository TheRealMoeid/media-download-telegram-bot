import pytest

from run import check_ffmpeg


def test_check_ffmpeg_passes_when_found(monkeypatch):
    monkeypatch.setattr("run.shutil.which", lambda path: "/usr/bin/ffmpeg")
    check_ffmpeg("ffmpeg")  # should not raise


def test_check_ffmpeg_raises_when_missing(monkeypatch):
    monkeypatch.setattr("run.shutil.which", lambda path: None)
    with pytest.raises(RuntimeError, match="FFmpeg was not found"):
        check_ffmpeg("ffmpeg")
