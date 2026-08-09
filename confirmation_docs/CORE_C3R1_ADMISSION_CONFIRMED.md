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

## 9. Not built, and owned by this lane

1. **`input_group` retirement** — **D-A's second half**: `capacity.py`'s early return for
   `fold` skips *every* input check, so such a capacity runs on a subset of its declared
   inputs and reports success. Ownership resolved with the owner (2026-08-05): the **field**
   is the C3 lane's, because it is a declaration attribute read at L3 invoke and not
   pipeline topology; its deferred **graph form** is withdrawn rather than deferred, so
   **C2R4 inherits nothing and is not blocked**. Last declaration in the world is arc1's
   `eliminate_bg_colour` (`arc_capacities.py:841`), which arc1 carries ahead of its merge.
2. **C3R1b** (predicate 3), labelled as hygiene.
3. The `catalog_check.py` divergence sweep — `pipeline.py`'s docstring named a function that
   does not exist and now says so, naming this item.
4. ADR-0206 → `Proposed`; `PipelineSelection` at C3R3; the §23.2 `.found` architecture guard
   (~5 sites, two of which are `execution.py`'s `_compose_pipeline(...).pipeline` reads that
   belong to C4R3, so it needs per-site triage or an allowlist entry).

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
