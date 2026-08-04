# Request Resolution — worked example: "Make me a cup of tea"

**Filed:** 2026-08-02. **Status:** for approval, step by step.
**Governed by:** `CORE_REQUEST_RESOLUTION_SCENARIO.md`. Where the two disagree, the
scenario wins and this file is corrected.
**Calls:** `CORE_CAPACITY_GRAPH_TRAVERSAL.md` (CGT) at §5.2 and §5.3.

The point of this example is to be followable by anyone. Nothing here is domain
knowledge about MindsOS; it is the Resolution pipeline run once, end to end.

---

## 0. Setting

An agent with **one free hand**, in a kitchen.

**Current system state — DataStates already loaded in L5:**

| DataState | meaning |
|---|---|
| `ds:tap_available` | there is a tap |
| `ds:stove_available` | there is a stove |
| `ds:kettle_located` | the agent knows where the kettle is — on the counter |
| `ds:mug_located` | the agent knows where a mug is — **inside the cupboard** |
Note what is **absent**: nothing says where the tea bags are.

**Resources** (a separate axis — not DataStates, not searched by CGT). A resource is
**given back**; a DataState is **transformed or consumed**:

| | classed as | why |
|---|---|---|
| the hand | **resource** — exclusive, attended | `grab` takes it, releases it on completion |
| the stove burner | **resource** — exclusive, **unattended** | `boil` holds it, releases it when the kettle comes off |
| the kettle | **DataState** | carried, placed, poured from — never given back before the tea exists |
| the mug | **DataState** | ends up inside `ds:cup_of_tea`; nothing returns it |

So the container is **not** a shareable resource. It is the output. Even as a
resource it would be exclusive — two pipelines cannot pour into one mug and get two
teas.

`ds:hand_free` no longer appears as a DataState.

The agent is **competent with the stove** — `use_stove` is a registered capacity —
and the stove **exists** (`ds:stove_available`). Availability, competence and
occupancy are three separate things and all three are needed to boil water.

**Known_Pipelines (L2), from earlier successful runs:**

- `P_brew` : `{ds:hot_water, ds:tea_bag_in_hand, ds:container_in_hand}` → `ds:cup_of_tea`
- `P_boil` : `{ds:kettle_on_stove}` → `ds:hot_water`

---

## 1. Request

> **"Make me a cup of tea."**

---

## 2. Hints

Extracted against the **L2 hint graph**. Other L2 graphs point into it — a
word-graph, a drink-graph, an object-graph — and those links are what let the
system read a clue out of plain words.

| hint | from | appropriateness |
|---|---|---|
| the thing does not exist yet | *make*, word-graph | high |
| it is produced by assembling parts | *make*, word-graph | high |
| tea requires a tea bag and hot water | *tea*, drink-graph | high |
| tea is served hot | *tea*, drink-graph — **assumed** | lower |
| a cup is a container | *cup*, object-graph | high |
| the cup is not necessarily the required container | *cup*, object-graph — **assumed** | lower |
| the recipient is the user | *me*, word-graph | high |

Two confidences on `request → hints`: **extraction** (did I find them all?) and
**appropriateness** (are they useful?). The two assumed hints carry lower
appropriateness — that is the mechanism, not a caveat.

The hint set is saved to **L5**.

---

## 3. Map

Built from the hint set, using **L2 knowledge**. The drink-graph is what knows tea
needs a tea bag; the map does not walk the L3 graph, and does not run CGT.

**Tasks and their final DataStates:**

| # | task | final DataState |
|---|---|---|
| T1 | boil water | `ds:hot_water` |
| T2 | obtain a tea bag | `ds:tea_bag_in_hand` |
| T3 | obtain a container | `ds:container_in_hand` |
| T4 | assemble the tea | `ds:cup_of_tea` |

Plus the **current system state** from §0.

Three confidences: **task extraction** (all tasks found?), **targeting** (right
final DataState per task?), **appropriateness** (is this task set useful?).

**Targeting does real work here.** Because *"a cup is not necessarily the required
container"* came in at lower appropriateness, T3's final DataState is
`ds:container_in_hand`, **not** `ds:cup_in_hand`. Had the assumption been trusted,
the system would have committed to a cup and failed if only a mug were available.

The **resolution-set** is `{ds:hot_water, ds:tea_bag_in_hand,
ds:container_in_hand, ds:cup_of_tea}`.

---

## 4. Milestone tree, tier 1

Tier 1 **is** the resolution-set — one milestone per task, four of them.

At this point the tree is flat. **No parent/child relation is known yet, and no
independence is known yet.** Both are read from the pipelines, in §5.

---

## 5. The plan loop

### 5.1 First pass — consult Known_Pipelines

`P_brew` is a hit for `ds:cup_of_tea`. It starts from `ds:hot_water`,
`ds:tea_bag_in_hand` and `ds:container_in_hand` — none held, none produced by
`P_brew`. **Not self-sufficient.**

The other three tier-1 milestones are exactly the DataStates it is missing, so they
become **children of `ds:cup_of_tea`**. The flat tier acquires its shape.

### 5.2 T1 — boil water

