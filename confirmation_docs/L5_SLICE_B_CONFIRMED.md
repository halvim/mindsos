# L5 capacity_mm persist — Slice B (per-run capacity_mm → Episode persistence)

**CR:** `confirmation_docs/CORE_CR_CAPACITY_MM_PERSIST_AND_SUBMIND.md` — Slice B (of A→B→C),
built per §7 PB-resolutions + project-memory `capacity-mm-persist-reopen-dq8.md` "SLICE B scope".
**Branch:** `feat/capacity-mm-persist-slice-b` (off `main` after Slice A `d82123e` / PR #62).
**Gate:** **PENDING** — Cowork built; commit on Mac, run the containerized full gate from a fresh
clone on Linux (baseline **4281** from Slice A; the pass count MUST move or the new
`tests/phase_48/test_capacity_mm_persist.py` did not run). Fill the number here after green.
**core_version:** stays `phase50` (L5-side code; no core-package / role / category change).

## What shipped (Slice B)

- **`mindsos_intelligence/mm_persister.py`** — `FalkorMMPersister.persist` is now **edge-aware**
  (PB-4): the snapshot copies `graph.edges` (was nodes-only), so the capacity grounding DAG's
  intra-graph `PRODUCES`/`CONSUMES` edges persist. Added an optional `node_value_encoder`
  (`Callable[[Node], value]`) — default reduces dataclass values via `asdict` (the chain path),
  the capacity path passes the PB-1 encode dispatch. `MMPersister` Protocol widened to match.
- **`mindsos_intelligence/capacity_persister.py`** — **NEW.** `default_encode` (PB-1 default A:
  require primitive/dict/list else `PersistenceError`), `make_node_value_encoder(encoders)` (PB-1
  dispatch on the per-DataState `encode` hint, keyed by DataState type IRI), and
  `persist_capacity_mm(persister, capacity_mm, run_graphs, *, task_id, encoders)` (PB-2: persist
  each run graph edge-aware, then a task-level **index graph** — one `CapacityRunRef` node per run
  graph — returning its `graph_id` as the `capacity_root_ref`).
- **`mindsos_capacity/datastate.py`** — added the optional brain-supplied **`encode`** callable to
  the `DataState` declaration (PB-1). Excluded from eq/hash (identity is the structural decl, not
  the encoder object); not emitted by `to_properties()` (live brain code, never node data);
  `validate_datastate` rejects a non-callable `encode`.
- **`mindsos_intelligence/consolidation.py`** — `consolidate_task` gained optional
  `capacity_graphs` / `capacity_encoders`; when supplied (with a persister) it persists them and
  sets the Episode's **7th** field `capacity_root_ref` (mirrors `mm_root_ref`). Default `None` →
  **inert** (no in-CR caller threads them; PB-3). Docstrings reverse the "capacity_mm live-only"
  language.
- **`mindsos_capacity/builtins/consolidate.py`** — docstring: Episode `value` now 7 fields incl.
  `capacity_root_ref` (rides inside the codec-encoded dict; no `DS_MM_COMPOSITE_INSTANCE` / L2
  schema change).
- **`docs/decisions/adr/0202-*.md`** — Amendment 1: reverses the "capacity_mm live-only until WSD"
  clause; documents per-run persist + index graph + `encode` hint. **`docs/decisions/adr/0176-*.md`**
  — Amendment 1: Episode gains `capacity_root_ref`. (No status flip; ADR-status gate stays green.)
- **`tests/phase_48/test_capacity_mm_persist.py`** — **NEW.** Unit (no Falkor): encode dispatch
  (registered / default / rejects non-codec-safe, incl. a bad encoder result) + index
  orchestration against a fake persister. Integration (`@pytest.mark.integration`, live Falkor): a
  writer `.graph` (nodes + PRODUCES/CONSUMES edges) persists and **reloads with edges + encoded
  payloads intact** (PB-4), and `capacity_root_ref` resolves to the index → run graph (PB-2).

## Scope — inert in prod until Step 5 (PB-3)
No in-CR path threads capacity run graphs into `consolidate_task` (the submind runs the writer but
never consolidates; the solve path's `execution.run` → `execute_pipeline` consolidation is the
out-of-CR Step 5). Slice B ships the **mechanism** behind synthetic tests. `capacity_root_ref` has
no v1 reader (dangles exactly as `mm_root_ref` does; PB-5 accepted). The encoders **map** is
supplied by whoever holds the DataState declarations (Step 5 / a brain follow-up) — core ships the
`encode` field + dispatch only, never invents encoders (note: `CapacityLayer.register_datastate`
persists `to_properties()`, so `ds.encode` is *not* recoverable from registered nodes; the caller
threads the map).

## Next
Merge Slice B (freeze on the capacity-writer surface holds until the CR lands). Then Slice C:
inject the real `MentalModel` into `SubMindArbiter` (D-B) at `intelligence_layer.py:189`; the
submind must pass a fresh `pipeline_run_ref` (Slice A now requires it).
