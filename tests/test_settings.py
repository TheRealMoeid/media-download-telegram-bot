"""Tests for config/settings.py.

These tests exercise Settings.from_env() with explicit, in-memory
environment mappings only. They never read or depend on a real .env
file or real process environment variables, and they never spawn or
check for FFmpeg - that belongs to a separate startup-check test, not
here.
"""

import pytest

from config.settings import ConfigurationError, Settings


def test_from_env_raises_when_bot_token_missing():
    with pytest.raises(ConfigurationError):
        Settings.from_env(env={})


def test_from_env_raises_when_bot_token_blank():
    with pytest.raises(ConfigurationError):
        Settings.from_env(env={"BOT_TOKEN": "   "})


def test_from_env_uses_defaults_when_optional_vars_absent():
    settings = Settings.from_env(env={"BOT_TOKEN": "abc123"})

    assert settings.bot_token == "abc123"
    assert settings.download_dir == "downloads/"
    assert settings.db_path == "bot.db"
    assert settings.ffmpeg_path == "ffmpeg"


def test_from_env_uses_explicit_values_when_provided():
    env = {
        "BOT_TOKEN": "abc123",
        "DOWNLOAD_DIR": "/tmp/my-downloads/",
        "DB_PATH": "/tmp/my-bot.db",
        "FFMPEG_PATH": "/usr/local/bin/ffmpeg",
    }

    settings = Settings.from_env(env=env)

    assert settings.download_dir == "/tmp/my-downloads/"
    assert settings.db_path == "/tmp/my-bot.db"
    assert settings.ffmpeg_path == "/usr/local/bin/ffmpeg"


def test_from_env_strips_whitespace():
    env = {"BOT_TOKEN": "  abc123  ", "DOWNLOAD_DIR": "  downloads/  "}

    settings = Settings.from_env(env=env)

    assert settings.bot_token == "abc123"
    assert settings.download_dir == "downloads/"


def test_settings_instance_is_frozen():
    settings = Settings.from_env(env={"BOT_TOKEN": "abc123"})

    with pytest.raises(AttributeError):
        settings.bot_token = "changed"
