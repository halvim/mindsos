"""FalkorClient + bootstrap integration tests (Phase 07).

Marked ``@pytest.mark.integration`` per M11. Skipped automatically when
the FalkorDB sidecar is unreachable (see ``tests/_shared/falkordb_fixture``).
"""

from __future__ import annotations

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture


pytestmark = pytest.mark.integration


def test_run_query_returns_rows(falkor_client) -> None:
    res = falkor_client.run_query("RETURN 1 AS one")
    assert res.rows[0]["one"] == 1


def test_run_batch_sequential(falkor_client) -> None:
    results = falkor_client.run_batch([
        ("RETURN 1 AS x", {}),
        ("RETURN 2 AS x", {}),
    ])
    assert [r.first()["x"] for r in results] == [1, 2]


def test_bootstrap_idempotent(falkor_client) -> None:
    from mindsos_core.persistence import bootstrap

    # FalkorClient.__init__ already ran bootstrap (P2 A). Re-running
    # is the actual idempotency check.
    bootstrap(falkor_client)
    bootstrap(falkor_client)


def test_graph_repository_round_trip(falkor_client) -> None:
    from mindsos_core.models.graph import Graph
    from mindsos_core.persistence import GraphRepository
    from mindsos_core.reconstruction import load_graph
    from tests._shared.graph_equality import assert_graphs_equal

    g = Graph(name="round-trip")
    n1 = g.add_node("v1", "T")
    n2 = g.add_node("v2", "T")
    g.add_edge(n1, n2, "REL")

    repo = GraphRepository(falkor_client)
    repo.persist(g)

    loaded = load_graph(falkor_client, g.graph_id)
    assert_graphs_equal(loaded, g)


def test_occ_conflict_against_live(falkor_client) -> None:
    """Stale expected_version against live FalkorDB raises OCC."""
    from mindsos_core.exceptions import OptimisticConcurrencyConflict
    from mindsos_core.models.graph import Graph
    from mindsos_core.persistence import GraphRepository

    g = Graph(name="occ")
    n = g.add_node("v", "T")
    repo = GraphRepository(falkor_client)
    repo.persist(g)

    # Bump _version externally.
    repo.update_node_properties(g.graph_id, n.node_id, {"step": 1})

    with pytest.raises(OptimisticConcurrencyConflict):
        repo.update_node_properties(
            g.graph_id, n.node_id, {"step": 2}, expected_version=1
        )


def test_diagnose_reports_14_indexes(falkor_client) -> None:
    """After bootstrap, CALL db.indexes() returns at least 14 rows."""
    try:
        ix = falkor_client.run_query("CALL db.indexes()")
    except Exception:
        pytest.skip("CALL db.indexes() unsupported on this FalkorDB version")
    assert len(ix.rows) >= 14
