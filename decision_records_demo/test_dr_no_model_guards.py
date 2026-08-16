"""Beat 5's guards — the model is not in the decision path, structurally.

Open decision 9 (2026-08-16) rules Phase 7's intake STRUCTURED: the demo runs
with **no model and no transport**. Its stated gain is that claim 5 — *the
model reads, it does not decide* — "stops being asserted and becomes
structurally unarguable". Until this file, it was asserted in prose and
pinned by nothing, which is the shape RULES §11 exists to refuse.

Beat 5 in the room is *"unplug the model"*. Under decision 9 there is nothing
on our side to unplug — the contrast lives entirely on Screen B, the frontier
LLM the room is comparing against. So the beat's claim about MindsOS is a
claim about absence, and absence is exactly what a guard can check.

**Two independent checks, because either alone is weak.**

* **Statically** no demo module imports the model seam. A file cannot call
  what it never imported.
* **At runtime** no origin record any demo case produces carries
  ``read_by_model``. This is the stronger half: it would catch a model
  reached through a registered capacity rather than an import.

**Neither may pass vacuously**, which is this lane's recorded trap (PR #169's
isolation guard walked its own list, so emptying the list made it check
nothing). So both ask the filesystem and the graphs rather than a constant:
the module list is globbed and the record count is asserted non-zero before
its contents are judged. ⚠ **And the import ban is currently checking
something unreachable** — the seam is not on the core this branch pins, which
is what :func:`test_the_pinned_core_carries_no_model_seam` states and watches.
Read the two together.

    PYTHONPATH=. python decision_records_demo/test_dr_no_model_guards.py
"""

from __future__ import annotations

import ast
import glob
import os

from mindsos_capacity.builtins.origin_v0 import (
    FIELD_ORIGIN_METHOD,
    ORIGIN_METHODS,
    ORIGIN_READ_BY_MODEL,
)
from mindsos_intelligence import execution

#: Import paths a demo module may not reach. The seam is real code on `main`
#: (`mindsos_capacity/llm`, PR #169) but is NOT on the core this branch pins —
#: see :func:`test_the_pinned_core_carries_no_model_seam`, which watches for
#: the pin bump that would make this ban load-bearing.
SEAM_MODULES = ("mindsos_capacity.llm", "mindsos_capacity.builtins.comprehension_v0")

HERE = os.path.dirname(__file__)


def _demo_modules():
    """Every non-test module in this directory, from the FILESYSTEM."""
    return sorted(
        path for path in glob.glob(os.path.join(HERE, "*.py"))
        if not os.path.basename(path).startswith("test_")
    )


def _imported_modules(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            out.append(node.module or "")
    return out


def _case_graphs():
    """Every case this file can run without a store, with its own harness.

    Deliberately not a hand-kept list of records: the graphs come from the
    demo's own case builders, so a new case that reaches a model is caught
    by the case existing, not by someone remembering to add it here.
    """
    from decision_records_demo.dr_routing import (
        CASE_A_EXPOSURES, CASE_B_EXPOSURES,
        DS_CLAIM_EXPOSURES as DS_ROUTED, routing_harness, routing_plan,
    )
    from decision_records_demo.dr_settlement import (
        CASE_MISSING_DOCUMENT, DS_CLAIM_INTAKE,
        settlement_capacities, settlement_datastates, settlement_plan,
    )
    from decision_records_demo.dr_dump import _harness

    graphs: list = []
    for exposures in (CASE_A_EXPOSURES, CASE_B_EXPOSURES):
        mm, dispatcher, writer, request_run = routing_harness()
        execution.run(
            dispatcher, writer, routing_plan(), request_run, mm=mm,
            solve_seed={DS_ROUTED: [dict(e) for e in exposures]},
            capacity_graphs=graphs, case_label="claim CLM-3007",
        )
    mm, dispatcher, writer, request_run = _harness(
        capacities=settlement_capacities(),
        extra_datastates=settlement_datastates(),
    )
    execution.run(
        dispatcher, writer, settlement_plan(), request_run, mm=mm,
        solve_seed={DS_CLAIM_INTAKE: dict(CASE_MISSING_DOCUMENT)},
        capacity_graphs=graphs, case_label="claim CLM-5093",
    )
    return graphs


def _origin_records(graphs):
    return [
        node.value
        for graph in graphs
        for node in graph.nodes.values()
        if isinstance(node.value, dict) and FIELD_ORIGIN_METHOD in node.value
    ]


def test_the_pinned_core_carries_no_model_seam():
    """The strongest form of beat 5\'s claim, and it was found by writing the
    weaker one: **the core this demo pins does not contain the seam at all.**
    `mindsos_capacity/llm` shipped to `main` in PR #169, three ships after
    `dr-partial-record-confirmed`, and this branch has not merged it — so on
    the demo\'s own core there is no model to reach, imported or not.

    This is also the vacuity guard for the import ban below: while it passes,
    that ban is checking something unreachable. The day a pin bump brings the
    seam in, THIS test reddens — and the ban becomes the load-bearing one.
    Re-read both together at that point; do not silence this one."""
    import importlib.util

    present = [m for m in SEAM_MODULES if importlib.util.find_spec(m) is not None]
    assert not present, (
        f"the pinned core now carries {present!r}. Beat 5\'s claim is no "
        "longer structural-by-absence: the import ban below is now the guard "
        "that matters, and it must be read as load-bearing."
    )


def test_no_demo_module_imports_the_model_seam():
    """Statically: the demo cannot call a model it never imported. The module
    list is globbed, so a new file is covered by existing, not by being added
    to a list here."""
    modules = _demo_modules()
    assert len(modules) >= 7, f"the glob found only {len(modules)} modules — vacuous"
    for path in modules:
        for imported in _imported_modules(path):
            for banned in SEAM_MODULES:
                assert not imported.startswith(banned), (
                    f"{os.path.basename(path)} imports {imported!r} — the demo "
                    "runs with no model (open decision 9)"
                )


def test_no_case_produces_a_value_read_by_a_model():
    """At runtime, and this is the half that would catch a model reached
    through a registered capacity rather than an import: every origin record
    every case produces says where its value came from, and none of them says
    a model read it."""
    records = _origin_records(_case_graphs())
    assert len(records) >= 4, (
        f"only {len(records)} origin records across every case — the guard "
        "would pass on a demo that recorded nothing"
    )
    for record in records:
        method = record.get(FIELD_ORIGIN_METHOD)
        assert method in ORIGIN_METHODS, f"unknown origin method {method!r}"
        assert method != ORIGIN_READ_BY_MODEL, (
            "a demo case produced a value a model read — claim 5 says the "
            "model reads and does not decide, and decision 9 says there is "
            "no model here at all"
        )


if __name__ == "__main__":
    for fn in sorted(
        (v for k, v in list(globals().items()) if k.startswith("test_")),
        key=lambda f: f.__name__,
    ):
        fn()
        print(f"PASS {fn.__name__}")
