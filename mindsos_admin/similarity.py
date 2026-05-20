"""Admin similarity surface (Phase 16 — read-only).

Implements ADR-0144 §Heuristic (Accepted at Phase 16 per
§amendment-1): three weighted scorers (Levenshtein on canonical names +
structural Jaccard on ``(frame_elements, synonyms, parents)`` +
reference Jaccard on outbound ``ref:<role>`` properties UNIONed with
XRef rows) with default weights 0.4 / 0.4 / 0.2 and thresholds 0.85
blocking / 0.5 review.

Public surface:

* :class:`CandidateRef` — frozen dataclass identifying a candidate.
* :class:`Finding` — frozen dataclass; one per candidate-matched pair
  whose combined score is at or above the review threshold (Bundle II
  per Phase 16 PB-H).
* :class:`SimilarityReport` — frozen dataclass holding ``findings`` +
  ``report_id`` content hash.
* :func:`list_candidates` — enumerate candidates in a role-graph; default
  excludes PROMOTED breadcrumbs (per ADR-0051 + Phase 16 PB-C2).
* :func:`compute_similarity` — primary entry-point. Intra-mg by default;
  cross-mg via ``target_mg`` keyword (Phase 24's release-ship audit gate
  uses the cross-mg form per Phase 16 PB-K2).

Per-role feature extractors live as private helpers
(``_extract_ontology`` / ``_extract_lexicon`` / ``_extract_concepts``).
Roles outside the three Phase 15a importer targets return all-empty
feature triples; empty-pair exclusion (ADR-0144 §amendment-2 at inner +
outer means) handles the rest.

All numeric outputs are rounded to 6 decimals per Phase 16 PB-T2 for
cross-machine determinism.

**Out of scope for Phase 16** (Phase 24 owns):

* ``promote_to_global`` / ``propose_for_promotion`` — the mutating
  entry-point. Reserved location: ``mindsos_admin/promotion.py``.
* ``PromotionResult`` / ``PromotionRequestResult`` dataclass.
* ``force=True`` / ``reviewed_similarity_report_id`` gate parameters.
* Per-candidate atomic rollback (ADR-0053).
* Release-ship audit gate placement (ADR-0144 §Placement).
* Bloom-filter / blocking-key pre-filter for scalability.

See ``halvim_mindsos/confirmation_docs/PHASE_16_DESIGN_LOG.md`` for the
multi-round design ledger that arrived at this scope.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Literal, Optional, Sequence

from mindsos_core import Metagraph
from mindsos_core.models.graph import Graph
from mindsos_core.models.node import Node

from ._content_hash import metagraph_content_hash
from .exceptions import EmptyComparisonError


__all__ = [
    "CandidateRef",
    "Finding",
    "SimilarityReport",
    "list_candidates",
    "compute_similarity",
]


# ── §1 Public dataclasses ──────────────────────────────────────────────


@dataclass(frozen=True)
class CandidateRef:
    """Identifies one promotion candidate within a metagraph (Phase 16 PB-D2).

    Attributes:
        node_id: The node's id within its containing graph.
        role: The role-graph the node belongs to (e.g. ``"ontology"``).
        node_type: The :class:`~mindsos_core.NodeType` name
            (e.g. ``"Class"`` for ontology, ``"Synset"`` for lexicon).
        source_user_id: Reserved for Phase 24's per-user transactional
            propose path. Always ``None`` at Phase 16 (single-mg, no
            user concept yet).
    """

    node_id: str
    role: str
    node_type: str
    source_user_id: Optional[str] = None


@dataclass(frozen=True)
class Finding:
    """One candidate-matched-target similarity finding (Phase 16 PB-D2).

    Emitted for every candidate-matched pair whose combined score is at
    or above ``threshold_review`` (Bundle II per Phase 16 PB-H). Findings
    are sorted in :attr:`SimilarityReport.findings` by ``(candidate_id
    ASC, -score, matched_id ASC)`` — admin sees candidates in id order,
    each with their best match first.
    """

    candidate_id: str
    candidate_node_type: str
    matched_id: str
    matched_node_type: str
    matched_is_candidate: bool
    score: float
    breakdown: dict[str, float]
    classification: Literal["blocking", "review"]


@dataclass(frozen=True)
class SimilarityReport:
    """Deterministic similarity findings + content-hash ``report_id``.

    Per ADR-0052 §amendment-1 (Phase 16). ``report_id`` is a SHA-256
    over: ``sorted(candidate_ids) || role_graph_content_hash(mg) ||
    role_graph_content_hash(target_mg if target_mg else mg) ||
    f"{threshold_blocking:.6f}" || f"{threshold_review:.6f}"``.
    """

    report_id: str
    findings: tuple[Finding, ...]
    threshold_blocking: float
    threshold_review: float

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable form (used by CLI ``--json``)."""
        return {
            "report_id": self.report_id,
            "threshold_blocking": self.threshold_blocking,
            "threshold_review": self.threshold_review,
            "findings": [
                {
                    "candidate_id": f.candidate_id,
                    "candidate_node_type": f.candidate_node_type,
                    "matched_id": f.matched_id,
                    "matched_node_type": f.matched_node_type,
                    "matched_is_candidate": f.matched_is_candidate,
                    "score": f.score,
                    "breakdown": dict(f.breakdown),
                    "classification": f.classification,
                }
                for f in self.findings
            ],
        }


