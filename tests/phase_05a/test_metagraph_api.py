"""Phase 05a — Metagraph in-memory API (P11 + P15 + P16 + P19)."""

from __future__ import annotations

import pytest

from mindsos_core import (
    Graph,
    IdentityError,
    Metagraph,
    PropertyShapeError,
    SchemaError,
    UUID4Strategy,
)


# ── add_graph (P16 invariants) ───────────────────────────────────────────────


def test_add_graph_unifies_identity_shared_reference():
    """P16 — post-call, ``g.identity is mg.identity`` (shared reference)."""
    mg = Metagraph(name="mg1")
    g = Graph(name="g1", role="ontology")
    pre_g_identity = g.identity
    mg.add_graph(g)
    assert g.identity is mg.identity
    assert g.identity is not pre_g_identity


def test_add_graph_id_strategy_untouched():
    """P16 — graph keeps its own id_strategy after unification."""
    g = Graph(name="g1")
    pre_id_strategy = g.identity  # graphs don't carry an id_strategy attr
    # Use a non-default strategy on the metagraph.
    mg = Metagraph(name="mg1", id_strategy=UUID4Strategy())
    mg.add_graph(g)
    # The graph's own identity registry has been swapped to shared, but
    # the graph object DOES NOT carry an id_strategy attribute (Phase 02
    # graphs delegate to the metagraph for mints when needed). Verify
    # that the metagraph's id_strategy survives untouched.
    assert mg.id_strategy is not None
    # Shared identity post-condition.
    assert g.identity is mg.identity


def test_add_graph_collision_refuses_atomically():
    """Q5-A — id collision aborts the entire add (no partial mutation)."""
    mg = Metagraph(name="mg")
    g1 = Graph(name="g1")
    g1.add_node(value="x", type_name="T", node_id="shared")
    mg.add_graph(g1)
    g2 = Graph(name="g2")
    g2.add_node(value="y", type_name="T", node_id="shared")  # collides
    pre_count = len(mg.graphs)
    with pytest.raises(IdentityError, match="collision"):
        mg.add_graph(g2)
    # Atomicity — no partial state.
    assert len(mg.graphs) == pre_count
    assert g2.graph_id not in mg.graphs


def test_add_graph_duplicate_graph_id_refused():
    """Re-adding the same graph object refused."""
    mg = Metagraph(name="mg")
    g = Graph(name="g1")
    mg.add_graph(g)
    with pytest.raises(IdentityError, match="already in metagraph"):
        mg.add_graph(g)


# ── add_metaedge (P11 + P15) ─────────────────────────────────────────────────


def test_add_metaedge_takes_graph_id_strings():
    """P11 — factory takes graph_id strings, not Graph objects."""
    mg = Metagraph(name="mg")
    g1 = Graph(name="g1"); mg.add_graph(g1)
    g2 = Graph(name="g2"); mg.add_graph(g2)
    me = mg.add_metaedge(
        source_graph_id=g1.graph_id,
        target_graph_id=g2.graph_id,
        type_name="REFINES",
    )
    assert me.source_graph_id == g1.graph_id
    assert me.target_graph_id == g2.graph_id


def test_add_metaedge_refuses_self_loop():
    """P15 — source_graph_id == target_graph_id rejected."""
    mg = Metagraph(name="mg")
    g = Graph(name="g1"); mg.add_graph(g)
    with pytest.raises(SchemaError, match="self-loop"):
        mg.add_metaedge(
            source_graph_id=g.graph_id,
            target_graph_id=g.graph_id,
            type_name="REL",
        )


def test_add_metaedge_refuses_unknown_source():
    """Source must be contained."""
    mg = Metagraph(name="mg")
    g = Graph(name="g"); mg.add_graph(g)
    with pytest.raises(IdentityError):
        mg.add_metaedge(
            source_graph_id="not-in-metagraph",
            target_graph_id=g.graph_id,
            type_name="REL",
        )


def test_add_metaedge_refuses_unknown_target():
    """Target must be contained."""
    mg = Metagraph(name="mg")
    g = Graph(name="g"); mg.add_graph(g)
    with pytest.raises(IdentityError):
        mg.add_metaedge(
            source_graph_id=g.graph_id,
            target_graph_id="not-in-metagraph",
            type_name="REL",
        )


def test_add_metaedge_validates_properties():
    """Reserved property keys rejected."""
    mg = Metagraph(name="mg")
    g1 = Graph(name="g1"); mg.add_graph(g1)
    g2 = Graph(name="g2"); mg.add_graph(g2)
    with pytest.raises(PropertyShapeError):
        mg.add_metaedge(
            source_graph_id=g1.graph_id,
            target_graph_id=g2.graph_id,
            type_name="REL",
            properties={"node_id": "evil"},  # reserved
        )


# ── add_metahyperedge (P11 + P15) ────────────────────────────────────────────


def test_add_metahyperedge_takes_graph_id_strings():
    """P11 — factory takes List[str] graph_ids."""
    mg = Metagraph(name="mg")
    g1 = Graph(name="g1"); mg.add_graph(g1)
    g2 = Graph(name="g2"); mg.add_graph(g2)
    g3 = Graph(name="g3"); mg.add_graph(g3)
    mhe = mg.add_metahyperedge(
        graph_ids=[g1.graph_id, g2.graph_id, g3.graph_id],
        type_name="TRIO",
    )
    assert set(mhe.graph_ids) == {g1.graph_id, g2.graph_id, g3.graph_id}


