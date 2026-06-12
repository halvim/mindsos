# Prompt for the DM‑4 chat: L5 export/import + Server panel (backend contract)

> Status: **APPROVED 2026‑06‑12** (Henrique). Paste the sections below into the **DM‑4 chat**
> (Seam B / WS producer). This is the **frontend → backend contract**: what the dashboard
> (`demo_ui/presentation.html`) needs DM‑4 to produce. Pair it with `ROBOT_DEMO_WS_CONTRACT.md`.
> Decisions recorded in `ROBOT_DEMO_UI.md` §5/§7.
>
> **Two contract items in this doc:**
> 1. **L5 export/import** (header Export/Import buttons) — modes **A** per‑brain episode/reasoning
>    audit (goals 1+2), **B** whole‑demo reloadable state. Goal #2 = reasoning chain only (Server
>    governance audit deferred).
> 2. **Server panel** (new infra panel) — `server_status` + `server_event` frames so the UI can
>    prove everything is live on a real MindsOS Server.
>
> The data **schema + WS frames/commands are locked in this chat**; live import write + the Server
> feed may land alongside DM‑8, but the contract is fixed now.

---

## Paste below into the DM‑4 chat

**Feature: L5 export / import — the dashboard's header Export/Import buttons.** TWO export modes
share one snapshot format (a `kind` discriminator):

- **A · Reasoning/memory export — per brain, user‑selectable** (`kind:"episode-audit"`). The user
  picks **which brain** to audit; export its episodes + reasoning chain. Serves **goal #1** (load
  episodic memory back into a brain and see it in the recap) and **goal #2** (audit the brain's own
  **decisions/reasoning** — a navigable "why did it decide / refuse X" record per episode).
  **Goal #2 = the reasoning chain only** (the Server governance `audit` table is OUT of scope for now).
- **B · Demo‑state snapshot — whole demo, reloadable** (`kind:"demo-state"`). Export everything
  needed to **reload the demo to a saved point** (resume / recover / re‑show). Superset of A.

You (DM‑4) own the **backend producer + the snapshot schema**; the UI side wires the buttons and
renders. Build to the contract below, or push back with specifics.

### Shipped constraints you must respect (already verified against the code — don't re‑derive)

- An **Episode** is a graph Node `type_name="Episode"`, `value` = exactly 6 dict fields
  (`mindsos_knowledge/schemas/episodic_memories.py`): `task_input_ref, mm_root_ref,
  task_pattern_iri, outcome_classification, crash_marker, consolidated_at`.
  `outcome_classification ∈ {succeeded, failed, low_confidence, asked_user, dont_know}`.
- `mm_root_ref` is a **pointer** to the intelligence sub‑MM, not an embedded snapshot.
- The **reasoning chain** (`HintSet→MappingResult→Plan→Milestone→Pipeline→PipelineRun→TaskRun`
  + `ReplanRecord`, `StepExecutionRecord`, `BlameVerdict`, `MappingResult.mapping_confidence`,
  dont‑know reason) is authored by `ChainArtifactWriter` into the in‑memory MM
  (`mindsos_intelligence/chain_artifacts.py`), then the MM is **released at consolidation and is
  NOT flushed to Falkor in v1** (ADR‑0179). ⇒ **You must serialize the chain at consolidation
  time, before release** — the Episode alone cannot satisfy goal #2. You are already authoring
  these artifacts for the live thinking panels (PB‑B), so this is a capture/serialize add.
- **Faithful episode→MM reconstruction is deferred to WSD** (`retention.resolve_refs` is
  unit‑test‑only; the dream driver re‑runs from `task_input`). So import produces a **static,
  recorded audit record** for display — NOT a re‑instantiated live MM. Do not promise replay.
- **Locals are in‑memory + re‑seeded each boot** in the demo, but the round‑trip primitive works:
  `robot_demo/backend/persistence.py:probe_episode_roundtrip()` persists+reloads dict‑valued
  Episodes through the ADR‑0182 `_value_json` codec (`mindsos_core/persistence/value_codec.py`).
  Use that as the serialization template.
