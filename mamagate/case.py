"""Per-case state and the code-owned referral note.

A :class:`CaseContext` is created for each consultation. Tools read and
write it, and the urgency it holds can only ever be raised. The
referral note is rendered by code from the triage result and the
selected facility; the model only supplies plain-language narrative
fields, which are dose-filtered before they are used.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from mamagate.languages import all_cards
from mamagate.safety import contains_drug_dose
from mamagate.triage import TriageResult, load_rules, max_urgency

REQUIRED_NARRATIVE = (
    "main_reasons_for_referral",
    "transport_plan",
    "information_given_to_woman_and_companion",
)


@dataclass
class CaseContext:
    """Mutable state for one consultation."""

    triage: TriageResult
    phc_name: str = "Synthetic PHC (demo)"
    phc_lat: float = 11.95
    phc_lon: float = 8.49
    referring_worker: str = "CHEW (synthetic)"
    case_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    urgency: str = ""
    urgency_raises: list[dict[str, str]] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    facility: dict[str, Any] | None = None
    note: dict[str, Any] | None = None
    note_verified: bool = False
    outbox: list[dict[str, Any]] = field(default_factory=list)
    events: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Start the case at the gate's urgency."""
        if not self.urgency:
            self.urgency = self.triage.urgency

    def raise_urgency(self, level: str, reason: str) -> str:
        """Raise urgency; a request to lower it is refused."""
        new = max_urgency(self.urgency, level)
        if new == self.urgency and level != self.urgency:
            return (f"Refused: urgency stays {self.urgency}. MamaGate can "
                    "raise urgency but never lower the code gate's level.")
        self.urgency = new
        self.urgency_raises.append({"to": new, "reason": reason})
        return f"Urgency raised to {new}."


def _now() -> str:
    """Return the current UTC time in ISO format."""
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


def build_note(ctx: CaseContext, narrative: dict[str, str]) -> dict:
    """Assemble the referral note from code-owned facts and narrative."""
    findings = {k: v for k, v in ctx.triage.findings.items()
                if v not in (None, False, "")}
    facility = ctx.facility or {}
    note = {
        "referral_id": f"MG-{ctx.case_id}",
        "who_is_referring": f"{ctx.referring_worker}, {ctx.phc_name}",
        "facility": facility.get("name", "NOT SELECTED"),
        "facility_id": facility.get("facility_id"),
        "facility_emonc_capability": facility.get("emonc", "unknown"),
        "referral_date_time": _now(),
        "emergency_or_not": ctx.urgency,
        "synthetic_id": ctx.triage.findings.get("synthetic_id", ctx.case_id),
        "age": ctx.triage.findings.get("age", "not recorded"),
        "major_findings": findings,
        "not_measured": list(ctx.triage.missing_core_inputs),
        "triggering_rule_ids": ctx.triage.rule_ids,
        "rule_sources": {r.rule_id: list(r.sources)
                         for r in ctx.triage.fired},
        "rule_labels": {r.rule_id: r.label for r in ctx.triage.fired},
        "warnings": [r.warning for r in ctx.triage.fired if r.warning],
        "treatments_given_and_time_before_referral": (
            "Record here what you gave and when, as authorised in your "
            "National Standing Orders. MamaGate does not suggest doses."),
        "travel": facility.get("route"),
        "counter_referral_request": load_rules()["referral_note_fields"][
            "counter_referral"],
        "rules_version": ctx.triage.rules_version,
        "disclaimer": ctx.triage.disclaimer,
    }
    for key in REQUIRED_NARRATIVE:
        note[key] = narrative.get(key, "").strip()
    return note


def verify_note(ctx: CaseContext) -> list[str]:
    """Return every problem with the drafted note; empty means it passes."""
    note = ctx.note
    if note is None:
        return ["No referral note has been drafted."]
    problems = []
    if ctx.facility is None:
        problems.append("No receiving facility is selected.")
    if note["emergency_or_not"] != ctx.urgency:
        problems.append("Note urgency does not match the case urgency.")
    if sorted(note["triggering_rule_ids"]) != sorted(ctx.triage.rule_ids):
        problems.append("Rule IDs do not match the gate result.")
    for key in REQUIRED_NARRATIVE:
        if len(note.get(key, "")) < 10:
            problems.append(f"Field '{key}' is missing or too short.")
        if contains_drug_dose(note.get(key, "")):
            problems.append(f"Field '{key}' contains a dose.")
    banned = ("you are safe", "she is safe", "no need to worry",
              "nothing to worry", "diagnos")
    for key in REQUIRED_NARRATIVE:
        lowered = note.get(key, "").lower()
        for phrase in banned:
            if phrase in lowered:
                problems.append(f"Field '{key}' uses '{phrase}'.")
    return problems


FINDING_LABELS = {
    "ga_weeks": ("Gestational age", "weeks"),
    "pulse": ("Pulse", "/min"),
    "resp_rate": ("Respiratory rate", "/min"),
    "temp_c": ("Temperature", "°C"),
    "urine_protein_plus": ("Urine protein", "+"),
    "blood_loss_ml": ("Blood loss", "ml"),
    "pad_soaked_minutes": ("Pad soaked in", "min"),
    "hb_g_dl": ("Haemoglobin", "g/dL"),
    "pcv_pct": ("PCV", "%"),
    "blood_sugar_mmol": ("Blood sugar", "mmol/L"),
    "labour_hours": ("Labour so far", "h"),
    "second_stage_hours": ("Second stage", "h"),
    "third_stage_minutes": ("Third stage", "min"),
    "fhr": ("Fetal heart rate", "/min"),
    "hours_since_delivery": ("Since delivery", "h"),
    "weight_gain_kg_week": ("Weight gain", "kg/week"),
}
STAGE_FLAGS = {"pregnant": "Pregnant", "in_labour": "In labour",
               "postpartum": "Postpartum"}
