# CORE — verified findings

**Filed:** 2026-07-31, core reconciliation chat.
**Verified at:** `origin/main` `b612c93` (re-confirmed unchanged from `644e91c` →
`01e4d0d` → `9fcb694` → `fafc679` → `b612c93` across every file cited here;
`9879a71` and `b612c93` are docs-only).
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
