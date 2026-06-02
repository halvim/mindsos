# ADR-0009: Similarity-report freshness via content hash with force-flag bypass

- **Status:** Accepted
- **Date:** 2026-04-22
- **Related:** ADR-0006, ADR-0008, ADR-0013

## Context

The promotion workflow is two-step: an admin first runs `similarity_report(candidate_ids)` to surface near-duplicate existing Global nodes, reviews the findings, and then calls `promote(candidate_ids, reviewed_report_id)` to commit. Between review and commit, the touched Locals or the Global may have mutated (another session's write landed, a concurrent promotion committed). If we blindly promote against a stale review, the admin's judgment — "these six drafts are novel, go ahead" — is based on a state that no longer exists.

At the same time, there are legitimate reasons to override: the admin reviewed the report, understands exactly what changed, and wants to commit anyway. A hard block would force a review loop that doesn't add information.

## Decision

Every `SimilarityReport` carries a deterministic `report_id` computed as:

```
sha256( sorted(candidate_ids)
      | each touched Local's metagraph_content_hash()
      | the Global's metagraph_content_hash() )
```

At `promote(..., reviewed_similarity_report_id=R, force=False)` time:

1. The server re-runs `KL.similarity_report(candidate_ids)` against the **current** installed state and gets a fresh `report_id = R'`.
2. If `R != R'` and `force is False`, the server raises `SimilarityReportStaleError(reviewed_report_id=R, fresh_report_id=R')`, audits `PROMOTION_REJECTED_STALE_REPORT`, and aborts — nothing is mutated.
3. If `force is True`, the freshness check is skipped; `None` is also a legal `reviewed_similarity_report_id` only when `force=True`.
4. On success, the audit `PROMOTION_COMMITTED` row stamps `promotion_forced: bool` and the `report_id` actually used.

`SimilarityReportStaleError` maps to HTTP 409 per the error taxonomy in `errors.py`.

## Rationale

- **Content hash, not wall-clock or version counter.** A content-based id means the report is invalidated precisely by changes that could matter; unrelated edits in an unrelated Local don't cause false staleness because the hash is scoped to the touched set.
- **Deterministic across callers.** Two admins running the same review on the same committed state get the same `report_id`. Good for audit, reproducibility, and test fixtures.
- **`force` with justification (audit), not a silent backdoor.** When an admin forces, the `promotion_forced=true` field plus the reviewed-vs-fresh ids live in the audit row permanently.
- **Re-check under lock.** The freshness re-check happens *after* `GLOBAL_PROMOTE_LOCK` and per-user mutexes are acquired (ADR-0006), so nothing can change between check and commit.

## Consequences

- Promotions are resilient to the classic TOCTOU attack: even a perfectly-timed interleaving between review and promote cannot sneak a change past.
- A review that sat idle for hours will typically be stale — expected UX, users retry with a fresh report.
- `SimilarityReport.report_id` is part of the stable API; any change to the hash construction is a breaking change.
- `force=True` without `reviewed_report_id` requires the admin to pass `force=True` explicitly; a stray `None` without force is a `ValueError`, not a silent bypass.
- The test suite exercises stale-rejection (mutating an author's Local between report and promote), force-bypass with a stale id, force-allows-None, and the ValueError on None-without-force.

## Alternatives considered

1. **Wall-clock TTL on reports ("valid for 5 minutes").** Rejected — no correctness guarantee; a fast change within 5 minutes would pass.
2. **Monotonic version counter per metagraph.** Works but requires plumbing a counter through every mutation path in KL; content hash has zero such coupling.
3. **Optimistic commit with post-hoc conflict detection.** Rejected — would force rollback after work is done, wasting effort; pre-commit check is cheaper.
4. **No override at all.** Rejected — forces re-review loops that don't add signal; the audit trail makes force safe.
