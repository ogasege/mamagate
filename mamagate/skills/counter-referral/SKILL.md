---
name: counter-referral
description: How to request and record a counter-referral, so the receiving facility reports the outcome back to the referring PHC.
---
# Counter-referral

Every referral note ends with a counter-referral request. The receiving
facility is asked to return: record number, admission date and time,
diagnoses, treatments given, recommendations for further care, and the
follow-up date and place.

When the health worker reports that the woman arrived or did not arrive,
call `record_arrival` with the outcome. A woman who has not arrived is a
missed referral, not a closed case: tell the worker to contact the family
and the supervisor.
