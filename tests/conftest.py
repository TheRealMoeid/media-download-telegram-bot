"""Shared pytest fixtures."""

import types

import pytest

import services.video_service as video_service_module


@pytest.fixture(autouse=True)
def _never_keep_downloads_by_default(monkeypatch):
    """Keep tests independent of a developer's real .env.

    If KEEP_DOWNLOADS=true is set locally, every test asserting that a
    request directory was cleaned up would otherwise fail. Tests that
    want the keep behavior override this themselves.
    """
    monkeypatch.setattr(
        video_service_module,
        "settings",
        types.SimpleNamespace(keep_downloads=False),
    )
