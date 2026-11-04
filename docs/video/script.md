# MamaGate demo video script (target 2:45, hard limit under 3:00)

Rules followed: under three minutes; shows the agent working on AWS; no
music; no third-party logos or copyrighted material; synthetic data
labelled on screen. Each narration block is under 650 characters so it
can be voiced in one text-to-speech request.

| # | Time | Screen | Rubric point |
|---|------|--------|--------------|
| 1 | 0:00-0:22 | Title card, then problem card (text only) | Social impact |
| 2 | 0:22-0:50 | UI: load severe pre-eclampsia case, gate fires instantly | Technical, originality |
| 3 | 0:50-1:25 | UI: live handoff on AgentCore, note drawer, family card | Technical, impact |
| 4 | 1:25-1:45 | Hospital tab: mark arrived, schedule cancelled | Originality (closed loop) |
| 5 | 1:45-2:05 | UI: dose request refused in code | Safety, technical |
| 6 | 2:05-2:30 | Architecture card, eval and real-data numbers | Technical, communication |
| 7 | 2:30-2:45 | Limits and what I learned, repo link | Communication |

## Narration

**1. Problem (0:00-0:18)**
In Nigeria, fewer than half of births have a skilled attendant. When a
pregnant woman shows a danger sign, the health worker beside her has to
decide fast, and then get her to hospital. In one Kano study, only one in
ten referred women actually got there. MamaGate is built for that moment.

**2. The gate (0:18-0:38)**
Here's a synthetic case. Thirty-four weeks pregnant, very high blood
pressure, a severe headache. Before any AI runs, a rules gate in plain code
checks thirty-five danger signs from Nigeria's Standing Orders and WHO. The
answer is refer now, in about a millisecond, with zero AI tokens.

**3. The handoff (0:38-1:02)**
Then a Strands agent on Amazon Bedrock AgentCore does the paperwork. It
picks the hospital, with a real road time from Amazon Location Service. It
writes the referral note, and code checks it before anything is sent. Then
it pre-alerts the hospital through Amazon SNS, and sets an arrival check
with EventBridge Scheduler.

**4. The family card (1:02-1:27)**
The family gets a card in plain words: where to go, what to bring, and
when to rush. The wording is fixed in code, never written by the AI, and
it speaks their language.

**5. Closing the loop (1:27-1:40)**
At the hospital, the referral arrives before she does. One tap marks her
arrived, and the supervisor alert is cancelled. If she never arrives,
someone is told.

**6. Safety (1:40-1:52)**
Ask MamaGate for a drug dose, and it refuses, in code, before any model is
called. It points to the right page of the Standing Orders instead.

**7. Proof (1:52-2:12)**
On synthetic cases, the gate caught every refer-now case, and escalated
none of the routine ones. On four hundred and fifty real antenatal
readings, the data showed a gap in blood pressure follow-up. So I added a
WHO aligned test-now step, and measured the change.

**8. Limits and learning (2:12-2:30)**
The rules still need a clinician's review, and the data is synthetic. My
lesson: let code decide what must never be wrong, and let the agent
coordinate around it. MamaGate is open source. Try it.

## Language clips (played inside block 4, after its narration)

Short excerpts of the family card, voiced in each language: headline plus
the first three "go at once" signs. Pidgin, then Hausa, then Yoruba. Igbo is
shown on screen as text only.

## On-screen text cards (no logos)

- Title: "MamaGate · danger-sign gate and referral relay for Nigerian
  primary health care"
- Problem: "46% of births with a skilled attendant (NDHS 2024) · 10% in
  Kebbi · 1 in 10 completed referral after pre-referral treatment (Kano,
  Ishaku et al. 2013)"
- Banner throughout UI shots: "Synthetic demo data. Decision support for
  trained health workers. Not a medical device."
- Architecture: Worker → Rules gate (code) → Strands agent on AgentCore
  (skills, steering, hooks, sessions on S3) → Amazon Location → note
  check → Amazon SNS → EventBridge Scheduler → hospital confirms arrival
- Proof: "24/24 refer-now (95% CI 86–100%) · 0/8 over-referral · 6/6 dose
  requests refused · 452 real readings checked"
- End: repository URL and "Built with Strands Agents SDK on Amazon
  Bedrock AgentCore"
