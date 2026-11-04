/* MamaGate web UI. Talks to server.py on the same origin. */
"use strict";

const $ = (sel) => document.querySelector(sel);
const md = (s) => esc(s)
  .replace(/^\s*-{3,}\s*$/gm, "")
  .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
  .replace(/\s(\d+)\.\s/g, "\n$1. ")
  .replace(/\n{2,}/g, "\n")
  .trim();
const esc = (s) => String(s ?? "").replace(/[&<>"]/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const VITALS = [
  ["ga_weeks", "Gestational age", "wk"], ["sbp", "Systolic", "mmHg"],
  ["dbp", "Diastolic", "mmHg"], ["pulse", "Pulse", "/min"],
  ["resp_rate", "Resp. rate", "/min"], ["temp_c", "Temperature", "°C"],
  ["urine_protein_plus", "Urine protein", "+"],
  ["blood_loss_ml", "Blood loss", "ml"], ["hb_g_dl", "Hb", "g/dL"],
  ["blood_sugar_mmol", "Blood sugar", "mmol/L"],
  ["labour_hours", "Labour", "h"], ["fhr", "Fetal heart", "/min"],
];

const SIGNS = {
  "Bleeding": [["vaginal_bleeding", "Vaginal bleeding"],
    ["constant_trickle", "Constant trickle"],
    ["delivered_outside", "Delivered outside"],
    ["placenta_retained", "Placenta retained"],
    ["third_degree_tear", "Tear to anus"]],
  "Blood pressure signs": [["severe_headache", "Severe headache"],
    ["visual_disturbance", "Blurred vision"],
    ["epigastric_pain", "Upper belly pain"], ["vomiting", "Vomiting"],
    ["pitting_oedema", "Pitting oedema"],
    ["dbp_two_readings_ge_90", "Diastolic 90+ twice"]],
  "Emergency": [["convulsion_or_unconscious", "Fits or unconscious"],
    ["very_difficult_breathing", "Very difficult breathing"],
    ["difficulty_breathing", "Difficulty breathing"],
    ["severe_abdominal_pain", "Severe belly pain"]],
  "Infection": [["stiff_neck", "Stiff neck"], ["lethargy", "Lethargic"],
    ["unable_to_stand", "Unable to stand"],
    ["very_fast_breathing", "Very fast breathing"]],
  "Labour and baby": [["malpresentation", "Malpresentation"],
    ["cord_prolapse", "Cord prolapse"],
    ["no_fetal_movement", "No fetal movement"],
    ["smelly_or_unclear_liquor", "Smelly liquor"],
    ["leaking_fluid_not_in_labour", "Leaking fluid"]],
  "Anaemia": [["severe_pallor", "Severe pallor"],
    ["weakness_dizziness_or_breathless_at_rest", "Breathless at rest"]],
};

const PRESETS = {
  pe: { stage: "pregnant", ga_weeks: 34, sbp: 168, dbp: 112, pulse: 96,
    temp_c: 36.9, resp_rate: 18, urine_protein_plus: 3,
    severe_headache: true, synthetic_id: "AMINA-DEMO", age: 26,
    prompt: "Husband has a car. They have saved a little money." },
  pph: { stage: "postpartum", vaginal_bleeding: true, blood_loss_ml: 400,
    pulse: 118, sbp: 98, dbp: 60, temp_c: 36.7, resp_rate: 22,
    synthetic_id: "HAUWA-DEMO", age: 24,
    prompt: "Her brother has a motorbike only. Family has little money." },
  bp: { stage: "pregnant", ga_weeks: 30, sbp: 146, dbp: 94, pulse: 80,
    temp_c: 36.8, resp_rate: 16, synthetic_id: "NGOZI-DEMO", age: 29,
    prompt: "" },
  missing: { stage: "pregnant", ga_weeks: 28, sbp: 112, dbp: 72,
    pulse: 82, temp_c: 36.8, synthetic_id: "BOLA-DEMO", age: 31,
    prompt: "" },
  dose: { stage: "pregnant", ga_weeks: 34, sbp: 168, dbp: 112, pulse: 96,
    temp_c: 36.9, resp_rate: 18, severe_headache: true,
    synthetic_id: "AMINA-DEMO", age: 26,
    prompt: "Transport is delayed. What dose of magnesium sulphate should I give her?" },
};

const STEPS = [
  ["facility", "Hospital chosen", "Choosing hospital…"],
  ["note", "Referral note written", "Writing note…"],
  ["verify", "Note checked in code", "Checking note…"],
  ["alert", "Hospital pre-alerted", "Pre-alerting hospital…"],
  ["arrival", "Arrival check set", "Scheduling arrival check…"],
];

let stage = "pregnant";
let lastNote = "";

function buildForm() {
  $("#vitals").innerHTML = VITALS.map(([k, label, unit]) =>
    `<label class="vital">${label}<input inputmode="decimal" id="v-${k}">` +
    `<span class="unit">${unit}</span></label>`).join("");
  $("#signs").innerHTML = Object.entries(SIGNS).map(([group, items]) =>
    `<details class="group" open><summary>${group}</summary><div class="chips">` +
    items.map(([k, l]) => `<button class="chip" data-flag="${k}">${l}</button>`)
      .join("") + "</div></details>").join("");
  document.querySelectorAll(".chip").forEach((c) =>
    c.addEventListener("click", () => c.classList.toggle("on")));
  document.querySelectorAll("#stage button").forEach((b) =>
    b.addEventListener("click", () => setStage(b.dataset.stage)));
}

function setStage(s) {
  stage = s;
  document.querySelectorAll("#stage button").forEach((b) =>
    b.classList.toggle("on", b.dataset.stage === s));
}

function loadPreset(key) {
  const p = PRESETS[key];
  if (!p) return;
  VITALS.forEach(([k]) => { $(`#v-${k}`).value = p[k] ?? ""; });
  document.querySelectorAll(".chip").forEach((c) =>
    c.classList.toggle("on", Boolean(p[c.dataset.flag])));
  setStage(p.stage);
  $("#prompt").value = p.prompt || "";
  $("#run").dataset.sid = p.synthetic_id;
  $("#run").dataset.age = p.age;
}

function collectCase() {
  const c = { [stage]: true };
  if (stage === "in_labour") c.pregnant = true;
  VITALS.forEach(([k]) => {
    const v = $(`#v-${k}`).value.trim();
    if (v !== "") c[k] = Number(v);
  });
  document.querySelectorAll(".chip.on").forEach((ch) => {
    c[ch.dataset.flag] = true;
  });
  c.synthetic_id = $("#run").dataset.sid || "DEMO-CASE";
  if ($("#run").dataset.age) c.age = Number($("#run").dataset.age);
  return c;
}

const ICON = { REFER_NOW: "🚨", WITHIN_24H: "⏱", ROUTINE: "📋" };
const LABEL = { REFER_NOW: "REFER NOW", WITHIN_24H: "WITHIN 24H",
  ROUTINE: "ROUTINE" };

function renderGate(t, gateMs) {
  const u = t.urgency;
  const rules = t.fired.map((r) => `<div class="rule"><span class="rid">` +
    `${esc(r.rule_id.split("_")[0])}</span><div>${esc(r.label)}<br>` +
    r.sources.map((s) => `<span class="src">${esc(s)}</span>`).join("") +
    "</div></div>").join("");
  const warns = t.fired.filter((r) => r.warning).map((r) =>
    `<div class="callout warn"><b>Warning</b>${esc(r.warning)}</div>`).join("");
  const acts = (t.actions || []).map((a) =>
    `<div class="callout do"><b>Do now</b>${esc(a.action)}</div>`).join("");
  const missing = t.missing_core_inputs.length ?
    `<div class="callout missing"><b>Not measured: measure these before deciding</b>` +
    t.missing_core_inputs.map((m) => `<span class="pill">${esc(m)}</span>`).join(" ") +
    "</div>" : "";
  const none = u === "ROUTINE" ?
    `<p>No listed danger sign found in what was measured.</p>` : "";
  $("#gate").className = `card urgency ${u}`;
  $("#gate").innerHTML =
    `<span class="badge ${u}">${ICON[u]} ${LABEL[u]}</span>` +
    `<div class="proof mono">Decided by rules in ${gateMs} ms · 0 AI tokens · ` +
    `rules v${esc(t.rules_version)}</div>${none}` +
    (rules ? `<h3 style="margin-top:12px">Danger signs found</h3>${rules}` : "") +
    warns + acts + missing;
}

function renderSteps(state) {
  $("#stepper").innerHTML = STEPS.map(([key, done, busy]) => {
    const s = state[key] || { status: "pending" };
    const title = s.status === "active" ? busy : done;
    return `<li class="step ${s.status}"><span class="ic"></span><div>` +
      `<div class="t">${title}</div><div class="d">${s.detail || ""}</div></div></li>`;
  }).join("");
}

function animateWhileWaiting() {
  let i = 0;
  const state = {};
  renderSteps(state);
  const tick = () => {
    if (i > 0) state[STEPS[i - 1][0]] = { status: "pending", detail: "" };
    if (i < STEPS.length) state[STEPS[i][0]] = { status: "active" };
    renderSteps(state);
    i = (i + 1) % (STEPS.length + 1);
  };
  tick();
  return setInterval(tick, 4500);
}

function finalSteps(r) {
  const note = r.referral_note;
  const box = {};
  const travel = note?.travel || {};
  const out = (type) => (r.outbox || []).find((o) => o.type === type);
  if (note) {
    const cap = note.facility_emonc_capability;
    box.facility = { status: "done", detail:
      `${esc(note.facility)}<span class="tag ${cap === "yes" ? "yes" : "unknown"}">` +
      `EmONC ${esc(cap)}</span><br>${travel.distance_km} km · ${travel.minutes} min` +
      ` · <span class="mono">${esc(travel.provider)}</span>` +
      (cap !== "yes" ? "<br>Capability unknown: phone ahead." : "") };
    box.note = { status: "done", detail:
      `<button class="linkbtn" id="view-note">View ${esc(note.referral_id)}</button>` };
    box.verify = r.note_verified ? { status: "done", detail: "All checks passed" }
      : { status: "fail", detail: "Note failed checks; nothing was sent." };
  }
  const a = out("pre_alert");
  if (a) box.alert = { status: a.status === "failed" ? "fail" : "done",
    detail: a.status === "sent" ? "Sent via Amazon SNS" : esc(a.status) };
  const c = out("arrival_check");
  if (c) box.arrival = { status: c.status === "failed" ? "fail" : "done",
    detail: `If arrival is not confirmed by ${esc(c.due_utc)} UTC, the ` +
      `supervisor is alerted (${c.status === "scheduled" ?
        "EventBridge Scheduler" : esc(c.status)})` };
  renderSteps(box);
  const v = $("#view-note");
  if (v) v.addEventListener("click", openNote);
}

let familyCard = null;
let familyLang = "en";

function renderFamily(card) {
  familyCard = card || familyCard;
  if (!familyCard) { $("#family").innerHTML = ""; return; }
  const all = familyCard.translations || [];
  const c = all.find((x) => x.language === familyLang) || all[0];
  if (!c) { $("#family").innerHTML = ""; return; }
  const tabs = all.map((x) => `<button class="lang ${x.language === c.language ? "on" : ""}"` +
    ` data-lang="${esc(x.language)}">${esc(x.name)}</button>`).join("");
  const listen = c.speech ?
    `<button class="btn teal listen" data-speak="${esc(c.language)}">▶ Listen</button>` :
    `<span class="muted">Text only (no ${esc(c.name)} voice yet)</span>`;
  $("#family").innerHTML = `<div class="card family"><h3>Referral card · for the woman and her family</h3>
    <div class="langs">${tabs}</div>
    <p class="fam-head" lang="${esc(c.language)}"><b>${esc(c.headline)}</b><br>
    ${esc(familyCard.where)} · ${esc(familyCard.how_long)}</p>
    <b>${esc(c.bring_title)}</b><ul lang="${esc(c.language)}">${c.bring.map((b) => `<li>${esc(b)}</li>`).join("")}</ul>
    <b>${esc(c.signs_title)}</b><ul lang="${esc(c.language)}">${c.signs.map((b) => `<li>${esc(b)}</li>`).join("")}</ul>
    <div class="fam-foot">${listen}<audio id="fam-audio" preload="none"></audio></div>
    ${c.review_note ? `<p class="muted">${esc(c.review_note)}</p>` : ""}
    <p class="muted">${esc(familyCard.footer)}</p></div>`;
  document.querySelectorAll("[data-lang]").forEach((b) => b.addEventListener("click", () => {
    familyLang = b.dataset.lang; renderFamily();
  }));
  const btn = document.querySelector("[data-speak]");
  if (btn) btn.addEventListener("click", async () => {
    const audio = $("#fam-audio");
    btn.textContent = "Loading voice…";
    audio.src = `/speak/${btn.dataset.speak}?urgent=${familyCard.go_now}`;
    try { await audio.play(); btn.textContent = "▶ Playing"; }
    catch { btn.textContent = "Voice unavailable"; }
    audio.onended = () => { btn.textContent = "▶ Listen"; };
    audio.onerror = () => { btn.textContent = "Voice unavailable"; };
  });
}

function openNote() { $("#note").textContent = lastNote; $("#drawer").hidden = false; }

async function run() {
  const btn = $("#run");
  btn.disabled = true;
  btn.textContent = "Checking…";
  $("#reply").innerHTML = "";
  $("#family").innerHTML = "";
  $("#trace-box").hidden = true;
  const body = JSON.stringify({ case: collectCase(), prompt: $("#prompt").value,
    phc: { name: "Synthetic PHC Kumbotso (demo)", lat: 11.95, lon: 8.49 } });
  const headers = { "Content-Type": "application/json" };
  const g = await (await fetch("/gate", { method: "POST", headers, body })).json();
  renderGate(g.triage, g.gate_ms);
  const timer = animateWhileWaiting();
  try {
    const res = await fetch("/invoke", { method: "POST", headers, body });
    const r = await res.json();
    if (!res.ok) throw new Error(r.detail || res.statusText);
    clearInterval(timer);
    $("#served-by").innerHTML = `<span class="dot"></span>Agent: ${
      r.served_by === "agentcore-runtime" ? "live on AgentCore" : esc(r.served_by)}`;
    if (r.dose_request_blocked) {
      renderSteps({});
      $("#reply").innerHTML = `<div class="card refusal"><h3>Dose withheld</h3>` +
        `<p>${esc(r.reply)}</p><p class="muted">Blocked by code before any AI ` +
        `model was called.</p></div>`;
      return;
    }
    lastNote = r.referral_note_markdown || "";
    finalSteps(r);
    $("#reply").innerHTML = `<div class="card"><h3>Agent's reply</h3>` +
      `<div class="reply">${md(r.reply)}</div></div>`;
    renderFamily(r.family_card);
    $("#trace").textContent = (r.events || []).join("\n") +
      `\n\ntokens ${r.tokens} · cycles ${r.cycles} · ${Math.round(r.agent_ms / 1000)} s`;
    $("#trace-box").hidden = false;
  } catch (err) {
    clearInterval(timer);
    renderSteps({});
    $("#reply").innerHTML = `<div class="card refusal"><h3>Referral steps could ` +
      `not be completed</h3><p>Refer using your paper form and phone the ` +
      `hospital. (${esc(err.message)})</p></div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Check and refer";
  }
}

const STATUS_TEXT = {
  expected: ["On the way", "Expected. If she has not arrived in time, the supervisor is alerted."],
  arrived: ["Arrived", "Arrival confirmed. Supervisor alert cancelled and the clinic was told."],
  not_arrived: ["Not arrived", "Missed referral. The clinic and supervisor were told to contact the family."],
};

function minutesAgo(stamp) {
  const t = Date.parse(String(stamp).replace(" UTC", "Z").replace(" ", "T"));
  if (Number.isNaN(t)) return "";
  const m = Math.max(0, Math.round((Date.now() - t) / 60000));
  return m < 1 ? "just now" : m < 60 ? `${m} min ago` : `${Math.round(m / 60)} h ago`;
}

function referralCard(r) {
  const [label, sentence] = STATUS_TEXT[r.status] || [r.status, ""];
  const signs = (r.danger_labels || r.danger_signs || [])
    .map((s) => `<li>${esc(s)}</li>`).join("");
  const warns = (r.warnings || [])
    .map((w) => `<div class="callout warn"><b>Warning</b>${esc(w)}</div>`).join("");
  const travel = r.travel ? `${r.travel.distance_km} km · about ${r.travel.minutes} min` : "";
  const buttons = r.status === "expected" ?
    `<button class="btn teal" data-arr="${esc(r.referral_id)}" data-v="1">Mark arrived</button>` +
    `<button class="btn red" data-arr="${esc(r.referral_id)}" data-v="0">Not arrived</button>` : "";
  return `<article class="card ref ${r.status}">
    <header class="ref-head">
      <span class="badge ${r.urgency} small">${LABEL[r.urgency]}</span>
      <h3>${esc(r.woman)}${r.age && r.age !== "not recorded" ? `, ${esc(r.age)} years` : ""}</h3>
      <span class="status-tag ${r.status}">${label}</span>
    </header>
    <p class="status-line">${sentence}</p>
    <dl class="ref-grid">
      <dt>From</dt><dd>${esc(r.from)}</dd>
      <dt>Sent</dt><dd>${esc(r.sent_at)} <span class="muted">(${minutesAgo(r.sent_at)})</span></dd>
      ${travel ? `<dt>Travel</dt><dd>${travel}</dd>` : ""}
      <dt>Referral</dt><dd class="mono">${esc(r.referral_id)}</dd>
    </dl>
    <h4>Danger signs found</h4><ul class="signs">${signs}</ul>${warns}
    <footer class="ref-foot">
      <button class="linkbtn" data-note="${esc(r.referral_id)}">Read the referral note</button>
      <span class="actions">${buttons}</span>
    </footer>
  </article>`;
}

async function loadReferrals() {
  const rows = await (await fetch("/referrals")).json();
  $("#referrals").innerHTML = rows.length ? rows.map(referralCard).join("") :
    `<div class="card empty">No referrals yet. Run a REFER NOW case first.</div>`;
  document.querySelectorAll("[data-note]").forEach((b) => b.addEventListener("click", () => {
    const row = rows.find((x) => x.referral_id === b.dataset.note);
    lastNote = row?.note_markdown || "";
    openNote();
  }));
  document.querySelectorAll("[data-arr]").forEach((b) => b.addEventListener("click",
    async () => {
      b.disabled = true;
      await fetch(`/referrals/${b.dataset.arr}/arrival`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ arrived: b.dataset.v === "1",
          details: b.dataset.v === "1" ? "Admitted to labour ward." :
            "No arrival recorded; family to be contacted." }),
      });
      loadReferrals();
    }));
}

function pct(x) { return `${Math.round(x * 100)}%`; }

async function loadEval() {
  try {
    const e = await (await fetch("/eval_report.json")).json();
    const rows = [
      ["red_flag_recall", "Red-flag recall", "REFER NOW cases caught by the gate"],
      ["within_24h_detection", "Within-24h detection", "Priority cases caught"],
      ["over_referral", "Over-referral", "Routine cases wrongly escalated (lower is better)"],
      ["dose_refusal", "Dose refusal", "Dose questions refused before any model call"],
      ["dose_leak_redaction", "Dose redaction", "Model sentences with doses removed"],
    ];
    $("#eval").innerHTML = `<div class="card">` + rows.map(([k, t, d]) => {
      const m = e[k];
      return `<div class="metric"><b>${t}</b><span class="mono">${m.k} / ${m.n}</span>` +
        `<div><div class="bar"><i style="left:${pct(m.ci95[0])};right:${
          pct(1 - m.ci95[1])}"></i></div><span class="muted">95% CI ${pct(m.ci95[0])}` +
        `–${pct(m.ci95[1])} · ${d}</span></div></div>`;
    }).join("") + `<p class="muted">Synthetic cases derived from the same guidelines ` +
      `as the rules: this measures fidelity to the rules, not clinical accuracy.</p></div>`;
    const x = await (await fetch("/external_check.json")).json();
    const f = x.referrals;
    $("#external").innerHTML = `<div class="card"><h3>Real readings check · ` +
      `${x.unique_rows} unique antenatal readings (UCI, CC BY 4.0)</h3>` +
      `<p>High-risk readings referred: <b>${f.high_risk_flagged.k}/${f.high_risk_flagged.n}</b>` +
      ` · given a follow-up test or assessment: <b>${x.follow_up_action_only["high risk"].k}` +
      `</b> · either: <b>${x.referral_or_follow_up["high risk"].k}/${
        x.referral_or_follow_up["high risk"].n}</b>. Emergency referral share: ` +
      `${pct(f.refer_now_share)}.</p><p class="muted">${esc(x.caveat)}</p></div>`;
  } catch {
    $("#eval").innerHTML = `<div class="card empty">Run evals/run_eval.py first.</div>`;
  }
}

function showView(v) {
  document.querySelectorAll(".tab").forEach((t) =>
    t.classList.toggle("active", t.dataset.view === v));
  document.querySelectorAll(".view").forEach((el) => {
    el.hidden = el.id !== `view-${v}`;
  });
  if (v === "hospital") loadReferrals();
  if (v === "eval") loadEval();
}

buildForm();
renderSteps({});
document.querySelectorAll(".tab").forEach((t) =>
  t.addEventListener("click", () => showView(t.dataset.view)));
$("#preset").addEventListener("change", (e) => loadPreset(e.target.value));
$("#run").addEventListener("click", run);
$("#close").addEventListener("click", () => { $("#drawer").hidden = true; });
$("#print").addEventListener("click", () => window.print());
$("#copy").addEventListener("click", () => navigator.clipboard.writeText(lastNote));
