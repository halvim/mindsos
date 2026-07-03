# ARC-1 — Full Solve Pipeline (decomposition)

**Status:** working decomposition · drafted 2026-06-18 · companion to `PIPELINE.md`
(the canonical build record), `ONTOLOGY.md` (§4 locked world-model), `LEXICON.md`.
**Purpose:** every step required to take a `RawTask` to a produced answer (or a
structural abstain), at maximum subdivision, with layer home, capacity signature,
and build status. Not a lock — a map to react to and prioritise against.

**Legend** — build status: ✅ built · ◐ partial / #8-only · ○ unbuilt · ⛔ parked or blocked.
Decision marker: ⚑ machine-can't-decide → option-A flag (answered in chat → rerun).
Layer home in brackets `[…]`. Capacities shown as `consumes → produces` (family, dont-know).

**Boundary invariant (binding):** L4 = loop / control / topo-sort only. Every *decision*
(next-step, goal, selector, conflict, min-path cost + selection, tie-break) is **L3**.
`find_pipeline` composes by PRODUCES/CONSUMES; no higher-order dispatcher; no capacity
calls another. Bodies are currently computed directly (not via `capacity_layer.invoke`);
`find_pipeline` only walks edges — crossing into `invoke` is a pending decision.

---

## Phase 0 — Acquire & load (pre-capacity)

- **0.1 acquire corpus** — ARC = fixture file; future autonomous acquire = adapter family (L3-49). `[substrate]` ✅ (fixture)
- **0.2 load task** → `RawTask` (deserialized, uninterpreted). Never raw IO in L3. `[substrate effect]` ✅
- **0.3 withheld-answer gating** — test-pair output sealed from induce/search. `[MM / Server]` ○

## Phase 1 — Perceive (representation, zero inductive commitment) — `[L4 phase_1 sweep, every grid]`

- **1.1 comprehend_task** — `RawTask → Task + Pair*(demo|test) + RawGrid*(input|output)` (comprehension, DATASTATE_MARKER). Structure + role-binding only; no descent into cells. ✅
- **1.2 build_grid** — `RawGrid → Grid` (perception, DATASTATE_MARKER) ✅
  - **1.2.1 recognize_cell** — `(Coordinate, ColorSymbol) → Cell` (perception, DATASTATE_MARKER) ✅
- **1.3 extract_palette** — `Grid → Palette` (derivation, DATASTATE_MARKER) ✅
- **1.4 extract_objects** — `Grid → Object*` (decomposition, deferred-default) — per-color 8-connected components, **all colors incl. background**, size ≥ 2 ✅
  - **1.4.1** per-object attributes: bbox, mask, position, size, color ✅
- **1.5 extract_points** — `Grid → Point*` (single cells; decomposition, deferred-default) ✅
- **1.6 extract_shapes / normalize_shape** — `Object → Shape` (colorless, translation-normalized; derivation, DATASTATE_MARKER) ✅
  - **1.6.1 base-shape recognition** — match Shape vs templated `vertical/horizontal/diagonal/square(n)` (comparator; "recognized as", not stored) ✅
- **Not decided here:** background, figure, "which objects matter" — all reasoning-time judgments.

## Phase 2 — Profile / preparation (mandatory feature profiling) — `[L4 phase_1 sweep, demos only]`

- **2.1 per-demo comparators** (every `preparation`-tagged leaf):
  - **2.1.1 compare_grid_dimension** — `(in Grid, out Grid) → DimensionDelta | None` (comparator, OPTIONAL_RETURN) ✅
  - **2.1.2 compare_palette** — `(in Palette, out Palette) → PaletteDelta | None` (comparator, OPTIONAL_RETURN) ✅
- **2.2 agrees_across_demos** — `Delta*(one/demo) → Bool + common Delta` (predicate/fold, NO_DONT_KNOW); generic over Delta type, calls nothing ✅
- **2.3 output** = candidate Rule fragments/constraints. Keep preparation a **small** universal set; the long tail stays lazy reasoning capacities `find_pipeline` pulls on demand. ✅

## Phase 3 — Reason — `[find_pipeline composes; transition∘state convention]`

