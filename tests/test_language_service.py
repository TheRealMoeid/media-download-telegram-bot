"""Tests for services/language_service.py.

Every test uses an isolated SQLite file under pytest's tmp_path fixture
and passes it explicitly via the db_path parameter, so these tests never
touch the real bot.db and never require BOT_TOKEN to be set for a
meaningful config.settings import.
"""

import pytest

from services.language_service import (
    DEFAULT_LANGUAGE,
    get_language,
    has_saved_language,
    set_language,
)


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_language.db")


def test_get_language_returns_default_for_unknown_user(db_path):
    assert get_language(123, db_path=db_path) == DEFAULT_LANGUAGE


def test_has_saved_language_false_for_unknown_user(db_path):
    assert has_saved_language(123, db_path=db_path) is False


def test_set_then_get_language_round_trips(db_path):
    set_language(123, "fa", db_path=db_path)

    assert get_language(123, db_path=db_path) == "fa"


def test_set_language_marks_user_as_having_saved_a_language(db_path):
    set_language(123, "en", db_path=db_path)

    assert has_saved_language(123, db_path=db_path) is True


def test_set_language_twice_overwrites_existing_value(db_path):
    set_language(123, "fa", db_path=db_path)
    set_language(123, "en", db_path=db_path)

    assert get_language(123, db_path=db_path) == "en"


def test_different_users_have_independent_languages(db_path):
    set_language(111, "fa", db_path=db_path)
    set_language(222, "en", db_path=db_path)

    assert get_language(111, db_path=db_path) == "fa"
    assert get_language(222, db_path=db_path) == "en"
    assert has_saved_language(111, db_path=db_path) is True
    assert has_saved_language(222, db_path=db_path) is True


def test_set_language_rejects_unsupported_code(db_path):
    with pytest.raises(ValueError):
        set_language(123, "xx", db_path=db_path)


def test_set_language_rejecting_unsupported_code_does_not_save_anything(
    db_path,
):
    with pytest.raises(ValueError):
        set_language(123, "xx", db_path=db_path)

    assert has_saved_language(123, db_path=db_path) is False
    assert get_language(123, db_path=db_path) == DEFAULT_LANGUAGE
