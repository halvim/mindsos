"""Bootstrap idempotency + index DDL tests (Phase 07)."""

from __future__ import annotations

from mindsos_core.persistence import InMemoryClient, bootstrap, DEFAULT_INDEXES
from mindsos_core.persistence.bootstrap import _ddl_for


def test_default_indexes_count_equals_14() -> None:
    """P95 B locked count."""
    assert len(DEFAULT_INDEXES) == 14


def test_default_indexes_split_10_node_3_rel_1_hotpath() -> None:
    """10 node-label `id` + 3 relationship `id` + 1 hot-path `:Node {graph_id}`.

    Node-form DDL count = 10 unique labels + 1 hot-path = 11; rel-form = 3.
    """
    kinds = [k for k, _, _ in DEFAULT_INDEXES]
    assert kinds.count("node") == 11
    assert kinds.count("rel") == 3


def test_ddl_node_form() -> None:
    """Node-label DDL uses `(n:Label)` syntax (no IF NOT EXISTS per B-07-T1)."""
    q = _ddl_for("node", "Node", "id")
    assert q == "CREATE INDEX FOR (n:Node) ON (n.id)"


def test_ddl_rel_form() -> None:
    """Relationship-type DDL uses `()-[r:RelType]-()` syntax per P89 A.

    Per B-07-T1 hotfix — bare ``CREATE INDEX FOR`` only; FalkorDB v4.18.3
    rejects ``IF NOT EXISTS`` as a Cypher parser syntax error. Idempotency
    via the bootstrap defensive try/except, not the clause.
    """
    q = _ddl_for("rel", "Edge", "id")
    assert q == "CREATE INDEX FOR ()-[r:Edge]-() ON (r.id)"


def test_bootstrap_emits_14_statements_against_inmemory() -> None:
    """One CREATE INDEX statement per DEFAULT_INDEXES entry."""
    c = InMemoryClient()
    bootstrap(c)
    create_calls = [q for q, _ in c.calls if q.startswith("CREATE INDEX")]
    assert len(create_calls) == 14


def test_bootstrap_swallows_already_exists_errors() -> None:
    """Bootstrap survives re-runs via the defensive 'already indexed' catch.

    Per B-07-T1 (2026-05-13) — FalkorDB v4.18.3 returns
    ``Attribute 'id' is already indexed`` on duplicate index creation;
    the substring ``already`` + ``indexed`` both match the catch.
    """
    from mindsos_core.exceptions import PersistenceError

    class ExistsRaiser(InMemoryClient):
        def run_query(self, q, p=None):
            super().run_query(q, p)
            raise PersistenceError("Attribute 'id' is already indexed")

    c = ExistsRaiser()
    bootstrap(c)  # Should not raise.
    assert len(c.calls) == 14


def test_bootstrap_reraises_unrelated_errors() -> None:
    """Non-already-exists errors propagate."""
    import pytest
    from mindsos_core.exceptions import PersistenceError

    class TotalFailure(InMemoryClient):
        def run_query(self, q, p=None):
            super().run_query(q, p)
            raise PersistenceError("syntax broken")

    with pytest.raises(PersistenceError, match="syntax broken"):
        bootstrap(TotalFailure())
