"""Item 7's guards — G1 (import ban), G2 (raise, never fill), G6 (no internal
tokens), the §30 rulings (correlation, completed-without-conclusion,
single-attempt scope) — each as a test that can go RED.

The tests drive `render_from_graphs` on LIVE harness graphs so they need no
FalkorDB; the persisted path is the §12 command (`dr_render_pages.py`, run by
the owner against a real store — and the smoke already asserted live==persisted
per node, so what these tests pin holds across the boundary).

Run under pytest, or with no dependencies at all:

    PYTHONPATH=. python decision_records_demo/test_dr_render_guards.py
"""

from __future__ import annotations

import ast
import copy
import os

from mindsos_intelligence import execution

from decision_records_demo.dr_dump import (
    DS_CLAIM_EXPOSURES,
    DS_DWELLING_LIMIT,
    DS_POLICY_AS_OF,
    EDITION_2023,
    EXPOSURES,
    _claim_plan,
    _leaf_plan,
    _lookup_declaration,
    _policy_datastates,
    _build_kl,
    _harness,
)
from decision_records_demo.dr_render import (
    NODE_CAPACITY,
    RendererGapError,
    render_from_graphs,
)

EPISODE_COMPLETED = {
    "capacity_root_ref": "unused-by-render_from_graphs",
    "consolidated_at": "2026-08-14T02:04:34.742986+00:00",
    "outcome_classification": "completed",
}
EPISODE_STOPPED = dict(EPISODE_COMPLETED, outcome_classification="stopped")


def _claim_graphs(exposures=None):
    mm, dispatcher, writer, request_run = _harness()
    graphs: list = []
    execution.run(
        dispatcher, writer, _claim_plan(), request_run, mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: list(EXPOSURES if exposures is None else exposures)},
        capacity_graphs=graphs, case_label="claim CLM-2041",
    )
    return graphs


def _refusal_graphs():
    mm, dispatcher, writer, request_run = _harness(
        capacities=[_lookup_declaration()],
        extra_datastates=_policy_datastates(),
        kl=_build_kl(EDITION_2023),
    )
    graphs: list = []
    execution.run(
        dispatcher, writer,
        _leaf_plan("plan:drdemo-refusal", DS_DWELLING_LIMIT, start=DS_POLICY_AS_OF),
        request_run, mm=mm,
        solve_seed={DS_POLICY_AS_OF: "2026-07-01"},
        capacity_graphs=graphs,
        case_label="claim CLM-2041, dwelling limit as of 2026-07-01",
    )
    return graphs


def _delete_node(graph, node_id):
    del graph.nodes[node_id]
    for edge_id in [
        eid for eid, e in graph.edges.items()
        if e.source.node_id == node_id or e.target.node_id == node_id
    ]:
        del graph.edges[edge_id]


