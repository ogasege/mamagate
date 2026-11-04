"""Code-owned maternal danger-sign gate.

The gate runs before any language model is called. It evaluates the
rules in ``rules.yaml`` against structured findings entered by a
health worker and returns the highest urgency that fired, the rule IDs,
and the core inputs that were missing.

Rule expressions are parsed with :mod:`ast` and evaluated by a small
whitelist interpreter; nothing from the rules file is passed to
``eval``. Missing numbers are NaN (every comparison with them is
false) and missing flags are false, so an absent vital can never fire
a rule, and an absent vital is reported instead of read as normal.
"""

from __future__ import annotations

import ast
import math
import operator
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

RULES_PATH = Path(__file__).with_name("rules.yaml")

URGENCY_ORDER = {"ROUTINE": 0, "WITHIN_24H": 1, "REFER_NOW": 2}

_COMPARE_OPS = {
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}


class RuleExpressionError(ValueError):
    """Raised when a rule uses syntax outside the allowed subset."""


@dataclass(frozen=True)
class FiredRule:
    """A rule that matched the entered findings."""

    rule_id: str
    label: str
    urgency: str
    status: str
    sources: tuple[str, ...]
    scope_ref: str | None = None
    warning: str | None = None
    action: str | None = None


@dataclass(frozen=True)
class TriageResult:
    """Outcome of the gate for one case."""

    urgency: str
    fired: tuple[FiredRule, ...]
    missing_core_inputs: tuple[str, ...]
    unknown_fields: tuple[str, ...]
    rules_version: str
    disclaimer: str
    findings: dict[str, Any] = field(default_factory=dict)
    actions: tuple[FiredRule, ...] = ()

    @property
    def rule_ids(self) -> list[str]:
        """Return the IDs of every danger-sign rule that fired."""
        return [rule.rule_id for rule in self.fired]

    @property
    def action_ids(self) -> list[str]:
        """Return the IDs of follow-up rules (no urgency change)."""
        return [rule.rule_id for rule in self.actions]

    @property
    def headline(self) -> str:
        """Return a one-line summary that never says "safe"."""
        if self.urgency == "ROUTINE":
            text = "ROUTINE: no listed danger sign found in the entered data"
        else:
            text = f"{self.urgency}: " + ", ".join(self.rule_ids)
        if self.actions:
            text += "; action needed: " + ", ".join(self.action_ids)
        if self.missing_core_inputs:
            text += " (not measured: " + ", ".join(
                self.missing_core_inputs) + ")"
        return text

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable view of the result."""
        return {
            "urgency": self.urgency,
            "headline": self.headline,
            "rule_ids": self.rule_ids,
            "fired": [
                {
                    "rule_id": r.rule_id,
                    "label": r.label,
                    "urgency": r.urgency,
                    "status": r.status,
                    "sources": list(r.sources),
                    "scope_ref": r.scope_ref,
                    "warning": r.warning,
                }
                for r in self.fired
            ],
            "actions": [
                {
                    "rule_id": r.rule_id,
                    "label": r.label,
                    "action": r.action,
                    "status": r.status,
                    "sources": list(r.sources),
                }
                for r in self.actions
            ],
            "missing_core_inputs": list(self.missing_core_inputs),
            "unknown_fields": list(self.unknown_fields),
            "rules_version": self.rules_version,
            "disclaimer": self.disclaimer,
        }


@lru_cache(maxsize=4)
def load_rules(path: str = str(RULES_PATH)) -> dict[str, Any]:
    """Load and validate the rules file once.

    Every rule expression is parsed eagerly so a malformed rule fails
    at start-up rather than silently during a consultation.
    """
    with open(path, encoding="utf-8") as handle:
        spec = yaml.safe_load(handle)
    known = set(spec["fields"]["numeric"]) | set(spec["fields"]["flags"])
    for rule in spec["rules"]:
        if rule["urgency"] not in URGENCY_ORDER:
            raise RuleExpressionError(f"{rule['id']}: bad urgency")
        tree = _parse(rule["when"])
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        unknown = names - known
        if unknown:
            raise RuleExpressionError(
                f"{rule['id']} uses undeclared fields: {sorted(unknown)}")
    return spec


@lru_cache(maxsize=256)
def _parse(expression: str) -> ast.Expression:
    """Parse a rule expression in eval mode."""
    return ast.parse(expression, mode="eval")


def _evaluate(node: ast.AST, env: dict[str, Any]) -> Any:
    """Evaluate the whitelisted expression subset."""
    if isinstance(node, ast.Expression):
        return _evaluate(node.body, env)
    if isinstance(node, ast.BoolOp):
        values = (_evaluate(v, env) for v in node.values)
        if isinstance(node.op, ast.And):
            return all(bool(v) for v in values)
        return any(bool(v) for v in values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not bool(_evaluate(node.operand, env))
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _evaluate(node.left, env) + _evaluate(node.right, env)
    if isinstance(node, ast.Compare):
        left = _evaluate(node.left, env)
        for op, comparator in zip(node.ops, node.comparators, strict=True):
            right = _evaluate(comparator, env)
            func = _COMPARE_OPS.get(type(op))
            if func is None:
                raise RuleExpressionError("operator not allowed")
            if not func(left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.Constant) and isinstance(
            node.value, (int, float, bool)):
        return node.value
    raise RuleExpressionError(f"syntax not allowed: {type(node).__name__}")


def _coerce_number(value: Any) -> float:
    """Convert an entered value to float, or NaN if absent or invalid."""
    if value is None or isinstance(value, bool):
        return math.nan
    try:
        number = float(value)
    except (TypeError, ValueError):
        return math.nan
    return number if math.isfinite(number) else math.nan


def _coerce_flag(value: Any) -> bool:
    """Convert an entered value to a boolean flag."""
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "y", "1"}
    return bool(value)


def build_environment(
    findings: dict[str, Any], spec: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Return the evaluation environment and any unknown field names."""
    numeric = spec["fields"]["numeric"]
    flags = spec["fields"]["flags"]
    env: dict[str, Any] = {}
    for name in numeric:
        env[name] = _coerce_number(findings.get(name))
    for name in flags:
        env[name] = _coerce_flag(findings.get(name, False))
    unknown = sorted(set(findings) - set(numeric) - set(flags) - {
        "synthetic_id", "age", "notes", "facility_lat", "facility_lon",
        "phc_name"})
    return env, unknown


