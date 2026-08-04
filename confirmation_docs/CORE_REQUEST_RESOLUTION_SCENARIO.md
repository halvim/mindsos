# Request Resolution — the owner's scenario

**Filed:** 2026-08-02. **Status:** owner-stated, restated here for agreement.
**This document is the source of truth for the discussion it governs.** Where it
conflicts with ADR-0206, the ADR changes — see §8.
**Reads with:** `CORE_CAPACITY_GRAPH_TRAVERSAL.md` (the walk this scenario calls),
ADR-0205, ADR-0206.

> Written because the owner has explained this several times. Restate against this
> file, not from memory.

---

## 1. Name

`request → hints → map → plan` is a **system pipeline** — a pipeline one
abstraction level above the L3 pipelines it produces. It is called **Resolution**.
The map's second confidence (§4) is therefore named **targeting**, not
"resolution"; the **resolution-set** keeps its name, being what Resolution
produces.

---

## 2. Request

A request is the input to the system. Everything below transforms it until it is
executable.

---

## 3. Hints

**Hints are small clues found in the request that indicate which tasks are
involved in solving it.**

**Hints are a graph in L2.** Nodes in other L2 graphs point at hint nodes, and
those links are what tell the system how to resolve a hint out of a request.
After the `request → hints` step, the L4 resolution system holds the extracted
**hint set** in **L5**.

Two confidences on `request → hints`:

| # | confidence | asks |
|---|---|---|
| 1 | **extraction** | did I find *all* the hints the request contains? |
| 2 | **appropriateness** | are the hints I found *useful* for solving this request? |

---

## 4. Map

**The map is a dictionary the system builds from the hint set.** It *contains* the
`hints → tasks` resolution; it is not that mapping alone. It holds:

1. every **task** resolved from the hint set;
2. each task's **final DataStates**;
3. the **current system state** — the DataState instances already loaded in L5.

Three confidences:

| # | confidence | asks |
|---|---|---|
| 1 | **task extraction** | did I find all tasks present in the hint set? |
| 2 | **targeting** | is this the right final DataState for this task? |
| 3 | **appropriateness** | is this task set useful for solving the request? |

The **resolution-set** is the set of final DataStates, one per task.

---

## 5. Plan

**The plan is the strategy for getting from the current system state — the known
DataStates loaded in L5 — to each task's final DataStates.** Planning is a loop of
three steps.

Its three subjects:

- **milestone** — a specific DataState in the L3 graph.
- **pipeline** — a possible path in the L3 graph.
- **decompose** — the step that finds further milestones.

### 5.1 Milestone tree

Produce the **milestone tree**: what the system must reach in order to arrive at a
final DataState for each task.

**On the first pass of the loop, the first tier of the tree is the resolution-set**
from the map.

Two relations:

- **dependent — parent/child.** The child must be reached before its parent.
- **independent — siblings.**

**Independence is not decided here.** It is a property of the pipelines, and no
pipeline exists yet at this step — see §5.3. Listing the tree establishes the
parent/child relation only.

One confidence:

| confidence | asks |
|---|---|
| **appropriateness** | is this milestone the right one to reach first, before getting to the final milestone? |

**Appropriateness is a child-to-parent measure**, not a property of a milestone on
its own: *how likely is the system to reach the parent, given it reaches this child
first?* Two children of the same parent are ranked against each other — for the
parent *throw a ball*, the child *ball in hand* scores higher than the child
*find a ball*.

### 5.2 Find the pipelines

Find the pipeline reaching each milestone. Execution order follows the tree:
**ordered** for dependent milestones — child pipeline before parent pipeline — and
**parallel** for independent ones.

On the first pass the system determines (a) the relationships among the current
milestone set (the resolution-set) and (b) the pipelines needed to reach them.

Pipelines are found by **CGT** (`CORE_CAPACITY_GRAPH_TRAVERSAL.md`). Its start set
is the **current system state** — the DataStates loaded in L5 — and its target is
the milestone.

Before searching, the system consults the **Known_Pipelines** store (L2) for a
pipeline matching the `current system state → milestone` combination, **children
before parents**.

**Known pipelines are pipelines that have previously been used successfully.**

**Pipelines carry no confidence.** They are deterministic, so it would always be
1.0.

### 5.3 Relate

Independence, overlappability and order are all read here, from the pipelines
found in §5.2. Nothing is declared in advance, so a mis-split cannot be produced.