def test_g1_import_ban():
    """G1: dr_render imports stdlib + mindsos_core ONLY — never blackboard,
    capacity context, L2 snapshot, Pipeline or chain_artifacts."""
    path = os.path.join(os.path.dirname(__file__), "dr_render.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    allowed_roots = {"__future__", "typing", "mindsos_core"}
    banned_fragments = (
        "blackboard", "context", "chain_artifacts", "pipeline",
        "mindsos_intelligence", "mindsos_capacity", "mindsos_knowledge",
    )
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
    for module in modules:
        root = module.split(".")[0]
        assert root in allowed_roots, f"G1: {module!r} is not an allowed import"
        assert not any(b in module for b in banned_fragments if b != "mindsos_core"), (
            f"G1: {module!r} touches a banned surface"
        )


def test_page_renders_and_is_g6_clean():
    """The claim page renders; G6: no IRI, no reason token, no run-ref
    material reaches it."""
    page = render_from_graphs(_claim_graphs(), EPISODE_COMPLETED)
    assert "Therefore:" in page and "payable" in page
    assert "A. Silva" in page and "B. Osei" in page
    banned = (
        "datastate:", "capacity:", "step_failed", "needs_input",
        "runstopped", "requestrun", "pipelinerun", "drdemo_",
    )
    low = page.lower()
    for token in banned:
        assert token not in low, f"G6: {token!r} leaked onto the page:\n{page}"


def test_g2_deleted_capacity_raises():
    """Probe D's exact mutation: delete the fold's CapacityInstance. The old
    sketch printed 'Given: a return must be filed'; this renderer must RAISE."""
    graphs = [copy.deepcopy(g) for g in _claim_graphs()]
    fold = graphs[-1]
    cap_ids = [nid for nid, n in fold.nodes.items() if n.type_name == NODE_CAPACITY]
    assert cap_ids
    _delete_node(fold, cap_ids[0])
    try:
        render_from_graphs(graphs, EPISODE_COMPLETED)
    except RendererGapError:
        return
    raise AssertionError("G2: a derived value rendered as a premise")


def test_g2_isolated_under_stopped_outcome():
    """The orphan check must be load-bearing on its OWN: with
    outcome='stopped' the Q2 check never runs, so only G2 can catch the
    orphaned conclusion. (Found by mutation: removing check_declared_starts
    reddened nothing until this test existed — the Q2 check was masking it.)"""
    graphs = [copy.deepcopy(g) for g in _claim_graphs()]
    fold = graphs[-1]
    cap_ids = [nid for nid, n in fold.nodes.items() if n.type_name == NODE_CAPACITY]
    _delete_node(fold, cap_ids[0])
    try:
        render_from_graphs(graphs, EPISODE_STOPPED)
    except RendererGapError:
        return
    raise AssertionError("G2 alone did not catch the orphaned conclusion")


def test_completed_without_conclusion_raises():
    """§30 Q2: the Episode says completed, the terminal graph shows no
    conclusion — raise."""
    graphs = [copy.deepcopy(g) for g in _claim_graphs()]
    fold = graphs[-1]
    produced_ids = {
        e.target.node_id for e in fold.edges.values() if e.type_name == "PRODUCES"
    }
    for node_id in list(produced_ids):
        _delete_node(fold, node_id)
    try:
        render_from_graphs(graphs, EPISODE_COMPLETED)
    except RendererGapError:
        return
    raise AssertionError("a success was asserted that the graph cannot show")


def test_order_follows_the_verdicts_list_alone():
    """Bank #7: graph iteration order is irrelevant; the seeded LIST decides.
    Reversing the graphs list changes nothing; reversing the LIST reverses
    the page's member blocks."""
    graphs = _claim_graphs()
    page = render_from_graphs(graphs, EPISODE_COMPLETED)
    page_reversed_graphs = render_from_graphs(list(reversed(graphs)), EPISODE_COMPLETED)
    assert page == page_reversed_graphs
    mutated = [copy.deepcopy(g) for g in graphs]
    fold = mutated[-1]
    for node in fold.nodes.values():
        if isinstance(node.value, list):
            node.value.reverse()
    page_reversed_list = render_from_graphs(mutated, EPISODE_COMPLETED)
    assert page != page_reversed_list
    assert page_reversed_list.splitlines()[3].endswith("hail, 12 March")
    assert "B. Osei" in page_reversed_list.splitlines()[3]


def test_missing_member_raises():
    """§30 Q1: a verdict entry matching no member graph is a gap."""
    graphs = _claim_graphs()
    without_member = [graphs[0]] + graphs[2:]
    try:
        render_from_graphs(without_member, EPISODE_COMPLETED)
    except RendererGapError:
        return
    raise AssertionError("a recorded verdict without its run graph rendered")


def test_single_attempt_scope_raises_on_two_folds():
    """§31: two terminal-shaped graphs — refuse to guess which is the Record."""
    graphs = _claim_graphs()
    doubled = graphs + [copy.deepcopy(graphs[-1])]
    try:
        render_from_graphs(doubled, EPISODE_COMPLETED)
    except RendererGapError:
        return
    raise AssertionError("two attempts rendered as one Record")


def test_refusal_page_is_in_band_and_g6_clean():
    """The refusal renders from origin-record fields with the run SUCCEEDED —
    and no IRI (source_datastate is a link) reaches the page."""
    page = render_from_graphs(_refusal_graphs(), EPISODE_COMPLETED)
    assert "Nothing." in page
    assert "no edition covering 2026-07-01" in page
    low = page.lower()
    for token in ("datastate:", "capacity:", "read_from_source", "no_source_in_force"):
        assert token not in low, f"G6: {token!r} leaked:\n{page}"


def test_boundary_stop_page():
    """n=0: the reducer's refusal renders as a stop with its prose detail."""
    page = render_from_graphs(_claim_graphs([]), EPISODE_STOPPED)
    assert "Stopped: a step could not be completed." in page
    assert "refusing to conclude a claim from zero exposure verdicts" in page


if __name__ == "__main__":
    for fn in sorted(
        (v for k, v in list(globals().items()) if k.startswith("test_")),
        key=lambda f: f.__name__,
    ):
        fn()
        print(f"PASS {fn.__name__}")
