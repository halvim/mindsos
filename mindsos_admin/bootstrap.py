"""Admin bootstrap helper for the importer-built Global flow.

Per Phase 15a PB-13 (Round 3): ``bootstrap_global`` is the
module-level orchestrator for the importer flow. Caller pattern:

.. code-block:: python

    from mindsos_admin import bootstrap_global, DolceImporter, OewnImporter, FrameNetImporter
    from mindsos_knowledge import KnowledgeLayer

    mg = bootstrap_global(importers=[
        DolceImporter("data/datasets/dolce-dul-4.1.owl"),
        OewnImporter("data/datasets/oewn-2024.xml"),
        FrameNetImporter("data/datasets/framenet-1.7/"),
    ])
    kl = KnowledgeLayer(global_metagraph=mg)

Per ADR-0042 §amendment-2 (Phase 15a): this is the third documented
first-install sequence (after server warm-restart and
``KnowledgeLayer.bootstrap()``). The resulting Metagraph has all 6
Global named role-graphs ensured (Phase 15a PB-21 parity with
``KnowledgeLayer.bootstrap()``'s output); 3 of them are populated by
importer content, the other 3 (``promoted-pipelines``,
``task-patterns``, ``problem-trace``) ship empty pending downstream
phases (Phase 16/24/28-31/33-35 populate them).

Per Phase 15a PB-22: importers self-describe via ``target_roles``
class/instance attribute. ``bootstrap_global`` ensures each importer's
``target_roles`` ahead of running, so importers' internal
auto-ensure (Phase 15a PB-14) becomes redundant-but-idempotent
insurance against direct callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol, Sequence, Union, runtime_checkable

from mindsos_core import Metagraph
from mindsos_core.models.identity import IdStrategy, UUID4Strategy

from mindsos_knowledge.bootstrap import (
    _GLOBAL_NAMED_ROLES,
    ensure_global_role_graph,
)


__all__ = [
    "ImportResult",
    "ImporterProtocol",
    "bootstrap_global",
    "bootstrap_pending_global",
    "PENDING_GLOBAL_METAGRAPH_NAME",
]


#: Canonical name of the pending-Global Metagraph (Phase 24, ADR-0118
#: + PB-15(a) + Z11(a)). Parallel to ``bootstrap_global``'s default
#: ``"global_knowledge"``; the ``"pending_"`` prefix distinguishes the
#: pending buffer from the shipped canonical at FalkorDB metagraph-id
#: scope.
PENDING_GLOBAL_METAGRAPH_NAME: str = "pending_global_knowledge"


# ── §1 ImportResult ────────────────────────────────────────────────────


@dataclass(frozen=True)
class ImportResult:
    """Frozen summary returned by every importer's ``run()``.

    Attributes:
        role: The role-graph the importer wrote into (e.g. ``"ontology"``).
            For multi-role importers (Phase 15b ``AlignmentsImporter``)
            this is the *primary* role; per-pair detail lives in
            ``stats``.
        version: The pinned dataset version (e.g. ``"4.1"`` for DOLCE-
            DUL, ``"2024"`` for OEWN, ``"1.7"`` for FrameNet).
        source: The importer's ``source_name`` constant (e.g.
            ``"dolce-dul"``, ``"oewn"``, ``"framenet"``, ``"alignments"``).
        imported_at: UTC timestamp at the moment ``run()`` returned.
        stats: Per-importer count dict. Keys are documented per
            importer in its module docstring (e.g. DolceImporter:
            ``classes``, ``properties``, ``restrictions``,
            ``subclass_of_edges``, ``intersection_hyperedges``, ...).
    """

    role: str
    version: str
    source: str
    imported_at: datetime
    stats: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable shape for CLI ``--json`` output."""
        return {
            "role": self.role,
            "version": self.version,
            "source": self.source,
            "imported_at": self.imported_at.isoformat(),
            "stats": dict(self.stats),
        }


# ── §2 ImporterProtocol ────────────────────────────────────────────────