**Independence — structural.** Two branches are independent when the subgraphs of
their self-sufficient pipelines are **disjoint**: sharing neither a DataState nor a
capacity. Branches that share a node are not independent; they are one branch that
was mis-split.

**Overlappability — temporal, and a different question.** Two pipelines that share
a resource are *not independent*, yet may still run overlapped if they do not need
that resource at the same time. Boiling holds the stove without holding the agent,
so searching for the tea bag overlaps it. Independence and overlappability are two
relations; one word must not decide both.

**Order** falls out of the two: dependency where a child feeds a parent, sequence
where an exclusive resource is contended, overlap everywhere else.

### 5.3a Resources — a separate axis

**Resources are not DataStates and do not enter the graph CGT searches.** The walk
answers *can it be done*; a resource constrains *when*. No plan is impossible
because of the hand — only slower. Putting resources in the searched graph turns a
timing fact into a reachability fact, and the walk is monotone so it could not
withdraw one anyway.

Representation: an **L2 resource graph**, with capacities linked to resources by a
`REQUIRES_RESOURCE` edge. Chosen over a declaration field because ADR-0205 forbids
topology in properties — the repo has been burned three times — and over a filtered
DataState realm, which is how `input_group` failed.

#### What is a resource and what is a DataState

> **A resource is given back. A DataState is transformed or consumed.**

The test is **declarative and per capacity**, not per object: a capacity either
`REQUIRES_RESOURCE` something and returns it, or `CONSUMES` it and produces
something else. The same physical object can appear either way depending on what
the capacity does to it.

- **the stove** — `boil` holds the burner and releases it. **Resource.**
- **the hand** — `grab` takes it, releases it when the grab completes. **Resource.**
- **the mug** — ends up inside `ds:cup_of_tea`; nothing gives it back. **DataState.**
- **the kettle** — carried, placed, poured from; never released during the request.
  **DataState.**

**Tie-breaker where an object is ambiguous: is it returned within *this request's*
horizon?** A kettle is given back eventually — but not before the tea exists, so for
this request it is a DataState. Only the resource axis is affected; nothing about
reachability changes.

Each resource carries two independent flags:

| | **attended** — occupies the agent | **unattended** — runs alone |
|---|---|---|
| **exclusive** | the hand | the stove burner |
| **shareable** | the camera being aimed | a loaded image, a text corpus |

**Overlappable = no two steps hold the same *exclusive* resource at coinciding
times.** Shareable resources never block. Attendedness decides whether the *agent*
is free, which is a separate question from whether the *tool* is free.

**Duration is a learned parameter**, not a declared field — it varies per run and is
measured, like any other learned parameter.

### 5.3b Tool use — three things, no new concept

- **availability** — is there a stove? A DataState (`ds:stove_available`).
- **competence** — do I know how to use it? A registered capacity, i.e. a Skill.
- **occupancy** — is it busy? The resource axis above.

Boiling water needs all three. Merging them would invent a fourth concept that is
not required.

### 5.4 Decompose

If no known pipeline matches, the system searches the L3 graph for one, **using
CGT**.

Decomposition has **two independent motivations**. Either is sufficient.

> **A pipeline P reaching milestone M is *self-sufficient* when every DataState
> involved in P can be produced using P alone.**

If a candidate `PP` for milestone `M'` needs a DataState `D` that `PP` cannot
produce, `PP` is not self-sufficient. The system then looks for a self-sufficient
pipeline `PP'` that produces `D`.

If it finds one, **`M'` is decomposed**: `Mc → M'`, where `Mc = D` is a child
milestone of `M'`, reached first via `PP'`. `PP` then serves as the pipeline from
`Mc` to `M'`.

**Motivation 2 — low appropriateness.** Where several paths exist between the
current state and a milestone, the known or found path is not necessarily the best
one. When a milestone's appropriateness is low, the system may decompose it in
order to reach a child whose pipeline carries higher confidence — even though the
pipeline it already has is self-sufficient.

**Decomposition proposes several children and chooses among them — but only where
they are alternatives.** CGT's verdict is grouped `capacity → [missing DataStates]`.
Within one group every DataState is a **required** child and there is nothing to
choose. Across groups the groups are **alternatives**, and the choice is made by a
`selection_policy` value weighing the children's **appropriateness** against their
pipelines' **cost**. Appropriateness alone is not the rule: cost is deliberately not
folded into it, so a policy that ignored cost would make §5.3's scheduling
decorative.

