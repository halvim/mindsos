# ADR-0201 — Amendment 1: Slice 2 capacity writer (built)

**Status:** Accepted (2026-07-21). Records the CR#4 Slice 2 build and two corrections to
`CORE_WORKITEM_TASK_INTO_L5.md` / the L5 CR found while grounding against the code.

## What shipped
`mindsos_intelligence/capacity_mm_writer.py` — `CapacityMMWriter`, the runtime instance
projection of L3 (D-1/D-3/Minting). `execute_pipeline` gained optional `mm=` /
`pipeline_run_ref=` params (B2): when an MM is supplied it records each start input and each
invocation output into `capacity_mm` as the bipartite grounding DAG — one CapacityInstance
per invocation, one DataStateInstance per output, PRODUCES/CONSUMES IntergraphEdges — under
`mm.lock` (write), never held across a dispatch. `mm=None` is byte-identical to the
pre-Slice-2 value-only path.

## Verified while grounding
- **`capacity_mm.schema is None`** (`Metagraph.__init__`, `metagraph.py:394`; `_new_sub_mm`
  attaches only an `ElementRegistry`). So free-form instance `type_name`s and PRODUCES/CONSUMES
  edge types need **no** schema/type registration — the schema-gated validation branches in
  `add_node`/`add_intergraph_edge` are skipped.
- **`add_intergraph_edge`** requires both endpoint nodes to pre-exist and the two graphs to be
  distinct (`metagraph.py:1535`, steps 3-5). The writer mints nodes before wiring edges and uses
  two graphs (datastate-instances / capacity-instances).

## Correction 1 — the "empty-room pin" is NOT flipped by Slice 2
The work item lists flipping `tests/phase_47/test_chain_artifact_emit.py:79-80` as this slice's
"non-additive breakpoint." **Incorrect.** That assertion
(`test_artifacts_live_in_intelligence_sub_mm_only`) exercises only `ChainArtifactWriter` and
asserts the *chain writer* does not leak into `capacity_mm` — which stays true. Slice 2 writes
`capacity_mm` via `execute_pipeline`, a path that test never touches. The system-wide
empty-room end-state arrives when a caller passes an MM (Step 5 / new tests), not here. Under
B2 + Phase-1 carve-out + Step 5 deferred, **no production caller passes an MM after Slice 2**,
so this slice is **additive** (writer exercised only by `tests/phase_48/test_capacity_mm_writer.py`)
and inert in prod until Step 5 wires `execution.run`.

## Correction 2 — the raw_task provenance XRef (Step 3.4) defers to Slice 3
`Metagraph.add_xref` mandates a concrete `target_id` (`metagraph.py:570`), so the DQ-1 "nullable"
provenance XRef cannot be a real row with a null target: the arc3 "None" case is simply **no XRef
row**, and arc1's `INSTANCE_OF` XRef to the pinned corpus-entry instance needs the knowledge-MM
target that **Slice 3** mints. Slice 2 therefore mints the `raw_task` root instance only
(`CapacityMMWriter.root`, exposed for the Step-5 caller); the XRef itself lands in Slice 3.

## Unchanged
`core_version` stays `phase50` (no core-package change; this is L5-side additive code).
Live-only — capacity_mm instances are not persisted (DQ-8 persists chain graphs only).
