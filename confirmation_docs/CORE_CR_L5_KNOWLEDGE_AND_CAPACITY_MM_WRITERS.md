# CORE CHANGE REQUEST — L5 has three rooms and only one door

**Filed:** 2026-07-15 · joint arc1+arc3 core chat
**Resolved:** 2026-07-16 · design converged (core/L5 + arc rulings). See §Resolution.
**Consumer of record:** arc1 (D1.6/D1.7/D1.8 — full task lifecycle); arc3 next
**Status:** RESOLVED. **Slice D8-B/3b BUILT + GATE-GREEN 2026-07-17** — branch
`fix/l5-per-task-chain-persist`, PR #52 (halvim/mindsos), full gate 4223 passed / 0 failed on live
Falkor. Slices 0 / 1 / 2 / 3 (§Slice plan) NOT built. **live-only** (per-task chain persist;
capacity/knowledge deferred to WSD).
Resolved build detail: task-unique writer scope = `task_id` when supplied, else a per-orchestrator
counter (`Orchestrator._writer_scope`).
**Version impact:** phase-shaped (the capacity writer deletes the blackboard and flips the
empty-room test); the DQ-2 vocabulary itself is additive. See §Blast radius.

---

## The defect

`MentalModel` allocates three sub-MMs (`mindsos_intelligence/mm.py:62-64`):

```python
self.knowledge_mm    = _new_sub_mm("mm:knowledge")
self.capacity_mm     = _new_sub_mm("mm:capacity")
self.intelligence_mm = _new_sub_mm("mm:intelligence")
```

`sub_mm_for_iri` (`mm.py:68-75`) routes by IRI namespace and raises `KeyError` on anything
unowned — a closed routing table. Verified by `tests/phase_46/test_three_sub_mm.py:34-37`:

| IRI | room |
|---|---|
| `ontology:Person`, `episodic:e1` | `knowledge_mm` |
| `capacity:text:tokenize`, `datastate:nlu.tokens` | `capacity_mm` |

**Only `intelligence_mm` has a writer.** `ChainArtifactWriter` (`chain_artifacts.py:166`)
writes *"the `chain` graph inside `mm.intelligence_mm` under the MM writer lock"*
(`chain_artifacts.py:7`); its nine `emit_*` methods are all chain artifacts (HintSet,
MappingResult, Milestone, Plan, Pipeline, PipelineRun, TaskRun, ReplanRecord,
StepExecutionRecord).

**`knowledge_mm` and `capacity_mm` have no writer, no reader, and no production caller.**
Repo-wide grep (`*.py`): they appear only in `mm.py` (construct / route / deep-copy) and in
two test files. And `tests/phase_47/test_chain_artifact_emit.py:79-80` **asserts they stay
empty**:

```python
assert sum(len(g.nodes) for g in mm.knowledge_mm.graphs.values()) == 0
assert sum(len(g.nodes) for g in mm.capacity_mm.graphs.values()) == 0
```

So: **MindsOS ships an intelligence-MM. It does not ship a knowledge-MM or a
capacity-MM.** L5 is the chain, not the working memory.

> **Resolution note (2026-07-16):** "no writer" is imprecise — `MMResolver` (`mm_resolver.py`)
> is the *designed* knowledge-MM writer: it pins `(iri, version)` correctly but stores nodes in
> a shadow dict (`self._instantiated`), never the graph, and is **unwired** (the live
> `mm_handle` is the raw `MentalModel`, which lacks `get_or_instantiate`). The real defect is
> **shadow state violating the `mm.py:1-8` "no shadow state outside the MM" invariant**, in the
> executor blackboard *and* the resolver.

## Three consequences, all currently misattributed to the brains

1. **Phase 1 fetches the task and throws it away.** `phase_1.run` (`phase_1.py:283-297`)
   calls `interpret()`, which runs the reference-resolve chain and returns
   `InterpretationResult.resolved_reference` — then builds a `Phase1Result` that has **no
   such field**. The value is computed and dropped. Phase 2 receives only
   `(mapping_result_ref, task_pattern_iri)` (`orchestrator.py:161-163`), so
   `planning.derive_initial_plan` plans a task it has never seen. There is nowhere to put
   the task, so it is discarded.

