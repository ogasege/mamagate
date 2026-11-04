"""Tests for the fixed family-card translations."""

import re

import pytest

from mamagate.languages import CARDS, VOICES, card_in, speech_text


@pytest.mark.parametrize("language", list(CARDS))
def test_every_language_has_complete_card(language):
    """Every language has the same number of items as English."""
    card = card_in(language, urgent=True)
    assert len(card["bring"]) == len(CARDS["en"]["bring"])
    assert len(card["signs"]) == len(CARDS["en"]["signs"])
    assert card["headline"]


@pytest.mark.parametrize("language", [k for k, v in VOICES.items() if v[0]])
def test_speech_text_fits_one_request(language):
    """Speech text stays under the 650-character request limit."""
    assert len(speech_text(language, urgent=True)) < 650


@pytest.mark.parametrize("language", ["ha", "yo"])
def test_hausa_and_yoruba_have_no_digits(language):
    """The speech service rejects digits in Hausa and Yoruba."""
    assert not re.search(r"\d", speech_text(language, urgent=False))


@pytest.mark.parametrize("language", list(CARDS))
def test_no_card_mentions_a_dose(language):
    """The family card never names a drug or a dose."""
    from mamagate.safety import contains_drug_dose

    card = card_in(language, urgent=True)
    assert not contains_drug_dose(" ".join(card["bring"] + card["signs"]))


def test_translations_are_labelled_as_drafts():
    """Every non-English card carries the review note."""
    assert card_in("en", True)["review_note"] is None
    assert all(card_in(k, True)["review_note"] for k in CARDS if k != "en")
