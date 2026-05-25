"""Global / Local L3 Capacity Metagraph bootstrap (Phase 28 ship).

Mirrors :mod:`mindsos_knowledge.bootstrap` exactly. Builds empty,
schema-wired L3 metagraphs: one shared ``capacity:datastates`` graph
plus one graph per functional category (ADR-0064 + ADR-0065).

Local metagraphs are created LAZILY — :func:`create_local` materialises
only the metagraph shell; per-category graphs and the DataStates graph
are added on first write via :func:`ensure_category_graph` /
:func:`ensure_datastate_graph` (mirrors KL's Local lifecycle).

Phase 28 ships the in-memory variant only. A future
``bootstrap_capacity_from_falkordb`` helper (mirroring
:func:`mindsos_server.persistence.bootstrap.bootstrap_kl_from_falkordb`)
is the slot that would surface ADR-0118 §amendment-5's :IN_GRAPH
closure — but no Phase 28-32 caller needs FalkorDB-backed L3 yet, so
the helper is deferred.
"""

from __future__ import annotations

from typing import Iterable

from mindsos_core import Graph, Metagraph

from .identifiers import (
    FUNCTIONAL_CATEGORIES,
    GLOBAL_METAGRAPH_NAME,
    LOCAL_METAGRAPH_NAME_FMT,
    ROLE_DATASTATES,
    category_role,
)
from .schemas import schema_for_role


def create_global(
    *,
    categories: Iterable[str] = FUNCTIONAL_CATEGORIES,
    strict: bool = False,
) -> Metagraph:
    """Construct an empty Global L3 Metagraph.

    The metagraph is pre-populated with one graph per ``category``, plus
    the shared ``capacity:datastates`` graph. Capacity and DataState
    nodes are added later via
    :class:`mindsos_capacity.CapacityLayer`.

    Args:
        categories: Functional categories to bootstrap. Defaults to the
            twelve categories per ADR-0065 (``FUNCTIONAL_CATEGORIES``).
        strict: Schema strict-mode flag (propagates to every schema).

    Returns:
        A fresh :class:`mindsos_core.Metagraph` named
        ``GLOBAL_METAGRAPH_NAME`` with ``len(categories) + 1`` contained
        graphs (the +1 is the shared DataStates graph).
    """
    mg = Metagraph(GLOBAL_METAGRAPH_NAME)
    mg.add_graph(
        Graph(
            name=ROLE_DATASTATES,
            role=ROLE_DATASTATES,
            schema=schema_for_role(ROLE_DATASTATES, strict=strict),
        )
    )
    for cat in sorted(set(categories)):
        role = category_role(cat)
        mg.add_graph(
            Graph(
                name=role,
                role=role,
                schema=schema_for_role(role, strict=strict),
            )
        )
    return mg


def create_local(
    user_id: str,
    *,
    strict: bool = False,
) -> Metagraph:
    """Construct an empty Local L3 Metagraph for ``user_id``.

    Like KL Local metagraphs, category graphs are created **lazily** on
    first write — only the metagraph shell exists initially. The
    ``strict`` argument is accepted for API symmetry with
    :func:`create_global` but not stored on the metagraph itself; it is
    threaded through :func:`ensure_category_graph` /
    :func:`ensure_datastate_graph` when those materialise the contained
    graphs (the layer caches the value on
    :class:`mindsos_capacity.CapacityLayer`).
    """
    if not isinstance(user_id, str) or not user_id:
        raise ValueError(f"user_id must be a non-empty string, got {user_id!r}")
    mg = Metagraph(LOCAL_METAGRAPH_NAME_FMT.format(user_id=user_id))
    mg.user_id = user_id  # type: ignore[attr-defined]
    return mg


def ensure_role_graph(
    metagraph: Metagraph,
    role: str,
    *,
    strict: bool = False,
) -> Graph:
    """Return the Graph for ``role`` inside ``metagraph``, creating lazily.

    Used by Local writes — and by Global bootstrap helpers to guarantee
    the DataState graph exists when a category is added after the fact.
    Idempotent: re-call with the same ``role`` returns the existing
    :class:`Graph` instance.
    """
    for g in metagraph.graphs.values():
        if g.role == role:
            return g
    g = Graph(name=role, role=role, schema=schema_for_role(role, strict=strict))
    metagraph.add_graph(g)
    return g


def ensure_category_graph(
    metagraph: Metagraph,
    category: str,
    *,
    strict: bool = False,
) -> Graph:
    """Return the graph for functional ``category`` inside ``metagraph``.

    Convenience wrapper for :func:`ensure_role_graph` with the role
    constructed via :func:`category_role` (the
    ``capacity:<category>`` prefix discipline per ADR-0065).
    """
    return ensure_role_graph(metagraph, category_role(category), strict=strict)


def ensure_datastate_graph(
    metagraph: Metagraph,
    *,
    strict: bool = False,
) -> Graph:
    """Return the shared ``capacity:datastates`` graph, creating lazily.

    Convenience wrapper for :func:`ensure_role_graph` targeting the
    fixed ``ROLE_DATASTATES`` role (ADR-0064).
    """
    return ensure_role_graph(metagraph, ROLE_DATASTATES, strict=strict)


__all__ = [
    "create_global",
    "create_local",
    "ensure_role_graph",
    "ensure_category_graph",
    "ensure_datastate_graph",
]