**Decomposition is per milestone, never per tier.** Each milestone is judged on its
own: one branch may decompose three levels while its sibling resolves in one step,
because the system's confidence and its current knowledge differ per branch. A tier
is not decomposed as a unit and the tree is expected to be uneven.

This is **recursive** — `M'` may decompose into many children. **Every
decomposition updates the milestone tree and restarts the loop.**

As self-sufficient pipelines are found, the **Found_Pipelines** store (L5) is
updated.

---

## 6. Promotion

**When a pipeline in Found_Pipelines is executed successfully, it is written to
Known_Pipelines (L2).** That is what makes it "known" for §5.2.

Two stores, two lifetimes: **Found_Pipelines is L5** — per-run, candidate,
unproven. **Known_Pipelines is L2** — durable, proven by execution.

---

## 7. What this scenario fixes about CGT

- **Self-sufficiency is exactly what the forward walk computes.** A pipeline is
  self-sufficient when every input of every step is either in the current system
  state or produced by an earlier step inside the same pipeline. That is the
  forward walk's termination condition, not an extra test.
- **CGT is called at §5.2 and §5.3**, once per milestone, with the current system
  state as its start set and the milestone as its target.
- **Failure is informative, not terminal.** When CGT reports a DataState it cannot
  produce, that DataState *becomes the next child milestone*.
- **The verdict is grouped `capacity → [missing DataStates]`, not a flat list of
  pairs.** The capacity is the grouping key that separates AND from OR: one capacity
  short of `D1` and `D2` means **both** are required children; two capacities each
  short of one means the two are **alternative** decompositions. A flat list cannot
  tell those apart. This holds only because every capacity is `all_required` —
  retiring `any_of` is what makes the grouping unambiguous.
- **CGT does not decide milestone order.** Its ordering is over capacities inside
  one pipeline. Milestone ordering comes from the tree (§5.1).

---

## 8. Where this changes ADR-0206

1. **Decomposition has two motivations, and only one is confidence.**
   Self-sufficiency (structural, deterministic) *and* low appropriateness
   (judgement). ADR-0206 §3 knows only the second. Its *"stop at the first pipeline
   clearing the bar"* is still true for motivation 2 and does not apply to
   motivation 1.
2. **Pipelines carry no confidence.** ADR-0206 §5's "fitness for this task" is
   replaced by the map's **targeting** confidence (§4) — fitness is decided when
   the task's final DataState is chosen, not when a pipeline is.
3. **Independence agrees with ADR-0206, it does not contradict it.** Rejected
   alternative 7 — *"deriving sequence/parallel from graph topology… the execution
   tree is an output of the loop"* — is exactly what §5.3 does: independence is read
   from the self-sufficient pipelines found, not from path-reachability and not
   declared when the tree is listed. No amendment needed on this point.
4. **Six confidences**: two on hints, three on the map, one on milestones. None on
   pipelines. ADR-0206's one-per-transition ladder is replaced by this set.
5. **`Found_Pipelines` is a new L5 store.** No such thing exists.
   `Known_Pipelines` maps onto the L2 `pipelines` store being built at C2R4.

---

## 9. Settled by the owner

**9.1 Appropriateness is child-to-parent.** Not a property of a milestone alone;
it ranks a child against its siblings for reaching the same parent. Folded into
§5.1.

**9.2 Independence is determined on the first pass of the plan loop**, as an output
of §5.3 — not recomputed as state grows.

**9.3 Cross-branch dependency cannot exist.** A branch is an independent pipeline
by definition. Two branches sharing a child milestone share a DataState and are
therefore not independent.

**9.4 Unproducible DataState ⟹ "I can't solve this request."** That is the
termination condition.

**9.5 There is no planner/executor split over ordering.** All ordering is decided by
Resolution, through milestone dependency. The executor follows the order the plan
gives it and makes no scheduling decision of its own. "Do X while Y runs" is not a
runtime optimisation — it is the correct dependency, discovered at plan time.

---

## 10. Open

**10.1 CLOSED** — resources moved to their own axis (§5.3a), outside the graph CGT
searches. The monotone walk is preserved.

