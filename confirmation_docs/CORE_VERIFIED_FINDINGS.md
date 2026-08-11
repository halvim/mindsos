# CORE — verified findings

**Filed:** 2026-07-31, core reconciliation chat.
**Verified at:** `origin/main` `b612c93` (re-confirmed unchanged from `644e91c` →
`01e4d0d` → `9fcb694` → `fafc679` → `b612c93` across every file cited here;
`9879a71` and `b612c93` are docs-only).
**§12 added by the CORE-C2 chat**, re-verified at `b612c93` and reconciled against
`60fe2ae` (the C3R1 ship). §12.6 **withdraws** a §3 claim of the reconciliation plan.
Everything below was read from the code, not inferred.

---

## 1. Finder defects (from the original CR, re-verified)

| # | Defect | Evidence |
|---|---|---|
| **D-A** | The sound finder was never wired to anything that executes. `find_pipeline` has no strategy parameter and hardcodes `BFSFinder`. BFS fires a capacity off the one input it arrived on and leaves the rest unwired. With `INPUT_GROUP_FOLD`, `_validate_inputs` short-circuits, so a 3-input capacity runs on 1 input and **reports success**. | `pipeline.py:479-505`, `capacity.py:322` |
| **D-B** | `ConjunctionFinder.fire` is non-monotonic. Phase 2 re-tests satisfiability with an **empty stack**, discarding phase 1's cycle guard, so a producer can be selected to feed itself. Adding an available input makes composition *fail*. | `pipeline.py:430`, `:462` (phase-1 site is `:398`) |
| **D-C** | `INPUT_GROUP_FOLD` fans in every producer at composition and aggregates nothing at execution — one blackboard slot per DataState IRI, so N producers overwrite each other and the run reports success. | `pipeline.py:433`, `pipeline_execution.py:200-202` |
| **D-D** | Arbitrary producer selection is unrecorded. `fire` takes `satisfiable[0]` sorted by IRI and records nothing, so the plan is indistinguishable from one where only a single producer existed. | `pipeline.py:424-436` |
| **D-E** | *(added 2026-07-31)* A capacity **under construction** is invisible to both guards. `fired[cap_iri]` is written *after* its inputs are built, and the cycle stack tracks DataStates under resolution, not capacities under construction — so mid-`fire` a capacity can be selected to produce one of its own transitive inputs. It then either recurses to `max_depth`, **or completes and is appended to `steps` twice**: a `Pipeline` naming one capacity as two distinct steps, returned with no error. `execute_pipeline` runs it twice and D-C's one-slot blackboard silently overwrites the first result. **D-B raises; D-E lies.** Also falsifies `ConjunctionFinder`'s own docstring claim that shared upstream producers fire once. | `pipeline.py:411-413` (memo written on exit), `:430`, `:462` |

### Line-number corrections (2026-07-31)

The first draft cited D-B at `pipeline.py:427-436, :451`. The empty-stack call sites are
**398** (phase 1, correct there), **430** and **462**. `:451` is wrong. D-C's execution
half is at `:200-202`, not `:193-201`.

### Measurement (2026-07-31)

`confirmation_docs/finder_variants_model.py` reproduces both finder phases exactly and
swaps only the phase-2 admission rule. Over 20,000 generated capacity graphs:

| phase-2 rule | `max_depth` blowups | duplicate-step pipelines |
|---|---|---|
| shipped (`frozenset()`) | — | — |
| live cycle stack only | **369** | **20** |
| live stack + in-flight guard | **0** | **0** |

The three conformance shapes (`all_required` AND, diamond convergence, fold fan-in) are
byte-identical across all three. Separately: the `fired` memo short-circuit is a **cost
optimisation, not a correctness clause** — identical results with and without it in all
20,000 graphs.

### Correction to the CR spec

The spec states `ConjunctionFinder` had **zero call sites**. **False.**
`mindsos_cli/commands/brain.py:687` (`_do_execute`, the skill-entry `execute` verb) calls
it on a shipped path. So D-B **and D-E** are live in the product today, and
`tests/resident_brain/test_execute.py` is in scope for any fix.

### Known-open, introduced by the just-merged #99

`_select_finder` keys off **start** arity, not **input** arity. A single start feeding a
3-input consumer still routes to `BFSFinder` and still under-wires. D-A is unfixed.

---

## 2. The taught-pipeline lookup does not exist at runtime

- Storage ships: `learned-pipelines` is a Local L2 role (ADR-0203). Teaching appends an
  immutable `LearnedPipeline` node holding a full `Pipeline.to_dict()`.
- **Runtime never consults it.** Every consumer of `iter_pipelines` /
  `iter_local_pipelines` is in `mindsos_cli/commands/brain.py`. `mindsos_intelligence`
  imports `mindsos_server` **nowhere** (verified: zero top-level imports).
- `execution.py` calls `find_pipeline` unconditionally at every leaf and every map
  member. There is no "do I already know this?" step anywhere on the path.
- This was foreseen and shelved. `pipeline.py`'s docstring: *"Deferred (consumer
  discipline): the promoted-path-lookup strategy (`promoted-pipelines` has no writer —
  verified)."* A writer now exists — for the Local `learned` role, not the Global
  `promoted` one.

**Consequence:** the system re-derives from scratch, with an unsound finder, the
pipelines that were taught to it.

### The layering constraint on any fix

ADR-0010 §I-S1: domain layers must **not** import `mindsos_server`, enforced by
`tests_server/integration/test_layer_isolation.py`. The shipped pattern is dependency
inversion — L3 defines a `SessionProtocol` naming only what it needs. Any pipeline
lookup must follow the same shape. Note `mindsos_server/__init__.py` says it *"sits ABOVE
every domain layer"*, while `docs/concepts/layers.md` calls it "L0 … orthogonal" — the
docs disagree on placement but agree on the ban's direction.

---

## 3. The thirteen placeholders

