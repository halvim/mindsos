"""Phase 46 — materialise round-trip for the two intergraph instance
subclasses (ADR-0166 / PB-24). Capacity-MM instantiation is the first
consumer; this closes the Phase 42 materialise deferral.
"""

from __future__ import annotations

import pytest

from mindsos_core import Graph, Metagraph
from mindsos_core.exceptions import IdentityError
from mindsos_core.models.intergraph_edge import IntergraphEdge
from mindsos_core.models.intergraph_hyperedge import IntergraphHyperEdge
import mindsos_instances as mi


@pytest.fixture
def mg_two_graphs() -> Metagraph:
    out = Metagraph(name="MG_INTERGRAPH")
    mi.attach_registry(out)
    g1 = Graph(name="G1", role="ontology")
    g2 = Graph(name="G2", role="concepts")
    out.add_graph(g1)
    out.add_graph(g2)
    g1.add_node("alice", type_name="Person")
    g2.add_node("widget", type_name="Thing")
    g2.add_node("gadget", type_name="Thing")
    return out


def _ids(mg):
    g1, g2 = mg.graphs.values()
    n1 = next(iter(g1.nodes.values()))
    n2 = next(iter(g2.nodes.values()))
    return g1, g2, n1, n2


def test_intergraph_edge_materialise_round_trip(mg_two_graphs):
    reg = mg_two_graphs.element_registry
    g1, g2, n1, n2 = _ids(mg_two_graphs)
    template = mg_two_graphs.add_intergraph_edge(
        source_graph_id=g1.graph_id,
        source_node_id=n1.node_id,
        target_graph_id=g2.graph_id,
        target_node_id=n2.node_id,
        type_name="PRODUCES",
    )
    inst = mi.IntergraphEdgeInstance(
        metagraph_id=mg_two_graphs.metagraph_id,
        template_id=template.edge_id,
        _registry=reg,
    )
    reg.add(inst)
    result = inst.materialise(mg_two_graphs)
    assert isinstance(result, IntergraphEdge)
    assert result.edge_id != template.edge_id
    assert result.source_graph_id == g1.graph_id
    assert result.source_node_id == n1.node_id
    assert result.target_graph_id == g2.graph_id
    assert result.target_node_id == n2.node_id
    assert result.type_name == "PRODUCES"


def test_intergraph_edge_materialise_label_override(mg_two_graphs):
    reg = mg_two_graphs.element_registry
    g1, g2, n1, n2 = _ids(mg_two_graphs)
    template = mg_two_graphs.add_intergraph_edge(
        source_graph_id=g1.graph_id,
        source_node_id=n1.node_id,
        target_graph_id=g2.graph_id,
        target_node_id=n2.node_id,
        type_name="CONSUMES",
    )
    inst = mi.IntergraphEdgeInstance(
        metagraph_id=mg_two_graphs.metagraph_id,
        template_id=template.edge_id,
        overrides={"label": "custom"},
        _registry=reg,
    )
    reg.add(inst)
    assert inst.materialise(mg_two_graphs).label == "custom"


def test_intergraph_edge_materialise_unknown_endpoint_raises(mg_two_graphs):
    reg = mg_two_graphs.element_registry
    g1, g2, n1, n2 = _ids(mg_two_graphs)
    template = mg_two_graphs.add_intergraph_edge(
        source_graph_id=g1.graph_id,
        source_node_id=n1.node_id,
        target_graph_id=g2.graph_id,
        target_node_id=n2.node_id,
        type_name="PRODUCES",
    )
    inst = mi.IntergraphEdgeInstance(
        metagraph_id=mg_two_graphs.metagraph_id,
        template_id=template.edge_id,
        overrides={"target_node_id": "nonexistent"},
        _registry=reg,
    )
    reg.add(inst)
    with pytest.raises(IdentityError):
        inst.materialise(mg_two_graphs)


def test_intergraph_hyperedge_materialise_round_trip(mg_two_graphs):
    reg = mg_two_graphs.element_registry
    g1, g2, n1, _ = _ids(mg_two_graphs)
    m1, m2 = list(g2.nodes.values())
    anchors = [(g1.graph_id, n1.node_id)]
    members = [(g2.graph_id, m1.node_id), (g2.graph_id, m2.node_id)]
    template = mg_two_graphs.add_intergraph_hyperedge(
        anchors=anchors,
        members=members,
        type_name="COMPOSES",
    )
    inst = mi.IntergraphHyperEdgeInstance(
        metagraph_id=mg_two_graphs.metagraph_id,
        template_id=template.edge_id,
        _registry=reg,
    )
    reg.add(inst)
    result = inst.materialise(mg_two_graphs)
    assert isinstance(result, IntergraphHyperEdge)
    assert result.edge_id != template.edge_id
    assert result.anchors == tuple(anchors)
    assert result.members == tuple(members)
    assert result.type_name == "COMPOSES"
