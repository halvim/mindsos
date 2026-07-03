"""arc-viz LIVE combined run — the ARC brain: solve THEN communicate, one L4.

Unlike the fixtures gate, this stands up the real MindsOS instance (the solver's
`build_instance`), registers the viz caps on the SAME CapacityLayer, and dispatches
the whole chain through ONE `L4Dispatcher`:

    emit_candidates -> select_rules -> apply_solution   (solve, L3 reasoning)
        -> ingest_solve -> express                      (communicate, L3 communication)

This is the integration DRIVER (a harness), so it imports the solver; the viz
CAPACITIES (`capabilities.py`) still import nothing from the solver — they consume
the `arc.*` DataStates the dispatched solver caps produce.
"""

from __future__ import annotations

from mindsos_capacity.identifiers import capacity_iri

from arc_solver.solve import pipeline
from arc_solver.spike import arc_capacities as ac
from arc_solver.spike.arc_grids import load_dataset
from arc_solver.spike.arc_l4 import build_instance

from .capabilities import (
    CATEGORY_COMMUNICATION,
    DS_ARTIFACT,
    DS_EXPRESSIBLE_RECORD,
    install_viz,
)

_CAP_INGEST = capacity_iri(CATEGORY_COMMUNICATION, "ingest_solve")
_CAP_EXPRESS = capacity_iri(CATEGORY_COMMUNICATION, "express")


def artifact_for(inst, task_id: str, dataset: dict) -> dict:
    """Dispatch solve (8/9/10) then communicate (ingest/express) through inst's
    single L4Dispatcher; return the communication artifact."""
    disp = inst.dispatcher
    ctx = pipeline.run_all(task_id, dataset)
    profile, enclosed = ctx["profile"], ctx.get("enclosed")
    base = {ac.DS_PROFILE: profile, ac.DS_ENCLOSED: enclosed}

    rules = disp.dispatch(ac.CAP_EMIT_CANDIDATES, {
        **base, ac.DS_BG_CAND: ctx.get("bg_cand"),
        ac.DS_RECOMPARISON: ctx.get("recomparison")}).outputs[ac.DS_RULES]
    sel = disp.dispatch(ac.CAP_SELECT_RULES, {
        **base, ac.DS_RULES: rules}).outputs[ac.DS_SELECTION]
    solve = disp.dispatch(ac.CAP_APPLY_SOLUTION, {
        **base, ac.DS_RULES: rules, ac.DS_SELECTION: sel,
        ac.DS_RAW_TASK: ctx.get("raw")}).outputs[ac.DS_SOLVE]

    record = disp.dispatch(_CAP_INGEST, {
        ac.DS_PROFILE: profile, ac.DS_RULES: rules, ac.DS_SELECTION: sel,
        ac.DS_SOLVE: solve, ac.DS_ENCLOSED: enclosed}).outputs[DS_EXPRESSIBLE_RECORD]
    artifact = disp.dispatch(_CAP_EXPRESS, {
        DS_EXPRESSIBLE_RECORD: record}).outputs[DS_ARTIFACT]
    return artifact


#: two solved rule families, communicated end-to-end.
_CASES = [("00d62c1b", "#2 recolor-enclosed"), ("05f2a901", "#8 move-to-touching")]


def main() -> int:
    inst = build_instance()          # real MindsOS instance: arc caps (Global) + v0/consolidate/…
    install_viz(inst.layer)          # viz caps on the SAME layer -> one brain
    dataset = load_dataset()
    for task_id, name in _CASES:
        art = artifact_for(inst, task_id, dataset)
        outcome = art["header"]["outcome"]
        assert outcome == "verified", (task_id, outcome)
        assert art["summary"].startswith("Solved by"), art["summary"]
        print(f"  [ok] arc-viz LIVE: {name} — solve->ingest_solve->express through ONE "
              f"L4 -> outcome=verified; {art['summary']!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
