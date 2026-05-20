"""Role-scoped content hash for :class:`~mindsos_core.Metagraph`.

Phase 16 NEW per ADR-0052 §amendment-1 (Phase 16 ship). Implements
``metagraph_content_hash(mg, *, role)`` — a deterministic SHA-256 over
a canonical-JSON serialisation of ONE role-graph within a metagraph.
Used by :func:`mindsos_admin.compute_similarity` as input to
:class:`SimilarityReport.report_id` per ADR-0052 §Decision (extended
in §amendment-1).

**Scope:** per-role, NOT whole-metagraph.

Cross-role mutation does NOT invalidate the hash. WAL + tombstones +
soft-deleted nodes (per ADR-0133 ``deprecated_at``) are excluded by
construction — different graphs in the metagraph; not visited under
role-scoped hashing. Soft-deleted edges/hyperedges within the scored
role-graph are filtered out at iteration time.

**Canonical-JSON rules:**

* Graphs in the metagraph are filtered to those carrying the requested
  ``role``. Multiple graphs may share a role (e.g., multiple
  ``alignment:a:b`` graphs); all matching graphs are included, sorted
  by ``graph_id``.
* Within each graph: nodes sorted by ``node_id``; edges sorted by
  ``edge_id``; hyperedges sorted by ``edge_id``.
* Property bags: keys sorted alphabetically. Values normalised per
  :func:`_canonical_value`:
  - ``frozenset`` → sorted list (canonicalized recursively).
  - ``set`` → sorted list.
  - ``tuple`` → list (canonicalized recursively).
  - ``datetime`` → ISO 8601 string with explicit timezone marker.
  - ``UUID`` → str.
  - ``float`` → ``f"{x:.6f}"`` per ADR-0052 §amendment-1 PB-T2 6-decimal
    canonicalization.
  - Otherwise: pass-through (JSON-serialisable primitives).
* Reserved system properties (keys starting with ``_``) are EXCLUDED
  from the hash inputs — they're operational metadata (e.g., ``_version``
  OCC counter, ``_deprecated_at`` rehydration sentinel) that should
  not invalidate ``report_id`` on a refresh-then-persist cycle.

**Output:** lowercase hex SHA-256 digest (64 chars).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import is_dataclass
from datetime import datetime
from typing import Any, Iterable
from uuid import UUID

from mindsos_core import Metagraph


__all__ = ["metagraph_content_hash"]


def metagraph_content_hash(mg: Metagraph, *, role: str) -> str:
    """Return SHA-256 hex digest of the role-graph content within ``mg``.

    Per ADR-0052 §amendment-1 (Phase 16 ship). Role-scoped: cross-role
    mutation does not invalidate. Soft-deleted edges/hyperedges within
    the scored role-graph are filtered.

    Args:
        mg: The metagraph to scan.
        role: The role-graph name. Matches ``graph.role`` on contained
            :class:`~mindsos_core.Graph` instances. Multiple matching
            graphs are merged (deterministically) into one hash input.

    Returns:
        Lowercase hex SHA-256 (64 characters).
    """
    payload = _canonical_role_payload(mg, role)
    serialised = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


# ── §1 Canonical payload assembly ──────────────────────────────────────


def _canonical_role_payload(mg: Metagraph, role: str) -> dict[str, Any]:
    """Build the canonical-JSON payload for one role within a metagraph.

    Returns a dict with ``role`` + ``graphs`` keys. ``graphs`` is a list
    sorted by a content-derived key (first node-id ascending, falling
    back to empty-string for empty graphs), each entry containing
    canonicalized ``nodes`` / ``edges`` / ``hyperedges``.

    Per Phase 16 B-16-T2 fix: ``graph_id`` (auto-generated UUID) and
    graph ``name`` are EXCLUDED from the payload. Two metagraphs with
    identically-content'd role-graphs hash equal regardless of graph
    identity. Sort key shifted from ``graph_id`` to a content
    fingerprint so multi-graph roles (alignment) stay deterministic.
    """
    matching = sorted(
        (g for g in mg.graphs.values() if g.role == role),
        key=_graph_content_sort_key,
    )
    return {
        "role": role,
        "graphs": [_canonical_graph(g) for g in matching],
    }


def _graph_content_sort_key(graph: Any) -> tuple:
    """Content-derived sort key for graphs sharing a role.

    Uses the sorted-tuple of node-ids; empty graphs sort first via the
    empty tuple. Stable across re-builds because node-ids in this
    codebase are caller-pinned IRIs (Phase 12+).
    """
    return tuple(sorted(graph.nodes.keys()))


def _canonical_graph(graph: Any) -> dict[str, Any]:
    """Canonicalize one :class:`~mindsos_core.Graph` (content only).

    Per Phase 16 B-16-T2 fix: ``graph_id`` and ``name`` are EXCLUDED
    from the payload. The hash is over CONTENT (role + nodes + edges +
    hyperedges), not graph identity.
    """
    return {
        "role": graph.role,
        "nodes": [
            _canonical_node(n)
            for n in sorted(graph.nodes.values(), key=lambda n: n.node_id)
        ],
        "edges": [
            _canonical_edge(e)
            for e in sorted(
                _iter_active_edges(graph),
                key=lambda e: e.edge_id,
            )
        ],
        "hyperedges": [
            _canonical_hyperedge(he)
            for he in sorted(
                _iter_active_hyperedges(graph),
                key=lambda he: he.edge_id,
            )
        ],
    }


def _iter_active_edges(graph: Any) -> Iterable[Any]:
    """Iterate non-deprecated edges (per ADR-0133 soft-delete filter)."""
    return graph.iter_edges(include_deprecated=False)


def _iter_active_hyperedges(graph: Any) -> Iterable[Any]:
    """Iterate non-deprecated hyperedges (per ADR-0133 soft-delete filter)."""
    return graph.iter_hyperedges(include_deprecated=False)


def _canonical_node(node: Any) -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "type_name": node.type_name,
        "value": _canonical_value(node.value),
        "properties": _canonical_properties(node.properties),
    }


def _canonical_edge(edge: Any) -> dict[str, Any]:
    return {
        "edge_id": edge.edge_id,
        "type_name": edge.type_name,
        "source_id": edge.source.node_id,
        "target_id": edge.target.node_id,
        "label": edge.label,
        "properties": _canonical_properties(edge.properties),
    }


def _canonical_hyperedge(hyperedge: Any) -> dict[str, Any]:
    return {
        "edge_id": hyperedge.edge_id,
        "type_name": hyperedge.type_name,
        "label": hyperedge.label,
        "members": sorted(n.node_id for n in hyperedge.members),
        "properties": _canonical_properties(hyperedge.properties),
    }


# ── §2 Value canonicalization ──────────────────────────────────────────


def _canonical_properties(props: dict[str, Any]) -> dict[str, Any]:
    """Strip reserved keys + canonicalize values; preserve sorted-key order."""
    return {
        k: _canonical_value(v)
        for k, v in sorted(props.items())
        if not k.startswith("_")
    }


def _canonical_value(value: Any) -> Any:
    """Recursively canonicalize a property value for JSON serialisation.

    Handles: frozenset/set → sorted list; tuple → list; datetime → ISO
    8601; UUID → str; float → 6-decimal string (PB-T2). Primitive
    JSON-serialisable types pass through unchanged.

    Dataclasses are reduced to their ``__dict__`` (rare in property
    bags but defensible). Anything else falls back to ``repr(value)``.
    """
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return f"{value:.6f}"
    if isinstance(value, (frozenset, set)):
        return sorted(_canonical_value(item) for item in value)
    if isinstance(value, tuple):
        return [_canonical_value(item) for item in value]
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, dict):
        return {
            k: _canonical_value(v)
            for k, v in sorted(value.items())
        }
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return _canonical_value(value.__dict__)
    return repr(value)
