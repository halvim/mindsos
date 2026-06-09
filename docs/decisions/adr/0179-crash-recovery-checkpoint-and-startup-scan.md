---
title: Crash recovery — D-B50 checkpoint trigger set + tombstone marker + startup scan
status: Accepted
date: 2026-06-09
accepted_date: 2026-06-09
layer: L4
related: [0171, 0176, 0121, 0044]
---

# ADR-0179: Crash recovery — D-B50 checkpoint trigger set + tombstone marker + startup scan

**Status:** Accepted

**Date:** 2026-06-09

**Related:** ADR-0171 (orchestrator — worker-per-task; the lifecycle the triggers hook), ADR-0176 (consolidation — the path a recovered task consolidates through), ADR-0121 (FalkorDB persistence — the marker store), ADR-0044 (`episodic_memories` — where the crash Episode lands).

## Context

Chat B D-B50 fixed the crash-recovery contract: a checkpoint trigger set (LifecyclePhase transitions + per-Milestone completion + per-replan event) and, on L4 startup, a scan for unconsolidated MMs that consolidates them with `crash_marker` set; the **physical mechanism was routed to L4-implementation**.

Phase 47 shipped **worker-per-task** (ADR-0171): the MM is **in-process working memory**, persisted to Falkor only at consolidation (ADR-0176). A crash mid-task therefore loses the MM entirely — so "scan for unconsolidated MMs at startup" presupposes checkpoints have persisted *something* to scan. The mechanism choice (how much to persist per trigger) is the load-bearing v1 decision.

## Decision

### 1. v1 mechanism = tombstone marker (PB-5, Opt B)

At each D-B50 trigger, write a small durable **checkpoint marker** (not the MM) to a Falkor staging node, carrying: `task_iri`, `task_input_ref`, last `LifecyclePhase`, last `Milestone`, `task_pattern_iri` (once Phase 1 maps it), timestamp, `consolidated=false`. Clean consolidation (ADR-0176) clears the marker. The marker is **metadata only** — the in-process MM is *not* flushed at v1.

### 2. Startup scan → crash tombstone Episode

On `IntelligenceLayer.start()`, scan the staging area for `consolidated=false` markers. For each, **first check whether an Episode for that task already exists** (idempotency — a crash *during* consolidation may have written the Episode before clearing the marker; ADR-0176 §4). If none, emit a crash tombstone Episode: `outcome_classification="failed"`, `crash_marker=CrashInfo(last_phase, last_milestone, detected_at, recovered=False)`, `mm_root_ref=None`, `task_input_ref` + `task_pattern_iri` from the marker. `crash_marker` is an Episode content field (schema already provides it); the partition validator checks classification, not presence, so a `None` `mm_root_ref` is writable.

### 3. Content recovery deferred to v1.5

Recovering the *partial MM content* (flush the live MM to Falkor staging per trigger; reconstruct on restart) is deferred. Rationale: a crashed task's MM is partial/mid-Milestone — not meaningfully dream-replayable or inspectable — so recovered content has low v1 value against high cost (per-trigger MM serialization), and a heavy checkpoint engine contradicts the phase's instrument-now posture (PB-QQ → retention policy v1.5). The upgrade is a clean swap (marker → MM staging flush) if observed crash rates justify it.

## Rationale

- **Delivers the three real v1 values:** clean startup (no orphaned in-flight tasks), a crash record (audit/observability), and task preservation (`task_input_ref`) for re-submission.
- **Cheap + testable:** the marker is tiny; the pass-criterion ("simulated crash → consolidated Episode with `crash_marker`") is met by leaving a `consolidated=false` marker and running the startup scan — no real crash needed.
- **Marker store = Falkor** (consistent with the Phase-44 Falkor-only persister; avoids re-opening the deferred SQLite persister).

## Consequences

- L4 startup now scans for crash residue (configurable per-deployment bootstrap overhead — small).
- A crash Episode has no recovered MM content at v1 (`mm_root_ref=None`); it is a metadata tombstone.
- Consolidation must be idempotent on `episode_id` (ADR-0176 §4) so the startup scan never double-writes.

## Alternatives considered

1. **Flush the live MM to Falkor staging per trigger (Opt A).** Rejected for v1 — per-trigger MM serialization cost + low value of partial-MM recovery + LOC budget; deferred to v1.5.
2. **Defer the mechanism entirely (hooks + no-op).** Rejected — cannot satisfy the "simulated crash → consolidated Episode" pass-criterion.

## §Implementation (Phase 48; pending ship)

`mindsos_intelligence/crash_recovery.py` (NEW — trigger-marker writer + startup scan); trigger calls wired into the orchestrator lifecycle (commit-group 3); `IntelligenceLayer.start()` invokes the scan. Tests: `tests/phase_48/test_crash_recovery.py` (marker fires at triggers; startup scan consolidates with `crash_marker`; idempotency on existing Episode).
