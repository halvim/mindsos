/* MindsOS demo v0.15 — L5 reasoning / audit view (goal #2: "why did it decide / refuse X").
 * Pure (no DOM): browser globals + node module.exports — same pattern as resolve.js / graph.js.
 *
 * Renders a RECORDED episode chain as 5 GENERIC stages (IP policy B,
 * ROBOT_DEMO_IP_SANITIZATION.md):
 *   Understood request -> Chose approach -> Planned steps -> Executed -> Outcome
 * The chain-artifact TYPE names (HintSet / MappingResult / Plan / Milestone / Pipeline /
 * PipelineRun / TaskRun) and capacity / task-pattern IRIs NEVER reach the DOM. The 7-artifact
 * structure collapses to 5 behavior stages here.
 *
 * Thin-v0-faithful: empty fields are shown honestly ("not exercised this run"), never hidden —
 * the demo never fakes depth it didn't compute (DM-4 coordination, Q2).
 *
 * Input = a sanitized Mode-A snapshot block (kind:"episode-audit"). The REAL chain comes from the
 * DM-4 Mode-A export; until then the page renders a clearly-chipped mock fixture (or, with no
 * fixture, an honest "available on live brains" placeholder).
 */

const AUDIT_STAGES = ["Understood request", "Chose approach", "Planned steps", "Executed", "Outcome"];

// Defensive de-IRI. The wire is sanitized upstream; this is belt-and-suspenders so a stray raw IRI
// (e.g. "a1.load_into_box", "task-pattern:demo:handoff", "grasp:jaw") can never render verbatim.
function plainLabel(s) {
  if (s == null) return "";
  s = String(s);
  if (s.indexOf(":") !== -1) s = s.split(":").pop();             // drop ns:/role: prefixes
  if (/\w\.\w/.test(s) && !/\s/.test(s)) s = s.split(".").pop(); // drop "a1." capacity prefix
  return s.replace(/_+/g, " ").trim();
}
// A field that is already display-ready (a sanitized sentence) is shown as-is; only a raw fallback
// key is run through plainLabel.
function disp(obj, dispKey, rawKey) {
  if (!obj) return "";
  if (obj[dispKey] != null) return String(obj[dispKey]);
  return plainLabel(obj[rawKey]);
}
function esc2(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
// Human request line. Handles a plain string, {request|summary|text}, and the real Mode-A order
// shape {order:{lines:[{item,shelf,pos}]}} (DM-4 fixture episode_audit_mgr.json).
function requestText(ti) {
  if (ti == null) return "";
  if (typeof ti === "string") return ti;
  if (ti.request || ti.summary || ti.text) return String(ti.request || ti.summary || ti.text);
  const lines = ti.order && ti.order.lines;
  if (Array.isArray(lines) && lines.length) {
    return lines.map(l => {
      const item = plainLabel(l.item || "item");
      const where = l.shelf ? ("shelf " + plainLabel(l.shelf)) : "";
      return where ? (item + " → " + where) : item;
    }).join("; ");
  }
  return "";
}
function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }

// --- episode list rows for one brain's snapshot block ---
function auditEpisodeList(brainBlock) {
  const eps = (brainBlock && brainBlock.episodes) || [];
  return eps.map((ep, i) => {
    const oc = (ep.value && ep.value.outcome_classification) || "";
    const ok = oc === "succeeded";
    const blocked = oc === "dont_know" || oc === "failed";
    let title = "—";
    if (ok) title = "Succeeded";
    else if (oc === "dont_know") title = "Blocked";
    else if (oc === "failed") title = "Failed";
    else if (oc === "low_confidence") title = "Low confidence";
    else if (oc === "asked_user") title = "Asked the user";
    else if (oc) title = plainLabel(oc);
    const sub = requestText(ep.task_input);
    return { i, ok, blocked, outcome: oc, glyph: ok ? "✓" : blocked ? "⊘" : "•", title, sub };
  });
}

