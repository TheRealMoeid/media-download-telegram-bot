"""Centralized translation lookup by message key + language code.

Callers request text via translate(key, lang) rather than embedding raw
strings in handlers (see PROJECT_ROADMAP.md, "Translation system"). Kept
minimal by design for Phase 1: a plain dict, no fallback chains, and no
external file formats (JSON/YAML) - those remain implementation details
to introduce later if/when they're actually needed.
"""

from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, str]] = {
    "welcome": {
        "en": "Welcome! \U0001F44B",
        "fa": "\u062E\u0648\u0634 \u0622\u0645\u062F\u06CC\u062F! \U0001F44B",
    },
    "welcome_back": {
        "en": "Welcome back! \U0001F44B",
        "fa": "\u062E\u0648\u0634 \u0628\u0631\u06AF\u0634\u062A\u06CC\u062F! \U0001F44B",
    },
    "choose_language": {
        "en": "Please choose your language:",
        "fa": "\u0644\u0637\u0641\u0627\u064B \u0632\u0628\u0627\u0646 \u062E\u0648\u062F \u0631\u0627 \u0627\u0646\u062A\u062E\u0627\u0628 \u06A9\u0646\u06CC\u062F:",
    },
    "language_set": {
        "en": "Language set to English \U0001F1FA\U0001F1F8",
        "fa": "\u0632\u0628\u0627\u0646 \u0628\u0647 \u0641\u0627\u0631\u0633\u06CC \u062A\u0646\u0638\u06CC\u0645 \u0634\u062F \U0001F1EE\U0001F1F7",
    },
}


def translate(key: str, lang: str) -> str:
    """Return the localized string for `key` in `lang`.

    Raises KeyError if the key or language is undefined, so a missing
    translation fails loudly during development instead of silently
    falling back to something else.
    """
    return TRANSLATIONS[key][lang]
