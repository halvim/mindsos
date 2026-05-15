"""xref_migration end-to-end (integration) — RPB-2 WAL-wrapped per add_xref."""

from __future__ import annotations

import pytest

from mindsos_core import Graph, Metagraph
from mindsos_core.cypher.builders import build_create_metagraph_anchor
from mindsos_core.persistence.xref_migration import (
    MIGRATION_FLAG, migrate_in_memory,
)

pytestmark = pytest.mark.integration


def test_migration_inline_writes_xref_via_wal(falkor_client):
    """RPB-2 — when _persist_client is set, each add_xref WAL-writes inline."""
    q, p = build_create_metagraph_anchor("mg-migint", "migint", props_json="{}")
    falkor_client.run_query(q, p)

    mg = Metagraph(name="migint", metagraph_id="mg-migint")
    g = Graph(name="ont", role="ontology")
    mg.add_graph(g)
    g.add_node("n1", type_name="C", node_id="n1", properties={
        "ref:global_lexicon": "tgt-1",
        "ref_type": "SPECIALISES",
    })
    # Attach the live client so add_xref (called by migrate) writes inline.
    mg._persist_client = falkor_client

    n = migrate_in_memory(mg, target_metagraph_id="mg-global")
    assert n == 1
    # Flag set.
    assert MIGRATION_FLAG in mg.properties

    # XRef row landed in DB.
    res = falkor_client.run_query(
        "MATCH (x:XRef {source_metagraph_id: $mid}) RETURN count(x) AS n",
        {"mid": "mg-migint"},
    )
    assert res.rows[0]["n"] == 1