> **Grounding update (2026-06-21):** the **#8 specimen** (background ensemble, correspondence,
> `touching_delta`, selector) is now **topology-registered** in `spike/arc_capacities.py`
> (`_reason_capacities`; swept, not `find_pipeline`-composed; stub bodies, compute still inline in
> `arc_solver`). Decisions + open items: `PIPELINE_DECISIONS.md`. The rest of 3A–3I is still inline.

### 3A — Correspondence (P3 — upstream of induce)

- **3A.1 background proposal** — most-frequent color/grid → `Background` (reasoning-time, **not** perceive) ◐ ⚑
- **3A.2 build C** (`input ref → output ref`, unambiguous subset only):
  - **3A.2.1 same_object** — `Object × Object → Bool` (color + position; comparator, OPTIONAL_RETURN) — invariant 1:1 ✅
  - **3A.2.2 1:1 moved** — color + shape + displaced ✅
  - **3A.2.3 same_point** — `Point × Point → Bool` (color + position; comparator) ✅
  - **3A.2.4** duplicate / ambiguous → left **uncorresponded** ⛔ (P3)
- **3A.3 correspondence completeness** — does C cover the objects the rule needs? non-unique on a needed object → abstain / flag ○ ⚑
- **3A.4 relational naming of correspondents** ("the divider", "the largest", "touching X") — PB-B ○

### 3B — Induce (fragments + state structure)

- **3B.1 transition detectors** (past-tense comparators → `Transform | None`):
  - **3B.1.1 moved** — `(in Object, out Object) → move Transform {kind:translate, vector:Δ}` (comparator, OPTIONAL_RETURN); self-guards (same color + shape + displaced) ✅
  - **3B.1.2 rotated / reflected / scaled / recolored** — ontology #10, named ○
  - **3B.1.3 compare family** (`is_rotation` / `is_congruent`) — `PointSet × PointSet → Transform?` (comparator, OPTIONAL_RETURN) ◐
- **3B.2 intra-grid state predicates** (present-participle, per grid → Bool):
  - **3B.2.1 touching** — `(Region, Region) → Bool` (8-neighbour; diff-color objects + Points; parameter-free; predicate, NO_DONT_KNOW) ✅
  - **3B.2.2 containing / overlapping / inside / aligned / touches-edge (object↔frame)** ○
- **3B.3 state-change detector** (P6 un-parked) — a state flips across input→output over C:
  - **3B.3.1 touching_changes** — gained / lost / maintained, background-excluded ✅
  - **3B.3.2** generalize to any state (gained/lost over containing, aligned, …) ○
- **3B.4 object feature profiles** feeding selectors: color, size, size-rank, base-shape, bbox, position ✅

### 3C — Hypothesis formation — `[L4 fold over induce caps]`

- **3C.1** enumerate states + transitions for pair 1 (canonical) ✅
- **3C.2 persistence filter** — keep those present in **every** demo (on changes/transitions, not static states) ✅
- **3C.3 combination test** — `(transition, state-change)`: same object within a pair, existential across pairs (∀pair ∃obj) ◐ — **only the single combo `(move, touching)` is tested; no enumeration over other pairs**
- **3C.4** cull spurious combos by MDL + selector ○
- **3C.5 output** = candidate ternary schema(s) `(mover-transition, state-change, target = select(S))` ◐

### 3D — Selector / target synthesis

- **3D.1 role identification** per demo — mover (gained-endpoint that moved) vs target (other endpoint) ✅
- **3D.2 selector** = minimal discriminative state-conjunction, task-invariant; must resolve a **unique** source + target, else **FLAG** (option A — the shape tie-break is a recorded flag, not an abstain; real tie-break → D11) (GF-5):
  - **3D.2.1** single-attribute candidates: color / size-rank / base-shape (`_selectors_for`) ✅
  - **3D.2.2** multi-attribute conjunctions when no single attribute discriminates ○
  - **3D.2.3** relational selectors ("the object touching X") ○
  - **3D.2.4** selector tie → flag (option A) ✅ ⚑
