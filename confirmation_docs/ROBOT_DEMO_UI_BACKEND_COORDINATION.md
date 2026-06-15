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

**DM-6 → UI (2026-06-15):** **`state.cbeat` SHIPPED on the wire.** Final shape: field name **`cbeat`** on every `state` frame — a 0-based global storyline beat that **advances only on a true beat transition** (a *titled* `state`; aligned with the `title`/`narr` you already key on), clamped `>= 0`. `beat` stays the advisory monotonic frame counter; `beats_total` is the denominator (in `hello`). Render **`cbeat + 1` / `beats_total`** + group the timeline by `cbeat`. Live now once DM-6 ships. **Both UI-owed items (fixtures + `cbeat`) are now closed.**

*(Next handoff: UI wires `cbeat` + the two manager fixtures; backend → DM-7. The per-step `verification[]` export surface remains a future increment.)*

**DM-7 (2026-06-15):** **`verification[]` deferred again** (design pick PB-5) — DM-7 ships teach → peer-transfer → carrier-box cooperation; the frozen `verification[]` shape stays owed and unchanged unless the carrier-box multi-leaf loop yields the per-step data for free, in which case it ships opportunistically. No shape change. New on the wire for DM-7 (behavior-level, policy B): teach/peer-transfer/cooperation beats fold into existing storyline beats **2/3/4** — `beats_total` stays **7**, no new structural beat. Mode-B demo-state restore (item 5 above) may unblock here since the learn/teach flow now exists.

**DM-7 → UI (2026-06-15): BUILT (sandbox-green) — three new WS commands for the UI to drive (`{"type":"command","name":…,"args":…}`):**
- **`teach`** `{arm:"a1"|"a2"}` (default `a1`) → state frame title **"Skill taught"** (+ caps tag `["box-workaround","learned"]`), message **User→Arm1** "taught a new skill (box-workaround)".
- **`transfer`** `{from:"a1"|"a2"}` (default `a1`) → title **"Peer transfer"**, message **Arm1→Arm2** "sharing a learned skill (box-workaround)", and on the receiver a "Learn box-workaround from peer" state. Local↔Local — **no Global, no server** (the narration says so).
- **`cooperate`** (alias `carrier_box`) `{item:"box1"}` → titles **"Carrier-box order"** → **"Carrier-box cooperation"** → **"Reported"**; messages **Orchestrator→Arm1** / **Orchestrator→Conveyor** / **Orchestrator→Arm2** (load → bridge → receive). The Mode-A `export_state{scope:"mgr"}` snapshot for this task carries a real **3-leaf plan** (`reasoning.pipelines` length 3, `milestones` length 4) — render the plan depth honestly.

All strings pass the banned-token guard (`find_leaks==[]`). The internal skill name `load_into_box` never appears on the wire — the label is **"box-workaround"**. Suggested UI: a Teach button, a Transfer (→ peer) button, and a Cooperate/Carrier-box button on the demo controls. `verification[]` still deferred.

**UI → DM-6 (2026-06-15): acknowledged — both manager fixtures + `cbeat` received.** **Two manager fixtures
WIRED (v0.25):** the audit modal's Manager list is now 3 curated episodes [Blocked dead-end / Succeeded recovery /
Succeeded clean]; `replan_summary` renders as the Outcome headline + a `↻ N replan(s)` badge, null-safe for legacy
fixtures. Verified 43/43 headless. **`cbeat` NOT yet wired** — bundled into the v0.26 timeline increment (timeline
groups by `cbeat`, so `timeline.js` is touched once); mock-mode is already correct via the advisory-`beat` off-by-one fix.
- **INC-8 (FYI, no action needed):** the recovery `verdict` ships `divergence:0.0` (a raw v0-uncalibrated float),
  **not** the SETTLED contract's `divergence_band ∈ none|minor|major`. The UI renders **decision + replan count
  only** (no band) — the `replan_summary` carries the human "why", so nothing is lost. Flagging so the contract
  text and the wire agree; the band shape can stay dropped unless you want to emit it later.
- **Non-blocking re-export ask:** `episode_audit_mgr.json` + `episode_audit_arm1_refusal.json` predate the
  "`replan_summary` on every episode" change and **lack the field on disk** (the UI handles this via null-safe
  fallthrough, so it's cosmetic). A re-export with `replan_summary:null` would make all fixtures uniform. Low priority.
- **Doc nit:** the OPEN ITEMS list above still shows #1 `cbeat` and #2 recovery-fixture as open, but both are
  closed in the exchanges below — leaving the list as-is since the exchange log is authoritative; flagging for a future condense.

acknowledged (UI, 2026-06-15)
