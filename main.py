"""Amazon Bedrock AgentCore Runtime entrypoint for MamaGate.

Wraps the agent in
``BedrockAgentCoreApp`` with an ``@app.entrypoint`` handler. The
payload carries the structured findings; the code gate runs first.

Payload::

    {"case": {...findings...}, "phc": {...}, "prompt": "...",
     "session_id": "..."}
"""

from __future__ import annotations

from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from mamagate.agent import run_case

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle one AgentCore invocation and return JSON."""
    findings = payload.get("case")
    if not isinstance(findings, dict) or not findings:
        raise ValueError("Missing required field: case (structured findings)")
    session_id = payload.get("session_id") or getattr(
        context, "session_id", None)
    return run_case(
        findings=findings,
        prompt=payload.get("prompt"),
        phc=payload.get("phc"),
        session_id=session_id,
    )


if __name__ == "__main__":
    app.run()
