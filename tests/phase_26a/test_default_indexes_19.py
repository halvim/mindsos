"""Phase 26a sentinel — DEFAULT_INDEXES gains the 19th entry.

Per ADR-0123 §am1 + Phase 26a R6-PB-1 (a). The 19th entry is
``("node", "Metagraph", "name")`` for the hot-path
:meth:`MetagraphLoader.find_by_name` invoked by
``bootstrap_kl_from_falkordb`` every CLI invocation.

Per memory ``feedback_phase_baseline_literal_audit.md`` — cumulative
literal-decay class for index-count assertions; this test pins the
post-Phase-26a expectation.
"""

from __future__ import annotations

from mindsos_core.persistence.bootstrap import DEFAULT_INDEXES


def test_default_indexes_count_is_19() -> None:
    """Phase 26a (R6-PB-1) — 18 + 1 (Metagraph.name) = 19."""
    assert len(DEFAULT_INDEXES) == 19


def test_metagraph_name_index_present() -> None:
    """The new entry is the second :Metagraph node index."""
    assert ("node", "Metagraph", "name") in DEFAULT_INDEXES


def test_existing_metagraph_id_index_retained() -> None:
    """Regression catch — the original :Metagraph.id index stays."""
    assert ("node", "Metagraph", "id") in DEFAULT_INDEXES


def test_node_graph_id_hot_path_index_retained() -> None:
    """Regression catch — the Phase 07 hot-path index stays."""
    assert ("node", "Node", "graph_id") in DEFAULT_INDEXES