`P_boil` is a hit for `ds:hot_water`. It starts from `ds:kettle_on_stove`, not
held. **Not self-sufficient.** → child `ds:kettle_on_stove`.

CGT runs for `ds:kettle_on_stove` from the current state. `place_on_stove` consumes
`ds:kettle_in_hand` and `ds:stove_available`; `ds:kettle_in_hand` is not held.
**Verdict:** `place_on_stove → [ds:kettle_in_hand]`. → child `ds:kettle_in_hand`.

CGT runs for `ds:kettle_in_hand`. `grab` consumes `ds:kettle_located` and
`ds:hand_free`, both held. **Self-sufficient.** Branch bottoms out.

### 5.3 T2 — obtain a tea bag

No known pipeline. CGT runs for `ds:tea_bag_in_hand`. `grab` needs
`ds:tea_bag_located`, which is **not** in the current system state.
**Verdict:** `grab → [ds:tea_bag_located]`. → child `ds:tea_bag_located`.

CGT runs for `ds:tea_bag_located`. `search_kitchen` consumes nothing held-dependent
and produces a location. **Self-sufficient.**

> This is the nuance case. Had the system known where the tea bags were, T2 would
> have resolved in one step, exactly as T3's container would have if the mug were
> on the counter. **What the system already knows is what decides how deep the tree
> goes.**

### 5.4 T3 — obtain a container

No known pipeline. CGT runs for `ds:container_in_hand`. `grab` needs
`ds:mug_located` — held — and `ds:hand_free`. But the mug is **inside the
cupboard**, so `grab` also needs `ds:cupboard_open`, not held.
**Verdict:** `grab → [ds:cupboard_open]`. → child `ds:cupboard_open`.

CGT runs for `ds:cupboard_open`. `open_door` consumes `ds:hand_free`. **Self-sufficient.**

### 5.5 Relate

**Independence — structural.** `ds:kettle_in_hand`, `ds:tea_bag_in_hand` and
`ds:container_in_hand` all use the `grab` capacity. Shared node ⟹ **not
independent**.

**Overlappability — temporal, and the interesting one.** The three grabs each hold
**the hand**, which is exclusive and attended, so no two of them overlap. But
`boil` holds **the stove burner**, which is exclusive and **unattended** — it does
not hold the agent. So everything the agent does overlaps the boiling freely.

That is why the agent searches for the tea bag while the kettle boils. Not a
scheduling trick and not an executor choice: the hand is released when
`place_on_stove` completes, so `search_kitchen` depends on `place_on_stove`, never
on `boil`. All ordering is Resolution's; the executor follows what it is given.

**No shareable resource appears in this example**, so only two of the four
resource quadrants are exercised. A modality example (two pipelines reading one
loaded image) would cover the rest.

---

## 6. The milestone tree

```
                              ds:cup_of_tea
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
        ds:hot_water        ds:tea_bag_in_hand    ds:container_in_hand
              │                     │                     │
     ds:kettle_on_stove     ds:tea_bag_located      ds:cupboard_open
              │
      ds:kettle_in_hand
```

Every edge is parent ← child: the child must be reached first. **Appropriateness**
is measured on each edge — *how likely is the parent, given this child?* — and
ranks siblings against each other, not milestones in isolation.

**Decomposition is per milestone, never per tier.** Each milestone is judged alone:
`ds:hot_water` decomposed twice while `ds:tea_bag_in_hand` decomposed once and
`ds:cup_of_tea`'s children were fixed in one pass. A tier is not decomposed as a
unit.

Depth is not uniform, and that is the point: `ds:hot_water` is three deep because
the system had to be told nothing about the kettle, while `ds:tea_bag_in_hand` is
two deep only because the tea bag's location was unknown.

---

## 7. Execution order

Bottom-up. The hand sequences everything that needs it; `boil` does not, so work
continues while it runs.

```
grab(kettle) ─→ place_on_stove ─→ boil ─────────────────────┐
                      │                                     │
                      └→ [hand free again]                   │
                            │                                │
                            ├→ search_kitchen → grab(tea bag)│
                            │                                │
                            └→ open_door → grab(mug) ────────┤
                                                             ▼
                                                    pour / assemble
                                                             │
                                                     ds:cup_of_tea
```

Nothing above is an executor choice. Every arrow is a dependency Resolution found.

---

## 7a. Every confidence in this run

| # | on | confidence | value | why |
|---|---|---|---|---|
| 1 | request → hints | **extraction** | high | short, plain request; little room for missed clues |
| 2 | request → hints | **appropriateness** | mixed | *make*, *tea*, *me* high; *tea is hot* and *a cup is the container* are assumptions, low |
| 3 | map | **task extraction** | high | the drink-graph enumerates what tea requires |
| 4 | map | **targeting** | high for T1/T2/T4, **low for T3** | the container is an assumption — which is why T3 targets `ds:container_in_hand`, not `ds:cup_in_hand` |
| 5 | map | **appropriateness** | high | the four tasks plainly serve the request |
| 6 | milestone edge `ds:kettle_on_stove → ds:hot_water` | **appropriateness** | high | boiling follows directly once the kettle is on the stove |
| 7 | milestone edge `ds:kettle_in_hand → ds:kettle_on_stove` | **appropriateness** | high | nothing else is needed |
| 8 | milestone edge `ds:tea_bag_located → ds:tea_bag_in_hand` | **appropriateness** | high | knowing where it is is what grabbing needs |
| 9 | milestone edge `ds:cupboard_open → ds:container_in_hand` | **appropriateness** | medium | the mug is *believed* to be in the cupboard; opening the door does not guarantee it |
| — | any pipeline | **confidence** | **none** | pipelines carry no confidence; fitness was decided at #4 |
| — | any pipeline | **cost** | learned | duration is a learned parameter, measured per run; it is weighed against appropriateness when children are alternatives, and never folded into it |

