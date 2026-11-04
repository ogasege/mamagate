# MamaGate: design prompts

Two prompts. Paste each one whole. Attach the files in `assets/brand/`
(`mamagate-icon.svg`, `mamagate-lockup.svg`) to the web-app prompt.

---

## 1. Web app prompt (Lovable or Claude Design)

---

### Your role

You are a principal product designer and senior front-end engineer. You
have designed clinical decision-support software used by nurses and
community health workers in Nigeria, Kenya and Ghana, and you have shipped
polished SaaS dashboards (think the clarity of Linear, the calm of Stripe
Dashboard, the plain language of the UK NHS design system). You care about
two things equally:

1. **Patient safety:** no ambiguous colours, no reassuring language, every
   number has a unit, every automated step shows whether it really happened.
2. **Visual quality:** this app will appear in a 3-minute demo video judged
   by AWS engineers. It must look like a funded product, not a template.

### The product, in one sentence

**MamaGate** helps a community health worker in a rural Nigerian clinic
decide, in seconds, whether a pregnant or postpartum woman must be sent to
hospital, and then completes the referral: chooses the hospital, writes the
referral note, alerts the hospital, and checks that she arrived.

The product name is **MamaGate**, written exactly like that.

### The people it serves

- **Hauwa, 31, Community Health Extension Worker (CHEW), Kumbotso, Kano.**
  Works alone at night, no doctor on site, uses a shared Android phone in
  bright light. Needs to enter vitals fast and know at a glance: send her
  now, within 24 hours, or not today.
- **Dr Okafor, registrar at the receiving hospital.** Reads the referral
  note when the woman arrives. Needs findings, times, and what was given.
- **The judge.** Watches once. Must see: rules decide urgency before any AI
  runs; the AI agent then works through visible steps; doses are refused.

### Non-negotiable look and feel

- **Light mode only.** Force light mode; ignore the system dark setting.
  Background `#F7F8FA`, cards `#FFFFFF`, ink `#101828`, secondary text
  `#475467`, borders `#E4E7EC`.
- **Brand:** teal `#0E7C7B` (primary actions, links, active states) and
  coral `#F07A4F` (brand accent only, used sparingly: logo, small
  highlights). Use the attached logo files; do not redraw the logo.
- **Urgency colours** (never use green for urgency):
  - REFER NOW: background `#FEF3F2`, border and text `#B42318`, solid
    badge `#B42318` with white text.
  - WITHIN 24H: background `#FFFAEB`, border and text `#B54708`, solid
    badge `#B54708`.
  - ROUTINE: background `#F2F4F7`, text `#344054`, solid badge `#475467`.
  Every badge also has an icon (siren, clock, clipboard) so it works in
  greyscale.
- **Type:** Inter. Scale: 12 / 14 / 16 (body) / 20 / 28 / 40 (urgency
  badge text 28 bold, letter-spacing 0.02em). Numbers use tabular figures.
- **Shape:** 12 px card radius, 1 px borders, one soft shadow
  `0 1px 2px rgba(16,24,40,.06)`. No gradients, no glassmorphism, no stock
  photos, no illustrations of people, no emoji.
- **Spacing:** 8 px grid. Generous white space. Max content width 1440 px.
- **Motion:** subtle only. Steps fade and slide in 150 ms as they complete.

### Page structure (desktop, 1440 px)

**Top bar (64 px, white, bottom border).** Left: the logo lockup (28 px
tall). Centre: a segmented control `Consultation | How it works |
Evaluation | Limits`. Right: a small grey pill `Synthetic demo data` and a
status dot `Agent: live` (teal) or `Agent: mock` (grey).

**Thin notice strip under the bar (32 px, `#F2F4F7`, 13 px text):**
"Decision support for trained health workers. Synthetic data only. Not a
medical device and not clinically validated."

**Main area: three columns, all visible above the fold at 1440 x 900.**