The orchestrator is **real and shipped** — six phases, dispatch, chain artifacts,
streaming Episode consolidation. What is missing is the capacities it dispatches. All 13
carry `placeholder=True` and are opt-in installs from Phase 47.

**`planning_v0`** — `derive_initial_plan` → single-milestone Plan; `decompose` → `[]`;
`is_leaf` → `True`; `aggregate_outputs` → last child.
⟹ **No plan has ever been decomposed.** Every request is one milestone, one pipeline.

**`phase1_v0`** — `process.identity` → passthrough; `hint.global` → empty;
`decision.derive_goal` → fixed goal; `decision.map_to_task_pattern` → fixed pattern at
confidence **1.0**.
⟹ The `mapping_confidence_threshold` check in `phase_1.py` is **vacuous**.

**`orchestration_v0`** — `signal_to_tier`, `attention_score`, `should_replan` (default
continue), `sufficient` (default True), `attribute_blame` (fixed).
⟹ Replan never fires on its own judgement; sufficiency is always true; blame is a
constant.

---

## 4. Plan and Milestone as shipped

`Milestone` (dataclass in `chain_artifacts.py`, emitted into the `chain` graph):

```
iri, name, sequence_index, parent_ref, is_leaf,
children_refs, pipeline_ref, status, output_data_state_ref, replans_used
```

- **Topology is in properties, not edges.** `parent_ref` / `children_refs` are node
  properties, so the plan tree exists as data but cannot be walked as a graph. Same
  defect class as DataState subsumption.
- `sequence_index` is a flat integer per sibling group. It can order siblings; it cannot
  express independence.
- `name` is a free string. There is **no declared target** — `output_data_state_ref`
  records what was produced, after the fact.
- The target does exist, in a second place: `PlanResult.solve_target` and
  `PlanResult.leaf_targets` carry `{start_datastate, target_datastate}` per leaf. So the
  plan has **two parallel representations** that have drifted apart.
- `MAX_DEPTH = 3` is a brain's test artifact, not a design.

`chain_artifacts.py` is **architecture, not a shim** (Chat B D-B22, the 6-level reasoning
chain). Its defect is representational, not existential.

---

## 5. `request_patterns` — the decomposition store nobody writes

Shipped since Phase 13: `RequestPattern` and `SubgoalTemplate` node types, with
`DECOMPOSES_INTO` and `PREREQUISITE_OF` edges, and a `confidence` field that ADR-0152 §2
deliberately **kept** when ADR-0094 §am-1 dropped it from `promoted_pipelines`
("per-pipeline confidence migrates to ALS").

Readers: `phase_1.py:139/142` checks existence of a `RequestPattern`. **Writers: none.**
`SubgoalTemplate` is entirely unused.

Earlier in this chat I reported "zero readers" — that was a case-sensitive grep miss
(`ROLE_REQUEST_PATTERNS` is uppercase). Corrected.

---

## 6. `learned_pipelines` content/metadata partition

```
content:  {pipeline_name}          frozen — immutable_successor
metadata: {taught_seq, recorded_at}  writable
```

⟹ a confidence field must be **metadata**. As content it would be frozen and ALS could
never update it.

---

## 7. WSD is a consumer — the rule exists, the scheduling does not follow it

- `RULES.md` §8 already says it, including *"Stop deferring core mechanics 'to WSD' —
  that framing is wrong and has misled multiple chats."*
- A **2026-06-25 ownership pass** already fixed *attribution*: an authoritative Owner
  column in `WSD_INSTALLATION_PHASE_MAP.md` §2.1, plus notes in `CLAUDE.md`, `HANDOFF.md`
  and `POST_PHASE_38_PHASE_MAP.md` §6. Its recorded lesson: *"putting the principle only
  in RULES did NOT stop the drift — chats believe ARTIFACTS, not rules; the fix is to make
  ownership a FIELD in the artifacts chats read."*
- **What was never changed is the scheduling.** The core rows are still sequenced inside
  WSD slots, so core still waits on WSD.
- **24 mentions across 18 `mindsos_*` files still say WSD ships it.** 16 are wrong, 3 are
  already-resolved reversals needing a reword, 5 are legitimate (WSD as consumer or a
  genuine WSD-owned id). The June pass did not touch code docstrings — the artifact a chat
  reads while editing.
- **Phases 51–56 are reserved by the WSD map; DWF is pencilled for 57+.** New numbered
  phases would collide. Use `feat/*` branches and `<name>-confirmed` tags (RULES §2).
- **WSD-4 / Phase 54 already schedules the work**, marked `MindsOS-core`: *"atomic v0→real
  `planning.*`/`phase1.*`/`orchestration.*` catalogs in one PR + orchestrator default flip
  + `placeholder=True` roster deleted."* Plus the `hint.*`/`predicate.*`/`decision.*`
  families. POST_PHASE_38 §7 **q4** routes "`planning.*` v0 → real catalog migration
  discipline" to the WSD chat.

---

## 8. Brains

**arc1's solver is disjoint from MindsOS — its own docstring says so:** *"This solver is
self-contained: it imports only `arc_grids` … it never touches the `CapacityLayer` or
`find_pipeline`. The registered reason topology (`arc_capacities`) and this executable
solver are **disjoint artifacts**; the 'grounding' is a hand-maintained mirror, not an
execution path."* ~3,750 LOC of reasoning outside MindsOS, mirrored by 1,032 LOC of
`arc_capacities.py` that never executes. Through the real lifecycle, arc fetches a task
and returns "don't know."

**nilm is the disciplined one:** composes with the real `ConjunctionFinder`, executes with
core's `execute_pipeline`, persists via `learn_pipeline`, and documents its own boundary.

**Both blame the same blocker, independently:** nilm — *"Rung 5 (mindsos's own
orchestrator driving this) is out of reach until core ships the WSD/phase-1 placeholders
— same as both arc brains. Not faked."*; arc1 — *"We do NOT use
`Orchestrator.run_lifecycle` — it is hardwired to the v0 catalogs."*

