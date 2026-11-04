"""Tests for the code-owned danger-sign gate."""

import pytest

from mamagate.triage import (
    RuleExpressionError,
    _evaluate,
    _parse,
    load_rules,
    max_urgency,
    triage,
)


def test_rules_file_loads_and_every_rule_parses():
    """All 35 rules parse and use only declared fields."""
    spec = load_rules()
    assert len(spec["rules"]) == 35


def test_severe_pre_eclampsia_refers_now():
    """34 weeks, BP 168/112 with headache fires R12 and R14."""
    result = triage({
        "pregnant": True, "ga_weeks": 34, "sbp": 168, "dbp": 112,
        "pulse": 96, "temp_c": 36.9, "resp_rate": 18,
        "severe_headache": True,
    })
    assert result.urgency == "REFER_NOW"
    assert "R12_SEVERE_PE_SYMPTOMS" in result.rule_ids
    assert "R14_BP_SEVERE_ALONE" in result.rule_ids


def test_shock_alone_refers_now():
    """Pulse above 110 fires the shock rule."""
    result = triage({"postpartum": True, "pulse": 118, "sbp": 100})
    assert result.urgency == "REFER_NOW"
    assert "R03_SHOCK" in result.rule_ids


def test_missing_vitals_never_fire_and_are_reported():
    """An empty case is ROUTINE but lists every missing core input."""
    result = triage({"pregnant": True})
    assert result.urgency == "ROUTINE"
    assert set(result.missing_core_inputs) == {
        "sbp", "dbp", "pulse", "temp_c", "resp_rate"}
    assert "safe" not in result.headline.lower()
    assert "not measured" in result.headline


def test_normal_antenatal_visit_is_routine():
    """Normal vitals at 28 weeks fire nothing."""
    result = triage({
        "pregnant": True, "ga_weeks": 28, "sbp": 112, "dbp": 72,
        "pulse": 82, "temp_c": 36.8, "resp_rate": 16,
    })
    assert result.urgency == "ROUTINE"
    assert result.rule_ids == []
    assert result.missing_core_inputs == ()


def test_late_bleed_carries_no_vaginal_exam_warning():
    """Bleeding at 30 weeks refers now with the exam warning."""
    result = triage({
        "pregnant": True, "ga_weeks": 30, "vaginal_bleeding": True})
    fired = {r.rule_id: r for r in result.fired}
    assert result.urgency == "REFER_NOW"
    assert "vaginal examination" in fired["R07_LATE_PREGNANCY_BLEED"].warning


def test_postpartum_haemorrhage_uses_lower_threshold():
    """300 ml postpartum fires R09 even though SO uses 500 ml."""
    result = triage({
        "postpartum": True, "vaginal_bleeding": True, "blood_loss_ml": 300})
    assert "R09_PPH" in result.rule_ids


def test_priority_sign_is_within_24h():
    """Severe pallor alone is a WHO priority sign."""
    result = triage({"pregnant": True, "severe_pallor": True})
    assert result.urgency == "WITHIN_24H"
    assert result.rule_ids == ["R33_WHO_PRIORITY_SIGNS"]


def test_toxaemia_counts_two_of_three_signs():
    """Proteinuria plus oedema fires the two-signs rule."""
    result = triage({
        "pregnant": True, "urine_protein_plus": 1, "pitting_oedema": True})
    assert "R15_TOXAEMIA_TWO_SIGNS" in result.rule_ids


def test_string_flags_and_bad_numbers_are_coerced():
    """"yes" counts as true and junk numbers count as missing."""
    result = triage({"convulsion_or_unconscious": "yes", "sbp": "abc"})
    assert result.urgency == "REFER_NOW"
    assert "sbp" in result.missing_core_inputs


def test_unknown_fields_are_reported():
    """Misspelled fields are surfaced instead of silently ignored."""
    result = triage({"systolic": 170})
    assert result.unknown_fields == ("systolic",)


def test_fired_rules_are_sorted_most_urgent_first():
    """REFER_NOW rules come before WITHIN_24H rules."""
    result = triage({
        "pregnant": True, "severe_pallor": True, "pulse": 120})
    assert result.fired[0].urgency == "REFER_NOW"
    assert result.fired[-1].urgency == "WITHIN_24H"


def test_evaluator_rejects_function_calls():
    """The rule interpreter refuses anything outside the whitelist."""
    with pytest.raises(RuleExpressionError):
        _evaluate(_parse("__import__('os')"), {})


def test_max_urgency_only_raises():
    """Urgency can be raised and never lowered."""
    assert max_urgency("REFER_NOW", "ROUTINE") == "REFER_NOW"
    assert max_urgency("ROUTINE", "WITHIN_24H") == "WITHIN_24H"


def test_raised_bp_without_protein_is_a_test_action_not_referral():
    """WHO: 140-159/90-109 without protein is counselled, not referred."""
    result = triage({"pregnant": True, "ga_weeks": 30, "sbp": 146,
                     "dbp": 94, "pulse": 80, "temp_c": 36.8,
                     "resp_rate": 16})
    assert result.urgency == "ROUTINE"
    assert result.action_ids == ["R34_HYPERTENSION_TEST_PROTEIN"]
    assert "urine protein" in result.actions[0].action
    assert "action needed" in result.headline


def test_severe_bp_is_not_downgraded_by_follow_up_rule():
    """Severe BP stays REFER_NOW and R34 does not fire."""
    result = triage({"pregnant": True, "sbp": 165, "dbp": 100})
    assert result.urgency == "REFER_NOW"
    assert "R34_HYPERTENSION_TEST_PROTEIN" not in result.action_ids


def test_high_blood_sugar_is_assessment_not_referral():
    """High glucose prompts assessment and never raises urgency."""
    result = triage({"pregnant": True, "blood_sugar_mmol": 13})
    assert result.urgency == "ROUTINE"
    assert result.action_ids == ["R35_HIGH_BLOOD_SUGAR_ASSESS"]
