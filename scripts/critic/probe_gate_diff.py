"""Probe: does an AMOUNTS-ONLY edit's page diff name the edition/source?

Grounds coordination 109.1 (answers 108.1 Q1). Run from a checkout containing
decision_records_demo/ and mindsos_* (ship-B code, f141deb / merged df57033 —
NOT this branch, which is off main and carries no demo dir):

    PYTHONPATH=. python scripts/critic/probe_gate_diff.py

Two edits of EDITION_2023's stated limit against the beat-4 prior page
(claim 400000): non-degenerate (350000 -> 360000) and equality
(350000 -> 400000). Output is repr-only unified diffs below a seam line;
all verdicts live in the coordination file, never here.
"""
import difflib

from mindsos_intelligence import execution
from decision_records_demo.dr_assessment import (
    CASE_ASSESSED_PRIOR, DS_ASSESSED_CLAIM, assessment_harness, assessment_plan,
)
from decision_records_demo.dr_render import render_from_graphs
from decision_records_demo.dr_dump import EDITION_2023, EDITION_2024

EP = {
    "capacity_root_ref": "unused-by-render_from_graphs",
    "consolidated_at": "2026-08-15T12:00:00.000000+00:00",
    "outcome_classification": "completed",
}


def page(claim, *eds):
    mm, dispatcher, writer, request_run = assessment_harness(*eds)
    graphs = []
    execution.run(
        dispatcher, writer, assessment_plan(), request_run, mm=mm,
        solve_seed={DS_ASSESSED_CLAIM: dict(claim)},
        capacity_graphs=graphs, case_label="claim CLM-4188",
    )
    return render_from_graphs(graphs, EP)


def edited(value):
    return dict(
        EDITION_2023,
        stated_value=value,
        text="The dwelling coverage limit is {:,}.".format(value),
    )


before = page(CASE_ASSESSED_PRIOR, EDITION_2023, EDITION_2024)

print("== raw output below this line ==")
for label, value in (("nondegenerate_360000", 360000), ("equality_400000", 400000)):
    after = page(CASE_ASSESSED_PRIOR, edited(value), EDITION_2024)
    print(repr("[" + label + "]"))
    for line in difflib.unified_diff(
        before.splitlines(), after.splitlines(), lineterm=""
    ):
        print(repr(line))
