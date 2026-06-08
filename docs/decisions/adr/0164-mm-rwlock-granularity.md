---
title: MM RWLock — per-active-MM, root granularity, writer-preferred
status: Accepted
date: 2026-06-08
accepted_date: 2026-06-08
layer: L4
related: [0165, 0163, 0166]
---

# ADR-0164: MM RWLock — per-active-MM, root granularity, writer-preferred

**Status:** Accepted

**Date:** 2026-06-08

**Related:** ADR-0165 (three-sub-MM composition — the structure this lock guards), ADR-0163 (Executor — `attention_score` write-through will acquire the writer lock at Phase 48), ADR-0166 (MM resolution+instantiation — instantiation writes take the writer lock).

## Context

Chat A D32.3 = C settled MM concurrency control as a **reader-writer lock per active MM**. The access pattern justifies it: the orchestrator thread runs replan-check + sufficient-predicate between every step (read-heavy), while L3 capacity writes (DataState appends, instantiation, decision-point pins) are bursty but less frequent.

Chat B D-B10 then composed the MM as a **metagraph of three sub-metagraphs** (knowledge-MM / capacity-MM / intelligence-MM). That raises a granularity question D32.3 did not face directly: one lock at the MM root, or one per sub-MM?

## Decision

### 1. One writer-preferred RWLock per active MM, at root granularity (PB-3)

Each active MM (one per session) holds a **single** reader-writer lock at the **root**, guarding all three sub-MMs together. Concurrent reads proceed in parallel; a write excludes all readers and writers across all three sub-MMs.

### 2. Writer-preferred fairness

When a writer is waiting longer than a threshold (default measured in ms, per-deployment configurable), new readers queue behind it to prevent writer starvation (D32.3 implementation note). Writer-preferred, not writer-absolute — an in-flight read completes before the writer acquires.

### 3. Per-sub-MM locking is explicitly NOT v1

D32.3 rejected per-instance locks (alternative B) for deadlock risk under multi-instance writes. Per-sub-MM locking re-opens exactly that hazard (a write touching capacity-MM and intelligence-MM atomically would need both locks in a fixed order). Root granularity is correct-by-construction. Per-sub-MM is a v2 throughput optimization, gated on benchmarks (the PB-AAA posture: optimize only when measured need appears, post-Phase-49).

## Rationale

- **Matches D32.3 = C literally** ("per active MM") and the bursty-write/heavy-read pattern.
- **No cross-sub-MM deadlock.** A single lock cannot deadlock against itself; atomic multi-sub-MM writes (e.g. ADR-0163's future `attention_score` write-through, which touches the TaskRun composite in intelligence-MM) are trivially safe.
- **Throughput cost is acceptable v1.** A capacity-MM write briefly blocks intelligence-MM reads. At v1 task concurrency this is negligible; the v2 split is reserved, not foreclosed.

## Consequences

- The MM container (ADR-0165) owns the lock; all readers/writers go through it.
- ADR-0163's deferred `attention_score` MM write-through (Phase 48) acquires this writer lock atomically.
- A v2 per-sub-MM split would require a documented lock-ordering protocol; the escape hatch is noted but unimplemented.

## Alternatives considered

1. **Whole-MM mutex (D32.3-A).** Rejected — serializes all reads; throughput cap on the read-heavy orchestrator loop.
2. **Per-sub-MM lock.** Rejected — re-opens the deadlock D32.3 rejected; premature optimization.
3. **Copy-on-write (D32.3-D).** Rejected — readers see stale state; flush-scheduling complexity.

## §v2-reservations

- Per-sub-MM RWLock with a fixed lock-ordering protocol, if benchmarks show root-lock contention post-Phase-49.

## §Implementation (Phase 46 — convergence; pending ship)

PR-A: writer-preferred RWLock owned by the MM container (`mindsos_intelligence/`, with ADR-0165). Test `tests/phase_46/test_mm_rwlock.py` (reader/writer exclusion + writer-preferred fairness under contention). The `attention_score` write-through that exercises it end-to-end lands Phase 48.
