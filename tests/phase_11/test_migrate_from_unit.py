"""Tier 5 — :func:`mindsos_core.schema.migrate_from` unit tests.

Covers each violation kind × element family (Node/Edge/HyperEdge) ×
detail mode (summary/each) per PB-7 C + PB-8 A locks. Uses
:class:`Graph` constructed without an attached schema so loader
validation does not interfere with seeding "bad" data.
"""

from __future__ import annotations

import pytest

from mindsos_core.models.graph import Graph
from mindsos_core.schema import (
    EdgeType,
    HyperEdgeType,
    NodeType,
    PropertyType,
    Schema,
    SchemaMigrationError,
    SchemaViolation,
    migrate_from,
)


# ── helpers ──────────────────────────────────────────────────────────────────


def _build_seeded_graph() -> Graph:
    """Seed a Graph with 2 Persons, 1 WORKS_AT edge, 1 MEETING hyperedge."""
    g = Graph(name="org")
    a = g.add_node("alice", "Person", node_id="alice", _validate=False)
    b = g.add_node("bob", "Person", node_id="bob", _validate=False)
    g.add_edge(
        source=a, target=b, type_name="WORKS_AT",
        properties={"since": "2020"}, _validate=False,
    )
    g.add_hyperedge(
        nodes=[a, b], type_name="MEETING", properties={}, _validate=False,
    )
    return g


def _old_schema() -> Schema:
    """Old schema: Person + WORKS_AT + MEETING; minimal property types."""
    s = Schema(strict=True)
    s.add_node_type(NodeType(name="Person"))
    s.add_edge_type(
        EdgeType(
            name="WORKS_AT",
            allowed_sources=frozenset({"Person"}),
            allowed_targets=frozenset({"Person"}),
            property_types={"since": PropertyType.STRING},
        )
    )
    s.add_hyperedge_type(
        HyperEdgeType(name="MEETING", allowed_member_types=frozenset({"Person"}))
    )
    return s


# ── kind: removed_node_type ─────────────────────────────────────────────────


def test_removed_node_type_summary_mode_aggregates() -> None:
    """Summary entry per (kind, type_name) with count."""
    old = _old_schema()
    g = _build_seeded_graph()
    new = Schema(strict=True)  # Person removed.
    new.add_edge_type(  # keep WORKS_AT to isolate the node-removal bucket.
        EdgeType(
            name="WORKS_AT",
            property_types={"since": PropertyType.STRING},
        )
    )
    new.add_hyperedge_type(HyperEdgeType(name="MEETING"))
    violations = migrate_from(old, g, new=new, detail="summary")
    removed_node = [v for v in violations if v.kind == "removed_node_type"]
    assert len(removed_node) == 1
    assert removed_node[0].type_name == "Person"
    assert removed_node[0].count == 2
    assert removed_node[0].element_id == ""


def test_removed_node_type_each_mode_one_per_element() -> None:
    """Each mode emits one violation per offending node."""
    old = _old_schema()
    g = _build_seeded_graph()
    new = Schema(strict=True)
    new.add_edge_type(EdgeType(name="WORKS_AT"))
    new.add_hyperedge_type(HyperEdgeType(name="MEETING"))
    violations = migrate_from(old, g, new=new, detail="each")
    removed_node = [v for v in violations if v.kind == "removed_node_type"]
    assert len(removed_node) == 2
    assert {v.element_id for v in removed_node} == {"alice", "bob"}
    assert all(v.count == 1 for v in removed_node)


# ── kind: removed_edge_type ─────────────────────────────────────────────────


def test_removed_edge_type_surfaces() -> None:
    """Edge type removed from new schema → violation."""
    old = _old_schema()
    g = _build_seeded_graph()
    new = Schema(strict=True)
    new.add_node_type(NodeType(name="Person"))
    # WORKS_AT removed.
    new.add_hyperedge_type(HyperEdgeType(name="MEETING"))
    violations = migrate_from(old, g, new=new, detail="summary")
    removed_edge = [v for v in violations if v.kind == "removed_edge_type"]
    assert len(removed_edge) == 1
    assert removed_edge[0].type_name == "WORKS_AT"
    assert removed_edge[0].count == 1


# ── kind: removed_hyperedge_type ────────────────────────────────────────────


def test_removed_hyperedge_type_surfaces() -> None:
    """HyperEdge type removed from new schema → violation."""
    old = _old_schema()
    g = _build_seeded_graph()
    new = Schema(strict=True)
    new.add_node_type(NodeType(name="Person"))
    new.add_edge_type(
        EdgeType(name="WORKS_AT", property_types={"since": PropertyType.STRING})
    )
    # MEETING removed.
    violations = migrate_from(old, g, new=new, detail="summary")
    removed_he = [v for v in violations if v.kind == "removed_hyperedge_type"]
    assert len(removed_he) == 1
    assert removed_he[0].type_name == "MEETING"
    assert removed_he[0].count == 1


# ── kind: missing_required_property ─────────────────────────────────────────


def test_missing_required_property_node() -> None:
    """New required property absent from persisted nodes."""
    old = _old_schema()
    g = _build_seeded_graph()
    new = Schema(strict=True)
    new.add_node_type(
        NodeType(name="Person", property_types={"email": PropertyType.STRING})
    )
    new.add_edge_type(
        EdgeType(name="WORKS_AT", property_types={"since": PropertyType.STRING})
    )
    new.add_hyperedge_type(HyperEdgeType(name="MEETING"))
    violations = migrate_from(old, g, new=new, detail="summary")
    missing = [v for v in violations if v.kind == "missing_required_property"]
    assert len(missing) == 1
    assert missing[0].type_name == "Person"
    assert missing[0].property_name == "email"
    assert missing[0].count == 2


