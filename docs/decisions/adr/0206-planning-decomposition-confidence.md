---
title: Planning as a loop — milestones, decomposition, and confidence
status: Proposed
date: 2026-07-31
layer: L4
related: [0094, 0152, 0156, 0171, 0172, 0195, 0198, 0199, 0203, 0205]
---

# ADR-0206: Planning as a loop — milestones, decomposition, and confidence

**Status:** Proposed

**Date:** 2026-07-31

**Related:** ADR-0205 (abstraction levels — this builds on it), ADR-0171 (orchestrator),
ADR-0172 (lifecycle phases), ADR-0195 (Phase-1 seam), ADR-0152 §2 (`request-patterns`
schema), ADR-0094 §am-1 (per-pipeline confidence moved to ALS — **not reopened**),
ADR-0199 (collection map/fold).

Closes `POST_PHASE_38_PHASE_MAP.md` §7 **q4** ("`planning.*` v0 → real catalog migration
discipline").

---

## Context

The six-phase lifecycle runs. What it lacks is the thing that makes planning mean anything:
a way to say **how sure am I**, and a way to act on the answer.

Concretely, at `origin/main` `fafc679`:

- `planning.decompose` returns `[]` and `is_leaf` returns `True`, so **no plan has ever
  been decomposed**. Every request is one milestone and one pipeline.
- `decision.map_to_task_pattern` returns a fixed pattern at confidence **1.0**, so the
  `mapping_confidence_threshold` check is vacuous.
- `predicate.sufficient` defaults `True`; `should_replan` defaults `continue`.
- `MAX_DEPTH = 3` in `plan_construction.py` is a brain's test artifact standing in for a
  stopping rule that was never designed.
- Taught pipelines are stored (`learned-pipelines`) but **never consulted at runtime** —
  `execution.py` composes from scratch at every leaf.
- `request-patterns` — which carries `relevant_hints`, `paired_pipelines`,
  `mapping_confidence_threshold` and `confidence` — **has no writers**.

The purpose of what follows is not to compute a number. It is to **use what the system is
confident about to raise the chance of success on what it isn't.** A low-confidence answer
is not a small number — it is an answer that is probably wrong.

---

## Decision

### 1. A milestone is a DataState

**A milestone is a DataState the system already knows about — one it can recognise and
reason with — which it does not currently hold, and which lies between where it is and
where it needs to go.**

It must be *known*: you cannot aim at something that is not in the graph. "Does not have"
refers to the current run's state, not to the DataState's existence.

Two halves, and conflating them causes confusion:

| Half | What | Lifetime | Where |
|---|---|---|---|
| target | a DataState | durable, shared | capacity graph |
| instance | "for request 42, reach it, pending, 1 replan" | per-request | `chain` graph |

A milestone therefore needs **no new declaration type**. Milestones must never become nodes
in the capacity graph: same shape as a capacity, different lifetime and scope.

**Discovery — hubs.** A DataState appearing in multiple pipelines is a milestone; pipelines
are sequences of capacities and DataStates, so a coincident DataState across two or more
pipelines is a hub. A hub the system **already holds** is not a milestone. Measurement is
over the capacity graph at v1, and over coincident DataStates across pipelines as the
system learns — computed incrementally on each learn. Milestones may also be **taught**.

**The milestone graph *is* the index.** A milestone node exists because it is a hub, and
its compositional members *are* the pipelines it is coincident in. There is no separate
index to maintain — only an update trigger.

### 2. A plan is a DAG of milestones

Not a list. An edge means "must complete before"; no edge means order is free. Sequential
and parallel are the presence or absence of an edge. A plan is a pipeline of milestones —
the same structure as a Pipeline one level down (ADR-0205).

Two relations: **parent → child** (decomposition) and **sibling → sibling** (dependency).
AND/OR and ordering are carried by the structure per ADR-0205 §3.

Tree vocabulary: *layer* (one level of the tree), *branch* (a milestone and everything
beneath it), *children*, *siblings*, *leaf* (not decomposed, because a pipeline reaching it
cleared the bar).

### 3. Planning is a loop

The steps are **request → hint → map → plan**, and *plan* is a loop:

```
search → find → decompose → (repeat)
```

- **Map** produces the milestone tree.
- For each milestone, **search** L2 for a pipeline the system already knows from the
  current state to that milestone's DataState.
- If none, **find** one in the graph.
- Check its confidence.
- Where confidence is too low, **decompose** that branch and repeat on the smaller pieces.

Outputs: a **formulated plan** and an **execution tree** (which milestones are parallel,
which dependent) — the execution tree is an *output*, read from the pipelines chosen.

**There is no "failed find."** If no path exists, the system *doesn't know* — a true
analysis result, not an error. `PipelineNotFoundError` is retired accordingly (a single
capacity is a one-step pipeline; "no route" is a verdict, not an exception).

### 4. Decomposition

> I'm confident in my plan if I'm confident in the sub-plans that achieve its milestones.
> Decomposition is what I do when I'm not confident: break the plan into parts I am
> confident about, and if all the parts clear the bar, my confidence in the whole plan goes
> up. Composition across milestones is what turns part-confidence into plan-confidence.

**It emits one layer at a time.** Each resulting sibling is evaluated independently:
sibling with a trusted pipeline is done; sibling without is decomposed. The tree grows only
where confidence is missing, so whole breakdowns are never enumerated and there is no
combinatorial explosion.

**It makes confidence computable, not success likelier.** An unresolved pipeline has no
confidence — not low, **unknown**. Inserting waypoints until every hop is known replaces an
unknown with a product of knowns.

**Therefore stop at the first pipeline clearing the bar.** Once a hop has a number,
decomposing further only multiplies more factors in and lowers it. **Never decompose
something you already trust.**

**Termination is guaranteed.** A capacity is a one-step pipeline at confidence 1.0, so a
breakdown is always possible. `MAX_DEPTH` is retired — the confidence rule is the stopping
rule.

**Two capacities, two families:**

| | `planning.decompose` | `decision.select_decomposition` |
|---|---|---|
| returns | candidate compositions for one layer | one breakdown, or "not sure" |
| deterministic | **yes** (per snapshot) | **no** |
| family | `planning.*` (structural) | `decision.*` (judgement) |
| brain-shadowable | should not need to be | yes |

Determinism is **per snapshot**: graph, current state and taught set all change as the
system learns, so plans are not reproducible across sessions — which is already what the
dream subsystem assumes.

### 5. Confidence

**Everything is deterministic, at every level.** A capacity always performs the same
transformation; a pipeline is built from capacities, so it too solves what it solves 100%
of the time.

> The pipeline solves *something* 100% of the time. Is that *something* needed to solve
> task T? **That is the confidence.**

So confidence is **the system's estimate that what a deterministic piece achieves can be
used to solve this task** — and that is exactly why a task is decomposed: keep breaking it
down until the pieces are ones you are confident are the *right* pieces.

**Confidence is relational, not intrinsic.** It is a property of a pairing — (pipeline,
milestone), (plan, request) — never of a pipeline alone. **⟹ Confidence belongs on the
edge.** A node carries *evidence* (`n_runs`, `outcome_history`); the confidence that it
serves a given request kind lives on the link. A capacity is 1.0 because the pairing is
degenerate: asking for its target DataState is asking for exactly what it does.

Confidence is **learned by doing** — internal reinforcement, distinct from the AI
industry's reinforcement learning. ALS moves the values from observed outcomes.
**ADR-0094 is not reopened**: it moved confidence *ownership* to ALS, and a value ALS
writes is consistent with that.

**Values and thresholds.** All confidence values are **1.0** for now; all thresholds are
**0.8**, but **per transition**, never one global constant.

> **Note for future chats:** you will find several constants equal to 0.8 compared against
> values equal to 1.0, and it will look like dead code. It is not. The structure exists so
> ALS can move each value independently. A hint you are 80% sure of and a plan you are 80%
> sure of are not comparable quantities. Do not collapse them.

**Transitions that carry a confidence:** request → hints; hints → milestone set;
milestone set → plan (**appropriateness** — sufficient, enough, correct); milestone →
pipeline; and the composed plan. **Appropriateness is validated at every layer**, not
checked once at mapping.

**Composition:** `P(plan) = P(the breakdown is appropriate) × ∏ P(reach each milestone)`.
Sequential siblings compose by the chain rule, parallel siblings by independence — the same
product, different justification, which matters once ALS measures them.

### 6. "I'm not sure" is not "I don't know"

A breakdown is always possible, so the failure mode is never *"no breakdown exists."* It is
*"I could not find a breakdown I am confident about"* — specifically, low confidence on the
**milestone set → plan** transition.

- **Externally** it answers as "I don't know."
- **Internally** it flags the request for the dream to verify, so the system can become
  sure.

Uncertainty stops being a dead end and becomes work for the dream. The dream's candidate
selection needs a third category — *completed-while-unsure* — alongside success and
failure.

### 7. `request_knowledge` — the shortcut store

**A recorded solution for a kind of request, so the system does not rediscover it through
request → hint → map → plan every time.** This is the shipped `request-patterns` role,
**renamed to `request_knowledge`** — it does not hold a *pattern*, it holds what the system
knows about a kind of request.

**It references hints, maps, plans, milestones and pipelines — and owns none of them.**
Each is its own knowledge node, linked by edges, so a map or a plan can be shared across
request kinds. `relevant_hints` and `paired_pipelines` are already references (IRI lists)
but stored as **properties**, so nothing can walk them; they become edges, and the
confidence rides on those edges.

**Requests do not match patterns.** A request *contains hints*; hints are patterns and are
what get matched. `relevant_hints` declares which hints identify a request kind.

**Scope:** already dual-scope by design (ADR-0150 §am-8) — authored or learned **Local**,
promoted by an admin to **Global**.

**Replacement, not decay.** As a pipeline becomes less appropriate another takes its place;
likewise for milestones; `request_knowledge` updates its pointer. A milestone ceasing to be
*pointed at* is unrelated to it ceasing to be a *hub*. **When nothing clears the threshold,
record "I'm not sure"** rather than pointing confidently at the least-bad option.
Replacement is a mechanism to be built (the writer plus ALS), not an emergent property.

### 8. The v0 placeholders are deleted

The thirteen `placeholder=True` capacities are removed, not kept as fixtures. The Phase-50
reference bundle becomes the canonical test fixture. Interpretation
(`process.*`, `hint.*`, `derive_goal`, `map_to_task_pattern`) ships as **contract only** —
bodies arrive in skill packages, because a core body would be shaped like whichever domain
it was written for and every other brain would shadow it.

---

## Consequences

**Good**

- `MAX_DEPTH` gains a real stopping rule; `planning.decompose` gains a specification.
- Taught pipelines become useful: the system stops re-deriving what it was taught.
- `request-patterns` gains its missing writer and its purpose.
- The system can say "I'm not sure" and route it to the dream — the first honest
  uncertainty path in the lifecycle.
- Blame attribution and planning descend the same ladder, so `chain_level` reconciles
  (`plan_subtree` retires — the loop covers it).

**Cost**

- `PlanResult`'s endpoint dictionaries collapse into the Milestone tree; `Milestone` gains
  a declared target and loses `sequence_index`. This changes an interface the dream and the
  collection-iteration work both read.
- Confidence fields land on five artifact types in one deliberate change.
- Every brain must adopt milestones. **None has them today**, and no milestone tree exists
  anywhere. Brains are users, not owners: they conform.
- The sequencing is core → skill packaging → brains. Brains do not package during core's
  work.

---

## Alternatives considered

1. **Presence-in-the-taught-store as the stopping rule.** Rejected — it would have to
   change when ALS lands. A threshold comparison against a stored value is additive.
2. **Confidence on the pipeline node.** Rejected — confidence is relational; the same
   pipeline is right for one task and useless for another.
3. **One global threshold.** Rejected — a hint you are 80% sure of and a plan you are 80%
   sure of are not comparable.
4. **`decompose` returning whole candidate breakdowns.** Rejected — combinatorial. One
   layer at a time, recursing only where confidence is missing.
5. **Splitting `decompose` into a generator capacity and a chooser capacity.** Partially
   accepted: the *split* is real (`planning.*` vs `decision.*`), but decomposition stays
   one capacity that generates, with selection as its own decision capacity.
6. **Keeping the v0 placeholders as test fixtures.** Rejected — they are how the
   placeholders came to be mistaken for the plan. The reference bundle replaces them.
7. **Deriving sequence/parallel from graph topology.** Rejected — path-reachability is not
   the pipeline chosen. The execution tree is an output of the loop.

---

## Amendments

### amendment-1 (2026-07-31, CORE-C2 pre-build read-through) — §1's milestone is corrected

**Amendment status:** Accepted. §1's correction is agreed and is not among the
contradicted sections; it is built by the milestone-level item (CORE-C2R5).

**Trigger.** The CORE-C2 chat read this ADR against ADR-0205 and against the code before
building the milestone level. §1 makes three statements that do not survive.

**1. A milestone is not a DataState.** §1 says *"A milestone is a DataState the system
already knows about…"*. ADR-0205 §1 places the milestone level **above** pipelines, and a
DataState is a **member** of pipelines. Under both statements the same node sits above and
below the pipeline level, and "verified by the level below" contains a cycle.

**Amended:** a milestone is a **node at the milestone level**. It is neither a DataState nor a
chain artifact. It **references** the DataState it targets and **composes** the pipelines that
reach it — two distinct links to two distinct objects, which §1 collapsed into one sentence.
§1's prohibition on milestones becoming nodes in the capacity graph is preserved and now
holds structurally: the milestone level is its own graph (ADR-0205 §2, the *inter*graph
primitive), so the capacity graph keeps exactly the bipartite topology the finder walks.

**2. "Needs no new declaration type" is wrong as stated — and must not be corrected toward
"a new declaration type".** A declaration is what a capacity or DataState has: a registry
entry with a field schema. Wording the correction that way rebuilds ADR-0205's rejected
Alternative 2 (*"a separate registry per level"*). **What makes a node a milestone is the link
it anchors, not a declared type.** Its node is thin — an identity and a target link; all
structure is links.

**3. Membership is one link per pipeline, not one link over all coincident pipelines.** §1
says *"its compositional members **are** the pipelines it is coincident in"* — plural, one
link. Two things forbid that:

- ADR-0205 §2: every member of a compositional link is **necessary**. Coincident pipelines are
  **alternative routes** to the milestone; a single many-member link would make every one of
  them required, so removing any one would destroy the milestone.
- ADR-0205 §3 already states the correct form: alternatives are **several compositional links
  sharing an anchor**. Combined with the compositional-immutability rule (members frozen),
  this is also the only way membership can grow — a milestone that later gains a pipeline
  gains a **new link on the same anchor**.

**Amended:** one compositional link per pipeline reaching the milestone. Frozen members and
growing membership are then the same mechanism, not two.

**Which primitive** (ADR-0205 §amendment-1.2, reconciled at `2c56246`): each of those links
has **exactly one member**, and `add_intergraph_hyperedge` refuses 1-anchor/1-member. So a
milestone→pipeline link is an **`IntergraphEdge` with `compositional=True`**, not a
hyperedge — same semantics, same `_compositional` persistence, selected by member count.
The hyperedge carries the many-member cases (a pipeline's ordered steps, a plan's set of
milestones). Convention: **source = anchor, target = member**.

**4. Hub-ness is a discovery method, not the definition.** §1's *"appearing in multiple
pipelines"* threshold (two or more) describes how **discovery** finds candidates. A **taught**
milestone — which §1 already permits — needs **one** pipeline beneath it, per the rule that a
declared level requires the level below. A validator written from §1 alone would reject every
taught milestone.

**5. Taught milestones are structural change outside a Skill.** ADR-0205 §7 restricts
structural change to Skill install. Until the skill-packaging system can declare milestone
content, a **temporary exception** is granted, recorded in the shim register of
`CORE_RECONCILIATION_PLAN.md` §9 with *the skill-packaging system* as its named replacement.
This is not optional slack: `promoted-pipelines` has no writer, so there are zero Global
pipelines and discovery will return nothing for the foreseeable future. **The taught path is
the primary path, not a stopgap**, and is a write capacity (precedent: `learn_parameter`),
not a CLI verb.

**Consumers:** the milestone-level item of CORE-C2, and every brain adopting milestones.
