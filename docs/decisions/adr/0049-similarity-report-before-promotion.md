---
title: Admin must review similarity report before non-forced promotion
status: Superseded
date: 2026-04-22
layer: L2
aliases: [kl-ADR-012]
supersededby: [0115, 0144]
---

# ADR-0049: Admin must review similarity report before non-forced promotion

**Status:** Superseded by [ADR-0115](0115-release-ship-audit-gate.md) + [ADR-0144](0144-similarity-at-release-ship-audit-gate.md) (2026-05-22 — Phase 24 ship; the gate-on-`promote()` mechanism is replaced by the release-ship audit gate per Phase 16 §am1 lock + Phase 24 design log §4 ADR delta + Round 0 PB-Z6 pre-flip-uniform-treatment lock).

**Date:** 2026-04-22 (accepted), 2026-05-22 (superseded)

## Context

Two admins promoting near-identical drafts independently causes duplicates in Global. A purely-procedural fix doesn't survive a distracted afternoon.

## Decision

`kl.similarity_report(session, candidate_ids)` is a read-only analysis that returns a `SimilarityReport` with a deterministic `report_id`. `kl.promote(session, candidate_ids, reviewed_similarity_report_id, *, force=False)` refuses when `reviewed_similarity_report_id is None and force is False`. The server additionally checks the id is *fresh*.

## Consequences

**Good:**
- Non-forced promotion is gated on a conscious review action.
- Auditors can reconstruct whether a promotion was force-bypassed or reviewed.

**Bad:**
- The baseline similarity heuristic is intentionally crude; admins reviewing may miss semantic duplicates.

## Alternatives considered

None recorded; this was the consensus choice during the 2026-04-22 design session.

## Revisions

### amendment-1 (Phase 16 ship — 2026-05-20) — documentary; §Decision does not ship at Phase 16

**Status of this ADR remains Accepted** for historical record; the gate-on-`promote()` mechanism described in §Decision does NOT ship at Phase 16.

**What Phase 16 actually ships:** a read-only similarity surface at `mindsos_admin/similarity.py` — `compute_similarity(mg, candidates, *, role, ...) -> SimilarityReport` + `list_candidates(mg, *, role, ...)`. There is no `promote()` callee at Phase 16 for the gate to wrap: per ADR-0141 (Proposed), `KL.promote()` is scheduled for deletion in favour of `propose_for_promotion()` (relocated to `mindsos_admin/promotion.py` per ADR-0140 §amendment-1). Phase 16 ships only the heuristic + report-id surface that downstream consumers (Phase 24's release-ship audit gate per ADR-0144) can call.

**Status flip pending Phase 24:** when ADR-0141 flips Accepted at Phase 24 (the phase that ships `mindsos_admin/promotion.py` + `propose_for_promotion()` under the ADR-0118 transactional model), this ADR's Status flips to Superseded (gate semantics replaced by ADR-0144 §Placement at the release-ship audit gate, not at proposal time).

**Phase 16 design log:** `halvim_mindsos/confirmation_docs/PHASE_16_DESIGN_LOG.md` §1 Round 1 PB-1 (1c reframe) + Round 5 PB-U (PB-U3 documentary-amendment lock).
