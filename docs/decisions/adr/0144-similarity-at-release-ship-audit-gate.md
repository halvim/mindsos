---
title: Similarity heuristic at release-ship audit gate; restore spec
status: Accepted
date: 2026-04-27
layer: L0
---

# ADR-0144: Similarity heuristic at release-ship audit gate; restore spec

**Status:** Accepted (2026-05-22 — Phase 24 ship; §Heuristic was Accepted at Phase 16 per §amendment-1; §Placement Accepts at this ship per §amendment-2; §amendment-1 partial-flip retires; ADR-0115 ships the audit-gate consumer; `mindsos_admin/audit_gate.py::run` consumes Phase 16's `compute_similarity` two-pass.)

**Date:** 2026-04-27

**Related:** ADR-0118 (per-user transactional promotion), ADR-0115 (audit gate — Reserved), ADR-0009 (similarity report freshness — superseded), ADR-0138 (KL drops write API), ADR-0141 (delete `promote()`).

## Context

Today's `KnowledgeLayer.similarity_report(session, candidates) -> SimilarityReport` is a content-addressed deterministic read used as a "freshness gate" by the deleted `promote()` (ADR-0141). The shipped heuristic is exact-match (1.0) + prefix-match (0.7) with threshold 0.5 — Pareto-dominated by both the original spec (Levenshtein + structural overlap + reference Jaccard) and a simpler exact-only baseline.

ADR-0141 deletes `promote()`. The pivot's `propose_for_promotion()` (relocated to `mindsos_server` per ADR-0140) does not enforce similarity. The question: where, if anywhere, does similarity live now?

## Decision

**Similarity moves into the release-ship audit gate (ADR-0115). Restore the original spec heuristic.**

### Placement

Similarity findings surface in `release_update()`'s audit step:

1. Admin invokes `release_update(admin_session, ...)` to ship a release.
2. Audit step iterates `pending_global` entries.
3. For each candidate, compute `SimilarityFinding` against the current Global.
4. Block release if any finding exceeds an admin-configurable threshold (default: 0.85 strong overlap).
5. Admin reviews findings, decides per-candidate (accept / drop / merge / defer).

There is **no pre-flight advisory** for the user calling `propose_for_promotion()`. The pivot model already accepts that proposals may collide; the audit gate is where collision is resolved.

### Heuristic

Restore the spec from `_source_backup/docs_legacy_full/DESIGN_CUSTOM_KNOWLEDGE.md` §12.5. Three weighted scorers:

- **Levenshtein** on canonical names (target IRI tail) — 0.0 to 1.0.
- **Structural overlap** — Jaccard on the candidate's frame-element set + synonym set + parent-class set against an existing Global node.
- **Reference Jaccard** — Jaccard on outbound `ref:<role>` and `XRef` targets.

Default weights: 0.4 / 0.4 / 0.2. Threshold 0.85 for "blocking" finding; 0.5–0.85 surfaced as "review."

The shipped prefix-match heuristic deletes.

### Module layout

- `mindsos_server/audit/similarity.py` — scorers + `compute_similarity(candidate, global_mg, weights, threshold) -> list[SimilarityFinding]`.
- `mindsos_server/release.py::release_update()` calls into it before the atomic ship.
- KL keeps no similarity surface. The shipped `mindsos_knowledge/similarity.py` deletes.

## Rationale

Pre-flight advisory at `propose_for_promotion()` time was rejected because:

- Skippable; no audit trail of what was checked.
- Encourages users to ignore findings ("I'm sure mine is fine").
- Requires the same scorer in two places (or one shared module imported from KL into server, which violates the layering).

Audit-gate placement is honest:

- Similarity is a *quality gate*. Quality gates belong where decisions are made, not where intent is expressed.
- Admin sees the full batch's collision picture, not a one-at-a-time snapshot.
- ADR-0115 already owns the audit slot; adding similarity is adding a check, not a new mechanism.

The heuristic restoration is straightforward correction: the shipped middle-ground (prefix-match) was Pareto-dominated by spec. Either restore spec or strip to exact-only. Since the audit gate gives similarity a real consumer (admin review), spec is the right ceiling.

## Consequences

**Good:**

- One similarity scorer in one place (`mindsos_server/audit/similarity.py`), called by one consumer (`release_update`).
- Admin sees aggregate collision findings at decision time.
- No two-format scorer drift (KL's vs server's).
- Heuristic is at least as good as the original spec; tunable via weights.

**Tradeoffs:**

- Users proposing don't get pre-flight collision feedback. Acceptable: pivot model already accepts proposal-time uncertainty.
- The spec heuristic is heavier than prefix-match (~70 LOC + tests for three scorers). Released-batch sizes are small (admin batches), so cost is amortised.
- Existing similarity tests delete; new tests under `tests_server/test_audit_similarity.py`.

## Alternatives considered

1. **Drop similarity entirely.** Rejected — admin gating with no collision visibility is worse than gating with imperfect findings.
2. **Pre-flight advisory only at `propose_for_promotion()`.** Rejected — skippable; no audit trail.
3. **Pre-flight + audit gate (D from the design discussion).** Rejected — two implementations of the same scorer; coordination tax.
4. **Keep the prefix-match heuristic.** Rejected — Pareto-dominated. If similarity gates real decisions, the heuristic must be at least minimally correct.
5. **Honest minimum (exact-only, threshold 1.0).** Considered. Loses the structural and reference signal; admin sees nothing for "X is similar to Y but not identical." Spec is the right default; tune weights down if admin finds findings too noisy.

## Implementation references

- New module: `mindsos_server/audit/similarity.py` (scorers + `SimilarityFinding`).
- `mindsos_server/release.py::release_update()` adds the audit step.
- Delete: `mindsos_knowledge/similarity.py` (if separate file) or remove `similarity_report()` from `KnowledgeLayer` per ADR-0138.
- Admin UX: out of scope for this ADR; documented in `docs/usage/server/promotion.md` once admin tooling lands.
- ADR moves to Accepted when (a) audit-gate similarity ships in `release_update()`, (b) the three scorers are tested, (c) `docs/usage/server/promotion.md` documents the admin review flow with similarity findings.

## Revisions

### amendment-1 (Phase 16 ship — 2026-05-20) — §Heuristic Accepted; §Placement stays Proposed; module relocated to admin

**Partial Status flip:** ADR-0144 ships as TWO decisions — §Heuristic (the three weighted scorers + their weights + thresholds) and §Placement (similarity moves to the release-ship audit gate in `release_update()`). Phase 16 ships §Heuristic; Phase 24 ships §Placement.

**§Heuristic — Accepted at Phase 16:**

* `mindsos_admin/similarity.py` ships `compute_similarity(mg, candidates, *, role, target_mg=None, threshold_blocking=0.85, threshold_review=0.5) -> SimilarityReport`.
* Three weighted scorers per §Heuristic: Levenshtein on IRI tail (canonical name) + structural Jaccard on `(frame_elements, synonyms, parents)` triple + reference Jaccard on outbound `ref:<role>` properties UNIONed with XRef rows.
* Weights 0.4 / 0.4 / 0.2; thresholds 0.85 blocking / 0.5 review per §Heuristic. Thresholds exposed as constructor parameters with §Heuristic defaults (per Phase 16 PB-H Bundle II).
* In-house Levenshtein DP (`~30 LOC`); zero external dependency.
* Per-role feature extractors for ontology / lexicon / concepts (per Phase 16 PB-B2; alignment + promoted-pipelines + task-patterns + problem-trace + capacity-state extractors return empty features at 16 — no candidates exist there yet).
* `Finding` dataclass carries the `classification: Literal["blocking", "review"]` field per §Heuristic threshold semantics.

**§Placement — stays Proposed at Phase 16; ships at Phase 24:**

* `release_update()` does not exist at Phase 16. `mindsos_admin/promotion.py` (the `propose_for_promotion()` entry-point) does not exist either — both defer to Phase 24 per ADR-0118 + ADR-0141 + Phase 16 PB-1c.
* When Phase 24 ships `release_update()`, the audit step at §Placement invokes Phase 16's `compute_similarity` — the heuristic ships once, in admin, and is called from two consumers (Phase 16 admin CLI for ad-hoc admin scans; Phase 24 release-ship audit gate). Reuse is by design (per Phase 16 PB-K2 `target_mg` keyword + PB-F2 role-scoped hash supporting cross-mg input).

**Module relocation vs §Module layout in original §Decision:**

* §Module layout originally said `mindsos_server/audit/similarity.py`. **Superseded at Phase 16** by `mindsos_admin/similarity.py` (per ADR-0140 §amendment-1 admin permanent home; the original `mindsos_server/` route under §Module layout is a category mismatch for the same reason ADR-0140 §Decision §1+§2 was superseded).
* The deletion targets in §Implementation references (`mindsos_knowledge/similarity.py` doesn't exist; ADR-0138's removal of `KL.similarity_report` honoured by absence per Phase 14 PB-6) are unchanged.

**Full Accept of this ADR pending Phase 24:** when Phase 24 ships `release_update()` + the §Placement audit step, this amendment-1 retires and this ADR's overall Status flips Accepted (the partial flip closes).

**Phase 16 design log:** `halvim_mindsos/confirmation_docs/PHASE_16_DESIGN_LOG.md` §1 Round 1 PB-2 (PB-2b lock) + Round 2 PB-A (PB-A2 partial-flip mechanism) + Round 2 PB-B (PB-B2 per-role extractors) + Round 3 PB-H (Bundle II) + Round 4 PB-K (PB-K2 target_mg signature).

### amendment-2 (Phase 16 ship — 2026-05-20) — empty-pair exclusion at inner + outer means; EmptyComparisonError contract

ADR-0144 §Heuristic specifies three sub-features for the structural Jaccard (frame_elements, synonyms, parents) and three outer components (Lev, Struct, Ref) for the weighted mean. Neither clause specifies behaviour when input sets are empty. Phase 16 PB-G2 + PB-L1 lock the rule:

**At the inner structural Jaccard:** for each sub-feature, if both the candidate's set AND the matched node's set are empty, that sub-feature is EXCLUDED from the structural Jaccard mean (not 0/0 NaN, not 0.0 contribution). The structural score is the arithmetic mean over the non-excluded sub-features. If all three sub-features are excluded, the structural component itself is undefined (passed up to the outer mean as "undefined").

**At the outer weighted mean (Lev / Struct / Ref):** the same rule applies. If a component is undefined (Struct undefined because all three sub-features excluded; Ref undefined because both candidate and matched have zero outbound `ref:<role>` properties AND zero outbound XRef rows), that component is EXCLUDED. Remaining weights renormalize to sum 1.0. If all three outer components are undefined, `compute_similarity` raises `mindsos_admin.exceptions.EmptyComparisonError` (the candidate-matched pair has nothing to compare).

Lev is well-defined whenever both nodes have non-empty IRI tails (always the case for properly-minted nodes), so the all-three-undefined case is rare in practice. The error contract gives callers an explicit signal rather than a misleading 0.0 score.

**`EmptyComparisonError` ships at `mindsos_admin/exceptions.py`** (NEW module at Phase 16). Phase 24's audit gate may choose to catch it (skip degenerate findings) or propagate (release-ship abort on degenerate input).

**Phase 16 design log:** `halvim_mindsos/confirmation_docs/PHASE_16_DESIGN_LOG.md` §1 Round 3 PB-G (PB-G2 inner-mean rule) + Round 4 PB-L (PB-L1 outer-mean rule + EmptyComparisonError raise).

### amendment-2 (Phase 24 ship — 2026-05-22) — §Placement fully Accepted; §am1 partial-flip retires; two-pass audit-gate consumption

**Full Status flip:** Proposed → Accepted at Phase 24 ship. §amendment-
1's partial-flip mechanism (§Heuristic Accepted at Phase 16; §Placement
stays Proposed) closes here: Phase 24 ships `mindsos_admin/audit_gate.
py::run` per ADR-0115 + `mindsos_server/release.py::release_update`
consumer, which invokes `compute_similarity` at the release-ship
audit gate exactly as §Placement specifies.

