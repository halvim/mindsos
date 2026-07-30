# DREAM PRE-0 Slice 2 — stream per-run content into the OPEN Episode (BUILD PLAN)

**Status:** SHIPPED 2026-07-30 (Slice 2a+2b; merged-state Linux gate 4415 passed / 12 skip / 1 xpass / 0 failed; tag dream-pre0-slice2-confirmed). DESIGN CONVERGED w/ HA 2026-07-29. Branch `feat/dream-pre0-slice2` off
`origin/main` @ `997a6fa` (Slice-1b ship). Authoritative model = project memory
`dream-episode-model.md`. Merged-state gate baseline = **4408**.

## Goal
Today the request's grounding + reasoning are written to Falkor only at terminal
consolidation. A crash mid-solve loses all partial work. Slice 2 writes each
pipeline run's content durably AS the run completes, so a crash keeps the partial
Episode. "Episode = saved MM": the MM has two halves that must both stream — the
**capacity_mm** grounding graphs (L5, one per run) and the **intelligence_mm**
chain graph (L4, the plan/task tree). knowledge_mm is out of scope (-> PRE-6).

## Decisions (locked w/ HA)
- **D1 — build now** even though the capacity path is inert in the v0-planner
  production runtime (no real `solve_target`). It IS gate-covered by `phase_48`
  (real-solve + map/fold + persist), so extend those tests, not net-new scaffold.
- **D2-A — never mutate the Episode NODE mid-stream.** Its content fields are
  write-once (1b). `mm_root_ref` / `capacity_root_ref` stay written ONCE at close.
  Streamed graphs are located by their DETERMINISTIC roles/names, not by a stored
  ref (graph_ids are random UUIDs — not derivable): chain by name `chain:{scope}`,
  capacity by role-prefix `capacity:run:{request_id}:`. A crashed Episode has null
  refs and is resolved by role/name.
- **D3-A — a streaming SINK replaces the plain `capacity_graphs` list.** Its
  `.append()` persists the run graph; `execution.py` is byte-unchanged (it already
  only `.append()`s + `list()`s). Byte-identical when a plain list is passed
  (v0 / simplified / tests).
- **D4-B (scoped) — stream BOTH halves.** Capacity per-run (fine, via the sink);
  chain graph at COARSE boundaries only (N1).
- **N1-A — chain flush = post-plan-construction + close ONLY.** Not per-run. The
  plan is the non-re-derivable part (planning is non-deterministic: confidence-
  driven map selection + drift); it is fixed once planning ends, so one flush
  right after plan+RequestRun preserves it. WHICH tasks completed comes from the
  per-run capacity graphs; latest-attempt-wins is resolvable from their attempt-
  keyed roles. Re-persist is a safe upsert (node upsert does unconditional
  `SET n.value=..., n += props`; verified `cypher/builders.py:164`), so the
  close re-persist overwrites the post-plan snapshot with final values.
- **N2-A — crash recovery stays minimal (no ref backfill).** The open-tolerant
  reader (Slice 3) resolves ref-less Episodes by role/name; it needs that path
  anyway for still-open Episodes.
- **N3 — DEFER knowledge_mm -> new phase PRE-6** (see DREAM_BUILD_PLAN.md).
  "Episode = saved MM" is only PARTIALLY true until PRE-6 lands.
- **N4-A — chain streaming is IN Slice 2** (past the memory's "capacity-only"
  wording), so the Episode is a coherent saved MM before Slice 3's reader.

## Durability spine (converged)
- Episode NODE (Local role `episodic_memories`): Local flush at open/suspend/close
  only (1b — UNCHANGED). No per-run Local flush (node untouched mid-stream).
- Chain graph (intelligence_mm): `mm_persister.persist` after plan-construction
  + at close. One growing graph; deterministic node-ids => idempotent MERGE.
- Capacity run graphs (capacity_mm): `mm_persister.persist` per run, via the sink.
  Each is a small, frozen, one-shot graph-scoped Falkor write (outside the MM
  lock — the run is complete when appended; only this worker touches this graph).
- Accepted-attempt-only: map retry already appends only the accepted attempt's
  graph, so rejected retries are never streamed (unchanged).

## Build steps
1. **Capacity sink** (`capacity_persister.py` or new small module): a list
   subclass `CapacityStreamSink(mm, mm_persister, encoders)` whose `append(g)`
   also does `mm_persister.persist(mm.capacity_mm, g, node_value_encoder=...)`
   (best-effort; a failed flush never fails the solve). No-op persist when
   `mm_persister is None`. Still a list for `list(capacity_graphs)` at close.
2. **Orchestrator** (`orchestrator.py`): construct the sink instead of
   `capacity_graphs: list = []` (plain list in simplified / no-persister).
   Add the post-plan chain flush: after `emit_request_run` +
   `update_priority`, `mm_persister.persist(mm.intelligence_mm,
   writer.chain_graph())` (best-effort, non-simplified, persister wired).
3. **Consolidation** (`consolidation.py` + `capacity_persister.py`): "move per-run
   persist OUT" — split `persist_capacity_mm` into `build_capacity_index(...)`
   (build + persist the index only, from the streamed run graphs) and drop the
   run-graph re-persist from the close path (already streamed). `capacity_root_ref`
   still set at close; on crash no index (reader role-scans). Chain persist at
   close stays (final values).
4. **Encoders**: the sink needs the PB-1 `node_value_encoder`; thread
   `capacity_encoders` (brain-supplied; None today) into the sink.

## Tests (extend phase_48)
- `test_capacity_mm_persist` / `test_step5_solve_execution`: assert each run's
  graph is persisted BEFORE close (persist called N times mid-run, not once at end).
- NEW: post-plan chain flush persists the chain graph before execution.
- NEW: simulated crash (no close) leaves run graphs + chain findable by
  role/name; Episode node stays `state=open` with null refs.
- Byte-identical guard: plain-list path (no persister) unchanged; dual-mode
  legacy consolidate untouched.

## Slice 3 (NEXT — outline, not this slice)
Open-tolerant reader (new module): given an `episode_id`, load the Episode (any
state); resolve grounding by `capacity_root_ref`/`mm_root_ref` when closed, else
by role/name (`chain:{scope}`, `capacity:run:{episode_id}:*`) when open/crashed;
latest replan attempt wins. **Naive whole-metagraph load accepted now**; efficient
role-scoped querying = PRE-3 (deferred). crash_recovery UNCHANGED (N2-A).

## Files (expected)
`mindsos_intelligence/`: `orchestrator.py`, `capacity_persister.py`,
`consolidation.py` (+ maybe a small `capacity_stream.py`). Tests under
`tests/phase_48/`. No schema / write-handle / consolidate-builtin changes (D2-A).

## Gate ritual (gate-hygiene)
`git fetch origin && git checkout feat/dream-pre0-slice2 && git reset --hard
origin/feat/dream-pre0-slice2 && git rev-parse --short HEAD` (CONFIRM sha) ->
`docker compose -p mindsos-core --profile test run --rm --build mindsos-test
pytest -q`. Pass-count == 4408 baseline with no new tests => stale checkout.
On landing: merge origin/main -> RE-GATE merged state -> ff to main -> tag +
STATE.json single-line recent[] insert. Delete worktree + branch at chat close.

## Open item carried
PRE-6 (knowledge_mm persistence) — decide re-resolve vs replay-exact at D-1.
