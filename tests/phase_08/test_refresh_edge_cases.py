"""R4-2 D — refresh empty-role no-op + role-mismatch raise.

Covers:

* empty-role: log-warn + no-op (unit-testable).
* role-mismatch: raise :class:`RoleMismatchError` with both roles
  surfaced (integration — needs DB-side role drift simulated).
"""

from __future__ import annotations

import logging

import pytest


def test_refresh_empty_role_log_warn_and_no_op(caplog) -> None:
    """R4-2 D — empty role → log WARNING + no-op return; no DB calls."""
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import InMemoryClient
    from mindsos_core.reconstruction import MetagraphLoader

    mg = Metagraph(name="empty-role-mg", identity=IdentityRegistry())
    # No contained graphs — refresh on any role hits the empty-role
    # branch.
    c = InMemoryClient()

    caplog.set_level(
        logging.WARNING,
        logger="mindsos_core.reconstruction.metagraph_loader",
    )
    loader = MetagraphLoader(c)
    result = loader.refresh(mg, role="nonexistent")

    assert result is None  # No-op return.
    assert any(
        "no graphs with role=" in rec.message for rec in caplog.records
    )
    # Empty-role path issues NO DB queries (no role mismatch precheck).
    assert c.calls == []


@pytest.mark.integration
def test_refresh_role_mismatch_raises_role_mismatch_error(falkor_client) -> None:
    """R4-2 D — DB role drift → RoleMismatchError with both roles."""
    from mindsos_core.exceptions import RoleMismatchError
    from mindsos_core.models.graph import Graph
    from mindsos_core.models.identity import IdentityRegistry
    from mindsos_core.models.metagraph import Metagraph
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import MetagraphLoader

    mg = Metagraph(name="role-drift", identity=IdentityRegistry())
    g = Graph(name="g1", role="lex", identity=mg.identity)
    g.add_node(value="x", type_name="T", node_id="n1", _validate=False)
    mg.add_graph(g)

    MetagraphRepository(falkor_client).persist(mg)

    # Simulate DB-side role drift by updating the :Graph.role property
    # directly via Cypher (mimics an external write / manual edit).
    falkor_client.run_query(
        "MATCH (g:Graph {id: $gid}) SET g.role = $new_role",
        {"gid": g.graph_id, "new_role": "ontology"},
    )

    loader = MetagraphLoader(falkor_client)
    with pytest.raises(RoleMismatchError) as excinfo:
        loader.refresh(mg, role="lex")

    err = excinfo.value
    assert err.graph_id == g.graph_id
    assert err.in_memory_role == "lex"
    assert err.db_role == "ontology"
