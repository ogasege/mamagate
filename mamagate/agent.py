"""MamaGate agent: the harness around the code-owned gate.

Layers:

* Tools: ``@tool`` functions bound to a
  per-case :class:`~mamagate.case.CaseContext`.
* Hooks: a gate lock, a dose lock on tool inputs, a rate
  limiter and an audit trail.
* Skills and steering: SKILL.md procedures, a deterministic
  referral-workflow handler and an LLM language guardrail.
* Sessions: file sessions locally, S3 sessions when deployed.
* Multi-agent: a referral-writer specialist used as a tool.

The gate itself (:func:`mamagate.triage.triage`) runs in plain Python
before the agent is created, so urgency never depends on a model.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from strands import Agent, AgentSkills, tool
from strands.agent.conversation_manager import (
    SlidingWindowConversationManager,
)
from strands.hooks import (
    AfterToolCallEvent,
    BeforeInvocationEvent,
    BeforeToolCallEvent,
    HookProvider,
    HookRegistry,
)
from strands.models import BedrockModel
from strands.vended_plugins.steering import (
    Guide,
    LedgerProvider,
    LLMSteeringHandler,
    Proceed,
    SteeringHandler,
    ToolSteeringAction,
)

from mamagate import notify
from mamagate.case import (
    CaseContext,
    build_family_card,
    build_note,
    render_note_markdown,
    verify_note,
)
from mamagate.facilities import rank_facilities
from mamagate.routing import route
from mamagate.safety import (
    contains_drug_dose,
    is_dose_request,
    redact_doses,
)
from mamagate.triage import URGENCY_ORDER, triage

SKILLS_DIR = Path(__file__).parent / "skills"
REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID = os.environ.get("MAMAGATE_MODEL_ID")

SYSTEM_PROMPT = """You are MamaGate, a referral assistant for trained \
Community Health Extension Workers (CHEWs) at Nigerian primary health care \
centres. You support the worker; you do not diagnose and you never give \
drug doses.

Hard rules:
- A code-owned danger-sign gate has already set the urgency. Treat it as \
final. You may raise urgency with raise_urgency, never lower it.
- Never give a drug dose, route or frequency. Point the worker to the page \
of their National Standing Orders instead.
- Never say the woman is "safe" or "fine". For ROUTINE say no listed \
danger sign was found in what was measured.
- If a core vital was not measured, ask the worker to measure it.
- Never state a diagnosis. Describe what was found: write "signs of severe \
pre-eclampsia", never "she has severe pre-eclampsia".
- If the gate lists follow-up actions (for example test urine protein), \
tell the worker to do them now, first.
- For REFER_NOW or WITHIN_24H, activate the referral-handoff skill and \
follow it to the end. Use the birth-preparedness skill for the transport \
plan.
- Reply in short numbered steps, plain English, under 180 words."""

WRITER_PROMPT = """You write the narrative fields of an obstetric referral \
note for a Nigerian primary health care centre. You receive the code-owned \
danger signs, findings, destination and route. Write plainly and \
specifically. Never include a drug name with a dose, and never write that \
the woman is safe. Do not diagnose: describe the danger signs that were \
found."""

LANGUAGE_GUARDRAIL = """You review replies written for a community health \
worker caring for a pregnant or postpartum woman. Ask for a revision if \
the reply: gives any drug dose, route or frequency; says or implies the \
woman is safe, fine or low risk; states a diagnosis as fact (for \
example "she has pre-eclampsia" instead of "signs of pre-eclampsia"); \
lowers or \
softens the urgency it was given; or uses jargon a CHEW would not use. \
Otherwise approve it."""


class NoteNarrative(BaseModel):
    """Narrative fields the writer specialist must return."""

    main_reasons_for_referral: str = Field(
        description="Danger signs found and why she needs this facility.")
    transport_plan: str = Field(
        description="Who takes her, how, with whom, money and blood donor.")
    information_given_to_woman_and_companion: str = Field(
        description="What was explained to the woman and her companion.")


# --------------------------------------------------------------------------
# specialist agent used as a tool
# --------------------------------------------------------------------------
def _model() -> BedrockModel:
    """Return the Bedrock model, defaulting to the Strands default."""
    if MODEL_ID:
        return BedrockModel(model_id=MODEL_ID, region_name=REGION)
    return BedrockModel(region_name=REGION)


def write_narrative(ctx: CaseContext, guidance: str) -> NoteNarrative:
    """Ask the referral-writer specialist for the note's narrative."""
    writer = Agent(
        model=_model(),
        system_prompt=WRITER_PROMPT,
        callback_handler=None,
    )
    facts = {
        "urgency": ctx.urgency,
        "danger_signs": [r.label for r in ctx.triage.fired],
        "warnings": [r.warning for r in ctx.triage.fired if r.warning],
        "findings": ctx.triage.findings,
        "destination": (ctx.facility or {}).get("name"),
        "destination_emonc": (ctx.facility or {}).get("emonc"),
        "route": (ctx.facility or {}).get("route"),
        "worker_guidance": guidance,
    }
    result = writer(
        "Write the referral narrative for this case:\n"
        + json.dumps(facts, default=str),
        structured_output_model=NoteNarrative,
    )
    return result.structured_output


