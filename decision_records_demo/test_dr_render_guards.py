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
    G6_BANNED,
    MANIFEST_MEMBER_IDS,
    NODE_CAPACITY,
    RendererGapError,
    render_from_graphs,
)


def _strip_member_ids(graphs):
    """A no-manifest-road fixture: the same graphs with the am-5 key removed
    from every manifest (a fold-only or degraded/stale record)."""
    stripped = [copy.deepcopy(g) for g in graphs]
    for graph in stripped:
        for node in graph.nodes.values():
            if node.type_name == "RunManifest":
                node.value.pop(MANIFEST_MEMBER_IDS, None)
    return stripped


def _partial_graphs():
    """The memberpartial shape: member 2 fails at MEMBER_RETRY_CAP, stops in
    place, the fold stops partial_domain (ADR-0201 am-6)."""
    from decision_records_demo.dr_dump import (
        _conclude_declaration, _decide_declaration, _make_flaky_decide,
    )
    mm, dispatcher, writer, request_run = _harness(
        capacities=[
            _decide_declaration(_make_flaky_decide({"A. Silva/contents": 99})),
            _conclude_declaration(),
        ],
    )
    graphs: list = []
    execution.run(
        dispatcher, writer, _claim_plan(), request_run, mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: list(EXPOSURES)},
        capacity_graphs=graphs, case_label="claim CLM-2041",
    )
    return graphs

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
    assert "Q." not in page, "no stored question exists here; Q. must be earned"
    banned = G6_BANNED + ("drdemo_",)
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


def test_order_follows_the_record_alone():
    """Bank #7 RESTATED on the manifest road: graph iteration order is
    irrelevant (kept half, verbatim); the RECORD decides order — reversing
    the ids AND the list together reverses the page, while reversing the
    list ALONE is the record and the value bus out of step, and raises."""
    graphs = _claim_graphs()
    page = render_from_graphs(graphs, EPISODE_COMPLETED)
    page_reversed_graphs = render_from_graphs(list(reversed(graphs)), EPISODE_COMPLETED)
    assert page == page_reversed_graphs
    coherent = [copy.deepcopy(g) for g in graphs]
    fold = coherent[-1]
    for node in fold.nodes.values():
        if isinstance(node.value, list):
            node.value.reverse()
        if node.type_name == "RunManifest":
            node.value[MANIFEST_MEMBER_IDS] = list(
                reversed(node.value[MANIFEST_MEMBER_IDS])
            )
    page_reversed_record = render_from_graphs(coherent, EPISODE_COMPLETED)
    assert page != page_reversed_record
    assert page_reversed_record.splitlines()[3].startswith("B. Osei")
    tampered = [copy.deepcopy(g) for g in graphs]
    fold = tampered[-1]
    for node in fold.nodes.values():
        if isinstance(node.value, list):
            node.value.reverse()
    try:
        render_from_graphs(tampered, EPISODE_COMPLETED)
    except RendererGapError as exc:
        assert "out of step" in str(exc)
    else:
        raise AssertionError("a list reversed against its ids rendered")


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
    assert "Q. What dwelling coverage limit was in force on 2026-07-01?" in page, (
        "the stored question EARNS the Q. line (source rule)"
    )
    assert "Nothing." in page
    assert "no edition covering 2026-07-01" in page
    low = page.lower()
    for token in ("datastate:", "capacity:", "read_from_source", "no_source_in_force"):
        assert token not in low, f"G6: {token!r} leaked:\n{page}"


def test_render_time_g6_refuses_a_tainted_store():
    """Critic §33 M-D, as a permanent guard: an IRI smuggled into a STORED
    manifest phrase must never render — the renderer scans its own composed
    page and raises. Test-time G6 only sees the fixtures it was written with;
    this closes the class (bad fixture, tampered store, future producer)."""
    graphs = [copy.deepcopy(g) for g in _claim_graphs()]
    for graph in graphs:
        for node in graph.nodes.values():
            if node.type_name == "RunManifest":
                phrases = node.value["capacity_phrases"]
                for key in list(phrases):
                    phrases[key] = phrases[key] + " (datastate:smuggled)"
    try:
        render_from_graphs(graphs, EPISODE_COMPLETED)
    except RendererGapError:
        return
    raise AssertionError("a tainted stored phrase rendered an IRI to the page")


