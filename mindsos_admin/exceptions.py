"""Admin-layer exceptions (Phase 16+).

Phase 16 ships :class:`EmptyComparisonError`, raised by
:func:`mindsos_admin.compute_similarity` when all three weighted
similarity components (Levenshtein / structural Jaccard / reference
Jaccard) are undefined for a candidate-matched pair per ADR-0144
§amendment-2 (Phase 16).

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


__all__ = [
    "AdminError",
    "EmptyComparisonError",
]