# --------------------------------------------------------------------------
# tools bound to the case
# --------------------------------------------------------------------------
def make_tools(ctx: CaseContext) -> list:
    """Create the tool set for one consultation."""

    @tool
    def get_triage_result() -> str:
        """Return the code-owned danger-sign gate result for this woman.

        Call this first. The urgency in it is final unless raised.
        """
        data = ctx.triage.to_dict()
        data["current_urgency"] = ctx.urgency
        return json.dumps(data)

    @tool
    def raise_urgency(level: str, reason: str) -> str:
        """Raise the case urgency when the worker reports a new concern.

        Args:
            level: REFER_NOW or WITHIN_24H.
            reason: What the worker observed.

        """
        if level not in URGENCY_ORDER:
            return "Unknown level. Use REFER_NOW or WITHIN_24H."
        return ctx.raise_urgency(level, reason)

    @tool
    def find_receiving_facility() -> str:
        """Rank receiving facilities by capability and travel time.

        Returns up to three candidates with a routed travel time when
        a routing provider is available, or a labelled estimate.
        """
        ranked = rank_facilities(ctx.phc_lat, ctx.phc_lon, ctx.urgency)
        for row in ranked:
            row["route"] = route((ctx.phc_lat, ctx.phc_lon),
                                 (row["lat"], row["lon"]))
        ctx.candidates = ranked
        return json.dumps(ranked)

    @tool
    def select_facility(facility_id: str, reason: str) -> str:
        """Choose the receiving facility from the ranked candidates.

        Args:
            facility_id: The facility_id of one ranked candidate.
            reason: Why this facility was chosen.

        """
        for row in ctx.candidates:
            if row["facility_id"] == facility_id:
                ctx.facility = row
                ctx.events.append(f"selected {facility_id}: {reason}")
                return f"Selected {row['name']}."
        raise ValueError("facility_id is not one of the ranked candidates")

    @tool
    def draft_referral_note(guidance: str = "") -> str:
        """Draft the structured referral note with the writer specialist.

        Args:
            guidance: Anything the worker said about transport, money,
                the companion or what the woman was told.

        """
        narrative = write_narrative(ctx, guidance).model_dump()
        cleaned = {}
        for key, value in narrative.items():
            cleaned[key], _ = redact_doses(value)
        ctx.note = build_note(ctx, cleaned)
        ctx.note_verified = False
        return render_note_markdown(ctx.note)

    @tool
    def verify_referral_note() -> str:
        """Check the drafted note in code before anything is sent."""
        problems = verify_note(ctx)
        ctx.note_verified = not problems
        if problems:
            ctx.events.append("verify problems: " + "; ".join(problems))
            raise ValueError("Note failed checks: " + "; ".join(problems))
        return "Referral note passed all checks."

    @tool
    def send_pre_alert() -> str:
        """Pre-alert the receiving facility that the woman is coming."""
        if ctx.urgency == "ROUTINE":
            raise ValueError("No referral: the gate found no danger sign.")
        if ctx.note is None or not ctx.note_verified:
            raise ValueError(
                "Blocked in code: the referral note has not passed "
                "verify_referral_note. Fix the note and verify it first.")
        record = notify.send_pre_alert(ctx.note)
        ctx.outbox.append(record)
        return json.dumps(record)

    @tool
    def schedule_arrival_check(minutes: int) -> str:
        """Alert the supervisor if arrival is not confirmed in time.

        Args:
            minutes: Minutes until the check fires.

        """
        if not any(r["type"] == "pre_alert" for r in ctx.outbox):
            raise ValueError(
                "Blocked in code: send_pre_alert must succeed first.")
        record = notify.schedule_arrival_check(ctx.note, int(minutes))
        ctx.outbox.append(record)
        return json.dumps(record)

    @tool
    def record_arrival(arrived: bool, details: str = "") -> str:
        """Record whether the woman reached the receiving facility.

        Args:
            arrived: True if her arrival was confirmed.
            details: Counter-referral details or what is known.

        """
        status = "arrived" if arrived else "NOT ARRIVED - missed referral"
        ctx.outbox.append({"type": "arrival", "status": status,
                           "details": details})
        return status

    return [get_triage_result, raise_urgency, find_receiving_facility,
            select_facility, draft_referral_note, verify_referral_note,
            send_pre_alert, schedule_arrival_check, record_arrival]