def test_noroute_page_names_what_was_in_hand():
    """The manifest-only page still says what the run HAD (owner polish,
    2026-08-14): the declared-start descriptions print above the stop line."""
    from decision_records_demo.dr_dump import DS_EXPOSURE, DS_UNREACHED
    from mindsos_intelligence.execution import LeafPipelineNotFound
    mm, dispatcher, writer, request_run = _harness()
    graphs: list = []
    try:
        execution.run(
            dispatcher, writer,
            _leaf_plan("plan:drdemo-noroute", DS_UNREACHED, start=DS_EXPOSURE),
            request_run, mm=mm,
            solve_seed={DS_EXPOSURE: EXPOSURES[0]},
            capacity_graphs=graphs, case_label="claim CLM-2041, unroutable ask",
        )
    except LeafPipelineNotFound:
        pass
    page = render_from_graphs(graphs, EPISODE_STOPPED)
    assert "In hand: one exposure, as filed" in page
    assert "Stopped before any step could run" in page
    assert "datastate:" not in page.lower()


def test_boundary_stop_page():
    """n=0 RESTATED on the am-5 core: the FOLD stops pre-dispatch with
    empty_domain — the reducer is never asked, so its refusal prose cannot
    appear; the stop phrase comes from the manifest snapshot (tokens branch,
    phrases print)."""
    page = render_from_graphs(_claim_graphs([]), EPISODE_STOPPED)
    assert (
        "Stopped: there was nothing to decide from - the collection had no "
        "members." in page
    ), page
    assert "refusing to conclude" not in page, "the reducer never ran"
    assert "empty_domain" not in page.lower()


def test_unmatched_member_graph_raises():
    """N-F1 (coordination §37, confirmed by the critic's probe): a member graph
    whose verdict appears in NO list entry used to render nothing and raise
    nothing — the exposure simply vanished from the page. The correlation now
    runs both directions, so the leftover member is a gap."""
    graphs = [copy.deepcopy(g) for g in _claim_graphs()]
    fold = graphs[-1]
    for node in fold.nodes.values():
        if isinstance(node.value, list):
            node.value.pop()
    try:
        render_from_graphs(graphs, EPISODE_COMPLETED)
    except RendererGapError as exc:
        assert "leaves a member out" in str(exc)
        assert "'" in str(exc), "the raise must name the unmatched graph role"
        return
    raise AssertionError("a member graph was dropped from the page silently")


def test_identical_bare_verdicts_do_not_collapse_onto_one_member():
    """N-F2, RE-SCOPED to the no-manifest road (am-5 consequence — never
    deleted): with the am-5 key stripped and the exposure stripped out of the
    verdict VALUE, every entry matches every member — ambiguity, not
    interchangeability, and the raise names this road's own classification
    ambiguity. On the manifest road identical bare verdicts are LEGAL
    (position correlates them); test_identical_bare_verdicts_render_by_position
    pins that half."""
    graphs = _strip_member_ids(_claim_graphs())
    fold = graphs[-1]
    for node in fold.nodes.values():
        if isinstance(node.value, list):
            node.value[:] = ["payable"] * len(node.value)
    for member in graphs[:-1]:
        produced = {
            e.target.node_id for e in member.edges.values()
            if e.type_name == "PRODUCES"
        }
        for node_id, node in member.nodes.items():
            if node_id in produced and isinstance(node.value, dict) \
                    and "decision" in node.value:
                node.value = "payable"
    try:
        render_from_graphs(graphs, EPISODE_COMPLETED)
    except RendererGapError as exc:
        assert "do not render alike" in str(exc)
        assert "no-manifest road" in str(exc), "the raise names the road"
        return
    raise AssertionError("identical verdict values collapsed onto one member")


def test_a_genuinely_duplicated_exposure_still_renders():
    """The bijection must not over-constrain (critic §37 Q1). Two IDENTICAL
    exposures render byte-identical blocks, so the assignment is genuinely
    interchangeable — §30's argument, and it must still hold."""
    page = render_from_graphs(
        _claim_graphs([EXPOSURES[0], EXPOSURES[0]]), EPISODE_COMPLETED
    )
    assert page.count("A. Silva") == 2, page


