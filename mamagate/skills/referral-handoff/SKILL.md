---
name: referral-handoff
description: Step-by-step procedure for a REFER_NOW or WITHIN_24H case - choose the receiving facility, draft and verify the referral note, pre-alert the facility and schedule the arrival check.
---
# Referral handoff

Use this skill whenever the code-owned gate returns REFER_NOW or WITHIN_24H.
The gate's urgency is final. You may raise it, never lower it.

1. Call `get_triage_result` and read every fired rule and any warning
   (for example "do not do a vaginal examination").
2. Call `find_receiving_facility`. Prefer a facility whose emergency
   obstetric capability is "yes". If it is "unknown", say so plainly and
   tell the health worker to phone ahead.
3. Call `select_facility` with the chosen facility ID and a short reason.
4. Call `draft_referral_note`. Pass the transport plan and what was told
   to the woman and her companion. Do not include any drug dose.
5. Call `verify_referral_note`. If it fails, fix the listed problems and
   draft again.
6. Call `send_pre_alert` so the receiving facility expects her.
7. Call `schedule_arrival_check` so a supervisor is alerted if her arrival
   is not confirmed. Use 60 minutes for REFER_NOW and 1440 for WITHIN_24H.
8. Reply to the health worker in short numbered steps: what to do now,
   where she is going, how long it takes, and what was sent.
