"""Installed-capacities role-graph schema (ADR-0183 §amendment-5 — NET-NEW).

First-class **Local** persistence surface for the *descriptors* of a resident
brain's installed-skill Local capabilities. A skill declares each Local
capability as a descriptor (metadata + a ``reactivation_key`` naming the builder
its module registers on import + opaque ``params`` + an ``installed_by``
provenance tag); install writes it here, boot registers a function-less
capability from it and builds the function on first use (ADR-0183 §am-5).

Sibling to ``learned-pipelines`` (Local-only persistence), but **mutable**: a
descriptor is rewritten on skill upgrade and removed on uninstall, so the
discipline is ``mutable_with_retention`` (not the append-ordinal shape of
learned-pipelines / installed-skills).

Single NodeType (``InstalledCapability``); no EdgeTypes. The full descriptor
rides on ``node.value`` (opaque ADR-0182 payload); flat queryable props
(``capacity_iri`` / ``reactivation_key`` / ``category`` / ``installed_by``) are
lifted for upgrade/uninstall lookup by bundle.

``strict=False`` per ADR-0149.
"""

from __future__ import annotations

from mindsos_core import NodeType

from ._base import Discipline, L2Schema


NODE_INSTALLED_CAPABILITY = "InstalledCapability"

INSTALLED_CAPACITIES_NODE_TYPES: tuple[str, ...] = (NODE_INSTALLED_CAPABILITY,)

INSTALLED_CAPACITIES_EDGE_TYPES: tuple[str, ...] = ()  # zero-edge role.

INSTALLED_CAPABILITY_PROPS: frozenset[str] = frozenset({
    "capacity_iri",
    "reactivation_key",
    "category",
    "installed_by",
})


def build_installed_capacities_schema(strict: bool = False) -> L2Schema:
    """Construct the installed-capacities role Schema.

    Local-only, single NodeType (``InstalledCapability``), no EdgeTypes,
    discipline ``mutable_with_retention`` (descriptors rewritten on upgrade).
    ``strict`` defaults to ``False`` per ADR-0149.
    """
    s = L2Schema(
        mutation_discipline=Discipline.MUTABLE_WITH_RETENTION, strict=strict
    )
    for nt in INSTALLED_CAPACITIES_NODE_TYPES:
        s.add_node_type(NodeType(nt))
    return s


__all__ = [
    "NODE_INSTALLED_CAPABILITY",
    "INSTALLED_CAPACITIES_NODE_TYPES",
    "INSTALLED_CAPACITIES_EDGE_TYPES",
    "INSTALLED_CAPABILITY_PROPS",
    "build_installed_capacities_schema",
]