# --------------------------------------------------------------------------
# hooks
# --------------------------------------------------------------------------
class GateAndDoseLockHook(HookProvider):
    """Refuse to run without a gate result, and refuse dosed tool inputs."""

    def __init__(self, ctx: CaseContext) -> None:
        """Bind the hook to the case."""
        self.ctx = ctx

    def register_hooks(self, registry: HookRegistry) -> None:
        """Register the lock on every tool call."""
        registry.add_callback(BeforeToolCallEvent, self.check)

    def check(self, event: BeforeToolCallEvent) -> None:
        """Cancel tool calls that break the gate or dose rules."""
        if self.ctx.triage is None:
            event.cancel_tool = "No gate result. Run the danger-sign gate."
            return
        payload = json.dumps(event.tool_use.get("input", {}))
        if contains_drug_dose(payload) and "draft_referral_note" == (
                event.tool_use["name"]):
            event.cancel_tool = (
                "Tool input contains a drug dose. Remove it; MamaGate "
                "never records or passes on doses.")


class RateLimiterHook(HookProvider):
    """Cap each tool at ``max_calls`` per invocation ."""

    def __init__(self, max_calls: int = 3) -> None:
        """Set the per-tool limit."""
        self.max_calls = max_calls
        self.counts: dict[str, int] = {}

    def register_hooks(self, registry: HookRegistry) -> None:
        """Register reset and check callbacks."""
        registry.add_callback(BeforeInvocationEvent, self.reset)
        registry.add_callback(BeforeToolCallEvent, self.check)

    def reset(self, event: BeforeInvocationEvent) -> None:
        """Reset counts at the start of each invocation."""
        self.counts = {}

    def check(self, event: BeforeToolCallEvent) -> None:
        """Cancel a tool call once the limit is exceeded."""
        name = event.tool_use["name"]
        self.counts[name] = self.counts.get(name, 0) + 1
        if self.counts[name] > self.max_calls:
            event.cancel_tool = (
                f"'{name}' hit the {self.max_calls}-call limit. "
                "Do NOT call this tool again.")


class AuditHook(HookProvider):
    """Record every tool call and its status for the trace view."""

    def __init__(self, ctx: CaseContext) -> None:
        """Bind the hook to the case."""
        self.ctx = ctx

    def register_hooks(self, registry: HookRegistry) -> None:
        """Register the audit callback."""
        registry.add_callback(AfterToolCallEvent, self.record)

    def record(self, event: AfterToolCallEvent) -> None:
        """Append the tool name and outcome to the case events."""
        status = event.result.get("status", "unknown")
        self.ctx.events.append(f"tool {event.tool_use['name']}: {status}")