This amendment retires §amendment-1's partial-flip mechanism and
records the §Placement implementation specifics.

**§Placement implementation per ADR-0115:** `mindsos_admin/audit_
gate.py::run(admin_session, *, pending_mutations, canonical_global,
pending_global) -> AuditGateResult` invokes `compute_similarity`
**twice per role** (Phase 24 design log PB-24(b)):

```python
intra_pending = compute_similarity(
    mg=pending_global[role], candidates=candidates, role=role,
    target_mg=None,                                            # intra-mg form
)
cross_mg = compute_similarity(
    mg=pending_global[role], candidates=candidates, role=role,
    target_mg=canonical_global[role],                          # cross-mg form
)
```

The two-pass design closes a load-bearing correctness gap that
single-pass cross-mg-only missed: pending-vs-pending duplicates
(admin proposed the same content twice). Phase 16 PB-K2 cross-mg
mode + PB-M2 intra-mg candidate-vs-candidate inclusion together
make both passes useful.

**§"Heuristic" weights + thresholds unchanged:** 0.4 / 0.4 / 0.2
weighted mean; 0.85 blocking / 0.5 review thresholds. Shipped at
Phase 16 per §am1; consumed unchanged at Phase 24.

**§"Module layout" final correction:** §am1 superseded the original
"`mindsos_server/audit/similarity.py`" location → `mindsos_admin/
similarity.py`. §am2 confirms the symmetric placement for the audit
gate: `mindsos_admin/audit_gate.py` (Phase 24 design log PB-9(a))
parallel to `mindsos_admin/similarity.py`. The original §Decision
"§Module layout" specifies `mindsos_server/release.py::release_
update()` calls into similarity; this clause holds — release.py is
server-side per ADR-0006 ownership of RELEASE_SHIP_LOCK, and the
import edge `mindsos_server → mindsos_admin` is the legitimate
composition direction (server composes admin machinery, per
CLAUDE.md "Server imports downward into the stack").

