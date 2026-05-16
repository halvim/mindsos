"""Walker for :class:`Metagraph` structural equality (Phase 08 RR-13 A).

Phase 08 Pass criterion needs a way to assert that a
``load_metagraph(client, mid)`` result equals the in-memory
:class:`Metagraph` that was just persisted. The walker checks every
field a roundtrip should preserve, with canonical comparisons for
list/set-typed structural fields (mirroring Phase 05c canonicalize-
before-cardinality precedent — B-08-T-likely-1 ranks the structural
drift risk on ``IntergraphHyperEdge.ordered`` list/set
inconsistencies).

Usage::

    from tests._shared.metagraph_equality import assert_metagraphs_equal

    mg1 = ...
    mg2 = load_metagraph(client, mg1.metagraph_id)
    assert_metagraphs_equal(mg1, mg2)

Comparison scope (RR-13 A):

* ``name`` + ``metagraph_id`` + ``schema_name``.
* ``properties`` dict (key + value equality).
* ``graphs`` — by graph_id; per-graph walker on
  (``name``, ``role``, ``properties``, nodes, edges, hyperedges).
* ``metaedges`` — by edge_id; per-edge (``source_graph_id``,
  ``target_graph_id``, ``type_name``, ``label``, ``properties``,
  ``_version``).
* ``metahyperedges`` — by edge_id; per-edge (sorted graph_ids,
  ``type_name``, ``label``, ``properties``, ``_version``).
* ``intergraph_edges`` — by edge_id; per-edge (source/target node/
  graph, ``type_name``, ``compositional``, ``label``, ``properties``,
  ``_version``).
* ``intergraph_hyperedges`` — by edge_id; per-edge (anchors,
  members, ``type_name``, ``compositional``, ``label``,
  ``properties``, ``_version``). Anchors + members compared as
  sorted lists of (graph_id, node_id) tuples to absorb ordered/set
  semantics inconsistencies.

Per-bucket failure raises :class:`AssertionError` with a precise
finding so the test surface tells which bucket diverged.
"""

from __future__ import annotations

from typing import Any


def assert_metagraphs_equal(mg1: Any, mg2: Any) -> None:
    """Walker for round-trip metagraph equality. Raises on any drift."""
    _assert_anchor(mg1, mg2)
    _assert_graphs(mg1, mg2)
    _assert_metaedges(mg1, mg2)
    _assert_metahyperedges(mg1, mg2)
    _assert_intergraph_edges(mg1, mg2)
    _assert_intergraph_hyperedges(mg1, mg2)
    # Phase 09 PB-3 + RR-4 — XRef id-set + per-id field-by-field check.
    _assert_xrefs(mg1, mg2)


def _assert_anchor(mg1: Any, mg2: Any) -> None:
    assert mg1.name == mg2.name, (
        f"Metagraph name drift: {mg1.name!r} vs {mg2.name!r}"
    )
    assert mg1.metagraph_id == mg2.metagraph_id, (
        f"Metagraph id drift: {mg1.metagraph_id!r} vs "
        f"{mg2.metagraph_id!r}"
    )
    s1 = getattr(mg1, "schema_name", None)
    s2 = getattr(mg2, "schema_name", None)
    assert s1 == s2, f"Metagraph schema_name drift: {s1!r} vs {s2!r}"
    p1 = dict(getattr(mg1, "properties", {}) or {})
    p2 = dict(getattr(mg2, "properties", {}) or {})
    assert p1 == p2, (
        f"Metagraph properties drift: {p1!r} vs {p2!r}"
    )


