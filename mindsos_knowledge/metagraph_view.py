"""Read-only view over a :class:`mindsos_core.Metagraph` (Phase 14).

:class:`MetagraphView` is a **whitelist wrapper** per Phase 14
round-1 PB-3: it holds a reference to a Metagraph and exposes only
specific read methods. Callers never access mutation surfaces
through the view; mutation goes through the L1 Graph reference
returned by :meth:`alignment_graph` or :meth:`graphs_by_role` (the
Phase 33-35 ``KLWriteHandle`` ADR-0143 Proposed path).

The wrapper does NOT subclass :class:`Metagraph` — ``isinstance(view,
Metagraph)`` is False. The two surfaces are intentionally distinct
to honour ADR-0138 "no public write methods on KL" structurally.

Read methods ship in Phase 14:

* :meth:`roles` — the set of distinct ``role`` values in the
  metagraph's contained graphs.
* :meth:`graphs_by_role` — list of Graphs whose ``role`` matches.
* :meth:`get_node` — first Node found by id within graphs of a role.
* :meth:`get_edges` — outgoing edges (alias :meth:`step`).
* :meth:`iter_nodes` — iterate Nodes within a role-graph.
* :meth:`alignment_graph` — convenience for the
  ``alignment:<a>:<b>`` lookup.
* :meth:`metagraph_id` (property) — the underlying metagraph_id.
* :meth:`metagraph_name` (property) — the underlying name.

Deferred surfaces:

* ``follow_ref(node, target_role)`` cross-metagraph helper — defers
  to Phase 25 (SessionProtocol seam) or first L3 capacity phase per
  Phase 14 PB-10 (v3 ``step`` overlay was a §1.2 contradiction;
  Phase 14 doesn't re-introduce it).
* ``version=`` kwarg on :meth:`step` — VACATED at Phase 17
  retirement (2026-05-20) per ADR-0150 §amendment-3. The shipped
  invariant is one graph per role per metagraph; there is no
  ``(role, version)`` discriminator to dispatch on. Phase 14 PB-15
  closure recorded in `confirmation_docs/PHASE_14_DESIGN_LOG.md`.
* ``iter_xrefs`` — defers; Phase 25 amends if needed.

Shipped at Phase 17 retirement (2026-05-20):

* :meth:`versions_in_role` — IRI-scan enumerator returning distinct
  ``parse_iri(node_id).version`` values observed in the role-graph.
  Per ADR-0150 §amendment-3.

Per Phase 14 PB-16, returned Node / Edge references are mutable L1
objects; the read-only contract is documented, not structurally
enforced on returned values. ADR-0138 governs the API surface
(``MetagraphView`` exposes no write methods); whether a caller
reaches L1 mutables via a write method or via a read accessor is
irrelevant — L1's own ``Graph.add_node`` etc. is the canonical
write path.
"""

from __future__ import annotations

from typing import Iterable, Iterator, List, Optional, Set

from mindsos_core import Edge, Graph, Node
from mindsos_core.models.metagraph import Metagraph


__all__ = ["MetagraphView"]


