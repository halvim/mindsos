"""Soft-delete persistence wiring (Phase 10 — RR-16a + P72).

This module owns:

* :class:`SoftDeleteKind` enum — typed keys for
  :attr:`Metagraph._soft_delete_dirty` (P72; replaces the string-keyed
  shape locked at RPB-4 to eliminate typo class).
* :func:`register_soft_delete_replayers` (Step 13) — registers the 4
  collapsed edge-side WAL replayer kinds (``element_deprecate`` /
  ``element_undeprecate`` / ``element_dispute`` / ``element_undispute``)
  on the per-:class:`Client` replayer registry. Wrapper
  :func:`mindsos_core.persistence.bootstrap.register_all_l1_replayers`
  composes this with Phase 09's
  :func:`mindsos_core.persistence.xref_repository.register_xref_replayers`
  (extended Phase 10: 2 → 6 kinds).

Phase 10 design lock RR-16a NEW (Round-4 resolution): module-level
function only, no class. Mirrors Phase 09's
``register_xref_replayers`` shape.

Phase 10 M8 + RR-16: wrapper grows 2 → 10 WAL replayer kinds:

* Phase 09 carry: ``xref_add`` + ``xref_remove`` (2).
* Phase 10 collapsed edge-side: ``element_deprecate`` +
  ``element_undeprecate`` + ``element_dispute`` + ``element_undispute``
  (4) — payload ``{element_id, element_kind, at}``.
* Phase 10 XRef-specific: ``xref_mark_stale`` + ``xref_unmark_stale`` +
  ``xref_deprecate`` + ``xref_undeprecate`` (4) — payloads vary per RR-1.

Per RPB-1, replayer bodies bypass public setters and emit cypher via
the per-method builders (PB-4a). No ``DeprecatedFilterPendingWarning``
fires on replay (warning class was STRIPPED entirely per P74 — filter
ships in this same phase under the P68 merge).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional


def _resolve_at(at: Optional[datetime]) -> datetime:
    """Centralized timestamp resolver for soft-delete setters (PB-2).

    The 20 Phase 10 setter methods (8 Graph + 8 Metagraph + 4 XRef per
    M6 + PX2) accept ``at: datetime | None = None``. ``None`` resolves
    here to ``datetime.now(timezone.utc)`` — the timezone-aware
    modernization replacing v3 baseline's deprecated
    ``datetime.utcnow()`` (PB-2 lock).

    Centralization avoids the v3-baseline copy-paste pattern across 20
    setters and gives WAL replayer bodies a single place to read the
    "resolved at" semantic (RR-1 payload shape per kind).
    """
    return at if at is not None else datetime.now(timezone.utc)


class SoftDeleteKind(str, Enum):
    """Typed element-kind keys for :attr:`Metagraph._soft_delete_dirty`.

    Replaces the string-literal shape locked at Phase 10 design RPB-4
    (``Dict[str, Set[str]]`` with bare-string keys). Phase 10 P72
    override (Round-2 batch sign-off 2026-05-15): Enum prevents typo
    silently dropping a drain bucket (e.g. ``"hyper_edge"`` vs
    ``"hyperedge"``) at persist time.

    Five kinds parallel the soft-delete-bearing element types:

    * :attr:`EDGE` — ``Graph.edges[edge_id]`` mutations.
    * :attr:`HYPEREDGE` — ``Graph.hyperedges[edge_id]`` mutations.
    * :attr:`METAEDGE` — ``Metagraph.metaedges[edge_id]`` mutations.
    * :attr:`METAHYPEREDGE` — ``Metagraph.metahyperedges[edge_id]`` mutations.
    * :attr:`XREF` — ``Metagraph.xrefs[xref_id]`` setter-driven mutations
      (XRef quartet PX2: ``mark_xref_stale`` / ``unmark_xref_stale`` /
      ``deprecate_xref`` / ``undeprecate_xref``). Distinct from the
      Phase 09 :attr:`Metagraph._xrefs_dirty` set, which tracks
      ``add_xref`` / ``remove_xref`` full-row writes per Phase 09 P54.

    Drain order per Phase 10 RPB-5 + RR-17:
    ``EDGE → HYPEREDGE → METAEDGE → METAHYPEREDGE → XREF``.
    """

    EDGE = "edge"
    HYPEREDGE = "hyperedge"
    METAEDGE = "metaedge"
    METAHYPEREDGE = "metahyperedge"
    XREF = "xref"


# Phase 10 Step 13 will append:
#   def register_soft_delete_replayers(client: "Client") -> None: ...
# Body bypasses public setters per RPB-1; emits cypher via per-method
# builders from ``mindsos_core.cypher.builders`` (Step 8). Wrapper
# ``register_all_l1_replayers(client)`` composes this with
# ``register_xref_replayers(client)``.


__all__ = ["SoftDeleteKind", "_resolve_at"]
