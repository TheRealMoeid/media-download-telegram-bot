"""Per-user language preference storage.

This is the only module in the project that touches SQLite directly. All
other code (handlers, other services) must go through the public functions
here rather than opening its own connection - see PROJECT_ROADMAP.md,
Phase 0 decision: "Language persistence (Phase 1): SQLite. Accessed only
through services/language_service.py; no other module touches storage
directly."

Design notes (Phase 1 scope only - see AI Development Rules, Rule 3):
    - Fresh SQLite connection per operation. No pooling, no long-lived
      shared connection.
    - Schema is created automatically on first access
      (CREATE TABLE IF NOT EXISTS). No migration system.
    - No SQLAlchemy, no repository/DAO abstraction. A future phase can
      introduce these if persistence requirements grow; Phase 1 does not
      need them.
    - Supported language codes are validated here, in Python, not via a
      database CHECK constraint - so adding a new language later doesn't
      require a schema migration.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from config.settings import settings

SUPPORTED_LANGUAGES = {"fa", "en"}
DEFAULT_LANGUAGE = "en"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_language (
    user_id  INTEGER PRIMARY KEY,
    language TEXT NOT NULL
);
"""


def _resolve_db_path(db_path: Optional[str]) -> str:
    return db_path if db_path is not None else settings.db_path


def _get_connection(db_path: str) -> sqlite3.Connection:
    """Open a fresh connection and ensure the schema exists.

    Called on every operation by design (see module docstring) - this
    keeps Phase 1 simple and avoids managing connection lifecycle/state.
    """
    conn = sqlite3.connect(db_path)
    conn.execute(_CREATE_TABLE_SQL)
    return conn


def get_language(user_id: int, db_path: Optional[str] = None) -> str:
    """Return the user's saved language, or DEFAULT_LANGUAGE if unset.

    Safe to call anywhere you just need "what language do I render this
    in" - it always returns a usable language code.
    """
    resolved_path = _resolve_db_path(db_path)
    with _get_connection(resolved_path) as conn:
        row = conn.execute(
            "SELECT language FROM user_language WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return row[0] if row is not None else DEFAULT_LANGUAGE


def has_saved_language(user_id: int, db_path: Optional[str] = None) -> bool:
    """Return True only if the user has explicitly saved a language.

    Used by /start to decide whether to show the language-selection menu,
    as distinct from get_language()'s "give me a language to render in"
    default-to-English behavior.
    """
    resolved_path = _resolve_db_path(db_path)
    with _get_connection(resolved_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM user_language WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return row is not None


def set_language(
    user_id: int, language: str, db_path: Optional[str] = None
) -> None:
    """Save the user's explicit language choice.

    Raises:
        ValueError: if `language` is not one of SUPPORTED_LANGUAGES.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language code: {language!r}. "
            f"Supported codes: {sorted(SUPPORTED_LANGUAGES)}"
        )

    resolved_path = _resolve_db_path(db_path)
    with _get_connection(resolved_path) as conn:
        conn.execute(
            """
            INSERT INTO user_language (user_id, language)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET language = excluded.language
            """,
            (user_id, language),
        )
        conn.commit()
