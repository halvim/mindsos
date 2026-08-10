---
title: Pipeline-finder is BFS over TYPE_COMPAT and ignores constraints
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-012]
---

# ADR-0071: Pipeline-finder is BFS over TYPE_COMPAT; ignores constraints

**Status:** Accepted

**Date:** 2026-04-21

## Context

L4 needs a default "how do I get from DataState A to DataState B" answer. The finder has two failure modes if it tries to do too much: it either returns wrong paths (ignoring constraints silently) or it returns no paths at all (when a constraint is merely advisory).

## Decision

`find_pipeline` does breadth-first search over the auto-discovered TYPE_COMPAT graph and returns the shortest path by capacity count. It does not read `:CONSTRAINT` edges. Constraint filtering is L4's responsibility, as a post-hoc pass over `iter_constraints()`.

## Consequences

**Good:**
- Deterministic default; easy to reason about; fast.
- L4 carries the policy weight, which is correct — L3 has no notion of task urgency, budget, or user preference.

**Cost:**
- L4 must tread carefully with constraints (flagged in open-concerns C2).

## Alternatives considered

1. **Dijkstra with constraint-derived edge weights** — rejected (premature given the slice's scale).
2. **A pluggable scoring function** — rejected (the abstraction is L4's to own).

## §Implementation (2026-05-25, Phase 30)

Shipped 2026-05-25 in `mindsos_capacity/pipeline.py` (NEW module):

- `find_pipeline(capacity_layer, *, session=None, start_datastate, target_datastate, max_depth=8) -> Pipeline` — free function. Raises `PipelineNotFoundError` when BFS exhausts without reaching `target_datastate`; returns `Pipeline(steps=())` when `start_datastate == target_datastate`.
- `Pipeline(start_datastate, target_datastate, steps: Tuple[PipelineStep, ...])` + `PipelineStep(capacity_iri, input_datastates, output_datastates, via_datastate: Optional[str])` — frozen dataclasses.
- `PipelineNotFoundError(CapacityLayerError)` — new raiser in `mindsos_capacity/exceptions.py`.

**BFS shape — datastate-keyed, not capacity-keyed.** The §Decision phrase "auto-discovered TYPE_COMPAT graph" is the structural substrate built by Phase 29's discovery hooks. The BFS implementation walks via `view.consumers_of(datastate_iri)` (Phase 29 view API; returns `List[Node]`), reading `cap.properties.get("outputs")` to push the next frontier. The implementation does NOT use `successors_of` (capacity-keyed walk; also Phase 29) — that primitive expresses the same TYPE_COMPAT graph in a capacity-to-capacity shape that doesn't fit a datastate-keyed BFS.

**Halvim divergences from parent reference:**
1. `find_pipeline` takes `session: SessionArg = None` (halvim Phase 28 R1 PB-14 lock; no legacy `user_id=` kw) where parent has `user_id: Optional[str] = None`.
2. The `build_bfs_capacity_declaration` scaffolding factory (parent ships it raising `NotImplementedError` for "phase-2 wrapping") is OMITTED at Phase 30 per Phase 27 R3 PB-26 precedent (no scaffolding without consumer). Phase 31 ships the registered builtin form directly when it lands.

**Shortest-by-capacity-count invariant** is locked by `tests/phase_30/test_find_pipeline_shortest_by_capacity_count.py` against a branching-capacity fixture (capacity with multiple outputs where capacity-count and edge-count diverge).

**Constraints remain ignored at the finder layer.** Phase 28's `:CONSTRAINT` edges exist but are not read by `find_pipeline`. L4 will do the post-hoc filtering pass.

Status remains Accepted.

## §Implementation (2026-05-25, Phase 31)

Pathfinding-as-registered-builtin formally retires at Phase 31.

The parent reference (`mindsos_capacity/builtins/pathfinding.py`) shipped a `build_bfs_capacity_declaration()` factory that raised `NotImplementedError` with the comment "phase-2 scaffolding — use find_pipeline() directly in the vertical slice." Halvim Phase 30 already omitted this stub per Phase 30 §Implementation halvim divergence #2 ("no scaffolding without consumer"). Phase 31's PHASE_MAP §31 line "install pathfinding" is narrowed inline to "expose for use" (recorded in `halvim_mindsos/notes-phase-31.md` §1) — `find_pipeline` (function-form, shipped Phase 30) is the canonical pipeline-finder surface at L3.

**Why retire rather than ship the registered form**: the registered form requires DataStates for `start_datastate` / `target_datastate` / `pipeline` whose `ShapeDescriptor` is genuinely synthetic — an IRI string is not a domain DataState, it is a *reference*. The parent's NotImplementedError stub admits this circular bootstrap problem. Inventing those DataStates at L3 to register a "pathfinding capacity" that wraps `find_pipeline` would (a) leak synthetic shapes into the DataState vocabulary, (b) have no consumer at Phase 31, and (c) preempt design choices L4's pipeline-planner will want to make about how it models pipelines internally. Phase 32+'s integration scenarios (Integration B) may surface a real consumer; if so, the registered form ships then with a properly-motivated DataState set. If not, the function-form is permanent.

**Halvim Phase 31 ship**:
- No code change at `mindsos_capacity/pipeline.py` (function-form intact).
- `mindsos_capacity/builtins/__init__.py` (NEW; first subpackage under `mindsos_capacity/`) intentionally does NOT re-export `Pipeline` / `PipelineStep` / `find_pipeline`; users continue importing those from `mindsos_capacity` (top-level) per Phase 30 shipping pattern.
- `build_bfs_capacity_declaration` is **never to be reintroduced** at any L3 phase without a concrete L4 consumer.

Status remains Accepted.

## §Amendment (Phase 42 — ADR-0156)

The BFS now walks the bipartite `PRODUCES`/`CONSUMES` edges (`consumers_of` via CONSUMES, `outputs_of` via PRODUCES) instead of the retired TYPE_COMPAT graph. Reachability is identical; the per-frontier hop count doubles (datastate→capacity→datastate). `find_pipeline` signature + `Pipeline` shape unchanged.

## §amendment-2 (feat/composition-lifecycle — 2026-06-21): pluggable finder seam; conjunction/fold finder; DAG result type

**Context.** A live probe (ARC reason-layer, `projects/arc_demo/.../PIPELINE_DECISIONS.md` §4) plus a code read confirm a latent correctness defect: the §Decision BFS fires a capacity from **one** reachable input (`via_datastate`) and never checks the capacity's other declared inputs. For any multi-input capacity it composes unsoundly (fires on one input, drops the rest; a fold is taken as a singleton). The defect is latent — `find_pipeline` has no production caller today — so the first real multi-input-composition consumer hits it. ARC is the motivating-but-non-pinning consumer (it ships provenance-only); it also **documented the resolution semantics** (three input-group cases), which size the fix.

**What changes.**

1. **Finder is pluggable (reverses the §Alternatives "a pluggable scoring function — rejected, the abstraction is L4's to own").** A `Finder` **interface** plus each concrete **algorithm** (BFS, conjunction/fold) live in **L3** — they are computation, and `find_pipeline` already lives at L3. *Which* strategy fires is an **L4** policy call. This splits the concern 0071 originally assigned wholesale to L4: L4 keeps **selection**, L3 owns the **interface + algorithms**. (No L4 "real finder" exists to extend — `plan_construction.py` is a v0 stub — so conjunction is net-new at L3, not an extension of an L4 owner.) BFS becomes one registered strategy; its result construction changes to emit the new DAG type (degenerate-linear DAG).

2. **Conjunction/fold finder.** A hyperpath search whose per-capability resolution is driven **per input-group** — `{all_required (AND) | any_of (optional-union) | fold (aggregate over producers)}` — crossed with **OR over the producers** of each consumed DataState. Explicitly **not** "AND over all inputs" (that mis-composes `any_of`/`fold`). The input-group typing is supplied by the ADR-0159 §amendment (declaration field); this finder *reads* it. Returns a converging DAG. Validated for **structural conformance** against ARC's three documented cases — `all_required` (`touching_delta`/`selector`), `any_of` (`build_correspondence`), `fold` (`reconcile_background`); structural because ARC composes those via an L4 sweep and will not execute the finder's DAGs.

3. **DAG result type replaces the linear `Pipeline`.** `Pipeline`/`PipelineStep` (linear `Tuple[PipelineStep]`) cannot represent a converging DAG. Replace — not additive — is safe: `Pipeline` has **zero production consumers** (verified: no L4/Server/L2/L0 import; the L5-chain `Pipeline` in `chain_artifacts.py` is an unrelated dataclass; the L2 `promoted_pipelines` persistence schema has no live writer). The conjunction finder is the DAG type's first producer.

**Scope held to consumer discipline.** The **promoted-path-lookup** strategy (named as a sibling in the original §Implementation intent) is **not** built — `promoted-pipelines` has no writer (verified). The seam ships with two real strategies (BFS + conjunction). The **graph** form of the input-group (a type-layer typed hyperedge + a hyperedge-aware view walk) is **deferred** to ADR-0156 §am until a graph-walking consumer exists; the finder reads the input-group from the declaration registry meanwhile.

**Supersedes.** The §Alternatives rejection of a pluggable finder, and the §Implementation note "L4's real pipeline-finder will extend this." Status remains Accepted; this records the seam + multi-input soundness fix. Companion: ADR-0159 §amendment (typed input-group field); design record `confirmation_docs/COMPOSITION_LIFECYCLE_DESIGN_LOG.md`.

## §amendment-3 (feat/finder-verdict — 2026-07-31): the two phase-2 cycle guards

**Amendment status:** Accepted. **Implemented by:** `finder-cycle-guards-confirmed`.
*(Label added 2026-08-05: `RULES.md` §9 requires an in-file amendment to carry
`**Amendment status:**`, never `**Status:**`, and this one carried neither. The
duplicate-step figure below was **20** and is corrected to **25** — the delivered
`finder_variants_model.py` produces 25 on the population this paragraph describes.
`CORE_CR_FINDER_AS_CAPACITIES.md` §1 is corrected with it.)*

**Context.** §amendment-2 shipped `ConjunctionFinder` as a two-phase walk: a pure reachability check, then construction over admissible producers. The two phases make the same claim at two resolutions — *"a route exists"* and *"here is the route"* — so they must agree. They did not, in two independent ways, and both were live on the CLI `execute` verb (`mindsos_cli/commands/brain.py:687`, the only shipped path reaching this finder).

**D-B — phase 2 discarded phase 1's cycle stack.** Phase 1 threads a `stack` of DataStates under resolution and refuses a capacity that would need one already on it. Phase 2 re-tested producers with `frozenset()` (`pipeline.py:430`, `:462`), so a producer phase 1 had refused could still be selected during construction, including to feed itself, then recursed to `max_depth` and raised. Composition was **non-monotonic in the start set**: adding an available input could make a compose *fail*.

**D-E — a capacity under construction was invisible to both guards.** `fired[cap_iri]` is written *after* a capacity's inputs are built, so during `fire(c)` the capacity `c` is in neither `fired` nor the stack — the stack tracks DataStates under resolution, not capacities under construction. A capacity could therefore be selected to produce one of its own transitive inputs while still being built, and either recurse to `max_depth` **or complete and be appended to `steps` twice**. The second outcome returned a `Pipeline` naming one capacity as two distinct steps, with `success=True` and no error; `execute_pipeline` then ran it twice and, because the blackboard holds one value per DataState IRI, the second run silently overwrote the first. **D-B raised; D-E lied.** D-E also falsified §amendment-2's own convergence claim ("shared upstream producers fire once (memoised), so diamonds and folds converge correctly").

**What changes.** Phase-2 producer admission moves into a single predicate with three clauses, in order: refuse a capacity that is **in flight**; admit a capacity that has **already fired** (reusing its step index); otherwise fall through to phase 1's own predicate **with the live cycle stack**. `fire` carries the stack and maintains an `in_flight` set. No declaration, signature or result shape changes; no capacity gains a field.

**Evidence, not argument.** `confirmation_docs/finder_variants_model.py` reproduces both phases exactly and swaps only the admission rule. Over 20,000 generated capacity graphs: the shipped rule and a stack-only fix both leave **369 `max_depth` blowups and 25 duplicate-step pipelines**; with the `in_flight` guard, **zero and zero**. The three §amendment-2 conformance shapes (`all_required` AND, diamond convergence, fold fan-in) are byte-identical across all variants. The `fired` short-circuit was separately measured to be a **cost optimisation, not a correctness clause** — identical results with and without it in all 20,000 graphs — and is documented as such rather than defended as one.

**This is a patch, not the design.** Both defects exist because the walk is a top-down recursion needing ad-hoc guards. The agreed replacement computes reachability **bottom-up as a fixpoint** across four dispatched capacities (`path-finding.reachable_strata` → `path-finding.producer_candidates` → `decision.select_producers` → `path-finding.construct_dag`), which makes both defects impossible by construction and retires the cycle stack, `in_flight` **and** `max_depth`. `BFSFinder` is deleted there and BFS becomes a `selection_policy` **value** — which discharges §amendment-2's "BFS is one registered strategy" as a value rather than a class. Spec: `confirmation_docs/CORE_CR_FINDER_AS_CAPACITIES.md`; its §8 lists eight already-rejected alternatives.

**Supersedes.** The fix shape in `confirmation_docs/CORE_CR_FINDER_CYCLE_SOUNDNESS.md` (threading the stack alone). That CR's D8, D9 and D11 stand; **D10 is retired** — `max_depth` is removed, not parameterised. Status remains Accepted.

---

## §amendment-4 (feat/finder-admission — 2026-08-05): step admission — three predicates, and where each of them lives

**Amendment status:** Accepted. **Implemented by:** `signature-sweep-confirmed`,
`bfs-step-admission-confirmed`, `arity-admission-confirmed`.

**Context.** §amendment-3 fixed the two ways the two phases disagreed *with each other*.
This amendment fixes the two ways **either finder disagreed with the executor**: it
returned a route the executor could not run. Both were reported as a right answer, which
is the same class as **D-A** and **D-C** — the failure surfaced one dispatch later, as
`InputContractError`, with nothing between the finder and the executor able to see it.

**The deciding fact, and it is one line of the executor.** `execute_pipeline` builds a
step's inputs as `{ds: blackboard[ds] for ds in step.input_datastates if ds in
blackboard}` and **never consults `DAGEdge`**. So what decides whether a step runs is
what is on the blackboard when it is reached, not how the DAG is drawn. Everything below
follows from that.

**Predicate 1 — path availability. `BFSFinder`-local.** `BFSFinder` fires each capacity
off the single `via` DataState it arrived on and draws one edge, while
`DAGStep.input_datastates` still lists every declared input. It now refuses a capacity
unless every *other* declared input is on this path — the starts plus the outputs of the
steps already taken — which is exactly the blackboard the executor will build. arc1
measured twelve capacities in that class on its own catalog and executed three.

*It is availability and not reachability, and the distinction is load-bearing.* An input
can be reachable from the catalog and still not have been produced on the branch the walk
is on; a route admitted on reachability composes and dies at dispatch exactly as before.
*It is `BFSFinder`-local* because `ConjunctionFinder` answers the same case by **wiring**
the missing input as another step — refusing it there would delete routes it correctly
builds.

**Predicate 2 — `operand_arity` on a scalar. Shared by both finders.** A capacity emits
one value per output DataState, so a consumer declaring `operand_arity=N>1` on a scalar
input can never be fed by route-finding. `operand_arity` lives only on the declaration and
is never written to the graph node, which is why both finders were blind to it. Measured
**arc3 14 of 27, arc1 16 of 45**, on both finders; **inert on core**, which declares no
arity anywhere. Arity on a **collection** input is *not* refused: after ADR-0205
§amendment-3's shape-2 ruling that is the sanctioned many-into-one form, whether the
collection carries N members is a property of the value at run time, and the executor
keeps the length check.

**Predicate 3 — outputs meeting inputs (C3R1b) is NOT built.** It is last by measured
value and ships labelled as hygiene: its original ground was withdrawn when arc3 showed it
does not fix arc3's case, and the surviving grounds argue *blanket over narrow* rather
than *rule over no rule*.

**Where they live, and why that is not one function.** Predicate 2 is answered from a
declaration alone — the same answer for every start set — so it is computed once per
`CapacityLayerView` (`admission.declaration_refusals`, scope-correct, because a Local
override may declare different arity than Global). Predicate 1 depends on the walk, so it
is evaluated per candidate. Both are **module-level functions over plain values** in
`mindsos_capacity/admission.py`: `ConjunctionFinder`'s checks are closures inside `find()`,
and that is the recorded reason **D-B and D-E survived to a tagged commit** — a closure
cannot be called from a test.

In `ConjunctionFinder` the declaration refusal sits in `cap_satisfiable`, not in
`eligible`, so it governs **phase 1** as well as phase 2: a capacity no route can feed must
not make its output look reachable either.

**Two of the three are transitional.** Under the Capacity Graph Traversal rewrite a
capacity cannot feed itself and the walk only uses DataStates it already holds, so
predicates 1 and 3 have nothing left to refuse. Only the arity rule survives. Do not build
a three-way structure that must be unpicked — the same warning the five `FIND_REASONS`
carry.

**This gains refusals, not capabilities, and nothing that ran stops running.** Reachability
is deliberately narrower than the Phase 30/42 BFS. Verified at all four `execute_pipeline`
call sites: each seeds the blackboard filtered to `pipeline.start_datastates`, so the
condition refused by a finder **is** the condition `_validate_inputs` would have raised on.
What moves is where the failure surfaces — an honest no-route instead of a crash. A brain
that needs those inputs wired must name `ConjunctionFinder` for the leaf, or put them on
the blackboard before dispatch.

**Also in this amendment's ships.** `find_pipeline` was annotated `-> Pipeline` while
returning a `FindVerdict` on the tagged `ae63aa2`; corrected, and guarded **structurally**
by `tests/architecture/test_finder_return_annotations.py` so a future finder is covered the
day it is written. `InputContractError` is exported and its `kind` set documented as the
three it actually raises, pinned by an AST scan of the raiser plus a docstring check.
`FindVerdict.already_held` answers **ADR-0205 §amendment-3.4** as a derived property, so
C2R4 does not build the fallback that amendment carries.

**Known and out of scope.** `BFSFinder` still draws `DAGEdge` for the `via` input only,
including for a step admitted because its other inputs are on the path. Inert today —
`Pipeline.edges` is read only by `to_dict()` — but the pipeline store reads edges as the
composition links. Completing them is DAG construction, which is `ConjunctionFinder`'s.

**Not superseded.** §amendment-3 stands in full; this adds a seam it did not have.

---

## §amendment-5 (feat/capacity-union-view — 2026-08-09): the finder view is a Local-preferring union, and D5's retry retires

**Amendment status:** Accepted. **Implemented by:** `union-view-confirmed`.

**Context.** Every amendment above concerns *which capacities a finder may take*. This one concerns *which capacities a finder can see at all*. `pipeline._view_for` resolved a session to `capacity_layer.local_view(user_id)` and a sessionless call to `global_view()` — one realm or the other, never both. A user who registered a single capacity Locally therefore lost the entire pre-installed Global catalog for that find: their one taught step could compose only with other Local steps. ADR-0061 gives Local-over-Global as a **specialisation** rule, and specialisation of one member is not replacement of the set.

**What changes.** With a session, `_view_for` returns a `LocalPreferringView` — a union of the Global and that user's Local `CapacityLayerView`. `session=None` is unchanged and still resolves to Global alone; a sessionless caller is asking about the shared catalog and must not see any user's Local realm.

**The rule is SHADOW, not merge.** A capacity IRI present in the Local metagraph hides the Global capacity of that IRI *entirely* — the node and its `PRODUCES` / `CONSUMES` edges together. There is no per-edge or per-field reconciliation: the union is over the IRI **set**, and at a colliding IRI exactly one side is visible. A merge would be unsound here for the reason ADR-0156 makes topology explicit: a Global capacity's edges describe *that* capacity's contract, and letting them survive an override would let the finder's OR-over-producers pick re-select a capacity the user has replaced, then dispatch the override against the shadowed one's declared inputs.

**The guard is structural, because the class is not a subclass.** `LocalPreferringView` cannot inherit from `CapacityLayerView`, which is defined over exactly one `Metagraph`; a union has no single store, so `metagraph` / `name` / `category_graph` / `datastates_graph` have no honest answer and are absent. That makes it duck-typed, and duck-typing is what made the first attempt at this class unshippable: it implemented five walk methods against the finder of the day, and §amendment-4's `declaration_refusals` then began calling `view.iter_capacities()` and `view.get_datastate()` — so every session-scoped find would have raised `AttributeError`, with no test able to notice because no test asserts what a view *is*. `tests/architecture/test_union_view_surface.py` now reads every `view.<attr>` access out of `pipeline.py` and `admission.py` by AST and fails if the union view cannot answer one. It is a guard of the same kind as `test_finder_return_annotations.py`: structural, not a maintained name list.

**`get_datastate` must union, and that is a correctness clause, not tidiness.** §amendment-4's arity predicate asks whether a declared input is a `collection`. A Local override may consume a DataState that exists only in the Local metagraph; a Global-only lookup returns `None`, the input is silently classified scalar, and a routable capacity is refused. Likewise `iter_capacities` must apply the shadow rule, or refusals get computed for capacities the walk can no longer reach.

**`_input_group_of` becomes scope-correct.** It read the merged, sessionless `get_declaration`. A Local override may declare a different `input_group` from the Global capacity at its IRI, and the union view can now surface either, so it reads `resolve_declaration(session=)` — the same reason §amendment-4 gives for `declaration_refusals`. It stays a per-call lookup rather than joining the once-per-find refusal map: it resolves to two dict lookups, and unlike a refusal it is not a whole-view predicate.

**Supersedes CORE-C3R1 D5.** `execution.py::_compose_pipeline` called `find` twice — the session's Local view, then Global — and `LeafPipelineNotFound` carried both verdicts, because a single view could only ever be one realm and a consumer's solve capacities are typically Local. Under a union view that second call is not a fallback, it is a **bypass**: when a Local override is refused by step admission — say its `operand_arity` is unroutable — the union correctly reports no route, and re-running Global-only composes the very chain the user overrode, silently, with no signal that their capacity was skipped. Local-over-Global must mean the Local capacity is authoritative *including when it is broken*; anything weaker makes an override advisory. The retry is removed and `LeafPipelineNotFound` carries one verdict. D5's reasoning — that only the caller making two calls should hold two verdicts — is not wrong; it is simply vacated, because there is now one call.

**Behaviour change, recorded rather than hidden.** A session whose Local metagraph holds no capacities previously found no route; it now composes the Global chain. `test_find_pipeline_with_unpopulated_session_local_raises` asserted the old outcome and is renamed and inverted — that expectation was the defect, not the contract. Callers passing `session=None` see no change.

**A read must not create state.** `_view_for` guards on the new `CapacityLayer.has_local`, not on `local_view`, which lazily mints an empty Local metagraph. That is the hazard ADR-0183 §am-6 records on the KL side, where a roster read ahead of the durable restore broke `test_durable_roundtrip`; `CapacityLayer` had no equivalent guard until now.

**Not superseded.** §amendments 2, 3 and 4 stand in full. Nothing here changes a declaration, a signature, or a result shape, and no capacity gains a field.

**Not here.** The union view is per-user and single-Local by construction — there is no multi-Local or team realm, and ADR-0061's dual-metagraph shape is unchanged. Producer *choice* between a Local and a Global capacity at **different** IRIs is still the finder's existing OR-over-producers pick, not a preference rule; that seam is `decision.select_producers` under `CORE_CR_FINDER_AS_CAPACITIES.md`, and this amendment deliberately adds no scoring to it.