def test_missing_decided_date_is_stated_not_omitted():
    """§52 condition 1 (owner-adopted §53): a page with no `consolidated_at`
    STATES the absence in room-safe words — a silently missing date line is
    indistinguishable from a renderer bug (G2's principle applied to the page
    itself). This is the from-root page's shape: the Episode is not
    store-resident (§51.1), so a store-only render has no date to prove."""
    graphs = _claim_graphs()
    dateless = {
        "capacity_root_ref": "unused-by-render_from_graphs",
        "consolidated_at": "",
        "outcome_classification": None,
    }
    page = render_from_graphs(graphs, dateless)
    assert "Decided date: not available from stored evidence" in page, page
    dated = render_from_graphs(graphs, EPISODE_COMPLETED)
    assert "Decided 2026-08-14" in dated
    assert "not available from stored evidence" not in dated


def test_identical_bare_verdicts_render_by_position():
    """The manifest road's half of N-F2: identical bare verdict values are
    LEGAL where a map supplied ids — position correlates them, and every
    member block renders once."""
    graphs = [copy.deepcopy(g) for g in _claim_graphs()]
    fold = graphs[-1]
    for node in fold.nodes.values():
        if isinstance(node.value, list):
            node.value[:] = ["payable"] * len(node.value)
    for member in graphs[:-1]:
        produced = {
            e.target.node_id for e in member.edges.values()
            if e.type_name == "PRODUCES"
        }
        for node_id, node in member.nodes.items():
            if node_id in produced and isinstance(node.value, dict) \
                    and "decision" in node.value:
                node.value = "payable"
    page = render_from_graphs(graphs, EPISODE_COMPLETED)
    assert page.count("payable") >= 3
    assert "A. Silva" in page and "B. Osei" in page


def test_swapped_ids_raise_out_of_step():
    """§72 Q4-1: order is a changed behaviour with its own red — two DISTINCT
    members' ids swapped must fail the per-position cross-check, not render
    swapped blocks."""
    graphs = [copy.deepcopy(g) for g in _claim_graphs()]
    fold = graphs[-1]
    for node in fold.nodes.values():
        if node.type_name == "RunManifest":
            ids = node.value[MANIFEST_MEMBER_IDS]
            ids[0], ids[2] = ids[2], ids[0]
    try:
        render_from_graphs(graphs, EPISODE_COMPLETED)
    except RendererGapError as exc:
        assert "out of step" in str(exc)
        return
    raise AssertionError("swapped ids rendered swapped members silently")


def test_stop_graph_with_produced_verdict_is_incoherent():
    """§72 Q2's precedence rule, the raise half: a member graph carrying BOTH
    a RunStopped and a produced verdict-typed value never classifies — it
    raises as incoherent."""
    partial = [copy.deepcopy(g) for g in _partial_graphs()]
    stopped_member = next(
        g for g in partial
        if any(n.type_name == "RunStopped" for n in g.nodes.values())
        and any(isinstance(n.value, dict) for n in g.nodes.values())
        and g is not partial[-1]
    )
    donor = partial[0]
    verdict_nodes = [
        (nid, n) for nid, n in donor.nodes.items()
        if (n.properties or {}).get("datastate_type", "").endswith("exposure_verdict")
    ]
    assert verdict_nodes, "fixture: the donor member must carry a verdict"
    nid, node = verdict_nodes[0]
    stopped_member.nodes[nid] = copy.deepcopy(node)
    donor_edge = next(
        e for e in donor.edges.values()
        if e.type_name == "PRODUCES" and e.target.node_id == nid
    )
    stopped_member.edges[f"forged-{nid}"] = copy.deepcopy(donor_edge)
    try:
        render_from_graphs(partial, EPISODE_STOPPED)
    except RendererGapError as exc:
        assert "incoherent" in str(exc)
        return
    raise AssertionError("a stopped member with a produced verdict classified")


