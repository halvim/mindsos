"""xref_migration idempotency — per-XRef content-tuple dedup (RPB-2 partial-crash)."""

from __future__ import annotations

from mindsos_core import Graph, Metagraph
from mindsos_core.persistence.xref_migration import (
    MIGRATION_FLAG,
    migrate_in_memory,
)


def _build_legacy_mg() -> Metagraph:
    mg = Metagraph(name="m", metagraph_id="mg-local")
    g = Graph(name="ont", role="ontology")
    mg.add_graph(g)
    g.add_node("n1", type_name="C", node_id="n1", properties={
        "ref:global_lexicon": "tgt-1",
        "ref_type": "SPECIALISES",
    })
    return mg


def test_re_run_after_clearing_flag_skips_existing_per_content_tuple():
    """RPB-2 partial-crash recovery — re-run with cleared flag hits the
    per-XRef ``already`` skip (content-tuple match) and does NOT
    duplicate.
    """
    mg = _build_legacy_mg()
    n_first = migrate_in_memory(mg, target_metagraph_id="mg-global")
    assert n_first == 1
    assert len(mg.xrefs) == 1

    # Simulate partial-crash recovery: flag cleared, but XRef survives
    # in mg.xrefs (was inline-persisted).
    del mg.properties[MIGRATION_FLAG]

    # Re-add a legacy property (simulating the migration crash before
    # property removal).
    n1 = mg.graphs[next(iter(mg.graphs))].nodes["n1"]
    n1.properties["ref:global_lexicon"] = "tgt-1"
    n1.properties["ref_type"] = "SPECIALISES"

    n_second = migrate_in_memory(mg, target_metagraph_id="mg-global")
    assert n_second == 0  # already exists ⇒ skipped
    # Still only one XRef (no duplicate).
    assert len(mg.xrefs) == 1


def test_different_target_id_creates_new_xref():
    """Per-XRef dedup is content-tuple-based; same source + different
    target_id ⇒ new XRef created (not deduped).
    """
    mg = _build_legacy_mg()
    migrate_in_memory(mg, target_metagraph_id="mg-global")
    del mg.properties[MIGRATION_FLAG]

    n1 = mg.graphs[next(iter(mg.graphs))].nodes["n1"]
    n1.properties["ref:global_lexicon"] = "tgt-DIFFERENT"
    n1.properties["ref_type"] = "SPECIALISES"

    n_second = migrate_in_memory(mg, target_metagraph_id="mg-global")
    assert n_second == 1
    target_ids = {x.target_id for x in mg.xrefs.values()}
    assert target_ids == {"tgt-1", "tgt-DIFFERENT"}