**10.2 The `relate` capacity is not scoped yet.** It is not a traversal — it is set
intersection plus an interval check over pipelines CGT already produced — so it does
not belong inside CGT. Family `path-finding`, alongside `reachable_strata` and
`construct_dag`. Naming and signature deferred until the resource graph exists.

**10.3 Cost has no home yet.** It is a property of a pipeline, learned, and consumed
by the selection policy in §5.4. Nothing currently stores it.

---

## 11. Change record — delete before this document is final

| # | Change | Why |
|---|---|---|
| 1 | Subsystem named **Resolution** (document retitled from "Request Formulation"); the map's second confidence renamed **resolution → targeting** | The word was needed for the subsystem; "resolution-set" keeps its name |
| 2 | Hints are an **L2 graph**; the extracted hint set lives in **L5** | Was written as if hints were only a transient list |
| 3 | The map **contains** `hints → tasks`; it is a dictionary also holding the current system state | Was written as if the map *were* the hint→task mapping |
| 4 | The plan runs from the **current system state (DataStates loaded in L5)**, not from "initial DataStates" | Same set, correct name |
| 5 | §5.1 retitled **Milestone tree**; its confidence question reworded to *is this the right milestone to reach first?* | Matches what appropriateness measures |
| 6 | **Appropriateness is child-to-parent**, ranking siblings against each other for reaching the same parent | Was written as a property of a milestone alone, which made a freshly decomposed child 1.0 |
| 7 | §5.2 and §5.3 name **CGT** as the finder | Was unattributed |
| 8 | Decomposition has **two motivations** — non-self-sufficiency *and* low appropriateness | Self-sufficiency was recorded as replacing confidence; it does not, it adds to it |
| 9 | Pipeline confidence replaced by the map's **targeting** confidence, not deleted | ADR-0206 §5's "fitness" has a home after all |
| 10 | **Self-sufficiency is the authority**; reachability rejected as a test | Two competing bases were in the document |
| 11 | Independence = **disjoint subgraphs**, and is **determined in §5.3 on the first pass**, not declared in §5.1 | No pipeline exists when the tree is listed, so there is nothing to test disjointness on |
| 12 | Former §8.3 reversed: independence **confirms** ADR-0206's rejected alternative 7 rather than contradicting it | Follows from 11 — the execution tree is an output |
| 13 | Former §10.1 (detecting a mis-split) **closed** | Follows from 11 — a split read from found pipelines cannot be wrong |
| 15 | **No planner/executor split** (§9.5); ordering is wholly Resolution's, discovered as dependency | An earlier note called runtime overlap an executor concern — wrong; correct dependency analysis already yields it |
| 16 | Independence also requires **disjoint capacities**, not only DataStates (§5.1) | Two branches using the same capacity interfere |
| 17 | **Decomposition is per milestone, not per tier** (§5.3); the tree is expected to be uneven | Confidence and current knowledge differ per branch |
| 18 | **§10.1 opened** — consumed resources vs the monotone walk | Surfaced by the one-handed agent in the worked example |
| 25 | **Resource vs DataState criterion** (§5.3a): a resource is *given back*, a DataState is *transformed or consumed*; declarative per capacity, with "returned within this request's horizon" as the tie-breaker | Without it every object drifts into being a resource |
| 19 | **Resources are a separate axis** (§5.3a) — an L2 resource graph with `REQUIRES_RESOURCE` edges, outside CGT's searched graph; two flags, exclusive/shareable and attended/unattended | The walk answers *can it be done*, resources constrain *when*; and the walk is monotone so it could not withdraw one |
| 20 | **Duration is a learned parameter** | It varies per run; it is measured, not declared |
| 21 | **Independence and overlappability are two relations** (§5.3) | Sharing a resource blocks independence but not necessarily overlap |
| 22 | The loop gains a third action, **relate** (§5.3); decompose becomes the fourth | Order must be known during the loop, not after, if cost is to influence decomposition |
| 23 | **Tool use = availability + competence + occupancy** (§5.3b), all three already modelled | Prevents a fourth concept being invented for tools |
| 24 | Decompose **proposes alternatives and chooses by policy**, weighing appropriateness *and* cost (§5.4) | Appropriateness is a likelihood, cost is a duration; folded together, neither is recoverable |
| 14 | Verdict shape is **grouped by capacity**, not a flat pair list | The capacity is what separates required children from alternative decompositions; the original "which capacity needed it" justification was diagnostic only |
