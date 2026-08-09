---
title: Abstraction levels — one graph at several resolutions
status: Accepted
date: 2026-07-31
layer: L3
related: [0071, 0132, 0148, 0156, 0182, 0183, 0203, 0206]
---

# ADR-0205: Abstraction levels — one graph at several resolutions

**Status:** Accepted

**Date:** 2026-07-31

**Related:** ADR-0156 (bipartite capacity↔DataState topology — the ground level),
ADR-0132 (intergraph edges / hyperedges — the composition primitive), ADR-0071
(pipeline finder), ADR-0148 (the intergraph primitives themselves — see
§amendment-1), ADR-0182 (node-value serialization), ADR-0183 (skill bundle
lifecycle), ADR-0203 (learned-pipelines Local persistence — **contradicted, see §6**),
ADR-0206 (planning, decomposition and confidence — builds on this).

---

## Context

MindsOS reasons about several kinds of structure: capacities and DataStates, pipelines,
milestones, plans, and what it knows about a kind of request. These were introduced
separately, at different phases, with different storage decisions, and no statement of how
they relate. The results are visible:

- A taught pipeline is stored as an **opaque blob** (ADR-0203) while a promoted pipeline is
  stored as a **normalised graph** (ADR-0071 / ADR-0152 §1) — two representations of the
  same thing. *(This second claim is false as written — see §amendment-1.8.)*
- A plan exists twice: as a `Milestone` tree in the chain graph and as endpoint
  dictionaries on `PlanResult`.
- Topology is repeatedly stored as **node properties instead of edges**
  (`Milestone.parent_ref` / `children_refs`; `RequestPattern.relevant_hints` /
  `paired_pipelines`), so it cannot be walked.
- The same upward walk — invalidation, hub discovery, verification, attribution — has no
  shared primitive and is on course to be implemented four times.

There is no principle saying what these structures *are* relative to each other, so each
decision was made locally and they drifted.

---

## Decision

### 1. There is one graph. Everything else is an abstraction level over it.

The ground truth is the L3 bipartite graph of **capacities and DataStates** (ADR-0156).
Every other structure the system reasons with is an **abstraction level** built from the
nodes of the level below:

| Level | Composed of | Verified by |
|---|---|---|
| request | plans | its plan |
| plan | milestones | its milestones and their pipelines |
| milestone | pipelines (a hub is their intersection) | the pipelines it is coincident in |
| pipeline | capacities and DataStates | its capacities and DataStates |
| capacity | — ground truth | — |

**Milestones sit above pipelines by dependency, not preference:** a hub cannot be
discovered without pipelines to intersect.

### 2. Composition is `IntergraphHyperEdge` with `compositional=True`

*(Amended — see §amendment-1.1 and §amendment-1.2. The primitive is selected by arity:
`IntergraphEdge` for one member, `IntergraphHyperEdge` for several.)*

The primitive already ships (Phase 05c). Its **anchors** side is identity-bearing (*the cat
in cat = c + a + t*); its **members** side is the constituents; it works across graphs.
A level-N node anchors a compositional hyperedge over its level-(N−1) members.

**Semantics:** *what it points to is formed by what it points from.* Every member is
**necessary** — remove one and the anchor no longer exists.

**Order is independent of necessity.** Some compositions are ordered (a dependent sequence;
`cat ≠ act`); some are not (parallel members, all required, sequence meaningless). Both must
be expressible. **P8-A — the factory's refusal of `compositional=True` with
`ordered=False` — is amended.** Its recorded rationale ("set semantics is incompatible")
conflates *identity-bearing* with *sequence-bearing*; a set-composed identity is coherent,
and `ordered=False`'s only real effect is factory dedup, which is harmless for genuine
sets. The original argument could not be recovered — `PHASE_05c_DESIGN_LOG.md` does not
exist. *(This last sentence is wrong — see §amendment-1.1.)*

### 3. AND and OR are carried by the structure; nothing is labelled

- **Within one composition: AND**, always. That is what `compositional` means.
- **Between compositions sharing an anchor: OR.** Two ways to reach the same milestone are
  two compositional hyperedges anchored on the same node. **No new edge type.**
- **Sequence vs parallel within an AND set:** read from the chosen pipelines' data flow —
  if B's pipeline consumes A's output they are sequential, otherwise parallel. An *output*
  of planning, not an input.

### 4. The system reasons by lazy descent

The Mental Model loads the **highest abstraction level** and analyses it. If it cannot find
what it needs, it loads the next level down **only for the nodes it needs**, and rechecks.
It descends until it has enough to understand what it is doing. Confidence decides whether
to descend (ADR-0206).

### 5. No structural blobs

A structure stored opaquely cannot be verified by the level below, so it breaks the model.
**This does not restrict opaque *values*** — a numpy array on a DataState is data, not
structure. ADR-0182's codec is unaffected; what changes is what may ride on it.

*(Scope clause added by §amendment-1.4 — the criterion as published has no boundary.)*

### 6. Verification is part of learning, and runs on read

Each level's claim is checkable against the level below. **Learning something new is a
comparison of the current state against the previous one**, so verification is not separate
maintenance — it is part of learning, and its output is new nodes *and* confidence deltas
on existing links. Learning that contradicts existing knowledge lowers a confidence; it
does not merely add.

**Verification runs on read** — an abstraction is verified against the level below when it
is loaded, which pays only for what is used and fits lazy descent. The dream performs the
full sweep.

### 7. Structure is stable; learning moves confidence

Two kinds of change, with different triggers:

- **Confidence change** — structure untouched, appropriateness moved. Constant.
- **Structural change** — a node or composition appears or disappears. **Not drift: a
  deliberate act, whose unit is the Skill.**

### 8. A Skill spans all abstraction levels

**A Skill is not a group of capacities.** It is everything across *all levels* needed to
serve a class of requests: capacities, pipelines, milestones, plans, request knowledge.
Install adds the vertical; uninstall removes it. Losing the ability to serve those requests
is the **intended** consequence, and because the vertical goes together nothing is left
pointing at something that no longer exists.

**Uninstall keeps what the user built, by default.** Two kinds of leftover:

