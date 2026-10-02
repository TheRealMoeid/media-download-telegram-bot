import pytest

from services.translations import TRANSLATIONS, translate

EXPECTED_KEYS = {
    "welcome",
    "welcome_back",
    "choose_language",
    "language_set",
    "url.detected_youtube",
    "url.unsupported",
    "youtube.choose_quality",
    "youtube.single_quality_auto",
    "youtube.download_started",
    "youtube.download_complete",
    "youtube.selection_expired",
    "youtube.extraction_failed",
    "youtube.download_failed",
    "instagram.downloading",
    "instagram.download_failed",
    "delivery.send_failed",
    "menu.title",
    "menu.settings_button",
    "menu.settings_title",
    "menu.language_button",
    "menu.back_button",
}


def test_all_expected_keys_present():
    assert set(TRANSLATIONS.keys()) == EXPECTED_KEYS


@pytest.mark.parametrize("key", sorted(EXPECTED_KEYS))
def test_each_key_has_both_languages(key):
    assert set(TRANSLATIONS[key].keys()) == {"en", "fa"}


def test_translate_returns_expected_english_strings():
    assert translate("welcome", "en") == "Welcome! \U0001F44B"
    assert translate("welcome_back", "en") == "Welcome back! \U0001F44B"
    assert translate("language_set", "en") == "Language set to English \U0001F1FA\U0001F1F8"


def test_translate_returns_expected_persian_strings():
    assert translate("language_set", "fa") == (
        "\u0632\u0628\u0627\u0646 \u0628\u0647 \u0641\u0627\u0631\u0633\u06CC "
        "\u062A\u0646\u0638\u06CC\u0645 \u0634\u062F \U0001F1EE\U0001F1F7"
    )


def test_translate_unknown_key_raises_keyerror():
    with pytest.raises(KeyError):
        translate("does_not_exist", "en")


def test_translate_unknown_language_raises_keyerror():
    with pytest.raises(KeyError):
        translate("welcome", "de")


def test_url_translation_keys_are_nonempty_in_both_languages():
    for key in ("url.detected_youtube", "url.unsupported"):
        assert translate(key, "en").strip()
        assert translate(key, "fa").strip()


def test_youtube_translation_keys_are_nonempty_in_both_languages():
    for key in (
        "youtube.choose_quality",
        "youtube.selection_expired",
        "youtube.extraction_failed",
        "youtube.download_failed",
    ):
        assert translate(key, "en").strip()
        assert translate(key, "fa").strip()


def test_delivery_translation_keys_are_nonempty_in_both_languages():
    for key in (
        "instagram.downloading",
        "instagram.download_failed",
        "delivery.send_failed",
    ):
        assert translate(key, "en").strip()
        assert translate(key, "fa").strip()


def test_menu_translation_keys_are_nonempty_in_both_languages():
    for key in (
        "menu.title",
        "menu.settings_button",
        "menu.settings_title",
        "menu.language_button",
        "menu.back_button",
    ):
        assert translate(key, "en").strip()
        assert translate(key, "fa").strip()


def test_translate_substitutes_quality_placeholder():
    assert translate("youtube.download_started", "en", quality="1080p") == (
        "Downloading 1080p. This may take a moment..."
    )
    assert "1080p" in translate("youtube.download_started", "fa", quality="1080p")


def test_translate_without_kwargs_leaves_placeholder_templates_unformatted():
    # Calling without kwargs on a template that has a placeholder would
    # raise if it were ever accidentally formatted with no arguments;
    # translate() must only format when kwargs are actually given.
    raw = TRANSLATIONS["youtube.download_started"]["en"]
    assert "{quality}" in raw


def test_translate_without_kwargs_returns_raw_unformatted_template():
    # translate() only formats when kwargs are actually passed - calling
    # it without kwargs on a placeholder-bearing key must not raise, it
    # should simply hand back the raw template untouched.
    assert translate("youtube.download_started", "en") == TRANSLATIONS[
        "youtube.download_started"
    ]["en"]
