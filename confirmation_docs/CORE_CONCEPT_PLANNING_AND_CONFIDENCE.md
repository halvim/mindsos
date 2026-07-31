# CORE CONCEPT — Milestones, Decomposition, and Confidence

**Status:** CONVERGED IN DISCUSSION, NOT BUILT, NOT AN ADR YET.
**Filed:** 2026-07-31, core reconciliation chat (`feat/core-c1`).
**Verified against:** `origin/main` `fafc679`.
**Nothing here is shipped.** Every mechanism below is either absent, or present as a
placeholder that returns a constant.

---

## 0. Why this document exists

MindsOS has a six-phase lifecycle that runs, and a reasoning chain it writes down. What
it does **not** have is the thing that makes planning mean anything: a way to say *how
sure am I*, and a way to act on the answer. Everything below is that missing half.

The purpose is not to compute a number. It is to **use what the system is confident
about to raise the chance of success on what it isn't.** A low-confidence answer is not
a small number — it is an answer that is probably wrong.

---

## 0.5 ABSTRACTION LEVELS — the governing idea

**Everything below is one graph seen at different resolutions.** There is a single L3
graph of capacities and DataStates. Every other structure the system reasons with —
pipelines, milestones, plans, request knowledge — is an **abstraction level** built from
the nodes of the layer beneath it.

> **Terminology: "abstraction level".** MindsOS already uses "layer" for L0–L5 and "tier"
> for `TierEnum` priorities, so neither is available. **"Level" is correct and is already
> in the code**: `BlameVerdict.chain_level` takes the values
> `hint | map | plan | plan_subtree | pipeline` — that is this ladder, already named, and
> Phase 6 already attributes blame by descending it. The so-called "6-level chain of
> artifacts" is not a competing concept; it is this same ladder seen per-request.
> Write **abstraction level**, and name them: *capacity level*, *pipeline level*,
> *milestone level*, *plan level*, *request level*.

| Abstraction | Composed of | Verified by |
|---|---|---|
| request | plans | its plan |
| plan | milestones | its milestones and their pipelines |
| milestone | pipelines (a hub is their intersection) | the pipelines it is coincident in |
| pipeline | capacities and DataStates | its capacities and DataStates |
| capacity | — the ground truth | — |

### 0.5.1 It is literally a metagraph

The layer above is **composed of nodes of the layer below**, and core already ships the
primitive: `IntergraphHyperEdge` (Phase 05c) has an **anchors** side (identity-bearing —
"the cat in cat = c + a + t") and a **members** side (the constituents), works across
graphs, and carries a **`compositional`** flag that makes the composition identity-bearing
and immutable. `CompositionalMetaEdge` was dropped in favour of exactly this flag.

So a Pipeline node anchors a compositional hyperedge over its capacity and DataState
members; a Milestone anchors one over the pipelines it is a hub of; a Plan over its
milestones; request knowledge over its plans.

**What a compositional edge means:** *what it points to is formed by what it points from.*
Every member is **necessary** — remove any one and the anchor no longer exists. If A is
formed by A1, A2 and A3, then A is gone without any single A(i), regardless of order.

**Order is separate from necessity.** Some compositions are ordered (a sequence of
dependent milestones, or `cat = c+a+t` where `cat ≠ act`); some are not (parallel
milestones, where all are required but sequence is meaningless). Both must be expressible.
Today the factory refuses `compositional=True` with `ordered=False` (P8-A), on the
rationale that "set semantics is incompatible" with identity-bearing composition. That
conflates *identity-bearing* with *sequence-bearing* and needs amending — see §8 Q11.

**AND and OR are both carried by the structure — no labelling, no new edge type.**

- **Within one composition: always AND.** Every member is necessary; that is what
  `compositional` means. There is no OR *inside* a breakdown.
- **Between compositions sharing an anchor: OR.** Two different ways to reach the same
  milestone are **two compositional hyperedges anchored on the same node**. Nothing forbids
  that — edge identity is per-edge — so alternatives need no new relation. They are simply
  more than one way to compose the same thing.
- **Sequence vs parallel, within an AND set:** read from the chosen pipelines' data flow —
  if B's pipeline consumes A's output they are sequential, otherwise parallel. This is an
  **output** of the planning loop, not an input (§1a).

⟹ Nothing has to *label* anything, and the deterministic/judgement split holds exactly:
`planning.decompose` **emits** candidate compositions (deterministic — the structure says
what they are); `decision.select_decomposition` **picks one** (judgement).

