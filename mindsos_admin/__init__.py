"""MindsOS Admin Layer — Phase 16 surface.

Admin operations package — the permanent home for code that mutates
L1/L2 state outside the L4→L3→L1 cognitive loop. Per ADR-0140
§amendment-1 (Phase 15a): admin operations live in ``mindsos_admin/``,
not ``mindsos_server/``. Server (when built) imports admin for HTTP
endpoint handlers; admin code is not server code.

Phase 15a shipped (still in scope):

* :class:`ImportResult` — frozen dataclass returned by every importer
  ``run()``.
* :class:`ImporterProtocol` — structural protocol every importer
  satisfies.
* :func:`bootstrap_global` — module-level helper building a populated
  Global :class:`~mindsos_core.Metagraph` from a sequence of importer
  instances.
* :class:`DolceImporter`, :class:`OewnImporter`, :class:`FrameNetImporter`
  — three knowledge-source importers.

Phase 16 adds (this phase):

* :func:`compute_similarity` — read-only similarity scorer per
  ADR-0144 §Heuristic (Accepted at Phase 16 per §amendment-1).
  Three weighted scorers (Levenshtein + structural Jaccard + reference
  Jaccard); thresholds 0.85 blocking / 0.5 review.
* :func:`list_candidates` — promotion-candidate discovery helper;
  excludes ADR-0051 ``PROMOTED`` breadcrumbs by default.
* :class:`SimilarityReport` — frozen dataclass with content-hash
  ``report_id`` per ADR-0052 §amendment-1 (role-scoped).
* :class:`CandidateRef`, :class:`Finding` — frozen dataclass companions.
* :class:`EmptyComparisonError` — raised when all three similarity
  components undefined per ADR-0144 §amendment-2.
* :func:`metagraph_content_hash` — role-scoped content hash helper
  per ADR-0052 §amendment-1. Public; Phase 24's release-ship audit
  gate consumes the same primitive.

NOT in Phase 16 scope (Phase 24 owns):

* ``mindsos_admin/promotion.py`` — the mutating entry-point
  (``propose_for_promotion`` per ADR-0118 + ADR-0141). Reserved
  location; deferred from Phase 15a PB-19 forward-cite per Phase 16
  PB-1c reframe.
* ``PromotionResult`` / ``PromotionRequestResult`` dataclasses.
* Per-candidate atomic rollback (ADR-0053).
* Release-ship audit gate placement (ADR-0144 §Placement).

See ``halvim_mindsos/confirmation_docs/PHASE_16_DESIGN_LOG.md`` for the
5-round design ledger that arrived at this scope.

ADRs honoured at Phase 16:

* ADR-0010 (Accepted) — layer isolation. ``mindsos_admin`` imports
  ``mindsos_knowledge`` + ``mindsos_core`` (downward); imports no
  ``mindsos_server`` module.
* ADR-0042 (Accepted) + §amendment-1 (Phase 14) + §amendment-2 (Phase
  15a) — first-install sequences (unchanged at Phase 16).
* ADR-0043 (Accepted) — KL stays in-memory only. Admin is permitted
  file-I/O for importers; similarity reads only, no I/O.
* ADR-0049 (Accepted) + §amendment-1 (Phase 16) — documentary; gate
  on ``promote()`` does NOT ship at 16.
* ADR-0051 (Accepted) — PROMOTED breadcrumb consumed by
  :func:`list_candidates` default filter.
* ADR-0052 (Accepted) + §amendment-1 (Phase 16) — content-hash
  ``report_id`` (role-scoped; 6-decimal FP canonicalization;
  cross-mg input set).
* ADR-0053 (Accepted) + §amendment-1 (Phase 16) — documentary;
  per-candidate undo-stack does NOT ship at 16.
* ADR-0055 (Accepted) + §amendment-1 (Phase 16) — heuristic
  superseded by ADR-0144 §Heuristic; this ADR's heuristic does not
  ship at 16.
* ADR-0056 (Accepted) + §amendment-1 (Phase 16) — documentary;
  PromotionResult does not ship at 16.
* ADR-0140 (Proposed) + §amendment-1 (Phase 15a) — admin permanent
  home; consumed by Phase 16 for similarity surface location.
* ADR-0144 (Proposed) + §amendment-1 (Phase 16) — §Heuristic Accepted
  at 16; §Placement stays Proposed; module location
  ``mindsos_admin/similarity.py`` (relocated from
  ``mindsos_server/audit/similarity.py`` in original §Module layout).
* ADR-0144 §amendment-2 (Phase 16) — empty-pair exclusion at inner +
  outer means; :class:`EmptyComparisonError` contract.
"""

from __future__ import annotations

__version__ = "0.0.0+phase17"

from ._content_hash import metagraph_content_hash
from .bootstrap import (
    ImporterProtocol,
    ImportResult,
    bootstrap_global,
)
from .exceptions import AdminError, EmptyComparisonError
from .importers import (
    DolceImporter,
    FrameNetImporter,
    OewnImporter,
)
from .similarity import (
    CandidateRef,
    Finding,
    SimilarityReport,
    compute_similarity,
    list_candidates,
)

__all__ = [
    "__version__",
    # Phase 15a — importer infrastructure.
    "ImporterProtocol",
    "ImportResult",
    "bootstrap_global",
    "DolceImporter",
    "OewnImporter",
    "FrameNetImporter",
    # Phase 16 — similarity surface.
    "compute_similarity",
    "list_candidates",
    "CandidateRef",
    "Finding",
    "SimilarityReport",
    "metagraph_content_hash",
    # Exceptions.
    "AdminError",
    "EmptyComparisonError",
]
