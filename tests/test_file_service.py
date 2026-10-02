"""Tests for services/file_service.py. All use pytest's tmp_path."""

import os

from services.file_service import cleanup, create_request_dir


def test_create_request_dir_returns_existing_dir_inside_base(tmp_path):
    path = create_request_dir(base_dir=str(tmp_path))

    assert os.path.isdir(path)
    assert os.path.dirname(path) == str(tmp_path)


def test_create_request_dir_creates_missing_base_dir(tmp_path):
    base = tmp_path / "nested" / "downloads"

    path = create_request_dir(base_dir=str(base))

    assert os.path.isdir(path)


def test_each_request_dir_is_unique(tmp_path):
    a = create_request_dir(base_dir=str(tmp_path))
    b = create_request_dir(base_dir=str(tmp_path))

    assert a != b


def test_cleanup_removes_dir_and_contents(tmp_path):
    path = create_request_dir(base_dir=str(tmp_path))
    with open(os.path.join(path, "video.mp4"), "wb"):
        pass
    with open(os.path.join(path, "video.mp4.part"), "wb"):
        pass

    cleanup(path, base_dir=str(tmp_path))

    assert not os.path.exists(path)


def test_cleanup_leaves_other_request_dirs_alone(tmp_path):
    a = create_request_dir(base_dir=str(tmp_path))
    b = create_request_dir(base_dir=str(tmp_path))

    cleanup(a, base_dir=str(tmp_path))

    assert not os.path.exists(a)
    assert os.path.isdir(b)


def test_cleanup_of_missing_dir_does_not_raise(tmp_path):
    cleanup(str(tmp_path / "req_gone"), base_dir=str(tmp_path))


def test_cleanup_refuses_to_delete_the_base_dir_itself(tmp_path):
    cleanup(str(tmp_path), base_dir=str(tmp_path))

    assert tmp_path.is_dir()


def test_cleanup_refuses_paths_outside_base_dir(tmp_path):
    base = tmp_path / "downloads"
    base.mkdir()
    outside = tmp_path / "important"
    outside.mkdir()
    (outside / "keep.txt").write_text("x")

    cleanup(str(outside), base_dir=str(base))

    assert (outside / "keep.txt").exists()


def test_cleanup_refuses_path_traversal(tmp_path):
    base = tmp_path / "downloads"
    base.mkdir()
    outside = tmp_path / "important"
    outside.mkdir()

    cleanup(str(base / ".." / "important"), base_dir=str(base))

    assert outside.is_dir()


def test_default_base_dir_comes_from_settings(tmp_path, monkeypatch):
    import types
    import services.file_service as fs

    monkeypatch.setattr(fs, "settings", types.SimpleNamespace(download_dir=str(tmp_path)))

    path = create_request_dir()

    assert os.path.dirname(path) == str(tmp_path)