### 0.5.1a The chain artifacts are the per-request view of the same ladder

`chain_artifacts.py` writes nine artifact types into intelligence-MM per request:
`HintSet → MappingResult → Plan(+Milestone tree) → Pipeline → PipelineRun → RequestRun`,
plus `ReplanRecord` and `StepExecutionRecord`.

These are **not a competing hierarchy.** They are the per-request *trace* across the
abstraction levels, plus execution records:

| Chain artifact | Abstraction level | Kind |
|---|---|---|
| `HintSet` | evidence for the request level | trace |
| `MappingResult` | request level — carries `selected_request_pattern_iri` + `mapping_confidence` | trace |
| `Plan`, `Milestone` | plan and milestone levels | trace |
| `Pipeline` | pipeline level — holds only `plan_ref` + `milestone_ref`, already a pointer, not a copy | trace |
| `StepExecutionRecord` | capacity level — **already has a `confidence` field** | trace |
| `PipelineRun`, `RequestRun`, `ReplanRecord` | — | execution / provenance |

Two things already exist that the model needs: `MappingResult` carries the
(request, request-knowledge) pairing **with its confidence** — relational confidence, on
the artifact representing the pairing, exactly as §5.0 requires. And
`StepExecutionRecord.confidence` is a per-step confidence slot.

⟹ The chain should **reference** the durable knowledge nodes, never duplicate them. Where
it duplicates today (`PlanResult` vs the Milestone tree) is a defect, not a design.

### 0.5.2 How the system reasons — lazy descent

The Mental Model loads the **highest abstraction** and analyses it. If it cannot find what
it needs, it loads the next abstraction down **only for the nodes it needs**, and rechecks.
It keeps descending until it has enough to understand what it is doing.

That descent **is** the planning loop (§1a), and decomposition **is** dropping an
abstraction. Confidence is what decides whether to descend.

### 0.5.3 Consequences

- **No structural blobs.** A structure stored opaquely cannot be verified by the layer
  below, so it breaks the model. This rules out `LearnedPipeline.value` holding a pipeline
  as an opaque `Pipeline.to_dict()` payload. *(Opaque **values** — a numpy array on a
  DataState — are data, not structure, and are unaffected.)*
- **Milestones sit above pipelines, and that is a dependency, not a preference.** You
  cannot discover a hub without pipelines to intersect. A system with no pipelines has only
  *taught* milestones.
- **Every layer's claim is checkable**, which is also how stale knowledge is repaired when
  the graph changes underneath it.
- **Every ADR must be re-read against this.** Any decision that stores a higher-abstraction
  structure opaquely, or duplicates it outside the graph, contradicts the model and needs
  correcting. Known instances so far: ADR-0203 (opaque pipeline blob), `PlanResult` vs the
  Milestone tree, `Milestone.parent_ref`/`children_refs` as properties, `relevant_hints` /
  `paired_pipelines` as IRI-list properties.

### 0.5.3a Structure is stable; learning moves confidence

Two different kinds of change happen, with different triggers and different meanings:

- **Confidence change** — the structure is untouched; only how *appropriate* it is has
  moved. This is what learning normally produces, and it happens constantly.
- **Structural change** — a node or composition appears or disappears. This is **not**
  drift; it is a deliberate act, and its unit is the **Skill**.

**A Skill is not a group of capacities.** It is everything the system needs across *all
abstraction levels* to serve a class of requests: capacities, pipelines, milestones, plans
and request knowledge. Installing one adds the whole vertical; uninstalling one removes the
whole vertical. Losing the ability to serve those requests is the **intended** consequence,
not a failure — and because the vertical goes together, nothing is left pointing at
something that no longer exists.

A milestone is a hub of several pipelines, so within a skill it is **stable by
construction**: for it to disappear, several proven pipelines would have to change at once,
and a proven pipeline has no reason to change.

**Uninstall keeps the user's data, by the user's choice.** Removing a Skill removes the
vertical the Skill shipped. It does **not** silently destroy what the user accumulated on
top of it — learned parameters, taught pipelines, discovered request knowledge. The user
decides. *Like deleting a game from disk and keeping the saved games.*

Two kinds of leftover, and they behave differently:

- **Data** (learned parameters, a taught appliance library) — meaningful on its own.
  Keep it.
