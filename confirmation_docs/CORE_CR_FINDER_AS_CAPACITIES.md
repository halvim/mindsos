# CORE CR — the finder as capacities (CORE-C3R1 + C3R3, merged)

**Filed:** 2026-07-31. **Status:** design agreed, owner signed off. **Nothing built.**
**Verified at:** `origin/main` `b612c93`.
**Supersedes the fix shape in:** `CORE_CR_FINDER_CYCLE_SOUNDNESS.md` (D8–D11 stand;
the *fix shape* is replaced — see §7).
**Amends:** ADR-0071 §am-2 (the finder is no longer a Python class hierarchy).
**Reads with:** ADR-0205, ADR-0206, ADR-0204, `CORE_RECONCILIATION_PLAN.md`,
`CORE_VERIFIED_FINDINGS.md`.

> **To the chat that picks this up: everything below was argued to conclusion with
> the owner and signed off. Do not re-open a section unless you have evidence the
> section itself is wrong. §8 lists what was rejected and why — read it before
> proposing an alternative, because it has probably already been rejected.**

---

## 0. The problem in one paragraph

`ConjunctionFinder.find` is a top-down recursive search: start at the target, ask
"can I produce this?", recurse. That shape needs two ad-hoc guards — a cycle
`stack` and `max_depth` — and it has two defects because the guards are
incomplete (§1). Computed **bottom-up as a fixpoint** — start from what is
available, repeatedly add whatever becomes producible, stop when nothing new
appears — self-feeding is impossible by construction, and both guards become
unnecessary. That reformulation also collapses the recursion, which is what makes
the walk expressible as a small number of dispatched capacities instead of
thousands.

---

## 1. The defects this closes

Both are **live on `main`**, reachable from the CLI `execute` verb
(`mindsos_cli/commands/brain.py:687`).

### D-B — phase 2 discards phase 1's cycle guard

Phase 1 threads a cycle `stack` and refuses a capacity that would need a DataState
already on it. Phase 2 re-tests with `frozenset()` — `pipeline.py:430` and `:462`
— so a producer phase 1 refused can still be selected during construction, and can
be selected to feed itself. It then recurses to `max_depth` and raises.

Composition is therefore **non-monotonic in the start set**: adding an available
input can make a compose *fail*.

> Line-number correction: `CORE_VERIFIED_FINDINGS.md` §1 D-B cites
> `pipeline.py:427-436, :451`. The empty-stack call sites are **398, 430, 462**.
> `:451` is wrong.

### D-E — a capacity under construction is invisible (NEW, not previously recorded)

`fired[cap_iri]` is written **after** `fire()` finishes building that capacity's
inputs. While `fire(c)` is still running, `c` is not in `fired`. If resolving one
of `c`'s inputs leads back to `c`, the `if cap_iri in fired` guard misses it and
`fire(c)` starts again.

Two outcomes:

- it recurses to `max_depth` and raises — visible;
- **it completes, and `c` is appended to `steps` twice.** `find` returns a
  `Pipeline` containing the same capacity as two distinct steps, with no error.
  `execute_pipeline` runs it twice and, because the blackboard holds one value per
  DataState IRI (D-C), the second run overwrites the first. **Wrong result,
  `success=True`.**

