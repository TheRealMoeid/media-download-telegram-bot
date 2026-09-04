import pytest

from services.translations import TRANSLATIONS, translate

EXPECTED_KEYS = {"welcome", "welcome_back", "choose_language", "language_set"}


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