- **3D.3 moving-target dependency DAG** — topo-resolve (`kahn_sort`, L4), acyclic, grounded at an absolute referent (edge / divider / invariant) ◐ — **#8 target is invariant (trivial)**
- **3D.4 selector uniqueness verify** — unique source + target in every demo **and** on query ◐

### 3E — Rule assembly

- **3E.1 bind schema → selectors**: `(transition, state-change) + mover-sel + target-sel + policy` ◐ — **stage-4 is a hardcoded string block, not synthesized**
- **3E.2 transition policy** — direction = toward target, magnitude = greedy iterate to goal; move = slide along the shared-axis perpendicular. Other transitions: undefined ◐
- **3E.3 write-conflict / compositing policy** (two objects → same cell) — **L3 decision** ○
- **3E.4** rule = the DAG run by the L4 loop (commits **P1 ≈ option b**) ◐

### 3F — Search / selection (the unbuilt spine) — `[L4 loop, L3 scores]`

- **3F.1** enumerate candidate rule sets (compose persistent fragments) — P1/P2 combinatorial control loop ⛔
- **3F.2 MDL ordering** — minimum path in a rule graph; L4 drives loop, L3 scores/selects ○
- **3F.3 equal-MDL tie-break** — an L3 prior ○
- **3F.4 budget semantics** (P4) — depth / node-count / wall-cost? Required for honest abstain ⛔ (undefined)
- **3F.5 seed operation set freeze** (ICECUBER_DSL, id-variant level) — blocks 3F.1 ⛔

### 3G — Apply (generate output) — `[L4 loop, L3 decisions]`

- **3G.1 resolve roles** on a grid via locked selectors → mover, target (`_shape_roles`) ◐ — **hardcoded irregular/square**
- **3G.2 next-step proposer** (**L3**, ranked) — the apply-loop boundary-keeper ○ — **currently the greedy `_slide` is the policy**
- **3G.3 transition generator** (present-tense, transform family) — `(A, Transform) → B`, CONSUMES the Transform DataState; only move ✅, others ○
- **3G.4 greedy apply loop** — min-transform/step, check the state-change until the goal holds; budget = grid bounds → structural abstain ✅ (slide)
  - **3G.4.1** closed-form alternative (directional contact distance, not bbox-adjacency) ○
- **3G.5 serializer** (objects → grid; inverse of perceive):
  - **3G.5.1** background fill ✅
  - **3G.5.2** non-mover objects at origin ✅
  - **3G.5.3** mover at slid position ✅
  - **3G.5.4** overlap / z-order ○
  - **3G.5.5** clipping at bounds ◐
  - **3G.5.6** multi-mover composition ○

### 3H — Verify

- **3H.1** apply rule set to each demo input ✅
- **3H.2** exact-match output (Consistency) ✅
- **3H.3** all-match → sufficient; mismatch → backtrack to 3F / abstain ✅
- **3H.4 Consistency ≠ Generalization (P5)** — a per-object `{obj → Vector}` passes verify yet transfers to nothing; the rule must carry the *generator*, not the vector ⚑ (false-confidence trap)

### 3I — Apply to query | Abstain

- **3I.1** selector resolves a unique source + target on the query → apply → produced output ◐
- **3I.2** confidence check (dev only) — vs withheld answer, **not used by the solver** ✅
- **3I.3 structural abstain** — no consistent rule in budget / non-unique selector / ambiguous correspondence / slide leaves grid ◐

---

## Appendix — Ontology / Lexicon coverage of the terms above

`O` = `ONTOLOGY.md` (class catalog §2 / capacity table §3 / decisions §4). `L` = `LEXICON.md`.

**In both O and L:** task, pair, demonstration, query/answer, grid, cell, position/coord,
color, background, palette, figure, object, shape, template, mask, connectivity, region,
bbox, vector, distance, rule/program, consistency, predicate, abstain.

**In O, missing from L** (lexicon is thinner than the ontology):
Point · Group · PointSet · Pattern · Lattice(N) · Divider · Sub-shape · Congruence ·
Background-as-role · base-shape (named individuals) · the Transform detector/generator pair.

