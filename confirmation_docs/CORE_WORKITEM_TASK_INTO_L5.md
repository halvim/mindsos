# CORE WORK ITEM — load the resolved task into L5 (make it reach the solve)

**Type:** sequencing work item — orders existing CRs; not a new design.
**Status:** Slices 0 + 1 + 2 + 3 ALL SHIPPED to main. **Only out-of-CR Step 5 (`execution.run` →
`execute_pipeline`) remains** — the true end-to-end blocker for `arc solve task 7`. Steps 1-4 gave
the task a home in L5 (capacity_mm grounding DAG + persist, knowledge_mm writer, provenance XRef);
they are **inert in prod** until Step 5 wires the solve path to actually read/write them.

> **UPDATE 2026-07-21:** Slice 2 (capacity writer) has since SHIPPED (PR #61) — but is now
> being **reopened**: `CORE_CR_CAPACITY_MM_PERSIST_AND_SUBMIND.md` (APPROVED) rewrites it to a
> per-task/run graph, adds `capacity_mm`→Episode persistence (reopens DQ-8/ADR-0202), and
> **absorbs the submind follow-on CR** (`CORE_CR_SUBMIND_RESOLVER_MM.md`, now SUPERSEDED) as its
> Slice C. That CR is the trunk of the L5 lane — Slice 3 + Step 5 should build on its model.
**Consumers of record:** arc1 (D1.6 / D1.8), arc3 (C9 "L5 unused").
**Reframes:** `CORE_CR_PHASE1_RESOLVED_REFERENCE.md` — that CR is **Step 3.1 below, in isolation.**
**Foundation (BUILT + on main):** D8-B/3b per-task chain persist — `mm_persister.py`,
ADR-0202, PR #52 (merged). This work item builds on it.

**Build progress (updated 2026-07-22):**
- Step 1 / Slice 0 — **SHIPPED** (PR #59, `e234914`; gate 4266/0). `L5_SLICE0_INSTANCE_IRI_CONFIRMED.md`.
- Step 2 / Slice 1 — **SHIPPED** (PR #60, `f3cc950`; gate 4271/0). `L5_SLICE1_FORK_INDEPENDENCE_CONFIRMED.md`.
- Step 3 / Slice 2 — **SHIPPED** (PR #61, `a4e4e12`; gate 4277/0), then **reshaped + persisted** by
  `CORE_CR_CAPACITY_MM_PERSIST_AND_SUBMIND.md` Slices A/B/C (per-run graph + Episode persist + real
  MM into the submind arbiter; all merged, gate 4292/0). `L5_SLICE_A/B/C_CONFIRMED.md`.
- Step 4 / Slice 3 — **SHIPPED** (branch `feat/l5-slice-3-knowledge-writer`; gate 4300/0, 0 regressions).
  Knowledge writer + `mm_handle`=`MMResolver` + DQ-1 provenance XRef. `L5_SLICE_3_CONFIRMED.md`;
  memory [[l5-slice-3-knowledge-writer-shipped]].
- **Step 5 — NOT built. ← NEXT (the only remaining work).** See §Step 5 below.

---

## Problem (one line)
`arc solve task 7` resolves the task, then drops it: `phase_1.run` discards
`resolved_reference`, Phase 2 hardcodes its plan, and Phase 3-5 never runs a pipeline.
The task reaches nothing downstream.

## Where it falls (verified against main, 2026-07-19)
1. **Phase 1 → 2 drop.** `interpret()` returns `resolved_reference` (`phase_1.py:281`);
   `run()` builds a `Phase1Result` without it (`phase_1.py:300-307`). Field absent.
2. **Phase 2 discards its planner.** `plan_construction.build` dispatches
   `derive_initial_plan` fire-and-forget and hardcodes a single root milestone
   (`plan_construction.py:41-45`). `DS_PLAN` is imported but unused — a dead import.
   `is_leaf`/`decompose` are dispatched with empty milestones (`{}`).
3. **Phase 3-5 is a stub.** `execution.run` emits a notional StepExecutionRecord per leaf
   and marks it `completed`; it **never calls `execute_pipeline`**. The only real callers
   of `execute_pipeline` are Phase 1's resolve and the submind arbiter.

## Why the pasted Phase-1 CR is insufficient
`CORE_CR_PHASE1_RESOLVED_REFERENCE.md` threads `resolved_reference` into
`derive_initial_plan`'s payload. But (a) that cap's output is discarded (#2 above), and
(b) `derive_initial_plan` is the **planner**, not the executor — an ARC grid is an
*execution input*, not a plan-shaping signal. The load-bearing work — give the task a home
in L5 and make execution read it — is exactly what that CR omits, which is why it can
advertise "additive-inert." **Additive here = inert.** It is one sub-part of one step.

## Resolved design (already decided — do not re-litigate)
From `CORE_CR_L5_KNOWLEDGE_AND_CAPACITY_MM_WRITERS.md`:
- **DQ-3: L5 IS the blackboard.** Delete the Python dict; `capacity_mm` is source of truth.
- **DQ-1/DQ-2: `raw_task` is capacity-canonical** — the grounding-DAG root; one
  `DataStateInstance` per invocation-**output** (ADR-0201, ratified 2026-07-16).
- Slices 0 + 1 SHIPPED; Slices 2 + 3 NOT built.

---

## Ordered work (5 steps — dependencies are hard)

**Step 1 — Slice 0: instance vocabulary (additive). ✅ SHIPPED (PR #59).**
Instance-IRI builders + vocabulary in `mindsos_capacity/identifiers.py`. **Blocks Step 3.**

**Step 2 — Slice 1: deep_copy independence. ✅ SHIPPED (PR #60).**
Three-layer fork-id independence (core `Metagraph.regenerate_ids`/`remap_xref_targets`, L1
`ElementRegistry.remap_ids`, L5 `mm.deep_copy`). Prerequisite for provenance surviving a fork.

**Step 3 — Slice 2: the capacity writer (phase-shaped core). ✅ SHIPPED (PR #61), then reshaped +
persisted by the capacity-persist CR (Slices A/B/C, gate 4292/0). §Slice 2 below is the original
scope; the shipped model is per-run graph + Episode persist (see `L5_SLICE_A/B/C_CONFIRMED.md`).**
  3.1 *Phase-1 drop fix* — add `resolved_reference` to `Phase1Result`, populate in `run()`,
      thread orchestrator → `plan_construction`. **← this is the entire pasted CR.**
  3.2 *Delete the dict blackboard* in `execute_pipeline`; `capacity_mm` is source of truth;
      run-local type→instance-IRI index for routing (IRIs, not values).
  3.3 *Write the grounding DAG* — one `DataStateInstance` per invocation-output, each grounded
      to `raw_task` via produces/consumes edges.
  3.4 *Nullable `raw_task` provenance XRef* — `capacity_mm`→`knowledge_mm`,
      `ref_type=INSTANCE_OF`; target = pinned corpus-entry instance (arc1) / `None` (arc3).
  Flip the empty-room pin (`tests/phase_47/test_chain_artifact_emit.py:79-80`) — the
  non-additive breakpoint. Lock discipline: single `mm.lock`; never held across a `dispatch`.

**Step 4 — Slice 3: knowledge writer + `mm_handle`. ✅ SHIPPED (gate 4300/0). See
`L5_SLICE_3_CONFIRMED.md` + memory [[l5-slice-3-knowledge-writer-shipped]].**
`MMResolver` finishes into the `knowledge_mm` graph; wired as the read handle at both L4 dispatcher
sites (`intelligence_layer.py` + `mindsos_server/boot.py`), un-inerting `reads_mm`. The DQ-1
provenance XRef is `CapacityMMWriter.link_provenance` (arc1 pinned corpus-entry target / arc3 None).
**Validation target = arc1** (has the built solver) — its Step-5 e2e has a real pipeline to run.
Slice 3 is inert in prod until Step 5 supplies the caller (mint `raw_task` root, pass the phase-1
resolved reference as the knowledge target to `link_provenance`).

**Step 5 — OUT-OF-CR GAP: make Phase 3-5 real. ← NEXT (the only remaining work).**
Wire `execution.run` to actually call `execute_pipeline(mm=…, pipeline_run_ref=…)` on each leaf
pipeline, seeding L5 with the task. This is what makes Steps 1-4 non-inert: the capacity grounding
DAG + Slice-B persist and the knowledge writer + provenance XRef all fire only when a real solve run
grounds through `execute_pipeline` and consolidates. Also fixes the Phase-1 → 2 drop (3.1) and the
hardcoded plan (#2) so the resolved task actually reaches execution. **True end-to-end blocker for
`arc solve task 7`; NOT in the L5 CR's blast radius** (lives in `L4_FUTURE_WORK.md`). File as its
own core item. See §Step 5 detail immediately below.

### Step 5 detail (for the next chat)
- **Trigger for the inert writers:** `execute_pipeline` already takes `mm=`/`pipeline_run_ref=`
  (Slice A) and grounds the capacity DAG when present; the submind arbiter already threads a real
  `mm` (Slice C). `execution.run` must do the same on the solve path — thread the session `mm` +
  a fresh `pipelinerun:<task_id>` ref, and `consolidate_task` the run so Slice-B persist becomes
  non-inert (persist is `capacity_root_ref` index + per-DataState `encode`; note the per-DataState
  encoders are a **brain follow-up**, not core — see `capacity-mm-persist-reopen-dq8` PB-1).
- **Knowledge target for the XRef:** the phase-1 resolved reference (once 3.1 lands) is the L2
  corpus entry; instantiate it via the knowledge writer (`MMResolver.get_or_instantiate`) to get
  the pinned `knowledge_mm` instance, then pass its iri + `INSTANCE_GRAPH_ROLE` to
  `CapacityMMWriter.link_provenance` on the `raw_task` root (arc1). arc3 passes `None`.
- **3.1 (Phase-1 drop) + #2 (hardcoded plan)** are the upstream half — without them the resolved
  task never reaches Phase 3-5. `CORE_CR_PHASE1_RESOLVED_REFERENCE.md` is 3.1 in isolation (do not
  ship alone). Decide with the owner whether Step 5 subsumes 3.1 or lands it first.
- **Acceptance:** `arc solve task 7` → `raw_task` lands in `capacity_mm` → the leaf solve pipeline
  reads it → produces an answer → the Episode persists the capacity graph. Cannot pass today.

---

## Slice 2 (Step 3) — scope & open decisions (scoped 2026-07-19; NOT built)

**Today's mechanism (verified in `mindsos_intelligence/pipeline_execution.py`):**
`execute_pipeline` threads DataState **values** on a run-local `Dict[str, Any]` (DataState
IRI → value) — the "blackboard". Each step reads inputs by `step.input_datastates`,
dispatches, and merges `result.outputs` (DataState IRI → value) back. That value-dict living
outside the MM is the shadow state DQ-3 deletes.

**Target shape (DQ-3):** values become `DataStateInstance` node payloads in `capacity_mm`;
the run-local dict shrinks to a type→instance-IRI **index** (IRIs, not values). Read a step
input = index → instance IRI → node payload; write a step output = mint a `DataStateInstance`
(Slice 0 `datastate_instance_iri`), store the value as its payload, add produces/consumes
edges (the grounding DAG), update the index. Plus the `raw_task` root instance
(`datastate_instance_root_iri`) + the nullable provenance XRef (which now survives a fork —
Slice 1).

**CRUX GOTCHA — contract change, not a local edit:** `execute_pipeline` has **no MM handle**.
Signature = `(dispatcher, pipeline, initial_inputs, *, task_id, cancel_token)`. To write
`capacity_mm` it must be given it → ripples to callers: `phase_1._resolve_reference` (:166),
`submind_arbiter` (:209), the future `execution.run` (Step 5), + their tests. The L4
dispatcher carries `self._mm_handle`, but per ADR-0200 that's an **MMResolver (read)**, not a
`capacity_mm` write handle.

**OPEN DECISIONS — resolve with owner before code:**
- **D-A — how does the writer get `capacity_mm`?** (a) thread it explicitly through
  `execute_pipeline`'s signature [ripple to all callers + tests], or (b) extend the
  dispatcher / MMResolver to expose a write handle [hides a write path behind a read
  abstraction]. Leaning (a).
- **D-B — mandatory or optional MM?** If `execute_pipeline` runs without an MM (SubMind
  resolver? isolated tests?), there's nowhere to put values, and a fallback dict
  **re-introduces** the shadow state DQ-3 deletes. Either require an MM on every execution,
  or document an explicit exception. Decide first; start by checking whether
  `submind_arbiter`'s resolver actually has an MM.

**Also in Slice 2 (beyond node writes):** `capacity_mm` starts empty — lazily create the two
bipartite graphs (DataStateInstances / CapacityInstances, ADR-0201 §D-3), mint one
`CapacityInstance` per invocation (`capacity_instance_iri`), wire produces/consumes
`IntergraphEdge`s. Flip the empty-room pin. Lock: single `mm.lock`, never held across a
`dispatch` (ADR-0201 DQ-6).

---

## End-to-end acceptance
`arc solve task 7` → `raw_task` lands in `capacity_mm` (L5) → the leaf solve pipeline reads
it → produces an answer. This test cannot pass at any layer today; that is the honest
measure of remaining work.

## Build vs validate order
**Target = arc1 (decided 2026-07-19)** — it has the built solver, so the e2e test runs a
real solve. Full sequence: Steps 1 → 2 → 3.1-3.4 → 4 → 5 → e2e.
(arc3 would drop Steps 3.4/4 but has no runnable solve pipeline yet — not a valid target.)

## Blast radius (per L5 CR + this item)
`mindsos_intelligence/`: `phase_1.py`, `orchestrator.py`, `plan_construction.py` (3.1);
`pipeline_execution.py` (3.2-3.3); `execution.py` (**Step 5, added by this item**);
`mm.py` (Step 2, done); `mm_resolver.py`, `consolidation.py` (Step 4). Plus `mindsos_instances`
(Step 1, done). Plus Phase-47/48 test suites. **Not a small additive fix** — Steps 3.2-3.3
and 5 are phase-shaped.

## ADRs
ADR-0201 (instance vocabulary), ADR-0202 (per-task chain persist — built), ADR-0200
(`mm_handle = MMResolver`), ADR-0176/0180 (retention/consolidation), ADR-0172 (six-phase
lifecycle). Amend ADR-0172 / the L5 CR to record Step 5 (execution wiring).