1. **Left, 400 px: "What you measured"** (scrolls independently).
   - "Load a demo case" select at the top with four presets (below).
   - Stage segmented control: Pregnant / In labour / Postpartum.
   - Vitals as a 2-column grid of compact inputs, unit shown inside the
     field on the right in grey: Gestational age (wk), Systolic (mmHg),
     Diastolic (mmHg), Pulse (/min), Resp. rate (/min), Temperature (°C),
     Urine protein (0, 1+, 2+, 3+ as a 4-segment control), Blood loss (ml),
     Hb (g/dL), Blood sugar (mmol/L), Labour (h), Fetal heart (/min).
   - Danger signs as toggle chips in collapsible groups with counts
     ("Bleeding · 1 selected"): Bleeding, Blood pressure signs, Emergency,
     Infection, Labour and baby, Anaemia. Selected chips turn teal with a
     check icon.
   - "Anything else? (transport, money, companion)" textarea, 3 rows.
   - Sticky footer inside the column: full-width primary button
     **Check and refer** (teal, 48 px tall, bold).

2. **Centre, flexible: "Gate result"**, the hero of the screen.
   - Before running: a calm empty card with the text "Enter what you
     measured. Leave a field empty if you did not measure it. Empty is
     never treated as normal."
   - After running: a large urgency card tinted with the urgency colour:
     - The solid urgency badge (REFER NOW), 28 px bold, with icon.
     - Directly under it, in 14 px monospace grey: `Decided by rules in
       2.1 ms · 0 AI tokens · rules v0.2`. This line matters: it proves
       the AI did not decide.
     - "Danger signs found": a list, each row = rule ID chip (monospace,
       e.g. `R12`), plain label, and source chips (`SO-CHEW p312`,
       `WHO B2`).
     - Warnings in a bordered callout with an alert icon, for example
       "Do not do a vaginal examination".
     - "Do now" callout (teal border) for follow-up actions such as
       "Re-check BP and test urine protein now".
     - "Not measured" row of grey pills: "Measure these before deciding".

3. **Right, 440 px: "Referral handoff"**: a vertical stepper. Each step
   has a status icon (pending circle, spinner, teal check, red cross) and
   a one-line result:
   1. Hospital chosen: name, capability tag (`EmONC yes` teal /
      `EmONC unknown` amber with "phone ahead"), `9.1 km · 12 min`, and a
      tiny provider label `Amazon Location Service`.
   2. Referral note written: "View note" opens a right-side drawer with the
      printable note.
   3. Note checked in code: check, or the list of problems.
   4. Hospital pre-alerted: `Sent via Amazon SNS` or `Simulated`.
   5. Arrival check set: `If not confirmed by 21:45, supervisor alerted`.
   Below the stepper: "Agent's reply" card with the numbered steps, then a
   collapsed "Agent trace" accordion (monospace list of tool calls, plus
   tokens, cycles, seconds).

**Dose refusal state:** if the worker asks for a dose, the right column
shows a red-bordered card "Dose withheld" with the refusal text and the
line "Blocked by code before any AI model was called."

**Referral note drawer (and print view):** looks like an official form:
heading with referral ID and urgency, From / To / Time / Woman rows,
sections "Danger signs", "Findings", "Reasons for referral", "Treatment
before referral" (blank lines to fill by hand), "Transport", "Told to the
woman and companion", and a dashed "Counter-referral: please return to
the referring clinic" box. Buttons: Print, Copy as text.

**Mobile (360 px):** single column. Order: urgency card (sticky summary
bar at the top once run), form, handoff. Primary button fixed at the
bottom. No horizontal scroll.

### Secondary pages

- **How it works:** one clean horizontal diagram:
  `Worker enters findings → Rules gate (code) → AI agent on Amazon Bedrock
  AgentCore → Choose hospital → Write note → Check note → Pre-alert →
  Arrival check`. Under it, three short cards: "Rules decide urgency",
  "The AI completes the handoff", "Doses are never given".
