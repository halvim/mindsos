---
title: needs_input verdict — non-terminal user-clarification (design-only)
status: Proposed
date: 2026-07-02
layer: L4
amends: []
aliases: [Feature-B, needs_input, clarification]
---

# ADR-0196: `needs_input` — non-terminal user-clarification

**Status:** Proposed (design-only; no code — pairs with [[ADR-0195]])

**Date:** 2026-07-02 (core-design chat; first consumer = arc-solver / mOS-AS)

## Context

The L4 lifecycle is **batch**: `run_lifecycle`
(`mindsos_intelligence/orchestrator.py`) has terminal outcomes only —
`TaskOutcome.status ∈ {succeeded, dont_know, aborted}`, each of which
consolidates (ADR-0176) and returns. There is **no** pause/await/suspend-resume
and **no** user-input path. `CATEGORY_INTERACTION` is a category name with zero
implementations. A capacity that cannot proceed without asking the user has no
way to say so.

Grounding (verified this chat):

- `dont_know` already exists as a **family-shaped capacity verdict** (ADR-0157
  `FamilyDontKnowShape`) that propagates up to a terminal outcome. `needs_input`
  is its natural sibling: "I can proceed *if you answer this*" (recoverable),
  versus `dont_know` = "I can't do this, here's the blame" (terminal).
- Durable suspend/resume is **blocked**: the L5 MM cannot flush to FalkorDB
  (node `value` is stored as a primitive; a structured MM/Episode dict does not
  serialize — PB-RT / L0-26). So parking a task durably is not available at v1.
- First consumer (arc-solver) surfaces clarification from the **standalone
  `interpret` call** ([[ADR-0195]] §Decision.3), not from `execution.run`.

## Decision

Add **`needs_input`** as a **capacity verdict**, sibling to `dont_know`, on the
existing verdict/propagation path. It carries a clarification payload; whoever
dispatched the capacity handles it.

1. **Caller-controlled trigger (hard constraint).** Core defines the verdict
   and *how* it is raised (a capacity body returns it) — but **never *when***.
   The decision to ask is policy inside the capacity body. (arc's `resolve`
   fires `needs_input` only while an arc-Local "ordering-established" marker is
   absent; the first confirm sets it; silent thereafter. That is arc-Local
   policy, not core.) Note the distinction core must preserve: "known" = the
   consumer's marker is set, **not** that enumeration/reference data exists.

2. **Payload contract.**
   `NeedsInput{question, missing: <DataState IRI>, choices: {label →
   task_input}}`. Each `choice` value is a **ready-to-re-submit `task_input`**,
   so a UI renders the question + choices and re-submits directly without
   reconstructing the request. Free-text answers use a `template` in place of
   enumerated `choices`.

3. **Two callers, one verdict.**
   - **Standalone `interpret` (arc):** returns the `NeedsInput` directly to the
     caller, which drives the two-turn flow itself.
   - **`run_lifecycle` (full lifecycle):** surfaces it as a **non-terminal
     `pending_confirmation` field on `TaskOutcome`**, orthogonal to `status`
     (the three terminal statuses + the `_OUTCOME_BY_STATUS` consolidation map
     are untouched). **No consolidation on that turn.** Detecting `needs_input`
     mid-execution (`execution.run` halt+bubble, shared with `dont_know`) is the
     general path, deferred (L4-25) — not required by the arc consumer.

4. **Wait model v1 = stateless re-submit.** The caller folds the chosen
   `task_input` into a fresh request; a new run re-does interpretation and
   proceeds. Core holds **no** session/resume state between turns.

5. **MM-ownership (designed, not built at v1).** A pending (awaiting-input)
   task's state belongs to that task's Mental Model. The future **in-memory
   continuation** — run the independent DAG branches, retain the MM, inject the
   answer, complete the dependent tail — retains + resumes that specific MM and
   adds an "awaiting-input / suspended" MM disposition (L5-NEW-19). **v1
   stateless re-submit discards the MM**, so v1 needs no L5 change. The
   continuation is deferred (L4-25 = L4-2 pause-and-resume via MM retention;
   in-memory feasible now, durable blocked on L0-26).

## Consequences

- A capacity anywhere can request user input via one additive verdict, reusing
  the `dont_know` propagation — no bespoke interaction-capacity wiring required.
- **Blocking vs non-blocking is emergent**, not a flag: it falls out of where
  the clarified value sits in the produces/consumes DAG (arc's is the root →
  whole flow gated; a scheduler's is a leaf → only the tail gated). v1 treats
  both as re-submit; the non-blocking "work while waiting" behavior needs the
  deferred continuation.
- **Reconcile with the L4-11 TaskOutcome schema** (`answer | dont_know |
  uncertain_answer`): `needs_input` is a **recoverable-by-user, non-terminal**
  disposition distinct from `uncertain_answer` (L4-27, folded here).
- **v1 audit gap:** the `needs_input` turn writes no Episode (no consolidation)
  → no durable ask/answer record. Revisit only if audit needs it (L4-28).
- **Build scope when implemented:** the verdict type + `pending_confirmation`
  field + the `interpret`-return path (arc). The `run_lifecycle` field-surface
  is small; the `execution.run` propagation defers. Independently shippable from
  [[ADR-0195]]. Version bump.

## Alternatives considered

- **4th terminal `status = "needs_confirmation"`** — rejected: every `status`
  switch + the consolidation map must special-case a non-terminal value; the
  separate `pending_confirmation` field keeps terminal invariants intact.
- **Dedicated `interaction.request_confirmation` capacity + a `ConfirmationRequest`
  chain artifact detected by L4 (M2)** — rejected as the primitive: a pipeline-
  composed interaction capacity only handles *planned* clarification steps, not
  the general "a capacity got stuck and needs the user" case at any phase. The
  verdict is strictly more general and costs less consumer wiring. (M2 remains a
  possible convenience wrapper later.)
- **Durable suspend/resume** — rejected at v1: blocked by the MM→Falkor node-
  value gap (L0-26); large.
- **Correlation-token resume** (`{token, answer}` interpreted by core) —
  rejected: adds core-held resume state for no v1 gain over stateless
  re-submit.

## Supersession / amendment trail
- Sibling to **ADR-0157** (family dont-know contracts — same verdict/propagation
  path). Extends the outcome model of **ADR-0171/ADR-0172** (lifecycle /
  `TaskOutcome`); preserves **ADR-0176** consolidation (skipped on the non-
  terminal turn). Amends none.
- **Pairs with [[ADR-0195]]** (the seam whose `interpret` returns this verdict).
- Future work: `L4_FUTURE_WORK.md` §6 / §6.2 + L4-25/L4-27/L4-28;
  `L5_FUTURE_WORK.md` L5-NEW-19 (awaiting-input MM disposition).