@runtime_checkable
class ImporterProtocol(Protocol):
    """Structural protocol every admin importer satisfies.

    Per Phase 15a PB-22 (Round 5): importers self-describe their
    target role-graphs via ``target_roles: tuple[str, ...]``. The
    attribute can be set at class level (single-role importers like
    DolceImporter / OewnImporter / FrameNetImporter) or instance
    level (parametric importers like Phase 15b's
    AlignmentsImporter).

    ``run(mg)`` does the actual write. **Single-shot contract**
    (Phase 15a B-15a-T3 calibration): ``run(mg)`` MUST be invoked
    against a Metagraph whose target role-graph(s) are empty.
    Re-running an importer against an already-populated role-graph
    raises :class:`IdentityError` on node IRI collision; for
    re-import use the **process-restart** pattern per ADR-0042
    §amendment-1 §Out-of-scope ("no Global-swap method; no
    consumer") — kill process, run ``bootstrap_global`` again, start
    new KL. Full mid-process idempotency (skip-existing-nodes +
    skip-existing-edges) is a carry-forward to Phase 15b or later;
    no admin-flow consumer requires it today.
    """

    target_roles: tuple[str, ...]

    def run(self, mg: Metagraph) -> ImportResult:  # pragma: no cover
        """Parse the importer's source and write into the supplied
        Metagraph. Returns an :class:`ImportResult` summary."""
        ...


# ── §3 bootstrap_global ────────────────────────────────────────────────


# Ordering of the 9 Global named roles (Phase 14 PB-9 baseline 6 +
# Phase 43 ADR-0150 §amendment-5 additions). Order matches the
# ``KnowledgeLayer.bootstrap()`` walk order for deterministic Metagraph
# state. The 3 importer-driven roles come first; the 3 Phase-13
# downstream-populated roles next; the 3 Phase-43 Global-form
# role-graphs (per ADR-0150 §am-5) last.
_GLOBAL_ROLE_ORDER: tuple[str, ...] = (
    "ontology",
    "lexicon",
    "concepts",
    "promoted-pipelines",
    "task-patterns",
    "problem-trace",
    # Phase 43 (ADR-0150 §am-5) Global-form additions.
    "pending-promotions",
    "capacity-gaps",
    "learned-parameters",
    # Phase 50 (ADR-0150 §am-6) — skill-install state; Global-only.
    "installed-skills",
)
# Sanity: matches mindsos_knowledge.bootstrap's frozenset content.
assert frozenset(_GLOBAL_ROLE_ORDER) == _GLOBAL_NAMED_ROLES, (
    "Phase 15a bootstrap_global _GLOBAL_ROLE_ORDER drifted from "
    "mindsos_knowledge.bootstrap._GLOBAL_NAMED_ROLES — Phase 14 "
    "PB-21 parity contract violated."
)


def bootstrap_global(
    importers: Sequence[ImporterProtocol] = (),
    *,
    name: str = "global_knowledge",
    id_strategy: Optional[IdStrategy] = None,
) -> Metagraph:
    """Build a populated Global :class:`Metagraph` for the importer flow.

    Per Phase 15a PB-21 (Round 5): the returned Metagraph has all 6
    Global named role-graphs ensured (``ontology``, ``lexicon``,
    ``concepts``, ``promoted-pipelines``, ``task-patterns``,
    ``problem-trace``) — end-state parity with
    :meth:`mindsos_knowledge.KnowledgeLayer.bootstrap`'s output. The
    3 importer-driven roles (``ontology``/``lexicon``/``concepts``)
    are populated when DolceImporter/OewnImporter/FrameNetImporter
    are passed; the other 3 ship empty.

    Per Phase 15a PB-22: each importer's ``target_roles`` is also
    ensured (covers Phase 15b's parametric ``alignment:<a>:<b>``
    pairs); the importer's internal auto-ensure (Phase 15a PB-14)
    becomes redundant-but-idempotent.

    Per Phase 15a PB-7 (Round 2): the caller hands the returned
    Metagraph to ``KnowledgeLayer(global_metagraph=mg)`` per ADR-0042
    §amendment-2. KL is never touched by the importer flow.

    Args:
        importers: Sequence of importer instances (must satisfy
            :class:`ImporterProtocol`). Executed in order. Empty
            sequence is permitted — returns a Metagraph with all 6
            named role-graphs ensured but no content (equivalent to
            ``KnowledgeLayer.bootstrap().global_view()`` shape).
        name: Metagraph name. Default ``"global_knowledge"`` matches
            Phase 14's ``KnowledgeLayer.bootstrap()`` default
            (preserves install-flow parity).
        id_strategy: Optional :class:`IdStrategy`. Default
            :class:`UUID4Strategy`. Forwarded to the constructed
            :class:`Metagraph`.

    Returns:
        A :class:`Metagraph` ready to hand to
        :class:`mindsos_knowledge.KnowledgeLayer`'s
        ``global_metagraph=`` constructor parameter.

    Raises:
        Any exception an importer raises during ``run()``. ``bootstrap_global``
        does not catch — caller decides whether to retry / abort.
    """
    mg = Metagraph(name=name, id_strategy=id_strategy or UUID4Strategy())

    # PB-21 — ensure all 6 Global named role-graphs first.
    for role in _GLOBAL_ROLE_ORDER:
        ensure_global_role_graph(mg, role)

    # PB-22 — ensure each importer's target_roles (covers Phase 15b's
    # parametric alignment:<a>:<b> pairs).
    for importer in importers:
        for role in importer.target_roles:
            # ensure_global_role_graph is idempotent — re-ensuring an
            # already-present role-graph (e.g. ontology when
            # DolceImporter.target_roles=("ontology",)) returns the
            # existing graph unchanged.
            ensure_global_role_graph(mg, role)

    # Run importers in declared order.
    for importer in importers:
        importer.run(mg)

    return mg


