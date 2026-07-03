---
title: SubMind (Mindlet) construct + Signal/Reflex two-output model
status: Accepted
date: 2026-06-23
layer: L4
aliases: [submind, mindlet]
amends: [ADR-0155]
related: [0150, 0159, 0162, 0169, 0180]
---

# ADR-0188: SubMind (Mindlet) construct + Signal/Reflex two-output model

**Status:** Accepted — Slice 1 shipped on `feat/subminds` (Linux gate green: 4069 passed / 11 skipped / 1 xpassed / 0 failed; tag `feat-subminds-slice1-confirmed`). Slices 2–4 (resource model + arbitration; Reflex path; Local scope + teaching + de-endowment) pending. See `confirmation_docs/SUBMIND_DESIGN_LOG.md` §19.

**Date:** 2026-06-23

## Context

MindsOS was inspired by Minsky's *Society of Mind* — a mind as the coordination of many dumb sub-systems. The three-tier framing (society of small minds → single mind → society of full minds) delivered the latter two but never formalized the first. A grounding pass found the autonomy dimension of the stack is hollow scaffolding: monitors are declarative-only (ADR-0155 retired their loop), signal-sources are empty, the ALS registry is empty, and the only self-firing loop is the dream-cycle timer.

We need a first-class construct for an autonomous, individually-dumb self-state regulator — the biological intuition being hydration/thirst, balance, battery: sub-processes that monitor a vital and escalate to the orchestrator when needed.

## Decision

Introduce the **SubMind** (nickname **Mindlet**): an autonomous, no-reasoning **reflex** over one self-state vital.

1. **Reflex / deliberation split.** Autonomy ≠ reasoning. A SubMind owns a minimal control loop (sense → compare to threshold → emit) and never deliberates. The single L4 **Mind** does all deliberation and arbitrates the outputs of all SubMinds. A SubMind does **not** get its own L4.

2. **Autonomy.** A SubMind owns its **sampling loop** and self-schedules an adaptive, proximity-driven **cadence** (a fixed control law inside the SubMind: rarer when safe, faster near threshold; bounded min/max + anti-thrash hysteresis). Two communication channels: **(a) L4-initiated** = an on-demand one-shot read only (not cadence); **(b) SubMind-initiated** = a push.

3. **Two output modes** of the sense loop:
   - **Signal** — normal output: enqueued with `(tier, severity)`, **deliberated** by L4 (ADR-0189).
   - **Reflex** — emergency output: a **declared non-reconcilable predicate** (not mere magnitude) fires a **pre-wired single fast capacity** that **bypasses the queue and L4 deliberation**, notifying L4 after. A Reflex has **no tier** — it is an output mode, not a priority level. Forcible resource seizure is **supersede, not negotiate**: a low-level **arbiter override** for command-stream/actuator resources, or a **drain** for compute/attention; never abstract locks. A Reflex stays **dumb** — its action is pure reallocation; any subsequent solving is a downstream CRITICAL deliberated task. The same SubMind may emit Signals normally and a Reflex at its declared extreme.

4. **Storm suppression.** Edge-triggered emission + reset band: ARMED → (cross) emit once → FIRED → silent until recovery past a reset margin → re-ARM; re-emit while FIRED only on worsening-past-a-step.

5. **Recursion.** The same `{sense → severity → Signal | Reflex}` machinery applies SubMind→Mind and Mind→Mind-of-Minds; the resource model + arbiter must exist at every orchestration level. (The society-of-full-minds tier itself is out of scope here.)

## Consequences

- **Reverses ADR-0155.** Resident, self-firing monitor loops return — but as an **L4-owned scheduler** (a single scheduler thread, timer-heap of next-fire times; see ADR-0189), **not** the deleted L3 `start_resident`/`stop_resident` lifecycle. The Phase-46 `MonitorSubscriptionRegistry` is repurposed as the write-hook/arbiter feed for Reflex instant-detection.
- SubMinds are **read-only** on the MM and push to the signal-triage queue; no MM writes (short read-locks only).
- The empty Phase-47 signal-source skeletons are superseded by SubMind Signal emission; `TierEnum` + `attention_score` (Phase 46/48) are reused unchanged.
- **Cost:** N autonomous loops need a lifecycle owner + concurrency discipline (ADR-0189); forcible Reflex seizure conflicts with the Phase-46 cooperative-cancellation model and requires an arbiter layer for Reflex-eligible resources.

**Open:** tuning of cadence bounds/hysteresis and the Reflex floor (deferred to implementation).

## Amendment trail

- **Amends ADR-0155** — the Monitor-lifecycle retirement is partially reversed: resident self-firing returns at L4 (scheduler-owned), not L3. ADR-0155's L3-purity rationale is preserved (no resident loop in `mindsos_capacity`); the loop lives in `mindsos_intelligence`.
- **Slice 2 resource model (shared with the Reflex path).** The forcible resource seizure of Decision 3 reuses the same `ResourceLedger` (`mindsos_intelligence/resources.py`) that Slice 2 built for Signal preempt/reconcile (ADR-0189 §2). Slice 2 uses the hold's *cooperative* `cancel` hook; the Slice-3 Reflex path adds a forcible *seize* hook (arbiter override / drain) on the same `ResourceHold` record — designed to host it without a ledger change.
- Composes with ADR-0189 (priority + arbitration) and ADR-0190 (endowment + `subminds` role-graph).
