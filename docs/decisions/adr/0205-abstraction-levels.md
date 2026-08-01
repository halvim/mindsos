---
title: Abstraction levels — one graph at several resolutions
status: Accepted
date: 2026-07-31
layer: L3
related: [0071, 0132, 0156, 0182, 0183, 0203, 0206]
---

# ADR-0205: Abstraction levels — one graph at several resolutions

**Status:** Accepted

**Date:** 2026-07-31

**Related:** ADR-0156 (bipartite capacity↔DataState topology — the ground level),
ADR-0132 (intergraph edges / hyperedges — the composition primitive), ADR-0071
(pipeline finder), ADR-0182 (node-value serialization), ADR-0183 (skill bundle
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
  same thing.
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
exist.

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
revives it. Removing user data is an explicit opt-in.

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

## Amendments

### amendment-1 (2026-07-31, CORE-C2 pre-build read-through) — §2's P8-A ground is withdrawn

**Trigger.** The CORE-C2 chat read this ADR against the code before building, per §0 of
`confirmation_docs/CORE_RECONCILIATION_PLAN.md`. Three of §2's supporting statements do not
survive. The **decision** to permit `compositional=True` with `ordered=False` stands; its
**recorded justification** is replaced.

**What was wrong.**

1. §2 states the original argument *"could not be recovered — `PHASE_05c_DESIGN_LOG.md` does
   not exist."* That file does not exist; `PHASE_05c_IMPLEMENTATION_LOG.md` does, and the
   argument survives in three places — `confirmation_docs/INTERGRAPH_EDGES_DESIGN.md`,
   `confirmation_docs/PHASE_MAP.md` (the Phase 05c P8-A row) and
   `confirmation_docs/PHASE_05c_CONFIRMED.md`. It reads: *compositional implies
   identity-bearing composition (`cat = c + a + t` — order and duplicates matter); set
   semantics is incompatible with that invariant.* The ADR set was never searched.

2. §2 states `ordered=False`'s *"only real effect is factory dedup"*. It **sorts and dedups**
   at construction (`mindsos_core/schema/types.py`, `IntergraphHyperEdgeType.ordered`).

3. **There is no recoverable ADR-0148 amendment on this point, and the two documents citing
   it contradict each other.** ADR-0148 §Decision says compositional hyperedges are
   `compositional=True, ordered=False` *"by default (per the amendment cited in the
   glossary)"*. `docs/concepts/glossary.md` says the primitive *"Refuses
   `compositional=True, ordered=False` per ADR-0148 amendment."* Each cites the other,
   neither reproduces the amendment, and they assert opposite outcomes. ADR-0148 is itself a
   reconstructed record which states it is *"not the original text"*. **Four independent
   sources — the code, the glossary, `PHASE_MAP.md` and `INTERGRAPH_EDGES_DESIGN.md` — say
   refused; one reconstructed line says default.** The refusal was the real decision.
   ADR-0148's line is a reconstruction error, corrected at ADR-0148 §amendment-1.

**What replaces it.** The amendment is a **deliberate override of a sound argument** — not
the recovery of a lost one, and not the restoration of a contract a later phase reversed:

> P8-A's rationale is correct about `cat = c + a + t`, and that case must keep working:
> `ordered=True` compositional links remain expressible and are what the pipeline level
> uses. What the rationale did not anticipate is a composition whose members form a **set
> with a partial order over them**. §3 of this ADR requires exactly that at the plan level —
> a plan's members are its milestones, all necessary, with sequencing carried by separate
> sibling dependency links so that *parallel* is the **absence** of a link (ADR-0206 §2). An
> `ordered=True` member list can only express a **total** order, and would make parallel
> siblings inexpressible. `ordered=False` compositional links are therefore required, and
> `ordered` is chosen **per level**, never fixed for the primitive.

**Ordering per level.**

| Link | `ordered` | Why |
|---|---|---|
| pipeline → its capacity steps | `True` | the sequence *is* the pipeline; duplicates legal (a capacity may fire twice). Holds only the capacity steps — start and end DataStates are separate links |
| milestone → a pipeline reaching it | moot | single-member links (ADR-0206 §amendment-1) |
| plan → its milestones | `False` | the **set** of milestones; the partial order over them lives in sibling→sibling dependency links |
| request → its plan | moot | single-member |

**Consumer:** CORE-C2R2, which also updates `docs/concepts/glossary.md`.

### amendment-2 (2026-07-31, same read-through) — §11's `chain_level` evidence is withdrawn

§11 states: *"'Level' is correct and already in the code: `BlameVerdict.chain_level` takes
`hint | map | plan | plan_subtree | pipeline` — this ladder, already named."*

**The terminology choice stands** — *layer* is taken by L0–L5 and *tier* by `TierEnum`, so
*abstraction level* is correct. **The evidence does not.** §1's ladder is
`capacity | pipeline | milestone | plan | request`. Two of five values match. `hint` and
`map` are Phase-1 **steps**, not levels (ADR-0206 §3: *"The steps are request → hint → map →
plan"*); `plan_subtree` is already retired by ADR-0206 §Consequences; `capacity`, `milestone`
and `request` are absent from `chain_level` entirely.

⟹ **`chain_level` has no defined target set** until hint and map are settled as steps rather
than levels. That is a decision for CORE-C4R2, not a wording fix, and that item's scope
("reconcile `chain_level` to the ladder") is undefined until it is made.

⟹ **Consequence for `request_knowledge`** (ADR-0206 §7): it references two different kinds of
thing — step outputs (hint, map) and levels (plan, milestone, pipeline). The rule that a
declared level requires the level below applies to the **level half only**; a hint has no
level beneath it to require. A validator must not demand all five.

### amendment-3 (2026-07-31, same read-through) — lazy descent implies a per-level trace

§4 states that the Mental Model loads the highest abstraction level and descends only as far
as confidence requires. §11 states the chain is *"the per-request trace across these same
levels"*. **Neither says the trace must therefore carry a record at each level** — and
without that statement, an optimisation replacing the per-level trace records with links into
the durable levels looks correct. It preserves *which* node was used at each level while
silently deleting **the descent itself**: loaded the plan level, not confident, descended to
milestone, still not confident, descended to pipeline. That history is the per-request
reasoning record, and it is what §4 describes.

**Amended:** the per-request trace carries **one record per abstraction level**. Those records
are thin — an identity, a link to the durable node used, and per-request state; all structure
remains links. The trace record for level *L* is named `<L>Run`.

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
exhaustive — `StepExecutionRecord` is the capacity-level trace and is renamed `CapacityRun`
rather than removed.

**Consumers:** the per-level items of CORE-C2. Renames land with each level's schema change,
never as a sweep (`CORE_RECONCILIATION_PLAN.md` §10).
