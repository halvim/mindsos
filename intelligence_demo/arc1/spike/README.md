# ARC-1 Solver Spike (`spike/`)

The runnable spike for the ARC-1 task-solving pipeline. It stands up a **live
in-memory MindsOS `CapacityLayer`**, registers `arc`-realm DataStates +
capabilities, proves the perceive chain is composed by `find_pipeline` (no
router), and computes per-task analysis surfaced in a human debug interface.

This README is **navigation only** — design rationale and locked decisions live
in `../ONTOLOGY.md` (§4) and `../PIPELINE.md`. Read those for the *why*.

## Run

From the repo root:

```
python -m intelligence_demo.arc1.spike.run_spike      # registers caps, proves discovery, writes arc_debug_data.js
```

Then open `arc_debug.html` (loads the generated `arc_debug_data.js` sibling).
Needs `tomli` on Python 3.10 (3.11+ has `tomllib`). Regenerate after any
code/data change.

## Files

| File | What it is |
|---|---|
| `arc_grids.py` | Pure-Python algorithm (no MindsOS dep): components, `extract_objects`/`extract_points`, `normalize_shape`, `base_shape_name`, comparators `same_object`/`same_shape`/`same_point`/`moved`. |
| `arc_capacities.py` | Registers `arc`-realm DataStates + capabilities into the `CapacityLayer` (functional families); `ordered_catalog`. |
| `arc_profile.py` | `grid_summary`, `match_pair` (the tiered match), profile sweep, `hypotheses` fold, `build_profile`. |
| `arc_search.py` | Search index — `FACETS` (grouped) + per-task availability tokens. |
| `arc_metagraph.py` | The **Arc metagraph** L3 overlay (operand sections as graphs + `requires` edge). |
| `run_spike.py` | Entry point — registration, `find_pipeline` discovery proof, writes `arc_debug_data.js`. |
| `arc_debug.html` | The human interface (side menu: Main / Search / Capacities / Map). |

## What's built (capability summary)

- **Perceive (LOCKED):** `comprehend_task → build_grid → extract_objects / extract_palette → extract_shapes`, plus `extract_points`. Discovered by `find_pipeline`.
- **Profile (LOCKED):** `compare_grid_dimension` + `compare_palette` via the L4-style sweep; `TaskProfile`.
- **Induce (partial):** object/shape/point matching (`match_pair` tiers), `moved` transform detector (per-pair candidates, same-colour + same-shape, self-guarding), the **hypotheses** fold (pair-1 induce caps persisting across all demos), and the **Arc metagraph** operand overlay (`atoms` / `object_comparator` / `profile` graphs + `moved → requires → same_shape` IntergraphEdge).
- **Human interface:** sectioned debug UI with a capability **Search** (faceted, AND-across / OR-within, hypothesis flag, inline result-pair expand) and a **Map** (interface map + search map + Arc metagraph).

## Not yet built / open

- **Reason stage** (search → verify → apply | abstain) — the original goal; not started beyond hypotheses.
- **Seed-operation freeze** (blocks `search`) — still open (`../ICECUBER_DSL.md`).
- **Parked problems P1–P5** and correspondence (P3) / generalization (P5) — see `../PIPELINE.md` "Parked problems".
- Capability **bodies are not executed via `invoke`** — `find_pipeline` walks edges; analysis is computed by the same body functions called directly.

## Canonical records

- Locked world-model decisions: `../ONTOLOGY.md` §4 (+ changelog).
- Pipeline design, build progress, parked problems: `../PIPELINE.md`.
- Interactive L2/L3/L5 graphs: `../arc_graphs.html`.
