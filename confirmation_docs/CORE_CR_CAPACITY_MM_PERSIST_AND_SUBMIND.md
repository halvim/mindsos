# CORE CHANGE REQUEST — capacity_mm persistence (reopen DQ-8) + SubMind resolver grounding

**Filed:** 2026-07-21
**Status:** LANDED — all decisions settled 2026-07-21 (reopen ADR-0202 + D-A..D-D). **Slice A
SHIPPED to `main` (`d82123e`, PR #62) 2026-07-21; Slice B SHIPPED to `main` (`5b07b8d`, PR #63)
2026-07-22; Slice C SHIPPED 2026-07-22 (gate 4292/0) — see `L5_SLICE_C_CONFIRMED.md`. All three
slices in; the capacity-writer surface freeze LIFTS.**
Build-reanalysis PB-1..PB-5 resolved — see §7; those §7 resolutions OVERRIDE the D-C wording in
§2.4 and the singular `capacity_root_ref` in §2.3.
**Supersedes:** `CORE_CR_SUBMIND_RESOLVER_MM.md` (the small "inject `mm`" CR — absorbed as the last slice here)
**Reopens:** DQ-8 / ADR-0202 (capacity_mm was ratified **live-only until WSD**; architect decision 2026-07-21 pulls capacity_mm persistence forward now)
**Relates:** the L5 umbrella CR (`CORE_CR_L5_KNOWLEDGE_AND_CAPACITY_MM_WRITERS.md`), ADR-0201, ADR-0176, ADR-0200, `CORE_CR_PHASE1_RESOLVE_MM.md`
**Consumer of record:** arc1/arc3 solve path (primary); the submind resolver (secondary)

---

## 0. What this CR is, and the decision behind it

The originally-filed submind CR was a 3-line "inject `mm` into `SubMindArbiter`." Three
architect constraints turned it into a substrate change:

1. **No designing around test preservation** — break shipped tests where the ideal design
   requires it; write new ones.
2. **Every MM persists into Episodes** — explicitly **reopens DQ-8/ADR-0202**, which had
   deliberately kept `capacity_mm` live-only. This is now intended, not an oversight.
3. **Replan must work** — the capacity writer collides on replan today.

So the real work is a **capacity_mm persistence substrate** (the reopened DQ-8), and the
submind wiring rides on top of it as the final slice.

**This reopening un-parked two decisions the umbrella CR had closed — both now RESOLVED 2026-07-21 (§2.4):**
- **DQ-4 / DQ-7 (retention & size).** Marked MOOT only because capacity_mm was live-only.
  Persisting reopens it — but node count is bounded by DQ-2 (one node per invocation-output;
  the "2416 components" is one node's payload *size*, not the node count), so this is a
  payload-encoding question, not a node-explosion one. → D-D.
- **The ADR-0182 codec problem.** capacity_mm payloads are arbitrary domain values, not the
  known dataclasses the chain graph `asdict`-ed. → D-C (inspectable encoding, not binary codec).

---

## 1. Findings from code review (true today)

### 1.1 capacity_mm is deliberately not persisted
`consolidate_task` persists only this task's **`intelligence_mm` chain graph** and points the
Episode's `mm_root_ref` at it (`consolidation.py:72–94`). Docstring: *"capacity_mm /
knowledge_mm stay live-only until WSD"* (`mm_persister.py:5–6`). The Episode's six fields
reference no capacity data (`builtins/consolidate.py:149–161`). ADR-0202 ratified this. **This
CR reverses that clause for capacity_mm.** (knowledge_mm stays live-only — Slice 3 / a later
CR; named here so it isn't dropped.)

### 1.2 No per-task room — only name-namespacing in shared graphs
`CapacityMMWriter` writes into **two fixed-role graphs**, `capacity:instances:datastates` /
`capacity:instances:capacities` (`capacity_mm_writer.py:49–50`, `:83–89`). Every task and
resolver writes into the same two graphs; instances are told apart only by the
`(task_id, run_ref, seq)` baked into their IRIs (`:132`, `:161`). There is no per-task
subgraph to hand to a persister — you'd filter the shared soup by task-id. Contrast the chain
graph, which Slice D8-B **already** made per-task and persists cleanly.

### 1.3 Replan collision (latent, unexercised)
`pipeline_run_ref` **defaults to `task_id`** (`pipeline_execution.py:82, 112`) and `seq`
restarts at 0 per writer (`capacity_mm_writer.py:91–94`). A second pipeline run under the same
task (a replan) re-mints identical IRIs and **overwrites** the first run's nodes. Nothing
threads a distinct `run_ref` today, so it's latent — fires the instant replan grounds. (The
chain writer had the analogous collision; Slice D8-B fixed it for the chain, not for
capacity.)

### 1.4 Persisting the DAG is new capability, not a mirror
`FalkorMMPersister.persist` writes **one graph, nodes only, no edges** — chain artifacts are
*"nodes-only (refs are IRI fields, not graph edges)"* (`mm_persister.py:20–22, 71–79`). But
capacity_mm's grounding DAG is **two graphs wired by PRODUCES/CONSUMES intergraph edges**
(`capacity_mm_writer.py:147–155`) — the edges *are* the structure. A nodes-only single-graph
persist throws the DAG away. Persisting capacity_mm is genuinely new work.

---

## 2. Design

### 2.1 Per-task/run capacity graph (replaces shared fixed-role graphs)
Key each pipeline run's instance graph(s) on `(task_id, run_ref)` instead of the two global
fixed-role graphs. Mirrors what Slice D8-B did for the chain graph. This simultaneously: fixes
replan by construction (fresh graph → fresh `seq` space), gives real isolation, and makes the
**persistence unit a single per-task object** — the thing `mm_persister` already knows how to
take.

**D-A — RESOLVED 2026-07-21: one graph per run.** Both instance node-types (CapacityInstance +
DataStateInstance) live in a single per-run graph; PRODUCES/CONSUMES become **intra-graph**
edges. Drops the L3-mirroring two-graph split (inherited symmetry, no instance-level consumer)
and, critically, sidesteps intergraph-edge persistence (§2.4) — the persister only ever handles
one graph with internal edges. Removes work rather than adding it.

### 2.2 Replan fix
Falls out of 2.1. Independently: **remove the `run_ref = task_id` default** — require a fresh
per-run ref (the `pipelinerun:` IRI) from every caller (solve-path Step 5 and the submind).
The silent default is the trap.

### 2.3 capacity_mm → Episode persistence (the reopened DQ-8)
1. Persist the task's per-run capacity graph **including edges** at consolidation, via an
   extended `MMPersister` path (new: edge-aware, or one-graph-with-intra-edges per D-A).
2. Add `capacity_root_ref` to the Episode record, mirroring `mm_root_ref`.
3. Reverse the ADR-0202 "capacity_mm live-only" clause; correct `consolidation.py` /
   `mm_persister.py` docstrings.

### 2.4 D-C / D-D — RESOLVED 2026-07-21

**Purpose that decides fidelity (Henrique, 2026-07-21):** re-run exists to find *new, more
efficient* pipelines/capacities for the **same task**, and to **audit** what/how was done. The
old run is persisted for **comparison against a new run** and for **audit** — it is never fed
back through the executor. So the fidelity required is *inspectable + re-runnable-from-input*,
**not** faithful binary reconstruction. `dream_cycle.py:12-14`'s `replay_recorded` (bit-perfect
value replay) stays WSD-gated; only `re_execute_capacities` (re-run from input) is in scope.

**D-C — per-DataState *inspectable* encoding. Nothing dropped, nothing stored as an opaque blob.**
- Persist the full DAG: all CapacityInstance + DataStateInstance nodes + PRODUCES/CONSUMES edges.
- Encode every payload to an **inspectable dict/JSON** via a per-DataState `to-dict` convention
  (lean on the existing `ShapeDescriptor`); primitives pass through unchanged. A grid → nested
  list; a component set → structured records.
- **Fidelity-critical nodes:** the `raw_task` root (re-run the same task through a new pipeline)
  and the **terminal outputs** (compare answers). Intermediates persist as inspectable records
  for audit.
- **Explicitly NOT** a faithful binary codec (`replay_recorded`). Re-run finds *new* pipelines;
  it never replays old values. That codec stays WSD-gated.
- **Cost, stated honestly:** every DataState type the brains use needs a `to-dict`. Bounded to
  actual DataState types, and it **is** the product's auditability feature (not scaffolding), so
  the build earns its keep — but it is real work, not free.
- **Scope assumption on "comparison":** same input → compare **final answer + cost/structure**
  (step count, capacities used), **not** old-step-N vs new-step-N internals (different pipelines
  don't share steps; step-level cross-pipeline diff is ill-defined). Revisit only if step-level
  comparison becomes a requirement.

**D-D — persist the full per-task DAG; no truncation.** Audit needs the whole trace, so
leaves-only is out (and it broke grounding anyway). Node count is **already bounded by DQ-2**
(one node per invocation-*output* — the "2416" is one node's payload *size*, not 2416 nodes).
Payload size is bounded by the D-C inspectable encoding. Long-resident-session accumulation is
**Episode-level eviction** (PB-QQ, deferred) — not per-node graph truncation in this CR.

### 2.5 SubMind wiring (final slice, small)
1. `SubMindArbiter.__init__` takes a **mandatory** `mm` (D-B — RESOLVED 2026-07-21: inject the
   real MentalModel object directly — the same one the solve path threads and that
   `execute_pipeline` already consumes, so both paths write identically with no executor
   contract change. **Not** the dispatcher's `mm_handle`, which goes read-only in Slice 3 /
   ADR-0200. Rejected the narrow-writer wrapper: tidier on privilege but costs a shared-executor
   refactor for a gain that prevents no real bug here — L4 is the legitimate L5 writer).
2. `_run_resolver` → `execute_pipeline(..., mm=self._mm, pipeline_run_ref=<fresh per run>)`.
3. Wire at `intelligence_layer.py:189`.
4. Fallback path (`_fire_fallback`, `submind_arbiter.py:217`) is a single dispatch — unaffected.

Note the Phase-1 carve-out ruling (`CORE_CR_PHASE1_RESOLVE_MM.md` rec (a)): interpret-resolve
stays **MM-less permanently**. So "mandatory MM" scopes to the **solve + submind** paths, not
every `execute_pipeline` call. The optional `mm=None` at the pipeline layer is retained for
that sanctioned carve-out — consistent with breaking tests only where the design demands it.

---

## 3. Sequencing & conflict (answers "do I stop other CRs?")

**You do not freeze the program.** Only the L5/MM lane serializes — and it already does by
design. With DQ-8 reopened, this CR becomes the **trunk of that lane**:

- **Serializes behind this CR:** the umbrella's unbuilt **Slice 3** (knowledge writer +
  `mm_handle`) should build **on top of** the new per-task/persist model, not race it; the
  **submind** slice (§2.5) is the last slice here; the **Phase-1 carve-out** CR is docs-only
  and can be ruled anytime.
- **Runs in parallel, no conflict** (different files/surfaces): dataset role (CR#5, L2/knowledge
  tagging), skill activation / brain verbs, the DataState `group→collection` rename. Let them
  proceed.
- **The one real hazard:** anything that grounds via `execute_pipeline` on the shared-graph
  model (a premature Step 5 wiring) must **not** merge before §2.1–2.2 land, or it bakes in the
  collision and the shared-graph shape this CR is replacing.

So: don't stop the program; **do** freeze the *capacity-writer surface*
(`capacity_mm_writer.py`, `pipeline_execution.py`, `consolidation.py`, `mm_persister.py`) to
this CR until it lands, and land it before Slice 3.

### Slice order
1. **Slice A — scope + replan: ✅ SHIPPED to `main` (`d82123e`, PR #62) 2026-07-21.** Per-run
   capacity graph (D-A) + killed the `run_ref` default; PRODUCES/CONSUMES now intra-graph edges;
   Slice 2 tests rewritten. Gate 4281/12/1xpass/0. Confirm `confirmation_docs/L5_SLICE_A_CONFIRMED.md`,
   ADR-0201 amendment-2. Read those + §7 before Slice B.
2. **Slice B — persistence: ✅ BUILT (branch `feat/capacity-mm-persist-slice-b`; Linux gate
   PENDING).** Edge-aware persist of the per-run capacity graph + `capacity_root_ref` (task-level
   index graph, PB-2) on the Episode + the per-DataState inspectable encoding (PB-1 `encode` field +
   dispatch) + the PB-4 nodes-only-snapshot → edges fix; persist the full DAG, no truncation (D-D).
   Inert until Step 5 (PB-3), synthetic phase-48 tests. Confirm
   `confirmation_docs/L5_SLICE_B_CONFIRMED.md`; ADR-0202 am-1 + ADR-0176 am-1.
3. **Slice C — submind wiring: ✅ SHIPPED 2026-07-22** (branch `feat/capacity-mm-persist-slice-c`,
   gate **4292/12/1xpass/0**, baseline 4287 + 5). §2.5 (D-B): mandatory real `mm` on
   `SubMindArbiter`; `_run_resolver` → `execute_pipeline(mm=self._mm,
   pipeline_run_ref=pipelinerun:<task_id>)` (fresh per-run ref); wired at `intelligence_layer.py`
   `start()`; fallback unaffected. Tests = grounding+edges / concurrent / replan / MM-less carve-out
   (+ null-mm guard). ADR-0189 am-1. Confirm `confirmation_docs/L5_SLICE_C_CONFIRMED.md`. **CR fully
   lands; freeze lifts.**

---

## 4. Decisions
**Resolved (2026-07-21):**
- **Reopen Slice 2 / ADR-0202** — rewrite the shipped writer, reverse the live-only clause. Approved.
- **D-C** — per-DataState inspectable (`to-dict`) encoding; full DAG; fidelity on root+terminals;
  intermediates inspectable for audit; NOT the binary replay codec. (§2.4)
- **D-D** — persist the full per-task DAG, no truncation; size bounded by DQ-2 + D-C encoding;
  growth handled by deferred Episode eviction. (§2.4)

- **D-A** — one capacity graph per run (intra-graph edges); drops the two-graph split, sidesteps
  intergraph-edge persistence. (§2.1)
- **D-B** — inject the real MentalModel directly into the arbiter (not via `mm_handle`); no narrow
  wrapper, no executor contract change. (§2.5)

**All CR decisions settled 2026-07-21. No open blockers — ready for build (Slice A → B → C).**

## 5. ADR impact
- **ADR-0202** — amend: reverse the "capacity_mm live-only" clause; add per-task capacity graph
  + persist. (knowledge_mm still live-only.)
- **ADR-0201** — per-task/run graph model; run_ref no longer defaults to task_id.
- **ADR-0176** — Episode gains `capacity_root_ref`; retention policy (D-D).
- **ADR-0189** — submind resolver grounds + persists under its own `task_id`/`run_ref` scope.

## 6. Tests (replace Slice 2's set where needed)
1. Resolver run with injected MM writes one CapacityInstance + output DataStateInstance(s)
   **with PRODUCES/CONSUMES edges** into its own per-run graph.
2. Two concurrent resolvers → **distinct** per-run graphs, no overwrite.
3. Replan (second run, same `task_id`) does **not** overwrite the first run's nodes.
4. Consolidation persists the per-run capacity graph **and its edges**; Episode's
   `capacity_root_ref` resolves to it; round-trips through the ADR-0182 codec (exercises D-C).
5. Retention policy honored (D-D): the persisted graph holds exactly what the policy admits.
6. Resolver instances do not collide with a concurrent main-task solve's instances.
7. interpret-resolve (MM-less carve-out) unchanged — no MM, no persist.

## 7. Build-time reanalysis — PB resolutions (2026-07-21, user-agreed)

A skeptical reanalysis (5 passes, premises grounded against code) surfaced 6 pushbacks before
Slice A. All adopted by the architect. These **override** the earlier prose where noted. Full
rationale + the grounded code findings live in project-memory `capacity-mm-persist-reopen-dq8.md`
— read it before Slice B.

- **PB-1 (D-C foundation) — overrides §2.4's "lean on ShapeDescriptor."** `ShapeDescriptor.to_dict()`
  serializes the DataState *type shape*, not the runtime value; per-value encoders for brain
  DataState types are brain-owned; `value_codec.encode_node_value` hard-throws on anything not
  primitive/dict/list. → **Resolution C:** add an optional `encode` field to the `DataState`
  declaration (brain-supplied); core dispatches on it; **default (A)** = require the value already be
  primitive/dict/list, else `PersistenceError` at persist. Core ships the mechanism only — arc's
  encoders are a brain follow-up.
- **PB-2 (retention vs audit) — overrides the singular `capacity_root_ref` in §2.3.** Replan (D-A)
  yields N per-run graphs per task, but one Episode ref can't address all of them, and D-D exists to
  compare old vs new runs. → **Resolution B:** a task-level capacity **index graph** (one node per
  run → each run graph); `capacity_root_ref` points at the index.
- **PB-3 (no in-CR trigger).** The submind resolver runs the writer but never calls `consolidate_task`;
  the only consolidation of a solve run's capacity graph is out-of-CR Step 5 (`execution.run` →
  `execute_pipeline`). → **Resolution A:** ship Slice B behind synthetic tests, documented
  inert-until-Step-5 (matches trunk-of-lane intent).
- **PB-4 (edge persistence) — RESOLVED BY INSPECTION; NOT a cost center.** `GraphRepository.persist`
  already writes edges (step 3, batched by rel-type); `reconstruction.load_graph` reconstructs them;
  `tests/_shared/graph_equality.assert_graphs_equal` compares them; and
  `tests/phase_07/test_client_falkor_integration.py::test_graph_repository_round_trip` (live Falkor,
  in the passing gate) already round-trips a graph WITH an intra-graph edge. Residual Slice-B work is
  small: `FalkorMMPersister.persist` snapshot copies **nodes only** (`mm_persister.py:72-79`) → extend
  it to copy `graph.edges`. No separate spike needed.
- **PB-5 (persist-ahead-of-consumer).** `capacity_root_ref` has no v1 reader (dream reconstruction is
  WSD-gated), exactly as `mm_root_ref` already dangles. → **Resolution A:** proceed (architect call);
  eyes open that the D-C cost is paid before a reader exists.

**Any of these may be revisited if new decisions arise.**