def test_missing_required_property_each_mode_emits_per_element() -> None:
    """Each mode emits one violation per missing-prop element."""
    old = _old_schema()
    g = _build_seeded_graph()
    new = Schema(strict=True)
    new.add_node_type(
        NodeType(name="Person", property_types={"email": PropertyType.STRING})
    )
    new.add_edge_type(
        EdgeType(name="WORKS_AT", property_types={"since": PropertyType.STRING})
    )
    new.add_hyperedge_type(HyperEdgeType(name="MEETING"))
    violations = migrate_from(old, g, new=new, detail="each")
    missing = [v for v in violations if v.kind == "missing_required_property"]
    assert len(missing) == 2
    assert {v.element_id for v in missing} == {"alice", "bob"}


# ── kind: tightened_property ────────────────────────────────────────────────


def test_tightened_property_detects_type_change() -> None:
    """Type change with mismatched persisted value → tightening violation."""
    old = Schema(strict=True)
    old.add_node_type(NodeType(name="Person"))
    old.add_edge_type(
        EdgeType(name="WORKS_AT", property_types={"since": PropertyType.STRING})
    )
    g = Graph(name="org")
    a = g.add_node("alice", "Person", node_id="alice", _validate=False)
    b = g.add_node("bob", "Person", node_id="bob", _validate=False)
    g.add_edge(
        source=a, target=b, type_name="WORKS_AT",
        properties={"since": "2020"},  # STRING value
        _validate=False,
    )
    new = Schema(strict=True)
    new.add_node_type(NodeType(name="Person"))
    new.add_edge_type(
        EdgeType(name="WORKS_AT", property_types={"since": PropertyType.INT}),
    )
    violations = migrate_from(old, g, new=new, detail="summary")
    tight = [v for v in violations if v.kind == "tightened_property"]
    assert len(tight) == 1
    assert tight[0].type_name == "WORKS_AT"
    assert tight[0].property_name == "since"
    assert tight[0].count == 1


def test_tightened_property_compatible_value_yields_no_violation() -> None:
    """If persisted value matches new type, no tightening violation."""
    old = Schema(strict=True)
    old.add_node_type(NodeType(name="Person"))
    old.add_edge_type(
        EdgeType(name="WORKS_AT", property_types={"since": PropertyType.STRING})
    )
    g = Graph(name="org")
    a = g.add_node("alice", "Person", node_id="alice", _validate=False)
    b = g.add_node("bob", "Person", node_id="bob", _validate=False)
    g.add_edge(
        source=a, target=b, type_name="WORKS_AT",
        properties={"since": "still-a-string"},
        _validate=False,
    )
    new = Schema(strict=True)
    new.add_node_type(NodeType(name="Person"))
    new.add_edge_type(
        EdgeType(name="WORKS_AT", property_types={"since": PropertyType.STRING}),
    )
    violations = migrate_from(old, g, new=new, detail="summary")
    assert violations == []


# ── per-type added-property absence path ────────────────────────────────────


def test_added_property_present_in_data_does_not_violate() -> None:
    """When the new required property is already present, no violation."""
    old = _old_schema()
    g = Graph(name="org")
    a = g.add_node("alice", "Person", properties={"email": "a@x"}, node_id="alice", _validate=False)
    b = g.add_node("bob", "Person", properties={"email": "b@x"}, node_id="bob", _validate=False)
    g.add_edge(source=a, target=b, type_name="WORKS_AT",
               properties={"since": "2020"}, _validate=False)
    g.add_hyperedge(nodes=[a, b], type_name="MEETING", properties={},
                    _validate=False)
    new = Schema(strict=True)
    new.add_node_type(
        NodeType(name="Person", property_types={"email": PropertyType.STRING})
    )
    new.add_edge_type(
        EdgeType(name="WORKS_AT", property_types={"since": PropertyType.STRING})
    )
    new.add_hyperedge_type(HyperEdgeType(name="MEETING"))
    violations = migrate_from(old, g, new=new, detail="summary")
    assert violations == [], "All persisted data satisfies new schema"


# ── error paths ─────────────────────────────────────────────────────────────


def test_bad_detail_kwarg_raises_schema_migration_error() -> None:
    """``detail`` must be ``"summary"`` or ``"each"``."""
    old = _old_schema()
    g = _build_seeded_graph()
    with pytest.raises(SchemaMigrationError, match="detail"):
        migrate_from(old, g, detail="bogus")


def test_bad_target_type_raises_schema_migration_error() -> None:
    """``target`` must be a Graph or Metagraph."""
    old = _old_schema()
    with pytest.raises(SchemaMigrationError, match="target must be"):
        migrate_from(old, "not-a-graph")


def test_no_new_schema_no_attached_schema_returns_empty() -> None:
    """Graph with no attached schema + no explicit ``new`` → clean."""
    old = _old_schema()
    g = Graph(name="org")  # no schema.
    assert migrate_from(old, g, detail="summary") == []


# ── SchemaViolation frozen contract ─────────────────────────────────────────


def test_schema_violation_is_frozen() -> None:
    """SchemaViolation is a frozen dataclass per PB-7 deferred items."""
    v = SchemaViolation(
        kind="removed_node_type",
        type_name="Person",
        element_id="alice",
        graph_id="g1",
        property_name="",
        count=1,
        detail="...",
    )
    with pytest.raises((AttributeError, Exception)):
        v.count = 99  # type: ignore[misc]


def test_schema_violation_has_seven_fields() -> None:
    """Field set matches the locked shape (PB-8 A + PB-7 C)."""
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(SchemaViolation)}
    assert field_names == {
        "kind", "type_name", "element_id", "graph_id",
        "property_name", "count", "detail",
    }