**Already reconciled — the template:** the REPL. arc1's `repl.py` is 21 lines
(`boot_brain` + shared `BrainREPL` + a per-brain `viz_spec`).

**Three gaps written three times:** iterative refinement (no core mechanism); a minimal
Local session (`DuckSession` ×3); driving the lifecycle at all.

---

## 9. Layer violations and shims

- **`mindsos_server/pipeline_runner.py` is in the wrong layer.** It runs a Pipeline by
  dispatching through the L4 dispatcher — L4 work in L0 — and duplicates
  `pipeline_execution.execute_pipeline` in a weaker form (no grounding writer, no MM,
  silently drops inputs not in its state map). It is the runner behind the `execute` and
  `invoke` REPL verbs, so the CLI and the lifecycle run pipelines through two different
  executors with different semantics.
- **`find_pipeline`** is a ten-line back-compat shim for the old singular
  `start_datastate=` keyword, delegating to `BFSFinder`. It is why the unsound walk is
  still the default at seven call sites.
- **`mindsos_capacity/types.py`** — a deprecation shim, self-described as dead code.
- **ADR-0158** allows single-dot DataState names only; multi-dot raises at registration
  and is deferred to v1.5+.

---

## 10. Environment

- **Another chat is working the finder.** `.git/worktrees/_MindsOS-finder-default-ruling1/`
  and `refs/heads/feat/finder-default-ruling.lock` exist. Collides with the finder chain.
  **Find out what it is doing before starting C2.**
- Sandbox-created git locks strand the Mac (`index.lock`, worktree `HEAD.lock`, ref
  locks). Clear with `find .git -name '*.lock' -delete` with no git process open.
- The device bridge has **no network access** — `git fetch` must run in the user's own
  terminal.
- `origin/main` is `fafc679`. #99 and #100 merged 2026-07-31; merged-state gate
  **4436 passed / 12 skipped / 1 xpassed / 0 failed**, `test_cli` collected 256; tag
  `mapfold-multiinput-confirmed` pushed. STATE.json `recent[]` entry still owed.

---

## 11. Round-2 findings (2026-07-31, after the first draft)

### 11.1 `RequestPattern` — three corrections to §5 above

- **`paired_pipelines` exists and is the pattern→pipeline binding.** `list[IRI]`, a
  **content** field, and the explicit **source of truth** (PB-R3-21). The pipeline-side
  reverse cache was deliberately removed (D-L2-7).
- **The lookup was designed and never built.** ADR-0152 §1: *"Phase-2 pipeline lookup
  walks task-patterns via L3 pipeline-finder, which maintains its own runtime index over
  `task-patterns.paired_pipelines`."* No such index exists.
- **`relevant_hints`** (metadata, admin-tunable) declares which hints identify this
  pattern. So a RequestPattern is a *recognized kind of request*; hints are the evidence.

Full field set — content: `pattern_name`, `task_shape_recognizer`,
`sufficient_predicate_iri`, `domain`, `paired_pipelines`. Metadata: `relevant_hints`,
`mapping_confidence_threshold`, `n_observations`, `confidence`, `provenance`,
`routing_override`, `created_at`, `last_updated_at`.

### 11.2 `SubgoalTemplate` is nearly empty

Only `subgoal_kind` and `ordering_hint`. ADR-0152 §2 explicitly deferred its partition
and kept Phase 13's advisory set. No DataState reference, no confidence. The node type and
both edge types exist; the content does not.

### 11.3 `request_patterns` is already dual-scope — PBBP is satisfied by design

ADR-0150 §am-8: *"request-patterns gains a Local form — dual-scope like
pending-promotions / learned-parameters: per-user patterns are authored/learned Local and
promoted to the shared Global form; discipline is `immutable_successor` so new pattern
nodes are addable Local."* Bootstrapped in both `_GLOBAL_NAMED_ROLES` and
`_LOCAL_NAMED_ROLES`.

**`promoted-pipelines` is Global-only.** `learned-pipelines` is Local-only.

### 11.4 `Pipeline` already has the lifecycle

Content: `pipeline_name`, `edge_sequence`, `start_ds`, `end_ds`, `expression_metadata`.
Metadata: **`status`** (5-state enum), `n_runs`, `outcome_history`, `provenance`,
`quarantine_threshold`, `created_at`, `tested_at`, `activated_at`, `quarantined_at`,
`quarantined_by`, `retired_at`.

So a learned/discovered/promoted tag is the existing `status` field, and `n_runs` +
`outcome_history` are the evidence ALS would consume. No writer exists.

### 11.5 D38 — the blocker ADR-0203 cited is mostly resolved

ADR-0203 rejected "extend the promoted `Pipeline` to Local" because it would couple to
*"the normalized `HAS_STEP` graph partition whose shape is in flux pending the D38
capacities-as-hyperedges reframe."*

**D38 was settled by ADR-0156** — capacity↔DataState topology is explicit **bipartite**,
superseding ADR-0069 and ADR-0086. That is what the finder walks today.

**What remains deferred is narrower:** the *graph form of `input_group`* — a typed
hyperedge plus a hyperedge-aware view walk (ADR-0156 §am), "out of scope until their
consumers land." This is also why `_input_group_of` reads the declaration registry rather
than the graph (Decision 8).

⟹ Unifying the pipeline stores is exposed to one open shape, not a whole reframe — and
settling that shape also removes the finder's declaration-registry read.

### 11.6 The same defect, three times

Topology stored as **properties instead of edges**:
1. `Milestone.parent_ref` / `children_refs` — the plan tree is unwalkable.
2. `RequestPattern.relevant_hints` / `paired_pipelines` — IRI lists, not edges.
3. DataState subsumption (the original C11 finding) — no `SPECIALIZES` edge.

### 11.7 Environment

All stale worktrees cleared (`_MindsOS-iteration-map`, `_MindsOS-finder-default-ruling`,
`/tmp/seam_wt`); `feat/finder-default-ruling` deleted — it had zero commits and an empty
diff. Sandbox-created worktrees carry a `locked` marker: `git worktree unlock <path>` then
`prune`, since the registered path does not exist from the Mac.

