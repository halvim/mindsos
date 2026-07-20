# CORE WORK ITEM — load the resolved task into L5 (make it reach the solve)

**Type:** sequencing work item — orders existing CRs; not a new design.
**Status:** IN PROGRESS. Slices 0 + 1 SHIPPED to main; Slices 2/3 + Step 5 NOT built.
**Consumers of record:** arc1 (D1.6 / D1.8), arc3 (C9 "L5 unused").
**Reframes:** `CORE_CR_PHASE1_RESOLVED_REFERENCE.md` — that CR is **Step 3.1 below, in isolation.**
**Foundation (BUILT + on main):** D8-B/3b per-task chain persist — `mm_persister.py`,
ADR-0202, PR #52 (merged). This work item builds on it.

**Build progress (2026-07-19):**
- Step 1 / Slice 0 — **SHIPPED** (PR #59, squash `e234914`; gate 4266/0). Confirm:
  `L5_SLICE0_INSTANCE_IRI_CONFIRMED.md`.
- Step 2 / Slice 1 — **SHIPPED** (PR #60, squash `f3cc950`; gate 4271/0, 0 regressions).
  Confirm: `L5_SLICE1_FORK_INDEPENDENCE_CONFIRMED.md`.
- Steps 3 (Slice 2) / 4 (Slice 3) / 5 — **NOT built.** Next = Slice 2 (see §Slice 2 below).

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

**Step 3 — Slice 2: the capacity writer (phase-shaped core). ← NEXT. See §Slice 2 below.**
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

**Step 4 — Slice 3: knowledge writer + `mm_handle` (REQUIRED for arc1).**
Finish `MMResolver` into the graph; wire as the handle (un-inert `reads_mm`). arc1's
provenance XRef (3.4) must resolve to a real target (the pinned corpus-entry instance in
`knowledge_mm`), so this is on the critical path. **Validation target = arc1** (decided
2026-07-19): it has the built solver, so Step 5 has a real pipeline to run end-to-end. arc3
would skip Steps 3.4/4 but has no runnable solve to validate against — deferred.

**Step 5 — OUT-OF-CR GAP: make Phase 3-5 real.**
Wire `execution.run` to actually call `execute_pipeline` on each leaf pipeline, seeding the
blackboard (now L5) with the task. Without this, Steps 1-3 give the task a home in L5 that
the execution phase never reads. **This is the true end-to-end blocker for `arc solve
task 7`, and it is NOT in the L5 CR's blast radius** (it lives in `L4_FUTURE_WORK.md`).
File as its own core item; amend the L5 CR slice plan to reference it.

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