def triage(
    findings: dict[str, Any], rules_path: str = str(RULES_PATH)
) -> TriageResult:
    """Run every rule and return the highest urgency that fired.

    Args:
        findings: Structured findings for one woman. Keys must be the
            field names declared in ``rules.yaml``.
        rules_path: Optional path to an alternative rules file.

    Returns:
        The gate result. ``ROUTINE`` means no listed rule fired; it is
        never a statement that the woman is safe.

    """
    spec = load_rules(rules_path)
    env, unknown = build_environment(findings, spec)
    fired: list[FiredRule] = []
    for rule in spec["rules"]:
        if _evaluate(_parse(rule["when"]), env):
            fired.append(
                FiredRule(
                    rule_id=rule["id"],
                    label=rule.get("label", rule["id"]),
                    urgency=rule["urgency"],
                    status=rule["status"],
                    sources=tuple(rule.get("sources", [])),
                    scope_ref=rule.get("scope_ref"),
                    warning=rule.get("warning"),
                    action=rule.get("action"),
                )
            )
    actions = tuple(r for r in fired if r.urgency == "ROUTINE")
    fired = [r for r in fired if r.urgency != "ROUTINE"]
    fired.sort(key=lambda r: -URGENCY_ORDER[r.urgency])
    urgency = fired[0].urgency if fired else "ROUTINE"
    missing = tuple(
        name for name in spec.get("core_inputs", [])
        if math.isnan(env[name]))
    return TriageResult(
        urgency=urgency,
        fired=tuple(fired),
        missing_core_inputs=missing,
        unknown_fields=tuple(unknown),
        rules_version=str(spec["version"]),
        disclaimer=spec["disclaimer"],
        findings=dict(findings),
        actions=actions,
    )


def max_urgency(first: str, second: str) -> str:
    """Return the more urgent of two urgency levels."""
    if URGENCY_ORDER[first] >= URGENCY_ORDER[second]:
        return first
    return second