---

## 12. Round-3 findings (2026-07-31, CORE-C2 pre-build read-through @ `b612c93`)

Every claim in §§1–11 held. What the re-read **added**:

### 12.1 The L2 knowledge layer cannot write a link

`KLWriteHandle` (`mindsos_knowledge/write_handle.py`) exposes `write_and_validate`,
`update_and_validate`, `validate_node` and `mint_iri` — **node operations only**.
`KLWriteHandle.validate_xref` raises `WriteHandleNotWiredError` (deferred at Phase 36
"alongside the first XRef writer"; the writer never arrived). `MetagraphView` reads edges
(`get_edges`, `step`) but has no writer. **`IntergraphHyperEdge` has zero consumers in
`mindsos_knowledge`, `mindsos_intelligence` and `mindsos_capacity`** — only `mindsos_cli`
and `mindsos_cli/migrations`.

⟹ ADR-0205's *"the composition primitive already ships; this is a use of core, not an
extension of it"* is true of `mindsos_core` and **false of the layer that has to use it**.
Four CORE-C2 items assumed the capability existed.

### 12.2 Compositional links can never be removed or have properties updated

`Metagraph.remove_intergraph_hyperedge` and `update_intergraph_hyperedge` both raise
`CompositionalImmutableError` when `compositional=True`, **with no escape hatch** —
`metagraph.py`, Phase 05b pushback **6-A**: *"Tester recovery for a wedged metagraph is
`mindsos metagraph reset`."* `remove_graph` carries the same cascade refusal.

⟹ ADR-0206's ALS-moves-confidence-on-the-edge, its recompute-hubs-on-every-learn, and
ADR-0205 §8's uninstall-removes-the-vertical are **all structurally impossible** on the
primitive both ADRs designate. Resolved by `CORE_C2_DECISIONS.md` §2.

### 12.3 The pipeline level is a fourth topology-in-properties instance

`promoted-pipelines` carries **both** a normalised `HAS_STEP`→`PipelineStep` partition **and**
an `edge_sequence` content property (`mindsos_knowledge/schemas/promoted_pipelines.py`).
§11.4 listed `edge_sequence` without flagging it. Phase 13 **PB-9** additionally locked
`HAS_STEP` as an ordinary `EdgeType` with an advisory `position`, *"NOT an ordered
hyperedge"* — a decision ADR-0205 §2 never considered.

### 12.4 `chain_artifacts.py` adds six more instances, and the C1R4 sweep missed the file

`HintSet.hints` is a `Dict[str, Any]` holding structure (ADR-0205 §5 bans it).
`StepExecutionRecord.confidence` sits on a node (ADR-0206 §5: confidence is relational).
`RequestRun.pipeline_runs`, `RequestRun.replan_history`, `ReplanRecord.invalidated_refs` and
`ReplanRecord.spawned_refs` are reference lists inside records.

⟹ §11.6 counts three instances of the defect system-wide. **With §12.3 and §12.4 the real
count is nine.**

### 12.5 P8-A's rationale is recoverable, and ADR-0148 contradicts the glossary

§10 of the plan and ADR-0205 §2 both record that the P8-A argument was lost. It is not — it
survives in `INTERGRAPH_EDGES_DESIGN.md`, `PHASE_MAP.md` and `PHASE_05c_CONFIRMED.md`; the
file searched for (`PHASE_05c_DESIGN_LOG.md`) never existed, while
`PHASE_05c_IMPLEMENTATION_LOG.md` does. Separately, ADR-0148 and `docs/concepts/glossary.md`
cite each other for an amendment neither reproduces and **assert opposite outcomes**.
Resolved at ADR-0148 §amendment-1 and ADR-0205 §amendment-1.

### 12.6 Attribution's "declared footprint" does not exist

`CORE_RECONCILIATION_PLAN.md` §3 claimed the declared half of skill attribution already
worked, because `installed-capacities` carries `capacity_iri` + `installed_by`. **The C3R1
chat verified that claim false and it is withdrawn.** The driver stamps `installed_by` on
**Global L2 content nodes** (`skills/driver.py`) and filters *those* on uninstall;
`mindsos_server/boot.py` states the `installed-capacities` role is "empty until" a
user-scoped install exists. The schema and IRI minting ship; **nothing populates them.**
ADR-0183 §am-5's Local half is specified and unbuilt.

⟹ **The skill ledger (`CORE_C2_DECISIONS.md` §7a) has no existing half to build on.** Its
"declared footprint already works" premise is void; the skill-packaging chat builds the
whole thing. This does **not** affect CORE-C2R1, which touched only `installed-skills`.

### 12.7 `input_group` is still unowned

`CORE_C2_DECISIONS.md` assigned the graph form of `input_group` to C3R1. **C3R1's
half-ship (`4fd8baa`) did not include it** — it shipped the two phase-2 cycle guards and
left `find_verdict` and the `catalog_check.py` divergence sweep open. `input_group` appears
in neither. **It remains unowned and it blocks the pipeline level.**

### 12.9 Reconciled with the CORE-C1R4 sweep at `2c56246`

The sweep (ADR-0205 §amendment-1, `CORE_ADR_CONTRADICTION_SWEEP.md`) reached §12.1, §12.2,
§12.3 and §12.5 **independently**. Two of its findings this read-through did **not** have,
both of which change CORE-C2's design:

- **am-1.2 — the composition primitive is selected by arity.** `add_intergraph_hyperedge`
  refuses 1-anchor/1-member (validation step 8, "NOT 1-1"); a single-member composition is
  an `IntergraphEdge` with `compositional=True`. **A milestone takes one link per pipeline
  reaching it, and a request one link to its plan — every one of those is single-member**,
  so the hyperedge alone cannot express the design. Adopted.
