"""Phase 14 — ``MetagraphView.step()`` returns within-view edges only.

Per Phase 14 PB-10 lock: NO Local-specialisation overlay (v3's
WalkResult contradicted §1.2). Phase 14 PB-15 lock: NO ``version=``
kwarg.

Covers:

* Step returns edges where the node is source or target (Phase 10
  ``get_edges_for_node`` semantics).
* ``edge_type`` filter.
* ``include_deprecated`` filter (ADR-0133).
* Step result is a plain list of Edges; no WalkResult overlay shape.
"""

from __future__ import annotations

from mindsos_knowledge import KnowledgeLayer, ROLE_ONTOLOGY


def _kl_with_ontology_chain():
    """Build a KL with a 3-node 2-edge chain in the ontology role-graph.

    A → (SUBCLASS_OF) → B → (SUBCLASS_OF) → C.
    """
    kl = KnowledgeLayer.bootstrap()
    ontology = kl.global_view().graphs_by_role(ROLE_ONTOLOGY)[0]
    a = ontology.add_node(value="A", type_name="Class")
    b = ontology.add_node(value="B", type_name="Class")
    c = ontology.add_node(value="C", type_name="Class")
    e_ab = ontology.add_edge(source=a, target=b, type_name="SUBCLASS_OF")
    e_bc = ontology.add_edge(source=b, target=c, type_name="SUBCLASS_OF")
    return kl, a, b, c, e_ab, e_bc


def test_step_returns_incident_edges() -> None:
    """B is in two edges; step on B returns both."""
    kl, a, b, c, e_ab, e_bc = _kl_with_ontology_chain()
    edges = kl.global_view().step(ROLE_ONTOLOGY, b.node_id)
    edge_ids = {e.edge_id for e in edges}
    assert edge_ids == {e_ab.edge_id, e_bc.edge_id}


def test_step_no_edges_for_isolated_node() -> None:
    """A node with no incident edges returns empty list."""
    kl = KnowledgeLayer.bootstrap()
    ontology = kl.global_view().graphs_by_role(ROLE_ONTOLOGY)[0]
    iso = ontology.add_node(value="iso", type_name="Class")
    assert kl.global_view().step(ROLE_ONTOLOGY, iso.node_id) == []


def test_step_edge_type_filter() -> None:
    """``edge_type`` kwarg narrows results."""
    kl, a, b, c, e_ab, e_bc = _kl_with_ontology_chain()
    ontology = kl.global_view().graphs_by_role(ROLE_ONTOLOGY)[0]
    # Add a different-typed edge from B.
    d = ontology.add_node(value="D", type_name="Class")
    e_bd = ontology.add_edge(source=b, target=d, type_name="DISJOINT_WITH")
    # Filter by SUBCLASS_OF — should NOT include e_bd (DISJOINT_WITH).
    edges = kl.global_view().step(
        ROLE_ONTOLOGY, b.node_id, edge_type="SUBCLASS_OF"
    )
    edge_ids = {e.edge_id for e in edges}
    assert e_bd.edge_id not in edge_ids
    assert {e_ab.edge_id, e_bc.edge_id} <= edge_ids


def test_step_default_excludes_deprecated() -> None:
    """ADR-0133 — default ``include_deprecated=False``."""
    kl, a, b, c, e_ab, e_bc = _kl_with_ontology_chain()
    ontology = kl.global_view().graphs_by_role(ROLE_ONTOLOGY)[0]
    ontology.deprecate_edge(e_ab.edge_id)
    edges = kl.global_view().step(ROLE_ONTOLOGY, b.node_id)
    edge_ids = {e.edge_id for e in edges}
    assert e_ab.edge_id not in edge_ids
    assert e_bc.edge_id in edge_ids


def test_step_include_deprecated_true_returns_deprecated() -> None:
    """``include_deprecated=True`` re-surfaces soft-deleted edges."""
    kl, a, b, c, e_ab, e_bc = _kl_with_ontology_chain()
    ontology = kl.global_view().graphs_by_role(ROLE_ONTOLOGY)[0]
    ontology.deprecate_edge(e_ab.edge_id)
    edges = kl.global_view().step(
        ROLE_ONTOLOGY, b.node_id, include_deprecated=True
    )
    edge_ids = {e.edge_id for e in edges}
    assert e_ab.edge_id in edge_ids


def test_step_returns_list_of_edges_not_walkresult() -> None:
    """Phase 14 PB-10 — return type is list[Edge], no WalkResult overlay.

    v3's `step` returned `list[WalkResult]` with `local_specialisation`
    overlay. Phase 14 drops this — the type is just `list[Edge]`.
    """
    kl, a, b, c, e_ab, e_bc = _kl_with_ontology_chain()
    edges = kl.global_view().step(ROLE_ONTOLOGY, b.node_id)
    for e in edges:
        # No WalkResult attributes.
        assert not hasattr(e, "local_specialisation")
        assert not hasattr(e, "target_role")  # WalkResult-only field


def test_step_no_version_kwarg() -> None:
    """Phase 14 PB-15 + ADR-0150 §amendment-3 — `version=` kwarg is permanently absent.

    Phase 17 retirement (2026-05-20) vacated PB-15: the shipped
    one-graph-per-role invariant leaves "active version" undefined,
    so the kwarg was never added. ADR-0150 §amendment-3 locks the
    model. The retirement sentinel in
    `tests/phase_17/test_retirement_sentinels.py` is the canonical
    enforcer; this test is the Phase 14-vintage call site.
    """
    import inspect

    from mindsos_knowledge import MetagraphView

    sig = inspect.signature(MetagraphView.step)
    assert "version" not in sig.parameters, (
        "ADR-0150 §amendment-3 lock — MetagraphView.step ships "
        "without `version=` kwarg. Phase 14 PB-15 carry-forward "
        "was vacated at Phase 17 retirement, not amended."
    )


def test_step_no_overlay_kwarg() -> None:
    """Phase 14 PB-10 — no `overlay_local=` or `with_specialisation=` kwarg."""
    import inspect

    from mindsos_knowledge import MetagraphView

    sig = inspect.signature(MetagraphView.step)
    forbidden = {"overlay_local", "with_specialisation",
                 "with_overlay", "local_user_id"}
    for fname in forbidden:
        assert fname not in sig.parameters, (
            f"Phase 14 PB-10 lock — step ships without overlay; "
            f"`{fname}` kwarg detected."
        )
