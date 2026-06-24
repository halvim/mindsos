"""Phase 14 — ``MetagraphView`` read-only whitelist wrapper.

Per Phase 14 PB-3 lock: wrapper class; NOT a subclass of Metagraph.

Covers:

* Identity accessors (metagraph_id, metagraph_name).
* ``roles()`` returns distinct contained-graph roles.
* ``graphs_by_role`` returns matches; empty list on miss.
* ``alignment_graph`` finds an ensured pair; None on miss.
* ``get_node`` / ``iter_nodes`` / ``get_edges``.
* Absence of write methods on the wrapper (structural enforcement).
* ``__repr__`` shape.
"""

from __future__ import annotations

from mindsos_core import Metagraph, Node

from mindsos_knowledge import (
    KnowledgeLayer,
    MetagraphView,
    ROLE_LEXICON,
    ROLE_ONTOLOGY,
    ensure_global_role_graph,
)


def _bootstrapped_view() -> MetagraphView:
    kl = KnowledgeLayer.bootstrap()
    return kl.global_view()


def test_metagraph_view_identity_accessors() -> None:
    """metagraph_id + metagraph_name surface through the wrapper."""
    kl = KnowledgeLayer.bootstrap()
    view = kl.global_view()
    g = kl.global_metagraph()
    assert view.metagraph_id == g.metagraph_id
    assert view.metagraph_name == g.name


def test_metagraph_view_roles_returns_distinct_roles() -> None:
    """``roles()`` reflects the bootstrapped 11 Global named roles
    (Phase 43 §am-5 + Phase 50 §am-6 + feat/subminds §am-7)."""
    view = _bootstrapped_view()
    assert len(view.roles()) == 11
    assert ROLE_ONTOLOGY in view.roles()
    assert ROLE_LEXICON in view.roles()


def test_metagraph_view_graphs_by_role_match() -> None:
    """``graphs_by_role`` returns the role-graph(s) matching the role."""
    kl = KnowledgeLayer.bootstrap()
    view = kl.global_view()
    matches = view.graphs_by_role(ROLE_ONTOLOGY)
    assert len(matches) == 1
    assert matches[0].role == ROLE_ONTOLOGY


def test_metagraph_view_graphs_by_role_empty_on_miss() -> None:
    """No match → empty list, not error."""
    view = _bootstrapped_view()
    assert view.graphs_by_role("nonexistent-role") == []


def test_metagraph_view_alignment_graph_present() -> None:
    """``alignment_graph(a, b)`` finds an ensured pair."""
    kl = KnowledgeLayer.bootstrap()
    ensure_global_role_graph(
        kl.global_metagraph(), "alignment:ontology:lexicon"
    )
    view = kl.global_view()
    g = view.alignment_graph("ontology", "lexicon")
    assert g is not None
    assert g.role == "alignment:ontology:lexicon"


def test_metagraph_view_alignment_graph_missing_returns_none() -> None:
    """``alignment_graph`` returns None on miss; doesn't auto-create."""
    view = _bootstrapped_view()
    assert view.alignment_graph("ontology", "lexicon") is None


def test_metagraph_view_alignment_pair_order_matters() -> None:
    """The pair ``a:b`` is distinct from ``b:a`` (ordered)."""
    kl = KnowledgeLayer.bootstrap()
    ensure_global_role_graph(
        kl.global_metagraph(), "alignment:ontology:lexicon"
    )
    view = kl.global_view()
    assert view.alignment_graph("ontology", "lexicon") is not None
    assert view.alignment_graph("lexicon", "ontology") is None


def test_metagraph_view_get_node_returns_existing() -> None:
    """``get_node`` reaches into the role-graph's nodes dict."""
    kl = KnowledgeLayer.bootstrap()
    ontology = kl.global_view().graphs_by_role(ROLE_ONTOLOGY)[0]
    # Add a node directly via L1 (PB-16: reference + convention).
    n = ontology.add_node(value="Object", type_name="Class")
    view = kl.global_view()
    found = view.get_node(ROLE_ONTOLOGY, n.node_id)
    assert found is n


def test_metagraph_view_get_node_missing_returns_none() -> None:
    """Miss → None, not error."""
    view = _bootstrapped_view()
    assert view.get_node(ROLE_ONTOLOGY, "no-such-id") is None
    assert view.get_node("no-such-role", "no-such-id") is None


def test_metagraph_view_iter_nodes_yields_role_nodes() -> None:
    """``iter_nodes`` walks the role-graph's nodes."""
    kl = KnowledgeLayer.bootstrap()
    ontology = kl.global_view().graphs_by_role(ROLE_ONTOLOGY)[0]
    ontology.add_node(value="A", type_name="Class")
    ontology.add_node(value="B", type_name="Class")
    view = kl.global_view()
    nodes = list(view.iter_nodes(ROLE_ONTOLOGY))
    assert len(nodes) == 2


def test_metagraph_view_iter_nodes_type_filter() -> None:
    """``iter_nodes(role, type_=...)`` filters by node type."""
    kl = KnowledgeLayer.bootstrap()
    ontology = kl.global_view().graphs_by_role(ROLE_ONTOLOGY)[0]
    ontology.add_node(value="A", type_name="Class")
    ontology.add_node(value="B", type_name="Class")
    view = kl.global_view()
    matched = list(view.iter_nodes(ROLE_ONTOLOGY, type_="Class"))
    assert len(matched) == 2
    unmatched = list(view.iter_nodes(ROLE_ONTOLOGY, type_="Individual"))
    assert unmatched == []


def test_metagraph_view_no_isinstance_of_metagraph() -> None:
    """PB-3 lock — MetagraphView is NOT a subclass of Metagraph."""
    view = _bootstrapped_view()
    assert not isinstance(view, Metagraph)


def test_metagraph_view_no_public_write_methods() -> None:
    """PB-3 + ADR-0138 — the wrapper has no add_/remove_/update_ methods."""
    view = _bootstrapped_view()
    forbidden = {"add_node", "add_edge", "add_hyperedge", "add_graph",
                 "remove_graph", "add_xref", "remove_xref",
                 "attach_schema", "update_metaedge_properties"}
    for fname in forbidden:
        assert not hasattr(view, fname), (
            f"MetagraphView exposes forbidden write method {fname!r}; "
            f"violates Phase 14 PB-3 lock."
        )


def test_metagraph_view_repr_includes_metagraph_id() -> None:
    """``__repr__`` shape — includes metagraph_id + role list."""
    view = _bootstrapped_view()
    r = repr(view)
    assert "MetagraphView(" in r
    assert "metagraph_id=" in r
    assert "roles=" in r


def test_metagraph_view_over_local() -> None:
    """``local_view(user_id)`` works symmetrically with global_view."""
    kl = KnowledgeLayer.bootstrap()
    view = kl.local_view("alice")
    assert "alice" in view.metagraph_name
    assert len(view.roles()) == 5  # episodic_memories + capacity-state + 3 Phase 43 dual-scope
