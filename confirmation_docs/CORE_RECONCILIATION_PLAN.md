# CORE reconciliation plan (CORE-C chains)

**Filed:** 2026-07-31. **Revised** after the abstraction-levels conclusion.
**Status:** approved. **C1R1–C1R3 shipped** (`df8d3a5`); **C1R4 part 1** at `2c56246` and
**part 2 is now C1R5** (§13.5) — an earlier version of this line said "C1 shipped", which was
false. **C3R1 half-shipped** (`4fd8baa`) — see §4.
**C2: A0 + C2R1 SHIPPED** — squash `0496e7f` (PR #107), tag
`installed-skills-dual-scope-confirmed`, merged-state gate 4472/0. **C3R1 SHIPPED** —
`ae63aa2`, tag `find-verdict-confirmed` (`FindVerdict` replaces `PipelineNotFoundError`,
shim S4 retired). **C2R2 is BUILT** on `feat/core-c2r2` off `3591add` — P8-A lifted, **D1
closed by having no consumer**, ADR-0205 §amendment-3 filed and §amendment-1 flipped to
Accepted. **C2R3 is next.**
**Revised** 2026-07-31 by the CORE-C2 pre-build read-through (§0, §3, §3.1, §7, §9, §10, §12),
then reconciled at `60fe2ae` with the C3R1 chat's corrections (§2, §4, §9, §11) and at
`2c56246` with the C1R4 sweep (ADR-0205 §amendment-1) — both verified against the code and
carried through here.
**[2026-08-10] §13 opens five items this plan did not own** — C2R3a (atomic whole-composition
delete), C2R3b (attribution as a provenance edge; the skill ledger is deleted), the
Global-update migration, the ADR status split, and C1R5. **None is built and none has an
owner.** Each is a consequence of a ruling made elsewhere, which is why none had a home.
**Reads with:** `CORE_CONCEPT_PLANNING_AND_CONFIDENCE.md` (the model),
`CORE_VERIFIED_FINDINGS.md` (the evidence, incl. §12) and
**`CORE_C2_DECISIONS.md`** (what changed after reading the ADRs against the code).

---

## 0. The standing rule for every item in this plan

> **Concepts are the source of truth. Code matches concepts, never the reverse.**

Where shipped code already fits the model, keep it. Where it does not, **change the code**
— do not bend the concept to fit what exists. Several things in this plan exist today only
because an earlier decision was convenient, not because it was right.

**Every item below carries the same acceptance question, and it is a gate, not a
formality:**

> **Does the code match the concept?** Name the concept section it implements, and state
> what was changed to fit it — or state explicitly that the existing code already fits and
> why.

An item that silently preserves a mismatch has not passed.

**For a level item, that question has an exact form** (`CORE_C2_DECISIONS.md` §1.1):

> **Walk from a node at this level to its members one level down, and back up, reading only
> links. If any part of that walk reads a property, the level is not built.**

**And the companion rule, added 2026-07-31 after the CORE-C2 pre-build read-through:**

> **An ADR does not reach Accepted until someone has read it against the code it governs.**

Four defects were found in ADR-0205 and ADR-0206 within a day of their being Accepted, and
none needed new information — all four surfaced by reading the text against the modules it
describes. Two were places where a caveat raised during the discussion did not survive into
the written text. **When a discussion raises a caveat and the ADR states the confident
version, the caveat is the thing that was true.**

### 0.1 Every item owes a downstream rationale record

Subsystem and brain chats (WSD, FOL, DWF, arc1, nilm, dream, bongard, robot) design and
build against core. When core changes a concept, **they must be able to recover the
reasoning, not just the diff** — otherwise they re-derive the old model and drift back to
it. That has already happened once with WSD ownership.

So every item ships, alongside its confirmation doc, a short **rationale record**:

1. **What changed** — the concept, not the code.
2. **Why** — the argument, including what was rejected and on what grounds.
3. **What a subsystem must now do differently**, and what stays the same.
4. **Which ADRs it amends or contradicts.**

These live where a cold-start chat will actually read them: the ADR, the module docstring
at the point of use, and the subsystem's own phase map. *Putting the reasoning only in a
central document does not work — chats believe the artifact in front of them* (the
recorded lesson from the 2026-06-25 WSD ownership pass).

---

## 1. Naming and numbering

**No phase numbers.** Phases 51–56 are reserved by the WSD installation map; DWF is
pencilled for 57+. Use `feat/*` branches and `<name>-confirmed` tags (RULES §2).

`CORE-C<chain>R<step>`. Same chain is sequential; different chains run in parallel.

---

## 2. CORE-C1 — foundations *(docs and ADRs; no behaviour change)*

| ID | Scope |
|---|---|
| **C1R1** | Extract the `MindsOS-core` rows out of WSD slots 51–56; fix the 16 wrong `mindsos_*` docstrings; land these documents + the shim register. ~~delete dead `mindsos_capacity/types.py`~~ — **not done, and correctly so** (C3R1 chat): `types.py` holds the live `SessionArg` / `SessionProtocol` that domain layers accept. Not dead code, must not be deleted; **shim S14 is struck** (§9). C5R1's session primitive lands in `mindsos_server`; `types.py` keeps the protocol |
| **C1R2** | **ADR — abstraction levels.** The governing idea: one graph at several resolutions, each composed of the level below and verifiable by it. Fixes the vocabulary (*abstraction level*; `capacity / pipeline / milestone / plan / request`) |
| **C1R3** | **ADR — planning, decomposition and confidence.** The loop, the stopping rule, relational confidence, "I'm not sure". Closes POST_PHASE_38 q4 |
| **C1R4** | **ADR contradiction sweep.** **[part 1 SHIPPED 2026-08-01 — `2c56246` PR #104, record `f7be926` PR #105]** Six passes; the per-ADR framing did not converge, an exhaustive code sweep did. Output = **ADR-0205 §amendment-1** (**Accepted at C2R2**, `92d7421` — its "flips at C2R1" line used the pre-renumbering ids) + the coverage ledger `CORE_ADR_CONTRADICTION_SWEEP.md`. Criterion gained a **scope clause**; the composition primitive is **arity-selected** (`IntergraphEdge` for one member, `IntergraphHyperEdge` for several — already shipped, no core change); subsumption is **not** composition; compositional is **terminal**. **Part 2 is now its own item — C1R5** (§13.5). It was owed to no chat: §11 says C1 ends after C1R1 |
| **C1R5** | **[OPENED 2026-08-10]** **C1R4 part 2, split by kind** — the 21 `contradicts` + 9 `contradicts-if-built` in `CORE_ADR_CONTRADICTION_SWEEP.md`. §13.5 |

---

## 3. CORE-C2 — the abstraction substrate

**Revised 2026-07-31** by the CORE-C2 pre-build read-through. Numbering now follows
`STATE.json` `pending_designs[0]` (C2R1 = `installed-skills`); the previous
C2R0–C2R5 + C2R4a scheme is retired. **This settles the id collision the C3R1 chat flagged
and its note is removed** — C2 owns this chain, and it has renumbered. Cite C2 items by id
from here. Full rationale for every change: `confirmation_docs/CORE_C2_DECISIONS.md`.

**The governing correction.** An abstraction level is **not a store**. A level exists because
a **compositional intergraph link** exists: a node anchors a link whose members are nodes one
level down, and that link *is* the coarser resolution (`CORE_C2_DECISIONS.md` §1). Framing a
level as a new node type in a new role with a field schema is ADR-0205's **rejected
Alternative 2**. Level nodes are **thin** — an identity and a target link; all structure is
links.

| ID | Scope | Depends on |
|---|---|---|
| **A0** ✅ | **[SHIPPED `1e45067`]** **The three ADR amendments** — ADR-0205 §am-2, ADR-0206 §am-1, ADR-0148 §am-1 (§am-1 came from **C1R4** and §am-3 was filed at **C2R2** — neither was A0's; an earlier version of this row claimed all three and called them four), plus these plan corrections and `CORE_VERIFIED_FINDINGS.md` §12. **Docs only, lands before every code item.** Not bundled with C2R2: bundling doc corrections with a code change makes the gate result unattributable. Docs-only is still **gated** — `tests/test_adr_status_consistency.py`, and the test image copies `docs/` and `confirmation_docs/` into `/app` | — |
| **C2R1** ✅ | **[SHIPPED — `df3af56`…`fa5e18d`, gate 4472/0]** **`installed-skills` became dual-scope.** Also amended **ADR-0183 S3** so a user-installable bundle can exist at all, and added the first one (`tests/fixtures/skill_bundle_local`). Four design corrections came out of building it — `CORE_C2_DECISIONS.md` §12.1. Originally scoped as: Today it is Global-only (ADR-0150 §am-6) while `installed-capacities` is Local-only — an asymmetry that makes skill install effectively **admin-only**. Under the model a **user installs a Skill Local**; an admin promotes it to Global. Role bootstrap + `CAN_INSTALL_SKILL` semantics. **Cheapest high-value item in the plan**, and it depends on nothing — runs in parallel with A0 | — |
| **C2R2** ✅ | **[BUILT — the composition primitive]** (a) **P8-A lifted** — `compositional=True` with `ordered=False` is permitted; validation step 10 is retired in both `add_intergraph_hyperedge` and `update_intergraph_hyperedge` (the update copy was already unreachable). A deliberate override of the recorded identity-bearing argument, argued on the plan level's need for a **partial** order, **not** a restoration of an ADR-0148 contract. (b) **D1 is CLOSED by having no consumer** — the properties-editable amendment is **not** made; see the resolved note under this table. Also: ADR-0205 §amendment-3 filed, §amendment-1 flipped to Accepted, `docs/concepts/glossary.md` updated, and the §am-2.3 ordering table amended (pipeline steps become `ordered=False`, order derived) | A0 |
| **C2R3** | ⚠ **BLOCKED ON THE SUBSTRATE — read ADR-0205 §amendment-4 first (shipped `50c0cbb`, tag `metagraph-boundary-confirmed`).** A compositional link requires both endpoint graphs in **one** `Metagraph` and a brain holds **four**, so the links this item exists to write are inexpressible until the substrate is unified. **The unification lands before this item builds.** Build scope as ruled: intergraph accessors on `MetagraphView` with **both** `CapacityLayerView` and `LocalPreferringView` routed through them (§am-4.8 — there are now two readers of the bipartite topology, not one); **inverse indexes** on `Metagraph`, which is also §13.6's `_has_intergraph_edge` O(E) scan; `walk(direction=…)`; **dangling-member detection** (`Graph.remove_node` is blind to intergraph links — findings §14.2 — and that blindness is the only trigger derived dormancy has); persister round-trip. *"Links become first-class" is NOT ruled* — indexed adjacency inside the existing ownership model is the boundary. Original scope follows. | **The link mechanism — what creates levels at all.** Write and read compositional and ordinary intergraph links between L2 role-graphs; **persister round-trip in the gate**, covering the link kinds every later item needs. ⚠ **The READ half is missing too, not only the write half** — `MetagraphView` has **no intergraph accessor at all**; `get_edges` / `step` are intra-graph. §12.1 and `CORE_VERIFIED_FINDINGS.md` §12.1 named only `KLWriteHandle`. Plus **the traversal primitive**, **attribution** (the DOWN walk + `installed_by`; must return *which* dependencies are missing, not a boolean) and **invalidation** (the UP walk — a level node becomes unsupported when its last member link is flipped out of force). ⚠ **Attribution moves out to C2R3b** (§13.3): as written it reads `installed-capacities.installed_by`, and that role has a schema, IRI minting and **no writer** — `driver.py:324` stamps `installed_by` on Global L2 content nodes instead | C2R2 |
| **C2R3a** | **[OPENED 2026-08-10]** **Atomic whole-composition delete** + the `remove_graph` **crossing-only** precheck + the §am-1.5 withdrawal. Accepted by the C2R3 chat as a consequence of its walk, explicitly **not** C2R3 scope. §13.1 | C2R3 |
| **C2R3b** | **[OPENED 2026-08-10]** **Attribution is a provenance edge**; `CORE_RECONCILIATION_PLAN.md` §8a item 7 (the skill ledger) is deleted and attribution becomes **core-owned**. §13.2 | C2R3 |
| **C2R4** | **The pipeline level** — one store named **`pipelines`**; retire `learned-pipelines` and `promoted-pipelines`; steps convert to the composition primitive (**`ordered=False`**, holding only the capacity steps; start and end DataStates are separate links); `edge_sequence` retired; **migration of shipped `promoted-pipelines` data**. Supersedes Phase 13 **PB-9**. **Three rulings from C2R2 land here** (ADR-0205 §am-3.2 / §am-3.4): step order is **derived** from the steps' `CONSUMES`/`PRODUCES` + start DataStates with a **first-by-IRI tie-break**, never stored; the store **must not persist a finder choice** (no `finder` field, no `selection_policy` — #99's start-arity `_select_finder` is transitional by construction); and an **empty pipeline is not a pipeline** — refuse it at the store unless CORE-C3 lands the `already_held` verdict first. Also carries a gate assertion that no registered capacity declares `fold` or `any_of` | C2R3 |
| **C2R5** | **The milestone level** — a node that *references* its target DataState and *composes* the pipelines reaching it, **one link per pipeline** (alternatives, per ADR-0205 §3); hub discovery; the **taught-milestone write capacity**. Moved **after** the pipeline level: a milestone links over pipelines and cannot exist first | C2R4, ADR-0206 §am-1 |
| **C2R6** | **The plan level** — the milestone tree lives here: parent→child is decomposition, sibling→sibling is dependency, and the plan's composition over its milestones is `ordered=False`. `PlanResult`'s endpoint dicts, `sequence_index`, `parent_ref` and `children_refs` all become links; `MAX_DEPTH` retired. **Send the dream chat the trace-reshape notice before this lands** | C2R5 |
| **C2R7** | **The request level** — `request_knowledge`, renamed from `request_patterns`. `relevant_hints` becomes links with confidence on them; **`paired_pipelines` is retired, not converted** — pipelines are reached through plan → milestone → pipeline, and a direct request→pipeline link would recreate the duplication this plan removes. `SubgoalTemplate` retired | C2R6 |

> **[reconciled at `2c56246`] The primitive is selected by arity** (ADR-0205 §am-1.2).
> `add_intergraph_hyperedge` refuses 1-anchor/1-member; a **single-member** composition is an
> `IntergraphEdge` with `compositional=True`. A milestone takes **one link per pipeline** and
> a request **one link to its plan** — all single-member — so every level item must use both
> primitives, chosen by member count. Convention: **source = anchor, target = member**.
>
> **[reconciled at `2c56246`] A composition pins its graphs** (§am-1.6). `remove_graph`
> refuses while any incident compositional edge exists; ADR-0202 persists one chain graph per
> task. **Ruled for the trace: per-request links are non-compositional** (§am-2.2), so task
> graphs stay removable and run state stays mutable. What *durable* structure may be
> compositional is **open** and belongs to the milestone-level item.
>
> **[RESOLVED at C2R2 — D1 is closed by having no consumer]** Neither candidate consumer
> exists. **Pipelines carry no confidence** (ADR-0206 §5's *fitness for this task* moves to the
> map's **targeting** confidence), so `StepExecutionRecord.confidence` is a restated success
> flag and is deleted. **The milestone confidence is *appropriateness*, child → parent** — both
> endpoints are milestone nodes in one graph, so it is **same-graph 1-1**, which no shipped
> primitive expresses as a composition; ADR-0205 §am-1.3 (Ruling A) already rules that case a
> **plain typed intra-graph `Edge`**, freely mutable. And **`in_force` must not exist** —
> dormancy is derived on read (§6 + §am-1.5), so storing it is ADR-0192's rejected pattern.
> ⟹ nothing in C2R2–C2R5 writes a property to a compositional link; **§am-1.5's terminality is
> left untouched** and the question re-opens at **C2R5** with the first item that writes.
> ⚠ One consequence handed to **C2R6**: if child → parent is a plain edge, **decomposition is
> not a composition**, which `CORE_C2_DECISIONS.md` §1.2 and ADR-0206 §2 both assume it is.

**Skill attribution is no longer a core item.** The **skill ledger** — the sole source of
truth for *what a skill added* (which nodes, which links; install-time, append-only, never
holding confidence or structure) — is built with the **skill-packaging system**. Uninstall is
then `X's links − the links in S's ledger`: two reads, exact, nothing verified twice. Core
provides only the walk in C2R3. See `CORE_C2_DECISIONS.md` §7a.

> **[corrected at `60fe2ae`] There is no existing declared half to build on.** An earlier
> version of this section claimed the declared footprint already worked because
> `installed-capacities` carries `capacity_iri` + `installed_by`. **The C3R1 chat verified
> that false.** The driver stamps `installed_by` on **Global L2 content nodes** and filters
> *those* on uninstall; `mindsos_server/boot.py` says the `installed-capacities` role is
> "empty until" a user-scoped install exists. Schema and IRI minting ship; **nothing
> populates them**, so ADR-0183 §am-5's Local half is specified and unbuilt. The ledger is
> built whole. This does **not** affect C2R1, which touched only `installed-skills`.
> Recorded as `CORE_VERIFIED_FINDINGS.md` §12.6.

---

### 3.1 One traversal primitive — but it is not one direction

**Corrected 2026-07-31.** This section previously claimed four things were *"the same upward
walk"*. They are not:

| | Direction | |
|---|---|---|
| **Invalidation** | **UP** | a member is flipped out of force; what above it is now unsupported? |
| **Verification** | **DOWN** | does this level still hold against the level below? |
| **Attribution** | **DOWN**, then a property read | walk to the capacity level, read `installed-capacities.installed_by` |
| **Hub discovery** | neither | an **intersection over a set** — a *consumer* of `walk(DOWN)` over the pipelines, not a mode of the walk |

What they share is **level-adjacent traversal over the composition relation, in both
directions**. The primitive is therefore direction-parameterised:

```
walk(start, *, direction: UP | DOWN, view, stop, visit, max_levels) -> Iterator[Frame]
# Frame = (node, level, link, path, depth)
# UP   = which anchors hold me as a member
# DOWN = which members does this anchor hold
```

It is built in **C2R3**, not with the milestone level — reading links at a grain is what a
level *is*, so the primitive is not milestone-specific.

Four separate implementations of the same walk is how the topology-in-properties instances
happened. Writing one *upward-only* primitive for four consumers, three of which are not
upward, would have been the same mistake in a new form.

---

## 4. CORE-C3 — search and find

> **The ranked, per-item handoff for this chain is `CORE_C3R1_ADMISSION_CONFIRMED.md` §9**
> (opened 2026-08-10). It states, per item, what is broken, what was decided and why, what it
> blocks and what it does not, and what to verify first. Its live items are in `STATE.json`
> `pending_designs` alongside §13's — **one queue, two documents holding the reasoning.**
> §9.6 and §9.7 are deliberately not owed to a chat; §9.7 is the owner's.

| ID | Scope | Depends on |
|---|---|---|
| **C3R1** | **[HALF SHIPPED 2026-07-31 — `4fd8baa`, tag `finder-cycle-guards-confirmed`, gate 4450/0]** Done: the two phase-2 cycle guards — **D-B** (self-feeding producer) and **D-E** (a capacity under construction, *new* — returned a Pipeline naming one capacity as two steps and reported success). ADR-0071 §am-3. **[find_verdict SHIPPED 2026-08-04 — `ae63aa2`, tag `find-verdict-confirmed`, gate 4479/0.]** **Still not done:** the divergence sweep in `catalog_check.py` — `pipeline.py`'s docstring used to point brains at a function that does not exist and now says so, naming this item. The graph form of `input_group` is **struck, not owed** — see §12.1 | — |
| **C3R1b** | **[SPLIT AND PART-SHIPPED 2026-08-05]** Step admission turned out to be **three** predicates, and they do not all belong in the same place. Full record: **ADR-0071 §amendment-4**, with `CORE_CAPACITY_GRAPH_TRAVERSAL.md` §7.1 / §7.1b / §7.1c. **Shipped:** path-availability, `BFSFinder`-local, closing **D-A**'s first half (`bfs-step-admission-confirmed`, gate 4510/0); and the `operand_arity`-on-a-scalar rule, **shared** by both finders (`arity-admission-confirmed`, gate 4522/0). Also shipped with them: `find_pipeline`'s mis-typed return annotation plus a structural gate guard, the `InputContractError` export and its three-value `kind` set (`signature-sweep-confirmed`, slate 145 → 146), and `FindVerdict.already_held`, which answers **ADR-0205 §amendment-3.4** so C2R4 does not build its fallback. **Not shipped:** the outputs-meet-inputs rule this item was named for — last by measured value, and it lands labelled as hygiene that closes nothing, since §23.4 withdrew its arc3 ground and the surviving grounds argue *blanket over narrow* rather than *rule over no rule* | — |
| **C3R2** | **The search capacity** — look up known pipelines in L2, read the confidence off the edge, compare to threshold. A capacity, so `CapacityContext.kl` makes the layering problem moot | C2R7, C3R1 |
| **C3R3** | **[MERGED INTO the finder-as-capacities CR]** Producer-choice seam: record alternatives, selection as a policy; `BFSFinder` retired. The seam is `decision.select_producers`, one of four capacities in `CORE_CR_FINDER_AS_CAPACITIES.md`, and BFS becomes a `selection_policy` **value**, not a method. C3R1's remainder and C3R3 are one item | C3R1 |
| **C3R4** | **The find capacity** (Plan → Pipeline); `find_pipeline` and `mindsos_server/pipeline_runner.py` retired | C3R3 |

---

## 5. CORE-C4 — the planning loop

| ID | Scope | Depends on |
|---|---|---|
| **C4R1** | **Hub calculation** — coincident DataStates across pipelines. *No separate index: the milestone level (C2R5) materialises it.* Scope is the **update trigger** — recompute affected hubs on learn, dream sweeps the rest | C2R5, C2R4 |
| **C4R2** | **Confidence fields**, all transitions, in one deliberate change. Reconcile `chain_level` to the ladder — **note ADR-0205 §am-2: the target set is undefined until `hint` and `map` are settled as steps rather than levels; that ruling is this item's first task** (`plan_subtree` is retired — the loop covers it) | C1R3, C2R6 |
| **C4R3** | `planning.decompose` (deterministic) + `decision.select_decomposition` (judgement) | C3R2, C4R1, C4R2 |
| **C4R4** | **Lazy descent in the MM** — load the highest abstraction, expand only the low-confidence members, recheck | C4R3 |
| **C4R5** | **"I'm not sure"** — the flag, and dream's *completed-while-unsure* candidate category | C4R3 |
| **C4R6** | **The `request_knowledge` writer** — record a discovered solution so it is not rediscovered; **update the pointer when confidence shifts** (replacement, not decay); **record "I'm not sure" when nothing clears the threshold** rather than pointing at the least-bad option. The learning loop's write half | C4R3, C4R5 |
| **C4R7** | Real `predicate.sufficient` + `decision.should_replan`; interpretation contracts; all `placeholder=True` deleted; the reference bundle becomes the test fixture | C4R3 |
| **C4R8** | `scoring.attention_score`, `decision.signal_to_tier`, `phase6.attribute_blame` (blame descends the reconciled ladder) | C4R2, C4R7 |

---

## 6. CORE-C5 — brain-facing primitives

| ID | Scope | Depends on |
|---|---|---|
| **C5R1** | L0 session primitive replacing `DuckSession` ×3 | — |
| **C5R2** | Iterative refinement — design | C4R3 |
| **C5R3** | Iterative refinement — build | C5R2 |

---

## 7. Handoffs, not chains

- `BRAIN_ARCHITECTURE_AUDIT.md` → the arc1 and nilm chats. Every brain must adopt
  milestones; none has them today.
- **Dream chat:** deeper plan trees are coming (C2R6, C4R3); candidate selection needs a
  *completed-while-unsure* category (C4R5); PRE-5 (finder exposing alternatives) lands at
  C3R3. **Corrected 2026-07-31 — the "no file overlap with C1–C3" claim was false.** From
  **C2R5** onward every item touches `chain_artifacts.py`, `phase_1.py`,
  `plan_construction.py` and `orchestrator.py`. The per-request trace is being renamed to
  `<Level>Run` and stripped to references plus run state (ADR-0205 §am-2.2 — an earlier version of
  this line cited §am-3, which is C2R2's and about step order), so dream's reader
  will either break or silently read nothing. **Coordination is continuous from C2R5, and the
  notice must go out before C2R6 lands.**
- **A future WSD chat:** §8.
- **A future skill-packaging chat:** §8a. A Skill spans all abstraction levels, so the
  bundle format must be able to declare milestones and request knowledge — which do not
  exist until C2R5 and C2R7. Skill packaging therefore sequences **after** the
  abstraction substrate.
- **Sequencing for brains (settled):** (1) this plan changes core; (2) the skill-packaging
  chat designs and builds its system on that core; (3) brains then modify themselves
  against the skill-packaging system. Brains do **not** package during this plan.
- **Every brain chat:** brains are **users, not owners**. They conform to these decisions;
  they do not negotiate them. arc's runtime capacity shadows and nilm's Python control flow
  both change as a consequence.

---

## 8. What to hand a future WSD chat

Three edits, none of which a WSD chat is open to receive today, so they must be written for
a cold start:

1. `WSD_INSTALLATION_PHASE_MAP.md` §2 — WSD-4 loses the core rows and gains: *"Depends on
   CORE-C4R7 (extracted 2026-07-31). WSD-4 ships the `wsd-pipeline` bundle, the NLU
   cookbook, and the end-to-end scenario, which now **consumes** the core catalogs rather
   than containing them."*
2. Same file §2.1 — the `MindsOS-core` cells for slot 54 point at CORE-C ids.
3. `POST_PHASE_38_PHASE_MAP.md` §6 + q4 — record the extraction.

**This is a real schedule change for WSD:** WSD-4 can no longer ship its end-to-end
scenario until the core catalogs land.

---

## 8a. What to hand a future skill-packaging chat

1. **A Skill is not a group of capacities.** It is everything across *all abstraction
   levels* needed to serve a class of requests: capacities, pipelines, milestones, plans,
   request knowledge. Install adds the vertical; uninstall removes it.
2. **The bundle format needs two new slots** — milestone and request-knowledge content —
   which cannot be declared until C2R5 and C2R7 ship. Sequence after them.
3. **Uninstall keeps the user's data by default.** Learned parameters and taught structure
   survive; taught structure goes **dormant** and revives on reinstall. Removal is an
   explicit user choice.
4. **On-read verification is what makes dormancy safe** — nothing has to be deleted for it
   to stop being offered.
5. **The reverse-dependency guard must cover Local artifacts**, not only
   `requires_bundles`. Verify.
6. **Brains package as Skills** — but *after* you ship, not during core's work. Runtime
   `register_capacity` shadows are structural change outside a Skill and need a ruling
   (Q16). Sequencing: core (this plan) → skill packaging (you) → brains.
7. ~~**Skill isolation is yours, and so is the skill ledger.**~~ **THE LEDGER IS DELETED —
   2026-08-10, §13.2.** Skill isolation stays yours; **attribution does not**. The rest of this
   item is struck and kept only so the argument is recoverable: Core provides the traversal
   primitive and the dormant state (C2R3). **You build the ledger** — the sole source of
   truth for *what a skill added*: which nodes and which links, written at install, append
   only, entries being modification events. It must **not** hold confidence (relational,
   lives on the link, ALS moves it) or structure (a parallel copy of the graph, ADR-0205 §5).
   Uninstall is then `X's links − the links in S's ledger`: two reads, exact, nothing
   verified twice. **Do not scan every other skill's ledger per element** — that costs one
   read per installed skill and returns the same answer. The ledger is what makes uninstall
   work **across realms**, which the walk cannot do: a Global skill's capacities have no
   reachable path to what a user built on them Local. This collapses *declared footprint* and
   *derived footprint* into one mechanism. See `CORE_C2_DECISIONS.md` §7a.
8. **Core hands you C2R1** — `installed-skills` made dual-scope so a user can install
   Local. **You** decide the discipline questions core deliberately did not: does a Local
   skill record **append or mutate** (`installed-skills` is append-ordinal today,
   `installed-capacities` is `mutable_with_retention`)? Is promotion to Global a **copy or
   a re-append**, and how does that interact with the admin audit trail? If two users
   install the same Skill at **different versions**, does promotion carry a version
   constraint? These are yours.
9. **Attribution is many-to-many.** A pipeline taught from capacities of Skills X and Y
   depends on both. Derived artifacts do not *belong* to one Skill — plan for dependency,
   not ownership.

---

## 9. Shim register

A shim may exist only while we know what it stands in for **and** a real MindsOS piece is
named to replace it. Anything failing either test is a defect.

| # | Shim | Stands in for | Replacement | In |
|---|---|---|---|---|
| S1 | `find_pipeline` | the old singular keyword; 7 call sites | the find capacity | C3R4 |
| S2 | `BFSFinder` | a search that cannot wire >1 input | **a `selection_policy` value**, not a method — `CORE_CR_FINDER_AS_CAPACITIES.md` | C3R3 |
| S3 | `mindsos_server/pipeline_runner.py` | REPL pipeline running, in L0 | `execute_pipeline` | C3R4 |
| ~~S4~~ | ~~`PipelineNotFoundError`~~ | **[RETIRED]** replaced by `FindVerdict` — CORE-C3R1, squash `ae63aa2`, tag `find-verdict-confirmed`. Struck here at C2R2 as register bookkeeping (§9's rule: updated on every ship); the ship is C3's | — |
| S5 | `learned-pipelines` + opaque blob | taught-pipeline storage | one normalised pipeline store | C2R4 |
| S6 | `SubgoalTemplate` | a milestone set | links from `request_knowledge` | C2R7 |
| S7 | `Milestone.sequence_index` | sibling ordering | dependency links on the plan | C2R6 |
| S8 | `MAX_DEPTH = 3` | a brain's test artifact | the confidence stopping rule | C4R3 |
| S9 | `PlanResult` endpoint dicts | the plan's targets | the milestone tree at the plan level | C2R6 |
| S10 | `chain_level = plan_subtree` | branch-level blame | the planning loop | C4R2 |
| S11 | `phase1_v0` / `planning_v0` / `orchestration_v0` (13 caps) | the real catalogs | C4R3, C4R7, C4R8 | C4R7 |
| S12 | `DuckSession` ×3 (brain-side) | a minimal Local session | core L0 primitive | C5R1 |
| S13 | `Session.for_testing` | test-only Session construction | folds into S12 | C5R1 |
| ~~S14~~ | ~~`mindsos_capacity/types.py`~~ | **[STRUCK]** not a shim and not dead code — it holds the live `SessionArg` / `SessionProtocol` domain layers accept. Do not delete | — |
| S15 | `signal_triage` passthrough | real triage | `decision.signal_to_tier` | C4R8 |
| S16 | `submind` stub resolver | a real resolver | submind arbiter work | separate lane |
| S17 | the **taught-milestone declaration capacity** | Skill-declared milestone content | **the skill-packaging system** | C2R5 (added), packaging (removed) |

**S17 note.** ADR-0205 §7 restricts structural change to Skill install. Hand-declaring a
milestone is structural change outside a Skill, granted as a **temporary exception** (ADR-0206
§am-1.5) because `promoted-pipelines` has no writer, so there are zero Global pipelines and
discovery will return nothing for the foreseeable future. It is the **primary** path in
practice, not a stopgap, and must be specified and tested as such.

**Rules:** a shim with no named replacement is a defect. Its docstring names its
replacement **CR**, never a subsystem or a phase. Deleting a shim is its own commit. This
register lives in the repo and is updated on every ship.

---

## 10. Rename inventory

All renames land **once**, bundled with the schema change that motivates them — never as a
standalone churn pass.

| From | To | In |
|---|---|---|
| `request_patterns` (role) | `request_knowledge` | C2R7 |
| `RequestPattern` (node type) | **`RequestKnowledge`** — it is a request *kind*, not a pattern | C2R7 |
| `promoted-pipelines` + `learned-pipelines` | **`pipelines`** — one store; "promoted" becomes a realm fact, not a name | C2R4 |
| `LearnedPipeline` | retired | C2R4 |
| `edge_sequence` (Pipeline content) | retired — steps are the composition link | C2R4 |
| `SubgoalTemplate` | retired | C2R7 |
| `paired_pipelines` | **retired, not converted** — reached via plan → milestone → pipeline | C2R7 |
| `StepExecutionRecord` | **`CapacityRun`** — the capacity-level trace | C2R4 |
| `chain_artifacts.Pipeline` | **`PipelineRun`** only; the duplicate node goes | C2R4 |
| `chain_artifacts.Milestone` | **`MilestoneRun`** | C2R5 |
| `chain_artifacts.Plan` | **`PlanRun`** | C2R6 |
| `HintSet` | **`Hints`** — a **step** output, so no `Run` suffix | C2R7 |
| `MappingResult` | **`Mapping`** — a **step** output, so no `Run` suffix | C2R7 |
| "layer" (for abstractions) | **abstraction level** | C1R2 |

**Renames land with the schema change that motivates them, never as a sweep** — so each
`<Level>Run` rename lands in its own level's item.

---

## 11. Chats

- **C1** — this chat. Ends after C1R1.
- **C2** — the abstraction substrate. The longest chain and the one everything waits on.
- **C3** — search and find. C3R1 is independent (half shipped). **C3R3 depends only on C3R1, not on C2R7** — only C3R2 (the search capacity) waits on C2R7, so the C3 chat can do the whole finder rewrite while C2 runs.
- **C4/C5** — starts on C5R1, then follows C2 and C3.

Each chat hands off to the next; sequential within a chain, parallel across chains.

---

## 12. Immediate blockers

**Corrected 2026-07-31.** Blocker 1 previously pointed at `OPEN_DECISIONS.md`, **a file that
does not exist** and was never written. The concept questions it stood for are closed in
`confirmation_docs/CORE_C2_DECISIONS.md`; anything still open is listed there under §10.

1. **`chain_level`'s target set** — undefined until `hint` and `map` are settled as steps
   rather than levels (ADR-0205 §am-2). C4R2 cannot be scoped until then. **Does not block
   C2.**
2. **The dream trace-reshape notice** — must go out before C2R6 lands (§7).
3. ~~**STATE.json `recent[]`** for #99 still owed.~~ **[done]**
4. **Worktree teardown** — each chat removes its own worktree before it closes.
5. **Merge `origin/main` into every open lane now** (C3R1 chat). `feat/core-c2` and
   `feat/adr-sweep` were both sitting at `b612c93` when `4fd8baa` shipped. Merge as soon as
   *another* lane ships, not at gate time.
6. **Gate on Linux, never the Mac** (RULES §5). A `docker.sock` path under `/Users/` means
   the run is on the Mac — and it will gate whatever branch that clone happens to be on,
   which has already produced one green belonging to a different lane.

7. **[re-filed 2026-08-01 — dropped by an intervening rewrite] `ADR-0205 §amendment-1.6`
   blocks C2R2.** `Metagraph.remove_graph` refuses if any incident intergraph edge or hyperedge
   is `compositional=True` (Pushback 17-A), and ADR-0202 persists **one chain graph per task**.
   If per-request plan structure is compositional, every task's graph becomes permanently
   unremovable. Compositional is **terminal** — remove, mutate **and deprecate** all raise
   `CompositionalImmutableError`, and the flag cannot flip; the only recovery on record is
   `mindsos metagraph reset --force`. **[C2R2] Half-resolved.** ADR-0205 §am-2.2 already ruled
   the **per-request** half: the trace links with **ordinary, non-compositional** intergraph
   edges, so task graphs stay removable. C2R2 adds that nothing it ships makes a *durable*
   compositional link either — D1 is closed by having no consumer, so no compositional link is
   written before **C2R5**. **The durable half stays open and moves to C2R5**, which writes the
   first one.
8. **[re-filed 2026-08-01] Four orphaned deferrals.**
   `_source_backup/root/mindsos_future_plans.md` no longer exists. It is the filed home of
   Pushback 6-A's compositional escape hatch, the `IntergraphEdge` endpoint-update verb, the
   in-place hyperedge→edge downgrade (P19-A), and Pushbacks 25-B / 31-B / 33-B / 34-B. No
   record survives anywhere.

### 12.1 Start order — updated 2026-08-04

~~⚠ **`input_group` is unowned again.**~~ **STRUCK at C2R2** — the concept is retired, so the
deferred graph form has no subject and blocks nothing. Detail below.

**A0 ✅, C2R1 ✅ and C2R2 ✅ are done.** A0 + C2R1 shipped at squash `0496e7f`, tag
`installed-skills-dual-scope-confirmed`, gate 4472/0. **C2R2 is built** on `feat/core-c2r2`
off `3591add` — P8-A lifted, D1 closed by having no consumer, ADR-0205 §am-3 filed.
**C2R3 is next.**

✅ **`input_group`'s graph form is STRUCK, not owned.** CORE-C3R1 retired the **concept**
entirely — `fold` and `any_of` measured across every repo as **`Arc3` 0 · `nilm` 0 · core 0 ·
`arc1-brain` 1** (`arc_capacities.py:841`, arc1 is moving it to `all_required` ahead of its
merge), leaving `all_required` as the only legal value, which is simply what declaring inputs
means. ADR-0159 §am-1 is superseded and **ADR-0156 §am's deferred graph form is withdrawn, not
deferred — it has no subject.** ⟹ **C2R4 is not blocked.** The retirement is agreed and not yet
built, so **C2R4 does not wait on it**: it builds on "all declared inputs are required" and
carries a gate assertion that no registered capacity declares `fold` or `any_of`, which gives
the retirement a green pre-condition to land against. Withdraws
`CORE_VERIFIED_FINDINGS.md` §12.7.

**[2026-08-05] Who retires the field: the C3 lane.** Resolved with the owner. The *field* is a
declaration attribute on `_CapacityBase` read by `_validate_inputs` at L3 invoke — it is not on
`Pipeline`, so it is not pipeline-level work, and once it is gone the graph form has no subject
to inherit. Retiring it closes **D-A's second half**: `capacity.py`'s early return for `fold`
skips *every* input check, so such a capacity runs on a subset of its declared inputs and reports
success. It is tracked on the **C3R1b** row and is **not built**.

### 12.2 New item — the resource graph (from CORE-C3R1)

Resources (a hand, a burner, an input channel) are a **separate axis** from DataStates and must
not enter the graph the walk searches: the walk answers *can it be done*, a resource constrains
*when*. Agreed with the C3R1 chat:

- an **L2 resource graph**, capacities linked to resources by a **`REQUIRES_RESOURCE`** edge —
  chosen over a declaration field because ADR-0205 forbids topology in properties, and over a
  filtered DataState realm, which is how `input_group` failed;
- two independent flags per resource: **exclusive/shareable** and **attended/unattended**;
- criterion for what *is* a resource: **it is given back**; a DataState is transformed or
  consumed. Declared per capacity;
- **duration is a learned parameter** — the shipped `learn_parameter` + `learned-parameters`
  role, not a declared field and not a new mechanism;
- **`REQUIRES_RESOURCE` is NON-compositional.** Capacity and resource both sit at or below the
  capacity level, so this is not a part-whole reading — same class as C11's `SPECIALIZES` under
  ADR-0205 §am-1.3 (Ruling A). Compositional would also pin the resource graph permanently
  unremovable (§am-1.6);
- **dual-scope, both realms bootstrapped up front.** *"This kitchen has two burners"* is user
  knowledge, and adding the second realm later changes a closed role set and forces a migration
  (`CORE_C2_DECISIONS.md` §6, the same call made for milestones). Role count **16 → 17** —
  asserted in six test files (`tests/phase_07/test_bootstrap.py:30`,
  `tests/dataset_role/test_dataset_role_core.py:73,74`, `tests/phase_13/test_dispatch.py:100`,
  `tests/learned_pipelines/test_learned_pipelines_core.py:76`,
  `tests/phase_50/test_installed_skills_substrate.py:57`,
  `tests/phase_50/test_skill_install_local_scope.py:130`);
- **an unrunnable-but-reachable route is L4's to filter**, after the verdict. The walk stays
  resource-blind and returns `found=True`; scheduling defers or rejects. No sixth verdict reason.

**It ships as its own item immediately after C2R3, not inside it** — C2R3's scope is the link
read/write path plus the traversal primitive, and bundling a new role, a new edge type and a
resource criterion into it makes the C2R3 gate result unattributable (`CORE_C2_DECISIONS.md`
§12.4). It is C2R3's **first consumer**, which is what ADR-0205 §Alternatives item 5 asks for.

---

## 13. Items opened 2026-08-10 (plan-audit lane)

Five things this plan did not own. Each was agreed with the owner; none is built. The pattern
they share is the one this project keeps logging — **work that is a consequence of a ruling, and
therefore in nobody's scope**. Evidence: `confirmation_docs/_to_delete/` boundary coordination
(chat scratch, never committed) and the two decision records named per item.

### 13.1 C2R3a — atomic whole-composition delete

**The problem.** `remove_intergraph_edge` / `remove_intergraph_hyperedge` refuse every removal
when `compositional=True`. That guard exists for Pushback 6-A's reason: an identity must not be
**unwound** after dependents exist. It also blocks **destroying a composition whole**, which is a
different operation. So today a pipeline, milestone or plan can never be deleted — only hidden —
and Local grows monotonically.

**The ruling.** §am-1.5's *"taught structure can never be removed"* conflates the two.
`INTERGRAPH_EDGES_DESIGN.md` §4.3 and 6-A both describe the composition **surviving in an altered
form** while something points at it. Destroying it whole, when nothing anchors its members, is not
that operation and 6-A's ground does not reach it.

Replacement text for §am-1.5:

> A composition's membership can never change, and a composition cannot be unwound while anything
> depends on it. A composition **can** be destroyed, but only whole, and only when nothing else
> anchors any of its members.

**Scope.**

- One operation: remove a compositional link **and the members no other composition anchors**, in
  a single transaction. Refuse if any member is anchored elsewhere, or if the composition is
  itself a member of one not also being removed.
- `remove_intergraph_hyperedge` keeps refusing piecemeal removal. **6-A stays closed.**
- The exclusivity check **is `walk(UP)`** — C2R3's invalidation walk, one more consumer, not a
  second implementation.
- Provenance links (§13.2) are anchored on the deleted element and go with it.
- `remove_graph`'s compositional precheck refuses only when a compositional edge **crosses the
  graph boundary**, not on any incident one. A fully contained composition is coherent to remove.

**Why derived dormancy is untouched.** §am-3.3's dormancy triggers on a member that cannot be
resolved. This is the one removal that provably never produces one — it refuses when a member is
anchored elsewhere, so nothing is left pointing at nothing, and after deletion there is no
composition left to be dormant. Dormancy's *current* trigger is the `Graph.remove_node` defect
(`CORE_VERIFIED_FINDINGS.md` §14.2) — an accident, not the mechanism.

**Depends on:** C2R3 (the walk and its index). **Owner: unassigned.**
Accepted as a consequence by the C2R3 chat, which declined it as C2R3 scope and stated that
**whoever builds it owns the §am-1.5 withdrawal**, with the argument written, not just the
capability. That argument is the two paragraphs above.

### 13.2 C2R3b — attribution is a provenance edge; the ledger is deleted

**The problem.** §8a item 7 hands skill-packaging a **ledger**: a record of every node and link
each Skill installed, so uninstall can subtract it. A ledger is a parallel copy of graph structure
held outside the graph — the shape ADR-0205 §5 prohibits — and §8a granted it an exemption nobody
argued for.

Its stated justification is wrong twice. *"The ledger is what makes uninstall work across realms,
which the walk cannot do"* — but a ledger records what a Skill **added**, not what the user
**built on top of it**, so it answers a different question than the one used to justify it. And
ADR-0205 §am-4 rules one `Metagraph` per user, so the realm boundary the argument rests on no
longer exists.

**The ruling.** Every node and link a Skill installs carries a **provenance link to the Skill
record**. Attribution is a link read. Uninstall walks those links. **Provenance links are not
themselves provenanced** — they are created by the same install as their subject, so a second one
carries no information.

Same criterion as ADR-0192, which refused a stored `fundamental` boolean because the `PRODUCES`
topology already encoded it.

**Consequences.** §8a item 7 is struck. **Attribution is core-owned, not skill-packaging's** —
§8a item 5 and item 9 stand. `installed-capacities` stops being the attribution mechanism;
`driver.py:324`'s `installed_by` stamp on Global L2 content nodes is superseded, not extended.
C2R3's attribution clause moves here.

**Depends on:** C2R3. **Owner: unassigned.**

### 13.3 The Global-update migration

**The problem.** Nobody owns what happens to a user's work when Global updates. A user teaches a
pipeline over capacities the system shipped; the system replaces those capacities; nothing in this
plan says what becomes of the pipeline. Today it breaks silently.

**The ruling.** Global **prunes** — it is the shipped baseline and must not accumulate every
version ever released, or every installation pays for elements it never used. The user carries
their own legacy, not the platform.

The copy must precede the prune, so **the update package carries the outgoing versions as well as
the new ones**. It is a transient input, discarded when the update completes; **Global retains
nothing**.

Migration is **version-driven and idempotent**, not event-driven. Global carries a baseline
version; each Local records the version it was last migrated to. One mechanism, two callers — the
update, and boot as the catch-up. Crash-safe and resumable.

1. The package carries the new elements **and** the outgoing versions of everything it replaces.
2. Replace Global; bump the baseline version.
3. Run the migration for each reachable Local.
4. Discard the artifact.

Per Local, idempotent and safe to re-run:

5. If the Local's recorded version equals Global's, **stop**. The normal case, one read.
6. Walk that Local **upward** from each replaced element, collecting the affected chain.
7. **Copy** each replaced element into that Local as a **new** element from the artifact,
   recording the original identity and version for provenance. Under ADR-0205 §am-4's one
   metagraph this is minting a node with `realm=local`, not a transfer between stores.
8. **Rebuild** each affected Local ancestor as a **new** element over the copies, bottom-up —
   members are frozen, so an existing composition can never be repointed.
9. **Atomically delete** the old chain top-down, with §13.1's exclusivity check.
10. Record Global's baseline version on the Local.
11. Notify the user that newer versions exist in Global.

At boot: run step 5. Normally a no-op; catches an interrupted or missed update.

**Copy downward, rebuild upward, delete the old chain whole.** Local-on-Local structure is
untouched. Updates apply **in sequence**, each package self-contained — a cumulative artifact and
a minimum-supported-version floor were both rejected.

**Use deterministic identity for migration copies** — derived from the original identity plus the
version migrated from, not minted fresh. Without it a crash between steps 8 and 9 re-runs the
whole migration and produces a second set of copies, so step 5's idempotency is nominal rather
than real.

**Rejected: append-only Global.** It costs nothing at update time but makes every installation
carry every superseded element forever, and it leaves the user's obsolete dependency working
silently with no forcing function. **Rejected: copying at Global-update time by checking each
user.** It requires reading every Local during an admin action, cannot reach a Local that is not
resident, and writes into private user stores from an admin operation.

**Depends on:** C2R3a, C2R4. **Must land before the first Global release that replaces anything.**
**Owner: unassigned.**

### 13.4 ADR status is two fields

**The problem.** `status:` answers two uncorrelated questions at once — *is this decision agreed*
and *is it built*. 154 ADRs read `Accepted` while almost nothing above the capacity level exists,
so `Accepted` already means *agreed*, de facto, and there is no word left for *built*.

The concrete failure: ADR-0205 §am-1 said *"flips to Accepted with CORE-C2R1"*, C2R1 shipped
without touching the primitive, and the flip was missed until C2R2 caught it. **The instance is
fixed; the pattern is still in §am-2 and §am-4**, both of which say "flips to Accepted with
`<item>`".

**The ruling.**

- **`status:`** records agreement only — `Proposed` → `Accepted` → `Superseded` / `Withdrawn`. It
  flips when someone has read the ADR against the code it governs. **Never on a ship.**
  ⟹ **Delete the "flips to Accepted with `<CR>`" pattern.**
- **`implemented:`** is a new front-matter field: a tag, or `none (<CR id>)`.
- Amendments carry `**Amendment status:**` and `**Implemented by:**`.
- Shipped = `status: Accepted` + `implemented: <tag>`.
- **Guard:** `tests/test_adr_status_consistency.py` gains a check — if `implemented:` names a CR
  it must exist in this plan; if it names a tag, the tag must exist. Per RULES §9 the check ships
  with a test that makes it go **red**.

**Two side findings.** `Deferred` is in use on 13 ADRs and is defined nowhere — RULES §9 lists
only `Proposed` and `Superseded`. And the checker enforces README-row agreement only, so **any
status string passes today**.

**Depends on:** nothing. **Can start immediately. Owner: unassigned.**

### 13.5 C1R5 — C1R4 part 2, split by kind

**The problem.** `CORE_ADR_CONTRADICTION_SWEEP.md` lists 21 ADRs that contradict ADR-0205 and 9
that would if built. Writing the per-ADR amendments is "part 2" and is unstarted. §11 says the C1
chat ends after C1R1, so no chat owns it, and the header's "C1 shipped" is false.

**The ruling.** Two different things were bundled:

- **Status truth** — an ADR that contradicts the governing ADR must not read `Accepted`. Mechanical,
  no reasoning, one commit, all 21.
- **The replacement design** — lands in the ADR with the item that builds the new form, per §0.1.

A batched 30-amendment docs commit reproduces the failure that created this: text written without
being read against the code it governs.

⚠ **The mechanical sweep must skip any ADR whose Decision is *replaced* rather than *qualified*.**
Those are `Superseded` and need a successor ADR, and a mechanical pass cannot tell them apart.
**ADR-0148 is one of them** — §am-4 rules against metagraph-qualified endpoints and the primitive
question is being settled at C2R3, so its Decision paragraph does not survive as written.

**Depends on:** nothing. **Can start immediately. Owner: unassigned.**

---

### 13.6 Two code findings, verified 2026-08-09

1. **`_has_intergraph_edge` (`mindsos_capacity/capacity_layer.py:98`) scans
   `iter_intergraph_edges()` linearly on every edge write** — O(E) per edge, O(E²) per
   registration batch, in the only live writer of intergraph edges (`:415-433`, the ADR-0156
   bipartite `PRODUCES`/`CONSUMES` topology the finder walks). C2R3's index removes it; the new
   existence check must not inherit it. Same root as `CORE_VERIFIED_FINDINGS.md` §14.3.
2. **`feat/capacity-two-tier-resolution` overrides by IRI collision** — `resolve_declaration`
   (`:547`) returns *"the owner's Local override when one exists, else Global"*, and `invoke`'s
   docstring says Local wins *"on a collision"*. **Under §am-4's one metagraph the same IRI cannot
   exist twice, so neither half survives** — there is nothing to shadow and no two stores to
   union. `LocalPreferringView` (`8400d6f`, ADR-0071 §am-5) has no referent. **The requirement
   survives, the class does not**, and what replaces it is ruled by §am-4 §3: *an override is
   topology, never identity* — owner-qualified IRIs refused, and an override never redirects an
   existing composition.
