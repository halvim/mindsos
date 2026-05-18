---
last_confirmed_phase: 13
---

# Promoted-pipelines role schema

System-wide learned pipelines. **2 NodeTypes, 2 EdgeTypes,
0 HyperEdgeTypes** at `strict=False`. **Global** metagraph (admin-shipped
via release; promoted from user Locals per Phase 16).

## NodeTypes

- `Pipeline` — advisory properties: `pipeline_name`, `task_type`,
  `confidence`, `n_runs`.
- `PipelineStep` — advisory properties: `capacity_iri`,
  `input_datastate`, `output_datastate`, `position`.

## EdgeTypes

- `HAS_STEP` — Pipeline → PipelineStep. Ordering via the `position`
  property on the edge (Phase 13 PB-9 — regular edge, not ordered
  hyperedge).
- `DERIVED_FROM` — Pipeline → Pipeline (provenance).

## Where it's used

Phase 16 (Promotion machinery) populates this role-graph from L4
consolidation output. Phase 30 (L3 pipeline finder) consumes for
BFS pipeline search.

## Strict-tighten status

`strict=False` (ADR-0149). PB-8 — advisory properties are module-level
constants, not Schema-resident PropertyType declarations; strict-tighten
phase converts.