- **Evaluation:** a table from `/eval_report.json` showing each metric as
  `24 / 24` with a 95% interval bar (e.g. 86–100%) and a one-line meaning.
  Caption: "Synthetic cases derived from the same guidelines as the rules:
  this measures fidelity to the rules, not clinical accuracy." Add a second
  card "Real readings check" from `/external_check.json` (452 real
  antenatal readings: referrals, follow-up actions, by risk label).
- **Limits:** a plain bulleted list of what the demo does not show.

### Words to never use in the UI
"safe", "fine", "low risk", "diagnosis", "AI doctor".
For ROUTINE write: "No listed danger sign found in what was measured."

### API

`API_BASE` is one constant (default `http://localhost:8899`). Mock mode is
a toggle in a small settings popover in the top bar, **off by default when
`API_BASE` answers `GET /eval_report.json`, on otherwise**.

`POST {API_BASE}/invoke` request:
```json
{
  "case": {"pregnant": true, "ga_weeks": 34, "sbp": 168, "dbp": 112,
           "pulse": 96, "temp_c": 36.9, "resp_rate": 18,
           "severe_headache": true, "urine_protein_plus": 3,
           "synthetic_id": "AMINA-DEMO", "age": 26},
  "phc": {"name": "Synthetic PHC Kumbotso (demo)", "lat": 11.95, "lon": 8.49},
  "prompt": "Husband has a car. They have saved some money.",
  "session_id": "optional-identifier-at-least-33-characters"
}
```
Response (fields the UI uses):
```json
{
  "served_by": "agentcore-runtime",
  "gate_ms": 2.1,
  "triage": {
    "urgency": "REFER_NOW",
    "headline": "REFER_NOW: R12_SEVERE_PE_SYMPTOMS, R14_BP_SEVERE_ALONE",
    "fired": [{"rule_id": "R12_SEVERE_PE_SYMPTOMS",
               "label": "Severe pre-eclampsia symptoms with severe BP or 3+ protein after 20 weeks",
               "urgency": "REFER_NOW", "status": "so_verified",
               "sources": ["SO-CHEW p311, p312 V", "SO-JCHEW p311"],
               "scope_ref": "SO-CHEW p312", "warning": null}],
    "actions": [{"rule_id": "R34_HYPERTENSION_TEST_PROTEIN",
                 "label": "Raised BP (140/90 or more, below severe)",
                 "action": "Re-check BP after 15 minutes of rest and test urine protein now..."}],
    "missing_core_inputs": [],
    "rules_version": "0.2-unreviewed"
  },
  "dose_request_blocked": false,
  "urgency": "REFER_NOW",
  "reply": "1. Refer now to Synthetic Teaching Hospital A (demo)...",
  "referral_note": {"referral_id": "MG-3f2a9c1b7d",
                    "facility": "Synthetic Teaching Hospital A (demo)",
                    "facility_emonc_capability": "yes",
                    "travel": {"distance_km": 9.1, "minutes": 12,
                               "provider": "amazon-location-service"}},
  "referral_note_markdown": "# Referral note MG-3f2a9c1b7d (REFER_NOW) ...",
  "note_verified": true,
  "outbox": [
    {"type": "pre_alert", "status": "sent", "channel": "amazon-sns"},
    {"type": "arrival_check", "due_utc": "2026-11-05T01:10:00", "status": "scheduled"}
  ],
  "events": ["tool get_triage_result: success", "tool find_receiving_facility: success"],
  "agent_ms": 29000, "tokens": 29600, "cycles": 7
}
```
Dose refusal response: `{"dose_request_blocked": true, "model_called":
false, "reply": "[Dose withheld by MamaGate] ...", "triage": {...}}`. In
mock mode return it whenever the prompt contains "dose", "how much" or
"mg".

The real agent takes 20–40 seconds. Show the gate card immediately from
the response's `triage` (in mock mode, at 300 ms), and animate the handoff
steps in order while waiting, labelled "Choosing hospital…", "Writing
note…", and so on.

### Demo presets
1. **Severe pre-eclampsia → REFER NOW:** pregnant, 34 wk, BP 168/112,
   pulse 96, temp 36.9, RR 18, severe headache, protein 3+.
