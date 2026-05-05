"""Unit tests for the Graph primitive and its schema integration.

Ported from the parent project's ``tests/unit/test_graph.py`` in Phase 04.
14 of 15 tests run as-is; ``test_restore_node_registers_provided_id`` is
skipped pending Phase 08 (when ``Graph._restore_node`` lands).
"""

from __future__ import annotations

import pytest

from mindsos_core import (
    EdgeType,
    Graph,
    IdentityError,
    NodeType,
    PropertyShapeError,
    Schema,
    SchemaError,
    UnknownTypeError,
)


@pytest.fixture
def schema() -> Schema:
    s = Schema(strict=False)
    s.add_node_type(NodeType("Person"))
    s.add_node_type(NodeType("Org"))
    s.add_edge_type(EdgeType("WORKS_AT", frozenset({"Person"}), frozenset({"Org"})))
    return s


def test_add_node_returns_typed_node(schema):
    g = Graph("world", role="ontology", schema=schema)
    n = g.add_node("Alice", "Person", properties={"age": 30})
    assert n.type_name == "Person"
    assert n.node_id in g.nodes
    assert g.nodes[n.node_id].properties == {"age": 30}


def test_add_node_rejects_unknown_type(schema):
    g = Graph("world", schema=schema)
    with pytest.raises(UnknownTypeError):
        g.add_node("x", "Alien")


def test_add_edge_respects_source_target_types(schema):
    g = Graph("world", schema=schema)
    a = g.add_node("Alice", "Person")
    o = g.add_node("Acme", "Org")
    b = g.add_node("Bob", "Person")
    g.add_edge(a, o, "WORKS_AT")
    with pytest.raises(UnknownTypeError):
        g.add_edge(a, b, "WORKS_AT")  # target must be Org


def test_reserved_property_key_rejected(schema):
    g = Graph("world", schema=schema)
    with pytest.raises(PropertyShapeError):
        g.add_node("Alice", "Person", properties={"id": "evil"})


def test_non_primitive_property_rejected(schema):
    g = Graph("world", schema=schema)
    with pytest.raises(PropertyShapeError):
        g.add_node("Alice", "Person", properties={"meta": {"nested": 1}})


def test_hyperedge_must_have_members():
    g = Graph("world")
    with pytest.raises(SchemaError):
        g.add_hyperedge([], type_name="MEMBERS")


def test_remove_node_cascades_edges(schema):
    g = Graph("world", schema=schema)
    a = g.add_node("Alice", "Person")
    o = g.add_node("Acme", "Org")
    e = g.add_edge(a, o, "WORKS_AT")
    g.remove_node(a.node_id, cascade=True)
    assert a.node_id not in g.nodes
    assert e.edge_id not in g.edges


def test_remove_node_no_cascade_raises_if_referenced(schema):
    g = Graph("world", schema=schema)
    a = g.add_node("Alice", "Person")
    o = g.add_node("Acme", "Org")
    g.add_edge(a, o, "WORKS_AT")
    with pytest.raises(SchemaError):
        g.remove_node(a.node_id, cascade=False)


@pytest.mark.skip(
    reason="Graph._restore_node ships in Phase 08 (reconstruction helpers); "
    "Phase 04 slim port omits the private restore API."
)
def test_restore_node_registers_provided_id():
    g = Graph("world")
    g._restore_node("fixed-id", "val", "Any", {"k": 1})  # type: ignore[attr-defined]
    assert "fixed-id" in g.nodes
    assert "fixed-id" in g.identity


def test_strict_schema_enforces_property_types():
    s = Schema(strict=True)
    from mindsos_core.schema.types import PropertyType
    s.add_node_type(NodeType("Person", property_types={"age": PropertyType.INT}))
    g = Graph("world", schema=s)
    g.add_node("Alice", "Person", properties={"age": 30})
    with pytest.raises(PropertyShapeError):
        g.add_node("Bob", "Person", properties={"age": "thirty"})


# ── Track A tests: explicit node_id / edge_id kwargs (Knowledge Layer prereq) ──

def test_add_node_honours_explicit_node_id(schema):
    g = Graph("world", schema=schema)
    n = g.add_node("Alice", "Person", node_id="dolce-dul-4.0:PhysicalObject")
    assert n.node_id == "dolce-dul-4.0:PhysicalObject"
    assert "dolce-dul-4.0:PhysicalObject" in g.nodes
    assert "dolce-dul-4.0:PhysicalObject" in g.identity


def test_add_node_default_is_still_uuid(schema):
    g = Graph("world", schema=schema)
    n = g.add_node("Alice", "Person")
    # UUID4 string is 36 chars with dashes; certainly not an IRI.
    assert len(n.node_id) == 36
    assert ":" not in n.node_id


def test_add_node_duplicate_explicit_id_raises(schema):
    g = Graph("world", schema=schema)
    g.add_node("Alice", "Person", node_id="iri:shared")
    with pytest.raises(IdentityError):
        g.add_node("Alicia", "Person", node_id="iri:shared")


def test_add_edge_honours_explicit_edge_id(schema):
    g = Graph("world", schema=schema)
    a = g.add_node("Alice", "Person")
    o = g.add_node("Acme", "Org")
    e = g.add_edge(a, o, "WORKS_AT", edge_id="edge-1")
    assert e.edge_id == "edge-1"
    assert "edge-1" in g.edges
    assert "edge-1" in g.identity


def test_add_hyperedge_honours_explicit_edge_id():
    """Phase 04-v2 — non-schema graph; type_name still required (cypher regex)."""
    g = Graph("world")
    a = g.add_node("Alice", "Person")
    o = g.add_node("Acme", "Org")
    he = g.add_hyperedge(
        [a, o], type_name="MEMBERS", label="project-X", edge_id="he-1",
    )
    assert he.edge_id == "he-1"
    assert "he-1" in g.hyperedges
    assert "he-1" in g.identity