HIDDEN = {"synthetic_id", "age", "phc_name", "facility_lat",
          "facility_lon", "notes", "sbp", "dbp"}


def _number(value: Any) -> str:
    """Format a number without a trailing .0."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(number)) if number.is_integer() else f"{number:g}"


def format_findings(findings: dict[str, Any]) -> list[str]:
    """Return the findings as labelled, human-readable lines."""
    lines = []
    stage = [v for k, v in STAGE_FLAGS.items() if findings.get(k)]
    if stage:
        lines.append("Stage: " + ", ".join(stage))
    if findings.get("sbp") is not None or findings.get("dbp") is not None:
        lines.append(f"Blood pressure: {_number(findings.get('sbp', '?'))}/"
                     f"{_number(findings.get('dbp', '?'))} mmHg")
    for key, value in findings.items():
        if key in HIDDEN or key in STAGE_FLAGS or value in (None, False, ""):
            continue
        if key in FINDING_LABELS:
            label, unit = FINDING_LABELS[key]
            suffix = unit if unit[0] in "+%/" else f" {unit}"
            lines.append(f"{label}: {_number(value)}{suffix}")
        elif value is True:
            lines.append(key.replace("_", " ").capitalize() + ": yes")
    return lines


def render_note_markdown(note: dict[str, Any]) -> str:
    """Render the referral note as readable Markdown for display or print."""
    travel = note.get("travel") or {}
    urgency = note["emergency_or_not"].replace("_", " ")
    sources = note.get("rule_sources", {})
    labels = note.get("rule_labels", {})
    lines = [
        f"# Referral note · {urgency}",
        "",
        f"**Referral ID:** {note['referral_id']}  ",
        f"**From:** {note['who_is_referring']}  ",
        f"**To:** {note['facility']} "
        f"(emergency obstetric care: {note['facility_emonc_capability']})  ",
        f"**Sent:** {note['referral_date_time']}  ",
        f"**Woman:** {note['synthetic_id']}, age {note['age']}",
        "",
        "## Danger signs found",
    ]
    for rid in note["triggering_rule_ids"]:
        label = labels.get(rid, rid)
        src = "; ".join(sources.get(rid, []))
        lines.append(f"- {label} ({rid.split('_')[0]}; {src})")
    if not note["triggering_rule_ids"]:
        lines.append("- None of the listed danger signs")
    if note["warnings"]:
        lines += ["", "**Warning:** " + " ".join(note["warnings"])]
    lines += ["", "## Findings"]
    lines += [f"- {line}" for line in format_findings(note["major_findings"])]
    if note["not_measured"]:
        lines.append("- Not measured: " + ", ".join(
            FINDING_LABELS.get(m, (m, ""))[0] if m in FINDING_LABELS else m
            for m in note["not_measured"]))
    lines += [
        "",
        "## Reasons for referral",
        note["main_reasons_for_referral"],
        "",
        "## Treatment before referral",
        note["treatments_given_and_time_before_referral"],
        "",
        "Given: ______________________  Time: ________",
        "",
        "## Transport",
        note["transport_plan"],
    ]
    if travel:
        lines += ["", f"Distance about {travel.get('distance_km')} km, "
                  f"about {travel.get('minutes')} minutes by road "
                  f"({travel.get('note', travel.get('provider'))})."]
    lines += [
        "",
        "## Told to the woman and companion",
        note["information_given_to_woman_and_companion"],
        "",
        "## Counter-referral: please complete and return to the clinic",
    ]
    lines += [f"- {field.replace('_', ' ').capitalize()}: "
              "______________________"
              for field in note["counter_referral_request"]]
    lines += ["", f"*{note['disclaimer']}*"]
    return "\n".join(lines)


FAMILY_DANGER_SIGNS = (
    "heavy bleeding",
    "fits or fainting",
    "severe headache or blurred vision",
    "fever or feeling very weak",
    "fast or difficult breathing",
    "severe pain in the belly",
    "the baby stops moving",
)


def build_family_card(note: dict[str, Any]) -> dict[str, Any]:
    """Return a plain-language card for the woman and her family.

    Fixed, code-owned wording only: where to go, how long it takes, what
    to bring, and which signs mean go at once. No diagnosis, no doses.
    The transport plan is the dose-filtered narrative from the note.
    """
    travel = note.get("travel") or {}
    urgent = note["emergency_or_not"] == "REFER_NOW"
    return {
        "title": "Your referral card",
        "go_now": urgent,
        "headline": ("Go to the hospital now. Do not wait."
                     if urgent else
                     "Go to the hospital within 24 hours."),
        "where": note["facility"],
        "how_long": (f"About {travel.get('minutes')} minutes by road"
                     if travel.get("minutes") else "Ask the health worker"),
        "referral_id": note["referral_id"],
        "transport_plan": note.get("transport_plan", ""),
        "bring": ["this card and the referral note", "the antenatal card",
                  "money for transport and hospital costs",
                  "an adult companion who will stay with her",
                  "a relative who can give blood if needed"],
        "go_at_once_if": list(FAMILY_DANGER_SIGNS),
        "footer": ("Show this card at the hospital. Synthetic demo. "
                   "Translations are drafts, not yet reviewed."),
        "translations": all_cards(urgent),
    }
