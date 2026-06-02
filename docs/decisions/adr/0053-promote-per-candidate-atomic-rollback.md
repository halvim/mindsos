---
title: promote does per-candidate atomic rollback internally
status: Superseded
date: 2026-04-22
layer: L2
aliases: [kl-ADR-016]
supersededby: [0118, 0129]
---

# ADR-0053: promote does per-candidate atomic rollback internally

**Status:** Superseded by [ADR-0118](0118-per-user-transactional-promotion.md) + [ADR-0129](0129-metagraph-snapshot-narrowed-to-release-ship.md) §am2 (2026-05-22 — Phase 24 ship; per-candidate atomic rollback replaced by per-role atomic ship + admin rerun on partial-ship per Phase 24 design log PB-1(b) + PB-Z1(b) MERGE-on-id idempotent rerun; Phase 16 §am1 lock + Phase 24 design log §4 ADR delta + Round 0 PB-Z6 pre-flip-uniform-treatment lock).

**Date:** 2026-04-22 (accepted), 2026-05-22 (superseded)

## Context

When `promote` is given N candidates, any of them can fail validation mid-flight. The server already snapshots every touched metagraph, but a clean raise with no mid-flight mutation is easier to reason about.

## Decision

`promote` builds an `undo: List[callable]` stack as it mutates. Each candidate contributes two undo entries: one pops the new Global node, one restores the Local draft's pre-promote `ref:global_<role>` / `ref_type`. On any exception, the undo stack runs in reverse before `raise`.

## Consequences

**Good:**
- Callers observe all-or-nothing: either the `PromotionResult` reflects every candidate, or the state is unchanged.
- The server's snapshot is still there for post-`promote` failures.

**Bad:**
- Two layers of rollback need to stay in agreement.

## Alternatives considered

None recorded; this was the consensus choice during the 2026-04-22 design session.

## Revisions

### amendment-1 (Phase 16 ship — 2026-05-20) — documentary; §Decision does not ship at Phase 16

**Status of this ADR remains Accepted** for historical record; the per-candidate undo-stack mechanism described in §Decision does NOT ship at Phase 16.

**What Phase 16 actually ships:** a read-only similarity surface at `mindsos_admin/similarity.py`. There is no `promote()` to wrap an undo stack around at Phase 16: per ADR-0141 (Proposed), `KL.promote()` is scheduled for deletion. Per ADR-0118 (Proposed) the replacement `propose_for_promotion()` uses a different atomicity model entirely — SQLite-transactional propose into `pending_global` buffer + release-boundary atomicity via `MetagraphSnapshot` (ADR-0129 narrowed) at release-ship — not in-memory undo stacks.

**Status flip pending Phase 24:** when ADR-0118 + ADR-0141 flip Accepted at Phase 24, this ADR's Status flips to Superseded (the per-candidate undo-stack pattern is replaced by per-user SQLite transactional propose + per-release `MetagraphSnapshot` rollback at release-ship).

**Phase 16 design log:** `halvim_mindsos/confirmation_docs/PHASE_16_DESIGN_LOG.md` §1 Round 1 PB-1 (1c reframe) + Round 5 PB-U (PB-U3 documentary-amendment lock).
