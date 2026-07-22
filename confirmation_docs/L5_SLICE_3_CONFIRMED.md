# L5 Slice 3 CONFIRMED — knowledge-MM writer + mm_handle=MMResolver + DQ-1 provenance XRef

**CR:** `confirmation_docs/CORE_CR_L5_KNOWLEDGE_AND_CAPACITY_MM_WRITERS.md` — the umbrella
"L5 has three rooms and only one door", **Slice 3** (the last slice). Built ON the per-run +
persist capacity model (`CORE_CR_CAPACITY_MM_PERSIST_AND_SUBMIND.md`, Slices A/B/C — landed;
capacity-writer surface freeze lifted).
**Branch:** `feat/l5-slice-3-knowledge-writer` (off `main` after Slice C).
**Gate:** **4300 passed / 12 skipped / 1 xpassed / 0 failed** (containerized full, Linux, live
FalkorDB, 2026-07-22, 1:02:12). Baseline 4292 (Slice C) + **8 new**
(`tests/phase_48/test_knowledge_mm_writer.py`); **0 regressions**. The +8 confirms the new
tests ran.
**core_version:** stays `phase50` (L4/L5-side code; no core-package / role / category change).

## What shipped

- **`mindsos_intelligence/mm_resolver.py`** — the **knowledge writer**. `MMResolver.get_or_
  instantiate` now finishes the pinned version-ref **into** the IRI-dispatched sub-MM's
  `mm:instances` graph (`INSTANCE_GRAPH_ROLE`), type `MMInstance`, carrying `pin_version` +
  `instance_type` properties — instead of only the shadow dict. An `ontology:`/`episodic:`
  corpus entry therefore lands in `knowledge_mm` (it was empty by construction). The
  `self._instantiated` dict is now a run-local pin cache/index over those nodes (pinned,
  monotone-grow); the graph is the store of record — closes the ADR-0165/0166 "no shadow state
  outside the MM" invariant for the knowledge room. DQ-5 **pin** preserved. New
  `KnowledgeMMSource` (KL-backed, duck-typed on `kl` — no `mindsos_knowledge` import; layer
  isolation).
- **`mindsos_intelligence/capacity_mm_writer.py`** — `link_provenance()`: the deferred DQ-1
  provenance XRef. Nullable first-class `capacity_mm`→`knowledge_mm` XRef, `ref_type=INSTANCE_OF`
  (M1), from the `raw_task` grounding-DAG root to the pinned corpus-entry instance the knowledge
  writer minted. arc1 supplies the target; arc3 `target_id=None` → **no XRef row** (T2). Passes
  `knowledge_mm` as target metagraph so `add_xref` validates target existence before the WAL
  (P59). Deferral docstring updated.
- **`mindsos_intelligence/intelligence_layer.py`** + **`mindsos_server/boot.py`** — both L4
  dispatcher sites now inject `mm_handle=MMResolver(mm, KnowledgeMMSource(kl))` (read-only), not
  the raw `MentalModel` (which is not an `MMHandle`). Un-inerts `reads_mm` with a working handle.
  Write access stays the real `mm` threaded to the arbiter/orchestrator — L4 remains the sole L5
  writer; capacity bodies only read.
- **`mindsos_intelligence/__init__.py`** — export `KnowledgeMMSource`.
- **`docs/decisions/adr/0200-reads-mm-gates-body-read-handle.md`** — Amendment 1 (the injected
  handle is the concrete `MMResolver`; no status flip).
- **`docs/decisions/adr/0201-amendment-3-slice-3.md`** — NEW (knowledge writer into graph + DQ-1
  provenance XRef; prose-only Status Accepted, matches amendment-2 format; ADR-status gate green).
- **`tests/phase_48/test_knowledge_mm_writer.py`** — NEW, 8 tests: writer-into-graph + pin;
  monotone-grow one node per IRI; unroutable IRI rejected before any write; a `reads_mm=True`
  body reads a written value through the `MMResolver` handle (CR test 1); arc1 XRef present /
  arc3 none / missing-target rejected (P59); `KnowledgeMMSource` adapter.

## Scope / posture (inert in prod; knowledge_mm live-only)

Mirrors Slices A/C. No shipped capacity declares `reads_mm=True`, and no prod caller invokes
`link_provenance` or consolidates a solve run's capacity graph yet — those are out-of-CR **Step
5** (`execution.run` → `execute_pipeline` on the solve path). So Slice 3 is additive / inert in
prod, exercised by the new phase-48 test. `knowledge_mm` **stays live-only** (persistence was the
reopened DQ-8's job for `capacity_mm` only, Slice B). The chain-writer non-leak invariant
(`test_chain_artifact_emit.py:79-80`, both other rooms empty on the chain-only path) is
deliberately unchanged — it is a correct isolation pin, exactly as Slice A left the parallel
`capacity_mm==0` assertion; the knowledge writer's positive coverage is the new test. The
deep_copy fork provenance XRef is covered by `tests/phase_47/test_mm_fork_independence.py` (CR
test 4) — not duplicated.

## §0 "three rooms, one door" gate — CLEARED (substrate)

All three sub-MMs now have their L4 writer: `intelligence_mm` (chain writer, Phase 47),
`capacity_mm` (Slices 2/A/C), `knowledge_mm` (this slice). L4 is the one door — the read handle
is `MMResolver` (read-only, ADR-0200) and all writes go through L4-side writers holding the real
`mm`. The structural defect ("MindsOS ships an intelligence-MM but no knowledge-/capacity-MM") is
closed. What remains is **activation**, not a missing writer: **Step 5** wires the real solve path
to exercise these writes non-inertly (`execution.run` → `execute_pipeline`, mint the `raw_task`
root + call `link_provenance` with the knowledge target), and a `reads_mm=True` consumer surfaces
the read handle.

## Next

Out-of-CR **Step 5** (`execution.run` → `execute_pipeline` on the solve path) — makes the capacity
+ knowledge writes and Slice B's persist non-inert, and is where `link_provenance` gets its arc1
knowledge target from the phase-1 resolved reference.
