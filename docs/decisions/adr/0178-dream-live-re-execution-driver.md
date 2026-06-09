---
title: Dream live re-execution driver — timer hookup, episode task_input re-run, ALS provenance
status: Accepted
date: 2026-06-09
accepted_date: 2026-06-09
layer: L4
related: [0162, 0171, 0173, 0044, 0177]
---

# ADR-0178: Dream live re-execution driver — timer hookup + episode `task_input` re-run + ALS provenance

**Status:** Accepted

**Date:** 2026-06-09

**Related:** ADR-0162 (L3 dream family — the capacities this drives), ADR-0171 (orchestrator — the lifecycle dream re-uses), ADR-0173 (replan-check — the ReplanInjection seam), ADR-0044 (`episodic_memories` — the dream corpus), ADR-0177 (D'1 — full reconstruction, deferred, would consume `resolve_refs`).

## Context

Chat B D-B5/B6 fixed dream-as-live: load an episode → materialize a fresh MM by deep-copy → re-execute through the phase-loop; ALS signals fire per normal mechanics; no separate dream-learning track. Phase 45 shipped the 3 L3 `dream.*` capacities (each emits a `DreamDirective(execution_policy, entry_point, replan_injection?)`). Phase 46 shipped the `DreamCycleTimer` with an **injected, default-absent callback** and `fork_dream_mm()`. Phase 47 deferred the driver wholesale (no episode corpus existed). Phase 48 wires it — episodes now exist (ADR-0176).

**Grounding (Phase 48 R0).** `IntelligenceLayer.fork_dream_mm()` is `self.mm.deep_copy()` — it copies the **live** MM, not a loaded episode. `run_lifecycle(task_input, *, tier, …)` takes its MM via the orchestrator **constructor** (`self._mm`) and always enters at `phase_1.run(...)`. So "load episode → fork → re-execute" has a missing middle (episode→MM reconstruction) the shipped primitive does not provide.

## Decision

### 1. v1 dream = re-run from the episode's `task_input` (PB-9, Opt B)

The dream-cycle callback: tick → invoke the 3 `dream.*` capacities (each selects a candidate TaskRun from the corpus and emits a `DreamDirective`; `dream.retry` only on a failed episode) → for each directive, **read the Episode, extract `task_input_ref`, build a fresh MM, construct an orchestrator over it, and `run_lifecycle(task_input, tier=TierEnum.DREAM)`** under the owning user's session. Signals emitted during re-execution carry `dream_source_episode_iri`; ALS tags Local-only (Chat B §5.2 privacy). `dream.retry`'s `ReplanInjectionDirective` is injected at the replan-check seam (force-replan at the injected level — ADR-0173).

### 2. Deferred to WSD (with the ALS mechanism)

Full **episode→MM reconstruction** (rebuild the frozen three-sub-MM from `mm_root_ref`, resolving version-pinned refs via ADR-0177 `resolve_refs`) and the `execution_policy` **behavioral** differentiation (`replay_recorded` regression replay needs a dispatcher "return recorded outputs" mode) defer together to WSD installation. v1 **records** the policy on the directive and fires signals, but runs all three pipelines as **live re-execution**. No v1 consumer exists for recorded-output replay.

### 3. `fork_dream_mm` unchanged

Kept as the live-MM deep-copy primitive (its v1 use is reconstruction-side, deferred). v1 dream does not call it (it builds a fresh MM from `task_input`).

## Rationale

- **Exercises the real path** — timer → `dream.*` capacities → orchestrator → ALS firing + provenance — on real episodes, reusing the Phase-47 lifecycle wholesale.
- **Lean + consistent.** Re-running from `task_input` avoids a reconstruction path with no other v1 consumer; pairs the reconstruction with the regression-replay mechanism that needs it (WSD).
- **Privacy + provenance** preserved per Chat B §5.2.

## Consequences

- v1 dream cannot do `replay_recorded` regression equivalence (needs recorded-output replay) — `dream.maintenance` runs live like the others, policy recorded only.
- ADR-0177 `resolve_refs` (S7) has no live v1 consumer → unit-test-only.
- Promotion-candidate surfacing (Chat B §5.3) is **not** v1 — deferred to WSD with the capacity-gaps admin queue.

## Alternatives considered

1. **Full episode→MM reconstruction at v1 (PB-9 Opt A).** Rejected — a whole reconstruction path mirroring consolidation, with no v1 consumer besides dream; belongs with the regression-replay mechanism (WSD).
2. **Defer the driver wholesale to WSD.** Rejected — the timer→capacity→orchestrator→ALS wiring is genuine L4 substrate, testable now that episodes exist; only the reconstruction/replay half lacks a v1 consumer.

## §Implementation (Phase 48; pending ship)

`mindsos_intelligence/dream_cycle.py` (NEW — timer callback + capacity dispatch + episode `task_input` re-run + ReplanInjection); `intelligence_layer.py` (wire the `DreamCycleTimer` callback). Tests: `tests/phase_48/test_dream_pipeline_hookup.py` (timer invokes the 3 capacities; `dream_source_episode_iri` provenance; `dream.retry` replan injection).
