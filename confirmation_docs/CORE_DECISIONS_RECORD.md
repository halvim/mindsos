# Open decisions

**Filed:** 2026-07-31. Everything settled in discussion is in the other three documents;
this is only what is still open.

---

## A. Concept — must close before `planning.decompose` can be built

**A1. Where does the AND/OR determination live?**
Two milestones are dependent if they lie on the same path, independent if on separate
paths — deterministic, readable from graph topology. Agreed it belongs to planning; the
placement is undecided.
*Caveat to weigh:* path-reachability in the capacity graph is not the same as the pipeline
eventually chosen, so a purely topological answer may over-constrain — it can mark two
milestones dependent because *some* path connects them, even if the chosen pipelines are
independent.

**A2. Does `decompose` emit labelled or unlabelled waypoints?**
If decompose labels which siblings are AND and which are OR, it is making a judgement,
which breaks the deterministic/judgement split. If it emits an unlabelled set and the
chooser assembles the arrangement, the chooser is doing more than picking. A1 and A2 are
one question seen from two sides.

**A3. Does the `Milestone` tree become the single plan representation?**
Today `PlanResult`'s endpoint dictionaries and the Milestone tree are two descriptions of
the same plan, and only `PlanResult` carries the target. Consolidating is the clean answer
and the largest interface change in the plan — it touches dream (streams the plan graph),
collection-iteration (reads leaf ordering and targets), and arc1's planner shadow. The
alternative is keeping both in sync, which is how they drifted apart.

**A4. Where is the incremental hub index maintained, and what updates it?**
Hub-from-pipelines is a calculation over coincident DataStates, performed as the system
learns new pipelines. That implies a maintained index. No home decided.

**A5. Who declares a brain's milestone DataStates, against what criteria?**
No brain has milestone DataStates today and no milestone tree exists anywhere. Hub
discovery proposes candidates; something has to accept them. ARC will need `profiling`,
`comparisons` and their children as real DataStates.

**A6. Does the "not sure" flag live on the Episode?**
And how does dream learn about it? `dream.retry` fires only on **failed** episodes today.
Completed-while-unsure is a third category that does not exist. Coordination item with the
dream chat.

---

## B. Verification owed before building

**B1. `SubgoalTemplate`'s property schema — unread.** Does it already carry a DataState
reference, or does it need a field? The whole "storage already exists" claim rests on
this.

**B2. `RequestPattern.confidence` — which confidence is it?** It may be the
appropriateness confidence the model needs, or something else. ADR-0152 §2 kept it
deliberately when ADR-0094 dropped confidence from pipelines, but the semantics are
unconfirmed.

**B3. ARC's DataState roster — unread.** My grep came back empty (wrong pattern, not a
finding). Needed to size A5.

**B4. `feat/finder-default-ruling` — what is that chat doing?** It has a live worktree in
the same territory as CORE-C2. Must be resolved before C2 starts.

---

## C. Plan and process

**C1. Approve the CORE-C chain structure and the `feat/*` naming** (no phase numbers).

**C2. The WSD map edits — do I make them here, or route them?** No WSD chat is open. You
said edit here with your approval; the edits are in `CORE_RECONCILIATION_PLAN.md` §3.

**C3. Does the concept document become an ADR?** Agreed in principle; timing was "after
we finish discussing." It defines a core mechanism and closes POST_PHASE_38 q4, so it is
ADR-shaped.

**C4. STATE.json `recent[]` for #99** — block drafted, not yet pasted or committed.

---

## D. Settled — recorded so they are not reopened

| Decision | Answer |
|---|---|
| Confidence values | all **1.0** for now (taught pipelines and capacities are 1.0 by definition) |
| Thresholds | all **0.8** for now, but **per transition**, never one global constant |
| ADR-0094 | **not reopened** — it moved confidence ownership to ALS; a field ALS writes is consistent |
| Confidence storage on taught pipelines | **metadata**, not content (content is frozen under `immutable_successor`) |
| Hub measurement, v1 | the **capacity graph**; taught/found-pipeline intersections as the system learns |
| Interpretation capacities | **contract only** — bodies come from skill packages |
| v0 placeholders | **deleted**, not kept; the Phase-50 reference bundle becomes the test fixture |
| Shims | any shim, placeholder or helper is deleted **once a proper replacement exists** |
| `BFSFinder` | deleted; BFS becomes a *method* the one Finder can use |
| Found pipelines | **stay in the plan**, but taught pipelines are the priority |
| Milestones | DataStates, discovered as hubs, and teachable |
| Decomposition | breaks work into pieces, one layer at a time, only where confidence is missing |
| `planning.decompose` | stays **one capacity**; generate-and-choose split is `planning.*` vs `decision.*` |
| Appropriateness | **validated** at every layer, not checked once at mapping |
| Failure mode | **"I'm not sure"**, not "I don't know" — answered externally as don't-know, flagged internally for dream |
| Dream work | **continues** — no file overlap with C1 or C2; C3 touches `plan_construction.py` and `orchestrator.py` |
| Numbering | `feat/*` + `<name>-confirmed` tags; phases 51–56 belong to WSD, 57+ to DWF |
| WSD | a **consumer**; the June 2026-06-25 pass fixed attribution, this plan fixes scheduling |

---

## E. Round-2 additions (2026-07-31)

### Newly settled

| Decision | Answer |
|---|---|
| Planning | is a **loop**: search L2 → find in graph → if not confident, decompose → find again |
| "No path found" | **not a failure** — an honest don't-know. Already ratified as the unbuilt `pipelinenotfound-to-dontknow` pending design |
| Milestone definition | a DataState the system **already knows**, does not currently hold, lying between here and the goal |
| Execution tree | an **output** of the planning loop, not an input — dependency read from the pipelines chosen |
| Searches | are **capacities** the system calls when needed — which dissolves the L4↔L0 layering problem (`CapacityContext` already carries `kl` and `cl`) |
| `request_patterns` | is the **shortcut store**; rename to `request_knowledge` |
| Ownership | `request_knowledge` **references**, never owns. Hints, maps, plans, milestones are individual L2 knowledge nodes shared across request kinds |
| Scope | all discovered/taught knowledge is written **Local**; an admin promotes to Global. Already the designed lifecycle (ADR-0150 §am-8) |
| `promoted_pipelines` | pipelines taught by us or discovered by the system; "promoted" = admin-approved into Global |

### Still open

**E1. Is retiring `learned-pipelines` worth it?** The blocker ADR-0203 cited (D38) was
settled by ADR-0156 as bipartite. What remains is the `input_group` graph form. Unifying
gets one store, a real `status` lifecycle, and `n_runs`/`outcome_history` for ALS — at the
cost of reopening ADR-0203 and settling the input-group hyperedge shape. My read: worth
it, because that shape blocks the finder too. **Your call.**

**E2. The two renames** — `request_patterns` → `request_knowledge`, and
`promoted-pipelines` → ? Decide both now, execute once with the schema change.

**E3. The `request_knowledge` writer.** Nothing writes to the role today. This is the
learning loop and is larger than the read side.

**E4. Normalisation scope.** Converting `relevant_hints` / `paired_pipelines` from IRI-list
properties to real edges, and adding node types for map, plan and milestone. Same defect
as `Milestone.parent_ref` and DataState subsumption — three instances, one fix pattern.
Decide whether they are fixed together.
