# Deep-research prompt: maternal danger-sign agent (paste into Argon / Claude)

You are a senior maternal-health researcher AND a senior AWS/agent architect helping me
win the AWS Builder Center hackathon "Strands SDK: Workshop to Ship". I am a Nigerian
software engineer, building solo. I have about 10 working hours left. Be skeptical,
cite primary sources with links, label every figure (primary / summary / modelled /
disputed / pre-2024), and NEVER invent statistics, guidelines, API names or SDK classes.
If you cannot verify something, say "unverified".

## The project (fixed — do not suggest a different problem)
A decision-support agent for Community Health Extension Workers (CHEWs/JCHEWs) and
midwives at rural Nigerian Primary Health Care centres caring for pregnant and
postpartum women. It addresses the "three delays" model of maternal death:
1. Delay in deciding to seek care -> deterministic red-flag (danger-sign) triage that
   runs in code BEFORE any LLM call; outputs urgency: Refer now / Within 24h / Routine.
2. Delay in reaching care -> birth-preparedness + transport plan, nearest facility
   that can provide emergency obstetric care (where data exists; otherwise "unknown").
3. Delay in receiving care -> auto-drafted structured referral note for the receiving
   facility so the woman is not re-triaged on arrival.
It is decision support for a trained worker, not a patient-facing diagnosis tool.
Synthetic cases only. No real patient data.

## Hackathon rules I must obey (verified from the Terms)
- Focus area: Health. Must "deliver measurable improvement for underserved populations".
- Working agent ON AWS built with the Strands Agents SDK (Python). Public repo with an
  OSI licence. Builder Center article. Public demo video < 3 min with no third-party
  trademarks or copyrighted music/material. Original, not previously published.
- One entry per person. Deadline 4 Nov 2026 11:59 PM PDT (07:59 WAT 5 Nov).
- Judging, 25% each: social impact (measurable), technical execution with Strands,
  communication (article + video), originality (agent architecture, novel AWS service
  use, how far beyond the workshop).
- The workshop covered: agent loop + tools, hooks, skills + steering, session managers,
  multi-agent (agents-as-tools / swarm / graph), deploy to Bedrock AgentCore Runtime.
- ~100 entries already submitted, mostly from India. Table stakes now: a code-owned
  emergency gate that fires before the model, bilingual output, a planner->critic graph,
  and a small eval with numbers. No entry covers maternal health or Nigeria/Africa.
