---
title: PromotionResult.promoted preserves input order
status: Superseded
date: 2026-04-22
layer: L2
aliases: [kl-ADR-019]
supersededby: [0114, 0118]
---

# ADR-0056: PromotionResult.promoted preserves input order

**Status:** Superseded by [ADR-0114](0114-release-manifest-and-version-db-schema.md) + [ADR-0118](0118-per-user-transactional-promotion.md) (2026-05-22 — Phase 24 ship; promotion-result order semantic replaced by `manifest_json.included_mutation_ids` contract per Phase 16 §am1 lock + Phase 24 design log §4 ADR delta + Round 0 PB-Z6 pre-flip-uniform-treatment lock; mutation_ids in manifest_json are append-order from `pending_mutations.mutation_id` AUTOINCREMENT, NOT input-order at propose-time).

**Date:** 2026-04-22 (accepted), 2026-05-22 (superseded)

## Context

Two behaviours to choose between: (a) `promoted` order matches input order, easy for callers to correlate; (b) `promoted` order matches `similarity_report` order (sorted), easy to correlate with the report findings.

## Decision

`promote` dedupes candidates (keeping first occurrence) but preserves input order. Results in `PromotionResult.promoted` are in input order, deduped. `similarity_report` sorts candidates internally — its report is order-independent.

## Consequences

**Good:**
- Server audit rows correlate one-to-one with the candidate list the admin submitted.
- Freshness check is robust against the admin reordering their input.

**Bad:**
- Callers who expect report order in `PromotionResult` will be surprised.

## Alternatives considered

None recorded; this was the consensus choice during the 2026-04-22 design session.

## Revisions

### amendment-1 (Phase 16 ship — 2026-05-20) — documentary; PromotionResult does not ship at Phase 16

**Status of this ADR remains Accepted** for historical record; the input-order-preservation contract on `PromotionResult.promoted` described in §Decision does NOT apply at Phase 16 because `PromotionResult` itself does not ship at 16.

**What Phase 16 actually ships:** a read-only similarity surface. The only output dataclass is `SimilarityReport` (with a `findings: tuple[Finding, ...]` field). `SimilarityReport.findings` ordering is `(candidate_id ASC, -score, matched_id ASC)` — admin sees candidates in id order, each with their best match first; deterministic tie-break by matched_id. This is the `similarity_report` sorting clause this ADR's §Decision called "order-independent" (sorted internally).

**`PromotionResult` contract pending Phase 24:** when Phase 24 ships `mindsos_admin/promotion.py` (the `propose_for_promotion()` entry-point), the result dataclass is `PromotionRequestResult` per ADR-0141 (Proposed), not `PromotionResult` per this ADR. The input-order-preservation principle survives the rename: `PromotionRequestResult.promoted` (or whatever the Phase 24 name is) preserves input order, deduped.

**Status flip pending Phase 24:** when ADR-0141 flips Accepted at Phase 24, this ADR's Status flips to Superseded (the `PromotionResult` shape is replaced; the input-order principle migrates into the ADR-0141 dataclass spec).

**Phase 16 design log:** `halvim_mindsos/confirmation_docs/PHASE_16_DESIGN_LOG.md` §1 Round 5 PB-U (PB-U3 documentary-amendment lock).
