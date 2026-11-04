"""Tests for the dose filter and facility ranking."""

import pytest

from mamagate.facilities import rank_facilities
from mamagate.safety import contains_dose, is_dose_request, redact_doses


@pytest.mark.parametrize("text", [
    "Give magnesium sulphate 4 g IV over 5 minutes.",
    "Administer oxytocin 10 IU IM now.",
    "Misoprostol 800 mcg sublingual.",
    "Give 2 tablets of nifedipine.",
    "Start a drip with 20 units.",
])
def test_doses_are_redacted(text):
    """Any dose with a drug or route is replaced by the refusal."""
    out, count = redact_doses(text, "SO-CHEW p312")
    assert count == 1
    assert "Dose withheld" in out
    assert "SO-CHEW p312" in out
    assert not contains_dose(out.replace("SO-CHEW p312", ""))


def test_clinical_measurements_are_kept():
    """BP, temperature and measured blood loss are not doses."""
    text = "BP 168/112 mmHg, temp 37.1 C. Estimated loss 300 ml so far."
    out, count = redact_doses(text)
    assert count == 0
    assert out == text


def test_dose_request_detection():
    """Questions about doses are recognised."""
    assert is_dose_request("What dose of magnesium should I give?")
    assert is_dose_request("Should I start a drip to augment labour?")
    assert not is_dose_request("Where is the nearest hospital?")


def test_refer_now_skips_primary_and_prefers_emonc():
    """REFER_NOW never ranks a PHC and puts confirmed EmONC first."""
    ranked = rank_facilities(11.95, 8.49, "REFER_NOW")
    assert all(r["level"] != "primary" for r in ranked)
    assert ranked[0]["emonc"] == "yes"
    assert "not a routed time" in ranked[0]["estimate_method"]


def test_swapped_coordinates_are_rejected():
    """Latitude and longitude swapped falls outside Nigeria."""
    with pytest.raises(ValueError):
        rank_facilities(8.49, 41.95, "REFER_NOW")


def test_routing_falls_back_to_labelled_estimate(monkeypatch):
    """With no provider available the estimate is labelled as such."""
    from mamagate.routing import route

    monkeypatch.setenv("MAMAGATE_DISABLE_AWS_ROUTES", "1")
    monkeypatch.delenv("MAMAGATE_ENABLE_OSRM", raising=False)
    result = route((11.95, 8.49), (12.00, 8.52))
    assert result["provider"] == "straight-line-estimate"
    assert "Not routed" in result["note"]


def test_measured_blood_loss_is_not_a_drug_dose():
    """A measured volume is a finding, not a dose."""
    from mamagate.safety import contains_drug_dose

    assert not contains_drug_dose("She has lost 400 ml of blood.")
    assert contains_drug_dose("Give oxytocin 10 IU IM.")