- **Data** (learned parameters, a taught signature library) — meaningful alone. Keep.
- **Structure** (a pipeline taught from the Skill's capacities) — meaningless while the
  Skill is gone, valuable again on reinstall. Keep, **dormant**.

On-read verification (§6) enforces the difference without deleting anything: a dormant
structure fails verification against the capacity level and is not offered. Reinstalling
revives it. Removing user data is an explicit opt-in. *(Narrowed — structure can never be
removed at all; see §amendment-1.5.)*

**Dormancy is per-dependency** — "which of my dependencies are missing" — never a boolean.
Attribution is **many-to-many**: a pipeline built from Skills X and Y depends on both and
belongs to neither.

### 9. Realm carries approval; tags carry provenance

**Global is what the system ships by default**, decided by a human admin. **Local is
everything that differs.** An admin promotes Local to Global.

⟹ **Any Global element is promoted by definition. No `promoted` tag exists.** Tags record
provenance only (taught / discovered).

### 10. One traversal primitive

Invalidation, hub discovery, verification and attribution are the **same upward walk**.
They share one primitive, built with the first consumer and with the other three named as
design inputs.

### 11. Terminology

**"Abstraction level"**, written in full, never numbered. MindsOS already uses *layer* for
L0–L5 and *tier* for `TierEnum`. "Level" is correct and already in the code:
`BlameVerdict.chain_level` takes `hint | map | plan | plan_subtree | pipeline` — this
ladder, already named. Refer to them as *capacity level*, *pipeline level*, *milestone
level*, *plan level*, *request level*.

The "6-level chain of artifacts" is **not** a competing hierarchy: the chain artifacts are
the **per-request trace** across these same levels, plus execution records
(`PipelineRun`, `RequestRun`, `ReplanRecord`). The chain **references** durable knowledge
and never duplicates it.

---

## Consequences

**Good**

- One statement decides a class of questions that were previously decided case by case.
- The composition primitive already ships; this is a use of core, not an extension of it.
- Verification, invalidation, dormancy and attribution all fall out of one walk.
- Skill uninstall becomes explainable to a user rather than a silent cascade.

**Cost**

- **ADR-0203 is contradicted** and must be superseded: a taught pipeline may not be an
  opaque blob. The `learned-pipelines` and `promoted-pipelines` roles unify into one
  `pipelines` store. ADR-0203's stated blocker — the D38 hyperedge reframe — was settled by
  ADR-0156 (bipartite); what remains open is only the narrower *graph form of
  `input_group`*.
- **P8-A is amended** (§2).
- Topology stored as properties must become edges: `Milestone.parent_ref` /
  `children_refs`, `RequestPattern.relevant_hints` / `paired_pipelines`.
- `PlanResult`'s endpoint dictionaries stop being a second description of the plan.
- Two abstraction levels have no representation yet: **milestone** and **request
  knowledge** as walkable structure.
- **Every existing ADR must be re-read** against the criterion *does this store a
  higher-level structure opaquely, or duplicate it outside the graph?*
- Skill packaging must be able to declare milestone and request-knowledge content, so it
  sequences **after** those levels exist.

---

## Alternatives considered

1. **Leave the structures independent and reconcile pairwise.** Rejected — that is what
   produced the four duplications this ADR removes.
2. **A separate registry per level.** Rejected — a registry grants a level's topology
   different trust from the edges beside it, and the finder already reads all topology from
   graph edges.
3. **Keep opaque blobs for convenience at the pipeline level.** Rejected — a blob cannot be
   verified by the level below, which is the property the whole model rests on.
4. **Introduce a new OR edge type for alternatives.** Rejected — several compositional
   edges sharing an anchor already express it.
5. **Design the traversal primitive standalone, ahead of consumers.** Rejected on consumer
   discipline; built with its first consumer instead, with the rest named.

---

## §amendment-1 (feat/adr-sweep — 2026-08-01): composition primitives, criterion scope, and four corrections

**Amendment status:** **Accepted** at **CORE-C2R2** (the composition-primitive item).
The original line read *"Flips to Accepted with CORE-C2R1"*, using the pre-renumbering
ids; under `CORE_RECONCILIATION_PLAN.md` §3 that item is **C2R2**, and C2R1
(`installed-skills` dual-scope) shipped without touching the primitive. Corrected here
rather than left as a stale `Proposed` on the amendment C2R2 builds from.

Produced by the CORE-C1R4 contradiction sweep. Coverage record and evidence:
`confirmation_docs/CORE_ADR_CONTRADICTION_SWEEP.md`. The canonical source for everything
about the intergraph primitives is `confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`, which
declares itself so and which §2 below failed to consult.

### am-1.1 — §2's stated basis for amending P8-A is wrong. The conclusion stands.

§2 says *"The original argument could not be recovered — `PHASE_05c_DESIGN_LOG.md` does not
exist."* The argument was never in a 05c design log. It is recorded in
`INTERGRAPH_EDGES_DESIGN.md` (2026-05-06 amendment block):

> compositional implies identity-bearing composition (cat=c+a+t — order/duplicates matter);
> set semantics is incompatible.

§2's conclusion is unaffected — the rationale does conflate *identity-bearing* with
*sequence-bearing*, and a set-composed identity is coherent. **What must change is the
argument's basis:** §2 overrides a recorded decision, not an absent one, and must say so.
Strike the "could not be recovered" sentence and argue against the quoted rationale
directly.

**Lesson, recorded because it caused the error:** `INTERGRAPH_EDGES_DESIGN.md` is the single
canonical source for both intergraph primitives and instructs readers not to chase pointers
elsewhere. Any future decision touching them reads it first.

### am-1.2 — The composition primitive is selected by arity, not fixed

§2 names `IntergraphHyperEdge` as *the* composition primitive. That is incomplete, and the
gap is at the ladder's base case.

- **Several members → `IntergraphHyperEdge` with `compositional=True`.** Ordered or not
  (per §2 as amended).
- **Exactly one member → `IntergraphEdge` with `compositional=True`.** Shipped Phase 05b;
  identical semantics (`INTERGRAPH_EDGES_DESIGN.md` field table row 9 and row 7); persists
  as the same `_compositional` reserved property.

**This is the recorded design, not a change to it.** The hyperedge's cardinality check
refuses 1-anchor/1-member (validation step 8: *n≥1, m≥1, NOT 1-1*), and P19-A names
`add-intergraph-edge --intergraph-edge-id <orig>` as the route for a composition that
collapses to 1-1. The two primitives partition by arity; ADR-0205 §2 used only one of them.

**Why it matters:** the base case of the ladder is 1-1. A capacity is a 1-step pipeline
(ADR-0206 §floor). `planning_v0` produces a single-milestone plan today. A milestone reached
by exactly one pipeline. None of these is expressible with the hyperedge alone.

**Amend §2** to read: *a level-N node anchors a compositional intergraph edge or hyperedge
over its level-(N−1) members, the primitive chosen by member count.*

**Ruling B — anchor direction.** A compositional `IntergraphEdge` has `source` and `target`,
not `anchors` and `members`. The convention is **source = anchor, target = member**, mirroring
the hyperedge's anchors-first ordering. This is not currently recorded anywhere; §10's upward
walk must traverse both primitives, so it must be, in `INTERGRAPH_EDGES_DESIGN.md` §4.3.

### am-1.3 — Ruling A: subsumption is not composition

DataState subsumption — the missing `SPECIALIZES` edge (C11), named in §Consequences — is
1-1 **within one graph**: ADR-0064 puts every DataState in the single shared
`capacity:datastates` graph. `add_intergraph_edge` step 3 refuses same-graph edges, and the
intra-graph `Edge` primitive has no `compositional` flag (verified: zero occurrences in
`mindsos_core/models/edge.py`). So a same-graph 1-1 composition is inexpressible under any
shipped primitive.

**Ruling: it should not be a composition.** A child DataState is not *made of* its parent —
subsumption is a typing relation, not a part-whole one, and §2's semantics ("remove one
member and the anchor no longer exists") does not hold for it.

⟹ C11 ships as a **plain typed `SPECIALIZES` edge** in the datastates graph. It remains an
instance of §Consequences' *topology stored as properties* class, and is fixed there. It is
**not** an instance of the composition class, and requires no core change.

This ruling is what makes am-1.2 sufficient: with subsumption excluded, no ladder
composition is same-graph.

### am-1.4 — §5 needs a scope clause

As published, §5's criterion has no boundary. Applied literally it condemns ADR-0016
(`ref:<role>` string properties) and ADR-0029 (a JSON pointer map) — L1 primitives that
predate this ladder and that this ADR does not intend to reverse. Add to §5:

> **Scope.** This applies to **members of the ladder at any level, including the ground**:
> capacities, DataStates, pipelines, milestones, plans, request knowledge — their
> composition, ordering, subsumption and dependencies. It does **not** apply to substrate:
> `Metagraph`, `Graph`, persistence, release manifests, server/session/auth state, audit
> logs, `ref:<role>` strings, `XRef`, `mindsos_instances`.
>
> Test: *if this structure disappeared, would the system have forgotten something it knows,
> or merely lost a way to store it?* Forgotten → in scope.

### am-1.5 — Compositional is terminal. §8 narrows accordingly.

Per `INTERGRAPH_EDGES_DESIGN.md` §4.3, when `compositional=True`:

- `remove_intergraph_edge` / `remove_intergraph_hyperedge` raise `CompositionalImmutableError`
- the mutation API raises the same
- ~~`deprecate_intergraph_edge` (Phase 10) raises the same~~ — **this method does not
  exist.** Corrected at §amendment-4; `INTERGRAPH_EDGES_DESIGN.md` §4.3 carries the same
  error. The three real refusals are `remove_intergraph_edge`,
  `update_intergraph_edge_properties` and the `compositional` `__setattr__` gate
  (Pushback 22-A). Terminality is unaffected — one of four citations was to a method
  that was planned and never built
- the flag itself cannot flip, deliberately: *"a `True` edge can't be removed, so flipping in
  error wedges the metagraph"*

Recovery is `mindsos metagraph reset --force`. **Pushback 6-A recorded this as a known gap
with no escape hatch**, and filed it to `_source_backup/root/mindsos_future_plans.md` — a
file that no longer exists. Three other deferrals point at the same missing file (endpoint
update, hyperedge→edge downgrade, structural mutation).

**Scope is narrower than it looks.** Immutability binds the edge/hyperedge, **not the nodes
it connects**:

- `Pipeline.status` (tested / activated / quarantined / retired), confidence and provenance
  are node properties. Unaffected.
- §8's dormancy is **derived** by on-read verification (§6), not recorded. Unaffected.

**What does not survive:** §8's *"Removing user data is an explicit opt-in"* implies removal
is available for structure. It is not, at any price short of wiping the metagraph. **Amend
§8** to state that taught structure can be made permanently dormant but never removed, and
that removal applies to *data* only. This does not weaken the model — dormancy was already
the default and the mechanism — but the ADR must stop implying an operation the primitive
forbids.

### am-1.6 — Open item: a composition pins its graphs

`Metagraph.remove_graph` runs an atomic precheck over both `intergraph_edges` and
`intergraph_hyperedges` and refuses if any incident edge is compositional (Pushback 17-A).
ADR-0202 persists **one chain graph per task**. If per-request plan structure is
compositional, every task's graph becomes permanently unremovable.

**Not decided here.** Owner: **CORE-C2R2**, before the milestone graph is built. Options
recorded, none chosen:

1. Per-request structure is non-compositional; only durable taught structure is compositional.
2. Compositions live only in durable role-graphs; the chain references them and composes nothing.
3. `remove_graph` gains a cascade for compositional edges (reopens 6-A).

### am-1.7 — §2's claim about consumers, checked

§Consequences says *"The composition primitive already ships; this is a use of core, not an
extension of it."* The first half is true. The second needs stating plainly: as of
`60fe2ae`, `IntergraphHyperEdge` and `compositional` have **zero users** in
`mindsos_capacity`, `mindsos_intelligence` and `mindsos_knowledge` — only `mindsos_instances`
and core itself. No abstraction level above `capacity` currently has any graph
representation. This is not an argument against the ADR; it is the size of the work it
implies, and it was not recorded.

### am-1.8 — §Context's "normalised graph" claim is false

§Context contrasts ADR-0203's blob against *"a promoted pipeline is stored as a normalised
graph (ADR-0071 / ADR-0152 §1)."* Verified in
`mindsos_knowledge/schemas/promoted_pipelines.py`: `edge_sequence` is a `list[capacity_edge_id]`
**content field**, `start_ds` / `end_ds` are content fields the ADR itself annotates
"Derivable", and `PipelineStep` / `HAS_STEP` are declared with no writer
(`PIPELINE_STEP_PROPS` is annotated *"deferred to ADR-0152 §amendment-1"*). Three
descriptions of one pipeline's topology, none of them written.

⟹ ADR-0152 §1 is itself an instance of both halves of the §5 criterion, and the ADR cited
as the good counterexample is not one. Correct §Context; the contrast it draws is between a
blob and a *declared but unbuilt* normalised form.

---

## §amendment-2 (CORE-C2 — 2026-08-01): the trace ladder and `chain_level`'s missing target

**Amendment status:** Proposed. Flips to Accepted with the milestone-level item.

Produced by the CORE-C2 pre-build read-through, and reconciled against §amendment-1 (the
CORE-C1R4 sweep) at `2c56246`. **This amendment does not restate §am-1.** Where the two
chats reached the same finding independently — P8-A's recoverable rationale, the absence of
consumers, the false "normalised graph" claim, compositional terminality — §am-1's text
stands and is not duplicated here. Two additions to it are recorded in §am-2.3.

### am-2.1 — §11's `chain_level` evidence is withdrawn; the target set is undefined

§11 states: *"'Level' is correct and already in the code: `BlameVerdict.chain_level` takes
`hint | map | plan | plan_subtree | pipeline` — this ladder, already named."*

**The terminology choice stands** — *layer* is taken by L0–L5 and *tier* by `TierEnum`, so
*abstraction level* is correct. **The evidence does not.** §1's ladder is
`capacity | pipeline | milestone | plan | request`. **Two of five values match.** `hint` and
`map` are Phase-1 **steps**, not levels (ADR-0206 §3: *"The steps are request → hint → map →
plan"*); `plan_subtree` is already retired by ADR-0206 §Consequences; `capacity`,
`milestone` and `request` do not appear in `chain_level` at all.

⟹ **`chain_level` has no defined target set** until `hint` and `map` are settled as steps
rather than levels. That is a decision, not a wording fix, and it belongs to the item that
reconciles the confidence fields — whose scope ("reconcile `chain_level` to the ladder") is
undefined until the decision is made.

⟹ **Consequence for `request_knowledge`** (ADR-0206 §7): it references two different kinds
of thing — step outputs (hint, map) and ladder levels (plan, milestone, pipeline). The rule
that a declared level requires the level below applies to the **level half only**; a hint
has no level beneath it to require. A validator must not demand all five.

### am-2.2 — Lazy descent implies a per-level trace, and §11 must say so

§4 states that the Mental Model loads the highest abstraction level and descends only as far
as confidence requires. §11 states the chain is *"the per-request trace across these same
levels"*. **Neither says the trace must therefore carry a record at each level** — and
without that statement, an optimisation replacing the per-level trace records with links
into the durable levels reads as correct. It preserves *which* node was used at each level
while silently deleting **the descent itself**: loaded the plan level, not confident,
descended to milestone, still not confident, descended to pipeline. That history is the
per-request reasoning record, and it is what §4 describes. This is not hypothetical — it was
proposed during CORE-C2 and rejected only because §4 was re-read.

**Amended:** the per-request trace carries **one record per abstraction level**. Those
records are thin — an identity, a link to the durable node used, and per-request state; all
structure remains links. The trace record for level *L* is named `<L>Run`.

| Level | Durable node | Trace record |
|---|---|---|
| capacity | `Capacity` / `DataState` | `CapacityRun` |
| pipeline | `Pipeline` | `PipelineRun` |
| milestone | `Milestone` | `MilestoneRun` |
| plan | `Plan` | `PlanRun` |
| request | `RequestKnowledge` | `RequestRun` |

`ReplanRecord` is a provenance composite, not a level. `Hints` and `Mapping` record **step**
outputs, not levels, and take no `Run` suffix; they attach to the request-level trace. §11's
list of three execution records (`PipelineRun`, `RequestRun`, `ReplanRecord`) was not
exhaustive — `StepExecutionRecord` is the capacity-level trace and is **renamed
`CapacityRun`**, not removed.

**Ruling on §am-1.6 (a composition pins its graphs), for the trace only.** ADR-0202 persists
one chain graph per task, and `remove_graph` refuses while any incident compositional edge
exists. **The per-request trace therefore links with ordinary, non-compositional intergraph
edges** — §am-1.6's option 1. Task graphs stay removable, and the links stay mutable, which
the trace requires because run state changes during a run. §am-1.6's wider question — what
durable structure may be compositional — stays open and stays with the milestone-level item.

### am-2.3 — Two additions to §amendment-1

**To am-1.1 (P8-A's basis).** §am-1 located the rationale in `INTERGRAPH_EDGES_DESIGN.md`.
It also survives in `confirmation_docs/PHASE_MAP.md` (the Phase 05c P8-A row) and
`PHASE_05c_CONFIRMED.md`, and the file §2 searched for (`PHASE_05c_DESIGN_LOG.md`) never
existed while `PHASE_05c_IMPLEMENTATION_LOG.md` does. **Beyond that: ADR-0148 and
`docs/concepts/glossary.md` cite each other for an amendment neither reproduces, and assert
opposite outcomes** — ADR-0148 says compositional hyperedges are `ordered=False` by default;
the glossary says the combination is refused. ADR-0148 is a self-declared reconstruction and
its line is corrected at ADR-0148 §amendment-1. ⟹ the P8-A amendment is a **deliberate
override of a recorded and sound argument**, never a restoration of a lost contract, and no
citation of ADR-0148 supports it.

**To §2 as amended by am-1.2 (arity-selected primitive).** `ordered=False` does not only
dedup — `mindsos_core/schema/types.py` **sorts and dedups** at construction. And the
override's real justification is narrower and stronger than §2's: a plan's members are its
milestones, all necessary, with sequencing carried by separate sibling dependency links so
that *parallel* is the **absence** of a link (ADR-0206 §2). An `ordered=True` member list
expresses only a **total** order and would make parallel siblings inexpressible. `ordered`
is therefore chosen **per level**:

| Link | Primitive | `ordered` |
|---|---|---|
| pipeline → its capacity steps | hyperedge | `True` — the sequence *is* the pipeline; duplicates legal. Holds only the steps; start and end DataStates are separate links |
| milestone → a pipeline reaching it | **`IntergraphEdge`** (single member, per am-1.2) | n/a |
| plan → its milestones | hyperedge | **`False`** — the set; the partial order lives in sibling links |
| request → its plan | **`IntergraphEdge`** (single member) | n/a |

`cat = c + a + t` keeps working: `ordered=True` compositional links remain expressible and
are what the pipeline level uses.

> ⚠ **The `pipeline → its capacity steps` row is SUPERSEDED by §amendment-3.2.** It becomes
> `ordered=False`, with step order **derived** from the steps' declarations rather than held
> in the member list. Every other row stands. `ordered=True` compositional links remain
> expressible — `cat = c + a + t` is unaffected — but no rung of the ladder uses one.

---

## §amendment-3 (CORE-C2R2 — 2026-08-04): P8-A lifted, ordering derived, and where confidence does not live

**Amendment status:** Accepted at CORE-C2R2 for §am-3.1 and §am-3.2 (both ship in this item).
**Proposed** for §am-3.3 and §am-3.4, which record rulings whose consumers arrive at C2R4 and
C2R5.

Produced by the CORE-C2R2 pre-build read-through, reconciled at `origin/main` `3591add`
against the CORE-C3R1 ship (`ae63aa2`, `find-verdict-confirmed`) and the decisions recorded in
`confirmation_docs/CORE_C2_DECISIONS.md`. **This amendment does not restate §am-1 or §am-2.**

### am-3.1 — P8-A is lifted. `compositional=True` with `ordered=False` is permitted.

`Metagraph.add_intergraph_hyperedge` validation **step 10** refused the combination
(`compositional and not ordered`). It is removed, along with the dead defence-in-depth copy in
`update_intergraph_hyperedge` — the early compositional refusal there means `ihe.compositional`
is always `False` by the time that check runs.

**This is a deliberate override of a recorded and sound argument, not the restoration of a
lost contract.** §am-1.1 located the rationale in `INTERGRAPH_EDGES_DESIGN.md`
(*"compositional implies identity-bearing composition (cat=c+a+t — order/duplicates matter);
set semantics is incompatible"*), and §am-2.3 established that **no** citation of ADR-0148
supports the override — ADR-0148's own claim that `ordered=False` is the compositional default
was a reconstruction error, corrected at ADR-0148 §amendment-1. The override must be argued on
its merits, and the merit is narrow and specific:

> `ordered` on a compositional link expresses a **total** order over its members. A plan's
> milestones are a **set** with a **partial** order over them, carried by sibling dependency
> links so that *parallel* is the **absence** of a link (ADR-0206 §2). An `ordered=True` member
> list cannot express a partial order, so without this lift **a plan with two parallel
> milestones is inexpressible.**

The identity argument survives untouched for the cases it was written about: an
identity-bearing composition whose members genuinely form a sequence still declares
`ordered=True`, and `cat = c + a + t` still constructs.

**Two behaviours callers must know**, neither of them new:

- `ordered=False` **sorts and dedups** at construction (`mindsos_core/schema/types.py`), not
  merely dedups. §am-2.3 records this correction to §2.
- Dedup happens **before** the cardinality check (P14-A), so a set that collapses to one
  anchor and one member still raises at step 8. That is correct — a single-member composition
  is an `IntergraphEdge` (§am-1.2).

**`ordered` is a property of the hyperedge *type*, not of the link**, and a reloaded metagraph
carries no schema (`MetagraphLoader` restores `schema_name` only), so on reload the factory
treats every hyperedge as `ordered=True` under P9-A. This is not a defect introduced here, and
§am-3.2 removes the ladder's exposure to it.

**Amends:** §2 (P8-A paragraph), Phase 05c pushback **P8-A**, `docs/concepts/glossary.md`.

### am-3.2 — A pipeline's step order is DERIVED, not stored

§am-2.3 assigned `pipeline → its capacity steps` the hyperedge with `ordered=True`, on the
ground that *"the sequence is the pipeline"*. That row is superseded. The link becomes
**`ordered=False`**, and the execution order is **recomputed** from the members' own
`CONSUMES` / `PRODUCES` declarations plus the pipeline's start DataStates — a topological sort
over the bipartite topology of ADR-0156, with a **first-by-IRI tie-break** where the order is
genuinely free.

**Ground — §1's own requirement, applied to itself.** Every level must be *verifiable by the
level below*. A stored member order is an assertion **that can contradict the level below**:
nothing prevents a persisted order from disagreeing with what the steps' declarations allow,
and the model has no way to detect it. A derived order **cannot** disagree, because it is
those declarations read in sequence. This is the criterion ADR-0192 used to reject a stored
`fundamental` boolean — *"it duplicates information the PRODUCES topology already encodes"* —
and §3 already states that sequence-versus-parallel is read from data flow and is *"an output
of planning, not an input."* Holding it in a member list feeds it back in as an input.

**What this deliberately gives up.** A capacity appearing **twice** in one stored pipeline
becomes inexpressible, because `ordered=False` dedups. That is intended, not a cost:
`execute_pipeline` holds one blackboard slot per DataState IRI, so a second firing overwrites
the first — the shape recorded as defect **D-E** — and repeated application is served by a
collection DataState with a map, one `PipelineRun` per member (ADR-0199, ADR-0204). Making it
structurally impossible is the point.

**What does not change, and must not be re-planned against.** This governs the **stored** form
only. The `Pipeline` dataclass keeps `steps: Tuple[DAGStep, ...]`; `execute_pipeline` keeps
walking it in tuple order; finders keep returning steps in the order they built them. **No
runtime behaviour and no brain-facing call changes.** What changes is what C2R4's `pipelines`
store writes, and the reconstruction that reads it.

**Consequence for the store:** the tie-break must be fixed and recorded, or `Pipeline` equality
and `Pipeline.to_dict()` stop being stable across a store round-trip. First-by-IRI is the
convention `ConjunctionFinder` already uses for producer selection.

**Amends:** §am-2.3's ordering table (one row). **Consumers:** C2R4.

### am-3.3 — Confidence does not reach a compositional link, so §am-1.5 is not amended

`CORE_C2_DECISIONS.md` §2 (**D1**) asked whether compositional links must gain editable
properties so confidence and an `in_force` flag could move. **Neither consumer exists**, so
§am-1.5's terminality is left exactly as recorded:

- **Pipelines carry no confidence.** ADR-0206 §5's *"fitness for this task"* moves to the
  map's **targeting** confidence — decided when a task's final DataState is chosen, not when a
  pipeline is. A pipeline is deterministic; once the target is right there is nothing left to
  be uncertain about. ⟹ `StepExecutionRecord.confidence`, populated as
  `1.0 if success else 0.0`, is a **restated success flag**, not a measurement. It is deleted.
- **The milestone confidence is *appropriateness*, child → parent.** Both endpoints are
  milestone nodes in the milestone graph, so the link is **same-graph 1-1** — and
  `add_intergraph_edge` refuses same-graph at step 3, the intra-graph `Edge` has no
  `compositional` flag, and the hyperedge refuses 1-1 at step 8. This is precisely the
  situation §am-1.3 (Ruling A) already ruled for C11's `SPECIALIZES`, and the same ruling
  applies: **a plain typed intra-graph `Edge`**, whose properties are freely mutable.
- **`in_force` must not exist.** §6 runs verification on read and §am-1.5 states that §8's
  dormancy is **derived**, not recorded. A stored flag restating a derived fact is ADR-0192's
  rejected pattern again.

⟹ **D1 is closed by having no consumer, not by a ruling on the mechanism**, and the question
re-opens at **C2R5** with the first item that writes. Deciding it now would be building a
mechanism ahead of its consumer, which §Alternatives item 5 already rejects.

⚠ **One consequence this hands to the plan-level item.** If child → parent is a plain edge,
then **decomposition is not a composition** — which `CORE_C2_DECISIONS.md` §1.2 and ADR-0206 §2
both assume it is. **C2R6 owns reconciling that**; it is not settled here.

### am-3.4 — A pipeline with no steps is not a pipeline

Both shipped finders return `Pipeline(steps=(), edges=())` when the target DataState is already
in the start set, and `learn_pipeline` validates only the ADR-0182 codec round-trip, which an
empty pipeline passes — so empty pipelines are **storable today**.

Under §2 as amended by §am-1.2 a pipeline node's steps are its compositional **members**, and
neither primitive expresses zero of them: `add_intergraph_hyperedge` refuses `m < 1`, and the
single-member `IntergraphEdge` has no target. The declaration rule closes it from the other
side — *a node with no link is not at any level.*

**Ruling: an empty pipeline is not a pipeline.** *"I already hold the target"* and *"here is a
route"* are different answers, and returning an empty collection for the first leaves **four**
consumers to infer it from an absence — the pipeline store, the episode corpus (an empty
capacity index closes a request with no grounding, the same shape as a crash), `viz_spec`, and
the planning loop, which otherwise cannot distinguish a **satisfied** milestone from an
unreachable one.

The fix belongs where the type is defined: **`FindVerdict` should distinguish *routed* from
*already held*.** That is CORE-C3's surface, and the request is filed to the C3 continuation.
**`already_held` is not transitional** — it survives the forward walk of
`CORE_CAPACITY_GRAPH_TRAVERSAL.md`, where it is the walk terminating at step zero.

**If C3 declines**, C2R4 refuses an empty pipeline at the store and the caller carries the
distinction. That is strictly worse — it makes `learn_pipeline` reject something the finders
legitimately return, and it leaves the episode and `viz_spec` halves unfixed — but it is
C2-local and C2R4 will take it rather than wait.

**C3 did not decline.** `FindVerdict.already_held` ships at CORE-C3R1 as a **derived**
property — `found and not pipeline.steps` — so there is no field beside the steps that can
disagree with them. That is this ADR's own §5 ground and the one ADR-0192 used to refuse a
stored `fundamental` flag, and it is why `found` is derived too. It is **not** a sixth
`FIND_REASONS` value: `reason` is `None` whenever a route was found, and *already held* **is**
a route, of length zero. The finders still return `Pipeline(steps=())`, so nothing any brain
calls changes — C2R4 reads `already_held` rather than inferring zero members, and the fallback
above is not needed.

**Consumers:** C2R4, and CORE-C3.

---

## §amendment-4 (CORE-C2R3 — 2026-08-06): the substrate boundary — a composition cannot cross a `Metagraph`

**Amendment status:** Proposed. Flips to Accepted with **CORE-C2R3**.

Produced by the CORE-C2R3 pre-build read-through, **read against the code at `origin/main`
`1063fd1`** (plan §0: *an ADR does not reach Accepted until someone has read it against the code
it governs*). Every line reference in §am-4.7 was verified, not inferred. **This amendment
does not restate §am-1, §am-2 or §am-3.** It records a constraint none of them saw: the
composition primitive §2 selects cannot express three of the five rungs of §1's ladder, for a
reason that is structural and not a defect in any one module.

---

### am-4.1 — A compositional link cannot cross a `Metagraph`

`Metagraph.add_intergraph_edge` **steps 1–2** (`mindsos_core/models/metagraph.py:1602-1611`)
require **both** endpoint graphs to be present in `self.graphs` — the graphs of **one**
`Metagraph` instance:

```
if source_graph_id not in self.graphs:  raise IdentityError(...)
if target_graph_id not in self.graphs:  raise IdentityError(...)
```

`add_intergraph_hyperedge` applies the same containment rule to anchors and members.
`IntergraphEdge` and `IntergraphHyperEdge` address their endpoints as `(graph_id, node_id)`
pairs, and `intergraph_edges` / `intergraph_hyperedges` are dictionaries **on the `Metagraph`**
(`metagraph.py:374,380`). There is no representation for an endpoint in another metagraph.

The name is misleading and has misled this plan: *inter**graph*** means *between two graphs*,
**not** *between two metagraphs*.

### am-4.2 — A running brain holds four `Metagraph` objects, and shares none of them

| Instance | Constructed at |
|---|---|
| KnowledgeLayer Global | `mindsos_knowledge/knowledge_layer.py:208` |
| KnowledgeLayer Local(user) | `knowledge_layer.py:243` — lazy auto-create |
| CapacityLayer Global | `mindsos_capacity/capacity_layer.py:160` — its **own** `create_global()` |
| CapacityLayer Local(user) | `capacity_layer.py:192` — `create_local(user_id)` |

`mindsos_server/boot.py:211,222` construct `CapacityLayer(kl=kl)`. The `kl` argument is injected
so **write-capacity bodies** can reach the KnowledgeLayer through `CapacityContext`
(`capacity_layer.py:137-158`). **No metagraph is shared.** `CapacityLayer` builds its own
Global whenever `global_metagraph` is not supplied, which is every caller in the repo.

### am-4.3 — Consequence: three of five rungs are inexpressible

§1's ladder is `capacity → pipeline → milestone → plan → request`. §2, as amended by §am-1.2,
makes each rung a compositional `IntergraphEdge` or `IntergraphHyperEdge`.

| Rung | Anchor lives in | Members live in | Expressible |
|---|---|---|---|
| pipeline → its capacity steps | KL metagraph (`pipelines` role, C2R4) | **Capacity metagraph** | **NO** |
| milestone → a pipeline reaching it | KL metagraph | KL metagraph | yes, **same realm only** |
| plan → its milestones | KL metagraph | KL metagraph | yes, **same realm only** |
| request → its plan | KL metagraph | KL metagraph | yes, **same realm only** |

And the realm qualifier is not cosmetic. The two shipped realm decisions both produce
cross-realm links immediately:

- A user teaches a pipeline **Local** (ADR-0203, `learned-pipelines`) over capacities that are
  **Global**. Cross-layer *and* cross-realm.
- `CORE_C2_DECISIONS.md` §6 and `CORE_RECONCILIATION_PLAN.md` §12.2 both bootstrap **both
  realms up front** — for milestones and for the resource graph — precisely so a Local node can
  compose over Global content. That is the link this constraint forbids.

⟹ **C2R4, C2R5, C2R6, C2R7 and the resource graph all require a link the substrate cannot
create.** C2R3 is where the mechanism is chosen, so it is where this is settled; discovering it
at C2R4 means rebuilding the substrate after three items have been designed against it.

**No prior record.** Not §Consequences, not §am-1.6 (which asks whether a composition *pins* a
graph, having assumed it can *reach* one), not `CORE_C2_DECISIONS.md` §4, not
`CORE_VERIFIED_FINDINGS.md` §12 or §13. §am-1.7 measured that the primitive has no consumers
and read that as *scale of work*; it is also *why the constraint was never hit*.

### am-4.4 — Ruling: one `Metagraph` per user. Realm becomes a node property.

**§1 says there is one graph. Four `Metagraph` objects are four graphs.** Under §0 of
`CORE_RECONCILIATION_PLAN.md` — *concepts are the source of truth, code matches concepts* — the
containers change, not the ladder.

1. **The layer split collapses.** `CapacityLayer` stops constructing its own metagraph and takes
   the `KnowledgeLayer`'s. The capacity category-graphs and the `capacity:datastates` graph
   become graphs **in the same `Metagraph`** as the L2 role-graphs. This is a change of
   *container*, not of *ownership*: `CapacityLayer` still owns capacity registration,
   `KnowledgeLayer` still owns roles and IRI minting. Nothing about RULES §8 changes.

2. **The realm split collapses.** One `Metagraph` per user, holding the Global content and that
   user's Local content. **Realm becomes a property of a node**, not a property of which object
   the node is stored in.

**Why realm must be a property.** §9 already states that *Global is what the system ships by
default* and *Local is everything that differs*, and that an admin **promotes** Local to Global.
Under two metagraphs, promotion is a **move between objects** — a delete and a re-mint, which
§am-1.5 terminality forbids for anything a composition points at, and which changes the node's
identity out from under every link that references it. Under one metagraph, promotion is a
property change on a node whose identity and links are untouched. The concept in §9 is only
implementable the second way.

**The identifiers already agree.** Only four IRI kinds embed a `user_id` —
`episode_iri`, `memory_composite_iri`, `capacity_snapshot_iri`, `staged_evidence_iri`
(`mindsos_knowledge/identifiers.py:264,278,299,327`), all per-user *records*. Everything the
ladder is made of does not: `learned_pipeline_iri` (`:439`) mints
`learned-pipelines-<v>:pipeline:<name>:<seq>` with **no user in it** and is Local-only by
**role**, not by identity. Same for `pipeline_iri`, `request_pattern_iri`,
`learned_parameter_iri`. **A ladder node's identity is already realm-independent** — the realm
lives only in which object currently holds it. Making it a property records a fact the IRIs
already imply.

**Sub-ruling: realm is a property of the NODE, inside one role-graph — not a graph per realm.**
Both realms' content for a role live in the **same** `Graph`. This keeps ADR-0150 §amendment-3's
lock — *one graph per role per metagraph* — intact, keeps `graphs_by_role` and the closed
16-role set unchanged, and keeps promotion a property change. **It also is not what makes the
ladder work:** a pipeline node and a capacity node are in different *graphs* regardless of
realm (`pipelines` vs `capacity:<category>`), so `add_intergraph_edge`'s step 3 — *source and
target graphs must differ* — is satisfied by the **layer** distinction alone. Realm never
enters the link rule. The cost lands entirely on persistence (§am-4.7 item 2).

**Consequence for §5's criterion.** Realm-as-a-property is **not** an instance of
*topology stored as properties*. Realm is not topology — it is an **approval fact about one
node**, per §9, and it relates that node to nothing else. §am-1.4's test applies: if the realm
flag disappeared the system would have lost a way to record approval, not forgotten something it
knows. Substrate, not ladder.

**And it is not the pattern §am-3.4 re-applies.** That ruling makes `already_held` **derived**
(`found and not pipeline.steps`) so no stored field can disagree with the steps, on the same
ground ADR-0192 used to refuse a stored `fundamental` flag. The test both share is *does the
graph already encode this?* For realm the answer is **no** — no topology, declaration or run
record says who approved a node, so there is nothing for a stored flag to contradict. A stored
fact is the rejected pattern only when it restates one the structure already carries.

### am-4.5 — Rejected

1. **Extend `XRef` with a `compositional` flag.** `XRef` (ADR-0128,
   `mindsos_core/models/xref.py:40`) is the one shipped primitive that spans metagraphs, and it
   already carries mutable `properties` and inverse indexes (`_xrefs_by_source`,
   `_xrefs_by_target`). **Rejected on three grounds.** §am-1.4's scope clause names `XRef` as
   **substrate**, explicitly outside the ladder — making it a ladder primitive reverses a ruling
   one amendment old. It would give the system **two** composition primitives with different
   rules, which is §Alternatives item 2 (a per-level registry) in a new form: the same
   relationship read two ways depending on which side of a container boundary it lands on. And
   its `target_stale` field is a **stored** dormancy flag — the exact pattern §am-3.3 and
   ADR-0192 reject — which would arrive as the by-product of a storage decision rather than as a
   decision anyone made.
2. **Mirror Global nodes into each Local metagraph** so compositions stay intra-metagraph.
   **Rejected — this is §5 verbatim.** A mirror is a parallel copy of graph structure, and the
   copy can disagree with the original with nothing able to detect it. It is also the failure
   §Context lists first: *a plan exists twice*.
3. **Narrow the ladder to one realm and one layer** — Local-only, capacities moved into the L2
   metagraph. **Rejected on the concept.** It makes Global pipelines, milestones and plans
   permanently impossible, so *"an admin promotes Local to Global"* (§9) has no referent above
   the capacity level, and a Skill (§8) could never ship a pipeline or a milestone — which
   §Consequences requires it to.
4. **One metagraph, but a separate `Graph` per realm** — a Global `pipelines` graph beside a
   per-user Local one. This is the cheaper option on machinery: `MetagraphRepository.persist`
   iterates `metagraph.graphs.values()` and `FalkorDBLocalPersister.delete` keys on
   `g.id IN $gids`, so realm-as-a-graph would need **no persistence change at all**.
   **Rejected on the concept.** It reopens ADR-0150 §amendment-3's explicit lock (*one graph per
   role per metagraph*, whose own alternatives table already rejected `(role, version)` keying),
   and — decisively — it makes promotion a **move between graphs**, which is the delete-and-re-mint
   §am-4.4 rejects two metagraphs for. Choosing it would buy back the persistence work by
   reintroducing the defect the ruling exists to remove.
5. **Leave the containers and let each level item work around it.** Rejected — that is
   §Alternatives item 1 (*reconcile pairwise*), and it is what produced the duplications this
   ADR removes.

### am-4.6 — What this does **not** change

- **Not a merge of the layers.** L2 and L3 keep their façades, their APIs and their ownership.
  What is shared is the **substrate object**, the same way two roles already share one.
- **Not a change to the primitive.** `add_intergraph_edge` / `add_intergraph_hyperedge` are
  untouched. Steps 1–2 remain correct; what changes is that both endpoints are now inside the
  same metagraph, which is what the steps have always required.
- **Not a change to §am-1.5.** Compositional links stay terminal. §am-3.3 stands: dormancy is
  derived on read, nothing is stored.
- **Not a change to `XRef`.** Cross-metagraph references remain available for the cases they were
  built for. What is removed is the *need* for one inside the ladder.
- **Not a change to persistence semantics.** Global and Local content must still be **saved and
  loaded separately** — a user's Local content is per-user and Global content is shared. That
  becomes a **partition of one metagraph by node realm** rather than two whole objects. This is
  the largest piece of work in the ruling and is named in §am-4.7.

### am-4.7 — Consequences, measured

The five below were read from the code at `1063fd1`. They are the ruling's blast radius. Ranked
by cost, not by order of discovery.

1. **Realm resolution — 76 call sites, and this is the bulk of the work.**
   `global_metagraph()` / `local_metagraph(user)` / `global_view()` / `local_view(user)` are
   called 76 times outside their own definitions across `mindsos_capacity`, `mindsos_knowledge`,
   `mindsos_server`, `mindsos_intelligence` and `mindsos_cli`. **Every one currently answers
   "which realm?" by which object it is holding.** Each becomes either a property filter or an
   unfiltered read of the single metagraph. Two shapes recur and should be converted first:
   the ten `builtins/*.py` bodies that take `capacity_layer.global_metagraph()`, and the
   Global-then-Local overlay in `learned_parameters_snapshot.py:64`, which becomes an ordering
   over one node set rather than over two objects.

2. **The persistence partition — the one genuinely new mechanism.**
   `MetagraphRepository.persist(metagraph)` (`metagraph_repository.py:113`) iterates
   `metagraph.graphs.values()` and persists **whole graphs**;
   `FalkorDBLocalPersister.delete(user_id)` DETACH-DELETEs by `g.id IN $gids` over every graph in
   the metagraph; `MetagraphLoader.load(metagraph_id)` reconstructs the whole object. Under one
   metagraph with realm as a node property, **all three would touch Global content on a Local
   operation** — `delete` most dangerously. Partitioning must move from **graph granularity to
   node-realm granularity**, and the loader must reconstruct Global + one user's Local into one
   object. An intergraph link straddling realms is written with the **Local** half.
   ⚠ **This is the cost §am-4.5 item 4 would have bought back, and the reason that option is
   worth re-reading before this ships.**

3. **`CapacityLayer` construction — six non-test sites.** `capacity_layer.py:160` must stop
   defaulting to `create_global()`; `mindsos_server/boot.py:211,222`,
   `mindsos_cli/commands/capacity.py:95,288` and `mindsos_cli/commands/skill.py:70,79` must
   supply the KnowledgeLayer's metagraph. `_capacity_index` is keyed by `metagraph_id`
   (`capacity_layer.py:171`) and collapses to a single key.

4. **Role and graph-id collision — NONE. Verified, no work.** Capacity roles are namespaced:
   `capacity:datastates` and `capacity:<category>` (`mindsos_capacity/identifiers.py:64,67`).
   L2 roles are bare names (`ontology`, `lexicon`, `learned-pipelines`, …). No overlap; the
   nearest pair is L2's `capacity-state` / `capacity-gaps`, hyphen not colon.
   **The six "role count 16→17" assertions are unaffected** — they assert
   `len(ALL_ROLES)` and `len(_ROLE_SCHEMA_BUILDERS)`, module constants in
   `mindsos_knowledge/identifiers.py`, not roles present in a metagraph. The only consumer of a
   live metagraph's role set is `mindsos_cli/commands/knowledge.py:635`
   (`sorted(view.roles())` for a scan), which would newly enumerate the `capacity:*` roles and
   needs a filter or a documented widening.

5. **Bootstrap ordering — the old hazard dissolves, a worse one replaces it.**
   `local_metagraph(user_id)` lazy-creates, which is what `CORE_C2_DECISIONS.md` §12.1 item 3
   caught (*a read must never create* — consulting a roster materialised an empty Local ahead of
   the durable boot that restores one). Under one metagraph there is no Local object to
   materialise and that specific hazard goes. **Its replacement is deletion scope** — item 2's
   `delete(user_id)`. The failure mode moves from *silently creating nothing* to *silently
   deleting everything*, so it must be closed with a test that makes it go RED (RULES §9).

### am-4.8 — Amends, and consumers

**Amends:** §1 (one graph — states the substrate consequence it implies), §2 (the primitive's
endpoints are in one metagraph), §9 (realm is a node property; promotion is a property change),
§am-1.4 (the scope clause gains `realm` as an explicit substrate example), and
`CORE_C2_DECISIONS.md` §4 (*"the link mechanism does not exist"* — see the correction below).

**Correction to §am-1.7 and to `CORE_C2_DECISIONS.md` §4.** §am-1.7 reports zero consumers for
`IntergraphHyperEdge` and `compositional` outside `mindsos_instances` and core. That holds. It
does **not** hold for the ordinary `IntergraphEdge`, which has a live writer and a live reader:

- **writer** — `mindsos_capacity/capacity_layer.py:425,432` emit `PRODUCES` / `CONSUMES`
  (ADR-0156's bipartite topology) on every capacity registration.
- **reader** — `mindsos_capacity/views.py:144` `_iter_edges`, feeding `outputs_of`, `inputs_of`
  and `producers_of`.

⟹ *"The L2 knowledge write path cannot write a link"* is true of `KLWriteHandle` and
`MetagraphView` only. **A link write path and a link read path already ship and are in
production use at the capacity level.** Under §10 — *one traversal primitive* — C2R3 must route
`CapacityLayerView`'s walk through the accessor it adds to `MetagraphView`, not add a second
reader beside it. Two readers of the same relation is the defect §10 exists to prevent.

**Consumers:** CORE-C2R3 (which cannot build `walk()` across realms until this lands), the
resource graph, C2R4, C2R5, C2R6, C2R7.

**Rationale record (plan §0.1).** Beyond this amendment, the reasoning is owed at the point of
use: the module docstrings of `mindsos_capacity/capacity_layer.py` (why it no longer builds a
metagraph), `mindsos_knowledge/knowledge_layer.py` (why one object holds both realms) and
`mindsos_core/models/metagraph.py`'s intergraph section (why *intergraph* is not
*inter-metagraph*), plus the CORE-C phase map. A central document alone does not work.
