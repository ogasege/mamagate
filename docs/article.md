# MamaGate: from danger sign to confirmed arrival, with a Strands agent on Amazon Bedrock AgentCore

*A rules gate and referral relay for community health workers in Nigerian
primary health care. Health focus area.*

**Demo video:** [VIDEO LINK] · **Code:** https://github.com/ogasege/mamagate

> Synthetic demo data. Decision support for trained health workers. Not a
> medical device. The rules have not been reviewed by a clinician.

## The problem

In Nigeria, fewer than half of births have a skilled attendant: 46%
nationally and 10% in Kebbi State (Nigeria Demographic and Health Survey
2023-24). In many rural primary health care centres the person in front of a
pregnant woman is a community health extension worker (CHEW), often alone
and with no doctor on site.

When a danger sign appears, three delays decide what happens next: deciding
to seek care, reaching care, and receiving care. Nigeria's evidence points
at the handover. In a Population Council study at Kano primary health care
centres (Ishaku et al., *Health*, 2013; fieldwork 2010-11), only one in ten
women given pre-referral treatment for severe pre-eclampsia went on to
complete the referral, against 44% of controls. Treatment felt like care,
and the journey to hospital did not happen.

MamaGate is built for that moment. It is used by the CHEW, and it exists for
the woman.

## What MamaGate does

1. **The CHEW enters what she measured.** Blood pressure, pulse, temperature,
   bleeding, symptoms. Anything not measured is left empty, and empty is
   never treated as normal.
2. **A rules gate decides urgency, in code, before any AI runs.** Thirty-five
   danger-sign rules transcribed from Nigeria's 2024 National Standing Orders
   for CHEWs and WHO's *Pregnancy, Childbirth, Postpartum and Newborn Care*
   charts return REFER NOW, WITHIN 24H or ROUTINE in about a millisecond,
   with the source page for every rule that fired.
3. **A Strands agent on Amazon Bedrock AgentCore completes the referral.**
   It chooses the receiving hospital with a real road time from Amazon
   Location Service, writes a structured referral note, has code check the
   note, pre-alerts the hospital through Amazon SNS, and schedules an arrival
   check with Amazon EventBridge Scheduler.
4. **The family gets a plain-language card:** where to go, how long it
   takes, what to bring (money, a companion, a blood donor), and which signs
   mean go at once. Fixed wording, no diagnosis, no doses.
5. **The hospital closes the loop.** The receiving ward sees the referral
   before she arrives. One tap marks her arrived, which deletes the pending
   supervisor alert and tells the clinic. If she never arrives, the
   supervisor is alerted, so a missed referral is noticed instead of lost.

Who is it for? Not a patient self-triage app, on purpose: the gate needs
measurements a woman cannot take at home, a missed alarm at home is exactly
the delay that kills, and only 30% of Nigerian women own a smartphone.
Patient chatbots already exist; the referral handover between two
facilities is the gap.

## Architecture