2. **Postpartum haemorrhage → REFER NOW:** postpartum, bleeding, blood loss
   400 ml, pulse 118, BP 98/60, temp 36.7, RR 22.
3. **Raised BP, protein not tested → ROUTINE + "Do now":** pregnant, 30 wk,
   BP 146/94, pulse 80, temp 36.8, RR 16.
4. **Missing vital → ROUTINE + "Not measured":** pregnant, 28 wk, BP
   112/72, pulse 82, temp 36.8, RR empty.

### Tech
React, TypeScript, Tailwind, shadcn/ui components restyled to the tokens
above, Lucide icons. No login, no database, no analytics, no external
fonts beyond Inter. Typed code, no `any`. Components: `TopBar`, `CaseForm`,
`GateCard`, `HandoffStepper`, `ReferralNoteDrawer`, `DoseRefusalCard`,
`AgentTrace`, `EvalPage`, `HowItWorksPage`, `LimitsPage`, `api.ts`.

### Definition of done
- At 1440 x 900, the form, the urgency card and the stepper are all visible
  without scrolling after running preset 1.
- Light mode even when the operating system is in dark mode.
- All four presets work in mock mode; preset 3 shows the "Do now" callout.
- Urgency badges are distinguishable in greyscale.
- None of the banned words appear.
- 360 px wide works with no horizontal scroll.

---

## 2. Logo prompt (Gemini image generation)

---

### Your role

You are a senior brand identity designer who builds marks for health
products used in Africa. You work in the tradition of clean geometric
identity design (simple shapes, strong silhouettes, perfect at small
sizes). You use West African visual references with restraint and never
as decoration or stereotype.

### The brief

Refine an existing logo concept for **MamaGate** (one word, no
tagline inside the logo). MamaGate is a maternal-health referral tool for
community health workers in Nigeria: a rules "gate" decides how urgently a
pregnant woman needs hospital care, then guides her safely to the right
hospital.

**Keep this concept (it is approved):** a rounded-square app icon in deep
teal `#0E7C7B`. Inside it, a white open doorway: two vertical posts joined
by a perfect semicircular arch (Roman-style round arch, NOT pointed, NOT
onion-shaped, NOT a mosque or church doorway). Standing in the doorway is
a mother, drawn as only two coral `#F07A4F` shapes: a round head and a
softly flared A-line dress whose curve suggests pregnancy. She is centred,
facing the viewer, with clear space between her and the posts.

**Refine it like this:**
- Optical balance: arch stroke weight equal to the post weight, about 8%
  of the icon width; rounded stroke ends; the doorway occupies about 60% of
  the icon height; generous padding.
- Make the mother feel human and dignified, not like a keyhole or a
  toilet sign: give the dress a gentle forward curve at the belly and a
  slightly wider hem; keep the head separate from the dress by a small gap.
- Optional, very subtle: a short path line on the floor of the doorway,
  leading forward out of the gate (the journey to care). Drop it if it
  clutters.
- Pure flat vector. No gradients, shadows, textures, 3D, outlines around
  the whole icon, medical crosses, hearts, stethoscopes, babies, flags,
  hands, or text inside the icon.

### Deliverables (one presentation board, white background)
1. App icon, 1024 x 1024, rounded square (corner radius about 22%).
2. The same icon shown at 180, 64, 32 and 16 px in a row to prove it reads
   small.
3. Horizontal lockup: icon on the left, wordmark "MamaGate" on the right
   in a geometric humanist sans-serif (Inter, Manrope or similar), "Mama"
   in ink `#101828` and "Gate" in teal `#0E7C7B`, semibold, tight but
   readable letter-spacing.
4. One-colour version (all ink `#101828` on white), for printed referral
   forms.
5. Reversed version: white mark on teal.
6. A greyscale check of the full-colour icon. The coral mother must stay
   clearly visible against the teal in greyscale; if not, lighten the
   coral.

Avoid any resemblance to the WHO, UNICEF, Red Cross, any hospital, any
government seal, or existing pregnancy apps.
