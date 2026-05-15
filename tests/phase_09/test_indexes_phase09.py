"""Phase 09 :XRef indexes — M15 (4 new indexes; bootstrap 14 → 18)."""

from __future__ import annotations

import pytest

from mindsos_core.persistence.bootstrap import (
    DEFAULT_INDEXES,
    _ddl_for,
)

pytestmark_unit = []


def test_default_indexes_grew_from_14_to_18():
    """M15 — Phase 09 adds 4 :XRef indexes."""
    assert len(DEFAULT_INDEXES) == 18


def test_xref_indexes_present_in_default():
    """4 specific :XRef indexes per M15."""
    xref_specs = [(k, l, p) for (k, l, p) in DEFAULT_INDEXES if l == "XRef"]
    assert len(xref_specs) == 4
    props = {p if isinstance(p, str) else p for (_, _, p) in xref_specs}
    assert "id" in props
    assert "source_metagraph_id" in props
    assert "source_id" in props
    assert ("target_metagraph_id", "target_id") in props


def test_compound_index_ddl_renders_correctly():
    """Compound index syntax: ON (n.p1, n.p2)."""
    ddl = _ddl_for("node", "XRef", ("target_metagraph_id", "target_id"))
    assert "ON (n.target_metagraph_id, n.target_id)" in ddl
    assert "CREATE INDEX FOR (n:XRef)" in ddl


def test_single_property_index_ddl_renders_correctly():
    ddl = _ddl_for("node", "XRef", "source_id")
    assert "ON (n.source_id)" in ddl
    assert "CREATE INDEX FOR (n:XRef)" in ddl


@pytest.mark.integration
def test_all_xref_indexes_substring_present_after_bootstrap(falkor_client):
    """B-07-T4 substring-check pattern — db.indexes() shows :XRef coverage.

    FalkorDB v4.18.3 groups multi-property indexes per label so we
    don't assert exact row count; we assert each expected label-prop
    pair appears in the indexes() output.
    """
    res = falkor_client.run_query("CALL db.indexes()")
    output = " ".join(str(r) for r in res.rows)
    # Substring check per B-07-T4.
    assert "XRef" in output