- **Structure** (a taught pipeline referencing capacities the Skill took away) —
  meaningless while the Skill is gone, valuable again the moment it is reinstalled. Keep
  it too, but **dormant**: retained, not silently treated as usable.

On-read verification (§0.5.3b) is what enforces the difference — a dormant structure fails
verification against the capacity level and is not offered, without anyone having to delete
it. Reinstalling the Skill revives it.

Uninstall is therefore a **user choice with a least-destructive default**: remove the
Skill, keep what the user built.

**Replacement, not decay.** When a pipeline becomes less appropriate, another takes its
place; when a milestone becomes less appropriate, another takes its place; request
knowledge is updated to point at whatever is currently best. So a milestone ceasing to be
pointed at has nothing to do with it ceasing to be a hub — the two are independent.

One condition on that: when **nothing** clears the threshold, request knowledge must record
*that* rather than keep pointing confidently at the least-bad option. That is the
"I'm not sure" path (§6), and it is what stops replacement from degrading into a stale
pointer. And replacement is a **mechanism to be built** (the writer, plus ALS) — not an
emergent property.

### 0.5.3b Learning includes verification

**Learning something new is a comparison of the current state against the previous one.**
Verification is therefore not a separate maintenance job — it is part of learning. When the
system learns, it must check how what it learned affects what it already knows, and the
output is both new nodes *and* confidence deltas on existing links. Learning that
contradicts existing knowledge lowers a confidence; it does not merely add.

This is the same mechanism as "verified by the level below" (§0.5). Three plausible times
to run it, and the choice is open (§8 Q13):

- **on read** — verify an abstraction against the level below when it is loaded. Natural
  under lazy descent, and pays only for what is used.
- **on learn** — eager, graph-wide recheck. Correct but potentially expensive.
- **at dream time** — batch sweep. The dream's existing job, and where a full pass belongs.

### 0.5.4 Realm, not tags

**Global is what the system ships by default**, decided by a human admin. **Local is
everything that differs from the default.** Admins promote a Local element to Global.

⟹ **Any Global element is promoted by definition; no `promoted` tag is needed.** Realm
carries approval. Tags carry provenance only (taught / discovered).

*Future work, recorded here:* admins need an **auditing and promotion system** to track
system versions and changes.

---

## 1. The chain

```
request → hints → mapping → milestone set → plan → decomposition → pipelines → capacities
```

Each arrow is a transformation, and each carries a confidence (§5).

- A **request** is what the user asks for. Requests do not match patterns.
- A request **contains hints**. Hints *are* patterns, and hints are what get matched.
- **Mapping** matches hints to a **milestone set**.
- A **plan** is the milestone set arranged into a DAG.
- **Decomposition** inserts more milestones where confidence is missing.
- At the bottom, every piece is a **pipeline** the system trusts, and the floor of any
  pipeline is a **capacity**.

---

## 1a. Planning is a loop

The four steps are **request → hint → map → plan**, but *plan* is not a single step. It
is a loop:

```
search → find → decompose → (repeat)
```

- **Map** produces the **milestone tree**.
- For each milestone, the loop first **searches** L2 for a pipeline the system already
  knows from the current state to that milestone's DataState.
- If it does not know one, it **finds** one in the graph.
- It checks its confidence — its *experience* that it can get there.
- Where confidence is too low, it **decomposes** that branch and repeats on the smaller
  pieces.