2. **`execute_pipeline` bypasses L5 entirely.** It threads DataState values step-to-step on
   a **Python blackboard dict** (`pipeline_execution.py`), not the MM. Core already has a
   per-task home for L3 results — `capacity_mm`, per its own routing — and the executor
   writes a dict instead.

3. **Both brains "not using L5" is not the brains' debt.** arc1 emits a bare `TaskRun` with
   no chain behind it; arc3 never touches `stack.mm`. Both recorded this as their own gap
   (arc3 conflict C9). It is not. There is nothing to use.

`ADR-0200` built `reads_mm` → `mm_handle` as a **read** surface for capacity bodies. It
reads two rooms that are empty by construction.

## Proposed

Two writers, one CR, because they share every design decision (instance vocabulary, IRI
minting, lock discipline, retention):

- **Knowledge-MM writer** — L4 instantiates the L2 content a task uses into `knowledge_mm`.
- **Capacity-MM writer** — L4 records L3 capacity + DataState instances (the results) into
  `capacity_mm` as the pipeline executes.

Both are L4-side: **L4 is the sole writer to L5** (HANDOFF §3.1), and `mm_handle` is
read-only (ADR-0200). A capacity cannot write its own result into the MM; the executor
must.

---

## Resolution (2026-07-16 · design converged)

**Framing.** Finish the ADR-0165/0166 invariant ("no shadow state outside the MM"). The MM
becomes the **live** working memory; cross-session persistence stays out of scope (D8-B).