- **am-1.6 — a composition pins its graphs.** `remove_graph` refuses while any incident
  compositional edge exists, and ADR-0202 persists one chain graph per task. **Ruling for
  the trace: per-request links are non-compositional** (ADR-0205 §am-2.2), so task graphs
  stay removable. The wider question stays open with the milestone-level item.

### 12.8 Environment

`origin/main` is `60fe2ae`. A worktree created **on the Mac** is unusable for git from the
sandbox — its `.git` file points at a Mac path — but file writes work, which is the correct
split. **The Linux gate host and the Mac are different machines: a `docker.sock` under
`/Users/` means the gate was run on the Mac, which RULES §5 forbids and which will silently
gate the wrong branch.**

---

## 13. Round-4 findings (2026-08-04, CORE-C2R2 pre-build read-through @ `3591add`)

Every claim in §§1–12 held except **§12.7**, which is withdrawn (below). What the re-read
**added** — all four read from the code, not inferred.

### 13.1 An ordered hyperedge's member order does NOT survive persistence

This is the finding that changed C2R4's design (ADR-0205 §amendment-3.2).

- `mindsos_core/cypher/builders.py` — `build_unwind_create_intergraph_hyperedges` writes
  `MERGE (ih)-[:MEMBER]->(n)` with **no ordinal property**. `MERGE` is idempotent, so a member
  appearing twice collapses to one relationship.
- `mindsos_core/reconstruction/metagraph_loader.py` — `_load_intergraph_hyperedges` reads them
  back with `collect(DISTINCT {node_id, graph_id})`. Arbitrary order, duplicates already gone.
- The loader **selects `ih.ordered`** in its `RETURN` clause and **never passes it** to the
  reconstruction call.
- Reconstruction goes through `mg.add_intergraph_hyperedge`, which derives `ordered` from the
  **schema type** — and a loaded metagraph has no schema (`MetagraphLoader` restores
  `schema_name` only, PB-11 A), so P9-A's permissive default applies and every reloaded
  hyperedge is treated as `ordered=True` regardless of what it was.

`FalkorDBLocalPersister.save` / `.load` (`mindsos_server/persistence/local_persister.py`) go
through `MetagraphRepository` / `MetagraphLoader`, so this is the durable path, not a corner.

⟹ **Member order and duplicates are destroyed on every durable round-trip.** Phase 05c's own
`cat = c + a + t` fixture does not survive a reload today. **No test asserts otherwise**, so the
gate is silent about it.

**Reachability: DECLARED, not live.** `IntergraphHyperEdge` still has zero consumers above
`mindsos_core` (§12.1), so nothing writes one into a persisted store today. C2R4 would have
been the first. It is a defect in `mindsos_core` independent of CORE-C2, and C2R4 avoids
depending on it by deriving order instead of storing it.

### 13.2 The L2 knowledge layer cannot READ a link either — §12.1 named only the write half

§12.1 records that `KLWriteHandle` is node-operations-only. The read half is missing too:
`MetagraphView` (`mindsos_knowledge/metagraph_view.py`) exposes `graphs_by_role`,
`alignment_graph`, `get_node`, `iter_nodes`, `get_edges`, `step` and `versions_in_role` —
**and no intergraph accessor at all**. `get_edges` and `step` walk `Graph.edges`, which is
intra-graph.

⟹ `CORE_RECONCILIATION_PLAN.md` §3.1 specifies the traversal primitive as
`walk(start, *, direction, view, …)`. The `view` it is meant to read through cannot see the
links it must walk. **C2R3's scope is the read path as well as the write path.**

### 13.3 A zero-step `Pipeline` is storable, and is not representable as a composition

- `mindsos_capacity/pipeline.py` — both finders return `Pipeline(steps=(), edges=())` when the
  target DataState is already in the start set (`BFSFinder` and `ConjunctionFinder`, each with
  an unconditional early return before their search phases).
- `mindsos_server/pipelines.py::learn_pipeline` validates only the ADR-0182
  `to_dict`/`from_dict` round-trip before persisting. An empty pipeline round-trips perfectly,
  so **it is storable today** and would carry into C2R4's migration.
- `add_intergraph_hyperedge` refuses `m < 1`; the single-member `IntergraphEdge` (§am-1.2) needs
  a target node. **There is no composition with zero members**, so under ADR-0205 §2 an empty
  pipeline is not at the pipeline level at all.

Downstream, confirmed by the dream lane: `mindsos_intelligence/capacity_persister.py`
`build_capacity_index` returns `None` when no run graph has nodes, so a request served by an
empty pipeline closes **successfully with `capacity_root_ref = None`** — the same shape a
crashed request has. Four consumers infer "already held" from an absence: the store, the episode
corpus, `viz_spec.SEGMENTS`, and the planning loop (satisfied vs unreachable milestone).

⟹ Ruled at ADR-0205 §amendment-3.4; the fix is requested of CORE-C3 as an `already_held`
distinction on `FindVerdict`.

### 13.4 §12.7 is WITHDRAWN — `input_group` blocks nothing

§12.7 records the graph form of `input_group` as unowned and blocking the pipeline level.
CORE-C3R1 retired the **concept**, so the deferred item has no subject (ADR-0156 §am's deferral
is withdrawn, not deferred). Measured across every repo: **`Arc3` 0 · `nilm` 0 · core 0 ·
`arc1-brain` 1** (`arc_capacities.py:841`, being moved to `all_required` ahead of its merge).

⚠ **Two corrections to how that number was reached, worth keeping because both were wrong in
the same way.** The first sweep claimed "zero declarations anywhere" having searched only the
mono-repo. A later table then listed `projects/amii_study/ondevice_profile.py:62` as a core
declaration; it is **untracked**, absent from `origin/main`, and was **deleted** at `0943d4b`
on the only two branches that ever held it — residue of a deletion, read out of a working tree.

> **The rule both misses point at: a claim about "the repo" is a claim about refs.** Use
> `git grep <ref>` / `git ls-files`, never `grep -rn` over a checkout — a checkout contains
> deleted files and other lanes' leftovers. And run `git log --all -- <path>` before calling a
> path absent, because a deletion commit changes the answer.

