# L5 capacity_mm persist — Slice C CONFIRMED (SubMind resolver grounds into the real MM, D-B)

**CR:** `confirmation_docs/CORE_CR_CAPACITY_MM_PERSIST_AND_SUBMIND.md` — Slice C, the
**final** slice (of A→B→C). Landing Slice C **fully lands the CR**.
**Branch:** `feat/capacity-mm-persist-slice-c` (off `main` @ `55413ba`, after Slice B PR #63).
**Gate:** **4292 passed / 12 skipped / 1 xpassed / 0 failed** (containerized full, Linux, live
FalkorDB, 2026-07-22, ~46m). Baseline 4287 (Slice B) + **5 new**
(`tests/feat_subminds/test_submind_arbiter_grounding.py`); **0 regressions**. The +5 confirms the
new tests ran.
**core_version:** stays `phase50` (L4/L5-side code; no core-package / role / category change).

## What shipped (Slice C — D-B)

- **`mindsos_intelligence/submind_arbiter.py`** — `SubMindArbiter.__init__` now takes a
  **mandatory `mm`**: the **real** `MentalModel` the solve path threads, injected directly — **not**
  the dispatcher's `mm_handle` (which goes read-only in Slice 3 / ADR-0200). A `None` mm raises
  `ValueError`, so grounding can never be silently dropped (the narrow-writer wrapper was rejected —
  L4 is the legitimate L5 writer). `_run_resolver` now calls
  `execute_pipeline(..., mm=self._mm, pipeline_run_ref=f"pipelinerun:{task_id}")` — a fresh per-run
  ref minted from the dispatch's unique `task_id` (Slice A made `pipeline_run_ref` mandatory when
  `mm` is present). Each resolver dispatch — including a replan re-dispatch of the same need —
  grounds an isolated per-run DAG that never overwrites another run's. `_fire_fallback` (goal-
  unreachable dont-know → direct ask-human) is unchanged.
- **`mindsos_intelligence/intelligence_layer.py`** — the arbiter wiring in `start()` passes
  `mm=self._mm` (set just above, at MM construction).
- **`tests/feat_subminds/test_submind_arbiter.py`** — the `_arb` helper now builds a real empty
  `MentalModel` (mm is mandatory); no test-count change.
- **`tests/feat_subminds/test_submind_arbiter_grounding.py`** — **NEW**, 5 tests (CR §6): (1) a
  resolver run grounds one CapacityInstance + the seed/output DataStateInstances wired by intra-graph
  PRODUCES/CONSUMES in its own per-run graph; (2) two concurrent resolvers → distinct per-run graphs;
  (3) a re-dispatch (replan) does not overwrite the first run; (7) the MM-less interpret-resolve
  carve-out is unchanged (value-only, no `pipeline_run_ref` required); + the arbiter refuses a null MM.
- **`docs/decisions/adr/0189-submind-priority-and-arbitration.md`** — Amendment 1 (submind resolver
  grounds under its own `task_id`/`run_ref` scope). No status flip; ADR-status gate green.

## Scope / posture (grounds live; persist stays inert until Step 5)

The submind runs the grounding **writer live** but does **not** itself consolidate (it never calls
`consolidate_task`), so Slice C exercises **grounding** while persistence stays synthetic/inert until
out-of-CR **Step 5** (`execution.run` → `execute_pipeline` on the solve path) — matching Slice B's
posture (PB-3). The phase-1 interpret-resolve carve-out (`phase_1.py`, `mm=None`) stays MM-less
**permanently** (CR §2.5); "mandatory MM" scopes to the solve + submind paths only.

## CR fully lands — freeze lifts

Slice C is the last slice, so the CR has landed. The **capacity-writer surface freeze**
(`capacity_mm_writer.py` / `pipeline_execution.py` / `consolidation.py` / `mm_persister.py`)
**lifts**. Next L5/MM-lane work (the umbrella CR's unbuilt **Slice 3** — knowledge writer +
`mm_handle` read-only) may now build on the per-run + persist model. Out-of-CR **Step 5** (make
Slice B's persist non-inert on the solve path) remains the trigger work.
