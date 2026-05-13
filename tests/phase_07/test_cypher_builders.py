"""Cypher builder shape tests (Phase 07 — P58 B typed args)."""

from __future__ import annotations

import pytest

from mindsos_core.cypher.builders import (
    build_create_composite_instance,
    build_create_element_instance,
    build_create_graph_anchor,
    build_create_metagraph_anchor,
    build_create_tombstone,
    build_remove_edge,
    build_remove_hyperedge,
    build_remove_node,
    build_unwind_create_edges,
    build_unwind_create_hyperedges,
    build_unwind_create_intergraph_edges,
    build_unwind_create_intergraph_hyperedges,
    build_unwind_create_metaedges,
    build_unwind_create_metahyperedges,
    build_unwind_create_nodes,
    build_update_edge_properties,
    build_update_hyperedge_properties,
    build_update_node_properties,
)
from mindsos_core.exceptions import CypherError


def test_metagraph_anchor_carries_schema_name_property() -> None:
    """P100 A — schema_name persists as plain Cypher property."""
    q, p = build_create_metagraph_anchor(
        "mg1", "Alice", props_json='{"k":"v"}', schema_name="lex_v1"
    )
    assert "m.schema_name = $schema_name" in q
    assert p["schema_name"] == "lex_v1"
    assert p["props_json"] == '{"k":"v"}'


def test_metagraph_anchor_schema_name_none_passes_none() -> None:
    q, p = build_create_metagraph_anchor("mg1", "Alice", props_json="{}")
    assert p["schema_name"] is None


def test_graph_anchor_no_properties_param() -> None:
    """P9 C — Graph .properties writer skipped; builder takes no properties arg."""
    q, p = build_create_graph_anchor("g1", "g1", "lexicon", "mg1")
    assert "g._version = 1" in q
    assert "props" not in p
    assert p["mid"] == "mg1"


def test_tombstone_uses_per_graph_element_key() -> None:
    """P69 A — per-(graph, element) tombstone shape."""
    q, p = build_create_tombstone("g1", "n1", "node", removed_by="alice")
    assert ":Tombstone {graph_id: $gid, element_id: $eid}" in q
    assert p["gid"] == "g1" and p["eid"] == "n1" and p["kind"] == "node"
    assert p["by"] == "alice"


def test_unwind_nodes_carries_version() -> None:
    q, p = build_unwind_create_nodes(
        "g1", [{"id": "n1", "type_name": "T", "value": "v", "props": {}, "_version": 1}]
    )
    assert "row._version" in q
    assert p["rows"][0]["_version"] == 1


def test_unwind_edges_validates_rel_type() -> None:
    """Cypher rel-type identifier regex enforced (ADR-0021)."""
    with pytest.raises(CypherError):
        build_unwind_create_edges("g1", "bad type name with spaces", [])


def test_unwind_edges_splices_validated_type_name() -> None:
    q, p = build_unwind_create_edges("g1", "REL", [
        {"id": "e1", "source": "n1", "target": "n2",
         "label": "lbl", "props": {}, "_version": 1}
    ])
    assert "[e:REL " in q


def test_unwind_hyperedges_includes_members() -> None:
    q, p = build_unwind_create_hyperedges("g1", [
        {"id": "h1", "label": None, "props": {}, "member_ids": ["n1", "n2"], "_version": 1}
    ])
    assert "UNWIND row.member_ids" in q
    assert p["rows"][0]["member_ids"] == ["n1", "n2"]


def test_unwind_metaedges_takes_graph_endpoints() -> None:
    q, p = build_unwind_create_metaedges("mg1", "MREL", [
        {"id": "me1", "source_graph_id": "g1", "target_graph_id": "g2",
         "label": None, "props": {}, "_version": 1}
    ])
    assert "row.source_graph_id" in q and "row.target_graph_id" in q


def test_unwind_metahyperedges_takes_member_graph_ids() -> None:
    q, p = build_unwind_create_metahyperedges("mg1", [
        {"id": "mh1", "label": None, "props": {},
         "member_graph_ids": ["g1", "g2", "g3"], "_version": 1}
    ])
    assert "row.member_graph_ids" in q


def test_unwind_intergraph_edges_carries_compositional() -> None:
    q, p = build_unwind_create_intergraph_edges("mg1", "XREL", [
        {"id": "ie1", "source_node_id": "n1", "source_graph_id": "g1",
         "target_node_id": "n2", "target_graph_id": "g2",
         "label": None, "compositional": True, "props": {}, "_version": 1}
    ])
    assert "row.compositional" in q
    assert p["rows"][0]["compositional"] is True


def test_unwind_intergraph_hyperedges_takes_members() -> None:
    q, p = build_unwind_create_intergraph_hyperedges("mg1", [
        {"id": "ih1", "label": None, "ordered": True, "compositional": False,
         "props": {},
         "members": [{"node_id": "n1", "graph_id": "g1"}],
         "_version": 1}
    ])
    assert "UNWIND row.members" in q
    assert "MATCH (n:Node {id: mem.node_id, graph_id: mem.graph_id})" in q


def test_update_node_with_expected_version_predicates() -> None:
    """P7 C OCC predicate."""
    q, p = build_update_node_properties("g1", "n1", {"k": "v"}, expected_version=3)
    assert "_version: $expected" in q
    assert p["expected"] == 3
    assert "_version = coalesce(n._version, 0) + 1" in q


def test_update_node_without_expected_version_omits_predicate() -> None:
    q, p = build_update_node_properties("g1", "n1", {"k": "v"})
    assert "_version: $expected" not in q
    assert "expected" not in p


def test_update_edge_and_hyperedge_share_pattern() -> None:
    qe, pe = build_update_edge_properties("g1", "e1", {"k": "v"}, expected_version=2)
    qh, ph = build_update_hyperedge_properties("g1", "h1", {"k": "v"}, expected_version=2)
    assert "_version = coalesce(" in qe
    assert "_version = coalesce(" in qh


def test_remove_node_writes_tombstone_and_deletes() -> None:
    q, p = build_remove_node("g1", "n1")
    assert ":Tombstone {graph_id: $gid, element_id: $nid}" in q
    assert "DETACH DELETE n" in q


def test_remove_edge_writes_tombstone() -> None:
    q, p = build_remove_edge("g1", "e1")
    assert ":Tombstone {graph_id: $gid, element_id: $eid}" in q
    assert "element_kind = 'edge'" in q


def test_remove_hyperedge_writes_tombstone() -> None:
    q, p = build_remove_hyperedge("g1", "h1")
    assert "element_kind = 'hyperedge'" in q


def test_element_instance_builder_uses_kind_label() -> None:
    q, p = build_create_element_instance(
        "i1", "node", "mg1", "n1", "g1", {"foo": "bar"}, None,
    )
    assert ":ElementInstance:NodeInstance" in q
    assert p["overrides_prefixed"] == {"ov__foo": "bar"}


def test_element_instance_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="Unknown ElementInstance kind"):
        build_create_element_instance("i1", "bogus", "mg1", "x", None, {}, None)


def test_composite_instance_carries_members() -> None:
    q, p = build_create_composite_instance(
        "c1", "mg1", ["i1", "i2"], {"k": 1}, None,
    )
    assert "MERGE (c:CompositeInstance" in q
    assert p["member_ids"] == ["i1", "i2"]
