# ADR-0201 — Amendment 2: per-run capacity graph + no run_ref default (Slice A)

**Status:** Accepted (2026-07-21). Records CR: capacity_mm persist + submind
(`CORE_CR_CAPACITY_MM_PERSIST_AND_SUBMIND.md`) **Slice A** — the reshape of the
Amendment-1 (Slice 2) capacity writer ahead of Slice-B persistence.

## Context

Amendment 1 shipped `CapacityMMWriter` writing into **two shared fixed-role
graphs** (`capacity:instances:datastates` / `capacity:instances:capacities`),
told apart only by the `(task_id, run_ref)` baked into instance IRIs, with
`PRODUCES`/`CONSUMES` as **intergraph** edges. Two problems this slice fixes:

1. **Replan collision (latent).** `execute_pipeline` defaulted
   `pipeline_run_ref` to `task_id`, and `seq` restarts per writer. A second run
   under one task re-minted identical instance IRIs into the same shared graph and
   overwrote the first run. Nothing threaded a distinct ref, so it was latent —
   it would fire the instant a replan grounds.
2. **No per-task persistence unit.** Shared graphs give no single object for a
   persister to take; you would filter the shared soup by task-id.

## Decision (D-A)

- **One graph per pipeline run**, keyed on `(task_id, pipeline_run_ref)` via
  `run_graph_role(task_id, run_ref)` (role prefix `capacity:run:`). Both
  instance node-types (CapacityInstance + DataStateInstance) live in that single
  graph.
- **`PRODUCES`/`CONSUMES` become intra-graph edges** (`Graph.add_edge`), not
  metagraph `add_intergraph_edge`. This sidesteps *intergraph*-edge persistence:
  the per-run graph is a single object the Slice-B persister takes whole (edges
  included).
- **Replan is fixed by construction** — a fresh run gets a fresh graph and fresh
  `seq` space, so it cannot overwrite an earlier run.
- **`execute_pipeline` removes the `run_ref = task_id` default.** When `mm` is
  supplied, `pipeline_run_ref` is **required**; `mm` present with
  `pipeline_run_ref=None` raises `ValueError`. `mm=None` is unchanged
  (value-only; `pipeline_run_ref` ignored).

The two Amendment-1 role constants (`DATASTATE_INSTANCE_GRAPH_ROLE`,
`CAPACITY_INSTANCE_GRAPH_ROLE`) are removed; `RUN_GRAPH_ROLE_PREFIX` /
`run_graph_role` replace them.

## Scope / not in this slice

- **Persistence is Slice B** — `capacity_root_ref` on the Episode, the
  per-DataState inspectable encoding, and the edge-aware persist path. Slice A
  writes only the live per-run graph.
- No production caller passes an `mm` yet (phase-1 interpret is MM-less by
  carve-out; the submind wiring is Slice C; `execution.run` → `execute_pipeline`
  is the out-of-CR Step 5), so Slice A remains **additive / inert in prod** —
  exercised only by `tests/phase_48/test_capacity_mm_writer.py`.

## Consequences

- `core_version` unchanged (`phase50`) — L5-side code, no core-package/role/
  category change.
- The instance-IRI builders (`datastate_instance_iri` / `capacity_instance_iri`
  / `datastate_instance_root_iri`, ADR-0201 §Minting) are unchanged; only the
  graph topology and the `run_ref` contract change.