### 13.5 Environment

The shared `MindsOS` clone carries an **untracked `projects/amii_study/` tree** inside the
`main` checkout. It has already misled two cross-repo sweeps into reading it as tracked
content. Clear it or ignore it.

---

## 14. Round-5 findings (2026-08-06, CORE-C2R3 pre-build read-through @ `1063fd1`)

> **Re-verified at `fe529c1`** (merge of `origin/main` through `c97d99a`, which shipped the
> two-tier union view). **Every claim below held.** Line references are the post-merge ones;
> three drifted in `capacity_layer.py` and are corrected in place.

Every claim in §13 held. §12.1's *"the L2 knowledge layer cannot write a link"* holds **for
`KLWriteHandle`** and is **too narrow as a statement about the repo** — see §14.5. All six
findings below were read from the code, not inferred.

### 14.1 A compositional link cannot cross a `Metagraph`, and a brain holds four

`Metagraph.add_intergraph_edge` steps 1–2 (`mindsos_core/models/metagraph.py:1602-1611`) require
both endpoint graphs in `self.graphs` — one `Metagraph` instance. `add_intergraph_hyperedge`
applies the same rule to anchors and members. Endpoints are `(graph_id, node_id)` pairs; the
link dictionaries hang off the `Metagraph` (`metagraph.py:374,380`). There is no representation
for an endpoint in another metagraph.

Four instances exist in a running brain, none shared: KnowledgeLayer Global
(`knowledge_layer.py:208`), KnowledgeLayer Local(user) (`:243`, lazy), CapacityLayer Global
(`capacity_layer.py:160`, its own `create_global()`), CapacityLayer Local(user) (`:203`).
`boot.py:211,222` pass `kl` into `CapacityLayer` **for write-capacity bodies only** — no
metagraph crosses.