# ── §4 Helper: source-path resolution ──────────────────────────────────


def _resolve_source(source: Union[str, Path, None], *, required: bool = True) -> Optional[Path]:
    """Normalise a source argument to a :class:`Path`.

    Importers accept ``str``, :class:`Path`, or ``None`` (use
    constructor-supplied source). Returns ``None`` if ``source`` is
    ``None`` and ``required=False``; raises :class:`ValueError`
    otherwise.
    """
    if source is None:
        if required:
            raise ValueError(
                "source must be supplied to constructor or run() — "
                "no constructor-default and no per-call value given"
            )
        return None
    return Path(source)


def _utcnow() -> datetime:
    """Convenience: timezone-aware UTC now."""
    return datetime.now(timezone.utc)


# ── §5 bootstrap_pending_global (Phase 24, ADR-0118 + PB-15(a) + Z11(a))


def bootstrap_pending_global(
    canonical_mg: Metagraph,
    *,
    id_strategy: Optional[IdStrategy] = None,
) -> Metagraph:
    """Build the parallel pending-Global :class:`Metagraph`.

    Per Phase 24 design log PB-15(a) (eager pending-Global bootstrap)
    + PB-Z11(a) (single pending_global Metagraph parallel to
    canonical) + PB-Z12(b) (reuse ``ensure_global_role_graph`` with
    pending Metagraph arg).

    The pending Metagraph mirrors the canonical's role-graph topology
    (same role-set; same schemas via Phase 13 ``schema_for_role``).
    Per ADR-0118 §"Decision" §1 + ADR-0114 §1, pending serves as the
    admin-curation buffer that ``propose_for_promotion`` writes into
    and ``release_update`` copies into canonical (per-role MERGE-on-
    node_id per Z9(a)).

    Per Z12(b), the existing :func:`mindsos_knowledge.bootstrap.
    ensure_global_role_graph` helper is reused with the pending
    Metagraph as the ``metagraph`` arg — no new helper needed,
    schemas + role-validation logic shared with canonical.

    Per PB-15(a), this function is called **eagerly at install time**
    alongside ``bootstrap_global`` (admin workflow:
    ``canonical_mg = bootstrap_global(...); pending_mg =
    bootstrap_pending_global(canonical_mg)``); deferring to first-
    propose creates a first-write race + adds test coverage burden.

    The pending Metagraph mirrors canonical's role-set but starts
    EMPTY (no propose has fired yet); per PB-15(a) "10 empty graphs
    is negligible."

    Args:
        canonical_mg: The canonical Global Metagraph built by
            :func:`bootstrap_global`. Used to determine the role-set
            to mirror — pending's roles = canonical's roles.
        id_strategy: Optional :class:`IdStrategy`. Default
            :class:`UUID4Strategy`. Independent from canonical's id
            strategy (pending node_ids are minted fresh per propose;
            preserved through MERGE-on-id into canonical per Z9(a)).

    Returns:
        A :class:`Metagraph` named :data:`PENDING_GLOBAL_METAGRAPH_NAME`
        with the same role-graphs as ``canonical_mg``, all empty.

    Raises:
        KnowledgeError: A canonical role isn't supported by
            ``ensure_global_role_graph`` (impossible if canonical was
            built via :func:`bootstrap_global`).
    """
    pending_mg = Metagraph(
        name=PENDING_GLOBAL_METAGRAPH_NAME,
        id_strategy=id_strategy or UUID4Strategy(),
    )

    # Mirror canonical's role-graphs. Phase 14 `ensure_global_role_
    # graph` is idempotent + schema-validating; we re-use the helper
    # per Z12(b).
    for graph in canonical_mg.graphs.values():
        ensure_global_role_graph(pending_mg, graph.role)

    return pending_mg
