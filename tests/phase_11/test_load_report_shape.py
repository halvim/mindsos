"""Tier 1 — :class:`LoadReport` / :class:`MetagraphLoadReport` shape.

Validates the additive-sibling report dataclasses ship per PB-9 B +
PB-13 A locks (recorded in PHASE_11_DESIGN_LOG.md §1 PB-9, PB-13).
"""

from __future__ import annotations

import pytest

from mindsos_core.reconstruction import LoadReport, MetagraphLoadReport


# ── LoadReport ───────────────────────────────────────────────────────────────


def test_load_report_default_construct_is_clean() -> None:
    """Default :class:`LoadReport` is clean (no drops)."""
    r = LoadReport(graph_id="g1")
    assert r.graph_id == "g1"
    assert r.dropped_edge_count == 0
    assert r.dropped_by_type == {}
    assert not r
    assert r.summary() == "clean"


def test_load_report_add_drop_increments_counts() -> None:
    """``add_drop`` increments total + per-type."""
    r = LoadReport(graph_id="g1")
    r.add_drop("WORKS_AT_LEGACY")
    r.add_drop("WORKS_AT_LEGACY")
    r.add_drop("OLD_TYPE")
    assert r.dropped_edge_count == 3
    assert r.dropped_by_type == {"WORKS_AT_LEGACY": 2, "OLD_TYPE": 1}
    assert bool(r)


def test_load_report_summary_string_shape() -> None:
    """``summary()`` describes count + distinct types when non-clean."""
    r = LoadReport(graph_id="g1")
    r.add_drop("A")
    r.add_drop("B")
    s = r.summary()
    assert "2 edge(s) dropped" in s
    assert "2 type(s)" in s


# ── MetagraphLoadReport ──────────────────────────────────────────────────────


def test_metagraph_load_report_default_construct_is_clean() -> None:
    """Default :class:`MetagraphLoadReport` is clean."""
    mr = MetagraphLoadReport(metagraph_id="m1")
    assert mr.metagraph_id == "m1"
    assert mr.per_graph == {}
    assert mr.total_dropped_edge_count == 0
    assert mr.total_dropped_by_type == {}
    assert not mr
    assert mr.summary() == "clean"


def test_metagraph_load_report_attach_aggregates_counts() -> None:
    """``attach`` folds per-Graph counts into Metagraph totals."""
    mr = MetagraphLoadReport(metagraph_id="m1")
    r1 = LoadReport(graph_id="g1")
    r1.add_drop("A")
    r1.add_drop("A")
    r2 = LoadReport(graph_id="g2")
    r2.add_drop("B")
    mr.attach(r1)
    mr.attach(r2)
    assert mr.total_dropped_edge_count == 3
    assert mr.total_dropped_by_type == {"A": 2, "B": 1}
    assert set(mr.per_graph.keys()) == {"g1", "g2"}
    assert mr.per_graph["g1"] is r1
    assert mr.per_graph["g2"] is r2


def test_metagraph_load_report_attach_clean_report_kept_in_per_graph() -> None:
    """Clean per-Graph reports are still indexed in ``per_graph``."""
    mr = MetagraphLoadReport(metagraph_id="m1")
    clean = LoadReport(graph_id="g_clean")
    mr.attach(clean)
    assert "g_clean" in mr.per_graph
    assert mr.total_dropped_edge_count == 0


def test_metagraph_load_report_summary_shape() -> None:
    """``summary()`` reports total/distinct/graph counts when non-clean."""
    mr = MetagraphLoadReport(metagraph_id="m1")
    r = LoadReport(graph_id="g1")
    r.add_drop("X")
    r.add_drop("X")
    r.add_drop("Y")
    mr.attach(r)
    mr.attach(LoadReport(graph_id="g2"))  # clean — not counted
    s = mr.summary()
    assert "3 edge(s) dropped" in s
    assert "2 type(s)" in s
    assert "1 graph(s)" in s  # only the non-clean one


def test_load_report_field_defaults_are_independent() -> None:
    """Multiple :class:`LoadReport` instances do not share mutable defaults."""
    r1 = LoadReport(graph_id="g1")
    r2 = LoadReport(graph_id="g2")
    r1.add_drop("A")
    assert r2.dropped_by_type == {}, "default_factory should isolate dicts"


def test_metagraph_load_report_field_defaults_are_independent() -> None:
    """Multiple Metagraph reports do not share mutable defaults."""
    m1 = MetagraphLoadReport(metagraph_id="m1")
    m2 = MetagraphLoadReport(metagraph_id="m2")
    r = LoadReport(graph_id="g")
    r.add_drop("A")
    m1.attach(r)
    assert m2.per_graph == {}
    assert m2.total_dropped_by_type == {}
