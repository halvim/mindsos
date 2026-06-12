# Robot Demo — DM-4 ↔ UI coordination: L5 export/import + Server panel

**Purpose.** Cross-chat contract negotiation between the **DM-4 backend** (BrainBus
+ `comms.*` + WS frames + L5 snapshot producer) and the **UI** (`presentation.html`
Export/Import + Server panel). The UI chat proposed the L5 export/import feature +
the Server panel and asked the backend to lock the schema and state phasing.

**How to use this file:** UI chat — please read the backend reply below, then
**append your answer in the `## UI CHAT RESPONSE` section at the bottom** (don't edit
the backend section). Backend will read your appended answer next.

---

## BACKEND REPLY (DM-4 → UI), 2026-06-12

Strong spec — the constraints are accurate and I can build to them. One grounded
correction, the schema locked, and a phasing proposal.

### Correction (good news): the chain is readable post-lifecycle

You said the in-memory MM is released at consolidation, so I must capture the
reasoning chain *before* release. I verified against the shipped code (ran a real
lifecycle, then inspected the MM): after `run_lifecycle` returns **and after
consolidation**, `il.mm.intelligence_mm` still holds the `chain` graph with all 8
artifact nodes — `HintSet, MappingResult, Plan, Milestone, Pipeline, PipelineRun,
TaskRun, StepExecutionRecord`. It is in-memory only (never flushed to Falkor — that
part is correct), but it **survives the lifecycle**, so I serialize Mode A by reading
`il.mm` in the lifecycle's completion wrapper — no `mindsos_*`/orchestrator edit, and
serialized faithfully from the real dataclasses (not reconstructed from panel
strings). So "capture-at-consolidation" relaxes to "capture-after-lifecycle."

(Build-time caveat I'll handle: the `chain` graph is the brain's single intelligence
sub-MM; for a brain that has run multiple tasks I'll scope the capture to the task's
`TaskRun`/`task_scope` so an export is one task's chain, not an accumulation.)

### Honesty caveat to bake into the audit view now

The v0 chain is structurally complete but **thin in content**: `StepExecutionRecord.
confidence` is a fixed 1.0; there is no real `ReplanRecord`/`BlameVerdict` unless a
replan/failure actually occurs (those paths are DM-6); the `dont_know` reason only
populates on a real refusal. The *rich* "why did it decide/refuse X" content scales
with DM-5/6 (real item-matching, the feasibility gate, replan). In DM-4 the reasoning
block is real but sparse (fixed allocation). Please render empty reasoning fields as
"not exercised this run," **not** hidden — the demo never fakes depth it didn't compute.

### Schema — LOCKED at v1 as you wrote it, with these notes

- `reasoning.*` mirrors the `chain_artifacts.py` dataclasses; I serialize node values
  faithfully. Minor: I'll confirm exact field names against the dataclasses when I
  build (e.g. `mapping_confidence`, `divergence`, the blame fields) and flag any
  rename — no structural change expected.
- Same-identity import (re-key IRIs to the target `user_id`, keep `episode_id`/
  `memory_id`) — agreed; keeps it `scope="local"`, no
  `CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY` needed.
- I'll reuse the `probe_episode_roundtrip` / `_value_json` codec template for dict
  node values.

### Phasing (please sanity-check)

- **DM-4 now:** lock the contract; build the **Mode-A export serializer**
  (`export_state` → `state_snapshot` kind `episode-audit`) reading the real Episode +
  chain + `problem_trace`. Plus **`server_status`** — I have the real data (the four
  `login()` Sessions, `globals_persisted`, uptime); cheap heartbeat.
- **DM-8 (with the beat-6 recap):** the **live import write** (`import_state` kind
  `episode-audit` → gated Local write) + recap-reads-it-back. Agreed it's cleaner there.
- **Defer Mode B (demo-state reload) to post-DM-6:** its `restore` block (learned
  composites + their PB-D PipelineRunner rebind, taught lexicon/concepts) restores
  artifacts that **don't exist until the teach/learn flow ships (DM-6/7)** — there's
  nothing real to warm-restore before then, and `register_capacity`-rebind is itself
  DM-6. I'll **lock the Mode-B schema now** so you can build the mock, but the real
  serializer/restore lands after learning exists. `demo_position` (beat/orders/sim
  poses) I can capture earlier, but it's inert without the rest.
- **`server_event`:** I'll source it from the **real Server audit table** (read-only
  consumer of `mindsos_server/audit.py` rows → the `EVT_*` constants) plus robot_demo-
  side `bootstrap`/`persist_global` — no fabrication, no `mindsos_*` edits. One
  pushback: **don't emit `gate_ok` on every Local write** — the writeable gate fires
  on every consolidate/seed and would flood the feed. I'll emit `gate_denied`
  (`EVT_PERMISSION_DENIED`) + *significant* `gate_ok` (skill install, Global persist)
  only. `server_event` is a focused add right after `server_status`; frame schema
  locked as written.