⟹ `pipeline → capacity` (C2R4's central link) is **inexpressible**, and so is every Local→Global
composition — which C2R5, C2R7 and the dual-scope resource graph all require.

**Reachability: DECLARED.** Nothing above the capacity level writes a compositional link today,
which is why the constraint has never been hit. **Ruled at ADR-0205 §amendment-4** — one
`Metagraph` per user; realm becomes a node property.

### 14.2 `Graph.remove_node` cannot see intergraph links

`mindsos_core/models/graph.py:483`. It collects `incident_edge_ids` from `self.edges` and
`incident_he_ids` from `self.hyperedges` — **intra-graph only**. A `Graph` holds no reference to
its containing `Metagraph`.

⟹ A node that is a **member of a compositional link can be removed**, and the link survives
pointing at nothing. No refusal, no cascade, no detection, at any `cascade` setting.
`mindsos_capacity/builtins/learn_parameter.py:139` already calls `handle.graph().remove_node`.

Two consequences, opposite in sign:

- ADR-0205 §8-as-amended and §am-1.5 state that taught **structure can never be removed**. That
  is false in practice — a composition can be gutted one member at a time. `remove_graph` guards
  compositional links (`metagraph.py:1055-1079`); `remove_node` does not.
- It is nonetheless **the only trigger derived dormancy has**. §am-3.3 requires dormancy to be
  computed on read rather than stored; a DOWN walk that finds a member gone is that computation.
  **C2R3 owns the detection**, since it owns the walk.

### 14.3 There is no adjacency index for intergraph links

`intergraph_edges` and `intergraph_hyperedges` are flat dicts whose only accessors are
`iter_intergraph_edges` / `iter_intergraph_hyperedges` (`metagraph.py:2233,2263`), both full
scans. `XRef` — a lower-traffic primitive — **does** have inverse indexes (`_xrefs_by_source`,
`_xrefs_by_target`, `metagraph.py:434-435`).

⟹ `CORE_RECONCILIATION_PLAN.md` §3.1's `walk(start, *, direction, ...)` is **O(all links) per
hop** as the substrate stands, in both directions. The existing consumer already pays it:
`mindsos_capacity/views.py:144` `_iter_edges` scans every intergraph edge per call, and
`outputs_of` / `inputs_of` / `producers_of` each call it. **C2R3 adds the index**, mirroring the
`XRef` pattern; `add_*` / `remove_*` / the loader maintain it.

### 14.4 `deprecate_intergraph_edge` does not exist

ADR-0205 §am-1.5 lists it — *"`deprecate_intergraph_edge` (Phase 10) raises the same"* — and
`confirmation_docs/INTERGRAPH_EDGES_DESIGN.md:296` says the same. `git grep deprecate_intergraph`
returns **documentation only**; no such method is defined anywhere in `mindsos_core`.

The three real refusals are `remove_intergraph_edge` (`metagraph.py:1676`),
`update_intergraph_edge_properties` (`:1701`) and the `__setattr__` gate on the `compositional`
field itself (`intergraph_edge.py:110-125`, Pushback 22-A). Terminality holds on those three; the
fourth citation is to a method that was planned and never built. Correct both documents.

### 14.5 §am-1.7's "zero consumers" is right about the hyperedge and wrong about the edge

§am-1.7 and `CORE_C2_DECISIONS.md` §4 read as *nothing outside core reads or writes an
intergraph link*. For `IntergraphHyperEdge` and the `compositional` flag that holds. For the
ordinary `IntergraphEdge` it does not:

- **writer** — `mindsos_capacity/capacity_layer.py:436,443` emit `PRODUCES` (capacity→DataState)
  and `CONSUMES` (DataState→capacity) on every registration, idempotently, guarded by
  `_has_intergraph_edge` (`:98-112`). This is ADR-0156's bipartite topology and it is **LIVE-WRITE**.
- **reader** — `mindsos_capacity/views.py:138-175` `_iter_edges` → `outputs_of`, `inputs_of`,
  `producers_of`. **LIVE-READ**, and it is the substrate the finder walks.

⟹ **C2R3 is not building a link mechanism from nothing.** It is unifying an existing one and
raising it to L2. Under ADR-0205 §10 — *one traversal primitive* — `CapacityLayerView` must
delegate to whatever `MetagraphView` gains, not keep a parallel scan. A second reader of the same
relation is the defect §10 was written to prevent, arriving from the direction nobody watched.

### 14.6 ADR-0206's status is `Accepted` on main; three artifacts say `Proposed`

`docs/decisions/adr/0206-planning-decomposition-confidence.md` front-matter `status:` and its
prose `**Status:**` line both read **`Accepted`**. `STATE.json` `pending_designs`
→ `core-c-reconciliation`, `confirmation_docs/CORE_C2R2_CONFIRMED.md` §5 and the C2R3 handoff
all state it is `Proposed` with §3 and §5 contradicted.

RULES §9: *"An ADR-level status change is FOUR edits."* None was made — the flip was recorded as
an intention in three downstream places and never executed in the ADR. This is the shape §13's
method note names: *an intention written in the past tense is indistinguishable from a fact.*

Separately, **ADR-0206 §amendment-1 carries no `**Amendment status:**` label**, which RULES §9
requires. ADR-0148 §amendment-1 is reported to have the same gap and is not re-verified here.

⟹ Two mechanical repairs, no design content, and they belong to whichever item next touches ADR
status truth.

### 14.7 A read that mints a Local, on the L4 dispatch path — ✅ FIXED

`mindsos_knowledge/learned_parameters_snapshot.py:64` —
`read_learned_parameter_snapshot` calls `kl.local_metagraph(user)` with **no `has_local`
guard**. `local_metagraph` lazily creates.

`mindsos_server/skills/records.py:111` guards the identical call and documents why:
*"``local_metagraph`` LAZILY CREATES, and materialising an empty Local while reading a roster
would run ahead of the durable boot that restores one. Reading must never mint state."* — the
ADR-0183 §am-6 hazard that broke `test_durable_roundtrip`, and the same finding
`CORE_C2_DECISIONS.md` §12.1 item 3 recorded from building C2R1.

**Reachability: LIVE-READ, and hotter than the guarded site.** The snapshot is frozen into every
request's `learned_parameters_snapshot` by `L4Dispatcher`, so this is the dispatch path — not a
roster read.

⟹ Two-line fix, precedent in the repo, **independent of ADR-0205 §amendment-4**.

✅ **FIXED** by the two-tier lane. `read_learned_parameter_snapshot` now guards with
`has_local`, using the same `getattr(kl, "has_local", lambda _u: False)` form `records.py`
uses. `_FakeKL` in `tests/learned_parameters/` gained `has_local` (defaulted `True`, so no
existing call site changed) plus a `local_metagraph_calls` counter — the fake did not model
the guard surface at all, so without that the guard would have silently skipped the Local
overlay and broken `test_reader_local_overrides_global_per_knob`. Two tests: no-mint, and
still-applies-local-when-one-exists.

*(This section read "NO OWNER" when §14 landed in #119. It was accurate at the time and is
struck here rather than deleted, because the reasoning for why it was homeless is what stopped
it staying homeless.)*

⚠ Related but distinct from §am-4.7 item 5, which says the lazy-create hazard *dissolves* under
one metagraph because no Local object remains to materialise. That is true of the future and
silent about the present: this instance is live today.

### 14.8 The two-tier override reads the collision in three places, and one is not an IRI collision

Established with the two-tier / union-view lane. **All three re-verified here at `fe529c1`**,
after `8400d6f` merged — items 1 and 2 are no longer second-hand.

1. `LocalPreferringView` (`mindsos_capacity/views.py:213`) — node-IRI collision.
2. `CapacityLayer._resolve_declaration` (`capacity_layer.py:752`) — node-IRI collision.
3. ⚠ **`read_learned_parameter_snapshot` (`learned_parameters_snapshot.py:63-64`) — NOT an IRI
   collision.** `_overlay` keys on `(parameter_set_iri, target_parameter_iri)` read from node
   **properties**, so two nodes with different IRIs can carry the same knob. Precedence comes
   from **calling `_overlay` twice over two containers** — `global_metagraph()` then
   `local_metagraph(user)` — with later-call-wins.

⟹ 1 and 2 die on the identity change. **3 survives the identity change and breaks on the
container change**, silently returning Global values with the suite still green. It needs an
explicit realm sort key and a test that goes RED.

Bounding the blast radius, verified: **`pending-promotions` does not resolve a collision**
(minting, role-prefix and allow-list references only); **C2R1's dual-scope `installed-skills`
unions rather than resolves** (`records.py:122` appends from both role-graphs, no same-IRI step);
and the **KL read path never did collision resolution at all** —
`mindsos_knowledge/metagraph_view.py:254` states *"Per Phase 14 PB-10: NO Local-specialisation
overlay"*. Collision-based override was only ever a capacity-layer mechanism plus this overlay.

### 14.9 A second persister method assumes realm == metagraph

`mindsos_server/persistence/local_persister.py` — the run-state wipe resolves the user's Local by
`find_by_name(self._metagraph_name(user_id))`, then matches
`(m:Metagraph {id: $mid})<-[:IN_METAGRAPH]-(g:Graph) WHERE g.role IN $roles` over
`episodic_memories`, `parameter-staging`, `pending-promotions`.

Under one metagraph the name has no referent, **and the role match reaches the Global graphs of
those same roles.** Its docstring promises *"leaving the durable role-graphs and the Metagraph
node in place"*; under one metagraph that promise inverts for three Global roles.

⟹ Same class as the `delete` hazard in §am-4.7 item 2, in a **second** method. Both deletion
paths need a RED test before the substrate is unified.

### 14.10 A FOURTH collision reader — the flat `_declarations` mirror, leaking Local into sessionless reads — ✅ FIXED

§14.8 names three collision readers. There is a fourth, and it is not a **view**, which is why
three separate reads missed it: `CapacityLayer._declarations` is a **realm-blind, IRI-keyed,
last-write-wins dict**. `self._declarations[declaration.iri] = declaration` at
`capacity_layer.py:409` and `:423`, inside `register_capacity`, **with no realm branch** — so a
Local registration overwrites the Global entry at the same IRI.

**Reachability: LIVE-READ, and it was leaking.** `get_declaration(capacity_iri)` takes **no
session** and read that mirror, so a sessionless caller could be handed **a user's Local
declaration**. That contradicts the invariant the view layer maintains and ADR-0071
§amendment-5 restates: *a sessionless caller is asking about the shared catalog and must not see
any user's Local realm.* `pipeline._view_for` enforces it; this registry did not.

Readers of the mirror: `mindsos_cli/commands/brain.py:356`,
`mindsos_intelligence/consolidation.py:54`, and `iter_monitors()` via
`mindsos_intelligence/monitor_subscription.py:52`.

✅ **FIXED** by the two-tier lane. `get_declaration` now reads the **Global capacity index**,
routed through `_maybe_build_lazy` so a metadata-only skill capability (ADR-0183 §am-5) still has
its function built on first resolve — reading the index raw would return an unbound declaration
and leave it unbound. It is now exactly the sessionless case of `_resolve_declaration`.

**Not a contract change, verified rather than assumed.** No public test pinned the merged
behaviour: `tests/phase_28/test_capacity_layer_register_capacity.py:64` asserts
`get_declaration(cap.iri) is cap` on a **Global** registration, and
`test_capacity_layer_local_wins.py` — the only test pinning Local-overwrites-Global — asserts on
the **private** `cl._declarations` dict, which the fix does not touch. Its docstring calls that a
"doc" of an internal consequence (R3 PB-36), not a public contract. **The mirror is unchanged**
and remains a non-authoritative Local-wins merge for enumeration (`iter_declarations` /
`iter_monitors`); only the sessionless lookup stops reading it.

⚠ Same shape as §am-4.7 item 5 and §14.7: **under one metagraph the mirror stops being a merge**
(one declaration per IRI) and the leak dissolves on its own. Item 5 is right about the future and
was silent about the present — this instance was live.

⟹ Under ADR-0205 §amendment-4, `_declarations` is a **fourth conversion site**, and the two tests
that pin the collision as executable contract —
`tests/phase_28/test_capacity_layer_local_wins.py` and
`tests/phase_30/test_invoke_local_wins_resolution.py` — convert with it.

### 14.11 The override mechanism §am-4 §3 declined to rule ALREADY SHIPS — as node properties

ADR-0205 §amendment-4 §3 rules the *principle* for what replaces override-by-IRI-collision
under one metagraph — **an override is topology, never identity**; owner-qualified IRIs are
rejected as location-encoded-in-a-reference — but declines to rule a *mechanism* on the
ground that no candidate has a consumer in C2R3.

**That ground does not hold. A mechanism is on `main` today:**

- `REF_GLOBAL_CAPACITY = "ref:global_capacity"` — `mindsos_capacity/identifiers.py:424`
- `"SPECIALISES"` is a declared ref type — `identifiers.py:438`
- `CapacityLayer.register_capacity(..., ref_to_global=<iri>, ref_type="SPECIALISES")` writes
  both — `capacity_layer.py:386`
- exercised by `tests/phase_28/test_capacity_layer_local_wins.py`, which asserts
  `local_node.properties[REF_GLOBAL_CAPACITY] == gcap.iri` and
  `properties[REF_TYPE_KEY] == "SPECIALISES"`

⟹ **The override-as-topology mechanism is half-built, and the built half is in the wrong
form: node PROPERTIES, not edges.** It satisfies the principle's *intent* — the override is
recorded as a relation to the thing it overrides — and violates its *mechanism*: **a walk
cannot traverse a property.**

That is ADR-0205's own anti-pattern — topology stored in properties rather than edges — and
the **third** shipped instance, after the missing `SPECIALIZES` DataState edge
(`C11`/`c11-datastate-subsumption`) and the pre-ADR-0156 `inputs`/`outputs` node properties
that the bipartite reframe retired.

⟹ The open item is therefore not *"choose a mechanism for a future override"* but
**"promote an existing property-encoded reference to an edge"** — which has a consumer
today, a test today, and a migration precedent in ADR-0156. Whoever rules it must also state
that such an edge **does not redirect existing compositions**: members are frozen, so using
an override means a **new composition on the same anchor**, never a repoint.

**Also unrecorded: §am-4.7 is missing two measurements it acknowledged.** Both were verified
in the C2R3 lane at `b041ebe` and confirmed in the metagraph-boundary coordination thread as
making §am-4.7 items 3 and 4 *cheaper than priced*; neither reached `main`:

1. **The injection seam already exists on BOTH sides for Global.**
   `CapacityLayer.__init__` takes `global_metagraph=` (`capacity_layer.py:134`, used verbatim
   at `:166`) and `KnowledgeLayer.bootstrap()` constructs via
   `cls(global_metagraph=global_mg, id_strategy=strategy)` (`knowledge_layer.py:204`).
   **Sharing one Global metagraph is boot wiring, not a core change.** Local has no such
   seam — `create_local(user_id)` is internal on both layers — and that is the real work.
2. **Roles are ENSURED, not GATED.** Nothing rejects an unknown role on a `Metagraph`;
   `_GLOBAL_NAMED_ROLES` / `_LOCAL_NAMED_ROLES` drive `kahn_sort` *ensure* loops, and
   `UnknownRoleError` is a `schema_for_role` **lookup miss**, not an add-time gate. Capacity
   roles are `capacity:`-namespaced. **The L2 closed role-set is not an obstacle to
   unification** — it is not even a check.

§am-4.7's claim is that it is *measured rather than estimated*. Recorded here so the two
measurements exist somewhere on `main`; amending §am-4.7 itself belongs to the C2R3 lane.
