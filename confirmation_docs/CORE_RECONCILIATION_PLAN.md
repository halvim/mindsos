# CORE reconciliation plan (CORE-C chains)

**Filed:** 2026-07-31. **Revised** after the abstraction-levels conclusion.
**Status:** approved. **C1 shipped** (`df8d3a5`). **C3R1 half-shipped** — see §4.
**Revised 2026-07-31** by the C3R1 chat: corrections in §2, §3, §4, §9, §11 are marked
`[corrected 2026-07-31]` and were verified against the code, not inferred.
**Reads with:** `CORE_CONCEPT_PLANNING_AND_CONFIDENCE.md` (the model),
`CORE_VERIFIED_FINDINGS.md` (the evidence), `OPEN_DECISIONS.md`.

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
| **C1R1** | Extract the `MindsOS-core` rows out of WSD slots 51–56; fix the 16 wrong `mindsos_*` docstrings; land these documents + the shim register. ~~delete dead `mindsos_capacity/types.py`~~ — **[corrected 2026-07-31] not done, and correctly so:** `types.py` holds the live `SessionArg` / `SessionProtocol` that domain layers accept. It is not dead code and must not be deleted; **shim S14 is struck** (§9). C5R1's session primitive lands in `mindsos_server` and `types.py` keeps the protocol |
| **C1R2** | **ADR — abstraction levels.** The governing idea: one graph at several resolutions, each composed of the level below and verifiable by it. Fixes the vocabulary (*abstraction level*; `capacity / pipeline / milestone / plan / request`) |
| **C1R3** | **ADR — planning, decomposition and confidence.** The loop, the stopping rule, relational confidence, "I'm not sure". Closes POST_PHASE_38 q4 |
| **C1R4** | **ADR contradiction sweep.** **[part 1 SHIPPED 2026-08-01 `2c56246` PR #104]** Six passes; the per-ADR framing did not converge, a code sweep did. Output = **ADR-0205 §amendment-1** (Proposed → Accepted at C2R1) + the coverage ledger `CORE_ADR_CONTRADICTION_SWEEP.md`. Criterion gained a **scope clause**; composition primitive is **arity-selected**; subsumption is **not** composition; compositional is **terminal**. **Part 2 owed:** the per-ADR amendments — 21 `contradicts` + 9 `contradicts-if-built`, listed with evidence and liveness in the ledger |

---

## 3. CORE-C2 — the abstraction substrate

> **[corrected 2026-07-31] ID collision — read before citing a C2 id.** This table numbers
> `installed-skills` dual-scope as **C2R0** and the P8-A amendment as **C2R1**.
> `STATE.json` and the chat prompts number `installed-skills` as **C2R1**. Two different
> items are called C2R1 depending on which artifact you read. **Cite C2 items by name, not
> by id, until the C2 chat renumbers this chain** — it owns the chain, so the C3 chat did
> not renumber it unilaterally. First C2 chat: settle it and delete this note.

| ID | Scope | Depends on |
|---|---|---|
| **C2R0** | **`installed-skills` becomes dual-scope.** Today it is Global-only (ADR-0150 §am-6) while `installed-capacities` is Local-only — an asymmetry that makes skill install effectively **admin-only**. Under the model a **user installs a Skill Local**; an admin promotes it to Global. Role bootstrap + `CAN_INSTALL_SKILL` semantics. **Cheapest high-value item in the plan** — it is the precondition for everything in the model being user-driven, and it depends on nothing | — |
| **C2R1** | Amend **P8-A**: permit `compositional=True` with `ordered=False`. *(No alternative-relation work — OR is several compositional edges sharing an anchor; see concept §0.5.1)* | C1R2 |
| **C2R2** | **The milestone graph** — a new abstraction level. Milestone nodes anchoring compositional hyperedges over the pipelines they are hubs of | C2R1 |
| **C2R3** | **The pipeline level** — one pipeline store named **`pipelines`**, normalised, no structural blob. Retire `learned-pipelines` and `promoted-pipelines`; `status` carries provenance | C2R1, C1R4 |
| **C2R4** | **The plan level** — Milestone declares its target DataState; parent/child and sibling relations become edges; `PlanResult` stops being a second description; `sequence_index` and `MAX_DEPTH` retired | C2R2 |
| **C2R4a** | **Skill isolation / attribution.** Any element answers "which Skill(s) do I depend on?", so uninstall knows its blast radius and a user can be told what they lose. **[corrected 2026-07-31] Declared footprint does NOT work — the claim below was false.** The driver never writes `installed-capacities`: `mindsos_server/boot.py:322` states the role is "empty until" a user-scoped install exists, and `skills/driver.py` stamps `installed_by` on **Global L2 content nodes** (`:285`) and filters *those* on uninstall (`:416`). The `installed-capacities` schema and IRI minting ship; nothing populates them. So ADR-0183 §am-5's Local half is **specified and unbuilt**, which is the real hole C2R1/C2R0 sits on. **Derived footprint is a graph walk up the abstraction levels**, not a new store. Dependency is **many-to-many**; **dormancy is per-dependency** ("which of my dependencies are missing"), never a boolean | C2R2, C2R3 |
| **C2R5** | **`request_knowledge`** — rename from `request_patterns`; `relevant_hints` and `paired_pipelines` become edges; confidence moves onto those edges; `SubgoalTemplate` retired | C2R3, C2R4 |

---

### 3.1 One traversal primitive, not four

Four things in this plan are the **same upward walk** over the abstraction levels:

1. **Invalidation** — a capacity is removed; what above it is affected?
2. **Hub discovery** — which DataStates are coincident across pipelines?
3. **Verification** — does this level still hold against the level below?
4. **Attribution** — which Skills does this element depend on?

They must share **one traversal primitive**, designed before any of them is written.
Four separate implementations of the same walk is how the four "topology in properties"
instances happened.

---

## 4. CORE-C3 — search and find

| ID | Scope | Depends on |
|---|---|---|
| **C3R1** | **[HALF SHIPPED 2026-07-31 — `4fd8baa`, tag `finder-cycle-guards-confirmed`, gate 4450/0]** Done: the two phase-2 cycle guards — **D-B** (self-feeding producer) and **D-E** (a capacity under construction, *new*, returned a Pipeline with the same capacity twice and reported success). ADR-0071 §am-3. **Not done:** the `find_verdict` type replacing `PipelineNotFoundError` (5 closed reasons, `(capacity, datastate)` pairs, no `__bool__`, faithful conversion with **no new checks**) and the divergence sweep in `catalog_check.py` (sources × producible targets, self-feeding from the existing x-ray). | — |
| **C3R2** | **The search capacity** — look up known pipelines in L2, read the confidence off the edge, compare to threshold. A capacity, so `CapacityContext.kl` makes the layering problem moot | C2R5, C3R1 |
| **C3R3** | **[corrected 2026-07-31 — MERGED INTO the finder-as-capacities CR]** Producer-choice seam: record alternatives, selection as a policy; `BFSFinder` retired. The seam is now `decision.select_producers`, one of the four capacities in `CORE_CR_FINDER_AS_CAPACITIES.md`, and BFS becomes a `selection_policy` **value** rather than a method. C3R1's remainder and C3R3 are one item. | C3R1 |
| **C3R4** | **The find capacity** (Plan → Pipeline); `find_pipeline` and `mindsos_server/pipeline_runner.py` retired | C3R3 |

---

## 5. CORE-C4 — the planning loop

| ID | Scope | Depends on |
|---|---|---|
| **C4R1** | **Hub calculation** — coincident DataStates across pipelines. *No separate index: the milestone graph (C2R2) materialises it.* Scope is the **update trigger** — recompute affected hubs on learn, dream sweeps the rest | C2R2, C2R3 |
| **C4R2** | **Confidence fields**, all transitions, in one deliberate change. Reconcile `chain_level` to the ladder (`plan_subtree` is retired — the loop covers it) | C1R3, C2R4 |
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
- **Dream chat:** deeper plan trees are coming (C2R4, C4R3); candidate selection needs a
  *completed-while-unsure* category (C4R5); PRE-5 (finder exposing alternatives) lands at
  C3R3. No file overlap with C1–C3; C4 touches `plan_construction.py` and `orchestrator.py`.
- **A future WSD chat:** §8.
- **A future skill-packaging chat:** §8a. A Skill spans all abstraction levels, so the
  bundle format must be able to declare milestones and request knowledge — which do not
  exist as roles until C2R2 and C2R5. Skill packaging therefore sequences **after** the
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
   which cannot be declared until C2R2 and C2R5 ship. Sequence after them.
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
7. **Skill isolation is yours to design, on core's C2R4a substrate.** Core provides the
   attribution walk and the dormant state; you decide the uninstall UX, the opt-in to
   remove user data, and what a Skill reports about its footprint.
8. **Core hands you C2R0** — `installed-skills` made dual-scope so a user can install
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
| S2 | `BFSFinder` | a search that cannot wire >1 input | **[corrected 2026-07-31]** a `selection_policy` **value**, not a method — see `CORE_CR_FINDER_AS_CAPACITIES.md` | C3R3 |
| S3 | `mindsos_server/pipeline_runner.py` | REPL pipeline running, in L0 | `execute_pipeline` | C3R4 |
| S4 | `PipelineNotFoundError` | a technical failure that isn't one | an honest don't-know verdict | C3R1 |
| S5 | `learned-pipelines` + opaque blob | taught-pipeline storage | one normalised pipeline store | C2R3 |
| S6 | `SubgoalTemplate` | a milestone set | edges from `request_knowledge` | C2R5 |
| S7 | `Milestone.sequence_index` | sibling ordering | dependency edges | C2R4 |
| S8 | `MAX_DEPTH = 3` | a brain's test artifact | the confidence stopping rule | C4R3 |
| S9 | `PlanResult` endpoint dicts | the plan's targets | the Milestone tree | C2R4 |
| S10 | `chain_level = plan_subtree` | branch-level blame | the planning loop | C4R2 |
| S11 | `phase1_v0` / `planning_v0` / `orchestration_v0` (13 caps) | the real catalogs | C4R3, C4R7, C4R8 | C4R7 |
| S12 | `DuckSession` ×3 (brain-side) | a minimal Local session | core L0 primitive | C5R1 |
| S13 | `Session.for_testing` | test-only Session construction | folds into S12 | C5R1 |
| ~~S14~~ | ~~`mindsos_capacity/types.py`~~ | **[STRUCK 2026-07-31]** not a shim and not dead code — it holds the live `SessionArg` / `SessionProtocol` domain layers accept. Do not delete | — |
| S15 | `signal_triage` passthrough | real triage | `decision.signal_to_tier` | C4R8 |
| S16 | `submind` stub resolver | a real resolver | submind arbiter work | separate lane |

**Rules:** a shim with no named replacement is a defect. Its docstring names its
replacement **CR**, never a subsystem or a phase. Deleting a shim is its own commit. This
register lives in the repo and is updated on every ship.

---

## 10. Rename inventory

All renames land **once**, bundled with the schema change that motivates them — never as a
standalone churn pass.

| From | To | In |
|---|---|---|
| `request_patterns` (role) | `request_knowledge` | C2R5 |
| `RequestPattern` (node type) | TBD — it is a request *kind*, not a pattern | C2R5 |
| `promoted-pipelines` + `learned-pipelines` | **`pipelines`** — one store; "promoted" becomes a realm fact, not a name | C2R3 |
| `LearnedPipeline` | retired | C2R3 |
| `SubgoalTemplate` | retired | C2R5 |
| "layer" (for abstractions) | **abstraction level** | C1R2 |

---

## 11. Chats

- **C1** — this chat. Ends after C1R1.
- **C2** — the abstraction substrate. The longest chain and the one everything waits on.
- **C3** — search and find. **[corrected 2026-07-31]** C3R1 is independent (half shipped). **C3R3 depends only on C3R1, not on C2R5** — only C3R2 (the search capacity) waits on C2R5. The C3 chat can do the whole finder rewrite while C2 runs.
- **C4/C5** — starts on C5R1, then follows C2 and C3.

Each chat hands off to the next; sequential within a chain, parallel across chains.

---

## 12. Immediate blockers

1. **Open decisions** — `OPEN_DECISIONS.md`. C4 cannot start until the concept questions
   close.
2. ~~**STATE.json `recent[]`** for #99 still owed.~~ **[done]**
3. **Worktree teardown** — each chat removes its own worktree before it closes.
4. **[added 2026-07-31] Merge `origin/main` into every open lane now.** `feat/core-c2` and
   `feat/adr-sweep` were both sitting at `b612c93` when `4fd8baa` shipped. The recorded
   lesson is to merge as soon as *another* lane ships, not at gate time.
5. **[added 2026-08-01] `ADR-0205 §amendment-1.6` blocks C2R2.** `Metagraph.remove_graph`
   refuses if any incident intergraph edge or hyperedge is `compositional=True`
   (Pushback 17-A), and ADR-0202 persists **one chain graph per task**. If per-request plan
   structure is compositional, every task's graph becomes permanently unremovable.
   Compositional is terminal — remove, mutate **and deprecate** all raise
   `CompositionalImmutableError`, and the flag cannot flip. Three options are recorded in the
   amendment; **none is chosen**. The C2 chat decides this *before* building the milestone
   graph.
6. **[added 2026-08-01] Two `_source_backup` orphans.**
   `_source_backup/root/mindsos_future_plans.md` no longer exists. It is the filed home of
   Pushback 6-A's escape hatch, the `IntergraphEdge` endpoint-update verb, the in-place
   hyperedge→edge downgrade (P19-A), and Pushbacks 25-B / 31-B / 33-B / 34-B. No record
   survives anywhere.
