"""Phase 05d — schema state file v=3 round-trip + serialization tests.

Locks the v=3 wire format: ``meta_edge_types`` + ``meta_hyperedge_types``
arrays, byte-stable sorted by ``name``; per-type frozensets serialized
as sorted lists; PropertyType serialized as ``.value`` string.
"""

from __future__ import annotations

import pytest

from mindsos_cli import state as state_mod
from mindsos_cli.commands.metagraph import (
    _metagraph_schema_to_state,
    _state_to_metagraph_schema,
)
from mindsos_core import (
    MetaEdgeType,
    MetaHyperEdgeType,
    MetagraphSchema,
    PropertyType,
)


class TestSerialize:
    def test_serialize_minimal_schema(self):
        ms = MetagraphSchema()
        state = _metagraph_schema_to_state(ms, name="ms")
        assert state["_state_version"] == 3
        assert state["meta_edge_types"] == []
        assert state["meta_hyperedge_types"] == []

    def test_serialize_meta_edge_type_full(self):
        ms = MetagraphSchema()
        ms.add_meta_edge_type(MetaEdgeType(
            name="REFERENCES",
            allowed_source_graphs=frozenset({"ontology"}),
            allowed_target_graphs=frozenset({"lexicon", "concepts"}),
            property_types={"weight": PropertyType.FLOAT},
            description="Test description.",
        ))
        state = _metagraph_schema_to_state(ms, name="ms")
        assert len(state["meta_edge_types"]) == 1
        met_dict = state["meta_edge_types"][0]
        assert met_dict["name"] == "REFERENCES"
        assert met_dict["allowed_source_graphs"] == ["ontology"]
        assert met_dict["allowed_target_graphs"] == ["concepts", "lexicon"]
        assert met_dict["property_types"] == {"weight": "float"}
        assert met_dict["description"] == "Test description."

    def test_serialize_meta_hyperedge_type_full(self):
        ms = MetagraphSchema()
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(
            name="UNIFIES",
            allowed_member_graphs=frozenset({"ontology", "lexicon"}),
            property_types={"strength": PropertyType.FLOAT},
            description="Cross-domain.",
        ))
        state = _metagraph_schema_to_state(ms, name="ms")
        assert len(state["meta_hyperedge_types"]) == 1
        mht_dict = state["meta_hyperedge_types"][0]
        # NO ordered field in serialized shape per P1 C.
        assert "ordered" not in mht_dict
        assert mht_dict["allowed_member_graphs"] == ["lexicon", "ontology"]

    def test_byte_stable_sort(self):
        ms = MetagraphSchema()
        # Insert in reverse alphabetical order.
        ms.add_meta_edge_type(MetaEdgeType(name="ZULU"))
        ms.add_meta_edge_type(MetaEdgeType(name="ALPHA"))
        ms.add_meta_edge_type(MetaEdgeType(name="MIKE"))
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(name="YYY"))
        ms.add_meta_hyperedge_type(MetaHyperEdgeType(name="AAA"))
        state = _metagraph_schema_to_state(ms, name="ms")
        names_me = [d["name"] for d in state["meta_edge_types"]]
        names_mh = [d["name"] for d in state["meta_hyperedge_types"]]
        assert names_me == ["ALPHA", "MIKE", "ZULU"]
        assert names_mh == ["AAA", "YYY"]


class TestRehydrate:
    def test_rehydrate_minimal(self):
        state = {
            "_state_version": 3,
            "name": "ms",
            "strict": False,
            "intergraph_edge_types": [],
            "intergraph_hyperedge_types": [],
            "meta_edge_types": [],
            "meta_hyperedge_types": [],
        }
        ms = _state_to_metagraph_schema(state)
        assert len(ms.meta_edge_types) == 0
        assert len(ms.meta_hyperedge_types) == 0

    def test_rehydrate_meta_edge_type(self):
        state = {
            "_state_version": 3,
            "name": "ms",
            "strict": False,
            "intergraph_edge_types": [],
            "intergraph_hyperedge_types": [],
            "meta_edge_types": [
                {
                    "name": "X",
                    "allowed_source_graphs": ["ontology"],
                    "allowed_target_graphs": ["lexicon"],
                    "property_types": {"weight": "float"},
                    "description": "desc",
                },
            ],
            "meta_hyperedge_types": [],
        }
        ms = _state_to_metagraph_schema(state)
        met = ms.require_meta_edge_type("X")
        assert met.allowed_source_graphs == frozenset({"ontology"})
        assert met.allowed_target_graphs == frozenset({"lexicon"})
        assert met.property_types == {"weight": PropertyType.FLOAT}
        assert met.description == "desc"

    def test_rehydrate_meta_hyperedge_type(self):
        state = {
            "_state_version": 3,
            "name": "ms",
            "strict": False,
            "intergraph_edge_types": [],
            "intergraph_hyperedge_types": [],
            "meta_edge_types": [],
            "meta_hyperedge_types": [
                {
                    "name": "Y",
                    "allowed_member_graphs": ["ontology", "lexicon"],
                    "property_types": {"strength": "float"},
                    "description": "test",
                },
            ],
        }
        ms = _state_to_metagraph_schema(state)
        mht = ms.require_meta_hyperedge_type("Y")
        assert mht.allowed_member_graphs == frozenset({"ontology", "lexicon"})
        assert mht.description == "test"

    def test_rehydrate_invalid_property_type_raises(self):
        state = {
            "_state_version": 3,
            "name": "ms",
            "strict": False,
            "intergraph_edge_types": [],
            "intergraph_hyperedge_types": [],
            "meta_edge_types": [
                {
                    "name": "X",
                    "allowed_source_graphs": [],
                    "allowed_target_graphs": [],
                    "property_types": {"weight": "not_a_property_type"},
                    "description": None,
                },
            ],
            "meta_hyperedge_types": [],
        }
        with pytest.raises(RuntimeError, match="unrecognised PropertyType"):
            _state_to_metagraph_schema(state)


class TestRoundTrip:
    def test_round_trip_preserves_meta_vocab(self):
        ms_in = MetagraphSchema(strict=True)
        ms_in.add_meta_edge_type(MetaEdgeType(
            name="LINKS_TO",
            allowed_source_graphs=frozenset({"ontology"}),
            allowed_target_graphs=frozenset({"lexicon"}),
            property_types={"weight": PropertyType.FLOAT},
            description="d1",
        ))
        ms_in.add_meta_hyperedge_type(MetaHyperEdgeType(
            name="GROUPS",
            allowed_member_graphs=frozenset({"a", "b", "c"}),
            property_types={"strength": PropertyType.FLOAT},
            description="d2",
        ))
        state = _metagraph_schema_to_state(ms_in, name="ms")
        ms_out = _state_to_metagraph_schema(state)
        assert ms_out.strict is True
        met = ms_out.require_meta_edge_type("LINKS_TO")
        assert met.allowed_source_graphs == frozenset({"ontology"})
        assert met.allowed_target_graphs == frozenset({"lexicon"})
        assert met.property_types == {"weight": PropertyType.FLOAT}
        assert met.description == "d1"
        mht = ms_out.require_meta_hyperedge_type("GROUPS")
        assert mht.allowed_member_graphs == frozenset({"a", "b", "c"})