def test_partial_page_stop_block_in_place():
    """am-6 rendered: the failed member's stop block sits at ITS position
    between its siblings' blocks, and the fold's partial_domain stop line
    closes the page — no conclusion, nothing dropped."""
    page = render_from_graphs(_partial_graphs(), EPISODE_STOPPED)
    first = page.find("A. Silva, hail, 12 March, dwelling".split(",")[0])
    assert "Stopped: a step could not be completed." in page
    assert (
        "Stopped: some of what was needed could not be completed, so no "
        "overall conclusion was drawn." in page
    ), page
    assert "Therefore:" not in page
    assert "B. Osei" in page
    stop_at = page.find("Stopped: a step could not be completed.")
    osei_at = page.find("B. Osei")
    assert first < stop_at < osei_at, "the stop block renders in place"
    low = page.lower()
    for token in G6_BANNED:
        assert token not in low, f"G6: {token!r} leaked:\n{page}"


def test_manifest_only_member_renders_no_route_block():
    """am-5's clean form: a manifest-only member graph (run-4's no-route
    shape) renders the no-route stop block at its position and consumes no
    list entry."""
    graphs = [copy.deepcopy(g) for g in _claim_graphs()]
    fold = graphs[-1]
    member = graphs[1]
    for node_id in list(member.nodes):
        if member.nodes[node_id].type_name != "RunManifest":
            del member.nodes[node_id]
    member.edges.clear()
    for node in fold.nodes.values():
        if isinstance(node.value, list):
            del node.value[1]
    page = render_from_graphs(graphs, EPISODE_STOPPED)
    assert "Stopped before any step could run" in page
    assert "A. Silva" in page and "B. Osei" in page


def test_manifest_naming_a_missing_graph_raises():
    """The id list promises a member the Episode cannot show — raise, the
    manifest-road form of the missing-member gap."""
    graphs = _claim_graphs()
    without_member = [graphs[0]] + graphs[2:]
    try:
        render_from_graphs(without_member, EPISODE_COMPLETED)
    except RendererGapError as exc:
        assert "not in this Episode" in str(exc)
        return
    raise AssertionError("a promised member graph was silently absent")


def test_empty_list_with_member_graphs_raises():
    """§72 Q4-3: key present, the list emptied, member graphs still in the
    Episode — the short-list raise fires; nothing renders as if complete."""
    graphs = [copy.deepcopy(g) for g in _claim_graphs()]
    fold = graphs[-1]
    for node in fold.nodes.values():
        if isinstance(node.value, list):
            node.value[:] = []
    try:
        render_from_graphs(graphs, EPISODE_COMPLETED)
    except RendererGapError as exc:
        assert "leaves a member out" in str(exc)
        return
    raise AssertionError("an emptied list rendered a complete-looking page")


def test_old_reds_stay_red_on_the_no_manifest_road():
    """§72 Q4-5 (the F2 census rule applied to a road move): the OLD
    bijection mutation set re-run with the am-5 key stripped — every old red
    stays red, and the genuinely-duplicated exposure still renders."""
    stripped = _strip_member_ids(_claim_graphs())
    without_member = [stripped[0]] + stripped[2:]
    try:
        render_from_graphs(without_member, EPISODE_COMPLETED)
    except RendererGapError as exc:
        assert "matches no run graph" in str(exc)
    else:
        raise AssertionError("no-manifest road: missing member rendered")
    popped = [copy.deepcopy(g) for g in stripped]
    for node in popped[-1].nodes.values():
        if isinstance(node.value, list):
            node.value.pop()
    try:
        render_from_graphs(popped, EPISODE_COMPLETED)
    except RendererGapError as exc:
        assert "leaves a member out" in str(exc)
    else:
        raise AssertionError("no-manifest road: unmatched member rendered")
    dup = _strip_member_ids(_claim_graphs([EXPOSURES[0], EXPOSURES[0]]))
    page = render_from_graphs(dup, EPISODE_COMPLETED)
    assert page.count("A. Silva") == 2


if __name__ == "__main__":
    for fn in sorted(
        (v for k, v in list(globals().items()) if k.startswith("test_")),
        key=lambda f: f.__name__,
    ):
        fn()
        print(f"PASS {fn.__name__}")
