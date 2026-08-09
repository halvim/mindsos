# CORE — two-tier Local-over-Global: the finder view is a union

**Ship:** `feat/capacity-union-view`, tag `union-view-confirmed`.
**Base:** `origin/main` `54ee88c`. **Decision record:** ADR-0071 §amendment-5.
**Date:** 2026-08-09.

---

## 1. What was wrong

`pipeline._view_for` resolved a session to `capacity_layer.local_view(user_id)` and a
sessionless call to `global_view()` — one realm or the other, **never both**. A user who
registered one capacity Locally lost the entire pre-installed Global catalog for that
find. ADR-0061 states Local-over-Global as a *specialisation* rule; specialising one
member is not replacing the set.

## 2. What shipped

| File | Change |
|---|---|
| `mindsos_capacity/views.py` | `LocalPreferringView` — union of a Global and one per-user Local view, Local shadowing Global at a colliding IRI |
| `mindsos_capacity/capacity_layer.py` | `has_local(user_id)` — read-only existence check, no lazy mint |
| `mindsos_capacity/pipeline.py` | `_view_for` returns the union for a session with a Local; `_input_group_of` is scope-correct |
| `mindsos_intelligence/execution.py` | `_compose_pipeline` does ONE session-scoped find; `LeafPipelineNotFound` carries one verdict |
| `tests/architecture/test_union_view_surface.py` | structural guard over the view read surface (new) |
| `tests/phase_30/test_two_tier_composition.py` | 7 behaviour tests (new) |
| `tests/phase_30/test_find_pipeline_with_session.py` | one assertion inverted — see §5 |

## 3. The rule, stated once

**SHADOW, not merge.** A capacity IRI present in the Local metagraph hides the Global
capacity of that IRI entirely — node **and** its `PRODUCES` / `CONSUMES` edges. The union
is over the IRI *set*; at a collision exactly one side is visible. There is no per-edge
or per-field reconciliation, and no scoring.

Three consequences that are correctness clauses, not tidiness:

- **`iter_capacities` applies the shadow rule.** Otherwise §am-4's `declaration_refusals`
  computes refusals for capacities the walk can no longer reach.
- **`get_datastate` unions Local-first.** The arity predicate asks whether a declared
  input is a `collection`. A Local override may consume a Local-only DataState; a
  Global-only lookup returns `None`, the input is silently classified scalar, and a
  routable capacity is refused.
- **`successors_of` walks the union**, built from this class's own `outputs_of` /
  `consumers_of`. Delegating to either underlying view would confine the two-hop walk to
  one metagraph — the very defect being fixed.

**The `_local_iris` snapshot at construction is deliberate.** `_view_for` builds one view
per `find()`, so the snapshot gives a single find a *consistent* catalog. A view
re-reading the Local index per call could shadow a producer halfway through a walk that
had already selected it.

## 4. Why the guard is structural

`LocalPreferringView` cannot subclass `CapacityLayerView` — that class is defined over
exactly one `Metagraph`, so `metagraph` / `name` / `category_graph` / `datastates_graph`
have no honest answer on a union and are absent. It is therefore duck-typed, and that is
precisely what made the **first attempt at this class unshippable**: it implemented five
walk methods against the finder of the day; §am-4's `declaration_refusals` later began
calling `view.iter_capacities()` and `view.get_datastate()`; every session-scoped find
would have raised `AttributeError`. No test caught it because **no test asserted what a
view is**.

`tests/architecture/test_union_view_surface.py` reads every `view.<attr>` access out of
`pipeline.py` and `admission.py` by AST and fails if the union view cannot answer one. A
new call site breaks it at collection time rather than at the bottom of a 33-minute gate.

## 5. Behaviour changes

1. **A session with an empty Local now composes the Global chain** instead of finding no
   route. `test_find_pipeline_with_unpopulated_session_local_raises` asserted the old
   outcome; renamed `..._composes_global` and inverted. That expectation *was* the defect.
2. **A refused Local override is no longer papered over.** See §6.
3. **`session=None` is unaffected.** Sessionless resolves to Global alone, before and
   after.

## 6. CORE-C3R1 D5 is superseded

`_compose_pipeline` called `find` twice — Local view, then Global — and
`LeafPipelineNotFound` carried both verdicts. That existed because a single view could
only ever be one realm.

Under a union view the second call is **not a fallback, it is a bypass**. When a Local
override is refused by step admission (e.g. unroutable `operand_arity`), the union
correctly reports no route, and the Global-only retry then composes the very chain the
user overrode — silently, with no signal their capacity was skipped. Local-over-Global
has to mean the Local capacity is authoritative *including when it is broken*; anything
weaker makes an override advisory.

The retry is removed; `LeafPipelineNotFound.__init__(verdict, starts, target)` carries
one verdict. `.local` / `.global_` are gone and had no readers — the class was raised in
one place and referenced nowhere else.

D5's reasoning (only the caller making two calls should hold two verdicts) is not wrong.
It is **vacated**: there is now one call.

## 7. Gate

Merged-state, containerised, Linux, live FalkorDB. Branch tip is a direct descendant of
`54ee88c` with `origin/main` unmoved, so the tip **is** the merged state.

Delta was confirmed by **collect-only node-id diff**, not by subtracting totals:
`54ee88c` collects 4535, the branch collects 4543 — 8 added, 1 renamed, nothing else.

## 8. Known-open, deliberately not built here

- **Producer choice between a Local and a Global capacity at *different* IRIs** is still
  the existing OR-over-producers pick, with no preference rule. That seam is
  `decision.select_producers` (`CORE_CR_FINDER_AS_CAPACITIES.md`); no scoring was added.
- **`_compose_pipeline` composing a pipeline per leaf** remains the defect ADR-0206 §3
  names. The caller moves at **C4R3**; `LeafPipelineNotFound` dies with it.
- **Multi-Local / team realms** are out of scope. ADR-0061's dual-metagraph shape is
  unchanged.
- **`consolidation.py:48` and `mindsos_cli/commands/brain.py:270`** still read flat
  declarations. They resolve fixed builtins nobody overrides.
- **Skip count moved 12 → 11** between base and branch. Not investigated; no test was
  removed and the id diff accounts for every identity change.

## 9. Superseded artifact

`feat/capacity-two-tier-resolution` (`fc950b7`, PR #68) is **abandoned**, and its recorded
`4312/0` gate must not be cited. Its steps 1–2 had already landed on main independently
(`resolve_declaration`, the per-scope `_capacity_index` tuple, the dispatch/`phase_1`
migration), so its diff *reverted* ADR-0183 §am-5 lazy skill descriptors; its view raised
`AttributeError` against §am-4; and it predated both the `FindVerdict` contract and the
`request_*` → `task_*` rename.
