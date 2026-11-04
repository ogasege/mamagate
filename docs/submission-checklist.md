# Submission checklist and design rationale

Every requirement and judging criterion of *Strands SDK: Workshop to Ship*,
with the evidence in this repository and the reason behind each choice.

## Qualification (pass/fail)

| Requirement | Evidence | Status |
|---|---|---|
| Workshop completed in the window | "Building AI Agents with Strands SDK: From Simple Loops to Multi-Agent Swarms", completed 4 Nov 2026 | Done |
| Agent built with the Strands Agents SDK | `mamagate/agent.py` (`strands.Agent`, `@tool`, hooks, steering, skills, sessions) | Done |
| Addresses a real-world social good challenge | Maternal referral completion in Nigeria, Health focus area | Done |
| Working agent on AWS | Deployed to Amazon Bedrock AgentCore Runtime (`MamaGateDeploy/`) | Done |
| Project article on Builder Center | Draft in `docs/article.md` | Publish |
| Public repository with source code, OSI licence | github.com/ogasege/mamagate, Apache-2.0 | Done |
| Public demo video under three minutes | `build/video/mamagate-demo.mp4` (render), upload to YouTube | Upload |
| No third-party trademarks or copyrighted music | Own logo and slides, no music, synthetic hospitals | Done |
| Original agent, not published before | Built for this hackathon | Done |

## Judging criteria

### Social impact (25%): measurable improvement for underserved populations

| What | Why |
|---|---|
| Target: the referral handover, not diagnosis | In Kano, only 1 in 10 women given pre-referral treatment completed referral (Ishaku et al., 2013). The gap is the journey and the handover. |
| User: the CHEW; beneficiary: the woman | The gate needs measured vitals a woman cannot take at home, and 30% of Nigerian women own a smartphone. The health worker is who is present when a danger sign appears. |
| Family card in English, Pidgin, Hausa, Yoruba, Igbo | The family must act on the referral; fixed wording in their language removes a barrier without risking a model-generated mistake. |
| Hospital confirms arrival | Turns "referred" into "arrived", the outcome that matters, and makes a missed referral visible. |
| Measurable outcome for a pilot | Referral completion rate and time from danger sign to arrival, against the Kano baselines (10% and 44%). |
| What we measured tonight | Gate fidelity on 44 synthetic cases with Wilson intervals; behaviour on 452 real antenatal readings. |

### Technical execution (25%): how well it is built with Strands and how well it works

| What | Why |
|---|---|
| Tools, hooks, skills, steering, sessions, agents as tools, AgentCore deployment, evals | Each layer has one job, so each can be tested and reasoned about separately. |
| Gate in plain Python before any model call | Urgency must be deterministic, testable and auditable; it runs in about 1 ms with zero tokens. |
| Whitelisted expression interpreter for `rules.yaml` | Rules are data a clinician can review, and nothing in the file can execute code. |
| Code locks inside the tools as well as steering | In testing, steering did not fire for one tool and an unverified pre-alert went out. Locks in the tools make the order hold regardless. |
| LLM steering only on replies | Reviewing every tool call with a second model took 12 minutes per case; tools are governed in code instead. |
| `S3SessionManager` on AgentCore | The runtime file system is read-only; S3 is the right store for production. |
| 45 unit tests, ruff-clean, offline evals | Behaviour is checked without AWS, so anyone can verify it in seconds. |

### Communication quality (25%): article and video explain agent, problem and learning

| What | Why |
|---|---|
| Three flow diagrams (`docs/diagrams/`) | Consistent visual language, so the architecture reads at a glance. |
| Video follows the user's journey: problem → gate → handoff → family → hospital → safety → proof → limits | One story, every rubric point, under three minutes. |
| "What I learned" grounded in real failures | Four concrete lessons, each from something that broke and was fixed. |
| Honest limits on every screen and in the article | Builds trust; avoids over-claiming clinical validity. |

### Originality (25%): architecture, novel AWS use, how far it goes

| What | Why |
|---|---|
| Closed referral loop across two facilities | Most agents end at an answer; MamaGate ends at a confirmed arrival. No other entry covers maternal health or Nigeria. |
| Amazon Location Service, Amazon SNS, Amazon EventBridge Scheduler, Amazon S3 | Each solves a step of the handover: road time, pre-alert, arrival check, persistence. None is decoration. |
| Urgency floor (raise only) and dose refusal before the model | Safety properties enforced in code, demonstrated live. |
| Real-data check that changed the rules | Synthetic tests could not find the blood-pressure follow-up gap; real readings did, and the fix follows WHO. |

## Key design decisions

1. **Code decides what must never be wrong; the agent coordinates.**
   Urgency, dose refusal, tool order and the family-card wording are code.
   Choosing a hospital, writing the narrative and talking to the worker are
   the agent's job.
2. **Missing is never normal.** An empty vital cannot fire or clear a rule;
   it is listed as "not measured".
3. **Follow WHO where the data disagreed with our first fix.** Raised BP
   without protein became "test urine protein now", not a referral.
4. **Never pretend.** Anything not really sent is labelled `simulated`;
   unknown hospital capability is shown as unknown; synthetic data is
   labelled on every screen.
