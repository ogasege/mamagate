# Competitor review: Strands SDK "Workshop to Ship" (read 4 Nov 2026)

About 100 projects were listed. I read 8 articles in full: JagaSungai, CareBridge AI, Emerald,
Yorisoi, Saklolo, Proof of Loss, MedClear and Brownout. I skimmed NALAM AI, Sukoon and Baadhi Saathi
(their text was cut off when read). The rest are covered only by their card summaries.
Likes are low everywhere (0 to 2), so the judges will not be swayed by popularity.

## 1. Project by project

| Project | Problem / user | Strands features | AWS beyond Bedrock | Safety pattern | Eval / headline numbers | Notable / clever |
|---|---|---|---|---|---|---|
| **JagaSungai** (Malaysia flood) | Flood coordinator for cut-off Orang Asli villages | Graph with 7 nodes, only one of which calls a model; conditional edge to skip quiet cycles; structured_output_model; verifier loop with `reset_on_revisit` (max 3 tries) then a fallback template; ApprovalGate hook (`BeforeNodeCallEvent` interrupt); DispatchGuard hook (`BeforeToolCallEvent`, `cancel_tool`); S3SessionManager to resume after an interrupt; ScriptedModel for offline tests | AgentCore Runtime + Observability, EventBridge Scheduler → Lambda, S3, End User Messaging (WhatsApp), SNS, SAM | "Model decides how to say it, code decides what is true"; actions come from a fixed library; never says "safe" | 77/77 classification, 33/33 injected hallucinations caught, 32/32 red-team attacks blocked, 181/192 replay cycles needed no model call | Honest "What I actually ran" section (the agent itself was not deployed, and the evals use a stand-in model); "challenges where my evals caught me"; YAML onboarding; 5-minute "try it" commands |
| **Emerald** (vet phone line, India) | Smallholder with a sick animal → vet | Graph with a custom MultiAgentBase verifier node and a loop; BidiAgent voice on Nova Sonic; hook interrupt that survives a restart; two model families (Nova drafts, Llama reviews); 7 MCP servers; offline lane on Ollama | AgentCore Runtime, **AgentCore Gateway** (MCP), **AgentCore Policy (Cedar)**, S3 Object Lock hash chain | Ed25519 signature over the exact tool arguments, single-use; doses computed in code from quoted rows; models cite sentence numbers and code fills in the words; triage rules run in code first; outbreak cluster detector in code | Pre-registered targets; 0/15 attacks succeeded, 0 misquotes, 0 doses told to a farmer, sign recall 1.0 (cloud) vs 0.90 (offline), about $0.003 per case | **Closest to our idea in structure** (triage → evidence → professional signs off → community warning). The strongest entry on health engineering |
| **Saklolo** (Philippine typhoon rescue pleas) | Dispatcher sorting Taglish rescue pleas | Graph of StepNodes (MultiAgentBase) over a typed `invocation_state`; Swarm only when confidence is low; typed verdict tool; set_max_node_executions and timeouts | **AgentCore Memory** (learns from dispatcher corrections), Amazon Location Places, Titan embeddings, Cognito, API GW, Lambda, SQS FIFO, DynamoDB, CloudFront, Terraform | "Agents may raise priority, only a human may lower it" (raise-only escalation enforced in code); phone numbers masked before the model sees them | Against a keyword baseline on a 150-message storm: critical recall 100% vs 91.2%, precision 89.5%, recycled posts 8/8 vs 4/8, median 4.0 s, about $4 per 10k messages | Baseline comparison; a per-case "how the agents decided" trace; live site; explains why each tool was chosen |
| **Proof of Loss** (crop insurance, India) | Farmer filing a claim within 72 hours | 5 @tools; AgentSkills (one SKILL.md per cause of loss); **SteeringHandler PacketGate** checklist; AuditTrail hook whose log is printed in the packet; claim ID used as the AgentCore session ID | AgentCore Runtime, Lambda, CloudFront, S3 presigned POST, DynamoDB, **Transcribe hi-IN**, CDK | Steering as a legal checklist, with an override only a human can trigger; never promises money | 14 scripted claims against the real model; 12/14 at first, then 14/14 and 96/96 checks; reports its own failures | A workshop-module → "where I took it" table; the deliverable (a printable bilingual packet) is the real outcome |
| **Brownout** (city website in a disaster) | Residents on weak networks | Agents-as-tools (Curator); PublishGuard hook (code checks, then a Verifier agent); retry with exact feedback | AgentCore Runtime, EventBridge, Lambda, S3, **CloudFront KeyValueStore + CloudFront Functions** | Facts only from one JSON file; an unsafe shelter is blocked in code; the old page stays live if checks fail | 3-way comparison (strip vs agent vs agent+guard): 0/6, 13/18, 18/18; load times on emulated 3G/2G | Novel use of an AWS service (the edge), with clear baselines |
| **Yorisoi** (Japan, medicine reminders) | Older adult living alone | @tools, a safety HookProvider (tool-call caps), multimodal image of the medicine bag | AgentCore Runtime, DynamoDB, **EventBridge Scheduler → SNS with no Lambda** (a dead-man switch), Polly | Prompt rules plus hard caps in a hook | 10/10 risky questions answered safely (small set) | Event-driven "alert only if the dose was missed" pattern; designed for listening |
| **CareBridge AI** (post-discharge, families) | Families of older patients | 4 specialist agents with Pydantic output; agents-as-tools (not on the request path) | CloudFront, S3, EC2 Graviton, Textract, SQS, CloudWatch, SNS, Budgets, CDK | Deterministic, versioned policy sets the alert level and the model only writes the wording; "insufficient information" before any model call; consent scoped per caregiver | No numeric eval shown | Consent and permission model; "unavailable" and "insufficient" treated as first-class states |
| **MedClear** (medicine labels, Sri Lanka) | Low-literacy patients, 3 languages | Regex rules → triage agent → main agent → output check; a tool-cap hook | — | 4 layers; refuses if unsure | Reports held-out and fresh cases honestly (rules alone: 0/6 → 12/12 with the triage agent) | Honest about tuning vs held-out results |
| NALAM AI, UyirKaappan, CareNest, Marunthu, MedGuide, Swasthya, CareAgent | Tamil/Indic health, medication, first aid | Mostly a single agent plus tools; a "code-owned 108 emergency gate" | Few | An emergency gate in code before the model | Mostly small or no evals | Very crowded lane; they look alike |
| Sukoon (Pakistan mental health) | Students and the public → therapists | Multi-agent with a triage agent | — | Risk detection → hand-off to a human | — | Strong evidence table; about $13/month running cost |
| Baadhi Saathi (Nepal flood) | Household SMS | Steering, hook, session memory, evals | SNS | Code owns flood level and safe places | — | Close to the household flood example |