**Capacities used above but absent from the O §3 table:**
comprehend_task · compare_grid_dimension · compare_palette · agrees_across_demos ·
touching_changes (the P6 state-change detector). Naming drift: PIPELINE/spike call it
**extract_shapes**; O §3 lists **normalize_shape** — same capacity, two names.

**In neither O nor L — the entire reason-stage convention vocabulary** (locked in
`PIPELINE.md` "Reason-stage design 2026-06-17" but not yet absorbed into the world-model):

- **State** — present-participle intra-grid predicate as a first-class category.
- **transition** — past-tense category carrying a Transform (Transform is in O; "transition" as the category is not).
- **state-change** — gained / lost / maintained (P6 names its concept home as "relation Delta §2.4–2.5" but the term is undefined).
- **selector** — minimal discriminative state-conjunction.
- **mover / target** — reasoning roles (only **Divider** is a named role in O #12).
- **correspondence** — referenced in O §2.4 prose as a pre-step, but not a catalog class and not a lexicon term.
- **touches-edge / object↔frame predicate** — explicitly flagged "new" in PIPELINE.
- **Delta / DimensionDelta / PaletteDelta** — the profile-comparator outputs; not a class in O §2, not in L.
- **dependency DAG · budget · next-step proposer · seed operation set** — control/mechanism terms; arguably substrate, but **budget** is a domain inference term (it defines Abstain) and is undefined (P4).

**Reading:** perceive/profile vocabulary is well-grounded in O (thinly in L); the reason
stage is grounded in `PIPELINE.md` but **not** in the world-model. Absorbing the
transition∘state convention into ONTOLOGY §2/§4 + LEXICON is an open consolidation task,
prerequisite to claiming the solver vocabulary is auditable end-to-end.

---

## Appendix — Pending primitive: intra-graph compositional hyperedge (PLACEHOLDER)

**Need.** Express `Cell ⊣ {Coordinate@position, ColorSymbol@color}` (and `Grid ⊣ {Cell*}`,
`Object ⊣ {Cell*}`) as a **single-graph** composition with a whole/part distinction and
**ordered, named part-roles**. The shipped flat `HyperEdge` has no anchors/members/
`compositional`/`ordered`; only `IntergraphHyperEdge` (cross-graph) carries them.

**Status:** NOT built. Author against the **abstract contract** below; bind to the concrete
realization when it lands. This is a **MindsOS-core** primitive (generic, every skill uses
it), NOT an ARC-specific artifact.

**Contract stub** (what the ARC consumer needs the primitive to guarantee):
- exactly **one anchor** = the whole (`Cell`); **N members** = the parts (`Coordinate`, `ColorSymbol`);
- **`ordered = True`** (part-roles are positional/named: slot 0 = position, slot 1 = color);
- **`compositional = True`** ⇒ identity-bearing + **immutable** post-create;
- intra-graph (anchor + members in the same graph);
- walkable as a **provenance** edge (members → anchor) by the grounding checker.

**Realization options (decision pending):**
- **A — same-graph `IntergraphHyperEdge` (shipped; meets the full contract TODAY).**
  `Metagraph.add_intergraph_hyperedge` has **no cross-graph requirement** — all anchors +
  members may live in one contained graph. With `compositional=True` (⇒ `ordered=True`,
  immutable) it satisfies one-whole / N-ordered-parts / provenance-walkable. **Zero core
  change**, single graph, inside the ARC metagraph. The recommended bridge — likely
  sufficient outright.
- **B — build a standalone-`Graph` compositional `HyperEdge` in `mindsos_core`** (a
  dedicated core chat; L1 + persistence/serde blast radius). Only needed if a consumer
  wants composition on a `Graph` *not* inside a metagraph. ARC does not.
- **C — instance convention over flat `Edge`/`HyperEdge`** (type_name encodes role; no
  core change; re-implements ordered/immutability as discipline). Inferior to A.

Recommendation: use **A now** (it already meets the contract — no wait, no core change);
file the standalone-Graph case as future work (L1-10) and build **B** only if a
non-metagraph consumer ever pins it. The earlier "must build a new primitive" framing was
wrong — the capability is shipped.