![MamaGate architecture](https://raw.githubusercontent.com/ogasege/mamagate/main/docs/diagrams/architecture.png)

**Why it is shaped this way:** urgency is decided by code before any model
runs, because it must be deterministic, testable and auditable. The agent
only coordinates the handoff, and the flow ends at a confirmed arrival,
because arrival is the outcome that matters.

![MamaGate referral loop](https://raw.githubusercontent.com/ogasege/mamagate/main/docs/diagrams/referral-loop.png)

**Why a loop:** in Kano only one in ten referred women completed the
referral. A referral that never arrives has to be noticed, so an
EventBridge schedule alerts a supervisor unless the hospital marks her
arrived.

![MamaGate safety layers](https://raw.githubusercontent.com/ogasege/mamagate/main/docs/diagrams/safety-layers.png)

**Why two kinds of guard:** rules that must never fail (dose refusal, tool
order, the urgency floor) are code; judgement calls (tone, diagnosis
wording) go to an LLM reviewer, the same split the workshop teaches with
deterministic and LLM steering.

## Technical execution with the Strands Agents SDK

I followed the workshop's seven modules and kept its patterns, then added
the parts a clinical handoff needs.

- **Agent loop and tools (Module 1).** Nine `@tool` functions bound to a
  per-case context. The docstrings are the model's manual.
- **Hooks (Module 2).** A `BeforeToolCallEvent` lock refuses to run any tool
  without a gate result and rejects dosed tool inputs. The workshop's rate
  limiter caps each tool at three calls. An `AfterToolCallEvent` audit hook
  records every step for the trace view.
- **Skills and steering (Module 3).** The referral procedure is a
  `SKILL.md`. A `SteeringHandler` with `LedgerProvider` enforces the order
  facility → note → verify → pre-alert → arrival check, exactly like the
  workshop's refund workflow. An `LLMSteeringHandler` reviews replies for
  doses, reassurance and diagnosis wording.
- **Sessions (Module 4).** `FileSessionManager` locally and
  `S3SessionManager` on AgentCore.
- **Deploy (Module 5).** `BedrockAgentCoreApp` with an `@app.entrypoint`,
  deployed with the `agentcore` CLI using Direct Code Deploy, traced in
  CloudWatch.
- **Multi-agent (Module 6).** A referral-writer specialist is called as a
  tool and returns typed fields through `structured_output_model`.
- **Evals (Module 7).** `strands_evals` trajectory and output evaluators,
  plus an offline harness with confidence intervals.

## Originality: what goes beyond the workshop

- **Code decides what must never be wrong.** Urgency comes from a
  whitelisted expression interpreter over a YAML rules file, not from a
  model. The agent can raise urgency but never lower it.
- **Locks inside the tools, not only around them.** During testing, a note
  failed verification four times and the pre-alert still went out, because a
  steering decision did not fire for that tool. I moved the rule into the
  tool itself: `send_pre_alert` now refuses to run unless the note passed
  verification, whatever the prompt or the steering does.
- **A closed referral loop across two facilities.** Amazon Location Service
  for road time, Amazon SNS for the pre-alert, Amazon EventBridge Scheduler
  for an arrival check that the hospital cancels when she arrives. Most
  agents end at an answer; this one ends at a confirmed arrival.
- **Honest outputs.** Anything not really sent is labelled `simulated`;
  routing says which provider produced the time; an unknown hospital
  capability is shown as unknown.

## Social impact and how it would be measured

The outcome that matters is **referral completion**: the share of women
referred who arrive at the receiving facility, confirmed by counter-referral.
The Kano baseline is 10% after pre-referral treatment and 44% without. A
pilot would measure completion and time from danger sign to arrival, with
the supervisor alerts as the safety net.

What I can measure tonight, offline:

| Metric | Result | 95% CI |
|---|---|---|
| REFER NOW cases caught by the gate | 24 / 24 | 86–100% |
| WITHIN 24H cases caught | 12 / 12 | 76–100% |
| Routine cases wrongly escalated | 0 / 8 | 0–32% |
| Dose requests refused before any model call | 6 / 6 | 61–100% |
| Dosed model sentences removed | 6 / 6 | 61–100% |

These cases were written from the same guidelines as the rules, so they
measure fidelity to the rules, not clinical accuracy.

## What I learned

1. **Real data found a gap that synthetic cases did not.** I ran the gate
   over 452 unique antenatal readings from the UCI Maternal Health Risk
   dataset. It referred only 38 of 112 "high risk" readings. Most of the rest
   had BP of 140/90 or more with no protein test recorded, or high blood
   sugar. My first fix made both a 24-hour referral; that was stricter than
   WHO and nearly doubled low-risk flags. Following the WHO antenatal care
   decision logic instead, they became follow-up actions (test urine protein
   now; arrange a diabetes assessment) that never change urgency. Now 98 of
   112 get a referral or an action, and emergency referrals stay at 9%.
2. **A measured volume is not a dose.** My first note checker rejected
   "400 ml of blood loss" as a dose and blocked every haemorrhage referral.
   Dose detection now needs a quantity in the same sentence as a drug name
   or an administration word.
3. **An LLM reviewer on every tool call is expensive.** Steering every tool
   call with a second model call made one consultation take twelve minutes
   on AgentCore. Reviewing only replies, and governing tools in code,
   brought it to about thirty to sixty seconds.
4. **Fidelity is not validity.** Without a clinician, my evaluation measures
   whether the code matches the guidelines I transcribed, not whether the
   guidelines were applied well. A clinical review of `rules.yaml` is the
   first step before any pilot.

## Limits

The rules are not clinically reviewed; the receiving hospitals are
synthetic; no health worker or patient has used MamaGate; clinical output is
English only; and its effect on referral completion is unknown until a pilot
measures it.

## Try it

```bash
git clone https://github.com/ogasege/mamagate && cd mamagate
uv sync && uv run pytest && uv run python -m evals.run_eval
uv run uvicorn server:app --port 8899   # then open http://localhost:8899
```

Built with the Strands Agents SDK, Amazon Bedrock AgentCore, Amazon Bedrock,
Amazon Location Service, Amazon SNS, Amazon EventBridge Scheduler and Amazon
S3.
