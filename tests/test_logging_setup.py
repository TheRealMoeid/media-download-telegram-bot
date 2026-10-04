"""Tests for config/logging_setup.py.

Everything uses a FAKE token and a tmp_path log file - no real token,
no network, no writes to the real logs/ directory. The fixture restores
the root logger and the httpx/httpcore loggers afterwards so other
tests are unaffected, and closes the file handler so Windows can delete
the tmp_path.
"""

import logging

import pytest

from config.logging_setup import RedactingFormatter, configure_logging

FAKE_TOKEN = "123456789:AAFakeTokenForTestsOnly_abcdefghijklmn"
TOKEN_URL = f"https://api.telegram.org/bot{FAKE_TOKEN}/getUpdates"


@pytest.fixture
def log_file(tmp_path):
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    saved_levels = {n: logging.getLogger(n).level for n in ("httpx", "httpcore")}

    yield str(tmp_path / "logs" / "bot.log")

    for handler in list(root.handlers):
        if handler not in saved_handlers:
            root.removeHandler(handler)
            handler.close()
    root.setLevel(saved_level)
    for name, level in saved_levels.items():
        logging.getLogger(name).setLevel(level)


def flush_all():
    for handler in logging.getLogger().handlers:
        handler.flush()


def read(path):
    flush_all()
    with open(path, encoding="utf-8") as f:
        return f.read()


# --- layer 1: httpx / httpcore are silenced ----------------------------


def test_httpx_info_records_are_never_emitted(log_file, capsys):
    configure_logging(FAKE_TOKEN, log_file=log_file)

    logging.getLogger("httpx").info('HTTP Request: POST %s "HTTP/1.1 200 OK"', TOKEN_URL)
    logging.getLogger("httpcore").info("connect %s", TOKEN_URL)

    assert "api.telegram.org" not in read(log_file)
    assert "api.telegram.org" not in capsys.readouterr().err


# --- layer 2: redaction safety net -------------------------------------


def test_httpx_style_record_with_token_is_redacted_in_file_and_console(
    log_file, capsys
):
    configure_logging(FAKE_TOKEN, log_file=log_file)

    # WARNING gets past the httpx level cap, so this exercises redaction.
    logging.getLogger("httpx").warning('HTTP Request: POST %s "HTTP/1.1 200 OK"', TOKEN_URL)

    file_text = read(log_file)
    console_text = capsys.readouterr().err
    for text in (file_text, console_text):
        assert FAKE_TOKEN not in text
        assert "AAFakeToken" not in text
        assert "HTTP Request: POST" in text  # the rest of the line survives


def test_bare_token_outside_a_url_is_redacted(log_file):
    configure_logging(FAKE_TOKEN, log_file=log_file)

    logging.getLogger("whatever").error("token was %s oops", FAKE_TOKEN)

    text = read(log_file)
    assert FAKE_TOKEN not in text
    assert "<redacted>" in text


def test_token_inside_a_traceback_is_redacted(log_file):
    configure_logging(FAKE_TOKEN, log_file=log_file)

    try:
        raise RuntimeError(f"request to {TOKEN_URL} failed")
    except RuntimeError:
        logging.getLogger("whatever").exception("boom")

    text = read(log_file)
    assert "Traceback" in text
    assert FAKE_TOKEN not in text


def test_url_shaped_token_is_redacted_even_if_it_is_not_the_configured_one(
    log_file,
):
    configure_logging("some-other-token", log_file=log_file)

    logging.getLogger("whatever").warning("calling %s", TOKEN_URL)

    assert FAKE_TOKEN not in read(log_file)


def test_ordinary_messages_pass_through_unchanged(log_file):
    configure_logging(FAKE_TOKEN, log_file=log_file)

    logging.getLogger("bot.test").info("Starting bot polling...")

    assert "bot.test - INFO - Starting bot polling..." in read(log_file)


def test_formatter_with_no_token_does_not_crash_or_mangle_text():
    formatter = RedactingFormatter(None)

    assert formatter.redact("plain text") == "plain text"


# --- file handler / rotation -------------------------------------------


def test_log_directory_is_created_if_missing(log_file):
    configure_logging(FAKE_TOKEN, log_file=log_file)

    logging.getLogger("x").info("hello")

    assert "hello" in read(log_file)


def test_file_handler_rotates_when_max_size_is_reached(log_file):
    configure_logging(
        FAKE_TOKEN, log_file=log_file, max_bytes=300, backup_count=2
    )

    for i in range(40):
        logging.getLogger("x").info("line number %d with some padding", i)
    flush_all()

    import os

    assert os.path.exists(log_file)
    assert os.path.exists(log_file + ".1")
    assert not os.path.exists(log_file + ".3")  # honours backup_count=2


# --- level + idempotency ------------------------------------------------


def test_level_argument_controls_the_root_logger(log_file):
    configure_logging(FAKE_TOKEN, level="warning", log_file=log_file)

    logging.getLogger("x").info("hidden")
    logging.getLogger("x").warning("shown")

    text = read(log_file)
    assert "hidden" not in text
    assert "shown" in text


def test_calling_twice_does_not_duplicate_log_lines(log_file):
    configure_logging(FAKE_TOKEN, log_file=log_file)
    configure_logging(FAKE_TOKEN, log_file=log_file)

    logging.getLogger("x").info("only once please")

    assert read(log_file).count("only once please") == 1