**There is no "failed find."** If no path exists in the graph, the system *doesn't know* —
a true analysis result, not an error. (Core has already ratified this: the pending design
`pipelinenotfound-to-dontknow` states *"`PipelineNotFoundError` 'shouldn't exist' — a
single capacity IS a 1-step pipeline, so 'no route' is not a technical failure but an
honest dont-know."*)

When the loop settles, the outputs are a **formulated plan** and an **execution tree** —
which milestones are parallel and which are dependent.

Two consequences worth stating:

- **Decomposition is the repair step inside the loop**, not the thing that builds the
  plan. The tree comes from map; decompose refines the branches that fall short.
- **The execution tree is an output, not an input.** Dependency is read from the pipelines
  actually chosen — if milestone B's pipeline consumes milestone A's output they are
  dependent, otherwise parallel. It is not guessed from graph topology.

---

## 2. What a milestone is

**A milestone is a DataState the system already knows about — one it can recognise and
reason with — which it does not currently hold, and which lies between where it is and
where it needs to go.**

It must be *known*: you cannot aim at something that is not in the graph. "Does not have"
refers to the current run's state, not to the DataState's existence.

Not a transformation, not a stage, not a name. A specific node in the graph.

Two halves, and conflating them causes confusion:

| Half | What it is | Lifetime | Where |
|---|---|---|---|
| the target | `ds:fried_egg` — a DataState | durable, shared | capacity graph |
| the instance | "for request 42, reach `ds:fried_egg`, pending, 1 replan" | per-request | `chain` graph in intelligence-MM |

So a milestone needs **no new declaration type**. It is a reference to an existing
DataState plus per-request bookkeeping. Milestones must never become nodes in the
capacity graph: same shape as a capacity, different lifetime and scope.

### 2.1 How milestones are discovered — hubs

**A DataState that appears in multiple pipelines is a milestone.** Pipelines are
sequences of capacities and DataStates in the L3 graph, so a coincident DataState across
two or more pipelines — taught or found — is a hub.

Refinement: a hub you **already have** is not a milestone. At the start of an ARC task
you are holding a grid, so "reach a grid" is nothing; "reach an *understood* grid" is the
waypoint. Hub-ness produces candidates; subtracting the current state turns candidates
into milestones. The useful hub is one that **lies between where you are and where you
need to be, and narrows what remains.**

**Measurement, v1:** the capacity graph (connectivity in the registered topology).
**As the system learns:** coincident DataStates across taught and found pipelines — a
calculation the system performs incrementally as it learns new pipelines.

### 2.2 Taught or discovered

Milestones arrive two ways, and both are first-class:

- **Taught** — we name a DataState as a milestone, possibly as a property on the DataState
  node.
- **Discovered** — the system computes hubs and proposes them.

The same is true of decompositions (`SubgoalTemplate`s) and of pipelines. Everything the
system knows is either taught by us or discovered by it.

### 2.3 Tree vocabulary

The plan is a **tree** of milestones, and the words matter because three different
relations get called "the plan":

- **layer** — one level of the tree. Each layer is a more detailed version of the layer
  above and a more concise version of the layer below.
- **branch** — a milestone together with everything beneath it. Decomposition operates on
  one branch at a time.
- **children** — the milestones one layer down from a parent, produced by decomposing it.
- **siblings** — children of the same parent. Siblings are where dependency lives:
  sequence, parallel or alternative (§3).
- **leaf** — a milestone that is not decomposed, because a pipeline reaching it cleared
  the bar.

Decomposition grows the tree **downward, one branch at a time, only where confidence is
missing.** Sibling branches are independent: some get decomposed, others stop at the first
layer.

---

## 3. What a plan is

**A plan is a DAG of milestones.** Not a list. An edge means "must complete before";
no edge means order is free. Sequential and parallel are not two kinds of plan — they are
the presence or absence of an edge.

This is the same structure as a Pipeline one layer down (a DAG of capacity steps). Same
structure, different granularity. A plan *is* a pipeline of milestones.

**Two distinct relations, and both are needed:**

- **parent → child** = *decomposition*. "This milestone is reached via these sub-milestones."
- **sibling → sibling** = *dependency*. "This one must finish before that one starts."

**Three sibling kinds:**

| Kind | Meaning | Order | Confidence |
|---|---|---|---|
| sequence | B consumes A's output | binding | product (chain rule) |
| parallel | independent, both required | free | product (independence) |
| alternative | either one reaches the milestone | n/a — pick one | max |

**AND/OR is deterministic and belongs to planning, not to judgement.** Two milestones
are *dependent* if they lie on the same path, and *independent* if they lie on separate
paths. This is readable from graph topology before any pipeline is chosen. It is the
thread mechanism: a plan is like code with multiple threads — for parallel milestones
order does not matter; for sequential milestones order matters absolutely.

---

## 4. What decomposition is

> **I'm confident in my plan if I'm confident in the sub-plans that achieve its
> milestones. Decomposition is what I do when I'm not confident: break the plan into
> parts I am confident about, and if all the parts clear the bar, my confidence in the
> whole plan goes up. Composition across milestones is what turns part-confidence into
> plan-confidence.**

Decomposition **is** breaking work into pieces. It produces a tree in which each layer
is a more detailed version of the layer above and a more concise version of the layer
below. The *mechanism* for producing a layer is finding waypoints.

### 4.1 It emits one layer at a time

`decompose` returns **one layer** of candidate waypoints for **one** milestone. Each
resulting sibling is then evaluated independently:

- sibling has a trusted pipeline → that piece is done, do not decompose it
- sibling does not → decompose that sibling

So the tree grows exactly where confidence is missing. There is no combinatorial
explosion, because whole breakdowns are never enumerated — only the next layer of
waypoints, per milestone.

### 4.2 It makes confidence computable, not success likelier

An unresolved pipeline has no confidence at all. Not low — **unknown**. Inserting
waypoints until every hop is a pipeline the system knows replaces an unknown with a
product of knowns. That is why decomposing raises confidence.

**And that is why you stop at the first pipeline clearing the bar.** Once a hop has a
number, decomposing it further only multiplies more factors in and lowers it. So:
decompose while confidence is unknown; stop the moment it is known and above threshold.
**Never decompose something you already trust.**

### 4.3 Termination is guaranteed

A capacity is a DataState transformation that works 100% of the time, by definition — a
one-step pipeline at confidence 1.0. Worst case, decomposition reaches bare capacities.
So **a breakdown is always possible.**

### 4.4 Two capacities, not one

Generating and choosing are different actions and belong to different families.

| | `planning.decompose` | `decision.select_decomposition` |
|---|---|---|
| returns | candidate waypoints for one layer | one breakdown, or "not sure" |
| deterministic? | **yes** — same graph + state + taught set ⟹ same candidates | **no** — reads confidences ALS will move |
| family | `planning.*` (structural) | `decision.*` (judgement) |
| brain-shadowable? | should not need to be | yes — this is where a brain's policy lives |

Determinism holds **per snapshot**, not across time: the graph, the current state and the
taught set all change as the system learns. Plans are therefore not reproducible across
sessions — which is already what the dream subsystem assumes.

### 4.5 Worked example — egg sandwich

Goal `ds:egg_sandwich`. Current state: egg, bread, pan, stove.

**Today:** `planning.decompose` returns `[]`. Everything is a leaf. One milestone, one
pipeline. No pipeline ⟹ "don't know."

**Under this model:** decompose emits candidate waypoints — `fried_egg`, `scrambled_egg`,
`boiled_egg`, `toast`. The chooser assembles a breakdown: `{fried_egg, bread}`, which are
independent of each other (parallel), then both feed the sandwich (sequence). `bread` is
already held, so it is not a milestone. Is there a trusted pipeline to `fried_egg`? If
yes, done. If no, decompose `fried_egg` → `{hot_pan, cracked_egg}` and recurse.

### 4.6 Worked example — ARC

Goal `arc.output_grid`. Current state `arc.raw_task`.

**Today:** `[]`, then a single `find_pipeline` from raw_task to output_grid, which finds
nothing.

**Under this model:** top layer `{profiling, comparisons}`; second layer beneath profiling
`{grid_understanding, …}`. Where a taught pipeline exists, stop. Where it does not,
recurse.

**Note:** ARC has no milestone DataStates today, and no milestone tree exists anywhere.
This is a new concept every brain will have to adopt.

---

## 5. Confidence

### 5.0 What confidence measures

**Everything in the system is deterministic, at every abstraction.** A capacity always
performs the same transformation; a pipeline is composed of capacities, so it too solves
what it solves 100% of the time; and the same holds all the way up, because every
abstraction is composed of deterministic pieces beneath it.

**What is uncertain is whether the thing a pipeline reliably produces is what task T
needs.**

> The pipeline solves *something* 100% of the time. Is that *something* needed to solve
> task T? That is the confidence.

So confidence is not a property of the mechanism. It is **the system's estimate that what
this deterministic piece achieves can be used to solve this task.** And that is precisely
why a task is decomposed: keep breaking it down until the system finds pieces it is
confident are the right pieces.

**Confidence is therefore relational, not intrinsic.** It is a property of a *pairing* —
(this pipeline, this milestone) or (this plan, this request) — never of a pipeline alone.
The same pipeline can be exactly right for one task and useless for another.

⟹ **Confidence belongs on the edge, not the node.** A pipeline node carries *evidence*
(`n_runs`, `outcome_history`); the confidence that it serves a given request kind belongs
on the link between them. This is the same conclusion §5.3 reaches from a different
direction.

A capacity is 1.0 at the floor because asking for its target DataState *is* asking for
exactly what it does — the pairing is degenerate, so there is no gap.

Confidence is **learned by doing** — an internal reinforcement, distinct from the AI
industry's reinforcement learning. ALS is the mechanism that will move these values from
observed outcomes.

### 5.1 Values and thresholds

- **All confidence values are 1.0** for now. Taught pipelines are taught by us, and
  capacities are 1.0 by definition. ALS will move these values later; nothing in the
  mechanism changes when it does.
- **All thresholds are 0.8** for now, but they are **per transition**, not one global
  number.

**They are separate values that happen to share a number.** A hint you are 80% sure of
and a plan you are 80% sure of are not comparable quantities. Collapsing the six
thresholds into one constant is a defect, not a simplification.

> **Note for future chats:** you will find several constants all equal to 0.8 compared
> against several values all equal to 1.0, and it will look like dead code. It is not.
> The structure exists so ALS can move each value independently. Do not simplify it.

### 5.2 Which transitions carry a confidence

| Transition | Question | Exists today? |
|---|---|---|
| request → hints | how sure am I these are the hints? | **no** |
| hints → milestone set | how sure am I these hints map to these milestones? | `mapping_confidence` maps hints to a *pattern*, not milestones |
| milestone set → plan | how sure am I this milestone set is the **appropriate** plan? (appropriate = sufficient, enough, correct) | `RequestPattern.confidence` may be this — unverified |
| milestone → pipeline | how sure am I this pipeline reaches this DataState? | **no** |
| plan → outcome | composed from the above | **no** |

Every layer of the tree **validates** appropriateness — actively confirming and producing
a confidence, not passing or failing a gate.

### 5.3 Where confidence lives

**On the edges, not on the milestone.** A milestone is a DataState; it has no confidence
of its own. What carries confidence is the *claim*: that this breakdown is appropriate,
and that this pipeline reaches that DataState.

For a taught pipeline, confidence must be a **metadata** field, not content. The
`learned-pipelines` role uses `immutable_successor`, which freezes content fields; ALS
must be able to update the value in place.

**ADR-0094 is not reopened.** It moved confidence *ownership* to ALS. A field ALS writes
is consistent with that.

### 5.4 Composition

`P(plan) = P(the breakdown is appropriate) × ∏ P(reach each milestone)`

Sequential siblings compose by the chain rule; parallel siblings by independence — the
same product, different justification, which will matter once ALS measures them.
Alternatives take the max.

---

## 6. "I'm not sure" is not "I don't know"

A breakdown is always possible (§4.3). So the failure mode is never *"no breakdown
exists."* It is *"I could not find a breakdown I am confident about."*

That is **"I'm not sure."** Specifically: low confidence on the **milestone set → plan**
transition — how sure the system is that this milestone set is the proper plan.

- **Externally** it is answered as "I don't know."
- **Internally** it flags the request as something to verify with the dream, so the
  system can become sure.

This turns uncertainty from a dead end into work for the dream subsystem.

---

## 6a. `request_knowledge` — the shortcut store

**A recorded solution for a kind of request, so the system does not rediscover it through
request → hint → map → plan every time.**

This is the shipped `request_patterns` role, whose name is wrong under this model. It does
not hold a *pattern*; it holds what the system knows about a kind of request. Proposed
name: **`request_knowledge`**.

**It should reference hints, maps, plans, milestones and pipelines — and own none of
them.** Each is its own knowledge node in L2, linked to the `request_knowledge` node. A
map, a plan or a milestone can then be shared across many request kinds. "I know this map,
and this map is linked to this request kind" — not "this request kind owns this map."

This is the same normalisation defect found twice elsewhere: `relevant_hints` and
`paired_pipelines` are already *references* (IRI lists), but stored as **properties**
rather than edges, so nothing can walk them. See findings §11.6.

**Scope.** `request_patterns` is already **dual-scope** by design (ADR-0150 §am-8):
per-user knowledge is authored or learned **Local**, and an admin promotes it to the
shared **Global** form. That is exactly the intended lifecycle — discovered or taught
Local, approved to Global.

**Pipelines.** `paired_pipelines` is the pattern→pipeline binding and is the declared
source of truth. It should carry a learned/discovered/promoted tag — and the shipped
`Pipeline` schema already has one: a `status` metadata field with a 5-state lifecycle,
alongside `n_runs` and `outcome_history` (the evidence ALS would consume). Unifying the
two pipeline stores is therefore possible but reopens ADR-0203 — see §8 Q8.

---

## 7. Everything already has a storage home

| Thing | Where | Status |
|---|---|---|
| milestone targets | DataStates, capacity graph | shipped, in use |
| durable decompositions | `request_patterns` — `RequestPattern`, `SubgoalTemplate`, `DECOMPOSES_INTO`, `PREREQUISITE_OF`, `confidence` | **shipped, zero writers** |
| per-request instances | `Milestone` in the `chain` graph | shipped, in use |
| taught pipelines | `learned-pipelines` role | shipped, **no runtime reader** |

**Nothing new needs designing at the storage layer.** What is missing is writers,
readers, and the confidence wiring. `request_patterns` has sat unused since Phase 13
because decomposition has never run — it is the decomposition store.

`SubgoalTemplate` is a taught decomposition: a milestone set with an appropriateness
confidence. Subgoals can be taught, and later learned by the system.

---

## 8. Open questions

| # | Question |
|---|---|
| **Q1** | Where does the AND/OR determination live? It is deterministic and belongs to planning, but the exact placement is undecided. |
| **Q2** | Does `planning.decompose` emit unlabelled waypoints, leaving the chooser to assemble the AND/OR arrangement — or does decompose label them? (Related to Q1.) |
| **Q3** | Does the `Milestone` tree become the single plan representation, with `PlanResult` reduced to refs into it? Today they are two descriptions of the same plan. |
| **Q5** | Where is the incremental hub index maintained, and what updates it on each teach? |
| **Q6** | Does the "not sure" flag live on the Episode, and how does dream's candidate selection learn about it? `dream.retry` fires only on *failed* episodes today; completed-while-unsure is a third category that does not exist. |
| **Q7** | Every brain lacks a milestone *tree*. ARC does have 60 single-dot DataStates including `arc.profile`, `arc.task`, `arc.rules` — so candidates exist. Who declares which are milestones, and against what criteria? |
| **Q8** | Retire `learned-pipelines` and unify on one pipeline store with a `status` tag? ADR-0203 rejected this because the normalised `HAS_STEP` shape was "in flux pending D38". **D38 was settled by ADR-0156 (bipartite, not hyperedges).** What remains open is narrower: the *graph form of `input_group`* as a typed hyperedge. Settling that also removes the finder's declaration-registry read. |
| **Q9** | ~~The renames.~~ **Answered:** `request_patterns` → **`request_knowledge`**; the unified pipeline store → **`pipelines`**. Execute once, bundled with the schema change that adds the fields. |
| **Q10** | The **writer**. Nothing writes to `request_patterns` today. Recording a discovered solution back into it is the learning loop, and it is a larger item than the read side. |
| **Q11** | Amend P8-A so `compositional=True` is permitted with `ordered=False`. The current refusal conflates identity-bearing with sequence-bearing; a set-composed identity ("this plan **is** these three milestones") is coherent. Note `ordered` lives on the `IntergraphHyperEdgeType`, not the instance, and its only real effect is factory dedup — harmless for genuine sets. |
| **Q13** | When does verification run — on read, on learn, or at dream time? (§0.5.3b) |
| **Q15** | Uninstall's data policy: default to keeping the user's data and dormant structure, with an explicit opt-in to remove it. Where is the choice surfaced, and what marks a structure dormant? |
| **Q16** | If a brain is a **user**, its runtime `register_capacity` shadows (arc's `arc_plan.py`, `arc_sufficient.py`) are structural change outside a Skill. Do brains package as Skills, and does `register_capacity` stop being a runtime surface? |
| **Q14** | **A Skill spans all abstraction levels**, so uninstalling one removes the whole vertical — capacities, pipelines, milestones, plans and request knowledge together. Losing the ability to serve those requests is the *intended* effect, not a defect, and nothing is left dangling. The shipped driver already has a reverse-dependency uninstall guard (`SkillUninstallRefusedError`). **Residual question:** does that guard cover *Local* knowledge taught on top of a skill — a user-taught pipeline built from skill X's capacities is not part of X's bundle. Verify. |

---

## 9. Things this concept retires

- **`MAX_DEPTH = 3`** in `plan_construction.py` — a brain's test artifact, not a design.
  Replaced by the confidence stopping rule.
- **`Milestone.sequence_index`** — a flat integer that can order siblings but cannot say
  two are independent. Replaced by dependency edges.
- **Topology stored in properties.** `parent_ref` / `children_refs` are node properties,
  so the plan tree cannot be walked as a graph. Replaced by real edges.