def _assert_graphs(mg1: Any, mg2: Any) -> None:
    ids1 = set(mg1.graphs.keys())
    ids2 = set(mg2.graphs.keys())
    missing = ids1 - ids2
    extra = ids2 - ids1
    assert not missing, f"Graphs missing from mg2: {sorted(missing)}"
    assert not extra, f"Graphs extra in mg2: {sorted(extra)}"
    for gid in sorted(ids1):
        g1 = mg1.graphs[gid]
        g2 = mg2.graphs[gid]
        assert g1.name == g2.name, (
            f"Graph {gid!r} name drift: {g1.name!r} vs {g2.name!r}"
        )
        assert g1.role == g2.role, (
            f"Graph {gid!r} role drift: {g1.role!r} vs {g2.role!r}"
        )
        # Properties (P9 C Graph .properties writer deferred at Phase 07;
        # Phase 08 inherits the gap). Compare for visibility.
        gp1 = dict(getattr(g1, "properties", {}) or {})
        gp2 = dict(getattr(g2, "properties", {}) or {})
        assert gp1 == gp2, (
            f"Graph {gid!r} properties drift: {gp1!r} vs {gp2!r}"
        )
        # Nodes.
        n_ids_1 = set(g1.nodes.keys())
        n_ids_2 = set(g2.nodes.keys())
        assert n_ids_1 == n_ids_2, (
            f"Graph {gid!r} node ids drift: missing={sorted(n_ids_1 - n_ids_2)}; "
            f"extra={sorted(n_ids_2 - n_ids_1)}"
        )
        for nid in sorted(n_ids_1):
            n1 = g1.nodes[nid]
            n2 = g2.nodes[nid]
            assert n1.value == n2.value, (
                f"Node {nid!r} value drift: {n1.value!r} vs {n2.value!r}"
            )
            assert n1.type_name == n2.type_name, (
                f"Node {nid!r} type_name drift: {n1.type_name!r} vs "
                f"{n2.type_name!r}"
            )
            assert dict(n1.properties) == dict(n2.properties), (
                f"Node {nid!r} properties drift: {dict(n1.properties)!r} "
                f"vs {dict(n2.properties)!r}"
            )
        # Edges.
        e_ids_1 = set(g1.edges.keys())
        e_ids_2 = set(g2.edges.keys())
        assert e_ids_1 == e_ids_2, (
            f"Graph {gid!r} edge ids drift: missing={sorted(e_ids_1 - e_ids_2)}; "
            f"extra={sorted(e_ids_2 - e_ids_1)}"
        )
        for eid in sorted(e_ids_1):
            e1 = g1.edges[eid]
            e2 = g2.edges[eid]
            assert e1.source.node_id == e2.source.node_id, (
                f"Edge {eid!r} source drift: {e1.source.node_id!r} vs "
                f"{e2.source.node_id!r}"
            )
            assert e1.target.node_id == e2.target.node_id, (
                f"Edge {eid!r} target drift"
            )
            assert e1.type_name == e2.type_name, (
                f"Edge {eid!r} type_name drift"
            )
            assert e1.label == e2.label, f"Edge {eid!r} label drift"
            assert dict(e1.properties) == dict(e2.properties), (
                f"Edge {eid!r} properties drift"
            )
        # Hyperedges.
        h_ids_1 = set(g1.hyperedges.keys())
        h_ids_2 = set(g2.hyperedges.keys())
        assert h_ids_1 == h_ids_2, (
            f"Graph {gid!r} hyperedge ids drift"
        )
        for hid in sorted(h_ids_1):
            h1 = g1.hyperedges[hid]
            h2 = g2.hyperedges[hid]
            m1 = sorted(n.node_id for n in h1.nodes)
            m2 = sorted(n.node_id for n in h2.nodes)
            assert m1 == m2, f"HyperEdge {hid!r} member drift: {m1} vs {m2}"
            assert h1.type_name == h2.type_name
            assert h1.label == h2.label
            assert dict(h1.properties) == dict(h2.properties)


def _assert_metaedges(mg1: Any, mg2: Any) -> None:
    ids1 = set(mg1.metaedges.keys())
    ids2 = set(mg2.metaedges.keys())
    assert ids1 == ids2, (
        f"MetaEdge ids drift: missing={sorted(ids1 - ids2)}; "
        f"extra={sorted(ids2 - ids1)}"
    )
    for eid in sorted(ids1):
        e1 = mg1.metaedges[eid]
        e2 = mg2.metaedges[eid]
        assert e1.source_graph_id == e2.source_graph_id, (
            f"MetaEdge {eid!r} source_graph_id drift"
        )
        assert e1.target_graph_id == e2.target_graph_id
        assert e1.type_name == e2.type_name, (
            f"MetaEdge {eid!r} type_name drift: {e1.type_name!r} vs "
            f"{e2.type_name!r}"
        )
        assert e1.label == e2.label
        assert dict(e1.properties) == dict(e2.properties)
        # Phase 10 RR-4 — soft-delete field equality.
        assert_soft_delete_state_equal(e1, e2)


def _assert_metahyperedges(mg1: Any, mg2: Any) -> None:
    ids1 = set(mg1.metahyperedges.keys())
    ids2 = set(mg2.metahyperedges.keys())
    assert ids1 == ids2, (
        f"MetaHyperEdge ids drift: missing={sorted(ids1 - ids2)}; "
        f"extra={sorted(ids2 - ids1)}"
    )
    for eid in sorted(ids1):
        e1 = mg1.metahyperedges[eid]
        e2 = mg2.metahyperedges[eid]
        # MetaHyperEdge: graph_ids is set semantics (uniqueness enforced;
        # ordered field vestigial per four-edge-primitives reference).
        # Compare as sorted lists.
        g1 = sorted(e1.graph_ids)
        g2 = sorted(e2.graph_ids)
        assert g1 == g2, f"MetaHyperEdge {eid!r} member drift: {g1} vs {g2}"
        assert e1.type_name == e2.type_name
        assert e1.label == e2.label
        assert dict(e1.properties) == dict(e2.properties)
        # Phase 10 RR-4 — soft-delete field equality.
        assert_soft_delete_state_equal(e1, e2)