- The strongest entries go further: enforcement that survives prompt failure (signed
  tool arguments, state re-checked on every send, "agents may raise urgency, only a
  human may lower it"), durable human-approval interrupts that resume later,
  evals against a baseline with injected-error and red-team cases, AWS services used
  for a reason (AgentCore Memory, Gateway + Cedar policy, EventBridge Scheduler + SNS),
  and honest "what this does not show" sections. The closest rival is a vet phone line
  (triage rules -> cited evidence -> professional sign-off -> community warning), so a
  sign-off gate alone is NOT novel. Our differentiator must be the full referral loop:
  danger sign -> referral decision -> structured referral note -> pre-alert to the
  receiving facility -> follow-up if arrival is not confirmed.

## Research I need (answer each section)

### A. Clinical content (the rules engine)
1. The authoritative danger-sign lists for pregnancy, labour and postpartum that apply in
   Nigeria: WHO (ANC 2016 recommendations, IMPAC "Managing Complications in Pregnancy and
   Childbirth", WHO Recommendations on maternal and newborn care), Nigeria's National
   Standing Orders for CHEWs/JCHEWs (2024 edition if it exists), FMoH/NPHCDA Minimum
   Service Package, Nigeria's Emergency Obstetric Care / CEmONC guidance, FIGO.
   For each source: title, year, publisher, link, licence/reuse terms, and whether I may
   quote short passages in a public repo.
2. A concrete, structured red-flag table I can encode as code: sign, threshold (e.g. BP
   >=160/110, temperature, bleeding amount, fetal movement, gestational age bounds),
   urgency level, and the source + page for each. Include pre-eclampsia/eclampsia,
   antepartum and postpartum haemorrhage, sepsis, obstructed/prolonged labour, ruptured
   membranes, severe anaemia, reduced fetal movement, convulsions, severe headache/
   blurred vision, breathing difficulty.
3. What pre-referral actions CHEWs are allowed to perform under Nigerian Standing Orders
   (e.g. MgSO4 loading dose, misoprostol, oxytocin, IV access, positioning) — and which
   are NOT in scope. I will hard-block anything outside scope.
4. Standard structure of an obstetric referral note/form in Nigeria (fields used by
   PHCs and general hospitals), plus the national referral pathway (PHC -> secondary ->
   tertiary) and counter-referral.
5. Known failure modes of clinical decision support for frontline workers (automation
   bias, over-referral where cost is the main barrier, alert fatigue). Cite evidence,
   including any Nigerian CHEW AI/decision-support evaluations (e.g. Kano).

### B. Evidence for the impact story (Nigeria, 2023-2026)
1. Maternal mortality: WHO/UN MMEIG modelled MMR and Nigeria's share of global deaths;
   2023-24 NDHS figures; explain why numbers differ. Leading causes (haemorrhage,
   hypertensive disorders, sepsis) with sources.
2. Skilled birth attendance, facility delivery, ANC4+/ANC8 coverage, urban/rural and
   North/South gaps (NDHS 2023-24 / DHS API).
3. CHEW workforce: share of PHC staff, PHCs without doctors (BudgIT, NPHCDA), referral
   delays and transport barriers. Evidence on the three delays in Nigeria specifically.
4. Existing tools and competitors: National Standing Orders app, CHEWA (PATH/Viamo),
   HelpMum, mDoc, Safe Delivery App (Maternity Foundation), WHO SMART guidelines /
   ANC digital adaptation kit, any LLM maternal tools in Africa. For each: what it does,
   and the gap my agent fills. Do not claim "no one does this".
5. One honest, measurable outcome metric for the article that I can actually measure
   offline tonight, plus the outcome metric a real pilot would measure.

### C. Data I can use tonight (free, no paid key, test it)
1. Facility data with emergency obstetric capability: GRID3 Nigeria health facilities,
   Nigeria Health Facility Registry, OnTIME/Lagos EmONC masterlist, HDX healthsites.
   Exact download URL, format, fields, licence, whether it has EmONC/functional status.
2. Any public synthetic or de-identified obstetric vignette sets I could adapt for
   evaluation (e.g. WHO training cases), with licence.
3. Routing/distance APIs without keys (OSRM public demo, OpenRouteService terms).

### D. Architecture with the Strands Agents SDK (Python) on AWS
Verify every class/function name against the current docs at strandsagents.com and the
GitHub repo strands-agents/sdk-python. Mark anything not verified.
1. Best multi-agent pattern: Graph (GraphBuilder, conditional edges) vs Swarm vs
   agents-as-tools for: rules-gate -> protocol lookup -> referral writer -> citation
   checker. How to make the deterministic red-flag gate run before any model call
   (hooks such as BeforeInvocationEvent / BeforeNodeCallEvent, or a function node).
2. How to hard-block out-of-scope drug/dose advice (hooks, interventions, steering,
   Bedrock Guardrails with guardrail_id on BedrockModel, contextual grounding checks).
3. Session/state: session managers, AgentCore Memory for a pregnancy record across
   visits; what works on AgentCore Runtime (ephemeral local disk).
4. Deployment: exact current steps to deploy a Strands agent to Amazon Bedrock
   AgentCore Runtime (CLI/toolkit name and commands), known pitfalls, Lambda fallback.
   Which Bedrock model to use in us-east-1 without approval friction (Nova vs Claude).
5. Novel AWS services that genuinely fit and score originality (not decoration):
   e.g. Amazon Location Service for routing, SNS/SMS or WhatsApp via AWS End User
   Messaging for the referral note, Amazon Translate (Hausa supported? Yoruba/Igbo?),
   Amazon Polly voices for Nigerian languages, Step Functions, HealthLake/FHIR for the
   referral document, AgentCore Gateway/Identity/Observability. For each: does it work
   in us-east-1 tonight, cost, and setup time.
6. Evaluation: strands-agents-evals or a plain pytest harness. Design a test set of
   ~40-60 synthetic vignettes (with label source), metrics (red-flag recall with 95% CI,
   over-referral rate, refusal rate for out-of-scope doses, citation correctness,
   latency, cost per case), and how to report them honestly.

### E. Safety, ethics and law
1. Nigeria Data Protection Act 2023 implications for a demo with synthetic data, and
   for a real pilot. 2. Medical-device / SaMD considerations in Nigeria (NAFDAC) — what
   wording to avoid ("diagnose", "clinically validated"). 3. Language: is Hausa/Yoruba/
   Pidgin output safe without a native clinical reviewer? Recommend what to ship.
4. Copyright: which guideline text I may quote or encode; what must stay out of the repo.

### F. Deliverables
1. A one-paragraph pitch and a title.
2. The red-flag rules table (from A2) as a ready-to-encode JSON/YAML snippet with sources.
3. Architecture diagram description (nodes, edges, tools, hooks, AWS services).
4. A 2:40 demo-video script in 3 scenes (no logos, synthetic cases, show a refusal).
5. An article outline mapped to the four judging criteria, including "what I learned".
6. An hour-by-hour plan for the next 10 hours with cut-lines if time slips.
7. Top 10 risks that could disqualify me or lose points, with mitigations.
