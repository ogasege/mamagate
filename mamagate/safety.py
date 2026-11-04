"""Deterministic output safety for MamaGate.

MamaGate never prints drug doses. Every piece of model text that leaves
the system passes through :func:`redact_doses`, which replaces any
sentence containing a dose-like quantity with a pointer to the National
Standing Orders. The check is code, so it holds even when a prompt or a
model misbehaves.
"""

from __future__ import annotations

import re

DOSE_PATTERN = re.compile(
    r"(?i)\b\d+(?:[.,]\d+)?\s*(?:-\s*\d+(?:[.,]\d+)?\s*)?"
    r"(?:mg|mcg|ug|µg|g|gm|grams?|iu|i\.u\.|ml|mls|units?|tabs?|"
    r"tablets?|drops?|%)(?![a-z])"
)

DRUG_TERMS = (
    "magnesium", "mgso4", "oxytocin", "misoprostol", "carbetocin",
    "ergometrine", "nifedipine", "hydralazine", "labetalol",
    "methyldopa", "diazepam", "ampicillin", "gentamicin",
    "metronidazole", "paracetamol", "iron", "folic",
)

DOSE_REQUEST_PATTERN = re.compile(
    r"(?i)\b(dose|dosage|how much|how many (?:mg|ml|tablets)|"
    r"what amount|milligram|units of|loading dose|regimen|"
    r"prescribe|augment|induce|start (?:a|an) drip)\b"
)

REFUSAL_TEMPLATE = (
    "[Dose withheld by MamaGate] MamaGate does not give drug doses. "
    "Check the treatment and dose in your National Standing Orders{ref}, "
    "give only what you are authorised to give, and do not delay the "
    "referral."
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?\n])\s+")


def refusal(scope_ref: str | None = None) -> str:
    """Return the standard dose refusal, citing a page when known."""
    ref = f" ({scope_ref})" if scope_ref else ""
    return REFUSAL_TEMPLATE.format(ref=ref)


def contains_dose(text: str) -> bool:
    """Return True if the text contains a dose-like quantity."""
    return bool(DOSE_PATTERN.search(text or ""))


def contains_drug_dose(text: str) -> bool:
    """Return True if any sentence pairs a quantity with a drug or route.

    Measured values such as "400 ml blood loss" are not doses; a dose is
    a quantity in the same sentence as a drug name or an administration
    verb or route.
    """
    return any(
        contains_dose(piece) and _mentions_drug_or_admin(piece)
        for piece in _SENTENCE_SPLIT.split(text or ""))


def is_dose_request(text: str) -> bool:
    """Return True if a user message asks for dosing or prescribing."""
    return bool(DOSE_REQUEST_PATTERN.search(text or ""))


def redact_doses(text: str, scope_ref: str | None = None) -> tuple[str, int]:
    """Replace every sentence that carries a dose with the refusal.

    Clinical values such as blood pressure (``mmHg``), temperature and
    blood-loss volumes measured by the worker are not doses, but the
    pattern still matches volumes in ``ml``. Blood loss is therefore
    expected in the structured findings and the referral note template,
    which are rendered by code, not by the model.

    Args:
        text: Model output to check.
        scope_ref: Standing Orders page to cite in the refusal.

    Returns:
        The redacted text and the number of sentences replaced.

    """
    if not text:
        return text, 0
    pieces = _SENTENCE_SPLIT.split(text)
    redacted = 0
    out: list[str] = []
    for piece in pieces:
        if contains_dose(piece) and _mentions_drug_or_admin(piece):
            redacted += 1
            if not out or out[-1] != refusal(scope_ref):
                out.append(refusal(scope_ref))
        else:
            out.append(piece)
    return " ".join(out), redacted


def _mentions_drug_or_admin(sentence: str) -> bool:
    """Return True if a sentence names a drug or an administration verb."""
    lowered = sentence.lower()
    if any(term in lowered for term in DRUG_TERMS):
        return True
    return bool(re.search(
        r"\b(give|administer|inject|infuse|bolus|im\b|iv\b|orally|"
        r"sublingual|stat\b|drip)", lowered))
