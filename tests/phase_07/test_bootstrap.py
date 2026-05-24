"""Bootstrap idempotency + index DDL tests (Phase 07; updated Phase 09 for M15)."""

from __future__ import annotations

from mindsos_core.persistence import InMemoryClient, bootstrap, DEFAULT_INDEXES
from mindsos_core.persistence.bootstrap import _ddl_for


def test_default_indexes_count_phase07_baseline_plus_phase09_xref() -> None:
    """P95 B locked Phase 07 baseline at 14; Phase 09 M15 grows to 18;
    Phase 26a (ADR-0123 §am1) grows to 19.

    Replaces ``test_default_indexes_count_equals_14``. Counts hard-coded
    so future bumps remain visible (audit cost analogous to state-file
    version literals per ``feedback_state_version_audit_scope.md``).
    """
    # 14 from Phase 07 + 4 :XRef from Phase 09 (M15) + 1 :Metagraph.name
    # from Phase 26a = 19.
    assert len(DEFAULT_INDEXES) == 19
    xref_entries = [(k, l, p) for (k, l, p) in DEFAULT_INDEXES if l == "XRef"]
    assert len(xref_entries) == 4


def test_default_indexes_split_node_rel_phase09() -> None:
    """Phase 09 split: 11 Phase 07 node-form + 4 XRef node-form = 15 node;
    3 relationship-form unchanged. Phase 26a (ADR-0123 §am1) adds 1 node
    (:Metagraph.name) → 16 node total; rel unchanged at 3.
    """
    kinds = [k for k, _, _ in DEFAULT_INDEXES]
    assert kinds.count("node") == 16
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


def test_bootstrap_emits_one_statement_per_default_index() -> None:
    """One CREATE INDEX statement per DEFAULT_INDEXES entry (Phase 09: 18)."""
    c = InMemoryClient()
    bootstrap(c)
    create_calls = [q for q, _ in c.calls if q.startswith("CREATE INDEX")]
    assert len(create_calls) == len(DEFAULT_INDEXES)


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
    assert len(c.calls) == len(DEFAULT_INDEXES)


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
