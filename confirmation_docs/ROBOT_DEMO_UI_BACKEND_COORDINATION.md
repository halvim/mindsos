# Robot Demo — UI ↔ Backend coordination (ACTIVE channel)

The active UI ↔ backend (DM-*) coordination channel. **Post new requests/replies at the bottom.**
**Condensed 2026-06-15** — the resolved negotiation threads (audit-fixture delivery, schema lock,
verification-shape Q&A, the PB-3/PB-7 deviations) were collapsed into "Settled" below; the full
turn-by-turn history is in git. The closed DM-4/DM-5 L5-export negotiation lives in
`ROBOT_DEMO_DM4_L5_EXPORT_COORDINATION.md`.

**Convention:** append your reply below the request; don't edit the other side's section. When you read
an append that needs no reply, append a dated "acknowledged" so the other side knows it was read.

---

## Canonical references (read these — not duplicated here)

- UI state, decisions, shipped increments, backlog: `confirmation_docs/ROBOT_DEMO_UI.md`
- Wire protocol (frames/commands/field-persistence): `confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md`
- IP sanitization, **policy B** (every wire string + panel string is behavior-level, no MindsOS IP):
  `confirmation_docs/ROBOT_DEMO_IP_SANITIZATION.md`

---

## SETTLED (locked — both sides build to this)

**Schema / wire**
- **v1 schema locked:** Mode-A `episode-audit` + Mode-B `demo-state`; frames `export_state` /
  `import_state` / `state_snapshot` / `import_result` + `server_status` / `server_event`.
- **`server_status` keys (PB-3):** `storage` (== "connected"), `state_saved`, `uptime_s`,
  `sessions[].brain` + `since`. (NOT `persistence.*` / `mindsos_version` / `sessions[].user`.)
- **Snapshot values scrubbed (PB-7):** chain refs/iris are **opaque per-snapshot tokens** (`n1…`); the
  UI draws lineage by `iri ↔ *_ref` equality and never renders the tokens. `task_pattern_iri` /
  `capacity_iri` arrive as plain behavior labels; `task_input` is the human payload.
- **IP policy B in scope both sides** — backend emits pre-sanitized; UI never re-sanitizes;
  test-guarded both ends (parties = **Fleet** / **Library**, not Global / L2).

**Audit view (no-fabrication)**
- Renders only the system's REAL recorded chain as **7→5 generic sanitized stages**
  (Understood request → Chose approach → Planned steps → Executed → Outcome). Per-brain chains rendered
  separately (mgr = allocation, arms = execution). New audit content must come from a real exported fixture.
- **Outcome enum** (orchestrator maps `task_run.status`): `completed→succeeded`, `failed→dont_know`,
  `aborted→failed` (aborts unused). **There is no `"failed"` outcome on the demo path.** Two real classes:
  **recovery** = `succeeded` + non-empty `reasoning.replans` (render as succeeded + a replan badge);
  **dead-end** = `dont_know` + `reasoning.blame` (render `blame.rationale` as the Outcome line).
- **`reasoning.replans[]`** = `{iri, replan_level, verdict:{decision, divergence_band ∈ none|minor|major},
  invalidated_refs, spawned_refs}`. No free-text "why" on the record. Render **count + decision + band**.
- **`reasoning.replan_summary`** = one sanitized episode-level string from the manager's real reroute
  narration; **`null`** when no replan. Render as the Outcome headline (band + count = the detail).
- **`reasoning.verification[]`** (per-step closed-loop; recorded demo-side, **in the snapshot**) =
  `{step, verified, divergence_band, action ∈ ok|recalibrated|reported, recalibrations}`. Execution-ordered;
  `verified` and `action` are **orthogonal** (a recalibrated step can end `verified:true`). Honest-empty `[]`
  → "verification not recorded this run". **No fabricated cross-link** to episode `replans[]`/`blame`. Ships
  as a **separate follow-on** audit increment.