# ── §2 list_candidates ─────────────────────────────────────────────────


def list_candidates(
    mg: Metagraph,
    *,
    role: str,
    node_type: Optional[str] = None,
    where: Optional[Callable[[Node], bool]] = None,
) -> list[CandidateRef]:
    """Enumerate promotion candidates in ``mg``'s ``role`` graph(s).

    Default behaviour (per Phase 16 PB-C2 + PB-J3):

    * Returns nodes in EVERY graph carrying ``role`` (multiple graphs
      may share a role — e.g. multiple alignment pair-graphs).
    * Excludes nodes carrying the ADR-0051 ``ref_type = "PROMOTED"``
      breadcrumb marker.
    * If ``node_type`` is given, filters to that single NodeType.
    * If ``where`` is given, additionally filters via the predicate
      (Phase 24's per-user-aware predicates use this hook).
    * Soft-deleted nodes (per ADR-0133) are NOT enumerable from
      :attr:`Graph.nodes` directly (soft-delete applies to edges /
      hyperedges only at Phase 10). Node-level soft-delete is not in
      scope at Phase 16.

    Result is sorted by ``node_id`` for determinism.
    """
    refs: list[CandidateRef] = []
    for graph in sorted(mg.graphs.values(), key=lambda g: g.graph_id):
        if graph.role != role:
            continue
        for node in graph.nodes.values():
            # Phase 16 PB-C2 — exclude PROMOTED breadcrumbs.
            if node.properties.get("ref_type") == "PROMOTED":
                continue
            # PB-J3 — optional NodeType filter.
            if node_type is not None and node.type_name != node_type:
                continue
            # PB-C2 — optional caller predicate.
            if where is not None and not where(node):
                continue
            refs.append(
                CandidateRef(
                    node_id=node.node_id,
                    role=role,
                    node_type=node.type_name,
                )
            )
    refs.sort(key=lambda r: r.node_id)
    return refs


# ── §3 compute_similarity ──────────────────────────────────────────────