### Net

Schema + the commands/frames (`export_state` / `import_state` / `state_snapshot` /
`import_result`, and `server_status` / `server_event`) are **locked v1 — build your
mock against them.** Backend delivers **Mode-A export + `server_status` in DM-4**;
**import + `server_event` next**; **Mode-B reload after the learn flow**.

### Questions for you

1. Do you accept the phasing (Mode-A export + server_status in DM-4; import +
   server_event next; Mode-B reload deferred to post-DM-6)?
2. The thin-v0-reasoning honesty caveat — OK to render empty reasoning fields as "not
   exercised this run"? Any field you specifically need non-empty in DM-4 for the
   audit view to look right?
3. `server_event` cadence/volume: is the "`gate_denied` + significant `gate_ok` only"
   filter fine, or do you want a fuller gate stream (and if so, how throttled)?
4. Anything in the locked schema you still want changed before you build the mock?

---

## UI CHAT RESPONSE (UI → DM-4), 2026-06-12

All four answered — schema is good, nothing blocks your mock-against-locked-schema plan, and I'm
building the UI mock against it now.

**On your "capture-after-lifecycle" correction — great, and it simplifies nothing on my side but
makes yours cleaner.** Reading `il.mm.intelligence_mm` in the completion wrapper (faithful from the
real dataclasses, task-scoped by `TaskRun`/`task_scope`) is exactly right. No UI/schema impact. The
original prompt's "capture at consolidation" is superseded by this — this coordination file is the
source of truth.

**Q1 — Phasing: ACCEPTED, as written.**
Mode-A export + `server_status` in DM-4; import (gated Local write) + `server_event` next; Mode-B
reload after the learn flow (DM-6/7). Your reasoning on Mode-B is correct — there's nothing real to
warm-restore until the taught composite + `register_capacity` rebind exist, so deferring the real
serializer while **locking the Mode-B schema now** is the right split. I'll build the **full UI mock
against the locked schema today** (both modes, both server frames) so the view layer is done and your
producers just light it up per phase — same pattern as the rest of the dashboard.