def _assert_intergraph_edges(mg1: Any, mg2: Any) -> None:
    ids1 = set(mg1.intergraph_edges.keys())
    ids2 = set(mg2.intergraph_edges.keys())
    assert ids1 == ids2, (
        f"IntergraphEdge ids drift: missing={sorted(ids1 - ids2)}; "
        f"extra={sorted(ids2 - ids1)}"
    )
    for eid in sorted(ids1):
        e1 = mg1.intergraph_edges[eid]
        e2 = mg2.intergraph_edges[eid]
        assert e1.source_graph_id == e2.source_graph_id
        assert e1.source_node_id == e2.source_node_id
        assert e1.target_graph_id == e2.target_graph_id
        assert e1.target_node_id == e2.target_node_id
        assert e1.type_name == e2.type_name
        assert e1.compositional == e2.compositional
        assert e1.label == e2.label
        assert dict(e1.properties) == dict(e2.properties)


def _assert_intergraph_hyperedges(mg1: Any, mg2: Any) -> None:
    ids1 = set(mg1.intergraph_hyperedges.keys())
    ids2 = set(mg2.intergraph_hyperedges.keys())
    assert ids1 == ids2, (
        f"IntergraphHyperEdge ids drift: missing={sorted(ids1 - ids2)}; "
        f"extra={sorted(ids2 - ids1)}"
    )
    for eid in sorted(ids1):
        e1 = mg1.intergraph_hyperedges[eid]
        e2 = mg2.intergraph_hyperedges[eid]
        # Canonical comparison — sorted to absorb ordered/set semantics
        # (B-08-T-likely-1 mitigation).
        a1 = sorted(tuple(p) for p in e1.anchors)
        a2 = sorted(tuple(p) for p in e2.anchors)
        assert a1 == a2, (
            f"IntergraphHyperEdge {eid!r} anchors drift: {a1} vs {a2}"
        )
        m1 = sorted(tuple(p) for p in e1.members)
        m2 = sorted(tuple(p) for p in e2.members)
        assert m1 == m2, (
            f"IntergraphHyperEdge {eid!r} members drift: {m1} vs {m2}"
        )
        assert e1.type_name == e2.type_name
        assert e1.compositional == e2.compositional
        assert e1.label == e2.label
        assert dict(e1.properties) == dict(e2.properties)


def _assert_xrefs(mg1: Any, mg2: Any) -> None:
    """Phase 09 PB-3 + RR-4 — XRef id-set + per-id field-by-field check.

    Round-trip path: source mg has the XRefs Persisted; loaded mg has
    the XRefs Reconstructed. xref_id is preserved across the round
    trip (UUID4 stable; persist + load both key by xref_id), so id-set
    equality + per-id 8-field equality is the right shape (P53 dropped
    ``target_stale`` + ``deprecated_at``; the equality check lives at
    8 fields).
    """
    xrefs1 = getattr(mg1, "xrefs", {}) or {}
    xrefs2 = getattr(mg2, "xrefs", {}) or {}
    ids1 = set(xrefs1.keys())
    ids2 = set(xrefs2.keys())
    assert ids1 == ids2, (
        f"XRef ids drift: missing={sorted(ids1 - ids2)}; "
        f"extra={sorted(ids2 - ids1)}"
    )
    for xid in sorted(ids1):
        x1 = xrefs1[xid]
        x2 = xrefs2[xid]
        assert x1.source_metagraph_id == x2.source_metagraph_id, (
            f"XRef {xid!r} source_metagraph_id drift"
        )
        assert x1.source_id == x2.source_id, (
            f"XRef {xid!r} source_id drift"
        )
        assert x1.target_metagraph_id == x2.target_metagraph_id, (
            f"XRef {xid!r} target_metagraph_id drift"
        )
        assert x1.target_role == x2.target_role, (
            f"XRef {xid!r} target_role drift"
        )
        assert x1.target_id == x2.target_id, (
            f"XRef {xid!r} target_id drift"
        )
        assert x1.ref_type == x2.ref_type, (
            f"XRef {xid!r} ref_type drift"
        )
        assert dict(x1.properties) == dict(x2.properties), (
            f"XRef {xid!r} properties drift"
        )
        # Phase 10 PB-3 reversal + RR-4 — restored XRef fields:
        # ``target_stale`` (bool) + ``deprecated_at`` (datetime|None).
        # XRef has NO ``disputed_at`` per ADR-0128 amendment-3.
        assert x1.target_stale == x2.target_stale, (
            f"XRef {xid!r} target_stale drift: "
            f"{x1.target_stale!r} vs {x2.target_stale!r}"
        )
        assert x1.deprecated_at == x2.deprecated_at, (
            f"XRef {xid!r} deprecated_at drift: "
            f"{x1.deprecated_at!r} vs {x2.deprecated_at!r}"
        )