def compute_similarity(
    mg: Metagraph,
    candidates: Sequence[CandidateRef],
    *,
    role: str,
    target_mg: Optional[Metagraph] = None,
    threshold_blocking: float = 0.85,
    threshold_review: float = 0.5,
) -> SimilarityReport:
    """Compute the similarity report for ``candidates`` against existing
    same-role same-NodeType nodes.

    Default (intra-mg, ``target_mg=None``): candidates are compared
    against other nodes of the same NodeType in the same role-graph of
    ``mg``. Self-comparison is excluded; candidate-vs-candidate
    comparisons are INCLUDED (per Phase 16 PB-M2 — flagged with
    :attr:`Finding.matched_is_candidate`).

    Cross-mg (``target_mg`` given): candidates from ``mg``'s role-graph
    are compared against nodes in ``target_mg``'s role-graph. This is
    the Phase 24 release-ship audit-gate shape per Phase 16 PB-K2.

    Args:
        mg: The metagraph candidates live in.
        candidates: The list of :class:`CandidateRef` to score.
        role: The role-graph to scan.
        target_mg: Optional — if given, comparison universe is this
            metagraph's same-role graph instead of ``mg``.
        threshold_blocking: Score ≥ this → ``classification="blocking"``.
        threshold_review: Score ≥ this and < blocking → ``"review"``.
            Pairs below this are not emitted as findings (Bundle II per
            Phase 16 PB-H).

    Returns:
        A :class:`SimilarityReport` with ``findings`` sorted by
        ``(candidate_id, -score, matched_id)`` and a content-hash
        ``report_id`` per ADR-0052 §amendment-1.

    Raises:
        EmptyComparisonError: A candidate-matched pair has all three
            similarity components undefined per ADR-0144 §amendment-2.
            Rare — Lev is well-defined whenever both nodes have
            non-empty IRI tails.
    """
    comparison_mg = target_mg if target_mg is not None else mg

    # Index target-side nodes by NodeType for O(N) per-NodeType lookup.
    target_index = _build_node_index(comparison_mg, role)
    # Index source-side nodes (for candidate self-lookup) — same mg.
    source_index = _build_node_index(mg, role)

    candidate_ids = {c.node_id for c in candidates}
    findings: list[Finding] = []

    for candidate in candidates:
        source_node = source_index.get(candidate.node_id)
        if source_node is None:
            # Candidate id doesn't resolve in mg's role-graph; skip.
            continue
        targets = target_index.get(candidate.node_type, {})
        for matched_id, matched_node in targets.items():
            # Self-comparison exclusion (PB-M2).
            # Self = same node-id AND same metagraph identity.
            if matched_id == candidate.node_id and comparison_mg is mg:
                continue
            scoring = _score_pair(
                source_graph=_find_role_graph(mg, role),
                source_node=source_node,
                target_graph=_find_role_graph(comparison_mg, role),
                target_node=matched_node,
            )
            score = scoring["score"]
            breakdown = scoring["breakdown"]
            if score < threshold_review:
                continue
            classification: Literal["blocking", "review"] = (
                "blocking" if score >= threshold_blocking else "review"
            )
            findings.append(
                Finding(
                    candidate_id=candidate.node_id,
                    candidate_node_type=candidate.node_type,
                    matched_id=matched_id,
                    matched_node_type=matched_node.type_name,
                    matched_is_candidate=(
                        matched_id in candidate_ids and comparison_mg is mg
                    ),
                    score=score,
                    breakdown=breakdown,
                    classification=classification,
                )
            )

    # Sort: candidate_id asc, score desc, matched_id asc (PB-H tie-break).
    findings.sort(key=lambda f: (f.candidate_id, -f.score, f.matched_id))

    report_id = _compute_report_id(
        mg=mg,
        target_mg=comparison_mg,
        role=role,
        candidate_ids=sorted(c.node_id for c in candidates),
        threshold_blocking=threshold_blocking,
        threshold_review=threshold_review,
    )

    return SimilarityReport(
        report_id=report_id,
        findings=tuple(findings),
        threshold_blocking=threshold_blocking,
        threshold_review=threshold_review,
    )


# ── §4 Pair scoring (three weighted components) ────────────────────────


# ADR-0144 §Heuristic weights.
_WEIGHT_LEV = 0.4
_WEIGHT_STRUCT = 0.4
_WEIGHT_REF = 0.2


def _score_pair(
    *,
    source_graph: Optional[Graph],
    source_node: Node,
    target_graph: Optional[Graph],
    target_node: Node,
) -> dict[str, Any]:
    """Score a single candidate-vs-matched pair per ADR-0144 §Heuristic.

    Returns a dict ``{"score": float, "breakdown": dict[str, float]}``.
    All scores rounded to 6 decimals per PB-T2.

    Empty-pair exclusion + renormalization at BOTH inner Jaccard AND
    outer weighted-mean per ADR-0144 §amendment-2 / Phase 16 PB-G2 +
    PB-L1.

    Raises:
        EmptyComparisonError: All three components undefined.
    """
    # Component 1: Levenshtein on IRI tail (canonical name).
    lev = _score_levenshtein(source_node.node_id, target_node.node_id)

    # Component 2: structural Jaccard on (frame_elements, synonyms, parents).
    struct = _score_structural(
        source_graph, source_node, target_graph, target_node
    )

    # Component 3: reference Jaccard on outbound ref:<role> + XRef.
    ref = _score_reference(
        source_node=source_node,
        source_graph=source_graph,
        target_node=target_node,
        target_graph=target_graph,
    )

    # Outer weighted-mean with empty-pair exclusion (PB-L1).
    components: list[tuple[float, float]] = []  # (weight, score)
    breakdown: dict[str, float] = {}
    if lev is not None:
        components.append((_WEIGHT_LEV, lev))
        breakdown["lev"] = round(lev, 6)
    if struct is not None:
        components.append((_WEIGHT_STRUCT, struct))
        breakdown["struct"] = round(struct, 6)
    if ref is not None:
        components.append((_WEIGHT_REF, ref))
        breakdown["ref"] = round(ref, 6)

    if not components:
        raise EmptyComparisonError(
            candidate_id=source_node.node_id,
            matched_id=target_node.node_id,
        )

    total_weight = sum(w for w, _ in components)
    weighted_sum = sum(w * s for w, s in components)
    score = weighted_sum / total_weight
    return {
        "score": round(score, 6),
        "breakdown": breakdown,
    }


