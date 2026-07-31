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
