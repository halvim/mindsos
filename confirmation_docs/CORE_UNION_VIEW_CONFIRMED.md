# CORE — two-tier Local-over-Global: the finder view is a union

**Ship:** `feat/capacity-union-view`, tag `union-view-confirmed`.
**Base:** `origin/main` `54ee88c`. **Decision record:** ADR-0071 §amendment-5.
**Date:** 2026-08-09.

> ⚠ **This lane took THREE code ships, not one.** §1–§9 below describe the first
> (`8400d6f`, #122). **§10 is the rest, and §10.1 is the reason the first ship was
> incomplete.** Read §10 before treating §8's known-open list as current — two of its
> items are now closed and one new one has opened.
>
> | | |
> |---|---|
> | `8400d6f` (#122) | the union view — §1–§9. Gate 4534/0 |
> | `530162f` (#125) | the call-site sweep — §10.1. Gate 4536/0, `test_cli` 256 |
> | `01cf5e3` (#134) | two realm leaks — §10.2. Gate 4539/0 |
>
> STATE entries: `476444e` (#123), `ab30f5b` (#126), `07d9a28` (#135).
> Findings: `CORE_VERIFIED_FINDINGS.md` §14.7, §14.10, §14.11.

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
- ~~**Skip count moved 12 → 11.** Not investigated.~~ ✅ **RESOLVED — see §10.3.**

## 9. Superseded artifact

`feat/capacity-two-tier-resolution` (`fc950b7`, PR #68) is **abandoned**, and its recorded
`4312/0` gate must not be cited. Its steps 1–2 had already landed on main independently
(`resolve_declaration`, the per-scope `_capacity_index` tuple, the dispatch/`phase_1`
migration), so its diff *reverted* ADR-0183 §am-5 lazy skill descriptors; its view raised
`AttributeError` against §am-4; and it predated both the `FindVerdict` contract and the
`request_*` → `task_*` rename.

---

# 10. The rest of the lane — what #122 alone did not finish

## 10.1 The call-site sweep that belonged in #122 (`530162f`, PR #125)

`mindsos_cli/commands/brain.py`'s `pl` and `execute` **hard-coded `session=None`** at their
finder calls. That was a workaround for the *pre*-§am-5 `_view_for`, which returned the
user's Local view ALONE for any session and so hid the global builtins (it silently broke
both verbs on 2026-07-05).

**Under the union view that workaround does the opposite of its intent: it discards the
user's Local capacities.** `execute` is the only shipped path that reaches
`ConjunctionFinder`, so **the feature #122 landed was unreachable from the surface that most
needed it.** Not a regression — behaviour was identical to before #122 — but the mechanism
was inert.

`BrainREPL._finder_session(scope)` now maps `--scope global` to `None` and every other scope
to the live `stack.session`. `_do_execute` takes no scope flag and always passes the session.

> **`--scope local` does NOT mean "Local only" for COMPOSITION**, and the asymmetry with
> `_views(scope)` is deliberate: a Local-only pipeline *search* is exactly the defect §am-5
> removed. The flag still governs *listing*. Recorded in the `_finder_session` docstring and
> guarded by a source-level test so it is not "fixed" back.

**Every finder call site, audited at `476444e`** — recorded so the next reader does not
re-derive it:

| site | session | verdict |
|---|---|---|
| `intelligence_layer.py:200` (submind resolver) | `self._session` | correct — union |
| `phase_1.py:165` (reference resolve) | `dispatcher.session` | correct — union |
| `execution.py::_compose_pipeline` | `dispatcher.session` | fixed in #122 (and one find, D5 superseded) |
| `capacity.py:191` (`capacity path` CLI) | none | **correct as-is** — builds `_construct_global_layer()`, a deliberately Global tool |
| `brain.py::_do_pl` | `_finder_session(scope)` | fixed in #125 |
| `brain.py::_do_execute` | `stack.session` | fixed in #125 |

**The rule this produced:** *a doc fact is not fixed until the code encoding it is found.*
A note describing a workaround is a **pointer to code**, not a record of a solved problem.
Changing what a shared accessor returns obsoletes every workaround written against the old
behaviour, and those live in code. **Do the call-site sweep in the same PR as the contract
change**, and list every site with its verdict — *including the ones that are correct as-is
and why*.

## 10.2 Two realm leaks (`01cf5e3`, PR #134)

Both live, both independent of ADR-0205 §amendment-4, both recorded in
`CORE_VERIFIED_FINDINGS.md` (§14.7, §14.10).

**A read that minted a Local.** `read_learned_parameter_snapshot` called
`kl.local_metagraph(user)` unguarded; it lazily *creates*. This is the L4 dispatch path —
the snapshot is frozen into every request — so it is hotter than the roster read in
`mindsos_server/skills/records.py:111`, which guards the identical call for the ADR-0183
§am-6 reason. Guarded with `has_local`.

**A sessionless lookup that returned a Local.** `_declarations` is written on every
registration regardless of realm, so a Local registration overwrites the Global entry at the
same IRI — and `get_declaration` takes no session. A sessionless caller could be handed a
user's Local declaration, contradicting §am-5's own invariant. `get_declaration` now reads
the Global capacity index via `_maybe_build_lazy`, making it exactly the sessionless case of
`_resolve_declaration`. **The mirror is unchanged** and stays a Local-wins merge for
enumeration.

⚠ **Both dissolve under §amendment-4** — its §am-4.7 item 5 is right about the future and
was silent about the present. These instances were live.

**Method note worth keeping:** `_FakeKL` in `tests/learned_parameters/` did not model the
guard surface at all, so the `has_local` fix would have silently skipped the Local overlay
and broken `test_reader_local_overrides_global_per_knob`. Caught by a **standalone
stubbed-import pre-filter**, not by the 33-minute gate.

## 10.3 The skip-count move, resolved

§8 recorded 12 → 11 as uninvestigated. It is closed: of 28 skip sites only two are
content-dependent, both in `tests/resident_brain/test_brain_repl.py`. Targeted runs gave
`54ee88c` = 69 passed / 1 skipped and `ab30f5b` = 72 / 0.

**Cause:** the union view lets the ephemeral task path compose a pipeline it previously
could not, so an Episode *is* written and `test_brain_repl.py:160` ("no Episode written on
the ephemeral task path") stopped skipping. **A test that started doing real work.**

## 10.4 NEW known-open — what is an override under ADR-0205 §amendment-4?

§amendment-4 rules **one metagraph, realm as a node property**. Under one node per IRI there
is **no collision to shadow and no two stores to union** — so `LocalPreferringView` has no
referent. **The requirement survives; the class does not.**

That leaves an unruled question this lane cannot answer alone: **a user cannot hold their own
version at the same IRI, so what IS an override?** §am-4's §3 ruling states the principle —
*an override is topology, never identity*; owner-qualified IRIs are rejected as
location-encoded-in-a-reference — but declines to rule a mechanism on the ground that no
candidate has a consumer.

⚠ **That ground does not hold — see `CORE_VERIFIED_FINDINGS.md` §14.11.** A mechanism ships
today: `REF_GLOBAL_CAPACITY` + `ref_type="SPECIALISES"`, written by `register_capacity` and
exercised by a test. It is written as **node properties, not edges**, so it satisfies the
principle's intent and violates its mechanism — a walk cannot traverse a property.

⟹ The open item is not "choose a mechanism" but **"promote an existing property-encoded
reference to an edge"**, which has a consumer today, a test today, and a migration precedent
in ADR-0156. Whoever rules it must also state that such an edge **does not redirect existing
compositions** — members are frozen; using an override means a *new* composition on the same
anchor.

Also carried forward: `_declarations` is a **fourth conversion site** under §am-4 (§14.10),
and the two tests pinning the collision as executable contract convert with it —
`tests/phase_28/test_capacity_layer_local_wins.py` and
`tests/phase_30/test_invoke_local_wins_resolution.py`.