- **Writes ride the `writeable` gate** (ADR‑0180, `mindsos_capacity/context.py:make_writeable`):
  importing Episodes into a brain's own Local is `scope="local"` and needs **no admin capability**;
  any Global write would need `CAN_WRITE_GLOBAL`. Cross‑brain episodic **reads** are gated by
  `CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY` (+ `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY`) — so keep import
  **same‑identity** (re‑key IRIs to the target brain's user_id).
- (The Server **`audit` table** governance trail — `mindsos_server/audit.py` — is **OUT of scope
  for now** per product decision. Goal #2 is the reasoning chain only. Noted for later.)

### Demo‑state reload — additional constraints (mode B)

- **Reload is only valid at a between‑tasks stable point.** The live MM is never flushed in v1 and
  reconstruction is WSD‑deferred, so a snapshot resumes *between beats*, not mid‑task. Snapshot when
  no task is in flight; label reload honestly as "restore checkpoint," not "resume mid‑reasoning."
- **Restoring a learned skill requires CL re‑registration, not just a node write.** Writing the
  `LearnedComposite` node into Local `capacity-state` restores the *memory* of learning; to restore
  the *ability to run it* you must also `register_capacity` the composite via the PB‑D
  `PipelineRunner` rebind (artifact → callable dispatching sub‑capacities through the brain's own
  dispatcher). Do both on import.
- **Design with reset, not separately.** Reset (G‑11) = restart + Local wipe → empty start.
  Demo‑state import = the **inverse** → restore a warm state. Same `run_id` scoping; treat them as
  two ends of one mechanism. The recorded‑backup video remains the crash fallback; this is the
  state‑level checkpoint.
- **"Demo state" is bounded** (don't let it grow): per‑brain Local **learnable substrate** —
  `episodic_memories`, learned composites (`capacity-state` `LearnedComposite`), taught
  lexicon/concepts, `capacity-state`, `capacity-gaps` — **plus** scenario position (beat index,
  placed orders), sim world poses, and `run_id`. **Excludes the transient MM.**
- **All writes stay Local + own‑user** → `writeable` gate, **no admin capability** (the demo keeps
  learned composites Local, P‑5). No live Global writes.

### What to produce

**A) A snapshot serializer.**
- *Mode A (per task, at consolidation, before the MM is released):* the 6‑field Episode value; the
  `Memory` node + `MEMORY_CONTAINS_EPISODE` edges; the **reasoning** chain artifacts (serialize the
  `chain_artifacts.py` dataclasses to plain dicts); the resolved `task_input`; any referenced
  `problem-trace` entries. Key by `run_id` + brain.
- *Mode B (on demand, between tasks):* additionally the per‑brain bounded **restore** payload
  (learned composites + their artifact bindings, taught lexicon/concepts, `capacity-state`,
  `capacity-gaps`) and the `demo_position` (beat, placed orders, sim poses). Reuse the
  `probe_episode_roundtrip()` serialization template (`_value_json` codec) for dict node values.

**B) Export over WS** (extends `ROBOT_DEMO_WS_CONTRACT.md`):
- Browser → server:
  `{ "type":"command", "name":"export_state", "args":{ "mode":"episode-audit" | "demo-state", "scope":"<brain>" | "all" } }`
  - `mode:"episode-audit"` + `scope:"<brain>"` = mode A (the user picks the brain to audit).
  - `mode:"demo-state"` (scope ignored / `"all"`) = mode B (whole demo, reloadable).
- Server → browser: `{ "type":"state_snapshot", "snapshot": { …schema below, `kind` set accordingly… } }`
  (browser downloads it as JSON).

**C) Import over WS** — branch on the snapshot's `kind`:
- Browser → server: `{ "type":"command", "name":"import_state", "args":{ "snapshot": {…} } }`
- **`kind:"episode-audit"` (goal #1 — a REAL gated Local write):** write `episodes[].value` +
  `memories[]` + edges into the target brain's own Local `episodic_memories` via
  `context.writeable(role=ROLE_EPISODIC_MEMORIES, scope="local", version="v1")`, **re‑minting IRIs**
  for the target user_id (keep `episode_id`/`memory_id`), `validate_node` first. Reply
  `{ "type":"import_result", "ok":true, "loaded":{ "<brain>":N } }`. Proven by the recap reading them back.
  The **reasoning** (goal #2) is rendered by the frontend directly from the snapshot — it does NOT
  go back into a live MM.
- **`kind:"demo-state"` (mode B reload):** for each brain, restore the bounded learnable substrate —
  episodes/memories (as above) **+** taught lexicon/concepts **+** `capacity-state`/`capacity-gaps`
  **+ learned composites**, and for each learned composite **`register_capacity` it via the PB‑D
  `PipelineRunner` rebind** (so the skill is runnable, not just remembered). Then apply scenario
  position (beat, placed orders) + sim poses + `run_id`. Reply
  `{ "type":"import_result", "ok":true, "restored":{ "<brain>":{episodes,composites,terms}, … }, "scenario":{…} }`.
  Only valid when no task is in flight (see constraints).

**D) The snapshot JSON schema** (frontend parses this — keep field names exact):

```json
{
  "snapshot_version": 1,
  "kind": "episode-audit | demo-state",
  "created_at": "<iso8601>",
  "mindsos_version": "<phase/tag>",
  "scenario": "open-order",
  "run_id": "<run-scope id>",
  "demo_position": {              // present when kind=="demo-state" (mode B reload)
    "beat": 3,
    "placed_orders": [ { "...": "the composed order lines already submitted" } ],
    "sim_poses": { "box1": [0.7,-0.62], "tube1": [0.7,-0.77], "sheet1": [-0.7,-0.77] }
  },
  "brains": {
    "mgr": {
      "device_type": "manager",
      "restore": {                // present when kind=="demo-state" — the runnable warm state
        "learned_composites": [
          { "name": "load_into_box", "scope": "Local",
            "artifact": { "steps": ["pick","present","insert","attach"], "bindings": { "...": "..." } } }
        ],
        "taught_terms":   [ { "name": "depot", "scope": "Local", "kind": "term", "cells": [[2,0]] } ],
        "capacity_state": { "...": "availability + embodiment subgraph nodes (F4-min)" },
        "capacity_gaps":  [ { "...": "Local gap records (beats 1/5)" } ]
      },
      "episodes": [
        {
          "episode_iri": "episodic-memories-v1:episode:mgr:<eid>",
          "value": {
            "task_input_ref": "...",
            "mm_root_ref": "...",
            "task_pattern_iri": "task-pattern:demo:handoff-via-box",
            "outcome_classification": "succeeded",
            "crash_marker": null,
            "consolidated_at": "<iso8601>"
          },
          "task_input": { "...": "resolved order/task payload (for inspection)" },
          "reasoning": {
            "hint_set":       { "iri": "...", "hints": { "...": "..." } },
            "mapping_result": { "iri": "...", "selected_task_pattern_iri": "...", "mapping_confidence": 0.9 },
            "plan":           { "iri": "...", "root_milestone_ref": "..." },
            "milestones":     [ { "iri": "...", "name": "...", "status": "...", "replans_used": 0 } ],
            "pipelines":      [ { "iri": "...", "milestone_ref": "..." } ],
            "pipeline_runs":  [ { "iri": "...", "status": "...", "task_run_ref": "..." } ],
            "task_run":       { "iri": "...", "status": "...", "replan_history": [], "attention_score": 0 },
            "steps":          [ { "iri": "...", "capacity_iri": "a1.load_into_box", "confidence": 0.0, "milestone_ref": "..." } ],
            "replans":        [ { "iri": "...", "replan_level": "pipeline", "verdict": { "decision": "replan", "divergence": 0.0 }, "invalidated_refs": [], "spawned_refs": [] } ],
            "blame":          { "chain_level": "pipeline", "blame_score": 1.0, "rationale": "...", "milestone_ref": "...", "capacity_step_ref": "..." },
            "dont_know":      { "outcome": "dont_know", "reason": "requires grasp:jaw; provides grasp:suction" }
          },
          "problem_trace": [ { "capacity_iri": "...", "error_type": "...", "error_message": "...", "emitted_at": "<iso8601>" } ]
        }
      ],
      "memories": [
        { "memory_iri": "episodic-memories-v1:memory:mgr:tp-<hash>",
          "value": { "task_pattern_iri": "..." },
          "episode_iris": [ "episodic-memories-v1:episode:mgr:<eid>" ] }
      ]
    },
    "a1": { "...": "same shape" }, "a2": { "...": "..." }, "conv": { "...": "..." }
  }
}
```
- `kind:"episode-audit"` → omit `demo_position` and the per‑brain `restore` block; include only the
  brain(s) the user chose.
- `kind:"demo-state"` → include `demo_position` + every brain's `restore` block; `reasoning` is
  optional for reload (carry it if cheap, but it's not needed to resume — episodes are, so the recap
  still works post‑reload).
- `reasoning.*` fields with no value on a given episode → omit or `null` (e.g. `replans`/`blame`/
  `dont_know` only on the relevant beats). `reasoning` shapes mirror the `chain_artifacts.py`
  dataclasses — serialize them faithfully.

### Honesty constraints (the demo never fakes)
- Memory **load** is a real `writeable`‑gated Local write through the shipped schema/codec.
- The reasoning view is the **recorded** chain (static audit), not a live re‑instantiated MM —
  reconstruction/replay is WSD scope. Label it honestly in the UI.

### Sequencing note
The **data contract (schema + commands) should be fixed now** so the UI can build against the mock.
The capture‑at‑consolidation serializer is a natural DM‑4 add (you already author the chain).
The live import write + recap‑reads‑back can land alongside the DM‑8 beat‑6 recap if that's cleaner
— your call on phasing, but please lock the schema in this chat.

### What the UI side will do (so you know the consumer)
- Header **Export** → a small chooser: *audit a brain* (mode A, pick the brain) or *demo state*
  (mode B). Sends `export_state` with `mode`/`scope`, receives `state_snapshot`, downloads JSON.
- Header **Import** → upload JSON; the UI branches on `kind`:
  - `episode-audit` → `import_state` writes episodes into the brain; recap shows them (goal #1); a
    per‑episode **reasoning view** (HintSet→…→TaskRun + decision/replan/blame/dont‑know, from
    `reasoning` + `problem_trace`) renders the "why did it decide/refuse X" audit (goal #2).
  - `demo-state` → `import_state` restores the warm state; UI jumps to `demo_position.beat`.
- In mock mode, the UI ships representative mock snapshots of both kinds (honest "mock"); `?live=`
  uses the real frames above.

---

## Contract item 2 — Server panel (`server_status` + `server_event` frames)

**Goal:** the dashboard adds a distinct **Server / runtime panel** (infrastructure — NOT a brain
card; the Server is the orthogonal runtime envelope per CLAUDE.md) so a viewer can *see* that
everything is live on a real MindsOS Server: real sessions, capability authorization + the
`writeable` gate, audit, and Falkor persistence. These are events the Server **already produces** —
surface them over WS; do not invent any.

### `server_status` — on connect + periodic heartbeat (~2–5 s)
```json
{ "type":"server_status", "t":<ms>,
  "endpoint":"wss://brains.sanmyaku.com",
  "mindsos_version":"phase-50",
  "sessions":[ {"brain":"mgr","user":"mgr","since":"<iso8601>"},
               {"brain":"a1","user":"arm1","since":"<iso8601>"},
               {"brain":"a2","user":"arm2","since":"<iso8601>"},
               {"brain":"conv","user":"conv","since":"<iso8601>"} ],
  "persistence":{ "falkordb":"connected", "globals_persisted":true },
  "uptime_s":1234 }
```
- `sessions` = the real four `login()` Sessions (P‑1). Panel renders "4 sessions live", Falkor ✓, uptime.

### `server_event` — append to the live server feed as events happen
```json
{ "type":"server_event", "t":<ms>,
  "kind":"login|logout|bootstrap|skill_install|skill_uninstall|gate_ok|gate_denied|persist|audit",
  "actor":"admin|mgr|a1|a2|conv|system",
  "target":"a1|Global|...",
  "summary":"admin installed demo-world@1.0 on a1 (gate ✓)",
  "audit_event":"EVT_SKILL_INSTALLED",
  "ok":true,
  "detail":{ "...": "kind-specific (bundle/version/digest, role, capability, etc.)" } }
```

**Real source for each `kind` (don't fabricate):**
| kind | real source |
|---|---|
| `bootstrap` / `login` / `logout` | admin bootstrap + per‑brain `login()` (DM‑1) → `EVT_BOOTSTRAP`/`EVT_LOGIN`/`EVT_LOGOUT` |
| `skill_install` / `skill_uninstall` | `install_skill` through the ADR‑0180 gate (DM‑2) → `EVT_SKILL_INSTALLED` / `EVT_SKILL_INSTALL_REJECTED` |
| `gate_ok` / `gate_denied` | the `writeable` gate firing on every Local/Global write (ADR‑0180); denials → `EVT_PERMISSION_DENIED` |
| `persist` | Global persisted to Falkor (`robot_demo/backend/persistence.py:persist_global`) |
| `audit` | a row appended to the Server `audit` table (`mindsos_server/audit.py`) |

`audit_event` carries the real `EVT_*` constant when the event maps to an `audit` row (lets the UI
show the governance fact too — even though the standalone governance‑audit panel is deferred).

### Honesty + separation
- **Real only under `?live=`.** Mock ships a representative server‑event sequence labeled mock.
- The Server feed is **Seam‑A / lifecycle / authz / audit / persistence** — keep it **distinct from
  the inter‑brain `message` feed (Seam B)**. Different frame type, different panel.

### UI consumer
- An **infra‑styled Server card** (neutral/steel accent, **no brain‑section tabs**): a vitals strip
  (● live · N sessions · Falkor ✓ · uptime · endpoint) + a live server‑event feed (color‑coded by
  `kind`). Optionally grouped into collapsible sub‑cards (Sessions / Authorization & gate / Audit /
  Persistence) using the shipped `.subsec` component.
