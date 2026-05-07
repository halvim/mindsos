"""Phase 05c — eager-attach extension (P6-A) walks intergraph_hyperedges.

Metaedges + metahyperedges still skipped (Push9-A from 05b carry-forward;
expires in 05d). Includes empty-vocab attach behavior (P29 (b) coverage
fold per row text + design doc 24-hybrid carry-forward).
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    Graph,
    IntergraphEdgeType,
    IntergraphHyperEdgeType,
    Metagraph,
    MetagraphSchema,
    UnknownTypeError,
)


def _build_mg_with_hyperedge():
    """Build a metagraph with one intergraph hyperedge before any schema."""
    mg = Metagraph(name="m")
    g_w = Graph(name="word", role="word")
    g_l = Graph(name="letter", role="letter")
    mg.add_graph(g_w)
    mg.add_graph(g_l)
    g_w.add_node("cat", type_name="Word", node_id="cat")
    g_l.add_node("c", type_name="Letter", node_id="c")
    g_l.add_node("a", type_name="Letter", node_id="a")
    mg.add_intergraph_hyperedge(
        anchors=[(g_w.graph_id, "cat")],
        members=[(g_l.graph_id, "c"), (g_l.graph_id, "a")],
        type_name="COMPOSED_OF",
    )
    return mg


class TestEagerAttachWalksHyperedges:
    def test_attach_validates_existing_hyperedge_type(self):
        mg = _build_mg_with_hyperedge()
        ms = MetagraphSchema()
        # Schema has no IntergraphHyperEdgeType for COMPOSED_OF → refuse.
        with pytest.raises(UnknownTypeError, match="COMPOSED_OF"):
            mg.attach_schema(ms, schema_name="ms")

    def test_attach_validates_existing_hyperedge_role_match(self):
        mg = _build_mg_with_hyperedge()
        ms = MetagraphSchema()
        # Vocab present but role-restricted to "phrase" — anchor role is
        # "word", so refuse.
        ms.add_intergraph_hyperedge_type(
            IntergraphHyperEdgeType(
                name="COMPOSED_OF",
                allowed_anchor_graphs=frozenset({"phrase"}),
            )
        )
        with pytest.raises(UnknownTypeError, match="anchor graph role"):
            mg.attach_schema(ms, schema_name="ms")

    def test_attach_validates_existing_hyperedge_passes(self):
        mg = _build_mg_with_hyperedge()
        ms = MetagraphSchema()
        ms.add_intergraph_hyperedge_type(
            IntergraphHyperEdgeType(
                name="COMPOSED_OF",
                allowed_anchor_graphs=frozenset({"word"}),
                allowed_member_graphs=frozenset({"letter"}),
            )
        )
        result = mg.attach_schema(ms, schema_name="ms")
        assert result is ms
        assert mg.schema_name == "ms"


class TestMetaedgesStillSkipped:
    """Push9-A from 05b carry-forward — metaedges + metahyperedges NOT walked."""

    def test_metaedge_with_unknown_type_does_not_block_attach(self):
        # 05b precedent — metaedges/metahyperedges aren't validated until 05d.
        mg = Metagraph(name="m")
        g_a = Graph(name="ga", role="r")
        g_b = Graph(name="gb", role="r")
        mg.add_graph(g_a)
        mg.add_graph(g_b)
        # Add a metaedge with an arbitrary type; would fail under 05d
        # but should pass attach in 05c.
        mg.add_metaedge(
            source_graph_id=g_a.graph_id,
            target_graph_id=g_b.graph_id,
            type_name="UNKNOWN_METAEDGE_TYPE",
        )
        ms = MetagraphSchema()
        # Schema has no MetaEdgeType vocab (none ships in 05c).
        # Attach should succeed since metaedges aren't validated.
        result = mg.attach_schema(ms, schema_name="ms")
        assert result is ms


class TestEmptyVocabAttach:
    """P29 (b) coverage — empty IntergraphHyperEdgeType vocab attach behavior."""

    def test_empty_vocab_no_existing_hyperedges_attach_succeeds(self):
        # No hyperedges to validate; empty vocab is fine.
        mg = Metagraph(name="m")
        g_a = Graph(name="ga", role="r")
        mg.add_graph(g_a)
        ms = MetagraphSchema()
        result = mg.attach_schema(ms, schema_name="ms")
        assert result is ms

    def test_empty_vocab_with_existing_hyperedge_fails_strictly(self):
        # Per Pushback 24-hybrid carry-forward — strict mode, pre-existing
        # hyperedge with type_name not in vocab fails attach.
        mg = _build_mg_with_hyperedge()
        ms = MetagraphSchema(strict=True)
        # No IntergraphHyperEdgeType registered.
        with pytest.raises(UnknownTypeError):
            mg.attach_schema(ms, schema_name="ms")

    def test_attach_preserves_state_on_failure(self):
        """Pushback 29-A — atomic precheck contract."""
        mg = _build_mg_with_hyperedge()
        ms = MetagraphSchema()  # empty
        with pytest.raises(UnknownTypeError):
            mg.attach_schema(ms, schema_name="ms")
        # State unchanged.
        assert mg.schema is None
        assert mg.schema_name is None
