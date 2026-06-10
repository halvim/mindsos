"""Phase 50 (SA-1) — ADR-0182 node-value serialization implementation.

Replaces the MAINTENANCE_CHAT M3 sentinel
(``tests/maintenance/test_adr_0182_sentinel.py``, deleted this phase)
with behavior coverage: codec unit tests, builder SET-clause emission,
repository row assembly, loader decode, and reserved-key roster
membership. The live save→load round-trip rides
``tests/maintenance/test_l0_25_falkor_local_persister_live.py``
(structured-value case added this phase per ADR-0182 §Consequences).
"""

from __future__ import annotations

import json

import pytest

from mindsos_core.cypher.builders import build_unwind_create_nodes
from mindsos_core.exceptions import PersistenceError
from mindsos_core.persistence.client import InMemoryClient
from mindsos_core.persistence.graph_repository import GraphRepository
from mindsos_core.persistence.value_codec import (
    decode_node_value,
    encode_node_value,
)
from mindsos_core.reconstruction.graph_loader import (
    _CORE_KEYS,
    _add_node_from_row,
)
from mindsos_core.schema.validation import RESERVED_PROPERTY_KEYS


# ── codec: encode (rules 1, 2, 4) ──────────────────────────────────────


class TestEncodeNodeValue:
    @pytest.mark.parametrize("value", ["s", 1, 1.5, True, False, None])
    def test_primitives_pass_through(self, value) -> None:
        assert encode_node_value(value) == (value, None)

    def test_dict_encodes_canonical(self) -> None:
        value, value_json = encode_node_value({"b": 2, "a": [1, None, "x"]})
        assert value is None
        assert value_json == '{"a":[1,null,"x"],"b":2}'

    def test_list_encodes(self) -> None:
        value, value_json = encode_node_value([1, "two", {"three": 3}])
        assert value is None
        assert json.loads(value_json) == [1, "two", {"three": 3}]

    def test_empty_containers_encode(self) -> None:
        assert encode_node_value({}) == (None, "{}")
        assert encode_node_value([]) == (None, "[]")

    def test_non_encodable_interior_raises(self) -> None:
        with pytest.raises(PersistenceError):
            encode_node_value({"bad": object()})

    def test_non_primitive_non_container_raises(self) -> None:
        with pytest.raises(PersistenceError):
            encode_node_value(object())


# ── codec: decode (rule 3) ─────────────────────────────────────────────


class TestDecodeNodeValue:
    @pytest.mark.parametrize("raw", ["s", 1, 1.5, True, None])
    def test_fast_path_passes_raw_through(self, raw) -> None:
        assert decode_node_value(raw, None) == raw

    def test_value_json_is_the_discriminator(self) -> None:
        assert decode_node_value(None, '{"a":1}') == {"a": 1}
        assert decode_node_value("ignored", '[1,2]') == [1, 2]

    @pytest.mark.parametrize(
        "structured",
        [
            {"b": 2, "a": [1, None, "x"]},
            [1, "two", {"three": 3}],
            {},
            [],
            {"nested": {"deep": [True, False, None, 1.5]}},
        ],
    )
    def test_encode_decode_round_trip(self, structured) -> None:
        value, value_json = encode_node_value(structured)
        assert decode_node_value(value, value_json) == structured

    def test_corrupt_json_raises(self) -> None:
        with pytest.raises(PersistenceError):
            decode_node_value(None, "{not json")


# ── builder: SET clause emission (rule 2) ──────────────────────────────


class TestBuilderEmitsValueJson:
    def test_set_clause_carries_both_columns(self) -> None:
        q, p = build_unwind_create_nodes(
            "g1",
            [{
                "id": "n1",
                "type_name": "Episode",
                "value": None,
                "_value_json": '{"a":1}',
                "props": {},
                "_version": 1,
            }],
        )
        assert "n.value = row.value" in q
        assert "n._value_json = row._value_json" in q
        assert p["rows"][0]["_value_json"] == '{"a":1}'


# ── repository: row assembly (the ADR's named caller surface) ─────────


def _persist_single_node(value):
    from mindsos_core.models.graph import Graph

    client = InMemoryClient()
    g = Graph(name="codec-test", role="episodic_memories")
    node = g.add_node(value, "Episode")
    GraphRepository(client).persist(g)
    unwind_calls = [
        (q, params) for q, params in client.calls if "UNWIND" in q and ":Node" in q
    ]
    assert len(unwind_calls) == 1
    return node, unwind_calls[0][1]["rows"]


class TestRepositoryRowAssembly:
    def test_structured_value_splits_into_pair(self) -> None:
        structured = {"roster": ["a", "b"], "outcome": "ok"}
        node, rows = _persist_single_node(structured)
        (row,) = rows
        assert row["id"] == node.node_id
        assert row["value"] is None
        assert json.loads(row["_value_json"]) == structured

    def test_primitive_value_rides_fast_path(self) -> None:
        node, rows = _persist_single_node("plain")
        (row,) = rows
        assert row["value"] == "plain"
        assert row["_value_json"] is None

    def test_non_encodable_value_fails_loud_at_persist(self) -> None:
        with pytest.raises(PersistenceError):
            _persist_single_node({"bad": object()})


# ── loader: decode at materialisation (rule 3) ─────────────────────────


def _materialise(row):
    from mindsos_core.models.graph import Graph

    g = Graph(name="codec-load-test", role="episodic_memories")
    _add_node_from_row(g, row)
    (node,) = g.nodes.values()
    return node


class TestLoaderDecode:
    def test_structured_row_decodes_value_json(self) -> None:
        node = _materialise({
            "id": "n1",
            "type_name": "Episode",
            "value": None,
            "value_json": '{"a":[1,null,"x"],"b":2}',
            "version": 3,
            "props": {
                "_value_json": '{"a":[1,null,"x"],"b":2}',
                "graph_id": "g0",
                "user_key": "kept",
            },
        })
        assert node.value == {"a": [1, None, "x"], "b": 2}
        assert node.properties.get("user_key") == "kept"
        assert "_value_json" not in node.properties

    def test_primitive_row_unchanged(self) -> None:
        node = _materialise({
            "id": "n2",
            "type_name": "Episode",
            "value": 42,
            "value_json": None,
            "version": 1,
            "props": {},
        })
        assert node.value == 42

    def test_legacy_row_without_column_unchanged(self) -> None:
        node = _materialise({
            "id": "n3",
            "type_name": "Episode",
            "value": "legacy",
            "version": 1,
            "props": {},
        })
        assert node.value == "legacy"


# ── reserved-key rosters (rule 3 + ADR-0161 family) ───────────────────


class TestReservedKeyRosters:
    def test_value_json_in_reserved_property_keys(self) -> None:
        assert "_value_json" in RESERVED_PROPERTY_KEYS

    def test_value_json_in_loader_core_keys(self) -> None:
        assert "_value_json" in _CORE_KEYS
