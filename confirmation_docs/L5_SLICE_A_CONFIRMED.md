# L5 capacity_mm persist — Slice A CONFIRMED (per-run graph + no run_ref default)

**CR:** `confirmation_docs/CORE_CR_CAPACITY_MM_PERSIST_AND_SUBMIND.md` — Slice A (of A→B→C).
**Branch:** `feat/capacity-mm-persist-slice-a` (off `main` @ `a4e4e12`).
**Gate:** **4281 passed / 12 skipped / 1 xpassed / 0 failed** (containerized full, Linux, live
FalkorDB, 2026-07-21, 32m28s). Baseline 4277 + net-new; **0 regressions**. Targeted
`tests/phase_48/test_capacity_mm_writer.py` = 9 passed.
**core_version:** stays `phase50` (L5-side code; no core-package/role/category change).

## What shipped
- **`mindsos_intelligence/capacity_mm_writer.py`** — REWRITTEN to **one graph per pipeline run**
  (D-A), keyed `(task_id, pipeline_run_ref)` via `run_graph_role()` (role prefix
  `capacity:run:`). Both node-types (CapacityInstance + DataStateInstance) live in that single
  graph; `PRODUCES`/`CONSUMES` are now **intra-graph** `Graph.add_edge` (not metagraph
  `add_intergraph_edge`). Dropped the two shared role constants → exports
  `RUN_GRAPH_ROLE_PREFIX` / `run_graph_role`. Added a `.graph` property (exposes this run's
  graph for the Slice-B persister). `seed`/`root`/`record` unchanged in contract; all writes
  under `mm.lock`, never across a dispatch.
- **`mindsos_intelligence/pipeline_execution.py`** — **removed the `run_ref = task_id` default**.
  With `mm` supplied, `pipeline_run_ref` is required; `mm` present + `pipeline_run_ref=None`
  raises `ValueError`. `mm=None` byte-identical to the pre-Slice-2 value-only path.
- **`tests/phase_48/test_capacity_mm_writer.py`** — REWRITTEN to the one-graph model; replaces
  the two-graph / intergraph-edge assertions. +3 net-new: replan-does-not-overwrite,
  distinct-tasks-distinct-graphs, mm-present-without-run-ref-raises.
- **`docs/decisions/adr/0201-amendment-2-slice-a.md`** — NEW, Accepted (ADR-status gate passed).

## Why (grounded)
The origin slice (ADR-0201 am-1) wrote two **shared fixed-role** graphs told apart only by
IRI, and `execute_pipeline` **defaulted** `pipeline_run_ref` to `task_id` — a latent replan
collision (a second run re-minted identical IRIs into the same graph and overwrote the first).
D-A's one-graph-per-run fixes replan by construction, gives real isolation (a submind resolver
and a main-task solve write disjoint graphs), and makes the Slice-B persistence unit a single
per-run object.

## Scope — inert in prod until Step 5
No production caller passes an `mm` yet (phase-1 interpret is a sanctioned MM-less carve-out;
submind wiring is Slice C; `execution.run`→`execute_pipeline` is the out-of-CR Step 5). Slice A
is **additive / inert in prod**, exercised only by the phase-48 test — same posture as the
origin slice.

## Downstream decisions recorded this chat (reanalysis, user-agreed — apply in Slice B/C)
- **PB-1 (D-C):** "lean on ShapeDescriptor" is wrong (it serializes the *type shape*, not the
  value; `value_codec` hard-throws on non primitive/dict/list). → optional `encode` field on the
  `DataState` declaration (brain-supplied); core dispatches, default = require primitive/dict/list.
- **PB-2:** replan yields N run-graphs but the Episode has one `capacity_root_ref` (vs D-D
  audit-comparison). → a task-level capacity **index graph**; `capacity_root_ref` → the index.
- **PB-3:** Slice B persistence has no in-CR trigger (submind never consolidates; solve
  consolidation = out-of-CR Step 5). → ship behind synthetic tests, documented inert-until-Step-5.
- **PB-4:** intra-graph edge persist is unverified (`mm_persister` snapshot copies nodes only;
  `GraphRepository` edge round-trip never exercised). → **spike GraphRepository edge round-trip
  before finalizing Slice B**; extend the snapshot to copy edges.
- **PB-5:** `capacity_root_ref` has no v1 reader (like `mm_root_ref` dangles) — persist-ahead-of-
  consumer, accepted (architect call).

## Next
Merge Slice A → freeze holds. Then the PB-4 spike (GraphRepository intra-graph edge round-trip),
then Slice B (per-run persist + `capacity_root_ref` index + per-DataState `encode`), then Slice C
(inject the real MentalModel into `SubMindArbiter`, D-B).
