# ADR-0201 — Amendment 3: knowledge-MM writer + DQ-1 provenance XRef (Slice 3)

**Status:** Accepted (2026-07-22). Records the L5 umbrella CR
(`CORE_CR_L5_KNOWLEDGE_AND_CAPACITY_MM_WRITERS.md`) **Slice 3** — the knowledge
writer and the deferred `capacity_mm`→`knowledge_mm` provenance XRef, built ON the
per-run + persist capacity model (Amendment 2 / Slice A; the capacity-writer surface
freeze has since lifted).

## Context

Amendments 1–2 built the capacity-MM writer (the L3 instance projection). The base
ADR named `knowledge_mm` as the room for **L2 instances** and specified the DQ-1
provenance XRef, but deferred both: `MMResolver` (the designed knowledge writer)
pinned `(iri, version)` into a shadow dict and never touched the graph, and the
capacity writer left the XRef unwritten because `add_xref` needs a concrete target
that only the knowledge writer mints (`capacity_mm_writer.py` deferral note).

## Decision (Slice 3)

- **Knowledge writer — `MMResolver` finishes instantiation INTO the graph.**
  `get_or_instantiate` now writes the pinned version-ref as a real node in the
  IRI-dispatched sub-MM's `mm:instances` graph (`INSTANCE_GRAPH_ROLE`), type
  `MMInstance`, carrying `pin_version` + `instance_type` properties. For an
  `ontology:`/`episodic:` corpus entry that lands in `knowledge_mm`, giving it a
  genuine writer (it was empty by construction). The `self._instantiated` dict
  stays as the run-local pin cache/index over those nodes (pinned, monotone-grow);
  the graph is the store of record — closing the ADR-0165/0166 "no shadow state
  outside the MM" invariant for the knowledge room. DQ-5 **pin** is preserved: the
  node is a pinned version-ref, not a copy.

- **Provenance XRef (DQ-1 / T2 / M1) — `CapacityMMWriter.link_provenance`.**
  Writes the nullable first-class `capacity_mm`→`knowledge_mm` XRef from the
  `raw_task` grounding-DAG root (minted by `root()`) to the pinned corpus-entry
  instance the knowledge writer put in `knowledge_mm`. `ref_type=INSTANCE_OF` (M1);
  the target metagraph is passed so `add_xref` validates target existence under its
  role before the WAL (P59). **Nullable (T2):** arc1 supplies the target; arc3
  passes `target_id=None` → **no XRef row** (returns `None`). The XRef is a
  metagraph-level row (ADR-0128), not a routed node — no `sub_mm_for_iri` concern;
  `validate_xref` (KL-scoped) untouched.

- **`mm_handle` is the `MMResolver`.** The L4 dispatcher's read handle is swapped
  from the raw `MentalModel` to the concrete read-only `MMResolver` (KL-backed
  `KnowledgeMMSource`), un-inerting `reads_mm` with a working handle — see ADR-0200
  Amendment 1. L4 remains the sole L5 writer; capacity bodies only read.

## Scope / not in this slice

- **`knowledge_mm` stays live-only.** Persistence was the reopened DQ-8's job for
  `capacity_mm` only (ADR-0202 am-1 / Slice B); `knowledge_mm` is not persisted.
- **Inert in prod.** No shipped capacity declares `reads_mm=True`, and no prod
  caller consolidates a solve run's capacity graph or invokes `link_provenance` yet
  (that is out-of-CR **Step 5**: `execution.run` → `execute_pipeline` on the solve
  path). Slice 3 is additive / inert in prod — exercised by
  `tests/phase_48/test_knowledge_mm_writer.py`; the deep_copy fork provenance XRef
  is covered by `tests/phase_47/test_mm_fork_independence.py` (CR test 4).
- **Chain-writer non-leak invariant unchanged.** `test_chain_artifact_emit.py:79-80`
  (both other rooms stay empty on the chain-only path) is a correct isolation pin,
  exactly as Slice A left the parallel `capacity_mm==0` assertion; the knowledge
  writer's positive coverage is the new phase-48 test, not a flip of that line.

## Consequences

- `core_version` unchanged (`phase50`) — L4/L5-side code; no core-package / role /
  category change.
- The instance-IRI builders and the two-graph→per-run topology (Amendments 1–2) are
  unchanged; this amendment adds the knowledge-room writer + the provenance XRef.
