"""HTTP bridge between the web UI and the MamaGate agent.

``POST /invoke`` forwards the UI payload to the deployed AgentCore
Runtime when ``MAMAGATE_RUNTIME_ARN`` is set (calls are signed with the
server's IAM credentials, which a browser cannot do), and otherwise runs
the agent in-process. ``GET /eval_report.json`` serves the latest
evaluation report.

Run with ``uv run uvicorn server:app --port 8899``.
"""

from __future__ import annotations

import hmac
import json
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from mamagate import notify
from mamagate.agent import run_case

ROOT = Path(__file__).parent


def _load_env(path: Path = ROOT / ".env") -> None:
    """Load KEY=VALUE lines from a local .env without overriding."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_env()
REFERRALS = ROOT / "build" / "referrals.json"

REGION = os.environ.get("AWS_REGION", "us-east-1")
RUNTIME_ARN = os.environ.get("MAMAGATE_RUNTIME_ARN")
EVAL_REPORT = Path(__file__).parent / "evals" / "eval_report.json"

app = FastAPI(title="MamaGate bridge")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get(
        "MAMAGATE_UI_ORIGINS", "http://localhost:8899").split(","),
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


def _invoke_runtime(payload: dict[str, Any]) -> dict[str, Any]:
    """Call the deployed AgentCore Runtime with boto3 (workshop Part 4)."""
    import boto3

    session_id = payload.get("session_id") or str(uuid.uuid4())
    if len(session_id) < 33:
        session_id = (session_id + "-" + uuid.uuid4().hex)[:64]
    from botocore.config import Config

    client = boto3.client(
        "bedrock-agentcore", region_name=REGION,
        config=Config(read_timeout=300, connect_timeout=10,
                      retries={"max_attempts": 1}))
    response = client.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        runtimeSessionId=session_id,
        payload=json.dumps(payload).encode(),
        qualifier="DEFAULT",
    )
    body = b"".join(
        chunk if isinstance(chunk, bytes) else chunk.encode()
        for chunk in response.get("response", []))
    data = json.loads(body.decode("utf-8"))
    data["served_by"] = "agentcore-runtime"
    return data


def require_key(x_api_key: str | None = Header(default=None)) -> None:
    """Require ``X-API-Key`` on writes when MAMAGATE_API_KEY is set.

    The demo server binds to 127.0.0.1. Set MAMAGATE_API_KEY before
    exposing it beyond the local machine; a pilot would use per-facility
    identities (for example Amazon Cognito) instead.
    """
    expected = os.environ.get("MAMAGATE_API_KEY")
    if expected and not hmac.compare_digest(x_api_key or "", expected):
        raise HTTPException(401, "Missing or invalid API key")


def _load_referrals() -> list[dict[str, Any]]:
    """Return stored referrals, newest first."""
    if not REFERRALS.exists():
        return []
    return json.loads(REFERRALS.read_text(encoding="utf-8"))


def _save_referrals(rows: list[dict[str, Any]]) -> None:
    """Persist referrals for the hospital view."""
    REFERRALS.parent.mkdir(exist_ok=True)
    REFERRALS.write_text(json.dumps(rows, indent=2), encoding="utf-8")


@app.post("/invoke", dependencies=[Depends(require_key)])
def invoke(payload: dict[str, Any]) -> dict[str, Any]:
    """Run one consultation through the runtime or locally."""
    if not isinstance(payload.get("case"), dict):
        raise HTTPException(400, "Missing required field: case")
    if RUNTIME_ARN:
        try:
            data = _invoke_runtime(payload)
        except Exception as exc:  # noqa: BLE001 - surface as JSON
            raise HTTPException(
                502, f"Agent unavailable: {exc!s:.200}") from exc
    else:
        try:
            data = run_case(findings=payload["case"],
                            prompt=payload.get("prompt"),
                            phc=payload.get("phc"),
                            session_id=payload.get("session_id"))
        except Exception as exc:  # noqa: BLE001 - surface as JSON
            raise HTTPException(
                502, f"Agent unavailable: {exc!s:.200}") from exc
        data["served_by"] = "local"
    note = data.get("referral_note")
    if note and data.get("note_verified"):
        rows = [r for r in _load_referrals()
                if r["referral_id"] != note["referral_id"]]
        rows.insert(0, {
            "referral_id": note["referral_id"],
            "urgency": note["emergency_or_not"],
            "facility": note["facility"],
            "from": note["who_is_referring"],
            "woman": note["synthetic_id"],
            "sent_at": note["referral_date_time"],
            "danger_signs": note["triggering_rule_ids"],
            "danger_labels": [r["label"] for r in data["triage"]["fired"]],
            "warnings": [r["warning"] for r in data["triage"]["fired"]
                         if r.get("warning")],
            "travel": note.get("travel"),
            "age": note.get("age"),
            "note_markdown": data.get("referral_note_markdown"),
            "status": "expected",
        })
        _save_referrals(rows)
    return data


@app.post("/gate", dependencies=[Depends(require_key)])
def gate(payload: dict[str, Any]) -> dict[str, Any]:
    """Run only the code-owned gate (no model), for an instant result."""
    import time

    from mamagate.triage import triage

    if not isinstance(payload.get("case"), dict):
        raise HTTPException(400, "Missing required field: case")
    started = time.perf_counter()
    result = triage(payload["case"])
    return {"triage": result.to_dict(),
            "gate_ms": round((time.perf_counter() - started) * 1000, 2)}


SPEECH_CACHE = ROOT / "build" / "voice" / "cards"


@app.get("/speak/{language}")
def speak(language: str, urgent: bool = True) -> FileResponse:
    """Return the family card read aloud (Aethex TTS), cached on disk."""
    import hashlib
    import urllib.error
    import urllib.request

    from mamagate.languages import VOICES, speech_text

    if language not in VOICES or VOICES[language][0] is None:
        raise HTTPException(404, "No speech voice for this language")
    text = speech_text(language, urgent)
    key = hashlib.sha256(f"{language}|{text}".encode()).hexdigest()[:16]
    path = SPEECH_CACHE / f"{language}-{key}.wav"
    if not path.exists():
        api_key = os.environ.get("AETHEX_API_KEY")
        if not api_key:
            raise HTTPException(503, "Speech is not configured")
        lang, voice = VOICES[language]
        body = {"text": text, "language": lang}
        if voice:
            body["voice_id"] = voice
        request = urllib.request.Request(
            "https://api.aethexai.com/api/v1/tts",
            data=json.dumps(body).encode(),
            headers={"X-API-Key": api_key,
                     "Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(request, timeout=60) as resp:  # noqa: S310
                audio = resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:200]
            raise HTTPException(502, f"Speech failed: {detail}") from exc
        SPEECH_CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(audio)
    return FileResponse(path, media_type="audio/wav")


@app.get("/referrals")
def referrals() -> list[dict[str, Any]]:
    """List referrals for the receiving-facility view."""
    return _load_referrals()


@app.post("/referrals/{referral_id}/arrival",
          dependencies=[Depends(require_key)])
def arrival(referral_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Record arrival or non-arrival and close the referral loop."""
    rows = _load_referrals()
    row = next((r for r in rows if r["referral_id"] == referral_id), None)
    if row is None:
        raise HTTPException(404, "Unknown referral")
    arrived = bool(body.get("arrived"))
    result = notify.record_arrival(
        referral_id, arrived, str(body.get("details", ""))[:500])
    row.update(status="arrived" if arrived else "not_arrived",
               counter_referral=body.get("counter_referral"),
               closed=result)
    _save_referrals(rows)
    return row


@app.get("/eval_report.json")
def eval_report() -> FileResponse:
    """Serve the latest evaluation report."""
    if not EVAL_REPORT.exists():
        raise HTTPException(404, "Run evals/run_eval.py first")
    return FileResponse(EVAL_REPORT)


@app.get("/external_check.json")
def external_check() -> FileResponse:
    """Serve the real-readings behaviour check."""
    path = EVAL_REPORT.with_name("external_check.json")
    if not path.exists():
        raise HTTPException(404, "Run evals/external_check.py first")
    return FileResponse(path)


UI_DIR = ROOT / "ui"
if UI_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ROOT / "assets"),
              name="assets")
    app.mount("/diagrams",
              StaticFiles(directory=ROOT / "docs" / "diagrams"),
              name="diagrams")
    app.mount("/", StaticFiles(directory=UI_DIR, html=True), name="ui")
