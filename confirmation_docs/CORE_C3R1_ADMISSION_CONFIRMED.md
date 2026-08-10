# CORE-C3R1 — step admission: confirmed

**Ships (three, all gated on the merged state, Linux, live FalkorDB):**

| item | squash | tag | gate |
|---|---|---|---|
| stale-signature sweep | `6f089c5` (#113) | `signature-sweep-confirmed` | 4489 / 12 skip / 1 xpass / **0 fail**, `test_cli` 256 |
| BFS step admission + `already_held` | `c7195f1` (#117) | `bfs-step-admission-confirmed` | 4510 / 12 / 1 / **0**, `test_cli` 256 |
| `operand_arity` step admission | `3a3b30f` (#120) | `arity-admission-confirmed` | 4522 / 12 / 1 / **0**, `test_cli` 256 |

State recorded at #118 and #121. **Decision record: ADR-0071 §amendment-4.**
Design doc: `CORE_CAPACITY_GRAPH_TRAVERSAL.md` §7.1 / §7.1b / §7.1c.

---

## 1. What was wrong

§amendment-3 fixed the two ways `ConjunctionFinder`'s two phases disagreed **with each
other**. This work fixes the two ways **either finder disagreed with the executor**: it
returned a route the executor could not run, and reported it as success. Same class as
**D-A** and **D-C** — a wrong answer reported as a right one, surfacing one dispatch later
as `InputContractError`, with nothing in between able to see it.

Plus one defect on a tagged commit: `find_pipeline` was annotated `-> Pipeline` while
returning a `FindVerdict` — the **public** entry point, what five brains were told to call,
and the SubMind arbiter's `plan_fn`. The conversion had matched a four-space *method*
indent, so the three `Finder.find` methods converted and the one module-level function did
not. Nothing caught it: the gate runs no type checker.

## 2. The deciding fact

`execute_pipeline` builds a step's inputs as
`{ds: blackboard[ds] for ds in step.input_datastates if ds in blackboard}` and **never
consults `DAGEdge`**. What decides whether a step runs is the blackboard when it is
reached, not how the DAG is drawn. Every ruling below follows from that one line.

## 3. Three predicates, and they do not live in the same place

**1 — path availability. `BFSFinder`-local. SHIPPED.** `BFSFinder` fires each capacity off
the single `via` DataState it arrived on and draws one edge, while `input_datastates` lists
them all. It now refuses a capacity unless every *other* declared input is on this path —
starts plus outputs of steps already taken, which is exactly the blackboard the executor
will build.

- **Availability, not reachability.** §26.1 ruled *reachable from the starts*. That is
  over-permissive: an input can be reachable and still not have been produced on the branch
  the walk is on, and such a route composes and dies at dispatch exactly as before.
- **`BFSFinder`-local, not shared.** `ConjunctionFinder` answers the same case by *wiring*
  the missing input as another step; refusing it there would delete routes it correctly
  builds. arc1 measured Conjunction as NOT FOUND on all three of its executed cases.
- Closes **D-A's first half**. arc1: twelve capacities in the class, three executed.

**2 — `operand_arity` on a scalar. SHARED by both finders. SHIPPED.** A capacity emits one
value per output DataState, so a consumer declaring `operand_arity=N>1` on a scalar input
can never be fed by route-finding. `operand_arity` lives only on the declaration and is
never written to the graph node — which is exactly why both finders were blind to it.
Measured **arc3 14 of 27, arc1 16 of 45**, on both finders; **inert on core**, which
declares no arity anywhere.

- **Arity on a *collection* input is NOT refused.** After ADR-0205 §amendment-3's shape-2
  ruling that is the sanctioned many-into-one form; whether the collection carries N members
  is a run-time property of the value and the executor keeps the length check. A rule that
  refused every capacity declaring arity would delete the migration's own target.
- In `ConjunctionFinder` the check sits in `cap_satisfiable`, **not** `eligible`, so it
  governs **phase 1** as well: a capacity no route can feed must not make its output look
  reachable either.

**3 — outputs meeting inputs (the original C3R1b). NOT SHIPPED.** Last by measured value,
and it lands labelled as hygiene that closes nothing: §23.4 withdrew its arc3 ground, and
the surviving grounds argue *blanket over narrow*, not *rule over no rule*.

## 4. Why the split, and why not one function

Predicate 2 is answered from a declaration alone — the same answer for every start set — so
it is computed **once per `CapacityLayerView`** (`admission.declaration_refusals`,
scope-correct, because a Local override may declare different arity than Global). Predicate
1 depends on the walk, so it is per candidate.

Both are **module-level functions over plain values** in `mindsos_capacity/admission.py`.
`ConjunctionFinder`'s checks are closures inside `find()`, and that is the recorded reason
**D-B and D-E survived to a tagged commit** — a closure cannot be called from a test.

**Two of the three are transitional.** Under the Capacity Graph Traversal rewrite a capacity
cannot feed itself and the walk only uses DataStates it already holds, so predicates 1 and 3
have nothing left to refuse. Only arity survives. The module docstring says so. Do not build
a three-way structure that must be unpicked.

## 5. `already_held`

`FindVerdict.already_held` = `found and not pipeline.steps`. **Derived, never stored** — a
zero-step pipeline already *is* the statement, and a field beside it could disagree
(ADR-0205 §5's ground, and ADR-0192's). **Not** a sixth `FIND_REASONS` value: `reason` is
`None` whenever a route was found, and *already held* **is** a route, of length zero. It
does **not** retire at the traversal rewrite — there it is the walk terminating at step zero.

Answers **ADR-0205 §amendment-3.4**, which asked C3 for it and carried a strictly worse
C2-local fallback. **C2R4 must not build that fallback**; it reads the property instead of
inferring zero members from four separate absences.

## 6. Guards added (both verified able to go RED)

- `tests/architecture/test_finder_return_annotations.py` — **structural, not a list of
  names**: R1 a function returning a `FindVerdict`, R2 a function returning
  `<X>Finder(...).find(...)`, R3 `find` on a `Finder` subclass. Verified by running it
  against `git show origin/main:mindsos_capacity/pipeline.py` at the shipped commit, where
  it reports the defect. A fifth finder is covered the day it is written.
- `InputContractError.kind` is pinned by an AST scan of `capacity.py`'s raisers **plus** a
  docstring check — a docstring cannot be gated, so the set is.

## 7. What every brain needs to know

**Nothing that previously *ran* stops running.** Verified at all four `execute_pipeline`
call sites (`execution.py:548`, `:785`, `phase_1.py:177`, `submind_arbiter.py:220`): each
seeds the blackboard filtered to `pipeline.start_datastates`, so the condition refused by a
finder **is** the condition `_validate_inputs` would have raised on. What moves is where the
failure surfaces — an honest no-route instead of a crash one dispatch later.

**Reachability is deliberately narrower than the Phase 30/42 BFS.** A brain that needs
multiple inputs wired must name `ConjunctionFinder` for the leaf, or put the other inputs on
the blackboard before dispatch. arc1 priced and accepted this for its twelve.

**Form B is not routable over scalars**, by design. The migration target is a collection
input that **keeps** `operand_arity`, and it is contingent on
`COLLECTION_ITERATION_ADOPTION_GUIDE.md` §14.1(a).

## 8. Known and out of scope

`BFSFinder` still draws `DAGEdge` for the `via` input only, including for a step admitted
because its other inputs are on the path. Inert today — `Pipeline.edges` is read only by
`to_dict()` and the executor reads the blackboard — but **the pipeline store reads edges as
the composition links**, so a stored BFS pipeline would under-record its own wiring.
Completing them is DAG construction, which is `ConjunctionFinder`'s.

## 9. Not built — the handoff

**Ranked for the 2026-08 refocus: core plus the Decision Records demo. Brains, dream and
skill packaging come after.** The order below is *not* the order these were decided in;
that order assumed the brains were live consumers. Each entry states what is broken, what
was decided and why, what it blocks and what it does **not**, and what to verify before
touching it.

Everything here is **decided**. None of it needs a new decision from the owner unless the
entry says so.

---

### 9.1 The `.found` architecture guard — highest value under the new focus

**The problem.** `§3` of this lane's contract tells every consumer to branch on
`verdict.found` and never on `verdict.pipeline` directly. Nothing enforces it. A stale
caller that reads `.pipeline` without the guard carries a `None` past the point of failure
and dies later, harder, and further from the cause — which is the exact shape of the
`find_pipeline` annotation defect this lane opened with.

**The decision (§23.2).** **Do not write a unit test for it.** `found` is derived, so
`verdict.pipeline if verdict.found else None` is identically `verdict.pipeline`; a green
test pinned to a no-op reads as coverage of a rule it does not enforce. The honest
enforcement is an **architecture guard** of the kind the repo already runs: no `mindsos_*`
source may read `.pipeline` off a finder result without a `.found` guard in the same block.

**Why it moves to the top now.** The Decision Records demo puts new L4 consumers on the
finder's output. This guard is what stops the next one from repeating the defect, and it is
the cheapest item on this list.

**What to verify first — it is why this did not ride with item 1.** Roughly five sites
match, and **two of them are `execution.py`'s `_compose_pipeline(...).pipeline` reads,
which belong to C4R3, not here.** So the guard needs either per-site triage or one
allowlist entry naming C4R3. An allowlist entry that exempts nothing fails the sibling
guard's own staleness test, so whichever is chosen must be load-bearing. Model it on
`tests/architecture/test_no_subsystem_ownership.py` and on this lane's
`test_finder_return_annotations.py`: **structural, and shown to go RED against a real
violation before it is trusted.**

---

### 9.2 `ADR-0206 → Proposed`

**The problem.** ADR-0206 is contradicted in four places by
`CORE_REQUEST_RESOLUTION_SCENARIO.md` §8, and nothing has been built from it. It currently
reads `Accepted` on `main` while at least three artifacts describe it as `Proposed`.

**The decision.** Flip it, per `RULES.md` §9: a contradicted ADR whose new form is decided
but unbuilt becomes `Proposed`.

**Why it matters now.** ADR-0206 governs the planning-loop concepts the demo's L4 path sits
on. A governing ADR that reads `Accepted` while its content is superseded is how a later
chat builds against the wrong contract.

**What to verify first.** RULES §9 makes a status change **four edits** — front-matter
`status:`, the prose `**Status:**` line, the `docs/decisions/adr/README.md` row, and any
summary-table cell. `tools/check_adr_status_consistency.py` is the pre-filter; it must stay
green. Note that a separate proposal to split `status:` into two fields
(`status:` = agreement, `implemented:` = tag or CR) is agreed but **not in the repo** — if it
lands first, this flip changes shape. Check before editing.

---

### 9.3 The `input_group` retirement — a real defect, but **inert for the demo**

**The problem, precisely.** This is **D-A's second half**. `_validate_inputs`
(`capacity.py`) returns early when `input_group == INPUT_GROUP_FOLD`, **before every
check** — required inputs, unexpected inputs and `operand_arity` alike. A capacity
declaring `fold` therefore runs on a subset of its declared inputs and reports success.
That is the same wrong-answer-reported-as-right class the rest of this lane closed.

**The decision.** Retire the **whole concept**, not two of its values: `fold`, `any_of` and
the field. Retiring `fold` and `any_of` leaves one legal value, and "all declared inputs
are required" is simply what declaring inputs means. Out with it: the field,
**ADR-0159 §amendment-1** (which introduced it), the early return, the three-way resolution
in `ConjunctionFinder`, `_input_group_of`, and the export-slate entries.

**The motivation, and the one objection kept on the record.** `fold` has zero declarations
anywhere, `exceptions.py` says it is unenforced, and there is no aggregation step — which is
*why* defect D-C exists. Many-into-one is served by collection → map → fold milestone →
`reduction.*`, which is shipped and which nilm already uses. **`any_of` was retired over a
recorded objection** — it *was* enforced, it has no replacement, and ADR-0071 §am-2 names a
real consumer. The objection is kept in `CORE_CAPACITY_GRAPH_TRAVERSAL.md` §4.2 so it is not
rediscovered as new. If `any_of` returns, it returns with a consumer attached.

**Ownership — settled, and the two records disagreed.** Coordination §26.5 assigned the
retirement to the C3 lane; a later owner decision assigned "`input_group`" to C2R4. **Both
are right about different things.** The *field* is a declaration attribute on
`_CapacityBase` read by `_validate_inputs` at L3 invoke — it is not on `Pipeline` and is not
pipeline topology, so it stays with C3. Its deferred *graph form* is **withdrawn, not
deferred** (`CORE_CAPACITY_GRAPH_TRAVERSAL.md` §9): once the field is gone there is no
subject to inherit. **C2R4 is not blocked and inherits nothing.**

**Why it ranks below the two above, under the new focus.** **Core declares no `fold`
anywhere**, and the demo's path is single-input chains, so retiring it changes no demo
behaviour. It is core hygiene that closes a genuine defect — worth doing, not urgent.

**What to verify first — a hard precondition.** The **last `fold` declaration in the world**
is arc1's `eliminate_bg_colour` (`arc_capacities.py:841`). arc1 holds moving it as its own
item, ahead of any core merge. **Deleting the constant before arc1 lands that breaks arc1's
catalog build.** With the brains deferred, either sequence this behind arc1 or accept and
state that arc1 will need a fix when it resumes. Also: this moves the export slate a
**second** time (146 → 143) across the same four count sentinels, so check no other lane is
mid-edit on them.

---

### 9.4 C3R1b — the predicate this item was originally named for

**The problem.** A capacity whose outputs intersect its inputs can be chosen to produce a
DataState it consumes.

**The decision.** Build it, **at producer eligibility inside the finder — never as a
registration raise** — and **label it as hygiene that closes nothing.**

**Why the labelling is part of the decision.** Its original ground was arc3's `grouped`
self-loop; arc3 then *executed* the case and found `moved` fails first and is not a
self-loop, so it does not fix arc3 at all. Measured as a rate over 20,000 catalogs the
blanket rule gives 0.46% against 2.69% for no rule, and the narrow variant gives **3.20% —
worse than no rule**; neither is causal, because the real failures are cycles between two
*distinct* capacities, which are legitimate and permanent. What survives is a modelling
principle — a refined DataState is a different DataState — not a defect closure. **The
grounds on record argue *blanket over narrow*, not *rule over no rule*.** Ship it saying so,
or the next reader will believe it fixed something.

**Two consequences to state when it lands.** A registration raise would have destroyed
transform composition, because arc1's `rotate` / `reflect` / `move` / `recolor` are closed
operations on a type — which is why it is an eligibility refusal. And an eligibility refusal
first *looks* to a brain like a **missing picture, not an error**: `viz_spec` recomposition
silently loses any segment routing through a refused pick.

**Where it goes.** Into `admission.declaration_refusals` beside the `operand_arity` rule —
it is a declaration predicate too, computed once per view. Near-zero cost now that the seam
exists.

---

### 9.5 The `catalog_check.py` divergence sweep — defer with the brains

**The problem.** `pipeline.py` used to tell nilm and arc1 to *"run the divergence sweep
(`mindsos_capacity.catalog_check`)"*. That module computes source / sink / orphan structure
and contains **no divergence function**, so both brains would have run a structural check,
got `ok`, and believed they had swept. The docstring now says so plainly and names this item.

**The decision (D5).** Build it in **`catalog_check.py`, not `tools/`** — `tools/` is
outside `pyproject.toml`'s `include`, so it would not ship.

**What to verify first.** The claim that sources **and producible targets** are "both already
computed by the existing x-ray" is **false**: `CatalogReport` exposes `sources` as
`(capacity, datastate)` pairs and has no producible-target set. Extending it is unscoped
work. The decision on record is to build it as specified and replace it later, with its
docstring naming the replacement.

**Rank.** It is a brain-facing tool with no core or demo consumer. Bottom of the list.

---

### 9.6 Carried, not owed here

- **`PipelineFindVerdict` → `PipelineSelection`** — deliberately deferred to **C3R3**, when
  `decision.select_producers` lands and becomes its first real consumer. `FindVerdict` is
  canonical and keeps its name; the other is a *selection*, not a *find*. Renaming an
  exported symbol with no in-flight consumer is churn.
- **Collection migration keeps `operand_arity` and gains an ordered-sequence guarantee** —
  ruled, but **brain-side**, and contingent on `COLLECTION_ITERATION_ADOPTION_GUIDE.md`
  §14.1(a), which is unanswered and is the owner's. Out of core's queue entirely under the
  new focus.
- **The four-capacity Capacity Graph Traversal rewrite** — the successor design that retires
  two of this lane's three predicates. **It is seam work, not defect closure**, and its own
  document says so: measured against the shipped finder over 20,000 catalogs it loses zero
  routes and gains zero. **Do not pick it up as demo work.** Anyone presenting it as a bug
  fix is working from a superseded reading.

---

### 9.7 Routed to the owner, not to a chat

- `COLLECTION_ITERATION_ADOPTION_GUIDE.md` **§14.1(a)**, unanswered since 2026-07-30. The
  Form-B collection migration target depends on it.
- **#99's `_select_finder` defaults single-start brains to `BFSFinder`.** After this lane,
  BFS refuses more than it used to rather than composing unrunnable routes, so the default
  is safe — but it still routes those brains to the finder that cannot *wire* multiple
  inputs. Changing the default is a one-line decision nobody has been given.

## 10. Method notes worth keeping

- **For a claim about `main`, read `main`** (`git show origin/main:<path>`). The shared
  checkout was 22 commits stale when this lane opened, and design docs still cite line
  numbers from pre-`ae63aa2` trees.
- **Diff collected node ids against `main`; never subtract totals.** Item 2's delta was
  predicted +16 and measured **+19** — two parametrized layering guards enumerate every file
  in `mindsos_capacity`, so adding a **new module** generated three cases. They pass, which
  independently confirms `admission.py` imports nothing upward.
- **A pre-filter that needs no pytest and no database:** stub `tomli`, import each test
  module, call every zero-argument `test_*`. It caught the one real regression — a test that
  pinned the very defect being fixed — before a 34-minute gate cycle. 195 modules, 834 tests.
- **Invert a test that pinned a defect; do not delete it.** `test_finder_seam`'s old
  assertion *was* D-A, so a later reader can see it was chosen away rather than lost.