// --- the 7->5 generic-stage collapse for one episode ---
function auditStages(ep) {
  ep = ep || {};
  const r = ep.reasoning || {};
  const val = ep.value || {};
  const oc = val.outcome_classification || "";
  const ok = oc === "succeeded";

  const req = requestText(ep.task_input);

  const mr = r.mapping_result || null;
  const approach = mr ? disp(mr, "approach", "selected_task_pattern_iri") : "";
  const conf = mr && mr.mapping_confidence != null ? mr.mapping_confidence : null;

  const msAll = (r.milestones || []).map(m => plainLabel(m.name || m.label || "")).filter(Boolean);
  // Hide the v0 structural placeholder name "root" (DM-4: it carries no computed meaning yet; the count
  // is the honest signal). Real milestone names from DM-5/6 render directly in the same shape.
  const ms = msAll.filter(n => n.toLowerCase() !== "root");
  const replans = (r.replans || []).length;

  const steps = (r.steps || [])
    .map(s => ({ lab: disp(s, "action", "capacity_iri"), ok: s.status ? (s.status === "completed" || s.status === "ok") : true }))
    .filter(s => s.lab);

  const dk = r.dont_know || null;
  const blame = r.blame || null;
  const stages = [];

  // 1 — Understood request
  stages.push({ num: 1, ttl: AUDIT_STAGES[0], tone: "ink",
    body: req || "—", note: req ? "" : "request not recorded this run" });

  // 2 — Chose approach
  stages.push({ num: 2, ttl: AUDIT_STAGES[1], tone: "ink",
    body: approach ? ("Approach: " + approach) : "no approach selected this run",
    note: conf != null ? ("match confidence: " + conf + " — v0 (uncalibrated)") : "" });

  // 3 — Planned steps
  let planBody, planNote;
  const replanNote = replans ? plural(replans, "replan", "replans") : "no replans this run";
  if (ms.length) {                       // real, named milestones (DM-5/6)
    planBody = ms.join("  →  ");
    planNote = plural(ms.length, "step", "steps") + " · " + replanNote;
  } else if (msAll.length) {             // v0 structural plan: count is the honest signal, names not yet computed
    planBody = plural(msAll.length, "step", "steps") + " planned";
    planNote = replanNote;
  } else {
    planBody = "no steps planned this run"; planNote = "";
  }
  stages.push({ num: 3, ttl: AUDIT_STAGES[2], tone: "ink", body: planBody, note: planNote });

  // 4 — Executed
  let execBody, execNote, execTone = "ink";
  if (steps.length) {
    execBody = steps.map(s => s.lab + (s.ok ? " ✓" : " ⊘")).join("   ·   ");
    const done = steps.filter(s => s.ok).length;
    execTone = done === steps.length ? "ok" : "warn";
    execNote = done === steps.length
      ? (plural(steps.length, "action", "actions") + " dispatched · all completed")
      : (done + " of " + steps.length + " completed · stopped");
  } else {
    execBody = ok ? "—" : "not reached";
    execNote = ok ? "" : "execution did not start (blocked before dispatch)";
  }
  stages.push({ num: 4, ttl: AUDIT_STAGES[3], tone: execTone, body: execBody, note: execNote });

  // 5 — Outcome
  let outBody, outNote, outTone;
  if (ok) {
    outBody = "Succeeded — remembered this run"; outTone = "ok";
    outNote = "no blame attributed (succeeded)";
  } else if (oc === "dont_know") {
    outBody = "Blocked — " + (disp(dk, "display", "reason") || "don’t know how to proceed");
    outTone = "stop";
    outNote = blame ? ("blame: " + disp(blame, "display", "rationale")) : "no fleet-shared skill covers it";
  } else {
    outBody = oc ? plainLabel(oc) : "—"; outTone = "warn";
    outNote = blame ? ("blame: " + disp(blame, "display", "rationale")) : "";
  }
  stages.push({ num: 5, ttl: AUDIT_STAGES[4], tone: outTone, body: outBody, note: outNote });

  return stages;
}

// --- full modal-body HTML (episode list + selected episode's stages) ---
function auditModalHTML(snapshot, brainKey, epIdx, opts) {
  opts = opts || {};
  const block = snapshot && snapshot.brains && snapshot.brains[brainKey];
  const list = auditEpisodeList(block);
  if (!list.length) {
    return { empty: true, selected: -1,
      html: '<div class="l5empty">' + esc2(opts.emptyMsg || "No recorded episodes for this brain yet.") + "</div>" };
  }
  const sel = Math.max(0, Math.min(list.length - 1, epIdx | 0));
  const stages = auditStages(block.episodes[sel]);
  const rows = list.map(e =>
    '<button class="l5ep' + (e.i === sel ? " sel" : "") + '" data-ep="' + e.i + '">'
    + '<span class="l5epg ' + (e.ok ? "ok" : e.blocked ? "stop" : "") + '">' + e.glyph + "</span>"
    + '<span class="l5ept">' + esc2(e.title) + "</span>"
    + '<span class="l5eps">' + esc2(e.sub) + "</span></button>"
  ).join("");
  const stageHTML = stages.map(s =>
    '<div class="l5stage"><span class="l5snum">' + s.num + "</span>"
    + '<div class="l5sbox"><div class="l5stt">' + esc2(s.ttl) + "</div>"
    + '<div class="l5sbody ' + s.tone + '">' + esc2(s.body) + "</div>"
    + (s.note ? '<div class="l5snote">' + esc2(s.note) + "</div>" : "")
    + "</div></div>"
  ).join("");
  return { empty: false, selected: sel,
    html: '<div class="l5eplist"><div class="l5ephdr">EPISODES · NEWEST FIRST</div>' + rows + "</div>"
        + '<div class="l5stages"><div class="l5shdr">SELECTED EPISODE — RECORDED CHAIN</div>' + stageHTML + "</div>" };
}

// first brain key that actually has episodes (for an imported snapshot)
function firstAuditBrain(snapshot) {
  const bs = (snapshot && snapshot.brains) || {};
  const keys = Object.keys(bs);
  for (const k of keys) if (bs[k] && bs[k].episodes && bs[k].episodes.length) return k;
  return keys[0] || null;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { AUDIT_STAGES, plainLabel, disp, auditEpisodeList, auditStages, auditModalHTML, firstAuditBrain };
}
