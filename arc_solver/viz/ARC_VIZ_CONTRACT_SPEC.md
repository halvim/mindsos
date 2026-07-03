# arc-viz — contract spec

Defines the DataState contracts + capacity signatures that let arc-viz express
what the arc-solver did. arc-viz is a communication intelligence: its own L3
capacities, orchestrated by the same L4 as the solver.
**Branch:** `arc-solver-viz` (off `arc-solver`). **Home:** `arc_solver/viz/`.

Runtime-coupled, code-independent: arc-viz consumes the solver's **output
DataStates** (`arc.*`, plain dicts) by IRI; it imports nothing from
`arc_solver.spike`. Same L4 co-registers both cap-sets; the human-visual render
and the machine payload are **adapters (transport)**, not capacities.

## 0. Principles (converged)

- Communicating **is** a capacity (L3, `communication` category). L4 decides *when*.
- The record it consumes is **general / producer-agnostic**; the producer-specific
  `ingest_solve` adapts the solver's output into it, so `express` never couples.
- Outcome is an enum; **"I don't know" (abstained) is first-class.**
- `express` emits a structured artifact; human/machine renders are transport.

## 1. The seam — the solver is not touched

`ingest_solve` reads DataStates the solver **already produces** (verified shapes):

| DataState | shape (unchanged) | arc-viz takes |
|---|---|---|
| `DS_PROFILE` | `{"task_id","split","train":[{"input":{"cells"},"output":{"cells"}}],"test":[{"input":{"cells"}}]}` | subject id + grids |
| `DS_RULES` | `{"candidates":[{"text","complete",…}],"bg":int\|None}` | resolved bg + candidates |
| `DS_SELECTION` | `{"set":[…],"size":int,"text":str}` \| `None` | rule text; `None` ⇒ abstained |
| `DS_SOLVE` | `{"output":cells,"matches_withheld":bool\|None}` \| `None` | answer + verify; `None` ⇒ inapplicable |
| `DS_ENCLOSED` | `{"train":[cells…],"test":[cells…]}` \| `None` | enclosed regions |

`DS_BG_CAND`/`DS_RAW_TASK` not needed (bg = `DS_RULES["bg"]`, verify =
`DS_SOLVE["matches_withheld"]`, id = `DS_PROFILE["task_id"]`).

`decision_path` **LOCKED (v1): hard-encoded** in `ingest_solve` as the three
reasoning caps with real IRIs (`capacity_iri("reasoning", …)`) + produced
DataStates. Edge-derivation deferred until a second producer — schema unchanged.

## 2. Outcome enum

`abstained` = `DS_SELECTION is None`; `inapplicable` = selection present but
`DS_SOLVE is None`; `verified`/`wrong` = `matches_withheld` True/False;
`solved_unverified` = answer produced, `matches_withheld is None`.

## 3. Content blocks (presentation-agnostic IR)

A general `express` can't draw an ARC grid, so the record carries ordered typed
blocks; `express`/adapters understand a small closed kind-set, the ARC producer
emits grid blocks. Kinds v1: `grid_pair` `{in,out,enclosed?,label}` · `grid_single`
`{grid,label}` · `rule` `{text,complete}` · `region` `{cells,of}` · `outcome`
`{value,detail}` · `note` `{text}`. Order: train delta(s) → rule → test → answer
→ outcome (→ note).

## 4. Produced DataStates (`comm` realm, `communication` category)

`comm.expressible_record` = `{producer, subject, outcome, claim, decision_path,
content:[Block]}`. `comm.artifact` (express output) = `{header:{producer,subject,
outcome}, summary:str, content:[Block], format_version:1}`. `summary` is templated
off `claim`+`outcome` in solver vocabulary — no free generation.

## 5. Capacities (`arc_solver/viz/capabilities.py`)

`ingest_solve` — inputs `(DS_PROFILE, DS_RULES, DS_SELECTION, DS_SOLVE,
DS_ENCLOSED)` → `DS_EXPRESSIBLE_RECORD` (producer-specific). `express` — input
`DS_EXPRESSIBLE_RECORD` → `DS_ARTIFACT` (producer-agnostic). `install_viz(cl)`
registers comm DataStates + caps (combined run: `install_arc` first);
`install_viz_standalone(cl)` also registers `arc.*` input stubs (fixtures gate).

## 6. L4 dispatch + adapters

After solve: `… apply_solution → ingest_solve → express`, then transport renders
`DS_ARTIFACT` — human adapter (grids/rule/outcome, the mockup) or machine adapter
(JSON, ingested by another mind). Adapters are transport, not L3.

## 7. Gate + deferred

Gate: `./run_viz` (root) exercises `#2` recolor-enclosed (→ `verified`) and `#5`
`045e512c` (→ `abstained`, "I don't know") over fixtures — no solver, no docker.
Deferred: live combined `solve → ingest → express` L4 run; the human HTML adapter;
cross-task summary; `wrong`-outcome expected-grid render (needs `DS_RAW_TASK`);
`region`/objects/sub-piece block kinds; edge-derived `decision_path`.
