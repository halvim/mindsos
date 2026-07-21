# L5 Slice 2 CONFIRMED — capacity-MM writer / grounding DAG (ADR-0201; CR#4 Slice 2)

**Branch:** `feat/l5-slice2-capacity-writer` (tip `948c75a`)
**Gate:** 4277 passed / 12 skipped / 1 xpassed / **0 failed** (containerized full, Linux, 33m34s, 2026-07-21) — baseline 4271 + 6 new; **0 regressions**.
**core_version:** stays `phase50` (L5-side additive; no phase/role/category change).
**Sequences:** `confirmation_docs/CORE_WORKITEM_TASK_INTO_L5.md` Step 3 (Slice 2 of the L5 CR).

## Decisions (resolved with HA before code)
- **D-A — explicit writer handle** (thread the MM/writer into `execute_pipeline`, NOT the dispatcher's `_mm_handle`). The dispatcher handle is a *conditional read* surface (`dispatch.py:116` nulls it when `reads_mm=False`) and becomes a read-only `MMResolver` in Slice 3 (ADR-0200) — routing writes through it would lose write access next slice.
- **D-B — optional MM (B2).** The submind resolver (`submind_arbiter.py` holds no MM) and `phase_1` interpret-resolve (`phase_1.py:15` "no MM") legitimately run MM-less; mandatory would break arc's standalone `interpret()` and force scratch MMs. Optional lets callers migrate independently. **Guard:** the solve path (Step 5) must always pass the MM, so the no-write branch is unreachable from a real task.
- **Follow-on CRs filed** for the MM-less callers: `CORE_CR_SUBMIND_RESOLVER_MM.md` (inject the session MM into the arbiter), `CORE_CR_PHASE1_RESOLVE_MM.md` (interpret-resolve = named carve-out, recommended — the resolve chain produces what *becomes* the grounding root, so it can't ground to it).

## What shipped
- **NEW `mindsos_intelligence/capacity_mm_writer.py`** — `CapacityMMWriter`: two bipartite graphs in `capacity_mm` (DataStateInstances / CapacityInstances, ADR-0201 D-3), minted via the Slice-0 builders, `PRODUCES`/`CONSUMES` `IntergraphEdge`s, run-local type→instance index. `seed()` (start inputs), `record()` (one CapacityInstance + one DataStateInstance per output + edges), `root()` (raw_task grounding root, exposed for Step 5). All writes under `mm.lock` (write), released between steps — never held across a dispatch (`RWLock` is non-reentrant).
- **EDIT `mindsos_intelligence/pipeline_execution.py`** — `execute_pipeline` gains optional `mm=` / `pipeline_run_ref=`. MM present → seed + record the grounding DAG. `mm=None` (default) → byte-identical to the pre-Slice-2 value-only path.
- **NEW `tests/phase_48/test_capacity_mm_writer.py`** (6).
- **NEW `docs/decisions/adr/0201-amendment-1-slice2.md`**.

## Grounded corrections to the plan
1. **The "empty-room pin" is NOT flipped.** `tests/phase_47/test_chain_artifact_emit.py:79-80` exercises `ChainArtifactWriter` only and asserts the *chain writer* doesn't leak into `capacity_mm` — a path `execute_pipeline` never touches. It stays green. Slice 2 is **additive**; the phase-shaped breakpoint lands at Step 5.
2. **Provenance XRef (Step 3.4) defers to Slice 3.** `add_xref` mandates a concrete `target_id`, so the arc3 "None" case = *no XRef row*, and arc1's `INSTANCE_OF` XRef needs the knowledge-MM target Slice 3 mints. Slice 2 mints the `raw_task` root only.

## Verified API / gotchas
- `capacity_mm.schema is None` (`metagraph.py:394`; `_new_sub_mm` attaches only a registry) → free-form instance `type_name`s + PRODUCES/CONSUMES need no registration.
- `add_intergraph_edge` requires both endpoints pre-existing + distinct graphs (`metagraph.py:1535`) → mint nodes before edges, two graphs.
- Instance IRIs bypass the type validators via the out-of-charset `#` fragment (Slice-0 builders).

## Scope — inert until Step 5
No production caller passes an MM after Slice 2 (`phase_1` passes `None`, submind is its own CR, `execution.run` is still the stub). The writer is exercised only by the new tests; **+6 / 0 regressions** confirms it. Step 5 (`execution.run` → `execute_pipeline`) is the true end-to-end blocker for `arc solve task 7`.

## Tests
`tests/phase_48/test_capacity_mm_writer.py` (6): grounding DAG on MM present (1 CapacityInstance/step, 1 DataStateInstance/output, 2 CONSUMES + 2 PRODUCES); payload+type on each DataStateInstance; every minted IRI routes to `capacity_mm` via `sub_mm_for_iri`; `root()` mints `…#<task>.root`; `mm=None` value-only + rooms empty; lock never held across dispatch (`RWLock._writer_active` probe).

## Blast radius
`mindsos_intelligence/`: `capacity_mm_writer.py` (new), `pipeline_execution.py` (optional `mm=` wiring). 1 new test file. 1 ADR amendment. No core-package change (`core_version` phase50).

## Next
Slice 3 (knowledge writer + `mm_handle`) — finish `MMResolver` into the graph, wire it as the handle (un-inert `reads_mm`), mint the arc1 corpus-entry target for the raw_task provenance XRef. Then Step 5 (`execution.run` wiring) for the `arc solve task 7` e2e.

**Merge:** PR squash — `feat/l5-slice2-capacity-writer` (sha recorded on merge).
