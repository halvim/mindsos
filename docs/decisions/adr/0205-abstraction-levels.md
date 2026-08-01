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

**Amendment status:** Proposed. Flips to Accepted with **CORE-C2R1**.

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
- `deprecate_intergraph_edge` (Phase 10) raises the same
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
