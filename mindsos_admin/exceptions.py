"""Admin-layer exceptions (Phase 16+).

Phase 16 ships :class:`EmptyComparisonError`, raised by
:func:`mindsos_admin.compute_similarity` when all three weighted
similarity components (Levenshtein / structural Jaccard / reference
Jaccard) are undefined for a candidate-matched pair per ADR-0144
§amendment-2 (Phase 16).

Phase 24 extends with promotion + audit-gate exceptions:

* :class:`BlockingFindingError` — audit gate's two-pass
  ``compute_similarity`` produced ≥1 blocking finding (score ≥0.85);
  ``mindsos_server.release.release_update`` catches, writes FAILED row
  with ``error_class="blocking_similarity_findings"``, emits
  ``EVT_RELEASE_FAILED``.
* :class:`EmptyReleaseError` — admin invoked ``release_update`` with
  no unshipped pending_mutations rows. CLI exit code 7.
* :class:`PendingMutationNotFoundError` — reserved for future propose-
  time validation (no v1 consumer).
* :class:`DuplicateProposalError` — reserved for future propose-time
  dedup (no v1 consumer; the release-ship audit gate is the canonical
  dedup choke point per ADR-0144 §am1).

The "undefined" case requires all three of:

1. Lev score undefined — neither node has a non-empty IRI tail (rare;
   only happens for IRIs without a ``:``-separated tail segment).
2. Structural Jaccard undefined — for every sub-feature
   (``frame_elements`` / ``synonyms`` / ``parents``), both the
   candidate's set AND the matched node's set are empty.
3. Reference Jaccard undefined — both candidate and matched have zero
   outbound ``ref:<role>`` properties AND zero outbound XRef rows.

Lev is well-defined whenever both nodes have non-empty IRI tails
(always the case for properly-minted nodes), so the all-three-undefined
case is rare in practice. The error contract gives callers an explicit
signal rather than a misleading 0.0 score.

Phase 24's release-ship audit gate (per ADR-0144 §Placement) may catch
this exception to skip degenerate findings, or propagate it to abort
release-ship on degenerate input — the policy is the consumer's choice.
"""

from __future__ import annotations


class AdminError(Exception):
    """Base for admin-layer exceptions (Phase 16+)."""


class EmptyComparisonError(AdminError):
    """A candidate-matched pair has no comparable signal.

    Raised by :func:`mindsos_admin.compute_similarity` when all three
    weighted components (Lev / Struct / Ref) are undefined for the pair
    per ADR-0144 §amendment-2 (Phase 16).

    Carries the candidate id and matched id as attributes for caller
    inspection.
    """

    def __init__(self, candidate_id: str, matched_id: str) -> None:
        self.candidate_id = candidate_id
        self.matched_id = matched_id
        super().__init__(
            f"All three similarity components (Lev/Struct/Ref) are "
            f"undefined for candidate {candidate_id!r} vs matched "
            f"{matched_id!r}; no comparable signal."
        )


class BlockingFindingError(AdminError):
    """Audit gate found ≥1 blocking similarity finding.

    Raised by :func:`mindsos_admin.audit_gate.run` (Phase 24) when its
    two-pass ``compute_similarity`` produced ≥1 finding with score ≥
    threshold_blocking (0.85 per ADR-0144 §Heuristic). Caller
    (:func:`mindsos_server.release.release_update`) catches, writes
    FAILED ``releases`` row with ``error_class=
    "blocking_similarity_findings"`` per ADR-0114 §am3, emits
    ``EVT_RELEASE_FAILED`` per Phase 24 design log PB-27(a), re-raises
    to admin caller.

    Force-override is v2 per ADR-0118 §Tradeoffs. v1 admin amends
    pending content + reruns ``release_update`` (rerun-suppression
    handles the prior-FAILED partial-ship per PB-Z1(b) + ADR-0114
    §am3).

    Carries the blocking findings list as an attribute for caller
    inspection (CLI output, audit row's ``extra_json``).
    """

    def __init__(self, blocking_findings: list) -> None:  # noqa: ANN001
        # Type annotation deferred: list[SimilarityWarning] would
        # create import cycle with audit_gate; loose typing acceptable.
        self.blocking_findings = blocking_findings
        super().__init__(
            f"Audit gate found {len(blocking_findings)} blocking "
            f"similarity finding(s); release-ship aborted. "
            f"Amend pending content + rerun (rerun-suppression handles "
            f"prior partial-ship per ADR-0114 §am3)."
        )


class EmptyReleaseError(AdminError):
    """Admin invoked ``release_update`` with no unshipped pending.

    Raised by :func:`mindsos_server.release.release_update` when the
    audit-gate-snapshot SELECT against ``pending_mutations`` returns
    zero rows (``WHERE shipped_in_release IS NULL`` per PB-26(b)).
    Strict-fail per Phase 24 design log PB-21(a) — empty release is
    likely-bug (admin clicked ship without proposing); explicit error
    surfaces the mismatch instead of writing a no-op SHIPPED row.

    CLI maps to exit code 7 per Phase 24 design log PB-14(b).
    """

    def __init__(self) -> None:
        super().__init__(
            "No unshipped pending mutations; nothing to release. "
            "Propose at least one mutation via "
            "``mindsos server release propose-for-promotion`` "
            "before invoking ``release ship``."
        )


class PendingMutationNotFoundError(AdminError):
    """Referenced pending_mutations.mutation_id does not exist.

    Reserved for future propose-time validation surfaces (e.g., an
    admin-rollback verb that deletes a specific pending row). **No v1
    consumer at Phase 24** — declared per Phase 24 design log §5
    exception-roster forward-shape contract.
    """

    def __init__(self, mutation_id: int) -> None:
        self.mutation_id = mutation_id
        super().__init__(
            f"pending_mutations row {mutation_id} does not exist."
        )


class DuplicateProposalError(AdminError):
    """Propose-time near-duplicate detection (reserved for v2).

    Reserved for a future propose-time intra-pending similarity check
    (PIVOT §7.9 candidate-discovery tooling). **No v1 consumer at
    Phase 24** per PB-24(c) — the canonical dedup choke point is the
    release-ship audit gate at PB-24(b). Declared per Phase 24 design
    log §5 exception-roster forward-shape contract.
    """

    def __init__(self, candidate_id: str, matched_id: str, score: float) -> None:
        self.candidate_id = candidate_id
        self.matched_id = matched_id
        self.score = score
        super().__init__(
            f"Candidate {candidate_id!r} is a near-duplicate of "
            f"pending {matched_id!r} (score {score:.3f})."
        )


__all__ = [
    "AdminError",
    "EmptyComparisonError",
    "BlockingFindingError",
    "EmptyReleaseError",
    "PendingMutationNotFoundError",
    "DuplicateProposalError",
]