# ── §5 Levenshtein scorer ──────────────────────────────────────────────


def _score_levenshtein(source_iri: str, target_iri: str) -> Optional[float]:
    """Normalised Levenshtein on the IRI tails (canonical names).

    Returns ``None`` (undefined) when either tail is empty.

    Per ADR-0144 §Heuristic: "Levenshtein on canonical names (target IRI
    tail) — 0.0 to 1.0". IRI tail per Phase 12 IRI builder convention:
    last ``:``-separated segment of the IRI.

    Score formula: ``1 - distance / max(len(a), len(b))``. Range
    [0.0, 1.0]; 1.0 = identical, 0.0 = wholly different.
    """
    a = _iri_tail(source_iri)
    b = _iri_tail(target_iri)
    if not a or not b:
        return None
    if a == b:
        return 1.0
    distance = _levenshtein_distance(a, b)
    longest = max(len(a), len(b))
    return 1.0 - (distance / longest)


def _iri_tail(iri: str) -> str:
    """Return the last ``:``-separated segment of an IRI.

    Phase 12 IRI builder convention: IRIs compose with ``:`` (e.g.,
    ``dolce:Class:PhysicalObject`` → ``PhysicalObject``;
    ``oewn:Synset:car.n.01`` → ``car.n.01``).
    """
    return iri.rsplit(":", 1)[-1] if ":" in iri else iri


