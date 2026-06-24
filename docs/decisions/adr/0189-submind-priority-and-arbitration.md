---
title: SubMind priority model + L4 arbitration (severity/tier/score, resource-contention preempt-vs-reconcile, unsatisfiable-need policy)
status: Accepted
date: 2026-06-23
layer: L4
related: [0169, 0171, 0188, 0190]
---

# ADR-0189: SubMind priority model + L4 arbitration

**Status:** Accepted — partially shipped on `feat/subminds` (Linux gate green; tag `feat-subminds-slice1-confirmed`). Slice 1 implements §1 (severity/tier/`attention_score`) and §4 (single scheduler thread + `SubMindRegistry`, MM read-only); §2 (preempt vs reconcile / resource model) and §3 (unsatisfiable-need policy) land in Slice 2. See `confirmation_docs/SUBMIND_DESIGN_LOG.md` §19.

**Date:** 2026-06-23

## Context

ADR-0188 introduces the SubMind and its two outputs but defers *how* L4 prioritizes Signals, *how* it decides whether a need preempts or coexists with running work, and *what* happens to a need that cannot currently be resolved. These are the arbitration mechanics — the "single mind" that unifies many dumb reflexes.

## Decision

### 1. Severity / tier / attention_score (three quantities, distinct owners)

- **severity** — *how bad now*, **physical**, normalized `0–1` over `[threshold → failure]`. **SubMind-owned.** Drives the tier band and the SubMind's over-time ordering.
- **tier** — system-wide urgency bucket (the executor's common currency). Computed by a **fixed, monotonic step-function of severity, set at endowment** (e.g. battery `>50%→BACKGROUND, 20–50%→FOREGROUND, <20%→CRITICAL`). Immutable *mapping*, dynamic *result*. A SubMind **never names its own tier** — doing so would leak arbitration into the reflex.
- **attention_score** = `importance_weight × severity`. **L4-owned.** Drives within-tier ordering across different SubMinds. Maps onto the existing `attention_score` heap key. The weight is **static at v1**; if ever learnable, the learner is a **core L4** mechanism (not WSD).

The queue orders by `(tier, attention_score)` — the shipped `PriorityTierExecutor` heap (ADR-0169). **Tier escalation is deterministic** (severity rises → band crossed → tier escalates; "adrenaline"), with hysteresis on band edges. **Tier is decoupled from preemption** — it governs ordering/visibility only; escalation to CRITICAL must not by itself cancel running work.

### 2. Preempt vs reconcile — derived from resource contention

The verdict is **not declared**; it is computed. At endowment each SubMind's **resolver declares the exclusive resources it needs**; each running task declares the resources it holds:

- **no overlap → reconcile** — run the resolver concurrently, woven into the running plan as a sub-goal/constraint;
- **overlap → contention** — resolve by tier/severity: **preempt** if the need outranks the task, else **defer** (§3).

A need is a *rival* only when resources overlap; otherwise it is a *constraint*. "resource" = **exclusive/contended** resources (actuators, single-holder locks), not shared schedulable compute. This requires a one-time **resource model** (a lock/acquisition model), shared with the Reflex seizure path (ADR-0188).

### 3. Unsatisfiable-need policy — split retry from awareness

- **Tier never decays** — criticality is a property of the need, not of solvability. A dying battery with no charger stays CRITICAL.
- **The cap is on retry activity only** — backoff + **event-driven** resume when the contended resource frees. An unsatisfiable need does not starve, because its resolver is **parked** (not running); lower-tier work proceeds.
- **Never auto-give-up** — the need persists at its true tier, visible, until resolved / the vital recovers / a human dismisses it.

### 4. Concurrency + lifecycle

- A **single scheduler thread** owns *when* (timer-heap of next-fire times; cheap checks inline, heavy ones offloaded to the Phase-46 worker pool). Thread-per-SubMind is rejected (does not scale).
- SubMinds are **read-only on the MM**, pushing to the signal-triage queue (short read-locks only).
- Lifecycle owner = the per-session L4 **`SubMindRegistry`** (start/stop/toggle); L4 owns activation state (active / floored-slow-cadence / off).

## Consequences

- L4 gains a small resource model + a scheduler thread + a registry; arbitration becomes mechanical (ordering by `(tier, score)`; preempt/reconcile by contention) rather than ad-hoc.
- Keeps the reflex/deliberation split intact: reflexes report physical severity + declare resources; L4 owns *mattering* (weight), *ordering* (tier/score), and *the preempt/reconcile decision*.
- **Cost:** every task must declare the exclusive resources it holds for the contention check to work; the standing-pressure mechanism adds per-unmet-need state (retry-backoff + awareness).

**Open:** the importance weights, backoff curve, standing-pressure cap, and floor are tuning, deferred to implementation.

## Amendment trail

- Composes with ADR-0188 (construct + outputs) and ADR-0190 (endowment + role-graph).
- Reuses ADR-0169 (`TierEnum` + signal-triage) and the ADR-0171 worker-per-task executor without amendment.
