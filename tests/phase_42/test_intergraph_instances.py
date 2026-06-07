"""Phase 42 — IntergraphEdgeInstance + IntergraphHyperEdgeInstance (ADR-0156/0132).

Phase 06 catalog amendment 8 -> 10. Per PB-15/PB-24 these ship ahead of
their capacity-MM consumer (Phase 46); ``materialise`` is deferred, so the
test scope is the instantiation contract (KIND + structural keys) + the
persistence/reconstruction dispatch wiring, not a materialise round-trip.
"""

from __future__ import annotations

import mindsos_instances
from mindsos_instances import IntergraphEdgeInstance, IntergraphHyperEdgeInstance
from mindsos_instances.reconstruction.instance_loader import _KIND_TO_CLASS


def test_subclasses_exported_from_package():
    assert "IntergraphEdgeInstance" in mindsos_instances.__all__
    assert "IntergraphHyperEdgeInstance" in mindsos_instances.__all__


def test_kind_class_vars():
    assert IntergraphEdgeInstance.KIND == "intergraph_edge"
    assert IntergraphHyperEdgeInstance.KIND == "intergraph_hyperedge"
    assert IntergraphEdgeInstance.FORBIDS_TYPE_NAME is True
    assert IntergraphHyperEdgeInstance.FORBIDS_TYPE_NAME is True


def test_structural_keys():
    assert IntergraphEdgeInstance.STRUCTURAL_KEYS == frozenset(
        {"source_graph_id", "source_node_id", "target_graph_id",
         "target_node_id", "label"}
    )
    assert IntergraphHyperEdgeInstance.STRUCTURAL_KEYS == frozenset(
        {"anchors", "members", "label"}
    )
    assert IntergraphHyperEdgeInstance.SET_TYPED_KEYS == frozenset(
        {"anchors", "members"}
    )


def test_reconstruction_kind_to_class_map_round_trip():
    assert _KIND_TO_CLASS["intergraph_edge"] is IntergraphEdgeInstance
    assert _KIND_TO_CLASS["intergraph_hyperedge"] is IntergraphHyperEdgeInstance


def test_catalog_expanded_to_ten_subclasses():
    from mindsos_instances.models import element_instance as ei

    subclasses = {
        name
        for name in dir(ei)
        if name.endswith("Instance") and name not in {"ElementInstance"}
    }
    # 7 element subclasses + Composite + 2 new intergraph = 10
    assert {"IntergraphEdgeInstance", "IntergraphHyperEdgeInstance"} <= subclasses
    assert len(subclasses) == 10
