"""Centralized translation lookup by message key + language code.

Callers request text via translate(key, lang) rather than embedding raw
strings in handlers (see PROJECT_ROADMAP.md, "Translation system"). Kept
minimal by design for Phase 1: a plain dict, no fallback chains, and no
external file formats (JSON/YAML) - those remain implementation details
to introduce later if/when they're actually needed.

translate() also accepts optional keyword arguments, applied via
str.format(), for the small number of messages that need to embed a
runtime value (currently: the YouTube quality label, e.g. "1080p").
This was anticipated in the original design note on `language_set`
("if a third language were ever added this would need to become a
template") - the same substitution mechanism now covers the YouTube
messages that need it. Messages that don't need substitution are
completely unaffected; translate() only formats when kwargs are given.
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
    "url.detected_youtube": {
        "en": "This looks like a YouTube link \U0001F3AC. Downloading isn't available yet, but support is on the way!",
        "fa": (
            "\u0627\u06CC\u0646 \u06CC\u06A9 \u0644\u06CC\u0646\u06A9 "
            "\u06CC\u0648\u062A\u06CC\u0648\u0628 \u0627\u0633\u062A \U0001F3AC. "
            "\u062F\u0627\u0646\u0644\u0648\u062F \u0647\u0646\u0648\u0632 "
            "\u0641\u0639\u0627\u0644 \u0646\u06CC\u0633\u062A\u060C \u0627\u0645\u0627 "
            "\u0628\u0647 \u0632\u0648\u062F\u06CC \u0627\u0636\u0627\u0641\u0647 "
            "\u062E\u0648\u0627\u0647\u062F \u0634\u062F!"
        ),
    },
    "url.detected_instagram": {
        "en": "This looks like an Instagram link \U0001F4F7. Downloading isn't available yet, but support is on the way!",
        "fa": (
            "\u0627\u06CC\u0646 \u06CC\u06A9 \u0644\u06CC\u0646\u06A9 "
            "\u0627\u06CC\u0646\u0633\u062A\u0627\u06AF\u0631\u0627\u0645 "
            "\u0627\u0633\u062A \U0001F4F7. \u062F\u0627\u0646\u0644\u0648\u062F "
            "\u0647\u0646\u0648\u0632 \u0641\u0639\u0627\u0644 \u0646\u06CC\u0633\u062A\u060C "
            "\u0627\u0645\u0627 \u0628\u0647 \u0632\u0648\u062F\u06CC \u0627\u0636\u0627\u0641\u0647 "
            "\u062E\u0648\u0627\u0647\u062F \u0634\u062F!"
        ),
    },
    "url.unsupported": {
        "en": "Sorry, I don't recognize that as a supported link. I currently support YouTube and Instagram.",
        "fa": (
            "\u0645\u062A\u0623\u0633\u0641\u0627\u0646\u0647\u060C \u0627\u06CC\u0646 "
            "\u0631\u0627 \u0628\u0647 \u0639\u0646\u0648\u0627\u0646 \u06CC\u06A9 "
            "\u0644\u06CC\u0646\u06A9 \u067E\u0634\u062A\u06CC\u0628\u0627\u0646\u06CC "
            "\u0634\u062F\u0647 \u0646\u0645\u06CC\u200C\u0634\u0646\u0627\u0633\u0645. "
            "\u0627\u06A9\u0646\u0648\u0646 \u0641\u0642\u0637 \u0627\u0632 "
            "\u06CC\u0648\u062A\u06CC\u0648\u0628 \u0648 \u0627\u06CC\u0646\u0633\u062A\u0627\u06AF\u0631\u0627\u0645 "
            "\u067E\u0634\u062A\u06CC\u0628\u0627\u0646\u06CC \u0645\u06CC\u200C\u06A9\u0646\u0645."
        ),
    },
    # --- YouTube quality-selection (Phase 1, YouTube downloading step) ---
    "youtube.choose_quality": {
        "en": "Multiple qualities are available for this video. Please choose one:",
        "fa": "چند کیفیت مختلف برای این ویدیو موجود است. لطفاً یکی را انتخاب کنید:",
    },
    "youtube.single_quality_auto": {
        "en": "Only one quality was available ({quality}), so I downloaded it automatically.",
        "fa": "فقط یک کیفیت ({quality}) موجود بود، پس آن را به‌طور خودکار دانلود کردم.",
    },
    "youtube.download_started": {
        "en": "Downloading {quality}. This may take a moment...",
        "fa": "در حال دانلود {quality}. ممکن است کمی طول بکشد...",
    },
    "youtube.download_complete": {
        "en": "Finished downloading {quality}. \u2705",
        "fa": "دانلود {quality} به پایان رسید. \u2705",
    },
    "youtube.selection_expired": {
        "en": "This selection has expired or was already used. Please send the YouTube link again.",
        "fa": "این انتخاب منقضی شده یا قبلاً استفاده شده است. لطفاً لینک یوتیوب را دوباره ارسال کنید.",
    },
    "youtube.extraction_failed": {
        "en": "Sorry, I couldn't check the available qualities for that video. Please try again later.",
        "fa": "متأسفانه نتوانستم کیفیت‌های موجود این ویدیو را بررسی کنم. لطفاً بعداً دوباره امتحان کنید.",
    },
    "youtube.download_failed": {
        "en": "Sorry, the download failed. Please try again later.",
        "fa": "متأسفانه دانلود ناموفق بود. لطفاً بعداً دوباره امتحان کنید.",
    },
}


def translate(key: str, lang: str, **kwargs: object) -> str:
    """Return the localized string for `key` in `lang`.

    Raises KeyError if the key or language is undefined, so a missing
    translation fails loudly during development instead of silently
    falling back to something else.

    If `kwargs` are given, the resolved template is passed through
    str.format(**kwargs) - e.g. translate("youtube.download_started",
    "en", quality="1080p"). Templates that don't contain any "{...}"
    placeholders are unaffected either way.
    """
    template = TRANSLATIONS[key][lang]
    if kwargs:
        return template.format(**kwargs)
    return template