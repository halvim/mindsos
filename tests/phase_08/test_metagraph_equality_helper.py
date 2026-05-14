"""RR-13 A — assert_metagraphs_equal walker (positive + N negatives)."""

from __future__ import annotations

import pytest

from mindsos_core.models.graph import Graph
from mindsos_core.models.identity import IdentityRegistry
from mindsos_core.models.metagraph import Metagraph
from tests._shared.metagraph_equality import assert_metagraphs_equal


def _build_paired_metagraphs() -> tuple[Metagraph, Metagraph]:
    """Two structurally-identical metagraphs (separate id registries)."""
    def _build():
        mg = Metagraph(
            name="m1", identity=IdentityRegistry(), metagraph_id="mg-1"
        )
        g1 = Graph(name="g1", role="lex", identity=mg.identity, graph_id="g-1")
        g2 = Graph(name="g2", role="ont", identity=mg.identity, graph_id="g-2")
        n1 = g1.add_node(
            value="x", type_name="T", node_id="n1", _validate=False
        )
        n2 = g2.add_node(
            value="y", type_name="T", node_id="n2", _validate=False
        )
        mg.add_graph(g1)
        mg.add_graph(g2)
        mg.add_metaedge(
            source_graph_id="g-1",
            target_graph_id="g-2",
            type_name="LINKS_TO",
            edge_id="me-1",
        )
        return mg

    return _build(), _build()


def test_positive_case_identical_metagraphs() -> None:
    """Two structurally identical metagraphs pass the walker."""
    mg1, mg2 = _build_paired_metagraphs()
    assert_metagraphs_equal(mg1, mg2)


def test_negative_anchor_name_mismatch() -> None:
    """Name drift surfaces."""
    mg1, mg2 = _build_paired_metagraphs()
    object.__setattr__(mg2, "name", "different-name")
    with pytest.raises(AssertionError, match="name drift"):
        assert_metagraphs_equal(mg1, mg2)


def test_negative_contained_graph_count_mismatch() -> None:
    """Different graph count surfaces."""
    mg1, mg2 = _build_paired_metagraphs()
    # Add a graph to mg1 only.
    g3 = Graph(name="g3", role="extra", identity=mg1.identity, graph_id="g-3")
    mg1.add_graph(g3)
    with pytest.raises(AssertionError, match="Graphs (missing|extra)"):
        assert_metagraphs_equal(mg1, mg2)


def test_negative_node_set_mismatch() -> None:
    """Node-id set drift inside a contained graph surfaces."""
    mg1, mg2 = _build_paired_metagraphs()
    g1 = list(mg2.graphs.values())[0]
    g1.add_node(value="z", type_name="T", node_id="n-extra", _validate=False)
    with pytest.raises(AssertionError, match="node ids drift"):
        assert_metagraphs_equal(mg1, mg2)


def test_negative_metaedge_id_drift() -> None:
    """MetaEdge id-set drift surfaces."""
    mg1, mg2 = _build_paired_metagraphs()
    # Add an extra metaedge to mg1.
    mg1.add_metaedge(
        source_graph_id="g-2",
        target_graph_id="g-1",
        type_name="REVERSE",
        edge_id="me-extra",
    )
    with pytest.raises(AssertionError, match="MetaEdge ids drift"):
        assert_metagraphs_equal(mg1, mg2)


def test_negative_schema_name_drift() -> None:
    """schema_name drift surfaces."""
    mg1, mg2 = _build_paired_metagraphs()
    mg2.schema_name = "different-schema"
    with pytest.raises(AssertionError, match="schema_name drift"):
        assert_metagraphs_equal(mg1, mg2)
