"""Persist :class:`ElementInstance` and :class:`CompositeInstance` (Phase 07).

Per Phase 06 P49 B Core/instances boundary — this repository lives in
the sibling ``mindsos_instances`` package, never imported by
``mindsos_core``. It consumes Core's :class:`Client` Protocol and
cypher builders only.

Per Phase 07 — M9 + P96 A 4-step lifecycle: the repository subscribes
to ``Metagraph.register_persist_observer`` via
:func:`mindsos_instances.attach_registry` extension. When the
metagraph repo fires ``after_persist(mg)``, this repository persists
every element + composite instance via the typed builders in
``mindsos_core.cypher.builders``.

Per P11 A — every instance row carries ``_version: int`` (default 1
from dataclass; bumps via repository update path).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Sequence

from ..models.element_instance import (
    CompositeInstance,
    ElementInstance,
    EdgeInstance,
    GraphInstance,
    HyperEdgeInstance,
    NodeInstance,
    SubGraphInstance,
)
from ..registry import ElementRegistry

if TYPE_CHECKING:
    # Deferred import to avoid the
    # mindsos_core.persistence ↔ mindsos_instances.persistence cycle.
    from mindsos_core.persistence.client import Client


class InstanceRepository:
    """Persist instance artefacts owned by an :class:`ElementRegistry`.

    Per Phase 06 + Phase 07 M9 — instances persist sibling-side via
    the observer hook. The repository's primary API is
    :meth:`persist_all`, called from within
    :func:`mindsos_instances.attach_registry`'s ``after_persist`` hook.
    """

    def __init__(self, client: "Client") -> None:
        self._client = client

    # ── observer-driven entry point ──────────────────────────────────

    def persist_all(self, registry: ElementRegistry) -> None:
        """Persist every element + composite instance on ``registry``.

        Phase 07 entry point invoked from the persist observer
        (M9 step 3 of the 4-step lifecycle per P96 A). Idempotent
        (MERGE-based builders); safe to re-run on observer failure
        per P33 A.
        """
        mid = registry.metagraph.metagraph_id
        # ElementRegistry stores both kinds in a single _instances dict
        # (Phase 06 shape); filter by isinstance for routing.
        for inst in registry.iter():
            if isinstance(inst, ElementInstance):
                self.persist_element_instance(inst, mid)
            elif isinstance(inst, CompositeInstance):
                self.persist_composite_instance(inst, mid)

    # ── per-instance persist (programmatic API) ──────────────────────

    def persist_element_instance(
        self, inst: ElementInstance, metagraph_id: str
    ) -> None:
        """Persist a single :class:`ElementInstance`.

        Resolves the kind-specific Cypher label + member_ids from the
        instance subclass; passes the override bag (validated at
        construction) verbatim through ``ov__`` prefixing in the
        builder.
        """
        # Late import to break the cypher builders ↔ instance models
        # cycle some installs trip on.
        from mindsos_core.cypher.builders import build_create_element_instance

        kind = _kind_for(inst)
        member_ids = _member_ids_for(inst)
        # source_id is the template_id at Phase 07 (templates are the
        # source primitives the instance derives from).
        source_id = inst.template_id
        # Phase 07 ships no source_graph_id back-resolution (deferred to
        # Phase 08 when metagraph reconstruction lands).
        source_graph_id: Optional[str] = None

        q, p = build_create_element_instance(
            instance_id=inst.id,
            kind=kind,
            metagraph_id=metagraph_id,
            source_id=source_id,
            source_graph_id=source_graph_id,
            overrides=dict(inst.overrides),
            label=None,  # halvim slim ElementInstance has no label field.
            member_ids=member_ids,
        )
        self._client.run_query(q, p)

    def persist_composite_instance(
        self, comp: CompositeInstance, metagraph_id: str
    ) -> None:
        """Persist a single :class:`CompositeInstance` + its :HAS_MEMBER edges."""
        from mindsos_core.cypher.builders import build_create_composite_instance

        # CompositeMember is a union of ElementInstance / CompositeInstance;
        # both expose ``.id`` per halvim Phase 06 shape.
        member_ids = [m.id for m in comp.members]
        q, p = build_create_composite_instance(
            instance_id=comp.id,
            metagraph_id=metagraph_id,
            member_instance_ids=member_ids,
            overrides=dict(comp.bundle_overrides),
            label=None,
        )
        self._client.run_query(q, p)


# ── private helpers ─────────────────────────────────────────────────────


def _kind_for(inst: ElementInstance) -> str:
    """Map an instance subclass to the kind string consumed by the builder."""
    if isinstance(inst, NodeInstance):
        return "node"
    if isinstance(inst, EdgeInstance):
        return "edge"
    if isinstance(inst, HyperEdgeInstance):
        return "hyperedge"
    if isinstance(inst, SubGraphInstance):
        return "subgraph"
    if isinstance(inst, GraphInstance):
        return "graph"
    # MetaEdgeInstance / MetaHyperEdgeInstance per Phase 06 — class
    # name lookup keeps the helper resilient to future subclasses.
    name = type(inst).__name__
    if name == "MetaEdgeInstance":
        return "metaedge"
    if name == "MetaHyperEdgeInstance":
        return "metahyperedge"
    raise TypeError(
        f"Unknown ElementInstance subclass: {type(inst).__name__}"
    )


def _member_ids_for(inst: ElementInstance) -> Optional[Sequence[str]]:
    """SubGraphInstance carries node_ids member selection per Phase 06 P13 B."""
    if isinstance(inst, SubGraphInstance):
        node_ids = inst.overrides.get("node_ids") or frozenset()
        return sorted(node_ids) if node_ids else None
    return None


__all__ = ["InstanceRepository"]