### Verified findings — corrections to the as-filed text
- **`DataStateInstance` / `CapacityInstance` do not exist as classes.** `mindsos_instances`
  ships `NodeInstance / CompositeInstance / …`; build the two as **typed `NodeInstance`s**
  (ADR-0201). (`CompositeInstance` *does* exist — `registry.py:33`; the earlier "not as DataState
  carriers" note rested on a truncated grep and is dropped.)
- **`mm_handle` swap blast radius is empty.** No non-test body reads `mm_handle`; no shipped cap
  declares `reads_mm=True`. Swapping the raw `MentalModel` → `MMResolver` breaks nothing (Slice 3
  de-risked).
- **`XRef` is a shipped first-class row, not a node** (`core/models/xref.py`, ADR-0128) → no
  `sub_mm_for_iri` hazard; `add_xref` self-validates; `validate_xref` (KL-scoped, ADR-0139 §am-1)
  is untouched.
- **No sub-MM is persisted.** `Episode.mm_root_ref = intelligence_mm.metagraph_id`
  (`consolidation.py:69`) **dangles** — nothing writes the MM to Falkor. `consolidation.py:10`'s
  "persisted by the L0 Falkor persister (Phase 44)" is **false** (Phase 44 = KL Local only).
- **`deep_copy` does not produce an independent MM.** `copy.deepcopy` preserves `metagraph_id`
  (+ identity registration + graph ids), so clone and original share ids — a latent bug the raw_task
  provenance XRef makes live. Contradicts `mm.py:7`.
- **Cross-task chain collision — live today, independent of this CR.** The `ChainArtifactWriter`
  scope is the orchestrator constant `"brain"` (`boot.py:171`) and `_seq` resets per
  `run_lifecycle`. Two tasks in one resident session both mint `taskrun:brain:1`, `hintset:brain:1`,
  … into the *same shared chain graph* → (a) node-id collision in the graph, and (b)
  `episode_id = task_run.iri` collides, and consolidation is idempotent on `episode_id`, so
  **task 2's Episode dedupes against task 1's**. This is a correctness bug the per-task scoping below
  fixes. **(Confirmed live by the gate — the fix is what makes the multi-task path correct.)**
- **Persist-codec gotcha — found by the gate (`test_durable_roundtrip`).** Chain nodes hold dataclass
  values (HintSet/TaskRun/…) that the ADR-0182 value codec (`value_codec.encode_node_value`) rejects —
  it takes only primitives / dict / list. `FalkorMMPersister` persists a **snapshot** of the chain
  graph with node values reduced via `dataclasses.asdict` (same `graph_id`), serialized at persist
  time so `TaskRun.status` etc. capture their final state. L4-local fix; no Core codec change.

### New decisions (beyond the six as-filed)
- **DQ-7 — Episode payload-retention: MOOT** under D8-B.
- **DQ-8 — persist the MM? → per-task chain scoping** (reframed from "persist `intelligence_mm`";
  absorbs option 3b). One lever: make the `ChainArtifactWriter` scope **task-unique** and key the
  chain graph on it. That single change (a) fixes the collision above, (b) bounds persist to
  O(task) — persist just this task's chain graph via a narrow injected `MMPersister`, since
  `GraphRepository.persist` is a full re-walk with no add-side dirty tracking, and (c) gives a real
  per-task `mm_root_ref` (the task's chain graph_id) instead of a session-shared blob. Also correct
  the false `consolidation.py:9-10` clause. `capacity_mm`/`knowledge_mm` stay live-only until WSD.
  Verified safe: `mm_root_ref` is an opaque `EPISODE_CONTENT_FIELDS` string
  (`episodic_memories.py:76`), not typed/validated as a metagraph ref, and nothing dereferences it.
  (Rejected: D8-A drop-the-field, and 3a shared-MM full re-walk / blob ref.)
- **deep_copy — fix independence as its own slice (Slice 1), RATIFIED.** Regenerate the clone
  sub-MM `metagraph_id`s **and graph ids** (now that `mm_root_ref` = a chain graph_id) + remap
  `XRef`/identity. Own slice (touches core element-key identity, `metagraph.py:1114`); must land
  **before** Slice 2, which writes the provenance XRef that makes the latent bug live.

### Slice plan
- **Slice D8-B / 3b — per-task chain scoping + persist. [BUILT + GATE-GREEN — PR #52, 4223/0]**
  Task-unique writer scope (`Orchestrator._writer_scope`: `task_id` or a per-orch counter) + per-task
  chain graph (`chain_artifacts._chain_graph(mm, scope)`, cached via `writer.chain_graph()`); persist
  that graph's **dict-snapshot** at consolidation via the injected `MMPersister`
  (`mindsos_intelligence/mm_persister.py`, wired on the durable `boot.py` path; `None`-no-op
  ephemeral/`simplified`); `mm_root_ref` → the task's chain graph_id; corrected `consolidation.py:9-10`.
  Test updated: `phase_48/test_consolidation_seam.py`.
- **Slice 0 — DQ-2 vocabulary (ADR-0201, additive):** typed `DataStateInstance`/`CapacityInstance`,
  two-graph bipartite mirroring L3, composite scope, node+edge instancing.
- **Slice 1 — deep_copy independence:** regenerate clone sub-MM ids **+ graph ids** + remap
  `XRef`/identity.
- **Slice 2 — capacity writer:** delete the blackboard; write the grounding DAG; carry
  `resolved_reference` into Phase 2 (the Phase-1 drop fix); add the nullable raw_task provenance
  XRef.
- **Slice 3 — knowledge writer + `mm_handle`:** finish `MMResolver` into the graph, wire it as the
  handle (un-inert `reads_mm`). Its corpus-entry instantiation is a **prerequisite** for the arc1
  provenance XRef (`add_xref` target-existence); arc3 (no XRef) is clean capacity-first.

---

## Design decisions — as-filed (rulings inline; see §Resolution)

**DQ-1 — the task's identity.** The ARC task corpus lives in L2 (arc1 D1.7). An instance of
it routes to `knowledge_mm` (`ontology:*`). But the same content flowing through pipelines
is `datastate:arc.raw_task` → `capacity_mm`. **Same content, two rooms, two namespaces.**
Which is it, and does the other hold a reference? This is D1.7 resurfacing inside the MM
and it must be answered once for both brains.
→ **RESOLVED (arc): B — capacity-canonical.** raw_task DataState is the grounding-DAG root;
`knowledge_mm` never holds the ingress. Provenance = nullable first-class `XRef`
capacity_mm→knowledge_mm (**T2**), `ref_type=INSTANCE_OF`, target = the pinned corpus-entry
instance in `knowledge_mm` (arc1) / `None` (arc3); `validate_xref` untouched (**M1**).

**DQ-2 — instances, not types.** A DataState IRI is a **type**. One task produces many
instances of one type (arc1: 8 grids, 2416 components). `capacity_mm` therefore cannot hold
one node per DataState IRI — it needs minted per-instance IRIs via `mindsos_instances`
(`ElementInstance` / `CompositeInstance`, ADR-0132). What is the minting convention, and
does `sub_mm_for_iri` still route the minted IRI correctly? (It raises `KeyError` on an
unowned namespace — an instance IRI that does not start with `datastate:` would not route.)
→ **RESOLVED + RATIFIED 2026-07-16 (ADR-0201):** one `DataStateInstance` per invocation-**output**
(payload = value; 2416 components = one payload); typed `NodeInstance`s (mirror L3's
`NODE_TYPE_DATASTATE`/`CAPACITY` plain nodes); two-graph bipartite mirroring L3
(`capacity_layer.py:411,418`); node+edge instancing; composite scope via a **dedicated
`datastate_instance_iri()` builder** that bypasses the type validator (`datastate_iri()` rejects
`#`/`:`, `identifiers.py:223`) — `#` guards type-vs-instance, type stored as a node property. See
ADR-0201 §Minting.

**DQ-3 — does the blackboard stay?** Either `execute_pipeline` writes `capacity_mm` and
reads from it (L5 *is* the blackboard), or it keeps the dict and mirrors into the MM
(two sources of truth). The first is architecturally right and touches the executor's hot
path; the second is cheap and dishonest.
→ **RESOLVED: L5 IS the blackboard** — the invariant decides it; the dict is the shadow-state
violation. Delete it; `capacity_mm` is source of truth; a run-local type→instance-IRI index
handles routing (IRIs, not values). Hot-path change → phase-shaped.

**DQ-4 — retention / size.** The MM is **retained by default** and consolidated into an
Episode on every terminal path (ADR-0176, Phase 48). Writing every intermediate DataState
into `capacity_mm` means every Episode carries every intermediate value — arc1 measured
2416 components in one run. Storage retention policy is already deferred (PB-QQ; Phase 48
ships monitoring only). **This CR could make that deferral untenable.** Options: write all;
write leaves only; write under a policy flag.
→ **SUPERSEDED by DQ-8.** Premise is wrong: nothing is persisted today (`mm_root_ref` dangles),
and node count is already bounded by DQ-2 (per-invocation, not per-element). Under D8-B,
capacity/knowledge stay live-only; retention/prune (DQ-7) is moot until WSD.

**DQ-5 — L2 instances: pin or copy?** The D'1 retention model is *"version-IRI freeze +
pin-at-instantiation + lazy inline-on-retire"* (CLAUDE.md L5; Phase 48 `retention.py`).
So `knowledge_mm` should hold **pinned version-refs** to L2 nodes, not copies. Confirm, and
confirm what happens when the pinned version retires mid-task.
→ **RESOLVED: pin** (code-confirmed — `MMResolver` `PinnedRef` + `retention.py` inline-on-retire).
Mid-task retire: the task reads its pinned version regardless of later source writes.

**DQ-6 — lock discipline.** `ChainArtifactWriter` writes under the MM writer lock
(`mm.lock`, `RWLock`). Both new writers must take it. The capacity-MM writer runs on the
per-task worker thread inside `execute_pipeline` — confirm no lock inversion against the
existing chain writes.
→ **RESOLVED:** single per-session `mm.lock`; **never held across a `dispatch`**; per-step
writes between dispatches; reads under `read_locked`. Same lock as the chain writer →
contention, not inversion.

## Additive-inertness

**Partial — and this CR does not clear the §0 gate cleanly.** The DQ-2 vocabulary (Slice 0) is
additive; the **capacity writer is not** (it deletes the blackboard and flips the empty-room
test). Specifically:

- `tests/phase_47/test_chain_artifact_emit.py:79-80` **asserts both rooms stay empty** and
  must change. That test is the pin on today's behaviour.
- DQ-3 = "L5 is the blackboard" changes `execute_pipeline`'s hot path — not additive.
- DQ-8 (per-task chain scoping) touches the shipped Phase-48 consolidation path **and** the chain
  writer (`chain_artifacts`, `orchestrator.run_lifecycle`) — the collision fix is not additive.

## Tests

1. `knowledge_mm` populated after Phase 1 for a task with a resolved reference; the value is
   readable via `mm_handle` from a `reads_mm=True` cap (Slice 3).
2. `capacity_mm` populated after `execute_pipeline`; one instance per invocation-output, not per
   DataState type (DQ-2); every DataStateInstance grounds to raw_task via produces/consumes.
3. `sub_mm_for_iri` routes every minted instance IRI without `KeyError`.
4. `deep_copy`: forked sub-MMs have **distinct** `metagraph_id`s **and graph ids**, and a provenance
   XRef resolves within the fork, not the original. **(Retarget required — `deep_copy` does NOT do
   this today; the as-filed "already does" was wrong.)**
5. Replace `test_chain_artifact_emit.py:79-80` — assert the rooms hold what the run put
   there, not that they are empty.
6. Consolidation: an Episode over a populated MM round-trips through the ADR-0182 codec;
   `mm_root_ref` resolves to *this task's* chain graph (per-task scoping).
7. `simplified=True` bypass unaffected.
8. Lock: a probe dispatcher asserts `mm.lock` is unheld at dispatch time.
9. **Multi-task session (collision regression):** two `run_lifecycle` calls on one Orchestrator
   produce distinct `taskrun`/`episode_id` (no Episode dedup) and distinct chain graphs.
10. Persist is O(this task's chain): persisting task 2 does not re-walk task 1's chain graph.

## Blast radius

`mindsos_intelligence/`: `mm.py` (deep_copy independence — metagraph + graph ids),
`pipeline_execution.py` (capacity writer), `phase_1.py` (the drop at `:283-297`),
`orchestrator.py` (`:161-163` Phase-2 payload; thread a task-unique token into the writer),
`chain_artifacts.py` (task-unique scope + per-task chain graph), `mm_resolver.py` (write graph +
wire as `mm_handle`), `consolidation.py` (per-task `mm_root_ref` + docstring). Plus a narrow
`MMPersister` wired at `mindsos_server/boot.py` (sole Orchestrator site). Plus `mindsos_instances`
(build the two instance types). Plus the Phase-47/48 test suites.

**This is the largest of the four CRs filed by this chat and the only one that is not a
small additive fix.** The capacity writer (DQ-3 = "L5 is the blackboard") is phase-shaped.

## ADR

- **New: ADR-0201** — `docs/decisions/adr/0201-capacity-mm-instance-vocabulary.md` (DQ-2
  vocabulary + minting + topology).
- **Amends:** ADR-0165/0166 (rooms now written); ADR-0200 (`mm_handle = MMResolver`);
  ADR-0176/0180 (DQ-8: per-task chain graphs persisted at consolidation; `mm_root_ref` → chain
  graph_id; drop the false persistence claim).
- **Untouched:** ADR-0139 §am-1 (`validate_xref` deferral).

## Why core and not the brains

L4 is the sole writer to L5. No brain can fix this. Both arc1 and arc3 have independently
recorded "L5 unused" as their own debt (arc3 C9, arc1 B4) — it is core's. Every consumer
that wires a task into `run_lifecycle` hits the Phase-1 drop and the executor's blackboard.