Confidence #9 is the one that would trigger the second decomposition motivation —
see §9.

---

---

## 8. Promotion

Each self-sufficient pipeline was written to **Found_Pipelines (L5)** as it was
found. On successful execution they are written to **Known_Pipelines (L2)**:
`[grab]`, `[place_on_stove]`, `[search_kitchen]`, `[open_door]`.

`P_brew` and `P_boil` were already known and are unchanged.

Next time the same request arrives, §5.1 and §5.2 hit immediately and the tree is
shallower — **unless the tea bag's location is again unknown**, which is what makes
this a plan and not a recipe.

---

## 9. What the example demonstrates

| concept | where |
|---|---|
| hints as L2 graph links, with assumed hints at lower appropriateness | §2 |
| the map naming outcomes from L2 knowledge, without walking L3 | §3 |
| targeting confidence changing a final DataState (`container`, not `cup`) | §3 |
| tier 1 = the resolution-set, flat, with no relations yet | §4 |
| a known pipeline that is not self-sufficient triggering decomposition | §5.1, §5.2 |
| CGT's grouped verdict naming the missing DataState | §5.2–§5.4 |
| recursive decomposition to depth 3 | §5.2 |
| current knowledge deciding tree depth | §5.3 |
| independence read from the pipelines, counting shared capacities | §5.5 |
| overlappability as a separate relation, decided by exclusive/attended flags | §5.5 |
| a tool needing availability, competence and occupancy at once | §0 |
| duration as a learned parameter, held apart from appropriateness | §7a |
| promotion Found → Known | §8 |

**Decomposition motivation 2 — low appropriateness — is present but not taken.**
It means: the pipeline found *works*, but the child it goes through scores badly for
reaching the parent, so the system decomposes anyway to look for a better child.
Here that is confidence #9: `ds:container_in_hand` is reachable by opening the
cupboard and grabbing the mug, but the mug is only *believed* to be there. If a cup
were known to be on the drying rack, the system could decompose toward that child
instead — same parent, better-scoring route. **Owner to supply the instance to
write in.**

---

## 10. Open

**10.1 CLOSED** — resources are their own axis, outside CGT's searched graph. §5.5
and §7 are now what the model actually produces.

**10.2 The instance for decomposition motivation 2** (§9). Owner to supply.

**10.3 Only two resource quadrants are exercised** (§5.5). A shareable-resource case
is owed — two pipelines reading one loaded image.

**10.4 Cost has nowhere to live.** §7a records it as learned per pipeline; no store
holds it.

---

## 11. Change record — delete before this document is final

| # | Change | Why |
|---|---|---|
| 1 | Independence counts **capacities** as well as DataStates | Two branches using the same capacity interfere |
| 2 | Runtime-overlap-as-executor-concern **removed** | Wrong: the hand is released by `place_on_stove`, so correct dependency analysis already yields the overlap. There is no planner/executor split over ordering |
| 3 | §7 execution order redrawn to show work continuing while `boil` runs | Follows from 2 |
| 4 | The map's "obvious" is **L2 knowledge**, not L3 self-sufficiency | Keeps *self-sufficient* meaning one thing |
| 5 | **§7a added** — every confidence in the run, with its value and reason | The example named only targeting |
| 6 | **Decomposition is per milestone, not per tier** (§6) | Confidence and current knowledge differ per branch; the tree is expected to be uneven |
| 7 | Motivation 2 stated concretely and located at confidence #9 (§9) | It was named but not defined |
| 8 | ~~§10.1 opened~~ **CLOSED** — resources moved to their own axis | The walk answers *can it be done*; resources constrain *when* |
| 9 | §0 gains a **resource table**; `ds:hand_free` removed as a DataState | The hand is a resource held by `grab`, not a fact in the graph |
| 10 | §5.5 retitled **Relate**, split into independence (structural) and overlappability (temporal) | Two different relations; the stove being *unattended* is what lets the agent work while it boils |
| 11 | §7a gains a **cost** row | Duration is learned, weighed against appropriateness, never folded into it |
| 12 | §0 states **availability + competence + occupancy** for the stove | Tool use needs all three and no fourth concept |
| 13 | §0 classifies each object by the **given-back vs consumed** criterion; kettle and mug are DataStates, hand and stove are resources | Without the criterion every object drifts into being a resource; it also answers "is the container shareable?" — it is not a resource at all |
