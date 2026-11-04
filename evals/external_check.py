"""Run the code gate over real antenatal readings (UCI Maternal Health Risk).

The dataset (``data/external/maternal_health_risk.csv``, CC BY 4.0) has
age, systolic and diastolic BP, blood sugar (mmol/L), body temperature
(deg F), heart rate and a risk label (low, mid, high) from Bangladeshi
clinics. It has no symptoms, proteinuria or gestational age, so only the
vital-sign rules can fire, and its labels come from a different risk
model. This is therefore a behaviour check on real numbers, not an
accuracy test.

Reported on the de-duplicated rows: referral urgency (REFER_NOW,
WITHIN_24H) and, separately, readings that only trigger a WHO-aligned
follow-up action (R34 test urine protein, R35 diabetes assessment).

Usage: ``uv run python -m evals.external_check``.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from mamagate.triage import triage

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "external" / "maternal_health_risk.csv"
OUT_PATH = ROOT / "evals" / "external_check.json"
ADDED_RULES = {"R34_HYPERTENSION_TEST_PROTEIN", "R35_HIGH_BLOOD_SUGAR_ASSESS"}
LABELS = ("high risk", "mid risk", "low risk")
URGENCIES = ("REFER_NOW", "WITHIN_24H", "ROUTINE")


def load_unique_rows(path: Path = CSV_PATH) -> tuple[list[dict], int]:
    """Return de-duplicated rows and the raw row count."""
    with open(path, encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    seen: set[tuple] = set()
    unique = []
    for row in rows:
        key = tuple(row.values())
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique, len(rows)


def row_to_findings(row: dict[str, str]) -> dict:
    """Map one dataset row to gate findings."""
    return {
        "pregnant": True,
        "age": int(row["Age"]),
        "sbp": float(row["SystolicBP"]),
        "dbp": float(row["DiastolicBP"]),
        "pulse": float(row["HeartRate"]),
        "temp_c": round((float(row["BodyTemp"]) - 32) * 5 / 9, 1),
        "blood_sugar_mmol": float(row["BS"]),
    }


def _summarise(table: Counter, n_by_label: Counter) -> dict:
    """Build the cross-tab and headline rates for one rule set."""
    crosstab = {lab: {u: table[(lab, u)] for u in URGENCIES}
                for lab in LABELS}

    def flagged(lab: str) -> int:
        return n_by_label[lab] - table[(lab, "ROUTINE")]

    total = sum(n_by_label.values())
    return {
        "crosstab": crosstab,
        "high_risk_flagged": {"k": flagged("high risk"),
                              "n": n_by_label["high risk"]},
        "low_risk_flagged": {"k": flagged("low risk"),
                             "n": n_by_label["low risk"]},
        "refer_now_share": round(
            sum(table[(lab, "REFER_NOW")] for lab in LABELS) / total, 3),
    }


def main() -> None:
    """Report referrals and follow-up actions on the real readings."""
    rows, raw_count = load_unique_rows()
    table: Counter = Counter()
    action_rows: Counter = Counter()
    n_by_label: Counter = Counter()
    rules: Counter = Counter()
    for row in rows:
        label = row["RiskLevel"]
        n_by_label[label] += 1
        result = triage(row_to_findings(row))
        rules.update(result.rule_ids + result.action_ids)
        table[(label, result.urgency)] += 1
        if result.urgency == "ROUTINE" and result.actions:
            action_rows[label] += 1
    referrals = _summarise(table, n_by_label)
    follow_up = {lab: {"k": action_rows[lab], "n": n_by_label[lab]}
                 for lab in LABELS}
    covered = {
        lab: {"k": n_by_label[lab] - table[(lab, "ROUTINE")]
              + action_rows[lab], "n": n_by_label[lab]}
        for lab in LABELS}
    report = {
        "dataset": "UCI Maternal Health Risk (id 863), CC BY 4.0",
        "raw_rows": raw_count,
        "unique_rows": len(rows),
        "rows_by_label": dict(n_by_label),
        "referrals": referrals,
        "follow_up_action_only": follow_up,
        "referral_or_follow_up": covered,
        "rules_fired": dict(rules.most_common()),
        "added_follow_up_rules": sorted(ADDED_RULES),
        "caveat": (
            "Labels come from a different risk model and the data has no "
            "symptoms, proteinuria or gestational age. Follow-up rules ask "
            "for a test or assessment and never change urgency. This checks "
            "gate behaviour on real vital signs; it is not accuracy."),
    }
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
