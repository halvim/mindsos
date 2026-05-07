"""Phase 05c — replace-only update factory (P10-C) + P19-A 1-1 collapse refusal.

Update path runs steps 1-13 on resolved replacement values; skips steps
14 + 16 (no new id, no register/insert); step 15 modified to setattr
existing edge in-place via object.__setattr__ (factory bypass per P27 A).
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    CompositionalImmutableError,
    Graph,
    IntergraphHyperEdgeType,
    Metagraph,
    MetagraphSchema,
    PropertyShapeError,
    SchemaError,
)


@pytest.fixture
def mg_built():
    mg = Metagraph(name="m")
    g_w = Graph(name="word", role="word")
    g_l = Graph(name="letter", role="letter")
    mg.add_graph(g_w)
    mg.add_graph(g_l)
    g_w.add_node("cat", type_name="Word", node_id="cat")
    g_w.add_node("dog", type_name="Word", node_id="dog")
    g_l.add_node("c", type_name="Letter", node_id="c")
    g_l.add_node("a", type_name="Letter", node_id="a")
    g_l.add_node("t", type_name="Letter", node_id="t")
    g_l.add_node("d", type_name="Letter", node_id="d")
    g_l.add_node("o", type_name="Letter", node_id="o")
    g_l.add_node("g", type_name="Letter", node_id="g")
    return {"mg": mg, "g_w": g_w, "g_l": g_l}


def _make_hyperedge(mg_built, *, compositional: bool = False, properties=None):
    mg = mg_built["mg"]
    g_w = mg_built["g_w"]
    g_l = mg_built["g_l"]
    return mg.add_intergraph_hyperedge(
        anchors=[(g_w.graph_id, "cat")],
        members=[
            (g_l.graph_id, "c"),
            (g_l.graph_id, "a"),
            (g_l.graph_id, "t"),
        ],
        type_name="COMPOSED_OF",
        compositional=compositional,
        properties=properties,
    )


class TestReplaceAnchorsAndMembers:
    def test_replace_anchors(self, mg_built):
        ihe = _make_hyperedge(mg_built)
        original_id = ihe.edge_id
        mg = mg_built["mg"]
        g_w = mg_built["g_w"]
        result = mg.update_intergraph_hyperedge(
            ihe.edge_id,
            anchors=[(g_w.graph_id, "dog")],
        )
        # P29 — edge_id stable across update.
        assert result.edge_id == original_id
        assert result.anchors == ((g_w.graph_id, "dog"),)
        # Members retained when anchors=None passed.
        assert len(result.members) == 3

    def test_replace_members(self, mg_built):
        ihe = _make_hyperedge(mg_built)
        original_id = ihe.edge_id
        mg = mg_built["mg"]
        g_l = mg_built["g_l"]
        new_members = [
            (g_l.graph_id, "d"),
            (g_l.graph_id, "o"),
            (g_l.graph_id, "g"),
        ]
        result = mg.update_intergraph_hyperedge(
            ihe.edge_id, members=new_members,
        )
        assert result.edge_id == original_id
        assert len(result.members) == 3
        assert result.members[0] == (g_l.graph_id, "d")

    def test_replace_both(self, mg_built):
        ihe = _make_hyperedge(mg_built)
        original_id = ihe.edge_id
        mg = mg_built["mg"]
        g_w = mg_built["g_w"]
        g_l = mg_built["g_l"]
        result = mg.update_intergraph_hyperedge(
            ihe.edge_id,
            anchors=[(g_w.graph_id, "dog")],
            members=[(g_l.graph_id, "d"), (g_l.graph_id, "o"), (g_l.graph_id, "g")],
        )
        assert result.edge_id == original_id

    def test_no_args_retains_current(self, mg_built):
        ihe = _make_hyperedge(mg_built)
        original_anchors = ihe.anchors
        original_members = ihe.members
        mg = mg_built["mg"]
        result = mg.update_intergraph_hyperedge(ihe.edge_id)
        assert result.anchors == original_anchors
        assert result.members == original_members


class TestReplaceProperties:
    def test_merge_default(self, mg_built):
        ihe = _make_hyperedge(mg_built, properties={"a": 1})
        mg = mg_built["mg"]
        result = mg.update_intergraph_hyperedge(
            ihe.edge_id, properties={"b": 2},
        )
        # P10-C default — merge.
        assert result.properties == {"a": 1, "b": 2}

    def test_replace_flag(self, mg_built):
        ihe = _make_hyperedge(mg_built, properties={"a": 1})
        mg = mg_built["mg"]
        result = mg.update_intergraph_hyperedge(
            ihe.edge_id, properties={"b": 2}, replace_properties=True,
        )
        assert result.properties == {"b": 2}


class TestP19ACardinalityCollapseRefusal:
    """P19-A — update collapsing to 1-1 cardinality refused."""

    def test_collapse_to_1_1_refused(self, mg_built):
        ihe = _make_hyperedge(mg_built)
        mg = mg_built["mg"]
        g_l = mg_built["g_l"]
        # Update would yield 1 anchor + 1 member.
        with pytest.raises(SchemaError, match="P19-A"):
            mg.update_intergraph_hyperedge(
                ihe.edge_id,
                members=[(g_l.graph_id, "c")],
            )
        # State unchanged — original 3 members preserved.
        assert len(ihe.members) == 3


class TestAtomicRollback:
    def test_validation_failure_leaves_state_unchanged(self, mg_built):
        ihe = _make_hyperedge(mg_built)
        original_anchors = ihe.anchors
        original_members = ihe.members
        original_props = dict(ihe.properties)
        mg = mg_built["mg"]
        # Trigger PropertyShapeError via reserved key.
        with pytest.raises(PropertyShapeError):
            mg.update_intergraph_hyperedge(
                ihe.edge_id,
                properties={"intergraph_hyperedges": "reserved!"},
                replace_properties=True,
            )
        # State unchanged.
        assert ihe.anchors == original_anchors
        assert ihe.members == original_members
        assert ihe.properties == original_props


class TestRefusalOnCompositional:
    def test_compositional_update_refused(self, mg_built):
        ihe = _make_hyperedge(mg_built, compositional=True)
        mg = mg_built["mg"]
        with pytest.raises(CompositionalImmutableError):
            mg.update_intergraph_hyperedge(
                ihe.edge_id, properties={"k": "v"},
            )


class TestUnknownIdRefusal:
    def test_unknown_id_raises(self, mg_built):
        from mindsos_core import IdentityError
        mg = mg_built["mg"]
        with pytest.raises(IdentityError):
            mg.update_intergraph_hyperedge("nonexistent")


class TestUpdateUnderDetachedSchema:
    """P20-A — structural-only validation when no schema attached."""

    def test_structural_pass_no_role_check(self):
        # Build mg + hyperedge under detached schema; update without
        # attached schema should validate structurally only.
        mg = Metagraph(name="m")
        g_a = Graph(name="ga", role="alpha")
        g_b = Graph(name="gb", role="beta")
        mg.add_graph(g_a)
        mg.add_graph(g_b)
        g_a.add_node("a1", type_name="A", node_id="a1")
        g_a.add_node("a2", type_name="A", node_id="a2")
        g_b.add_node("b1", type_name="B", node_id="b1")
        g_b.add_node("b2", type_name="B", node_id="b2")
        ihe = mg.add_intergraph_hyperedge(
            anchors=[(g_a.graph_id, "a1")],
            members=[(g_b.graph_id, "b1"), (g_b.graph_id, "b2")],
            type_name="ANYTYPE",
        )
        # Update with new structurally-valid arrangement; no schema → ok.
        result = mg.update_intergraph_hyperedge(
            ihe.edge_id,
            anchors=[(g_a.graph_id, "a1"), (g_a.graph_id, "a2")],
        )
        assert len(result.anchors) == 2