## 2. Patterns everyone uses (now table stakes; no extra points)
- A code-owned emergency gate or red-flag rules that run before any model call.
- "Decision in code, wording in the model."
- Statements like "decision support only", "synthetic data" and "not clinically validated".
- A bilingual or local-language interface.
- A small hand-written safety eval (10 to 50 cases) with a 100% pass headline.
- A table mapping each workshop module to where the project went beyond it.
- Deployment to AgentCore Runtime with Bedrock Nova Lite or Nova 2 Lite.

## 3. What the top entries do that others don't
1. **Enforcement that survives prompt failure, deeper than a hook.** Emerald signs tool arguments; JagaSungai's guard re-reads stored state on every send; Saklolo enforces raise-only priority; Proof of Loss allows an override only from the human in the UI.
2. **Human-in-the-loop as a persisted graph interrupt** that resumes in another process or person (JagaSungai, Emerald).
3. **Comparison against a baseline**: keyword baseline (Saklolo); strip vs agent vs guarded agent (Brownout).
4. **Red-team and injected-error evals** that report the failure first and then the fix (JagaSungai 33/33 and 32/32; Emerald's pre-registered targets).
5. **AWS services used for a real reason, not decoration**: AgentCore Memory as a correction loop, Gateway plus Cedar Policy, CloudFront KVS, a Scheduler→SNS dead-man switch, S3 Object Lock, Amazon Location, Transcribe.
6. **Honest "what I actually ran" and "what this doesn't show" sections**, plus a "my evals caught my bugs" section in the lessons learned.
7. **A tangible artefact**: a claim packet, a WhatsApp brief, a sub-1 KB page, or a dispatch queue.
8. **A 5-minute "try it" path**: one-command tests that run offline with a scripted or stand-in model.

## 4. Gaps, and recommendations for our maternal CHEW agent

What nobody has covered: maternal or obstetric care; Nigeria or Africa; Hausa, Yoruba or Pidgin; a **referral handoff to the receiving facility**; **community health worker supervision**; and **cost and transport barriers**.

Recommendations by rubric criterion:

**Social impact**
1. Make the user a CHEW or JCHEW and the outcome a specific workflow: "danger sign → referral decision → referral note → facility pre-alert → follow-up within 24 hours". Measure the things a pilot would measure: time from intake to referral note, red-flag recall, over-referral rate, and the share of referrals with a complete handoff.
2. Cover the "three delays", not only the first. Delay 2 (reaching care): transport plan and community emergency-transport contact. Delay 3 (receiving care): a structured referral note so the woman is not re-triaged on arrival. Nobody else has this.

**Technical execution**
3. Use a Graph: `intake (structured_output)` → `redflag_rules (code node)` → `protocol_lookup (agent with cited sentence IDs; code fills in the text, as Emerald does)` → `referral_writer` → `verifier (code: every vital sign, gestational age and number must match the intake)` → `handoff`. Loop back to the writer on failure, then fall back to a code template.
4. Make safety stronger than a hook:
   - Urgency can only be raised, never lowered, by a model (Saklolo's pattern).
   - Doses are never shown unless quoted verbatim from a protocol row.
   - A supervisor-approval interrupt before a "manage locally / do not refer" outcome, persisted with S3SessionManager.
5. Build an eval with a baseline:
   - 60 or more synthetic vignettes, held out and frozen before tuning.
   - Compare against an "LLM-only prompt" baseline.
   - Report red-flag recall with a confidence interval and over-referral side by side.
   - Add injected-error cases for the verifier and red-team cases (requests for doses, "she's fine, skip referral", prompt injection hidden in notes).

**Originality and AWS services**
6. Add one or two AWS services that each have a real reason:
   - **EventBridge Scheduler → SNS follow-up dead-man switch**: if the CHEW doesn't confirm arrival or follow-up within X hours, alert the supervisor.
   - **AgentCore Memory** for supervisor corrections, which feed back into later triage.
   - Optionally, AgentCore Gateway plus Cedar to deny dose tools.
   - Optionally, Amazon Location to find the nearest facility.
7. The artefact: a printable or SMS **referral note**, in English plus the CHEW's language, with a facility pre-alert message. Show it in the video.

**Communication**
8. Follow JagaSungai's or Saklolo's article structure: a human opening line → the problem with dated sources → "what the CHEW actually gets" (the real output) → architecture and why a Graph → evals table with a baseline → "what I actually ran / what this doesn't show" → "my evals caught me" lessons → path to adoption (a PHC or LGA supervisor, running cost per case) → 5-minute "try it".
9. Ship a ScriptedModel or stand-in model so `pytest` and `evals.run_all` run offline in about 20 seconds. Judges can then verify every number.
10. Be explicit that this is not a patient-facing diagnostic tool, list what was synthetic, and state the next step (clinician review, then a pilot with a named type of partner). Do not claim lives saved.

**Biggest risk:** Emerald already owns "triage → evidence → professional signs off". To stand apart, lead with the referral handoff and follow-up loop and the Nigerian CHEW context, and don't present the sign-off gate as the novelty.