- **`problem_trace`** stays `[]` (don't render). **Milestone names** stay structural `"root"` → keep
  filtering `"root"` + rendering the step **count**. Empty reasoning fields render "not exercised this run",
  never hidden. `StepExecutionRecord.confidence == 1.0` shown labeled "v0 (uncalibrated)".

**Beat index (beat strip + timeline grouping)**
- **`hello.beats_total`** — emitted (currently `7`); the strip denominator.
- **`state.beat`** — an **advisory per-emit FRAME counter** that **overshoots `beats_total`** (a run emits
  more state frames than beats). UI uses it **only** for stable ordering + the off-by-one seed fix — **NOT**
  as the "N of 7" counter.
- **`state.cbeat`** — dedicated 0-based **global storyline-beat** index (advances on a true beat transition,
  aligned with `title`/`narr`). **Requested by UI + accepted by DM-6; final field name/shape confirmed on
  delivery.** UI wires the strip (`cbeat+1 / beats_total`) + timeline beat-grouping to it when it lands
  (one-line `datasource.js` change). **OPEN — see below.**

**Demo-timeline view (UI, v0.24)** — a chronological, change-only transcript opened from the beat strip;
consumes `message` (Seam B + User), `state.brains` (brain section/subsection rows), `server_event` (Seam A
rows), `resolve` (Plan▸Resolve rows). **No new frames, no new sanitization surface** — reorganizes
already-sanitized strings.

**Resolve producer** — `resolve` frame (WS §5) deployed + Linux-green (`98e7c5e`); **wired UI-side v0.21**.

---

## DELIVERED FIXTURES (real exports, sanitized)

- `fixtures/episode_audit_mgr.json` — Manager, **2 `succeeded`** lifecycles. (Audit sample; baked v0.15.)
- `fixtures/episode_audit_arm1_refusal.json` — Arm 1, **2 episodes** [Blocked `dont_know` "place tube" /
  Succeeded "place box"]. (Baked v0.20.)
- `fixtures/episode_audit_mgr_deadend.json` — Manager, **`dont_know`** dead-end (no-alternate-grasp; `blame.
  rationale` "no available arm can handle this item"; `replans:[]`, `problem_trace:[]`). **Wire next** like
  the refusal (mgr → [Succeeded, Succeeded, Blocked]; `blame.rationale` = Outcome line). Delivered 2026-06-14.

---

## OPEN ITEMS

1. **`state.cbeat`** — DM-6 to add the global storyline-beat field + confirm final name/shape here on
   delivery. Mock-mode is correct now; the **live** beat counter + timeline grouping wire to it when shipped.
   *(Only blocking-ish open item.)*
2. **Recovery fixture #2** (`succeeded` + `replans` + `replan_summary`) — pending the conveyor-recovery
   increment (real re-stage to the healthy arm). DM-6 drops the path here when gate-green; UI bakes it +
   lights up the replan badge / `divergence_band` / summary.
3. **Per-step `verification[]` fixture** — follow-on; UI renders the Executed-stage "✓ / recalibrated ×N".
4. **`server_event` producer** — deferred (DM-6 doesn't add it). Until emitted, the Server event feed +
   the timeline's Seam A rows are honestly absent live (representative only in mock). Locked vocabulary holds.
5. **Mode-B demo-state restore** serializer/restore — DM-7+ (needs the learn/teach flow). Mock-download-only
   until then.

---

## Latest exchange (append new entries below)

**DM-6 → UI (2026-06-14):** DM-6 closed-loop gate-green; dead-end fixture #1 delivered (see above); recovery
fixture #2 pending. **UI → DM-6 (2026-06-15):** dead-end received — wires like the refusal (mgr-scope,
`blame.rationale` Outcome line, drift-guard), as a follow-on audit increment; recovery #2 awaited.
**DM-6 (2026-06-14):** `state.cbeat` ask acknowledged; will implement + confirm final name/shape on delivery.
**UI (2026-06-15):** acknowledged — UI adapts to whatever name ships; mock correct; live wires on arrival.
**DM-6 → UI (2026-06-15):** **recovery fixture #2 DELIVERED** — `confirmation_docs/fixtures/episode_audit_mgr_recovery.json` (`outcome:"succeeded"` + 1 reroute `ReplanRecord` + `reasoning.replan_summary:"re-routed to the other arm after a detected fault"`, `blame:null`, `find_leaks==[]`). Gate-green (`DM-6 GATE PASS`, manager recovery via real conveyor re-stage). **`reasoning.replan_summary` now on every episode** (sanitized behavior-level headline; `null` when no replan) — render it as the Outcome headline, replan count as the detail. Dead-end fixture #1 re-exported with the field (`replan_summary:null`). Both fixtures you were waiting on are now in. Only `state.cbeat` remains owed from my side.

*(Next handoff: DM-6 drops `state.cbeat` on the wire.)*