# --------------------------------------------------------------------------
# steering
# --------------------------------------------------------------------------
def _succeeded(calls: list[dict], name: str) -> bool:
    """Return True if a tool succeeded earlier in this invocation."""
    return any(c["tool_name"] == name and c["status"] == "success"
               for c in calls)


class ReferralWorkflowHandler(SteeringHandler):
    """Enforce the referral order: facility, note, verify, alert, check."""

    name = "referral-workflow"

    PREREQUISITES = {
        "draft_referral_note": ["find_receiving_facility",
                                "select_facility"],
        "send_pre_alert": ["draft_referral_note", "verify_referral_note"],
        "schedule_arrival_check": ["send_pre_alert"],
    }

    def __init__(self, ctx: CaseContext) -> None:
        """Bind the handler to the case and enable the tool ledger."""
        super().__init__(context_providers=[LedgerProvider()])
        self.ctx = ctx

    async def steer_before_tool(
        self, *, agent: Agent, tool_use: dict, **kwargs: Any
    ) -> ToolSteeringAction:
        """Block referral steps that run out of order."""
        action = self._decide(tool_use)
        self.ctx.events.append(
            f"steering {tool_use.get('name')}: {type(action).__name__}")
        return action

    def _decide(self, tool_use: dict) -> ToolSteeringAction:
        """Return the steering decision for one tool call."""
        name = tool_use.get("name")
        if name in {"send_pre_alert", "schedule_arrival_check"} and (
                self.ctx.urgency == "ROUTINE"):
            return Guide(reason=(
                "The gate found no listed danger sign, so there is no "
                "referral to send. If the worker is concerned, call "
                "raise_urgency with the reason first."))
        needed = self.PREREQUISITES.get(name)
        if not needed:
            return Proceed(reason="No prerequisite for this tool")
        ledger = self.steering_context.data.get("ledger", {})
        calls = ledger.get("tool_calls", [])
        for prerequisite in needed:
            if not _succeeded(calls, prerequisite):
                return Guide(reason=(
                    f"You must call {prerequisite} successfully before "
                    f"{name}."))
        if name == "send_pre_alert" and not self.ctx.note_verified:
            return Guide(reason="The note has not passed verification.")
        return Proceed(reason="Referral workflow order validated")


class LanguageGuardrailHandler(LLMSteeringHandler):
    """LLM review of each reply for doses, reassurance and jargon."""

    name = "language-guardrail"

    def __init__(self) -> None:
        """Configure the reviewing prompt."""
        super().__init__(system_prompt=LANGUAGE_GUARDRAIL)

    async def steer_before_tool(
        self, *, agent: Agent, tool_use: dict, **kwargs: Any
    ) -> ToolSteeringAction:
        """Skip tool calls; the deterministic handler governs those.

        Reviewing every tool call with a second model call made one
        consultation take over ten minutes on AgentCore. Only the
        model's replies are reviewed.
        """
        return Proceed(reason="Tool calls are governed in code")


# --------------------------------------------------------------------------
# sessions
# --------------------------------------------------------------------------
def _writable_session_dir() -> str:
    """Return ./sessions if writable, else a temp directory."""
    local = Path("./sessions")
    try:
        local.mkdir(exist_ok=True)
        return str(local)
    except OSError:
        import tempfile

        return str(Path(tempfile.gettempdir()) / "mamagate-sessions")


def _session_manager(session_id: str | None):
    """Return an S3 or file session manager, or None without an ID."""
    if not session_id:
        return None
    bucket = os.environ.get("MAMAGATE_SESSION_BUCKET")
    if bucket:
        from strands.session.s3_session_manager import S3SessionManager

        return S3SessionManager(session_id=session_id, bucket=bucket,
                                prefix="sessions/", region_name=REGION)
    from strands.session.file_session_manager import FileSessionManager

    return FileSessionManager(
        session_id=session_id,
        storage_dir=os.environ.get("MAMAGATE_SESSION_DIR",
                                   _writable_session_dir()))


