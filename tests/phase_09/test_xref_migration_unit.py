"""xref_migration unit tests — RPB-2 + M9 flag rename + per-XRef dedup."""

from __future__ import annotations

from datetime import datetime

from mindsos_core import Graph, Metagraph
from mindsos_core.persistence.xref_migration import (
    MIGRATION_FLAG,
    migrate_in_memory,
)


def _mg_with_legacy_refs(*, n: int = 1) -> Metagraph:
    """Build mg with legacy ref:global_<role>= properties on a node."""
    mg = Metagraph(name="local", metagraph_id="mg-local")
    g = Graph(name="ont", role="ontology")
    mg.add_graph(g)
    g.add_node("n1", type_name="Concept", node_id="n1", properties={
        "ref:global_lexicon": "tgt-1",
        "ref_type": "SPECIALISES",
    })
    if n >= 2:
        g.add_node("n2", type_name="Concept", node_id="n2", properties={
            "ref:global_concepts": "tgt-2",
            "ref_type": "INSTANCE_OF",
        })
    return mg


def test_migration_flag_constant_is_xref_namespace_m9():
    """M9 — flag key uses xref: namespace (not v3 server: namespace)."""
    assert MIGRATION_FLAG == "xref:migrated_at"


def test_migrate_creates_xref_per_legacy_property():
    mg = _mg_with_legacy_refs(n=2)
    n = migrate_in_memory(mg, target_metagraph_id="mg-global")
    assert n == 2
    # Both source nodes' legacy props gone.
    n1 = mg.graphs[next(iter(mg.graphs))].nodes["n1"]
    assert "ref:global_lexicon" not in n1.properties
    assert "ref_type" not in n1.properties
    # Two XRefs created.
    assert len(mg.xrefs) == 2
    roles = {x.target_role for x in mg.xrefs.values()}
    assert roles == {"lexicon", "concepts"}


def test_migrate_sets_xref_migrated_at_flag():
    mg = _mg_with_legacy_refs()
    migrate_in_memory(mg, target_metagraph_id="mg-global")
    assert MIGRATION_FLAG in mg.properties
    # ISO datetime parses.
    datetime.fromisoformat(mg.properties[MIGRATION_FLAG])


def test_migrate_no_legacy_returns_zero():
    mg = Metagraph(name="empty")
    g = Graph(name="g", role="ontology")
    mg.add_graph(g)
    g.add_node("n1", type_name="X", node_id="n1")
    n = migrate_in_memory(mg, target_metagraph_id="mg-global")
    assert n == 0
    # Flag still set (whole-loop completion marker).
    assert MIGRATION_FLAG in mg.properties


def test_migrate_uses_default_ref_type_when_node_lacks_one():
    mg = Metagraph(name="m")
    g = Graph(name="g", role="ontology")
    mg.add_graph(g)
    g.add_node("n1", type_name="C", node_id="n1", properties={
        "ref:global_lexicon": "tgt-1",
        # NO ref_type property → default applies.
    })
    migrate_in_memory(
        mg, target_metagraph_id="mg-global", default_ref_type="EXTENDS",
    )
    [x] = list(mg.xrefs.values())
    assert x.ref_type == "EXTENDS"


def test_migrate_skips_when_flag_already_set():
    mg = _mg_with_legacy_refs()
    mg.properties[MIGRATION_FLAG] = "2026-01-01T00:00:00"
    n = migrate_in_memory(mg, target_metagraph_id="mg-global")
    assert n == 0
    # Legacy properties NOT touched (whole-fn short-circuit).
    n1 = mg.graphs[next(iter(mg.graphs))].nodes["n1"]
    assert "ref:global_lexicon" in n1.properties


def test_migrate_does_not_touch_intra_metagraph_refs():
    """ADR-0128 — only ref:global_* migrates; intra-metagraph ref:<role> unchanged."""
    mg = Metagraph(name="m")
    g = Graph(name="g", role="ontology")
    mg.add_graph(g)
    g.add_node("n1", type_name="C", node_id="n1", properties={
        "ref:concept": "intra-target",  # intra-metagraph; not migrated
    })
    migrate_in_memory(mg, target_metagraph_id="mg-global")
    n1 = mg.graphs[next(iter(mg.graphs))].nodes["n1"]
    assert n1.properties.get("ref:concept") == "intra-target"
    assert len(mg.xrefs) == 0
