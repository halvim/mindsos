# CORE-C2 — decisions taken before building

**Filed:** 2026-07-31, CORE-C2 chat. **Closed** 2026-08-01.
**Verified at:** `origin/main` `b612c93`; reconciled at `2c56246`.
**Status:** **A0 + C2R1 SHIPPED** — squash `0496e7f` (PR #107), tag
`installed-skills-dual-scope-confirmed`, merged-state gate **4472 / 12 skip / 1 xpass / 0
fail**, `test_cli` 256. **C2R2 onward not started.** **One decision is reopened and C2R2
opens with it — read §2's note before acting on D1.** §12 records what shipped and what the
build taught.

**Revision 6.** Reconciled at `origin/main` `2c56246` with two lanes that shipped mid-chat —
the C3R1 ship and the C1R4 sweep; **see §11**, and read §2's reopening note before acting on
D1. Revision 4 settled ordering per level. Revision 3 rejected revision 2's chain proposal
(§7). Revision 1 framed every abstraction level as a *store* — a new node type in
a new L2 role with a field schema. That is ADR-0205's **rejected Alternative 2**
(*"A separate registry per level. Rejected — a registry grants a level's topology different
trust from the edges beside it, and the finder already reads all topology from graph
edges."*). Revision 1 proposed five registries. §1 below replaces that reading; every
decision after it is restated against the corrected model.

---

## 1. What an abstraction level actually is

ADR-0205 §1 states one graph seen at several resolutions:
`capacity → pipeline → milestone → plan → request`, each composed of the level below and
verified against it. §2 makes the composition primitive `IntergraphHyperEdge` — the
**inter**graph primitive, anchors in one graph, members in another.

That choice already answers where the levels live. **"One graph" means one ground truth and
one way of reading topology, not one `Graph` object.** The metagraph is what makes them one.

> **A level is not a store. A level exists because a compositional intergraph link exists.**
> A node anchors a link whose members are nodes at the level below; that link *is* the
> coarser resolution.

| Level | Graph | What makes it that level |
|---|---|---|
| capacity | the bipartite capacity graph (ADR-0156) | ground truth; no link |
| pipeline | pipeline graph | link over capacity-graph nodes |
| milestone | milestone graph | link over pipeline nodes |
| plan | plan graph | link over milestone nodes |
| request | request graph | link over plan nodes |

**This is not the rejected alternative.** A registry is read differently from the edges
beside it. These are read by the same walk as everything else — the finder reads edges, the
traversal primitive reads links, same mechanism at a different grain. The distinction is
checkable: a registry has a field schema describing structure; a level graph has thin nodes
and all structure in links.

**ADR-0206 §1's "milestones must never become nodes in the capacity graph" is satisfied for
free.** A milestone is in the milestone graph. The capacity graph stays exactly the
bipartite topology the finder walks.

**The nodes are thin.** A milestone node carries an identity and a link to the DataState it
targets. Nothing else. No `parent_ref`, no `children_refs`, no `sequence_index`, no
`paired_pipelines`, no `relevant_hints`, no `edge_sequence`, no `hints` blob. Every one of
those is structure, and structure is links.

**The declaration rule is automatic.** A declared level requires the level below — because
the link *is* the level. A node with no link is not at any level. There is nothing to
validate; it cannot be constructed.

### 1.1 The acceptance test — replaces the vaguer form

> **Walk from a node at this level to its members one level down, and back up, reading only
> links. If any part of that walk reads a property, the level is not built.**

This supersedes "does the code match the concept?" as the gate for every level item. That
question remains the gate for the non-level items.

### 1.2 Depth comes from alternation, not from new levels

A plan is a link over milestones. Decomposing one of those milestones means **that milestone
anchors its own plan-link over child milestones**. The tree grows
plan → milestone → plan → milestone, and every rung is one of the five resolutions.
**Decomposition adds depth inside the plan level; it never adds a level.**

⟹ The milestone tree is **not** information the milestone level holds. It is the plan's own
structure (ADR-0206 §2: parent→child is decomposition, sibling→sibling is dependency), and
it lands at the plan-level item.

⟹ `Milestone.sequence_index`, `parent_ref` and `children_refs` are wrong three ways at once:
structure held as properties, on the wrong node, at the wrong level.

---

## 2. D1 — compositional links: membership frozen, properties editable

**The conflict.** ADR-0205 §2 makes `IntergraphHyperEdge(compositional=True)` the
composition primitive at every level. ADR-0206 §5 puts confidence on the link and has ALS
move it; ADR-0206 §1 recomputes hub membership on every learn; ADR-0205 §8 has skill
uninstall remove what install added. The code refuses **all three**:
`Metagraph.remove_intergraph_hyperedge` and `update_intergraph_hyperedge*` raise
`CompositionalImmutableError` when `compositional=True`, with no escape hatch
(`metagraph.py:1982`, Phase 05b pushback **6-A** — *"recovery is `metagraph reset`"*).

**The original motivation, recovered.** ADR-0148: when the flag is on the link is
**identity-bearing** — the composition *is* the bound whole. Changing its members would turn
one entity into a different entity under a fixed identity. Pushback 6-A then removed the
demote verb so an identity could not be unwound after dependents existed.

**The reason is sound and it is narrow.** It constrains *membership*. It says nothing about
a number attached to the link, and nothing about whether the assertion is still in force.

> ⚠ **REOPENED at `2c56246`.** The C1R4 sweep (ADR-0205 §am-1.5) independently confirmed
> compositional terminality and resolved it the other way — leave the primitive alone, and
> note that **node** properties (`Pipeline.status`, provenance) are unaffected. That works
> only if confidence lives on nodes, which ADR-0206 §5 rejects by name. A third option
> neither chat wrote down: **keep compositional links terminal and carry confidence and
> `in_force` on a separate ordinary link beside each composition.** ADR-0206 §5 keeps
> confidence on a link, the core invariant is untouched, and no Phase-05b pushback is
> reopened. **This is now the recommended resolution.** Not decided; **C2R2's subject.**
> **A0 deliberately does not carry D1** — nothing built so far depends on it.

**Decision (as originally taken — see the note above).** Amend the immutability rule to
**block membership only**:

| Aspect | Compositional | Rationale |
|---|---|---|
| `members` / `anchors` | **frozen** | ADR-0148 identity-bearing; unchanged |
| existence (removal) | **frozen** | pushback 6-A; unchanged |
| `properties` | **editable** | never part of the identity |

Confidence and an `in_force` flag are properties, so both become writable without touching
what the composition *is*. Retirement, supersession, dormancy and skill uninstall are all a
**property flip, never a delete** — which is exactly the dormancy ADR-0205 §8 specifies.
This gives ADR-0205 §7 ("structure is stable; learning moves confidence") an exact
mechanism: **frozen members = structure; editable properties = learning.**

**Membership grows by accumulation, not update.** A new pipeline reaching an existing
milestone is a **new link on the same anchor** — which ADR-0205 §3 already calls
alternatives. Frozen members and growing membership are the same mechanism, not two.

**Rejected:** full reversal of the ban (discards a sound reason, and under D4 it would apply
to every pipeline); leaving the ban intact and routing all change to a second parallel link
(a second link per composition purely to hold a number, and reads then reconcile two).

**Amends:** ADR-0148, Phase 05b pushback 6-A (partial — removal survives).

---

## 3. D2 — a milestone is a node at the milestone level

**The conflict.** ADR-0206 §1 says a milestone **is** a DataState and needs "no new
declaration type". ADR-0205 §1 puts the milestone level **above** pipelines. A DataState is
a *member* of pipelines, so under both statements the same node sat above and below the
pipeline level.

**Decision.** A milestone is a **node at the milestone level**. It is neither a DataState nor
a chain artifact. It **references** the DataState it targets and **composes** the pipelines
that reach it — two distinct links to two distinct objects, which ADR-0206 §1 collapsed
into one sentence.

**Wording matters here.** The amendment must **not** say "a milestone is a new declaration
type." Declarations are what capacities and DataStates have — registry entries with field
schemas. That phrasing rebuilds the rejected Alternative 2. What makes a node a milestone is
the link it anchors, not a declared type.

**Consequences.**

- ADR-0206 §1's *"needs no new declaration type"* is **wrong as stated** and is amended —
  but it is corrected toward *a node at a level*, not toward *a declaration type*.
- The per-request `Milestone` in `mindsos_intelligence/chain_artifacts.py` is superseded —
  see §7.
- Hub-ness is how **discovery finds candidates**, not what a milestone *is*. Discovery uses
  the two-or-more-pipelines threshold; a **declared** milestone needs **one** pipeline
  beneath it. A validator written from ADR-0206 §1 alone would reject every declared
  milestone. This must be stated in the amendment.

---

## 4. D3 — the link mechanism is built first, and it is what creates levels

**The conflict.** The plan's central repair is "topology stored in properties must become
edges". The L2 knowledge write path cannot write a link:

- `KLWriteHandle` (`mindsos_knowledge/write_handle.py`) exposes `write_and_validate`,
  `update_and_validate`, `validate_node`, `mint_iri` — **node operations only**.
- `KLWriteHandle.validate_xref` raises `WriteHandleNotWiredError` — deferred at Phase 36
  "alongside the first XRef writer", which never arrived.
- `MetagraphView` reads edges (`get_edges`, `step`) but has no writer.
- `IntergraphHyperEdge` has **zero consumers** in `mindsos_knowledge`,
  `mindsos_intelligence` or `mindsos_capacity` — only `mindsos_cli` and migrations.

**Decision.** Build it first, as its own item. Under §1 this is not plumbing for the
milestone item — **the link is the level.** Without it there are no levels at all, only the
ground graph.

**Scope:** write and read compositional and ordinary intergraph links between role-graphs;
survive save and reload (persister round-trip in the gate, covering the link types every
later item needs, not only the first); and the **traversal primitive**, which is the reading
half — reading links at a grain is what a level *is*.

**The traversal primitive.** It was a deliverable of the milestone item. It moves here,
because it is not milestone-specific.

```
walk(start, *, direction: UP | DOWN, view, stop, visit, max_levels) -> Iterator[Frame]
# Frame = (node, level, link, path, depth)
# UP   = which anchors hold me as a member       (invalidation)
# DOWN = which members does this anchor hold     (verification, attribution)
```

**The plan's §3.1 premise is wrong.** The four consumers are **not** all an upward walk.
Invalidation is UP. Verification is DOWN. Attribution is DOWN then a property read
(`installed-capacities.installed_by`). Hub discovery is an **intersection over a set** — a
*consumer* of `walk(DOWN)` over the pipeline set, not a fifth mode.

**Attribution folds in here.** It answers "which Skills does this element depend on", so
uninstall can say what stops working and dormancy can be per-dependency. It is the DOWN walk
plus `installed_by`.

> **[corrected at `60fe2ae`] `installed_by` does not exist where this assumed.** The C3R1
> chat verified that the driver stamps `installed_by` on **Global L2 content nodes**, not on
> `installed-capacities` — which `mindsos_server/boot.py` says is "empty until" a
> user-scoped install exists. Schema and IRI minting ship; nothing populates them. So the
> DOWN walk lands on content nodes carrying a provenance tag, and ADR-0183 §am-5's Local
> half is specified and unbuilt. **§7a's ledger is therefore built whole, with no existing
> declared half.** Recorded as `CORE_VERIFIED_FINDINGS.md` §12.6. Two named line items remain: the walk must
return **which dependencies are missing**, not a boolean; and uninstall needs to run it
**eagerly** over everything a user built, not lazily on read.

**Invalidation goes live here too, not later.** Under the declaration rule a level needs the
level below, so a milestone becomes unsupported the moment its last pipeline is flipped out
of force. Something must notice. That is the UP walk.

---

## 5. D4 — pipelines convert to the composition primitive

**The conflict.** ADR-0205 §2 makes the compositional link the one way to record "made of".
Phase 13 **PB-9** locked `HAS_STEP` as an ordinary `EdgeType` carrying an advisory
`position` property, explicitly *"NOT an ordered hyperedge"*, on the argument that the
ordering claim is on the *set* of steps from one Pipeline rather than on any single edge.
ADR-0205 never considered PB-9. Separately `promoted-pipelines` carries **both** normalised
`HAS_STEP`→`PipelineStep` **and** an `edge_sequence` content property.

**Decision.** PB-9 falls. Pipeline steps convert to the composition primitive;
`edge_sequence` is retired.

**Consequences.**

- The pipeline-level item gains a **migration** of shipped `promoted-pipelines` data.
- Every pipeline inherits D1. A retired or quarantined pipeline is flipped out of force,
  never deleted. The `status` lifecycle survives as properties, which D1 keeps writable.

**Supersedes:** Phase 13 PB-9.

---

## 6. Milestones — realm, discovery, and the temporary declaration path

- **Both realms bootstrapped, only Local written for now.** Same call as the pipeline store.
  Adding the Global half later would change the closed role set and force a migration.
- **No Global milestones will be discovered for now**, because `promoted-pipelines` has **no
  writer** (verified) — there are zero Global pipelines. Discovery therefore looks only at
  taught pipelines.
- **Declaration is the primary path, not a stopgap.** ARC has taught essentially no pipelines
  through MindsOS — its solver is disjoint from the core by its own docstring. Discovery will
  return nothing there for a long time. The declaration path must be properly specified and
  tested, not sketched.
- **Declaring is a capacity, not a CLI verb.** It writes knowledge into a per-user store; the
  shipped precedent is `learn_parameter`, an L3 write capacity.
- **The §7 exception.** Hand-declaring a milestone is structural change outside a Skill,
  which ADR-0205 §7 forbids. A **temporary exception** is granted, entered in the shim
  register with **"the skill-packaging system"** as its named replacement — satisfying the
  register's own rule that a shim without a named replacement is a defect.
- **ARC prerequisite.** To declare a milestone ARC must first teach a pipeline through
  `learn_pipeline`. It has none. That half is brain-chat work and can start now, in parallel.

### 6.1 When a brain can test

| Point | What a brain can do |
|---|---|
| end of the milestone item | teach a pipeline, declare a milestone on it, read both back, walk the link |
| end of the plan item | read plan structure — parent/child, dependencies, targets |
| **end of C4** (`decompose` real + placeholders deleted) | the first actual planning test |

The lifecycle test cannot come earlier: no brain can run `run_lifecycle` today, because it is
hardwired to the v0 placeholder catalogs, which C4 replaces. Both brains recorded that
blocker independently.

---

## 7. The chain — one trace node per level

**A first proposal — replacing the per-level trace nodes with links from `RequestRun` — was
rejected, correctly.** Links can record *which* durable node was used at each level. They
cannot record **the descent itself**: loaded the plan level, not confident, descended to
milestone, still not confident, descended to pipeline. That sequence is the per-request
reasoning history, and it is the thing ADR-0205 §4 describes:

> *"The Mental Model loads the highest abstraction level and analyses it. If it cannot find
> what it needs, it loads the next level down only for the nodes it needs, and rechecks…
> Confidence decides whether to descend."*

ADR-0205 §11 calls the chain *"the per-request trace across these same levels"* — a trace
across levels means **a record at each level**.

**Decision: one trace node per abstraction level.**

| Level | Durable node | Trace node |
|---|---|---|
| capacity | `Capacity` / `DataState` | **`CapacityRun`** (was `StepExecutionRecord`) |
| pipeline | `Pipeline` | `PipelineRun` |
| milestone | `Milestone` | **`MilestoneRun`** (was the chain `Milestone`) |
| plan | `Plan` | **`PlanRun`** (was the chain `Plan`) |
| request | `RequestKnowledge` | `RequestRun` |
| — | — | `ReplanRecord` — a provenance composite, not a level |

This reverses an earlier ruling that `StepExecutionRecord` was outside the model: it is the
**capacity-level trace**, which is why ADR-0205 §11's list of three execution records never
fitted it. The convention also removes the live collision where `Pipeline` means two
different things depending on which file you are reading.

### 7.1 `Hints` and `Mapping` — steps, not levels

`HintSet` → **`Hints`**. `MappingResult` → **`Mapping`**. Names taken directly from
ADR-0206 §3's step sequence (*request → hint → map → plan*). They are the odd ones out in
`chain_artifacts.py` precisely because they were modelled as levels when they are **steps**;
they attach to the request-level trace and take no `Run` suffix, because neither claims to be
a level.

### 7.2 Node per level does not mean fat nodes

Each trace node holds an identity, a link to the durable node it used, and per-request state.
Everything structural is still links. These remain defects and are fixed in the item that
owns each level:

- `HintSet.hints` — `Dict[str, Any]` holding structure (ADR-0205 §5).
- `StepExecutionRecord.confidence` — confidence on a node (ADR-0206 §5: it is relational).
- `RequestRun.pipeline_runs`, `RequestRun.replan_history`, `ReplanRecord.invalidated_refs`,
  `ReplanRecord.spawned_refs` — reference lists inside records.

### 7.3 Renames land per item, never as a sweep

Plan §10: renames land bundled with the schema change that motivates them. So `CapacityRun`
lands with the capacity-level work, `MilestoneRun` with the milestone level, and so on — not
as one churn pass.

### 7.4 Coordination

The dream lane reads Episodes out of these records. Any reshape needs the dream chat before
it lands.

---

## 7a. Skill attribution — the skill ledger

**Routed to the skill-packaging chat, to be created with the packaging system.** Recorded
here because core's C2R3 must not build the thing it replaces.

**Two sources of truth, answering two different questions. Neither verifies the other, so
nothing is read twice.**

- **The ledger is the only source of truth for *what a skill added*** — which nodes and,
  critically, **which links** it created. An install-time fact, not derivable from the graph
  (nothing in a link says who put it there), and it never changes afterwards. Append-only,
  matching D1's append-only structure. Entries are **modification events**.
  **It is built whole:** the "declared footprint already works" premise was verified **false**
  at `60fe2ae` — `installed-capacities` has a schema and IRI minting and **no writer**
  (`CORE_VERIFIED_FINDINGS.md` §12.6). There is no existing half to extend.
- **The graph is the only source of truth for *what an element depends on*** — its links.
  Live, and moving.

**Uninstalling skill S, for element X:** `X's links − the links in S's ledger` = what X still
has. One read of X's links, one read of S's ledger, subtract. Exact.

**Rejected:** scanning every other skill's ledger per element — that costs one read per
installed skill per element and returns the same answer the subtraction gives in two reads.

**The ledger must not hold confidence.** Confidence is relational, lives on the link, and ALS
moves it constantly. A ledger holding it would need rewriting on every learn, and would give
two confidences that disagree. Same for structure generally: the ledger holds *references to*
what was added, never its shape, or it becomes a parallel copy of the graph (ADR-0205 §5).

**Why a ledger rather than the walk alone.** Invalidation walks **up** from the capacities
being removed. That works inside one metagraph. It cannot enumerate dependents in a
*different realm* — a Global skill's capacities have no reachable path to what a user built
on top of them in their Local store. A per-user ledger solves exactly the case the walk
cannot.

**It collapses a distinction the plan makes.** *Declared footprint* and *derived footprint*
become the ledger and the subtraction — one mechanism, not two. Core's attribution scope
shrinks to the walk C2R3 already builds.

### 7.1 Defect instances this file adds to the count

`CORE_VERIFIED_FINDINGS.md` §11.6 counts three instances of topology-stored-as-properties.
`chain_artifacts.py` alone adds six more, and C1R4's contradiction sweep missed the file:

- `HintSet.hints` — structure in an opaque blob (ADR-0205 §5).
- `StepExecutionRecord.confidence` — confidence on a node (ADR-0206 §5: it is relational).
- `RequestRun.pipeline_runs`, `RequestRun.replan_history`,
  `ReplanRecord.invalidated_refs`, `ReplanRecord.spawned_refs` — reference lists in records.

Plus `promoted_pipelines.edge_sequence` (§5). Real system-wide count is closer to nine.

---

## 8. Four ADR amendments — one docs-only commit, landed first

These are corrections to ADRs that are one day old. Leaving them wrong while C2 builds
against them is precisely the failure ADR-0205 exists to prevent. They land **together, as
one docs-only commit, ahead of every code item** — bundling them with the P8-A code change
would make the gate result unattributable.

**A docs-only commit is still gated.** `tests/test_adr_status_consistency.py` gates ADR
status and cross-references, and the test image copies `docs/` and `confirmation_docs/` into
the container. It is fast, not free.

### A1 — P8-A: a defect fix, not a design change

ADR-0205 §2 grounds the P8-A amendment on *"the original argument could not be recovered —
`PHASE_05c_DESIGN_LOG.md` does not exist."* **False.** The argument survives in
`confirmation_docs/INTERGRAPH_EDGES_DESIGN.md:24`, `PHASE_MAP.md:1489` and
`PHASE_05c_CONFIRMED.md:83`; the file is `PHASE_05c_IMPLEMENTATION_LOG.md`. The ADR set was
never searched.

**The real ground inverts the amendment.** ADR-0148 — the ADR that introduced the primitive —
says compositional intergraph hyperedges are `compositional=True, ordered=False` **by
default**. P8-A does not merely lack a rationale: **it contradicts its own governing ADR and
refuses the combination that ADR declares the default.** C2R2 is therefore *restoring the
ADR-0148 contract a later phase silently reversed* — a defect fix, cheaper to justify.

Two cautions: ADR-0148 is itself a reconstructed record (it says so), so cite **the glossary
amendment it points at**, not only the ADR. And `ordered=True` compositional must stay
expressible — the Phase 05c fixture is `cat = c+a+t`, which genuinely needs order.

Also inaccurate: §2 says `ordered=False`'s *"only real effect is factory dedup."*
`mindsos_core/schema/types.py:166` **sorts and dedups** at construction.

**Action:** strike the "could not be recovered" paragraph; cite ADR-0148 + its glossary
amendment; correct the dedup sentence. **Prerequisite for C2R2.**

### A2 — ADR-0206 §1: the milestone

Amend per §3 above. **Prerequisite for the milestone-level item** — that is where the
contradiction bites. Three things it must state:

1. The **node-at-a-level** framing, not "declaration type".
2. The **one-pipeline** threshold for a declared milestone; two-or-more is how *discovery*
   finds candidates.
3. **One link per pipeline, not one link over all coincident pipelines.** §1 currently says
   *"its compositional members ARE the pipelines it is coincident in"* — plural, one link.
   D1 forces the opposite: members are frozen, so a milestone that later gains a pipeline
   must gain a **new link on the same anchor**, which ADR-0205 §3 already calls alternatives.
   Alternative routes to a milestone are an OR, and OR is several links sharing an anchor —
   never one link with many members, which would make every coincident pipeline *necessary*.

### A3 — `chain_level`: strike the false evidence, defer the target

ADR-0205 §11 claims *"`BlameVerdict.chain_level` takes `hint | map | plan | plan_subtree |
pipeline` — this ladder, already named."* The §1 ladder is
`capacity | pipeline | milestone | plan | request`. Two of five match. `hint` and `map` are
Phase-1 **steps** (ADR-0206 §3: *"The steps are request → hint → map → plan"*), not levels;
`plan_subtree` is already retired.

The terminology choice survives — "layer" and "tier" are genuinely taken. The evidence does
not. **`chain_level` has no defined target set until hint and map are settled as steps rather
than levels — that is a decision for C4R2, not a wording fix.**

**Consequence for `request_knowledge`:** it references two different kinds of thing — step
outputs (hint, map) and levels (plan, milestone, pipeline). The declaration rule applies to
the level half only; a hint has no level beneath it to require. The validator must not demand
all five.

### A4 — lazy descent implies a per-level trace

ADR-0205 §4 states lazy descent. **Nothing states that the per-request trace must therefore
carry a record at each level.** Without that, an optimisation that replaces the trace nodes
with links looks correct and silently deletes the descent history — which is exactly what a
first pass here proposed. Add it to §4 or §11 (§7 above).

### A5 — the drafting failure mode, for the next ADR author

Three defects inside 24 hours, and two are places where a caveat raised in discussion did not
survive into the text. **When a discussion raises a caveat and the ADR states the confident
version, the caveat is the thing that was true.**

Stronger form, and it belongs in the plan's §0 beside the standing rule: **an ADR does not
reach Accepted until someone has read it against the code it governs.** All three defects
were found that way and none needed new information.

---

## 9. The revised CORE-C2 chain

Numbering follows `STATE.json` `pending_designs[0]`, not `CORE_RECONCILIATION_PLAN.md` §3
(which used C2R0–C2R5 + C2R4a). The plan document is renumbered to match.

| ID | Scope |
|---|---|
| **A0** | The three ADR amendments — docs only, lands first (§8) |
| **C2R1** | `installed-skills` becomes dual-scope. Independent; starts now |
| **C2R2** | The composition-primitive corrections: P8-A restored to the ADR-0148 contract, **plus D1** (properties editable; members and existence frozen) |
| **C2R3** | **The link mechanism** — write/read compositional and ordinary intergraph links at L2, persister round-trip, **the traversal primitive**, **attribution**, **invalidation** |
| **C2R4** | **The pipeline level** — one store, `pipelines`; steps convert to the composition primitive; `edge_sequence` retired; migration |
| **C2R5** | **The milestone level** — nodes, target link, composition over pipelines, hub discovery, the declaration capacity |
| **C2R6** | **The plan level** — the milestone tree lives here; `PlanResult` endpoint dicts, `sequence_index`, `parent_ref`, `children_refs` all become links |
| **C2R7** | **The request level** — `request_knowledge`; `paired_pipelines` **retired** (not converted — pipelines are reached through plan → milestone → pipeline; a direct link would recreate the duplication); `relevant_hints` becomes links; confidence rides on them |

**The pipeline level moves ahead of the milestone level.** A milestone links over pipelines
and cannot exist first. The plan had these the other way round.

**Each level's chain record is stripped in the item that creates that level's durable form**,
not in a later cleanup pass — or the duplication survives to the end of the chain.

### 9.1 Corrections owed to `CORE_RECONCILIATION_PLAN.md`

1. §3 renumbered; every cross-reference in §4, §5 and §9 re-pointed.
2. §3.1's "same upward walk" premise replaced (§4 above).
3. §7's *"No file overlap with C1–C3"* is **false**. From C2R5 onward every item touches
   `chain_artifacts.py`, `phase_1.py`, `plan_construction.py` and `orchestrator.py`, which the
   dream lane streams. Coordination is continuous, not a one-time conversation.
4. §12 — resolve or delete the two `OPEN_DECISIONS.md` references. **The file does not
   exist.**
5. §10 rename inventory — `paired_pipelines` is **retired**, not converted to an edge.
6. §0 gains the "read it against the code" rule (§8 A4).

---

## 9.2 Ordering, per level — settled

`ordered` on a composition link expresses a **total** order over its members. A partial
order — "A before B, C parallel to both" — cannot be expressed by a member list and must be
expressed by **edges**. ADR-0206 §2: *"An edge means 'must complete before'; no edge means
order is free. Sequential and parallel are the presence or absence of an edge."*
ADR-0205 §3: sequence versus parallel is *"an output of planning, not an input."*

| Link | `ordered` | Why |
|---|---|---|
| pipeline → its capacity steps | **`True`** | the sequence *is* the pipeline; duplicates legal (a capacity may fire twice) |
| milestone → a pipeline reaching it | moot | single-member links (§8 A2.3) |
| plan → its milestones | **`False`** | the **set** of milestones in the plan; the partial order over them lives in sibling→sibling dependency links, and their absence is what *parallel* means |
| request → its plan | moot | single-member |

**Forcing `ordered=True` at the plan level would put every milestone in a line and make
parallel siblings inexpressible.** This is precisely what the P8-A restoration is for:
without `ordered=False` a plan whose milestones form a set with a partial order over them
cannot be represented at all.

**The pipeline's composition link holds only its ordered capacity steps.** `start_ds` and
`end_ds` are separate links, not members and not content — ADR-0205 §1's *"capacities and
DataStates"* would otherwise duplicate what the capacities' declarations already give.

---

## 9.3 Scheduling — settled

- **C3R1 starts now**, in parallel with A0 and C2R1. It has no dependencies. It must be
  *finished* before C2R4, not started before anything.
- **A0 and C2R1 run in parallel.** C2R1 is independent of all four decisions and all four
  amendments.
- **The dream handoff is a message, not a decision.** Dream reads the per-request records
  this plan renames and strips. When the chain `Plan` becomes `PlanRun` and loses its
  reference lists, dream's reader either breaks or silently reads nothing. **The message goes
  out before C2R6 lands, not after.**

---

## 10. Open

- ⚠ **`input_group` graph form — UNOWNED AGAIN.** It was assigned to C3R1; **C3R1's
  half-ship (`4fd8baa`) did not include it**, and the remaining C3R1/C3R3 scope (the
  finder-as-capacities CR) does not name it. **It blocks C2R4.**

- **The graph form of `input_group`** — `CORE_VERIFIED_FINDINGS` §11.5 says it blocks both
  the pipeline-store unification and the finder. **Assigned to C3R1.** ⚠ This makes C2R4 wait
  on a C3 deliverable; the two chains are no longer fully parallel.
- **`chain_level`'s target set** — C4R2 (§8 A3). Not blocking C2.
- **The chain reshape (§7)** — decided, but needs the dream chat before C2R6 lands.
- Whether skill uninstall covers Local artifacts built on a Skill — **effectively answered by
  §7a**, and owned by the skill-packaging chat.
- `origin/main` is `b612c93`; `CORE_VERIFIED_FINDINGS.md` states `fafc679`.

---

## 11. Reconciliation with two lanes that shipped mid-chat

`origin/main` moved twice while CORE-C2 was building, both times into these documents.

**`60fe2ae` — the C3R1 ship.** Corrections carried through: `types.py` is not dead code and
**S14 is struck**; **C3R1 is half-shipped** (the two phase-2 cycle guards only — `find_verdict`
and the `catalog_check.py` sweep remain); C3R3 merged into the finder-as-capacities CR and
`BFSFinder` becomes a `selection_policy` **value**; C3R3 depends only on C3R1, so the finder
rewrite runs fully parallel to C2. **And the claim that skill attribution's declared footprint
already worked is FALSE** — see §7a and findings §12.6.

**`2c56246` — the C1R4 sweep (ADR-0205 §amendment-1).** It reached four of this chat's
findings independently. Two it had that this chat did not, both adopted:

- **§am-1.2 — the primitive is selected by arity.** Single-member compositions are
  `IntergraphEdge`; the hyperedge refuses 1-1. **Every milestone→pipeline and request→plan
  link is single-member**, so the design as first written was unbuildable.
- **§am-1.6 — a composition pins its graphs.** Ruled for the trace: per-request links are
  **non-compositional**, so task graphs stay removable (§am-2.2). The durable case is open.

**Numbering.** Their amendment holds ADR-0205 §amendment-1; this chat's is **§amendment-2**,
and it does not restate theirs. Their note that §am-1 "flips to Accepted with CORE-C2R1" uses
the pre-renumbering ids — under this plan's numbering that is **C2R2**.

**Standing lesson, third instance.** Merge `origin/main` into a lane the moment another lane
ships. Two of the three conflicts here were substantive, not textual.

---

## 12. What shipped, and what building it taught

**A0** — `1e45067`. Docs only, landed ahead of every code item so the gate result stayed
attributable. ADR-0205 §amendment-2, ADR-0206 §amendment-1, ADR-0148 §amendment-1, plus the
plan corrections and `CORE_VERIFIED_FINDINGS.md` §12.

**C2R1** — `df3af56` → `fa5e18d`. `installed-skills` dual-scope; the install **record's**
realm follows the principal; the bundle's **content** goes where the manifest's `entry.tier`
says; ten roster readers scope-aware; `USER_CAPS` non-empty; **ADR-0183 S3 amended**; the
first bundle a non-admin can install.

### 12.1 Four things the build corrected in the design

1. **`scope` was doing two jobs.** It was applied to the bundle's L2 content as well as the
   install record, which **silently redirected a bundle's content away from where its
   manifest declared it**. The record's realm and the content's realm are unrelated.
2. **A fixed `scope="local"` default broke every session-less caller.** Local writes are
   user-scoped, so there is no coherent Local destination without a session. `_resolve_scope`
   follows the principal instead.
3. **Reading a roster was minting state.** `local_metagraph` lazy-creates, so consulting the
   install roster materialised an empty Local *ahead of the durable boot that restores one* —
   which is what broke `test_durable_roundtrip`. Guarded with `has_local`. **A read must
   never create.**
4. **S3 made the feature unreachable.** Preflight refused every non-Global tier, so
   §am-11's Local install record had **no bundle it could ever carry**. Without the S3
   amendment C2R1 would have shipped a capability nobody could use — the write half working
   and no way to exercise it.

### 12.2 Behaviour worth knowing before touching the install path

**A refused install is not a no-op.** ADR-0183 §S8 appends a `failed` record before
re-raising, so the attempt stays auditable. Assert *"never reaches `installed`"*, never
*"no record exists"*.

### 12.3 What C2R1 deliberately did not settle

Most useful bundle content — concepts, ontology — lives in **Global-only** roles, so a
user-installable bundle is a narrow thing today. **Which bundles should be user-installable,
and what a Skill may legitimately place in a user's realm, is a skill-packaging question**
and is ADR-0183 §am-5's unbuilt Local half. The **skill ledger** (§7a) belongs there too, and
is built whole — the "declared footprint already works" premise was verified false.

### 12.4 Gate hygiene — three full runs were wasted

The gate clone sat in an **unresolved merge**. Every `checkout` and `merge` refused with
*"you need to resolve your current index first"*, and each run silently reused the image
built from the first stale state. One earlier green belonged to a **different lane**
entirely.

- **`git status --short` must be clean before believing any gate result.** A wedged index is
  silent and survives every subsequent command.
- **Gate `origin/feat/<lane>` directly** when the lane already contains `main` — the merge
  step is a failure point, not a safeguard.
- **Never create a gate branch inside a lane's worktree.** It evicts the lane's branch.
- **The diagnostic that worked:** grep the gate host *and* the container for a string only
  the new commit has. Failing tests whose names no longer exist prove staleness outright.