def build_agent(ctx: CaseContext, session_id: str | None = None) -> Agent:
    """Assemble the agent harness for one case."""
    plugins: list = [AgentSkills(skills=[str(SKILLS_DIR)]),
                     ReferralWorkflowHandler(ctx)]
    if os.environ.get("MAMAGATE_LLM_STEERING", "1") == "1":
        plugins.append(LanguageGuardrailHandler())
    return Agent(
        model=_model(),
        tools=make_tools(ctx),
        system_prompt=SYSTEM_PROMPT,
        hooks=[GateAndDoseLockHook(ctx), RateLimiterHook(max_calls=3),
               AuditHook(ctx)],
        plugins=plugins,
        conversation_manager=SlidingWindowConversationManager(
            window_size=30),
        session_manager=_session_manager(session_id),
        callback_handler=None,
    )


# --------------------------------------------------------------------------
# Entry point used by main.py, chat.py and the evals
# --------------------------------------------------------------------------
def _instruction(ctx: CaseContext, prompt: str | None) -> str:
    """Compose the turn prompt from the gate result and the worker."""
    gate = ctx.triage
    lines = [
        f"Code-owned gate result: {gate.headline}.",
        f"PHC: {ctx.phc_name}.",
    ]
    for action in gate.actions:
        lines.append(f"Follow-up action ({action.rule_id}): {action.action}")
    if gate.urgency == "ROUTINE":
        lines.append("Give the follow-up actions first, then a short "
                     "birth-preparedness reminder.")
    else:
        lines.append("Complete the referral handoff now.")
    if prompt:
        lines.append(f"Health worker says: {prompt}")
    return "\n".join(lines)


def run_case(
    findings: dict[str, Any],
    prompt: str | None = None,
    phc: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Run one consultation: code gate first, then the agent.

    Args:
        findings: Structured findings (see ``rules.yaml`` fields).
        prompt: Optional free text from the health worker.
        phc: Optional ``name``, ``lat`` and ``lon`` of the PHC.
        session_id: Optional ID to persist the conversation.

    Returns:
        Gate result, agent reply, referral note, outbox and timings.

    """
    started = time.perf_counter()
    gate = triage(findings)
    gate_ms = round((time.perf_counter() - started) * 1000, 2)
    phc = phc or {}
    ctx = CaseContext(
        triage=gate,
        phc_name=phc.get("name", "Synthetic PHC (demo)"),
        phc_lat=float(phc.get("lat", 11.95)),
        phc_lon=float(phc.get("lon", 8.49)),
    )
    result: dict[str, Any] = {"triage": gate.to_dict(), "gate_ms": gate_ms}

    if prompt and is_dose_request(prompt):
        scope = next((r.scope_ref for r in gate.fired if r.scope_ref), None)
        from mamagate.safety import refusal

        result.update(
            reply=refusal(scope) + f" Current urgency: {gate.urgency}.",
            dose_request_blocked=True, model_called=False,
            referral_note=None, outbox=[], events=[])
        return result

    agent_started = time.perf_counter()
    response = None
    for attempt in range(3):
        agent = build_agent(ctx, session_id)
        try:
            response = agent(_instruction(ctx, prompt))
            break
        except Exception as exc:  # noqa: BLE001 - transient model errors
            transient = any(word in str(exc) for word in (
                "serviceUnavailable", "ThrottlingException",
                "unable to process", "ModelNotReady"))
            if not transient or attempt == 2:
                raise
            ctx.events.append(f"model retry {attempt + 1}: {exc!s:.80}")
            time.sleep(2 * (attempt + 1))
    reply, redacted = redact_doses(str(response).strip())
    usage = response.metrics.accumulated_usage
    result.update(
        reply=reply,
        doses_redacted=redacted,
        dose_request_blocked=False,
        model_called=True,
        urgency=ctx.urgency,
        referral_note=ctx.note,
        referral_note_markdown=(render_note_markdown(ctx.note)
                                if ctx.note else None),
        note_verified=ctx.note_verified,
        family_card=(build_family_card(ctx.note)
                     if ctx.note and ctx.note_verified else None),
        outbox=ctx.outbox,
        events=ctx.events,
        agent_ms=round((time.perf_counter() - agent_started) * 1000),
        tokens=usage.get("totalTokens"),
        cycles=response.metrics.get_summary().get("total_cycles"),
    )
    return result
