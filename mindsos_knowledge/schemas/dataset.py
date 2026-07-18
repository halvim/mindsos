"""Dataset role-graph schema helper (ADR-0150 §amendment-9 — NET-NEW).

Datasets are **Local-only** and **per-instance** (``dataset:<name>``).
Unlike the fixed named roles, a dataset schema is **registered**
(:func:`mindsos_knowledge.schemas.register_dataset_schema`), not built
from the static ``_ROLE_SCHEMA_BUILDERS`` dispatch table, because
instances differ in shape: ``dataset:arc1`` holds ``Task`` nodes carrying
train/test grid ``content``; ``dataset:arc3`` holds ``Game`` nodes that
are a handle only (id + title, no content).

This module ships only a thin *builder helper* a brain uses to construct
its instance schema before registering it. Core owns no dataset shape.

Discipline defaults to ``append_only`` (a corpus is pure-append; an entry
is never superseded). Note: ``append_only`` has no live write-boundary
enforcement at v1 (``validate_mutation_discipline`` is uncalled) — it is a
declared, forward-looking discipline. ``content`` is a plain JSON node
field (persists inline via the ADR-0182 ``_value_json`` codec); no
``StorageMode`` declaration is needed or honoured at v1.
"""

from __future__ import annotations

from typing import Iterable

from mindsos_core import EdgeType, NodeType

from ._base import Discipline, L2Schema


def build_dataset_schema(
    node_types: Iterable[str],
    edge_types: Iterable[str] = (),
    *,
    discipline: Discipline = Discipline.APPEND_ONLY,
    strict: bool = False,
) -> L2Schema:
    """Construct an L2 schema for a dataset instance role.

    Args:
        node_types: NodeType names for the instance (e.g. ``("Task",)``
            for arc1, ``("Game",)`` for arc3).
        edge_types: Optional EdgeType names; each is added as an
            any-node→any-node edge over ``node_types``.
        discipline: Mutation discipline (default ``append_only``).
        strict: Opt-in property-type enforcement (default ``False`` per
            ADR-0149).
    """
    s = L2Schema(mutation_discipline=discipline, strict=strict)
    nts = tuple(node_types)
    for nt in nts:
        s.add_node_type(NodeType(nt))
    any_node = frozenset(nts)
    for et in edge_types:
        s.add_edge_type(EdgeType(et, any_node, any_node))
    return s


__all__ = ["build_dataset_schema"]