D-E is worse than D-B: D-B raises, D-E lies. It also falsifies the shipped
`ConjunctionFinder` docstring ("shared upstream producers fire once (memoised), so
diamonds and folds converge correctly").

### Evidence

`finder_variants_model.py` (delivered with this CR) reproduces `pipeline.py`'s
phase 1 and phase 2 exactly and swaps only the phase-2 admission rule. Over 20,000
generated capacity graphs:

| variant | `max_depth` blowups | duplicate steps |
|---|---|---|
| shipped (`frozenset()`) | — | — |
| threaded cycle stack | **369** | **25** |
| threaded stack + in-flight guard | **0** | **0** |

The three shipped conformance scenarios (all_required AND, diamond convergence,
fold fan-in) are byte-identical across all three variants.

**Settled by measurement, not argument** (owner's instruction): the `fired` memo
short-circuit is a **cost optimisation, not a correctness clause**. Running the fix
with and without `c in fired` gave identical results in all 20,000 graphs. A prior
claim in this chat that it was load-bearing was wrong and the model refuted it.

---

## 2. The design

Four capacities. Topology arrives through `CapacityContext`, never as a DataState
(§3.2). L4 dispatches all four directly.

| # | Capacity | Family | Consumes | Produces |
|---|---|---|---|---|
| 1 | `path-finding.reachable_strata` | `path-finding` — L3 functional | `core.available_datastates` | `core.reachability_strata` |
| 2 | `path-finding.producer_candidates` | `path-finding` | `core.reachability_strata` | `core.producer_candidates` *(scored)* |
| 3 | `decision.select_producers` | `decision` — L4-support, opt-in | `core.producer_candidates`, `core.selection_policy` | `core.producer_selection` |
| 4 | `path-finding.construct_dag` | `path-finding` | `core.producer_selection`, `core.available_datastates`, `core.target_datastate` | `core.find_verdict` |

### DataStates (realm `core`, single-dot per ADR-0158)

- `core.available_datastates` — the start set.
- `core.reachability_strata` — every reachable DataState with the **round** it
  entered, and every satisfiable capacity with the round it became satisfiable.
  **The stratum number is what replaces the cycle stack.**
- `core.producer_candidates` — map, DataState → ordered **scored** producer list,
  filtered to producers whose stratum is strictly below that DataState's. Scored
  per the ADR-0204 convention so a selection capacity can consume it.
- `core.selection_policy` — the ranking policy. A value, not code.
- `core.producer_selection` — map, DataState → one chosen producer. Produced in
  **one** dispatch for the whole search, not one per node.
- `core.find_verdict` — the result type (§4).

### Why each exists

1. **`reachable_strata`** — makes D-B and D-E *structurally impossible* rather than
   guarded against. A capacity enters the satisfiable set only once all its inputs
   are already in the reachable set, so it can never be admitted to produce
   something it depends on. This is the "does the code match the concept?" answer:
   the concept is monotone reachability; the code was an unguarded recursive search.
   Deletes the cycle stack, `eligible`, the in-flight guard **and** `max_depth`.
2. **`producer_candidates`** — fixes **D-D** (`CORE_VERIFIED_FINDINGS.md` §1):
   alternatives are recorded as a value instead of being discarded inside
   `satisfiable[0]`. This is the PRE-5 the dream chat is waiting on.
3. **`select_producers`** — the producer-choice seam (C3R3). Judgement, therefore
   `decision.*` per ADR-0206 §4's own split between structural `planning.*` and
   judgement `decision.*`. Brain-shadowable. **BFS becomes a `selection_policy`
   value**, which is how "BFS becomes a method, not a class" is discharged.
4. **`construct_dag`** — pure construction over a decided selection. No search
   left in it.

### Two properties worth keeping

- **Four dispatches per find, not thousands.** This is the entire reason the
  set-at-a-time reformulation is required. Porting the existing per-node closures
  (`fire`, `cap_satisfiable`, `ds_reachable`) as capacities would dispatch once per
  recursion step, through the L4 dispatcher, grounding writer and MM lock.
- **The four form a linear chain**, each DataState written exactly once. If the
  chain is ever expressed as a `Pipeline`, `execute_pipeline` runs it with no
  blackboard clobbering. The end state (§6) comes free.

---

## 3. Constraints that must not be broken

### 3.1 The finder's DataStates stay disjoint from domain DataStates

These capacities register into the `CapacityLayer`, so the finder can see them.
That is **benign only because** no domain capacity produces or consumes a `core.*`
DataState from this set — they form a disconnected component of the bipartite
graph, unreachable from any domain target.

**If a future capacity ever consumes `core.reachability_strata`, domain searches
begin routing through the finder.** This rule belongs in the module docstring.

### 3.2 Topology arrives through `CapacityContext`, not as a DataState

The obvious design gives each capacity an input for "the graph being searched."
That value is a live `CapacityLayerView` — not serialisable, not groundable into
the MM, and ADR-0182's codec would have to carry it. It arrives through
`CapacityContext`, which is the shipped dependency-inversion pattern and is what
`CORE_RECONCILIATION_PLAN.md` already cites for C3R2 (*"a capacity, so
`CapacityContext.kl` makes the layering problem moot"*).

### 3.3 The finder is a floor: Global, and not user-removable

A Python class is always importable. Four registered capacities are not.
`path-finding` is a pre-bootstrapped *category* with **zero capacities in it
today**; `decision.*` is an opt-in installable family. So finding acquires an
install-order dependency it has never had.

**Ruling (owner, 2026-07-31):** vital architectural pieces ship **Global** and are
**not user-removable**. Removing the finder is removing the kernel — the system
fails, and the remedy is reinstalling it, not tolerating the absence. An accidental
removal has the same consequence as a deliberate one; that is not an argument for
tolerating it, it is an argument for making it impossible.

**The criterion (owner-approved, 2026-07-31):**

> **A capacity is in the floor set if the system cannot serve *any* request
> without it.**

Testable: remove it, and ask whether find, plan and execute still function *at all*.
Under this test `path-finding.*` and `decision.select_producers` are **in** — without
them nothing can be found, so nothing can be planned or run. `text.*` and
`reduction.*` are **out**: a system without them still works, it can just do less.
The test is deliberately about *capability to function*, not about how much is lost.

This is a **new rule the model did not have.** ADR-0205 §9 says realm carries
approval; it says nothing about a floor set that cannot be withdrawn. Both the rule
and the criterion must be recorded as an ADR-0205 amendment **when C2R1 lands the
Local-install path**, because that is the item that first makes user removal
possible — and C2R1 is the item that must enforce it.

---

## 4. `find_verdict` — the shape (D3)

Retiring `PipelineNotFoundError` into an honest don't-know verdict (ADR-0206 §3;
shim register S4).

- **Faithful conversion.** Every existing raise site becomes its corresponding
  verdict reason. **No new checks, no new failure modes.**
- **`reason` is a closed set, not free text** — consumers must branch on it, and
  the dream must not parse English. Five values:

  | reason | from |
  |---|---|
  | `bfs_exhausted` | `find_pipeline` / `BFSFinder` exhaustion |
  | `no_satisfiable_producer` | Conjunction phase 1 |
  | `max_depth_exceeded` | Conjunction `fire` |
  | `required_input_unproducible` | Conjunction, `all_required` |
  | `unregistered_target` | new; one line, no behaviour |

- **`unproducible` carries `(capacity, datastate)` pairs**, not bare IRIs. "Which
  DataState" is half the answer; "which capacity needed it" is the other half, and
  `fire` already has both at the raise site.
- **No `__bool__`.** A result type meaning "found or not" invites `if result:` and
  a silent wrong branch. Force `.pipeline is None` or an explicit `.found`.

**Deliberately NOT done:** an added registration check to separate caller error
from world verdict. It was considered and rejected — `views.producers_of` returns
`[]` for an unregistered IRI and never raises, so the distinction does not exist
today and adding it would be **new behaviour, not a preserved one**, breaking any
test that passes an unregistered IRI. `unregistered_target` exists as a reason for
callers that do check; the finder itself adds no check.

**Blast radius** (budget the work here, not on the registration question):
4 raise sites; `find_pipeline`'s signature; `mindsos_capacity.exceptions` and the
`__all__` export-slate sentinels (`tests/phase_30`, `tests/phase_31`);
`tests/phase_30/test_cli_capacity_find.py`'s rendered error payload;
`tests/resident_brain/test_execute.py`; `execution.py::_compose_pipeline`;
`brain.py::_do_execute`. Two known Slice-1 landmines: export-slate parity and the
Py3.10-blind CLI.

---

## 5. What "an L4 capacity" means here

Recorded because it was misunderstood once in this chat and will be again.

**No capacity lives at L4.** Every capacity declaration is in `mindsos_capacity`
(L3) — including `planning.*`, `decision.*`, `predicate.*`, `phase6.*` and
`reduction.*`. What makes a family "L4" is three properties, all in
`identifiers.py`:

1. its category is an **L4-support family**, dispatched by the L4 orchestrator
   rather than composed into domain pipelines;
2. it is **opt-in installable**, category graph created lazily at first register;
3. it is **excluded from `FUNCTIONAL_CATEGORIES`** — the count invariant stays 13.

`CATEGORY_PATH_FINDING` is already one of the 13, pre-bootstrapped into the default
Global L3, and **empty** — a reserved slot never filled. Capacities 1, 2 and 4 fill
it: they are structural graph computation, which is what an L3 functional category
is for. L4 owns the **coordination** — dispatch order and which selection policy
runs. That is the same line ADR-0206 §4 draws between `planning.*` and `decision.*`.

---

## 6. Where finding belongs, and where it will be called from

**Finding is a graph operation, not a planning operation.** A pipeline is a path in
the L3 graph the system judges appropriate. Under ADR-0206 §3 the loop
`search → find → decompose` runs **in planning**, and its output is a plan whose
milestones already name their pipelines. Execution then runs what the plan names.

**The shipped code does the opposite**, and this is a defect, not the design:
`execution.py` composes fresh at every leaf (`:506`) and every map member (`:742`),
while `PlanResult.pipeline_refs` — populated at plan-construction time
(`plan_construction.py:165, 240`) and read at `execution.py:427` — is used only for
`emit_pipeline_run` provenance. So the plan carries a reference to a pipeline it did
not choose, and the choice happens later, somewhere else. Same two-representations
defect class as `PlanResult` vs the Milestone tree.

**Decision (owner-approved):** ship the four capacities with the direct-dispatch
entry point and **leave `execution.py`'s call sites alone**. Record explicitly that
the caller moves to the planning loop at **C4R3**. The mechanism lands now, the
misplacement is named rather than hidden, and C4R3 inherits a finder it can call
instead of one it must build.

The two alternatives were rejected: plugging into today's caller as if it were
correct fails the standing rule (*does the code match the concept?*); waiting for
C4R3 removes this from the set of items that can start now, since C4R3 depends on
C3R2, C4R1 and C4R2.

---

## 7. Relationship to the prior CR

`CORE_CR_FINDER_CYCLE_SOUNDNESS.md` D8–D11 stand. What changes is the **fix shape**:
that CR proposed threading the cycle stack through phase 2. The model shows that
closes D-B but leaves D-E — 369 blowups and 25 corrupt pipelines per 20,000 graphs.
The bottom-up reformulation closes both without either guard.

D10 (optional `max_depth` on the map spec) is **superseded**: `max_depth` is retired,
not parameterised. There is no depth to bound once reachability is a fixpoint.

---

## 8. Rejected, with reasons — read before proposing an alternative

1. **Port `fire` / `cap_satisfiable` / `ds_reachable` / `eligible` as capacities
   one-for-one.** Rejected. They are per-node recursion; as capacities each
   recursion step becomes a dispatch through the L4 dispatcher, grounding writer and
   MM lock. Set-at-a-time reformulation gives four dispatches instead of thousands,
   and is what "not as they are built currently" means.
2. **Lift the four closures to private methods on `ConjunctionFinder`.** Rejected by
   the owner: it creates named Python helpers where the register wants fewer. Noted
   cost: while they remain closures inside `find()`, they cannot be tested
   individually — which is why D-B and D-E survived. `finder_variants_model.py` is
   the standing substitute and is cited from the docstring.
3. **`reduction.selection(strategy)` as a new member of the `reduction.*` family.**
   Rejected. ADR-0204 §Decision: *"Direction is fixed by the two named variants
   (**not** a parameter)"*; the module docstring: *"never a `reverse` parameter."*
   The family deliberately refuses parameterised behaviour. The shape does not fit
   either: ADR-0204 defines the family over *"a variable-size, per-member-scored
   collection"* returning **one member**; group-wise selection over a map of
   collections is a different signature. The **shape** of the proposal was accepted
   — one group-wise capacity, policy as a DataState — and lands as
   `decision.select_producers`.
4. **`reduction.argmin` as the selection capacity.** Rejected for the same reason:
   `argmin` selects one member from one collection globally. Producer selection needs
   one choice per DataState, and no group-wise reduction primitive exists. (Adjacent
   to arc3's recorded blocker — *cross-product over two collections, not a map over
   one*. Same missing shape.)
5. **Running selection through a `fold` milestone.** Rejected. `_run_fold_milestone`
   is executor machinery dispatching a plan-named L3 reducer via
   `spec["reducer_iri"]`; `reduction_v0.py` states its capacities are *"**not**
   `execution.py` fold reducers."* Separately, the map's ∀-abort (`MemberAbortError`
   after `MEMBER_RETRY_CAP = 2`) is wrong semantics here: a DataState with no
   candidates is legitimate under `any_of` and is skipped today, but as a map member
   it would abort the whole plan.
6. **A "finding recurses through execution" objection.** Raised in this chat and
   **withdrawn — it was wrong.** It reasoned from `execution.py`'s current
   composition-per-leaf as if that were the architecture. See §6: finding happens in
   planning, so there is no regress.
7. **Keeping `PipelineNotFoundError` and adding a non-raising `try_find`.**
   Rejected: two entry points for one operation is how `find_pipeline` vs
   `BFSFinder().find()` happened, and it contradicts the ratified position that
   no-route is a verdict rather than an exception.
8. **Returning `Optional[Pipeline]` now and enriching later.** Rejected: it deletes
   diagnosis that exists today and adds it back at C3R3 — a regression to justify
   twice. The four raise sites carry four distinct facts.

---

## 9. Scope

This merges **C3R1 and C3R3**. Capacity 3 *is* C3R3's producer-choice seam, and once
selection is a policy value, `BFSFinder` has no reason to exist — shim **S2** is
deleted in the same item. The plan's C3 chain re-numbers accordingly.

**Stopgap, recommended:** land the threaded-stack + in-flight patch first as its own
branch. Not primarily to close the bugs sooner — **for the tests.** The four
regression tests (self-feeding refused, diamond converges, fold fans in, no
duplicate step) assert *behaviour*, not implementation, so they survive the rewrite
untouched and become its acceptance bar. Without them the rewrite has nothing
proving it did not regress. The patch code is deleted by the rewrite; the tests are
the asset.

---

## 10. Owed

- `CORE_VERIFIED_FINDINGS.md` §1 — add **D-E**; correct D-B's `:451` → `:462`;
  re-pin the header from `fafc679` to `b612c93`.
- `CORE_RECONCILIATION_PLAN.md` — C3 re-numbering (§9); strike S14 and the C1R1
  "delete `mindsos_capacity/types.py`" line (C1 shipped without deleting it,
  correctly — it holds live `SessionArg` / `SessionProtocol`); correct C2R4a's claim
  that the driver writes `installed-capacities` (it does not — `boot.py:322` says the
  role is empty and the driver only stamps `installed_by` on Global L2 content).
- An ADR amending ADR-0071 §am-2, once built.
- The §3.3 floor rule, as an ADR-0205 amendment, when C2R1 lands Local install.
