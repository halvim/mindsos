"""Guard on the dump instrument itself (coordination §19 finding 1, §22 scope).

The plan's §2.7 worry — a dump that under-reports "looks healthy" — applies to
`dr_dump` too: nothing else fails if `_dump_graphs` silently skips a node type
or the collected list stops matching `capacity_mm`. These tests pin the
printer to the objects and the collected list to the MM, and pin that the
retry shape's deliberate delta (a rejected attempt's graph stays in the MM
only) is REPORTED rather than hidden.

Run under pytest, or with no dependencies at all:

    PYTHONPATH=. python decision_records_demo/test_dr_dump_printer_guard.py
"""

from __future__ import annotations

import contextlib
import io
import re

from decision_records_demo.dr_dump import (
    DS_CLAIM_EXPOSURES,
    EXPOSURES,
    _claim_plan,
    _conclude_declaration,
    _decide_declaration,
    _dump_graphs,
    _dump_mm_delta,
    _harness,
    _make_flaky_decide,
    execution,
)


def _run_claim(capacities=None):
    mm, dispatcher, writer, request_run = _harness(capacities=capacities)
    graphs: list = []
    execution.run(
        dispatcher, writer, _claim_plan(), request_run,
        mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: list(EXPOSURES)},
        capacity_graphs=graphs,
        case_label="claim CLM-2041",
    )
    return mm, graphs


def _captured(fn, *args) -> str:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        fn(*args)
    return out.getvalue()


def test_printer_counts_match_objects():
    """Every node and every edge of every collected graph is printed —
    printed counts equal object counts, so a printer that skips a node type
    under-counts and fails here."""
    _mm, graphs = _run_claim()
    text = _captured(_dump_graphs, graphs)
    printed_nodes = len(re.findall(r"^  node type=", text, flags=re.M))
    printed_edges = len(re.findall(r"^  edge ", text, flags=re.M))
    printed_graphs = len(re.findall(r"^graph\[\d+\] role=", text, flags=re.M))
    object_nodes = sum(len(g.nodes) for g in graphs)
    object_edges = sum(len(g.edges) for g in graphs)
    assert printed_graphs == len(graphs), (printed_graphs, len(graphs))
    assert printed_nodes == object_nodes, (printed_nodes, object_nodes)
    assert printed_edges == object_edges, (printed_edges, object_edges)
    assert f"graphs collected: {len(graphs)}" in text


def test_collected_equals_capacity_mm_on_claim():
    """On the happy claim shape nothing is filtered: the collected/persisted
    list holds exactly the graphs in `capacity_mm` (§19's cross-check, as a
    test)."""
    mm, graphs = _run_claim()
    mm_ids = {id(g) for g in mm.capacity_mm.graphs.values()}
    collected_ids = {id(g) for g in graphs}
    assert mm_ids == collected_ids
    text = _captured(_dump_mm_delta, mm, graphs)
    assert f"graphs in capacity_mm: {len(graphs)} (collected: {len(graphs)})" in text
    assert "capacity_mm-only graphs" not in text


def test_mm_delta_reported_on_retry():
    """A rejected member attempt's graph stays in `capacity_mm` and out of the
    collected list BY DESIGN — the dump must report that delta, not hide it."""
    failures = {"A. Silva/contents": 1}
    mm, graphs = _run_claim(
        capacities=[
            _decide_declaration(_make_flaky_decide(failures)),
            _conclude_declaration(),
        ],
    )
    mm_graphs = list(mm.capacity_mm.graphs.values())
    assert len(mm_graphs) == len(graphs) + 1, (len(mm_graphs), len(graphs))
    text = _captured(_dump_mm_delta, mm, graphs)
    assert "capacity_mm-only graphs" in text
    assert len(re.findall(r"^graph\[\d+\] role=", text, flags=re.M)) == 1


if __name__ == "__main__":
    for fn in (
        test_printer_counts_match_objects,
        test_collected_equals_capacity_mm_on_claim,
        test_mm_delta_reported_on_retry,
    ):
        fn()
        print(f"PASS {fn.__name__}")
