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
    assert settings.keep_downloads is False


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


@pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "on", " true "])
def test_keep_downloads_true_values(value):
    settings = Settings.from_env(env={"BOT_TOKEN": "abc", "KEEP_DOWNLOADS": value})

    assert settings.keep_downloads is True


@pytest.mark.parametrize("value", ["false", "0", "no", "off", "", "banana"])
def test_keep_downloads_false_values(value):
    settings = Settings.from_env(env={"BOT_TOKEN": "abc", "KEEP_DOWNLOADS": value})

    assert settings.keep_downloads is False


def test_settings_instance_is_frozen():
    settings = Settings.from_env(env={"BOT_TOKEN": "abc123"})

    with pytest.raises(AttributeError):
        settings.bot_token = "changed"


# --- LOG_LEVEL (Phase 2A) ----------------------------------------------


def test_log_level_defaults_to_info():
    settings = Settings.from_env(env={"BOT_TOKEN": "abc"})

    assert settings.log_level == "INFO"


def test_log_level_blank_falls_back_to_info():
    settings = Settings.from_env(env={"BOT_TOKEN": "abc", "LOG_LEVEL": "   "})

    assert settings.log_level == "INFO"


@pytest.mark.parametrize("value", ["debug", "DEBUG", " Warning ", "error", "CRITICAL"])
def test_log_level_accepts_valid_names_case_insensitively(value):
    settings = Settings.from_env(env={"BOT_TOKEN": "abc", "LOG_LEVEL": value})

    assert settings.log_level == value.strip().upper()


@pytest.mark.parametrize("value", ["verbose", "10", "warn"])
def test_log_level_rejects_invalid_names(value):
    with pytest.raises(ConfigurationError):
        Settings.from_env(env={"BOT_TOKEN": "abc", "LOG_LEVEL": value})
