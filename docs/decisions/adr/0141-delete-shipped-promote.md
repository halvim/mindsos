---
title: Delete shipped KL.promote(); ADR-0118 path is canonical
status: Accepted
date: 2026-04-27
layer: L2
---

# ADR-0141: Delete shipped `KL.promote()`; ADR-0118 path is canonical

**Status:** Accepted (2026-05-22 — Phase 24 ship; halvim's KL never ported `promote()` per Phase 14 PB-6 + ADR-0138 honoured by absence, so "delete shipped" is vacuous in halvim; surface relocated to `mindsos_admin/promotion.py` per §amendment-1.)

**Date:** 2026-04-27 (proposed), 2026-05-22 (accepted)

**Related:** ADR-0118 (per-user transactional promotion), ADR-0007 (`MetagraphSnapshot` rollback — superseded), ADR-0138 (KL drops write API), ADR-0140 (server owns admin), ADR-0144 (similarity at audit gate).

## Context

`mindsos_knowledge/promotion.py` ships `KnowledgeLayer.promote(session, candidates, reviewed_similarity_report_id, force=False) -> PromotionResult`. It implements the pre-pivot cross-user atomic model: server-orchestrated under `GLOBAL_PROMOTE_LOCK`, KL does in-memory writes, rollback via `MetagraphSnapshot` per ADR-0007.

ADR-0118 supersedes ADR-0007 with the pivot model: per-user transactional `propose_for_promotion()` writing into a `pending_global` buffer, release-boundary atomicity at `release_update()` under `RELEASE_SHIP_LOCK`. The two paths cannot coexist — they have different atomicity semantics and different consumers.

ADR-0138 separately removes KL's write API. `promote()` is one of the methods that go.

## Decision

**Delete `KnowledgeLayer.promote()` from `mindsos_knowledge/promotion.py`.** All promotion flows through:

- `mindsos_server.propose_for_promotion(session, candidates) -> PromotionRequestResult` (relocated per ADR-0140) — per-user transactional, writes into `pending_global`.
- `mindsos_server.release_update(admin_session, ...) -> ReleaseResult` — admin-batched, atomic under `RELEASE_SHIP_LOCK`.
- `KnowledgeLayer.request_promotion(session, draft_id, justification) -> PromotionRequest` (per ADR-0137) — user-initiated request that admin approves.

L4's cognitive layer reaches the proposal path through `capacity:promote:pipeline` (ADR-0145), which wraps `mindsos_server.propose_for_promotion()`.

`mindsos_knowledge/promotion.py` deletes. Existing `PromotionResult`, `PromotedNode` dataclasses move to `mindsos_server/promotion.py` if still needed; otherwise drop.

## Rationale

ADR-0118 is the explicit supersession. Keeping `promote()` alongside `propose_for_promotion()` creates two paths with different atomicity guarantees and different consumers, which is the exact "two ways to do it" anti-pattern the pivot was designed to eliminate.

The "wrap `promote()` as a thin shim over `propose_for_promotion()` + immediate `release_update()`" alternative (B from the design discussion) was considered and rejected because it hides the semantic shift: cross-user-atomic was specifically the failure mode the pivot stops, and silently auto-shipping each promotion as its own release defeats the release model.

## Consequences

**Good:**

- One promotion path. ADR-0007 is fully retired.
- Tests against `promote()` migrate to tests against `propose_for_promotion()` + `release_update()`, which is what the pivot expected anyway.
- `MetagraphSnapshot` use is now contained to `release_update()` (per ADR-0129); KL no longer needs it.

**Tradeoffs:**

- Tests of the old `promote()` path delete or rewrite (~30 tests).
- Any external caller of `KnowledgeLayer.promote()` breaks. Audit before delete.
- The `reviewed_similarity_report_id` freshness gate goes away with the method; ADR-0144 replaces it with audit-gate similarity at `release_update()`.

## Alternatives considered

1. **Keep `promote()` for migration window with `DeprecationWarning`.** Rejected — pivot is canonical; coexistence period invites callers to keep using the wrong path. Audit + delete is cleaner.
2. **Repurpose `promote()` as wrapper over `propose_for_promotion()` + immediate `release_update()`.** Rejected — auto-shipping each promotion as its own release defeats the release-batching model.
3. **Move `promote()` to `mindsos_server` as admin-direct path.** Rejected — admin already has `release_update()` for batched ship; no need for a per-promotion admin path.

## Implementation references

- Files affected: `mindsos_knowledge/promotion.py` (delete), `mindsos_knowledge/__init__.py` (drop re-exports), `tests/unit/knowledge/test_promotion.py` (rewrite for pivot path), `tests_kl/` (audit).
- Audit step: `grep -rn 'KnowledgeLayer.promote\b' --include='*.py'` before deletion.
- ADR moves to Accepted when (a) `promote()` deleted from KL, (b) all tests migrated, (c) `docs/usage/server/promotion.md` reflects the pivot path only.

## Revisions

### amendment-1 (Phase 24 ship — 2026-05-22) — surface location corrected to mindsos_admin; KL no-op in halvim; doc deferred

**Status flip:** Proposed → Accepted at Phase 24 ship. This
amendment records (a) the surface location correction, (b) the
halvim-specific no-op for "delete shipped `promote()`", and (c) the
doc-defer.

**§Decision surface location correction:** §Decision names
**`mindsos_server.propose_for_promotion(session, candidates) ->
PromotionRequestResult`** as the relocated entry-point. The canonical
location at Phase 24 ship is **`mindsos_admin.propose_for_promotion
(admin_session, proposal) -> PromotionResult`** — a top-level
function in `mindsos_admin/promotion.py`, NOT in `mindsos_server`.
Rationale: ADR-0140 §am1 established `mindsos_admin/` as the
permanent home for admin-curated surfaces; ADR-0144 §am1 followed
for similarity; this ADR (and ADR-0118 §am1, Phase 24 ship) follow
for propose. The `mindsos_server.propose_for_promotion` location in
§Decision was a pre-ADR-0140-§am1 placement that drifted from the
admin-home convention.

The signature shape also tightens: `proposal: PromotionProposal`
(per PIVOT §7.1) replaces the original `candidates` list, and the
return type is `PromotionResult` (matches PIVOT §7.1 + Phase 24
design log PB-18(a) full PromotionProposal shape).

**§Decision "Delete `KnowledgeLayer.promote()` from `mindsos_
knowledge/promotion.py`" — vacuous in halvim:** halvim's Phase 14
ship (per `project_mindsos_phase_14_implemented` memory) honoured
ADR-0138 by absence — `KnowledgeLayer.promote()`, `similarity_
report()`, and `add_local_alignment()` were NOT ported from the v3
baseline. `mindsos_knowledge/promotion.py` does not exist in halvim
(probe-confirmed at Phase 24 round 0). The "delete shipped" clause
has nothing to delete.

The corresponding test migration (§Consequences "Tests of the old
`promote()` path delete or rewrite (~30 tests)") is also vacuous —
no `tests/unit/knowledge/test_promotion.py` was ported.

This is a halvim-specific honoured-by-absence pattern (Phase 14 PB-
6 precedent). The §Decision clause holds upstream of halvim (the
original mindsos repo); in halvim it's a documentary acknowledgement
that the deletion already happened structurally at Phase 14.

**§"Implementation references" file-affected list correction:** The
list `mindsos_knowledge/promotion.py` (delete), `mindsos_knowledge/
__init__.py` (drop re-exports), `tests/unit/knowledge/test_
promotion.py` (rewrite) is **vacuous in halvim** (none of those
files exist). Phase 24's actual file affected list:

* `mindsos_admin/promotion.py` (NEW at Phase 24) — `propose_for_
  promotion` entry-point.
* `mindsos_admin/__init__.py` (MODIFIED) — +exports.
* `tests/phase_24/test_propose_for_promotion_atom.py` (NEW at
  Phase 24) — happy path.

**`docs/usage/server/promotion.md` deferred:** Phase 24 design log
§6 + Phase 18-22 documentation-deferral pattern defer the user-
facing doc to Phase 38 (doc consolidation). The §Decision §c clause
("`docs/usage/server/promotion.md` reflects the pivot path only")
relaxes to "Phase 38 doc consolidation reflects the pivot path
only."

**`capacity:promote:pipeline` (ADR-0145):** §Decision references
the L4 cognitive layer reaching the proposal path through
`capacity:promote:pipeline` (ADR-0145). L4 / L3 capacity-promote
ship at later phases (Phases 33-35 + L4 phases); the wrapping
contract holds — `capacity:promote:pipeline` will wrap
`mindsos_admin.propose_for_promotion()` when capacity-promote
ships. No P24 implementation.

**Phase 24 design log:** `halvim_mindsos/confirmation_docs/PHASE_24_
DESIGN_LOG.md` §1 Round 2 PB-8 (surface location lock) + §4 ADR
delta (this ADR + ADR-0118 §am1 + ADR-0144 §am2 batch).
