---
title: Baseline similarity heuristic is deliberately crude
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-018]
---

# ADR-0055: Baseline similarity heuristic is deliberately crude

**Status:** Accepted

**Date:** 2026-04-22

## Context

The similarity algorithm could be as sophisticated as the reviewer wants — semantic embeddings, graph-structure distance, property-level diff. Each level of sophistication is: more code, more failure modes, more variance in `report_id`. The algorithm's *job* is to prompt the admin to look at a match; it is not the decision mechanism.

## Decision

Ship a deterministic baseline: for each candidate, compare against Global same-type nodes — exact value match = 1.0, prefix match = 0.7, otherwise 0.0. Threshold 0.5. Results are sorted for determinism.

## Consequences

**Good:**
- Same inputs → same `SimilarityReport` → same `report_id`.
- The algorithm can be strengthened later without changing the signature.

**Bad:**
- Semantic near-duplicates (synonyms, paraphrases) are invisible to the baseline.

## Alternatives considered

None recorded; this was the consensus choice during the 2026-04-22 design session.

## Revisions

### amendment-1 (Phase 16 ship — 2026-05-20) — heuristic superseded by ADR-0144 §Heuristic; this ADR not implemented at Phase 16

**Status of this ADR remains Accepted** for historical record; the crude `exact 1.0 + prefix 0.7 + threshold 0.5` heuristic described in §Decision is **superseded** by ADR-0144 §Heuristic (Levenshtein on canonical names + structural Jaccard on `frame_elements ∪ synonyms ∪ parents` + reference Jaccard on outbound `ref:<role>` properties + XRef targets; weights 0.4 / 0.4 / 0.2; threshold 0.85 blocking, 0.5 review).

**Trigger:** ADR-0144 (Proposed) explicitly calls this ADR's heuristic "Pareto-dominated" by both the original spec (Levenshtein + structural overlap + reference Jaccard) and a simpler exact-only baseline. Phase 16 ships ADR-0144's heuristic at `mindsos_admin/similarity.py` rather than this ADR's crude baseline.

**What Phase 16 actually ships:** `compute_similarity(mg, candidates, *, role, target_mg=None, threshold_blocking=0.85, threshold_review=0.5)`. The 0.5 threshold from this ADR is preserved only as the `threshold_review` default; `threshold_blocking=0.85` per ADR-0144.

**Status not flipped to Superseded yet** because ADR-0144 remains Proposed at Phase 16 (only §Heuristic is in active code; §Placement waits for Phase 24's release-ship audit gate). When ADR-0144 flips Accepted in full at Phase 24, this ADR's Status flips to Superseded.

**Phase 16 design log:** `halvim_mindsos/confirmation_docs/PHASE_16_DESIGN_LOG.md` §1 Round 1 PB-2 (PB-2b lock) + Round 2 PB-A (PB-A2 partial-flip mechanism).