**`SimilarityWarning` records carry `source` discriminator:**
`SimilarityWarning.source: Literal["intra_pending", "cross_mg"]`
records which pass surfaced each finding. Admin can distinguish
"two admin-proposed candidates collide with each other" (intra_
pending) from "admin-proposed candidate collides with shipped
canonical" (cross_mg). Both block at blocking threshold; admin's
resolution differs (delete one of the duplicates vs amend the
candidate that collides with canonical).

**Blocking-finding handling per ADR-0115 + Phase 24 design log
PB-20(c):** Any blocking finding → `BlockingFindingError` raise →
`release_update` writes a FAILED `releases` row with `error_class=
"blocking_similarity_findings"` + emits `EVT_RELEASE_FAILED`. No
force-override at v1 (deferred to v2 per ADR-0118 §Tradeoffs).
Admin amends pending content + reruns.

**§"Implementation references" addenda:** ADR-0115 ships at Phase
24 alongside this full Accept; both ADRs share the implementation
surface (`mindsos_admin/audit_gate.py` per PB-9(a), with `compute_
similarity` from Phase 16 unchanged). ADR-0049 / 0053 / 0056
Supersessions per §am1 lock close at Phase 24 ship (per Phase 24
design log §4 ADR delta).

**§"EmptyComparisonError" contract (per §am2) unchanged:** Phase 24
audit gate may catch `EmptyComparisonError` to skip degenerate
findings (e.g., comparing a node with no IRI tail and no features
against a similar-shape pending neighbour) without abort. The
choice is implementation-side; v1 default per ADR-0115 §5
implementation reference is to **propagate** (release-ship abort on
degenerate input — admin's data is malformed).

**Phase 24 design log:** `halvim_mindsos/confirmation_docs/PHASE_24_
DESIGN_LOG.md` §1 Round 2 PB-9 (audit-gate module home lock) + Round
5 PB-24 (two-pass) + §4 ADR delta.