class MetagraphView:
    """Read-only whitelist wrapper over a :class:`Metagraph`.

    Constructed by :meth:`KnowledgeLayer.global_view` and
    :meth:`KnowledgeLayer.local_view`. Not part of any public
    constructor surface for callers — use the KL factory methods.
    """

    __slots__ = ("_metagraph",)

    def __init__(self, metagraph: Metagraph) -> None:
        """Wrap ``metagraph`` for read-only access.

        Args:
            metagraph: The :class:`mindsos_core.Metagraph` to expose
                read access to. The view holds a reference; the
                metagraph remains mutable through the L1 API but
                the view exposes no mutation methods.
        """
        # Direct attribute write to the slot; no proxying / property
        # setter (private slot, no public attribute access intended).
        object.__setattr__(self, "_metagraph", metagraph)

    # ── identity accessors ────────────────────────────────────────────

    @property
    def metagraph_id(self) -> str:
        """The underlying :attr:`Metagraph.metagraph_id`."""
        return self._metagraph.metagraph_id

    @property
    def metagraph_name(self) -> str:
        """The underlying :attr:`Metagraph.name`."""
        return self._metagraph.name

    # ── role-graph discovery ──────────────────────────────────────────

    def roles(self) -> Set[str]:
        """Return the set of distinct role values across contained graphs.

        Excludes ``None`` (graphs without a role attribute set).
        """
        return {
            g.role
            for g in self._metagraph.graphs.values()
            if g.role is not None
        }

    def graphs_by_role(self, role: str) -> List[Graph]:
        """Return contained graphs whose ``role`` matches.

        One graph per role per metagraph (locked by ADR-0150
        §amendment-3 at Phase 17 retirement, 2026-05-20). The list
        return shape is preserved for API stability; in practice it
        is always length-0 or length-1.

        Args:
            role: The role string to filter on.

        Returns:
            List of :class:`Graph` objects with ``g.role == role``;
            empty list if no match.
        """
        return [
            g
            for g in self._metagraph.graphs.values()
            if g.role == role
        ]

    def alignment_graph(
        self, role_a: str, role_b: str
    ) -> Optional[Graph]:
        """Convenience: look up the ``alignment:<role_a>:<role_b>`` graph.

        Returns ``None`` if no alignment pair-graph exists for the
        ordered ``(role_a, role_b)`` pair. Per ADR-0150 §amendment-1,
        alignment is Global-only at v1; this method only finds graphs
        in the wrapped metagraph regardless.

        Note: the alignment role string is ordered (``a:b`` ≠ ``b:a``);
        callers must pass the same order used at ensure time.

        Args:
            role_a: First role of the alignment pair.
            role_b: Second role of the alignment pair.

        Returns:
            The :class:`Graph` for the alignment pair, or ``None`` if
            not found.
        """
        role = f"alignment:{role_a}:{role_b}"
        matches = self.graphs_by_role(role)
        return matches[0] if matches else None

    # ── element accessors ─────────────────────────────────────────────

    def get_node(self, role: str, node_id: str) -> Optional[Node]:
        """Return the first Node with ``node_id`` in any role-matching graph.

        One graph per role per metagraph (ADR-0150 §amendment-3);
        "first" is "the only one" in practice.

        Per PB-16 calibration: returned Node is the L1 reference, not a
        defensive copy. Caller MUST treat the result as read-only.

        Args:
            role: The role-graph to search in.
            node_id: The element id to look up.

        Returns:
            The :class:`Node` if found in any matching role-graph,
            else ``None``.
        """
        for g in self.graphs_by_role(role):
            n = g.nodes.get(node_id)
            if n is not None:
                return n
        return None

    def iter_nodes(
        self,
        role: str,
        *,
        type_: Optional[str] = None,
    ) -> Iterator[Node]:
        """Iterate Nodes in the role-matching graph(s).

        Args:
            role: The role-graph to iterate.
            type_: Optional :attr:`Node.type_name` filter. Nodes with
                a different ``type_name`` are skipped.

        Yields:
            :class:`Node` references from matching role-graphs.
        """
        for g in self.graphs_by_role(role):
            for n in g.nodes.values():
                if type_ is not None and n.type_name != type_:
                    continue
                yield n

    def get_edges(
        self,
        role: str,
        node_id: str,
        *,
        edge_type: Optional[str] = None,
        include_deprecated: bool = False,
    ) -> List[Edge]:
        """Return edges incident on ``node_id`` in the role-graph.

        "Incident on" matches v3's `Graph.get_edges_for_node` semantics:
        edges where ``source.node_id == node_id`` OR ``target.node_id
        == node_id``.

        Per ADR-0133 (Phase 10), ``include_deprecated=False`` filters
        out soft-deleted edges by default.

        Args:
            role: The role-graph to search.
            node_id: The element id whose incident edges to return.
            edge_type: Optional :attr:`Edge.type_name` filter.
            include_deprecated: When True, includes edges whose
                ``deprecated_at is not None``.

        Returns:
            List of :class:`Edge` references (possibly empty).
        """
        out: List[Edge] = []
        for g in self.graphs_by_role(role):
            for e in g.get_edges_for_node(
                node_id, include_deprecated=include_deprecated
            ):
                if edge_type is not None and e.type_name != edge_type:
                    continue
                out.append(e)
        return out

    def step(
        self,
        role: str,
        node_id: str,
        *,
        edge_type: Optional[str] = None,
        include_deprecated: bool = False,
    ) -> List[Edge]:
        """Selective walk helper — returns within-view edges incident on a node.

        Per Phase 14 PB-10: NO Local-specialisation overlay. v3's
        :class:`WalkResult` shape (left-joining Local onto Global)
        contradicted v3 §1.2's own out-of-scope clause; ADR-0138's
        narrowing reaffirms separation. Cross-metagraph composition
        belongs at Phase 25 / first L3 capacity / Mental Model layer.

        Per ADR-0150 §amendment-3 (Phase 17 retirement, 2026-05-20):
        NO ``version=`` kwarg. The shipped invariant is one graph per
        role per metagraph; "active version" has no graph-layer
        dispatch. Version enumeration ships via :meth:`versions_in_role`
        (IRI-scan); active-version routing is vacated and locked.

        Effectively an alias for :meth:`get_edges`. Kept as a named
        entry point for API surface stability.

        Args:
            role: The role-graph to step in.
            node_id: The starting element id.
            edge_type: Optional filter.
            include_deprecated: ADR-0133 filter.

        Returns:
            List of :class:`Edge` references (possibly empty).
        """
        return self.get_edges(
            role,
            node_id,
            edge_type=edge_type,
            include_deprecated=include_deprecated,
        )

    # ── version enumeration (Phase 17 retirement) ─────────────────────

    def versions_in_role(self, role: str) -> Set[str]:
        """Return the distinct IRI-string versions observed in ``role``.

        IRI-scan enumerator. For each node in the role-graph, attempts
        to parse the ``node_id`` as a version-qualified IRI via
        :func:`mindsos_knowledge.identifiers.parse_iri` and collects
        the ``.version`` field. Nodes whose ``node_id`` is not a
        version-qualified IRI (e.g., bare fragments, alignment-graph
        node ids) are silently skipped.

        Per ADR-0150 §amendment-3 (Phase 17 retirement, 2026-05-20):
        this is the canonical "what versions are in this role-graph"
        surface. There is no notion of "active version" — the
        amendment locks one-graph-per-role with version-as-IRI-string.

        Args:
            role: The role-graph to scan.

        Returns:
            Set of distinct version strings (e.g., ``{"4.1", "4.2"}``);
            empty set if the role-graph is empty or holds no
            version-qualified IRIs.
        """
        # Lazy import to avoid circular dependency at module load.
        from .identifiers import parse_iri
        from .exceptions import RefFormatError

        versions: Set[str] = set()
        for g in self.graphs_by_role(role):
            for node_id in g.nodes:
                try:
                    versions.add(parse_iri(node_id).version)
                except RefFormatError:
                    # Bare fragments / non-version-qualified ids are
                    # legitimate (e.g., alignment-graph member ids).
                    continue
        return versions

    # ── repr ──────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"MetagraphView(metagraph_id={self._metagraph.metagraph_id!r}, "
            f"name={self._metagraph.name!r}, "
            f"roles={sorted(self.roles())!r})"
        )

    # ── write-method blocker (defensive; structural by absence) ───────
    # No write methods are defined. ADR-0138 enforced by the absence
    # of mutation methods. The class does NOT subclass Metagraph;
    # callers cannot reach L1 mutation via the wrapper. They CAN reach
    # mutation via ``graphs_by_role(...)[0].add_node(...)``, but that's
    # the L1 surface, not the KL surface — see PB-16 design rationale.