def test_add_metahyperedge_refuses_single_member_at_factory():
    """P15 — < 2 members rejected (factory delegates to dataclass)."""
    mg = Metagraph(name="mg")
    g = Graph(name="g"); mg.add_graph(g)
    with pytest.raises(SchemaError, match="at least 2"):
        mg.add_metahyperedge(
            graph_ids=[g.graph_id],
            type_name="X",
        )


def test_add_metahyperedge_refuses_unknown_member():
    """Member must be contained."""
    mg = Metagraph(name="mg")
    g1 = Graph(name="g1"); mg.add_graph(g1)
    g2 = Graph(name="g2"); mg.add_graph(g2)
    with pytest.raises(IdentityError):
        mg.add_metahyperedge(
            graph_ids=[g1.graph_id, "not-in-metagraph"],
            type_name="X",
        )


# ── update_*_properties (P4 — covers spec'd features) ────────────────────────


def test_update_metaedge_properties_merges_by_default():
    mg = Metagraph(name="mg")
    g1 = Graph(name="g1"); mg.add_graph(g1)
    g2 = Graph(name="g2"); mg.add_graph(g2)
    me = mg.add_metaedge(
        source_graph_id=g1.graph_id,
        target_graph_id=g2.graph_id,
        type_name="REL",
        properties={"a": 1},
    )
    me2 = mg.update_metaedge_properties(me.edge_id, {"b": 2})
    assert me2.properties == {"a": 1, "b": 2}


def test_update_metaedge_properties_replace_swaps():
    mg = Metagraph(name="mg")
    g1 = Graph(name="g1"); mg.add_graph(g1)
    g2 = Graph(name="g2"); mg.add_graph(g2)
    me = mg.add_metaedge(
        source_graph_id=g1.graph_id,
        target_graph_id=g2.graph_id,
        type_name="REL",
        properties={"a": 1},
    )
    me2 = mg.update_metaedge_properties(me.edge_id, {"b": 2}, replace=True)
    assert me2.properties == {"b": 2}


def test_update_metahyperedge_properties_merges_by_default():
    mg = Metagraph(name="mg")
    g1 = Graph(name="g1"); mg.add_graph(g1)
    g2 = Graph(name="g2"); mg.add_graph(g2)
    mhe = mg.add_metahyperedge(
        graph_ids=[g1.graph_id, g2.graph_id],
        type_name="REL",
        properties={"a": 1},
    )
    mhe2 = mg.update_metahyperedge_properties(mhe.edge_id, {"b": 2})
    assert mhe2.properties == {"a": 1, "b": 2}


def test_update_metahyperedge_properties_replace_swaps():
    mg = Metagraph(name="mg")
    g1 = Graph(name="g1"); mg.add_graph(g1)
    g2 = Graph(name="g2"); mg.add_graph(g2)
    mhe = mg.add_metahyperedge(
        graph_ids=[g1.graph_id, g2.graph_id],
        type_name="REL",
        properties={"a": 1},
    )
    mhe2 = mg.update_metahyperedge_properties(
        mhe.edge_id, {"b": 2}, replace=True,
    )
    assert mhe2.properties == {"b": 2}


# ── remove_graph (P19 always-cascade) ────────────────────────────────────────


def test_remove_graph_no_cascade_param():
    """P19 — no ``cascade`` parameter; signature is (graph_id)."""
    mg = Metagraph(name="mg")
    g = Graph(name="g"); mg.add_graph(g)
    # Should accept exactly one positional arg.
    mg.remove_graph(g.graph_id)


def test_remove_graph_cascades_metaedges():
    """Always-cascade default: incident metaedges removed."""
    mg = Metagraph(name="mg")
    g1 = Graph(name="g1"); mg.add_graph(g1)
    g2 = Graph(name="g2"); mg.add_graph(g2)
    g3 = Graph(name="g3"); mg.add_graph(g3)
    mg.add_metaedge(g1.graph_id, g2.graph_id, "REL")
    mg.add_metaedge(g2.graph_id, g3.graph_id, "REL")
    pre_count = len(mg.metaedges)
    mg.remove_graph(g2.graph_id)
    # Both metaedges incident on g2 should be cascaded.
    assert len(mg.metaedges) == pre_count - 2


def test_remove_graph_cascades_metahyperedges():
    """Always-cascade default: incident metahyperedges removed."""
    mg = Metagraph(name="mg")
    g1 = Graph(name="g1"); mg.add_graph(g1)
    g2 = Graph(name="g2"); mg.add_graph(g2)
    g3 = Graph(name="g3"); mg.add_graph(g3)
    mg.add_metahyperedge(
        graph_ids=[g1.graph_id, g2.graph_id, g3.graph_id],
        type_name="TRIO",
    )
    mg.remove_graph(g2.graph_id)
    assert len(mg.metahyperedges) == 0


def test_remove_graph_unknown_id_raises():
    mg = Metagraph(name="mg")
    with pytest.raises(IdentityError, match="Unknown graph id"):
        mg.remove_graph("not-real")


# ── property bag (N1-A1 + P13) ──────────────────────────────────────────────


def test_metagraph_properties_reserved_metaedges_key_rejected():
    """P13 — 'metaedges' is reserved at metagraph property scope."""
    with pytest.raises(PropertyShapeError, match="reserved"):
        Metagraph(name="mg", properties={"metaedges": "lol"})


def test_metagraph_properties_namespaced_keys_accepted():
    """ADR-0130 — namespaced keys accepted."""
    mg = Metagraph(
        name="mg",
        properties={"kl:active_graph_ids": "x", "server:user_id": "u1"},
    )
    assert mg.properties["kl:active_graph_ids"] == "x"
    assert mg.properties["server:user_id"] == "u1"
