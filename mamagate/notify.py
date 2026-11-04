"""Pre-alerts and arrival checks for the referral loop.

When configured, the pre-alert is published to an Amazon SNS topic that
the receiving facility subscribes to, and the arrival check is an
Amazon EventBridge Scheduler one-time schedule that publishes to the
same topic if the woman's arrival is not confirmed. Without
configuration both are recorded locally and marked ``simulated`` so the
demo never pretends a message was sent.

Environment:
    MAMAGATE_ALERT_TOPIC_ARN: SNS topic for pre-alerts and reminders.
    MAMAGATE_SCHEDULER_ROLE_ARN: IAM role EventBridge Scheduler assumes
        to publish to the topic.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

LOGGER = logging.getLogger(__name__)
REGION = os.environ.get("AWS_REGION", "us-east-1")


def _topic() -> str | None:
    """Return the configured SNS topic ARN, if any."""
    return os.environ.get("MAMAGATE_ALERT_TOPIC_ARN") or None


def send_pre_alert(note: dict[str, Any]) -> dict[str, Any]:
    """Pre-alert the receiving facility that a referral is on its way."""
    message = (
        f"MamaGate pre-alert {note['referral_id']} ({note['emergency_or_not']}"
        f"): woman {note['synthetic_id']} referred from "
        f"{note['who_is_referring']} to {note['facility']}. Danger signs: "
        f"{', '.join(note['triggering_rule_ids']) or 'none'}. "
        "Synthetic demo message."
    )
    record = {"type": "pre_alert", "to": note["facility"],
              "message": message, "status": "simulated"}
    topic = _topic()
    if topic:
        try:
            import boto3

            response = boto3.client("sns", region_name=REGION).publish(
                TopicArn=topic,
                Subject=f"MamaGate referral {note['referral_id']}"[:100],
                Message=message,
            )
            record.update(status="sent", channel="amazon-sns",
                          message_id=response["MessageId"])
        except Exception as exc:  # noqa: BLE001 - report, never crash
            LOGGER.warning("SNS publish failed: %s", exc)
            record.update(status="failed", error=str(exc))
    return record


def schedule_arrival_check(
    note: dict[str, Any], minutes: int
) -> dict[str, Any]:
    """Schedule a supervisor alert if arrival is not confirmed in time."""
    due = datetime.now(UTC) + timedelta(minutes=minutes)
    record = {"type": "arrival_check", "referral_id": note["referral_id"],
              "due_utc": due.strftime("%Y-%m-%dT%H:%M:%S"),
              "status": "simulated"}
    topic = _topic()
    role = os.environ.get("MAMAGATE_SCHEDULER_ROLE_ARN")
    if topic and role:
        try:
            import boto3

            name = f"mamagate-{note['referral_id']}".replace("_", "-")[:64]
            boto3.client("scheduler", region_name=REGION).create_schedule(
                Name=name,
                ScheduleExpression=f"at({record['due_utc']})",
                FlexibleTimeWindow={"Mode": "OFF"},
                ActionAfterCompletion="DELETE",
                Target={
                    "Arn": topic,
                    "RoleArn": role,
                    "Input": json.dumps({
                        "default": (
                            f"MamaGate arrival check: referral "
                            f"{note['referral_id']} to {note['facility']} "
                            "has no confirmed arrival. Contact the family "
                            "and the receiving facility."),
                    }),
                },
            )
            record.update(status="scheduled",
                          channel="eventbridge-scheduler", name=name)
        except Exception as exc:  # noqa: BLE001 - report, never crash
            LOGGER.warning("Scheduler failed: %s", exc)
            record.update(status="failed", error=str(exc))
    return record


def record_arrival(
    referral_id: str, arrived: bool, details: str = ""
) -> dict[str, Any]:
    """Close the loop: cancel the arrival check and notify the PHC.

    Called by the receiving facility when the woman arrives (or by the
    supervisor when she has not). Deletes the pending EventBridge
    schedule so no false alarm fires, and publishes the outcome.
    """
    name = f"mamagate-{referral_id}".replace("_", "-")[:64]
    record: dict[str, Any] = {
        "type": "arrival", "referral_id": referral_id,
        "arrived": arrived, "details": details,
        "schedule_cancelled": "simulated", "notice": "simulated"}
    topic = _topic()
    if not topic:
        return record
    import boto3

    if arrived:
        try:
            boto3.client("scheduler", region_name=REGION).delete_schedule(
                Name=name)
            record["schedule_cancelled"] = "yes"
        except Exception as exc:  # noqa: BLE001 - may already be gone
            record["schedule_cancelled"] = f"no: {exc.__class__.__name__}"
    status = "ARRIVED" if arrived else "NOT ARRIVED - missed referral"
    try:
        boto3.client("sns", region_name=REGION).publish(
            TopicArn=topic,
            Subject=f"MamaGate {referral_id}: {status}"[:100],
            Message=(f"MamaGate referral {referral_id}: {status}. "
                     f"{details} Synthetic demo message."),
        )
        record["notice"] = "sent"
    except Exception as exc:  # noqa: BLE001 - report, never crash
        record["notice"] = f"failed: {exc}"
    return record
