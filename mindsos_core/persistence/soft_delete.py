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
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .client import Client


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


# ── WAL replayer kinds (Phase 10 M8 + RR-1; payload shapes per kind) ────────


#: 4 collapsed edge-side kinds (M8). Payload shape:
#:   {element_id, element_kind, scope_id, at?}
#: ``element_kind`` ∈ {"edge", "hyperedge", "metaedge", "metahyperedge"}.
#: ``scope_id`` is ``graph_id`` for edge/hyperedge, ``metagraph_id`` for
#: metaedge/metahyperedge. ``at`` is an ISO-8601 string for *_deprecate /
#: *_dispute kinds; absent for the un-* kinds.
KIND_ELEMENT_DEPRECATE = "element_deprecate"
KIND_ELEMENT_UNDEPRECATE = "element_undeprecate"
KIND_ELEMENT_DISPUTE = "element_dispute"
KIND_ELEMENT_UNDISPUTE = "element_undispute"


def register_soft_delete_replayers(client: "Client") -> None:
    """Register the 4 collapsed edge-side WAL replayer kinds (Phase 10 M8 + RPB-1).

    Per-Client replayer registry (Phase 09 P51 + P61); replayer bodies
    bypass public setters per RPB-1 — they invoke the per-method cypher
    builders directly via the captured ``client`` closure. No
    ``DeprecatedFilterPendingWarning`` fires on replay (the warning class
    was STRIPPED entirely per P74 — filter ships in the same phase under
    the P68 merge).

    Composed by
    :func:`mindsos_core.persistence.bootstrap.register_all_l1_replayers`
    alongside :func:`mindsos_core.persistence.xref_repository.register_xref_replayers`
    (extended Phase 10: 2 → 6 kinds). Wrapper grows 2 → 10 total kinds.

    Per RPB-1 — set/unset dispatch by ``at`` presence in payload + by
    ``kind``. Per RR-1 — payload shape ``{element_id, element_kind,
    scope_id, at?}`` (scope_id added at Step 13 over the design-log
    schema; ``element_id`` alone is not enough to MATCH).
    """
    # Late import — break the soft_delete → cypher.builders cycle that
    # would otherwise hit during module load. Builders are pure functions
    # so the late import is cheap.
    from ..cypher.builders import (
        build_set_edge_deprecated_at,
        build_set_edge_disputed_at,
        build_set_hyperedge_deprecated_at,
        build_set_hyperedge_disputed_at,
        build_set_metaedge_deprecated_at,
        build_set_metaedge_disputed_at,
        build_set_metahyperedge_deprecated_at,
        build_set_metahyperedge_disputed_at,
        build_unset_edge_deprecated_at,
        build_unset_edge_disputed_at,
        build_unset_hyperedge_deprecated_at,
        build_unset_hyperedge_disputed_at,
        build_unset_metaedge_deprecated_at,
        build_unset_metaedge_disputed_at,
        build_unset_metahyperedge_deprecated_at,
        build_unset_metahyperedge_disputed_at,
    )
    from .wal import register_replayer

    # Per-element-kind dispatch tables. Two tables (set + unset) × 4
    # element kinds. The set table is keyed by (element_kind, field) and
    # returns the SET builder; the unset table returns the UNSET builder.
    _SET_BUILDERS = {
        ("edge", "deprecated_at"): build_set_edge_deprecated_at,
        ("edge", "disputed_at"): build_set_edge_disputed_at,
        ("hyperedge", "deprecated_at"): build_set_hyperedge_deprecated_at,
        ("hyperedge", "disputed_at"): build_set_hyperedge_disputed_at,
        ("metaedge", "deprecated_at"): build_set_metaedge_deprecated_at,
        ("metaedge", "disputed_at"): build_set_metaedge_disputed_at,
        ("metahyperedge", "deprecated_at"): build_set_metahyperedge_deprecated_at,
        ("metahyperedge", "disputed_at"): build_set_metahyperedge_disputed_at,
    }
    _UNSET_BUILDERS = {
        ("edge", "deprecated_at"): build_unset_edge_deprecated_at,
        ("edge", "disputed_at"): build_unset_edge_disputed_at,
        ("hyperedge", "deprecated_at"): build_unset_hyperedge_deprecated_at,
        ("hyperedge", "disputed_at"): build_unset_hyperedge_disputed_at,
        ("metaedge", "deprecated_at"): build_unset_metaedge_deprecated_at,
        ("metaedge", "disputed_at"): build_unset_metaedge_disputed_at,
        ("metahyperedge", "deprecated_at"): build_unset_metahyperedge_deprecated_at,
        ("metahyperedge", "disputed_at"): build_unset_metahyperedge_disputed_at,
    }

    def _replay_element_set(field: str, payload: Dict[str, Any]) -> None:
        kind = payload["element_kind"]
        builder = _SET_BUILDERS[(kind, field)]
        q, p = builder(payload["scope_id"], payload["element_id"], payload["at"])
        client.run_query(q, p)

    def _replay_element_unset(field: str, payload: Dict[str, Any]) -> None:
        kind = payload["element_kind"]
        builder = _UNSET_BUILDERS[(kind, field)]
        q, p = builder(payload["scope_id"], payload["element_id"])
        client.run_query(q, p)

    register_replayer(
        client, KIND_ELEMENT_DEPRECATE,
        lambda p: _replay_element_set("deprecated_at", p),
    )
    register_replayer(
        client, KIND_ELEMENT_UNDEPRECATE,
        lambda p: _replay_element_unset("deprecated_at", p),
    )
    register_replayer(
        client, KIND_ELEMENT_DISPUTE,
        lambda p: _replay_element_set("disputed_at", p),
    )
    register_replayer(
        client, KIND_ELEMENT_UNDISPUTE,
        lambda p: _replay_element_unset("disputed_at", p),
    )


__all__ = [
    "SoftDeleteKind",
    "_resolve_at",
    "register_soft_delete_replayers",
    "KIND_ELEMENT_DEPRECATE",
    "KIND_ELEMENT_UNDEPRECATE",
    "KIND_ELEMENT_DISPUTE",
    "KIND_ELEMENT_UNDISPUTE",
]