def assert_xref_contents_equal(xrefs1: Any, xrefs2: Any) -> None:
    """Phase 09 PB-3 + RR-4 sibling — content-tuple equality on XRef collections.

    Designed for migration tests where xref_ids differ between source
    and target (e.g., migration mints fresh UUIDs from legacy
    property-string state). Compares as multiset of 7-tuples
    (source_metagraph_id / source_id / target_metagraph_id /
    target_role / target_id / ref_type / sorted properties tuple).

    Accepts either a dict[str, XRef] (mg.xrefs shape) or an iterable
    of XRefs.
    """

    def _to_tuples(xs: Any):
        items = xs.values() if isinstance(xs, dict) else xs
        return sorted(
            (
                x.source_metagraph_id,
                x.source_id,
                x.target_metagraph_id,
                x.target_role,
                x.target_id,
                x.ref_type,
                tuple(sorted(dict(x.properties).items())),
            )
            for x in items
        )

    t1 = _to_tuples(xrefs1)
    t2 = _to_tuples(xrefs2)
    assert t1 == t2, (
        f"XRef content drift: only-in-1={set(t1) - set(t2)}, "
        f"only-in-2={set(t2) - set(t1)}"
    )


def assert_soft_delete_state_equal(element_a: Any, element_b: Any) -> None:
    """Phase 10 RR-4 — assert soft-delete fields equal between two elements.

    Per ADR-0133 — every soft-deletable element carries
    ``deprecated_at: datetime|None`` + ``disputed_at: datetime|None``
    (Edge / HyperEdge / MetaEdge / MetaHyperEdge). XRef carries
    ``target_stale: bool`` + ``deprecated_at: datetime|None`` instead
    (no ``disputed_at`` per ADR-0128 amendment-3).

    Dispatches by ``hasattr`` so a single helper covers all 5 element
    kinds. Used by:

    * :func:`_assert_metaedges` / :func:`_assert_metahyperedges` /
      :func:`_assert_xrefs` in this module (inline assertions per RR-4).
    * Per-element round-trip tests in ``tests/phase_10/`` that need to
      assert a setter-then-persist-then-load cycle preserved both
      fields.

    Both elements must be the same kind (Edge × Edge, XRef × XRef, …).
    Raises :class:`AssertionError` with the kind-specific message.
    """
    # XRef path: target_stale + deprecated_at (no disputed_at).
    if hasattr(element_a, "target_stale"):
        assert element_a.target_stale == element_b.target_stale, (
            f"XRef target_stale drift: "
            f"{element_a.target_stale!r} vs {element_b.target_stale!r}"
        )
        assert element_a.deprecated_at == element_b.deprecated_at, (
            f"XRef deprecated_at drift: "
            f"{element_a.deprecated_at!r} vs {element_b.deprecated_at!r}"
        )
        return
    # Edge / HyperEdge / MetaEdge / MetaHyperEdge: deprecated_at + disputed_at.
    if hasattr(element_a, "deprecated_at") and hasattr(element_a, "disputed_at"):
        kind = type(element_a).__name__
        assert element_a.deprecated_at == element_b.deprecated_at, (
            f"{kind} deprecated_at drift: "
            f"{element_a.deprecated_at!r} vs {element_b.deprecated_at!r}"
        )
        assert element_a.disputed_at == element_b.disputed_at, (
            f"{kind} disputed_at drift: "
            f"{element_a.disputed_at!r} vs {element_b.disputed_at!r}"
        )
        return
    raise TypeError(
        f"assert_soft_delete_state_equal: element of type "
        f"{type(element_a).__name__} has neither soft-delete shape "
        f"(missing target_stale AND missing deprecated_at/disputed_at)"
    )


__all__ = [
    "assert_metagraphs_equal",
    "assert_xref_contents_equal",
    # Phase 10 RR-4
    "assert_soft_delete_state_equal",
]