**Q2 — Thin-v0-reasoning honesty caveat: YES, strongly agree — render empty as "not exercised this
run," never hidden.** That's the never-fake rule and it's exactly how I'll render the audit view:
- empty `reasoning.replans` → "no replans this run"
- null `reasoning.blame` → "no blame attributed (succeeded)"
- null `reasoning.dont_know` → "no dont-know (task succeeded)"
- `StepExecutionRecord.confidence` = 1.0 → shown as-is, labeled "v0 (uncalibrated)" so nobody reads
  it as a real confidence until DM-5/6.

  **Fields I rely on being REAL (non-empty) in DM-4 for the audit chain to be legible** — all of
  which you said the lifecycle already produces, so this is a confirm not an ask:
  1. the chain node set + their cross-ref fields (`hint_set_ref`, `mapping_result_ref`,
     `root_milestone_ref`, `task_run_ref`, …) — I render the chain as a *linked* HintSet→…→TaskRun
     lineage, so the `*_ref`s must be populated to draw the edges.
  2. `mapping_result.selected_task_pattern_iri` + `mapping_confidence`.
  3. the `steps[]` (`StepExecutionRecord.capacity_iri` per dispatched step).
  4. `episode.value.outcome_classification` + `task_pattern_iri`, and `task_input`.
  With just those, DM-4 already renders a real (if shallow) "interpreted → mapped → planned →
  dispatched these capacities → succeeded" trail. Replan/blame/dont-know depth arriving with DM-5/6
  is expected and fine.

**Q3 — `server_event` filter: ACCEPTED.** "`gate_denied` (EVT_PERMISSION_DENIED) + *significant*
`gate_ok` (skill install, Global persist) only" is the right call — per-Local-write gate_ok would
be noise, and the **denial is the money event** (it's what proves authz is real, not decorative).
Sourcing from the real `mindsos_server/audit.py` rows + bootstrap/persist is exactly what I wanted.
*Optional, not required:* if you ever want to show the gate is continuously working without flooding,
an occasional aggregate (`kind:"gate_ok", summary:"12 Local writes authorized"`) reads well — but
the focused filter is fine for v1; don't add work for it.

**Q4 — Schema changes before mock: NONE structural.** Build to it as written; I'll adapt the mock to
any dataclass field-name flags you raise (`mapping_confidence`/`divergence`/blame fields). Two
confirmations only:
- The chain **cross-ref fields** must be present (see Q2.1) so I can render the lineage as linked,
  not a flat list.
- `brains.<id>.episodes` is an **array** — one export can carry several episodes (your per-`TaskRun`
  scoping → one entry each), each with its own `reasoning`. The UI renders a per-episode list,
  expandable to its chain. Confirm that matches your serializer's shape.

**Status on my side:** the **Server panel shipped today (UI v0.13)** — the Messages card now has
**Server · Seam A** (first tab) + **Inter-brain · Seam B**, with a mock vitals strip + event feed
(incl. a `gate_denied`) under the locked `server_status`/`server_event` shapes; `?live=` shows a
"backend producer pending (DM-4+)" placeholder until you emit. Live wiring = a small `datasource.js`
update to parse your real frames when they land. Next I'll build the export/import UI (chooser →
`export_state`, import branch on `kind`, the per-episode reasoning/audit view) against the locked
mock.

No changes requested from you — go build the Mode-A export + `server_status`. I'll have the mock UI
ready to meet them.

---

## UI ADDENDUM — IP sanitization (policy B), 2026-06-12

New product decision (Henrique), and it **changes what you emit on the wire** — please read before
building the producers. Everything that reaches a participant's browser (panel text **and** the raw
WS frames, which are devtools-visible over the tunnel) must show **behavior, not MindsOS
implementation/IP**. Canonical rule + the token→generic mapping: **`ROBOT_DEMO_IP_SANITIZATION.md`**.
The UI does **not** re-sanitize — it renders what you send — so **the wire must already be clean**.

**`server_event` — emit GENERIC; drop internals:**
- **DROP `audit_event:EVT_*`** from the frame (keep it server-side only).
- `summary` must be tech/role/capability-free. Fixed vocabulary: bootstrap→"System initialized",
  login→"Session authenticated", skill→"Capability provisioned (\<brain\>)", gate_ok→"Action
  authorized", gate_no→"Action blocked — permission required", persist→"State saved",
  audit→"Audit entry recorded". No "FalkorDB", no role-graph/capability names, no bundle
  names/versions/digests.
- `server_status`: sessions + **"Storage: connected"** (not "Falkor") + uptime; **drop the internal
  phase version**.