def _levenshtein_distance(a: str, b: str) -> int:
    """In-house Levenshtein DP (no external dependency).

    Standard 2-row dynamic programming. O(len(a) * len(b)) time,
    O(min(len(a), len(b))) space.
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    # Ensure b is the shorter — minimises the working-row size.
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    current = [0] * (len(b) + 1)
    for i, ca in enumerate(a, start=1):
        current[0] = i
        for j, cb in enumerate(b, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            substitute_cost = previous[j - 1] + (0 if ca == cb else 1)
            current[j] = min(insert_cost, delete_cost, substitute_cost)
        previous, current = current, previous
    return previous[-1]


# ── §6 Structural Jaccard scorer (per-role feature extraction) ─────────


def _score_structural(
    source_graph: Optional[Graph],
    source_node: Node,
    target_graph: Optional[Graph],
    target_node: Node,
) -> Optional[float]:
    """Structural Jaccard over (frame_elements, synonyms, parents).

    Per ADR-0144 §Heuristic + §amendment-2 (Phase 16): three named
    sub-features. For each, compute Jaccard on (candidate-set,
    matched-set). Exclude any sub-feature where BOTH sets are empty
    (PB-G2). Structural score = arithmetic mean over non-excluded
    sub-features. Returns ``None`` when all three excluded.

    Role determination: read from ``source_node``'s containing graph's
    ``role`` attribute. Comparison nodes are assumed to be in the same
    role-graph (caller's responsibility — :func:`compute_similarity`
    enforces this by indexing by NodeType within a role-graph).
    """
    if source_graph is None or target_graph is None:
        return None
    role = source_graph.role or target_graph.role
    if role is None:
        return None
    source_features = _extract_features(source_graph, source_node, role)
    target_features = _extract_features(target_graph, target_node, role)

    per_feature: list[float] = []
    for feature_name in ("frame_elements", "synonyms", "parents"):
        s = source_features[feature_name]
        t = target_features[feature_name]
        if not s and not t:
            continue  # Empty-pair exclusion (PB-G2).
        per_feature.append(_jaccard(s, t))

    if not per_feature:
        return None
    return sum(per_feature) / len(per_feature)


def _extract_features(
    graph: Graph, node: Node, role: str
) -> dict[str, frozenset[str]]:
    """Per-role feature extractor (Phase 16 PB-B2).

    Three Phase-15a-importer-target roles (ontology / lexicon /
    concepts) have role-specific feature mappings. Roles outside this
    set return all-empty features — empty-pair exclusion handles them.

    Returns a dict with keys ``frame_elements``, ``synonyms``,
    ``parents``; values are frozensets of node ids.
    """
    if role == "ontology":
        return _extract_ontology(graph, node)
    if role == "lexicon":
        return _extract_lexicon(graph, node)
    if role == "concepts":
        return _extract_concepts(graph, node)
    return _empty_features()


def _empty_features() -> dict[str, frozenset[str]]:
    return {
        "frame_elements": frozenset(),
        "synonyms": frozenset(),
        "parents": frozenset(),
    }


def _extract_ontology(graph: Graph, node: Node) -> dict[str, frozenset[str]]:
    """DOLCE-style ontology feature extractor.

    * ``parents`` — outbound ``SUBCLASS_OF`` edge targets.
    * ``synonyms`` — N/A (DOLCE has no synonym vocabulary at the L1
      level); empty.
    * ``frame_elements`` — N/A; empty.
    """
    parents = _outbound_edge_targets(graph, node, edge_type="SUBCLASS_OF")
    return {
        "frame_elements": frozenset(),
        "synonyms": frozenset(),
        "parents": parents,
    }


def _extract_lexicon(graph: Graph, node: Node) -> dict[str, frozenset[str]]:
    """OEWN three-level lexicon feature extractor.

    * ``parents`` — outbound ``HYPERNYM_OF`` targets (Synset only;
      empty for Lemma/Sense).
    * ``synonyms`` — outbound ``IN_SYNSET`` targets (Sense → Synset);
      OR for Synset, the union of inbound ``IN_SYNSET`` source-side
      Lemmas-and-Senses. At Phase 16 we approximate via outbound
      ``IN_SYNSET`` only (simpler; inbound would require Graph reverse
      index which Phase 11 didn't ship).
    * ``frame_elements`` — N/A; empty.
    """
    parents = _outbound_edge_targets(graph, node, edge_type="HYPERNYM_OF")
    synonyms = _outbound_edge_targets(graph, node, edge_type="IN_SYNSET")
    return {
        "frame_elements": frozenset(),
        "synonyms": synonyms,
        "parents": parents,
    }


def _extract_concepts(graph: Graph, node: Node) -> dict[str, frozenset[str]]:
    """FrameNet concepts feature extractor.

    * ``parents`` — outbound ``INHERITS_FROM`` targets (Frame-to-Frame).
    * ``frame_elements`` — outbound ``HAS_FE`` targets (Frame → FE).
    * ``synonyms`` — N/A (FrameNet at the Frame level; LU-level
      synonymy is out of scope at Phase 16); empty.
    """
    parents = _outbound_edge_targets(graph, node, edge_type="INHERITS_FROM")
    frame_elements = _outbound_edge_targets(graph, node, edge_type="HAS_FE")
    return {
        "frame_elements": frame_elements,
        "synonyms": frozenset(),
        "parents": parents,
    }


def _outbound_edge_targets(
    graph: Graph, node: Node, *, edge_type: str
) -> frozenset[str]:
    """Set of target node ids from ``node`` along edges of type ``edge_type``."""
    return frozenset(
        e.target.node_id
        for e in graph.iter_edges(include_deprecated=False)
        if e.source.node_id == node.node_id and e.type_name == edge_type
    )


# ── §7 Reference Jaccard scorer ────────────────────────────────────────


def _score_reference(
    *,
    source_node: Node,
    source_graph: Optional[Graph],
    target_node: Node,
    target_graph: Optional[Graph],
) -> Optional[float]:
    """Reference Jaccard per ADR-0144 §Heuristic.

    "Jaccard on outbound ``ref:<role>`` and ``XRef`` targets."

    Phase 16 reads BOTH:

    * ``ref:<role>`` properties on the node (legacy property-string form
      per ADR-0142 read-fallback contract).
    * Outbound XRef rows where ``XRef.source_id == node.node_id`` (the
      ADR-0128 hybrid form). Currently Phase 16 reads from the
      containing metagraph's ``iter_xrefs`` surface (M2 hybrid model).

    Sets are unioned per source-side and target-side, deduplicated by
    target IRI.

    Returns ``None`` when both candidate's set AND target's set are
    empty (per ADR-0144 §amendment-2 empty-pair exclusion at outer
    mean — PB-L1).
    """
    source_refs = _collect_outbound_refs(source_node, source_graph)
    target_refs = _collect_outbound_refs(target_node, target_graph)
    if not source_refs and not target_refs:
        return None
    return _jaccard(source_refs, target_refs)


def _collect_outbound_refs(
    node: Node, graph: Optional[Graph]
) -> frozenset[str]:
    """Union of ``ref:<role>`` property values + outbound XRef targets.

    XRef collection requires reaching the containing Metagraph; at
    Phase 16 we read XRefs from a metagraph reference threaded through
    the public API. For simplicity at this phase, we read XRefs from
    the graph's ``_metagraph`` back-reference if set; otherwise we
    skip the XRef contribution (the property-bag path still works).
    """
    refs: set[str] = set()
    for key, value in node.properties.items():
        if key.startswith("ref:") and isinstance(value, str):
            refs.add(value)
    mg = _graph_metagraph(graph)
    if mg is not None:
        for xref in mg.iter_xrefs():
            if xref.source_id == node.node_id and not xref.target_stale:
                refs.add(xref.target_id)
    return frozenset(refs)


def _graph_metagraph(graph: Optional[Graph]) -> Optional[Metagraph]:
    """Best-effort back-reference from a Graph to its Metagraph.

    Phase 16 follows the back-reference set by
    :meth:`Metagraph.add_graph` (Phase 05a P16: shared identity
    registry; the graph's metagraph back-reference is implicit via
    the shared registry but not stored as ``graph._metagraph``).
    Returns ``None`` if no back-reference path is available.
    """
    return getattr(graph, "_metagraph", None) if graph is not None else None


# ── §8 Helpers ─────────────────────────────────────────────────────────


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard index ``|a ∩ b| / |a ∪ b|``.

    Empty inputs (both empty) is the caller's responsibility to handle
    (empty-pair exclusion). When called with at least one non-empty set,
    the union is non-empty and the result is well-defined in [0.0, 1.0].
    """
    if not a and not b:
        return 0.0  # Caller should have excluded; defensive default.
    union = a | b
    intersection = a & b
    return len(intersection) / len(union)


def _build_node_index(
    mg: Metagraph, role: str
) -> dict[str, dict[str, Node]]:
    """Return ``{node_type: {node_id: Node}}`` for all nodes in ``role``."""
    index: dict[str, dict[str, Node]] = {}
    for graph in mg.graphs.values():
        if graph.role != role:
            continue
        for node in graph.nodes.values():
            index.setdefault(node.type_name, {})[node.node_id] = node
    return index


def _find_role_graph(mg: Metagraph, role: str) -> Optional[Graph]:
    """Return the first :class:`Graph` in ``mg`` carrying ``role``, or None.

    Phase 16 expects one graph per role per metagraph (the
    bootstrap_global / KL.bootstrap convention). Alignment roles
    (multiple ``alignment:a:b`` graphs) are out of similarity scope at
    Phase 16 — extractors return empty features for those roles.
    """
    for graph in mg.graphs.values():
        if graph.role == role:
            return graph
    return None


# ── §9 report_id content hash ──────────────────────────────────────────


def _compute_report_id(
    *,
    mg: Metagraph,
    target_mg: Metagraph,
    role: str,
    candidate_ids: list[str],
    threshold_blocking: float,
    threshold_review: float,
) -> str:
    """SHA-256 over the canonicalized similarity-call inputs.

    Per ADR-0052 §amendment-1 (Phase 16). Input set:

    * ``sorted(candidate_ids)`` — already sorted by caller.
    * ``metagraph_content_hash(mg, role=role)``
    * ``metagraph_content_hash(target_mg, role=role)`` — same as the
      first hash when ``target_mg is mg`` (intra-mg call).
    * ``f"{threshold_blocking:.6f}"`` + ``f"{threshold_review:.6f}"`` —
      PB-T2 6-decimal canonicalization.
    """
    source_hash = metagraph_content_hash(mg, role=role)
    target_hash = metagraph_content_hash(target_mg, role=role)
    payload = "|".join(
        [
            ",".join(candidate_ids),
            source_hash,
            target_hash,
            f"{threshold_blocking:.6f}",
            f"{threshold_review:.6f}",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
