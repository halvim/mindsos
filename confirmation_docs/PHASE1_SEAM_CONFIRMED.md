# Phase-1 interpretation seam + `needs_input` — SHIPPED

**Date:** 2026-07-02
**Branch:** `feat/phase1-seam-and-needs-input`
**Kind:** non-phase feat (core_version stays `phase50`; no manifest version bump — SubMind/F9 precedent)
**ADRs:** 0195 (Accepted) + 0196 (Accepted); ADR-0150 §am-8 (+ backfilled §am-7)
**Gate:** Linux, live FalkorDB — **4111 passed / 11 skipped / 1 xpassed / 0 failed** (the two Local-role-set sentinels fixed after the first run's 2 failures).
**Merge commit:** `<fill on merge to main>`  **Tag:** `feat-phase1-seam-confirmed`

## What shipped

Two decoupled, independently-shippable core features (RULES §8 core-owned; first consumer = arc-solver / mOS-AS, interpretation-only, owns no core component). Built in four slices.

**S0.5 — `task-patterns` dual-scope (Local+Global).** ADR-0150 §am-8: added `ROLE_TASK_PATTERNS` to `_LOCAL_NAMED_ROLES` (joins `pending-promotions`/`learned-parameters` as dual-scope). Local named-role count 5→6; closed named-role-set count unchanged (14). Discipline `immutable_successor` both scopes; `reset_run_state` leaves it durable; the `episodic_memories ← task-patterns` bootstrap edge is now within-Local (kahn orders task-patterns first). Backfilled the missing subminds §am-7. Enables a consumer's `map` target to resolve Local→Global.

**S1 — ADR-0195 seam.** Factored a writer-free `interpret(dispatcher, task_input, *, profile) → InterpretationResult | NeedsInput` out of `phase_1.run` (now the artifact-emitting wrapper; v0 behavior byte-identical). `Phase1Profile` (4 slots `process`/`hint`/`derive_goal`/`map` + `resolve_target_datastate`) bound at `L4Dispatcher` construction — dispatch-time IRI selection, no metagraph scope-mix (hard constraint a). `resolve` is **composed via the shipped `find_pipeline`** (ADR-0156) from the hint's `reference_kind` type to `resolve_target_datastate`, run via the shipped `pipeline_execution` executor — not a slot (cardinality-1 is still a real `find_pipeline`, per the user). Map-resolution (Local→Global) + never-trip confidence checks gated on a real `map` slot, so all-v0 is untouched.

**S2 — ADR-0196 `needs_input`.** `NeedsInput` verdict (`mindsos_capacity/needs_input.py`; kept out of `mindsos_capacity.__all__` for export-slate parity = 139, the `InputContractError` precedent) → `call_capacity` short-circuit → `InvocationResult.needs_input` envelope (parallel to `write_outcome`) → `pipeline_execution` halt+bubble → `interpret` returns it → `TaskOutcome.pending_confirmation` + `run_lifecycle` Phase-1 short-circuit (non-terminal `status="pending_confirmation"`, no TaskRun, no consolidation). Caller-controlled trigger (hard constraint b). Mid-execution propagation + in-memory continuation deferred (L4-25).

**S3 — arc worked example.** Local integration test: cold-start `"solve task 8"` → `NeedsInput` → stateless re-submit `"solve task 05f2a901"` → `InterpretationResult{05f2a901}`; caller-controlled arc-Local marker; Local-only pattern.

## Design decisions / deviations

- **PB-3 reversed (user):** build `find_pipeline`-composed resolve now even at cardinality 1 (symmetric with `map`), not a bespoke direct-dispatch slot.
- **PB-4 reversed (user):** add Local `task-patterns` (S0.5) rather than soften the map check to well-formedness.
- **One deviation from literal ADR-0196:** the pending outcome uses a non-terminal `status="pending_confirmation"` marker in addition to the field (the three terminal statuses + `_OUTCOME_BY_STATUS` map are untouched). Recorded in ADR-0196 §Decision.3.

## Deferred (unchanged)

L4-25 (`execution.run` mid-execution propagation + in-memory continuation / MM retention), L4-26 (generic hints→pattern matcher / multi-pattern disambiguation), L4-27/28, L5-NEW-19 (awaiting-input MM disposition).

## Files

Production: `mindsos_knowledge/bootstrap.py`, `knowledge_layer.py`; `mindsos_capacity/needs_input.py` (new), `capacity.py`, `runtime.py`; `mindsos_intelligence/phase1_profile.py` (new), `phase_1.py`, `dispatch.py`, `orchestrator.py`, `pipeline_execution.py`, `__init__.py`.
Docs: ADR-0150/0195/0196.
Tests: `tests/phase1_seam/*` (new), 5 phase_14 + phase_43 + phase_44 + phase_25 sentinels.
