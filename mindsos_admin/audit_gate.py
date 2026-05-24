"""Release-ship audit gate (Phase 24 — ADR-0115).

Per ADR-0115 (NEW at Phase 24) + ADR-0144 §am2 + Phase 24 design log
Round 5 PB-24 (two-pass) + PB-Z7 (suppression-set) + PB-Z11 (single
pending Metagraph) + PB-Z15 (FAILED-row watermark) + PB-Z16
(EmptyComparisonError propagates).

This module ships :func:`run` — the single entry-point for the
release-ship audit gate. Consumed by
:func:`mindsos_server.release.release_update` per ADR-0118 §"Decision"
§2 audit-gate step.

**v1 narrow scope per Phase 24 design log §6:**

* Two ImpactReport sections only: :class:`ReleaseSummary` (from
  pending_mutations data) + :class:`SimilarityWarning` (from
  ``compute_similarity`` two-pass per PB-24(b)).
* Three PIVOT §7.8 sections deferred to substrate phases:
  ``PeerDepStatus`` (needs peer_deps table), ``UserImpactDistribution``
  (needs cross-user read at Phase 25), ``CompositionCheck`` (needs
  Core ``CompositionalMetaEdge``).
* Force-override is v2 per ADR-0118 §Tradeoffs.

**Two-pass per PB-24(b):** Phase 16 cross-mg form does NOT self-
exclude by node_id (probe-confirmed at ``mindsos_admin/similarity.py``
line 271 — requires ``comparison_mg is mg`` which is False on cross-
mg). So the gate runs:

1. ``intra_pending`` pass (``target_mg=None``) — catches admin-
   proposed-same-content-twice duplicates within pending; self-
   exclusion fires for matched_id == candidate.node_id.
2. ``cross_mg`` pass (``target_mg=canonical_global_mg``) — catches
   pending-vs-shipped-canonical collisions; does NOT self-exclude.

**Rerun suppression-set per PB-Z7(a) + PB-Z15(a):** On a rerun after
a FAILED release with partial-ship, the cross-mg pass would fire
blocking findings against the prior-shipped canonical content (same
node_id; cross-mg doesn't self-exclude). Suppression set =
``failed_release_canonical_node_ids`` union over FAILED rows since
last SHIPPED (per ADR-0114 §am3 §2 SQL watermark) — cross-mg
findings whose ``matched_id`` is in the suppression set are dropped.

The intra-pending pass is NOT suppression-filtered: legitimate
duplicates within pending must still surface (admin proposed same
content twice).

**EmptyComparisonError propagates per PB-Z16(a):** ``compute_
similarity`` may raise :class:`EmptyComparisonError` for degenerate
pairs (all three sim components undefined per ADR-0144 §am2). At
v1, the audit gate propagates this; caller
(:func:`release_update`) writes FAILED row with ``error_class=
"empty_comparison"`` per ADR-0114 §am3 §4.

ADR cross-references: ADR-0115 (this module's defining ADR); ADR-
0144 §am2 (placement + two-pass); ADR-0114 §am3 §1+§4 (FAILED
manifest_json + error_class enum); ADR-0118 §"Decision" §2 (audit
gate callsite); Phase 24 design log §1 PB-9 + PB-24 + PB-Z7 + PB-Z11
+ PB-Z15 + PB-Z16.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, Literal, Mapping, Sequence

from mindsos_core import Metagraph

from mindsos_admin.exceptions import EmptyComparisonError
from mindsos_admin.similarity import (
    CandidateRef,
    Finding,
    compute_similarity,
)
from mindsos_server.session import Session

if TYPE_CHECKING:
    from mindsos_core.persistence.client import Client


__all__ = [
    "PendingMutationRow",
    "SimilarityWarning",
    "ReleaseSummary",
    "AuditGateResult",
    "run",
]


# ─── §1 PendingMutationRow ──────────────────────────────────────────────


@dataclass(frozen=True)
class PendingMutationRow:
    """A snapshot of one ``pending_mutations`` row passed to :func:`run`.

    Per Phase 24 design log PB-26(b) — release_update selects the
    snapshot set inside its admin_tx and passes it to ``run(...)``.
    The gate doesn't re-query SQLite; it operates on the supplied
    snapshot.

    Attributes:
        mutation_id: ``pending_mutations.mutation_id`` PK.
        proposer_admin_user_id: Who proposed this mutation.
        target_role: The role-graph for the candidate node.
        node_id: The candidate's node_id (from payload_json).
        node_type: The candidate's NodeType (from payload_json).
        source_user_id: Always None at v1 (PB-11(a) admin-direct only).
    """

    mutation_id: int
    proposer_admin_user_id: str
    target_role: str
    node_id: str
    node_type: str
    source_user_id: str | None = None


# ─── §2 SimilarityWarning ───────────────────────────────────────────────


@dataclass(frozen=True)
class SimilarityWarning:
    """One blocking-or-review finding from the audit gate.

    Per ADR-0144 §am2 — carries a ``source`` discriminator so admin
    can distinguish "two admin-proposed candidates collide" (intra_
    pending) from "admin-proposed candidate collides with shipped
    canonical" (cross_mg). Resolution differs per source.

    Suppressed cross-mg findings (whose ``matched_node_id`` is in
    the PB-Z7 suppression set from a prior FAILED release) are NOT
    emitted as warnings.

    Attributes:
        candidate_node_id: Pending node that triggered the finding.
        matched_node_id: Existing node (in pending or canonical) the
            candidate scored against.
        score: Combined similarity score (0.0-1.0).
        classification: ``"blocking"`` if score ≥ 0.85, ``"review"``
            if 0.5-0.85 per ADR-0144 §Heuristic.
        source: ``"intra_pending"`` (matched within pending_global)
            or ``"cross_mg"`` (matched against canonical_global).
        matched_is_candidate: Only meaningful when source ==
            "intra_pending"; True if matched_node is itself a
            candidate in the snapshot set.
        role: Role-graph where the comparison happened.
    """

    candidate_node_id: str
    matched_node_id: str
    score: float
    classification: Literal["blocking", "review"]
    source: Literal["intra_pending", "cross_mg"]
    matched_is_candidate: bool
    role: str


# ─── §3 ReleaseSummary ──────────────────────────────────────────────────


@dataclass(frozen=True)
class ReleaseSummary:
    """The v1 ImpactReport summary section per ADR-0115.

    Attributes:
        mutation_count: Number of pending_mutations rows in the
            snapshot set; == len(pending_mutations) param to run().
        roles_affected: Distinct roles across the snapshot set
            (sorted).
        proposer_admin_user_ids: Distinct proposers across the
            snapshot set (sorted).
    """

    mutation_count: int
    roles_affected: tuple[str, ...]
    proposer_admin_user_ids: tuple[str, ...]


# ─── §4 AuditGateResult ─────────────────────────────────────────────────


@dataclass(frozen=True)
class AuditGateResult:
    """Outcome of :func:`run`.

    Per ADR-0115 §3 shape + Phase 24 design log PB-20(c) blocking-
    finding handling.

    Attributes:
        passed: True iff no blocking findings; False if ≥1 blocking
            (release_update writes FAILED row).
        summary: :class:`ReleaseSummary` always populated.
        blocking_findings: Findings with classification ==
            "blocking"; empty when passed=True.
        review_findings: Findings with classification == "review";
            informational only — never blocks. Admin sees them in
            CLI output.
        suppressed_count: Number of cross-mg findings filtered by
            the PB-Z7 suppression set (logging / forensic interest).
    """

    passed: bool
    summary: ReleaseSummary
    blocking_findings: tuple[SimilarityWarning, ...] = field(default_factory=tuple)
    review_findings: tuple[SimilarityWarning, ...] = field(default_factory=tuple)
    suppressed_count: int = 0


# ─── §5 run ─────────────────────────────────────────────────────────────


def run(
    admin_session: Session,
    client: "Client | None" = None,
    *,
    pending_mutations: Sequence[PendingMutationRow],
    canonical_global_mg: Metagraph,
    pending_global_mg: Metagraph,
    prior_failed_canonical_ids: Mapping[str, Iterable[str]] | None = None,
) -> AuditGateResult:
    """Run the release-ship audit gate (Phase 24 v1 narrow).

    Per ADR-0115 + ADR-0144 §am2 + Phase 24 design log PB-9 + PB-24 +
    PB-Z7 + PB-Z11 + PB-Z15 + PB-Z16.

    Side-effect-free: reads only; emits no audit rows; mutates no
    SQLite or in-memory Metagraph state. The only internal mutation
    is ``compute_similarity``'s process-local cache.

    Args:
        admin_session: Admin :class:`Session`. The gate does NOT do
            its own capability check (caller — release_update —
            already validated ``CAN_APPROVE_RELEASE`` per ADR-0002
            §am2). Passed for forensic logging only at v1.
        pending_mutations: Snapshot of the release_update's selected
            unshipped pending rows per PB-26(b). The gate operates on
            this set; doesn't re-query SQLite.
        canonical_global_mg: The canonical-Global :class:`Metagraph`
            (Phase 14 KL bootstrap output OR Phase 15a
            bootstrap_global output). Read-only.
        pending_global_mg: The pending-Global :class:`Metagraph` per
            PB-Z11(a). Read-only.
        prior_failed_canonical_ids: Suppression set per PB-Z7(a) +
            PB-Z15(a) — ``{role: [canonical_node_id, ...]}``. Cross-
            mg findings whose matched_id is in this set per role are
            filtered (suppressed). None or empty mapping at clean-
            system or non-rerun invocations.

    Returns:
        :class:`AuditGateResult` with ``passed`` flag + findings.

    Raises:
        EmptyComparisonError: ``compute_similarity`` raised per ADR-
            0144 §am2 for a degenerate pair. Propagated per PB-Z16(a);
            caller (release_update) catches at outer boundary and
            writes FAILED row with ``error_class="empty_comparison"``.
        BlockingFindingError: NOT raised by ``run`` itself per ADR-
            0115 §3 — passed=False signals blocking; caller decides
            whether to raise. (Kept this way for testability:
            ``run`` is pure read-only.)
    """
    # ── Step 1: ReleaseSummary (cheap; from snapshot set alone) ─────
    roles_affected = sorted({row.target_role for row in pending_mutations})
    proposer_ids = sorted({row.proposer_admin_user_id for row in pending_mutations})
    summary = ReleaseSummary(
        mutation_count=len(pending_mutations),
        roles_affected=tuple(roles_affected),
        proposer_admin_user_ids=tuple(proposer_ids),
    )

    # Short-circuit on empty snapshot — defensive; release_update
    # raises EmptyReleaseError before calling us, but if called with
    # empty input, return a passing all-zero result.
    if not pending_mutations:
        return AuditGateResult(passed=True, summary=summary)

    # ── Step 2: Group candidates by role for per-role two-pass ──────
    candidates_by_role: dict[str, list[CandidateRef]] = {}
    for row in pending_mutations:
        ref = CandidateRef(
            node_id=row.node_id,
            role=row.target_role,
            node_type=row.node_type,
            source_user_id=row.source_user_id,
        )
        candidates_by_role.setdefault(row.target_role, []).append(ref)

    # ── Step 3: Normalize suppression set per role ──────────────────
    suppression_by_role: dict[str, frozenset[str]] = {}
    if prior_failed_canonical_ids:
        for role, ids in prior_failed_canonical_ids.items():
            suppression_by_role[role] = frozenset(ids)

    # ── Step 4: Two-pass per role ───────────────────────────────────
    blocking: list[SimilarityWarning] = []
    review: list[SimilarityWarning] = []
    suppressed_total = 0

    for role, candidates in candidates_by_role.items():
        suppression = suppression_by_role.get(role, frozenset())

        # 4a. Intra-pending pass: catches duplicates within pending.
        # target_mg=None → compute_similarity uses pending_global_mg
        # as both source and target; candidate-vs-candidate findings
        # surface per Phase 16 PB-M2 (matched_is_candidate=True).
        try:
            intra_report = compute_similarity(
                mg=pending_global_mg,
                candidates=candidates,
                role=role,
                target_mg=None,
            )
        except EmptyComparisonError:
            # PB-Z16(a) — propagate to caller.
            raise

        for finding in intra_report.findings:
            warning = _to_warning(
                finding, source="intra_pending", role=role
            )
            if finding.classification == "blocking":
                blocking.append(warning)
            else:
                review.append(warning)

        # 4b. Cross-mg pass: catches pending-vs-canonical collisions.
        # Applies suppression set per PB-Z7(a) — drop findings whose
        # matched_id is in the prior-FAILED canonical-id list.
        try:
            cross_report = compute_similarity(
                mg=pending_global_mg,
                candidates=candidates,
                role=role,
                target_mg=canonical_global_mg,
            )
        except EmptyComparisonError:
            raise

        for finding in cross_report.findings:
            if finding.matched_id in suppression:
                suppressed_total += 1
                continue
            warning = _to_warning(
                finding, source="cross_mg", role=role
            )
            if finding.classification == "blocking":
                blocking.append(warning)
            else:
                review.append(warning)

    # ── Step 5: Sort findings deterministically ─────────────────────
    blocking.sort(
        key=lambda w: (w.candidate_node_id, -w.score, w.matched_node_id, w.source)
    )
    review.sort(
        key=lambda w: (w.candidate_node_id, -w.score, w.matched_node_id, w.source)
    )

    return AuditGateResult(
        passed=(len(blocking) == 0),
        summary=summary,
        blocking_findings=tuple(blocking),
        review_findings=tuple(review),
        suppressed_count=suppressed_total,
    )


# ─── §6 Helpers ─────────────────────────────────────────────────────────


def _to_warning(
    finding: Finding,
    *,
    source: Literal["intra_pending", "cross_mg"],
    role: str,
) -> SimilarityWarning:
    """Convert a Phase 16 :class:`Finding` to a :class:`SimilarityWarning`.

    The ``source`` discriminator + ``role`` come from the caller
    (which knows which pass generated this finding).
    ``matched_is_candidate`` is preserved as-is from Finding (only
    meaningful for intra_pending source; cross_mg always has it
    False since target_mg is canonical, not pending).
    """
    return SimilarityWarning(
        candidate_node_id=finding.candidate_id,
        matched_node_id=finding.matched_id,
        score=finding.score,
        classification=finding.classification,
        source=source,
        matched_is_candidate=finding.matched_is_candidate,
        role=role,
    )