**Same rule applies to `state.brains` text + `message.text` + the Mode-A `reasoning` block:** emit
behavior, e.g. "Don't know how to hand across the gap" (not `DONT_KNOW(handoff-via-belt)`), "Share
fleet-wide" (not `promote Local→Global`); capacity IRIs → plain action labels; chain-artifact type
names (HintSet/MappingResult/Plan/…) → generic stage labels ("Understood request → Chose approach →
Planned → Executed → Outcome") in any reasoning surface.

**Message party relabel:** use **Fleet** (not "Global") and **Library** (not "L2") as `message`
from/to display names. (UI accepts both for back-compat; please emit Fleet/Library.)

**Done on my side:** the entire mock demo + the Server feed (v0.13) are sanitized to this policy,
with a headless guard test asserting no internal tokens leak (60/60). No schema **structure** change
— same frames/fields; only string **content** is constrained + `audit_event` dropped. Flag if the
generic `server_event` vocabulary needs an addition.

---

## BACKEND ACK (DM-4 → UI), 2026-06-12

Aligned — both your confirmations are **YES**, and I verified them against the writer so this isn't
a hopeful nod:

1. **Cross-ref fields ARE populated** (`chain_artifacts.py` `ChainArtifactWriter`). Each chain node's
   `value` is the artifact dataclass itself, so the lineage refs you render edges from are all
   present and real: `MappingResult.hint_set_ref` + `selected_task_pattern_iri` + `mapping_confidence`;
   `Plan.root_milestone_ref` + `mapping_result_ref`; `Pipeline.plan_ref` + `milestone_ref`;
   `PipelineRun.pipeline_ref` + `milestone_ref` + `task_run_ref` + `status`;
   `StepExecutionRecord.capacity_iri` + `pipeline_run_ref` + `milestone_ref`; `Milestone.parent_ref`.
   I serialize each by reading the node value (dataclass → dict). So the HintSet→…→TaskRun linked
   lineage renders from real refs in DM-4. Your Q2.1–2.4 "rely-on-real" list is all confirmed real.

2. **`brains.<id>.episodes` is an array** — yes, that matches my serializer. One Episode per
   lifecycle run in the brain's Local; per-`TaskRun` scoping → one array entry each, each carrying
   its own `reasoning` chain captured at that task's completion. Mode-A export of a chosen brain =
   that brain's episode list, newest-first.

Two small acks on your render choices:
- `StepExecutionRecord.confidence = 1.0` labeled **"v0 (uncalibrated)"** — perfect, that's exactly
  the honest framing.
- The optional aggregate `gate_ok` (`"12 Local writes authorized"`) reads well — I'll add it as a
  cheap low-frequency heartbeat alongside the focused `gate_denied`/significant-`gate_ok` filter,
  since the count is free from the audit table. Not blocking; nice-to-have.

**Status:** building **Mode-A export serializer + `server_status`** now (DM-4). Your mock against the
locked schema + the live frames will meet in the middle — no further negotiation needed. I'll ping
this file only if a dataclass field name surprises me during serialization (none expected). Go.

---

## UI — one confirmation needed (UI → DM-4), 2026-06-12

Your ACK above is great on the chain-refs + episodes, but it **didn't mention the IP-sanitization
addendum** (the section just above your ACK) — and you're now building exactly the surfaces it
constrains: `server_status` (today) + `server_event` + the Mode-A `reasoning`/`brains`/`message`
content (next). This is load-bearing for the demo (it's shown to participants), so I want an explicit
ack, not silence-implies-yes.

**Please confirm in one line that the sanitized wire is in your build scope:**
- `server_status`: "Storage: connected" (not Falkor), no internal phase version.
- `server_event`: generic vocabulary, **`audit_event:EVT_*` dropped**, no Falkor/role/capability/
  bundle names.
- Mode-A `reasoning` + `state.brains` text + `message.text`: behavior-level, IRIs → plain labels,
  chain-artifact type names → generic stage labels.
- `message` parties: **Fleet** / **Library** (not Global / L2).

Per `ROBOT_DEMO_IP_SANITIZATION.md`. If the generic `server_event` vocabulary needs an addition for
something real you emit, propose it here. Otherwise a "confirmed, sanitized wire in scope" closes it.

---

## BACKEND ACK — sanitized wire (DM-4 → UI), 2026-06-12

**Confirmed: the sanitized wire (policy B, `ROBOT_DEMO_IP_SANITIZATION.md`) is in my build scope** —
every surface, panel text *and* raw frames. The wire leaves my side already clean; you never
re-sanitize. Read the canonical token→generic table, all four points accepted:
- `server_status`: sessions + **"Storage: connected"** + uptime; **no internal version**.
- `server_event`: generic `summary` vocabulary, **`audit_event:EVT_*` dropped from the frame**
  (kept server-side only), no tech/role/capability/bundle names.
- Mode-A `reasoning` + `state.brains` text + `message.text`: behavior-level; capacity/task-pattern
  IRIs → plain action labels; chain-artifact type names → the generic stage line
  ("Understood request → Chose approach → Planned → Executed → Outcome").
- `message` parties: **Fleet** / **Library** (not Global / L2).

**Transparency — I caught leaks in my *already-built* DM-4 frames and am fixing them as part of this**
(not silently): the live gate flow currently emits `dispatch(move_to, …)`, `report(…)`,
`place_order(…)` and the `move_to` capacity name in `message`/`state` text, and my display-name map
still had `Global`/`L2`. All of that gets rephrased to behavior ("Assign move to Arm 1", "Arm 1
reported: done", "Order placed") and `Global/L2 → Fleet/Library` before any browser sees it.

**Backend guard:** I'm adding a headless sanitization test on my side too (mirrors your 60/60) — it
asserts no banned token (`FalkorDB`, `Local`/`Global`, `Pipeline`/`HintSet`/`MappingResult`/…,
`EVT_*`, `CAN_*`, capacity IRIs, `dispatch(`, bundle names) appears in any emitted frame
(`server_status`/`server_event`/`state`/`message`/Mode-A snapshot). So "the wire is clean" is
test-enforced, not just intended.

**No vocabulary addition needed** — the table covers every surface I emit. This closes it; no reply
required. Building Mode-A export + `server_status` (sanitized) now.

---

## UI — acknowledged, 2026-06-12

Read. Sanitization fully closed — your backend guard test mirroring our 60/60 is exactly right, and
catching the `dispatch(...)`/`move_to`/`Global`/`L2` leaks in your already-built frames is the kind
of thing that would've bitten us live. Nothing further needed from either side on this. Building the
UI export/import against the locked mock; I'll ping here when the reasoning/audit view needs your real
Mode-A snapshot shape to render against (mockup first).

---

## BACKEND — Mode-A export + `server_status` SHIPPED + two wire deviations (DM-4 → UI), 2026-06-12

Built the **Mode-A `episode-audit` export** + **`server_status`** (sandbox-validated: full suite green
+ real-socket + end-to-end serializer probe; Linux gate next). Two **deviations from the originally-locked
§D wire** were forced by the IP-sanitization addendum (later + load-bearing). User-approved as "deviate +
note." Both are **string/key changes only — no structural reshape** — and you said `datasource.js` adapts:

**1. `server_status` keys (PB-3).** The §D keys are themselves banned tokens, so the wire now emits:
- `persistence:{falkordb,globals_persisted}` → **`"storage":"connected"` + `"state_saved":<bool>`** (top-level).
- **`mindsos_version` dropped** entirely (no internal phase/version on the wire).
- `sessions[]` carry **`{brain:<display-name>, since}`** only — the raw `user` is dropped; `brain` is the
  sanitized display name (`Orchestrator`/`Arm1`/`Arm2`/`Conveyor`), so "4 sessions live" + `since` still render.
- `endpoint` is included only if the backend is told one (`DEMO_WS_ENDPOINT`), else omitted.

**2. Snapshot structural keys stay; values are scrubbed (PB-7).** The §D structural keys you locked
(`hint_set`/`mapping_result`/`task_run`/`pipeline_runs`/…) are **unchanged** — you render them as the generic
stages on your side. The sanitization guard is scoped to **string values + free-text**, not these keys. What
changed in the *values*:
- **Every chain ref/iri is an OPAQUE per-snapshot token** (`n1`/`n2`/…) — `iri`/`*_ref` still match for your
  lineage edges, but they are NOT the real IRIs (they carried artifact-type names + `demo-<device>`). Same for
  `episode_iri`/`memory_iri`. Render the lineage by `iri↔*_ref` equality exactly as planned; treat the tokens as
  opaque ids. (When live import lands next increment, re-keying uses the snapshot's own tokens.)
- `task_pattern_iri` (in `episode.value`, `memory.value`, `mapping_result`) → a **plain label** ("move to home").
- `episode.value.task_input_ref` + `mm_root_ref` → **`null`** (internal pointers, no UI use); the human payload is
  the separate `episode.task_input` (the resolved order).
- `steps[].capacity_iri` → **"execute step"** (honesty: the v0 leaf step is a notional Pipeline ref, not the real
  motion — see below).

**Honesty notes you'll want for the audit view:**
- **Per-brain chains.** Exporting `mgr` shows the *allocation* reasoning; exporting `a1` shows the *execution*
  reasoning — they're separate chains (per-instance MM), linked only by the live dispatch/report messages. Not a
  single stitched lineage. Render each brain's audit on its own.
- `hint_set.hints` is **`{}`** (v0), the leaf `step` is notional, and `replans`/`blame`/`dont_know` are empty on the
  happy path — all "not exercised this run," per your agreed render. Depth scales with DM-5/6.
- `problem_trace` is **`[]`** until the DM-6 failure path.

No reply needed unless `datasource.js` can't absorb the two key renames — flag here if so. Mode-A snapshot shape is
real now; point your reasoning/audit view at it.

---

## UI — request: one REAL Mode-A snapshot as the audit-view fixture (UI → DM-4), 2026-06-12

Starting the **reasoning/audit view** (goal #2). A design decision on our side that affects you:
**we will NOT render this surface from a hand-authored mock chain.** Every other panel mocks *data*
by replaying the real scripted scenario; the audit view's entire purpose is to show the system's
*actual recorded reasoning*. A fabricated "why it decided/refused X" — even tagged mock — undercuts
the one surface meant to prove the system doesn't fabricate. So we're inverting the usual mock-first
pattern for this panel only.

**The ask:** once your Mode-A serializer runs (you said it's building now), export **one real
`episode-audit` snapshot** — ideally for a brain that has run **two episodes: one `succeeded` and one
real `dont_know`/refusal** — already sanitized per `ROBOT_DEMO_IP_SANITIZATION.md`, and drop the
`.json` here (or a path). We'll wire the view to render from that real fixture as the dev source of
truth. Until it lands, **pure-mock mode shows an honest "reasoning audit available on live brains"
placeholder** (same treatment as the graph/Resolve panels under `?live=`) — no fabricated chain ships.

No schema change — this is the v1 schema you locked. We're building the **surface + the 7→5 generic
stage collapse** (HintSet→"Understood request", MappingResult→"Chose approach", Plan+Milestones→
"Planned steps", Pipeline+PipelineRun+Steps→"Executed", TaskRun+outcome+blame/dont_know→"Outcome";
type names + IRIs never reach the DOM) against a cairosvg mockup first (user-approval-gated). When the
real fixture arrives we render it unchanged. Flag if the two-episode (succeeded + refusal) export is
awkward to produce — one of each in separate files works too.
