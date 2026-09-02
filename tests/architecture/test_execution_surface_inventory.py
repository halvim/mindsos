"""Sentinel — the run-surface inventory, derived by grep, closed by this test.

RULES §12 (the sweep) rests on a **mechanical** surface inventory: every gap in
the Decision Records lane's ten-gap history had the shape *a quantified claim
checked on one element of its domain* — "every run leaves a graph", verified on
the leaf while ``_run_member_pipeline`` minted nothing (gap 7) and
``_run_fold_milestone`` grounded nothing (gap 10). Recalled surface lists are
the failure being fixed: the lane that recalls seams is the lane that missed
the member path. So the inventory is **derived from the source**, and this
test pins it exactly.

A ship that adds a caller of ``execute_pipeline``, a direct ``.dispatch(``
site, a persistence entry point, or an executor REDDENS this test — that is
its purpose. The fix is never to widen a regex until it is green again: it is
to add the new surface here **with its classification**, and to add the
corresponding matrix row to the sweep in the same ship (RULES §12.1).

Classifications used below:

* **grounding-executor** — the one function that grounds a run
  (``execute_pipeline``); every run-shaped execution must pass through it.
* **executor-caller** — a run path entering the grounding executor.
* **L4-policy-meta** — a single policy/meta capacity dispatched outside a run
  (replan check, sufficient predicate, blame, consolidation, dream, crash
  recovery, plan construction, submind priority scoring). Deliberately
  ungrounded; a dispatch here becoming run-shaped is exactly what this
  sentinel must announce.
* **notional-runner** — ``mindsos_server.pipeline_runner.run_pipeline``: runs
  steps and grounds nothing (the open §3.6 surface; being listed is not being
  endorsed).
* **outside-service call** — a path that hands control to code MindsOS does
  not own (a database driver, a model provider). Added 2026-08-16: the four
  censuses above are all about RUN shape, and a stub client doing live
  network IO dropped into ``mindsos_llm/`` left this file 6/6 GREEN
  (critic re-run, coordination §88). The first code path that leaves the
  machine was invisible to every axis.

⚠ **A census counts source TEXT, so it counts comments and docstrings too.**
A token this file censuses must not appear in prose anywhere under
``mindsos_*`` — caught while adding the axis below, when a new explanatory
comment became the census's only "match". If a census needs a token that
prose wants too, rewrite the prose.

The fold's former direct dispatch (``execution.py``, gap 10) was on this
census before the fold-grounding CR removed it; its absence is asserted, not
assumed.
"""

from __future__ import annotations

import re
from pathlib import Path

_PACKAGES = (
    "mindsos_core",
    "mindsos_knowledge",
    "mindsos_capacity",
    "mindsos_intelligence",
    "mindsos_llm",
    "mindsos_instances",
    "mindsos_admin",
    "mindsos_server",
    "mindsos_cli",
)


def _source_root() -> Path:
    """Marker-free package anchor — mirrors ``test_no_subsystem_ownership``:
    the test image copies the packages + ``tests`` but not the repo-root
    markers, so anchoring on the packages works in a checkout and in the
    container alike."""
    for parent in Path(__file__).resolve().parents:
        if all((parent / pkg).is_dir() for pkg in _PACKAGES):
            return parent
    try:
        import mindsos_capacity

        candidate = Path(mindsos_capacity.__file__).resolve().parent.parent
        if all((candidate / pkg).is_dir() for pkg in _PACKAGES):
            return candidate
    except Exception:  # noqa: BLE001 — fall through to the explicit error
        pass
    raise RuntimeError(
        "source root not found: no directory above this test contains all of "
        f"{list(_PACKAGES)}"
    )


def _census(pattern: str) -> dict[str, int]:
    """``{repo-relative path: match count}`` across every ``mindsos_*`` module,
    zero-count files omitted."""
    root = _source_root()
    rx = re.compile(pattern)
    counts: dict[str, int] = {}
    for pkg in _PACKAGES:
        for path in sorted((root / pkg).rglob("*.py")):
            n = len(rx.findall(path.read_text(encoding="utf-8")))
            if n:
                counts[str(path.relative_to(root))] = n
    return counts


#: Call sites entering the grounding executor. The three in ``execution.py``
#: are the leaf, the member, and — fold-grounding CR — the fold; before that CR
#: the fold bypassed the executor entirely and left nothing in the graph.
EXPECTED_EXECUTOR_CALLERS = {
    "mindsos_intelligence/execution.py": 3,          # executor-caller: leaf, member, fold
    "mindsos_intelligence/phase_1.py": 1,            # executor-caller: MM-less interpret carve-out
    "mindsos_intelligence/submind_arbiter.py": 1,    # executor-caller: submind grounded run
}

#: Direct dispatch sites — everything that invokes a capacity WITHOUT the
#: grounding executor. Each is a deliberate single-capacity L4-policy-meta
#: dispatch, except the server's notional runner. ``execution.py`` must NOT
#: appear: its former fold dispatch was gap 10.
EXPECTED_DIRECT_DISPATCH = {
    "mindsos_intelligence/pipeline_execution.py": 1,  # grounding-executor: the step walk itself
    "mindsos_intelligence/phase_1.py": 1,             # L4-policy-meta: interpret step
    "mindsos_intelligence/phase_6.py": 1,             # L4-policy-meta: blame
    "mindsos_intelligence/consolidation.py": 3,       # L4-policy-meta: consolidate
    "mindsos_intelligence/plan_construction.py": 3,   # L4-policy-meta: plan derive/walk
    "mindsos_intelligence/orchestrator.py": 1,        # L4-policy-meta: planner scoring
    "mindsos_intelligence/replan_check.py": 1,        # L4-policy-meta: replan predicate
    "mindsos_intelligence/sufficient_predicate.py": 1,  # L4-policy-meta: sufficiency
    "mindsos_intelligence/dream_cycle.py": 1,         # L4-policy-meta: dream driver
    "mindsos_intelligence/crash_recovery.py": 1,      # L4-policy-meta: startup scan
    "mindsos_intelligence/submind_arbiter.py": 1,     # L4-policy-meta: priority scoring
    "mindsos_server/pipeline_runner.py": 1,           # notional-runner: grounds nothing (§3.6)
    "mindsos_cli/commands/brain.py": 1,               # cli-direct: operator single dispatch
}

#: The only door persistence has (ADR-0207 D10 restated at the entry level):
#: ``persist_capacity_mm`` is reached from consolidation and nowhere else —
#: "rendered from the PERSISTED graph" is unmet until a Decision Records path
#: joins this census, and joining it must redden this sentinel first.
EXPECTED_PERSISTENCE_CALLERS = {
    "mindsos_intelligence/consolidation.py": 1,
}

#: Outside-service imports — every place a ``mindsos_*`` module reaches for
#: a driver or the network directly. Both entries are the persistence layer
#: talking to FalkorDB, which is the ONE outside service core has ever had.
#:
#: A third entry means a second one arrived; classify it or route it through
#: a deployment-supplied seam, the way the model client does (the transport
#: is a callable the deployment passes, so ``mindsos_llm`` imports
#: no network library at all and is deliberately ABSENT from this census —
#: its own axis is the consumption census, which arrives with its first
#: consumer).
EXPECTED_OUTSIDE_SERVICE_IMPORTS = {
    "mindsos_core/persistence/client.py": 1,             # outside-service call: FalkorDB driver
    "mindsos_core/persistence/metagraph_repository.py": 1,  # outside-service call: driver exceptions
}

#: Outside-service CONSUMPTION — every body that reaches an injected
#: external client. This is the count that sees the seam itself: the
#: import census above cannot, because the model client imports no
#: network library at all (its transport is a callable the deployment
#: supplies), which is exactly how a stub with live network IO dropped
#: into the package left this file 6/6 green before the axis existed.
#:
#: A second entry means a second capacity consults an outside model.
#: That is a design event — the declaration flag ``consults_llm`` was
#: chosen over a category rule so this set stays enumerable — and it
#: lands here with its row, not silently.
EXPECTED_EXTERNAL_CLIENT_CONSUMERS = {
    "mindsos_capacity/builtins/comprehension_v0.py": 1,  # outside-service call: the model reader
}

#: Executor definitions. Two exist; only one grounds.
EXPECTED_EXECUTOR_DEFS = {
    "mindsos_intelligence/pipeline_execution.py": 1,  # grounding-executor
    "mindsos_server/pipeline_runner.py": 1,           # notional-runner
}


def test_execute_pipeline_caller_census_is_exact():
    got = _census(r"(?<!def )execute_pipeline\(")
    assert got == EXPECTED_EXECUTOR_CALLERS, (
        "execute_pipeline caller census changed. A new run path exists (or one "
        "vanished): classify it above AND add its sweep row in the same ship "
        f"(RULES §12.1). Got {got!r}"
    )


def test_direct_dispatch_census_is_exact():
    got = _census(r"dispatcher\.dispatch\(")
    assert got == EXPECTED_DIRECT_DISPATCH, (
        "direct-dispatch census changed. If the new site is run-shaped it must "
        "go through execute_pipeline (the fold's bypass was gap 10); if it is "
        "L4-policy-meta, classify it above and add its sweep row in the same "
        f"ship (RULES §12.1). Got {got!r}"
    )


def test_persistence_entry_census_is_exact():
    got = _census(r"(?<!def )persist_capacity_mm\(")
    assert got == EXPECTED_PERSISTENCE_CALLERS, (
        "persist_capacity_mm caller census changed — a new persistence entry "
        f"point exists. Classify it and add its sweep row. Got {got!r}"
    )


def test_executor_definition_census_is_exact():
    got = _census(r"def (?:execute_pipeline|run_pipeline)\(")
    assert got == EXPECTED_EXECUTOR_DEFS, (
        "executor definition census changed — a third executor (or a rename) "
        f"is a new surface, not a refactor detail. Got {got!r}"
    )


#: Partial-record CR (ADR-0201 am-6): ``MemberAbortError`` is RETIRED as a
#: raiser — a failing member stops in place and its siblings run. The class
#: remains as API; this census pins the ABSENCE of raisers, so the day a
#: raise reappears the sentinel names it (coordination §63 Q4 — the tripwire
#: placed where truth lives, instead of a dead orchestrator catch).
def test_nothing_raises_member_abort_error():
    got = _census(r"raise MemberAbortError")
    assert got == {}, (
        "MemberAbortError is retired as a raiser (partial results, ADR-0201 "
        "am-6): a failing member stops IN PLACE. A new raise reintroduces "
        f"the all-or-nothing abort - classify or remove it. Got {got!r}"
    )


def test_outside_service_import_census_is_exact():
    got = _census(
        r"(?:^|\n)\s*(?:import|from)\s+"
        r"(?:falkordb|urllib|socket|http\.client|requests)\b"
    )
    assert got == EXPECTED_OUTSIDE_SERVICE_IMPORTS, (
        "a mindsos_* module reaches an outside service directly. That is a "
        "new surface, not an implementation detail: it is untestable in a "
        "gate with no network, and it is where credentials and a customer's "
        "document leave our control. Classify it here, or take it through a "
        f"deployment-supplied seam. Got {got!r}"
    )


def test_external_client_consumer_census_is_exact():
    got = _census(r"""context\.llm\b|getattr\(\s*context\s*,\s*["']llm["']""")
    assert got == EXPECTED_EXTERNAL_CLIENT_CONSUMERS, (
        "a body reaching an outside-service client is a run surface: it can "
        "fail in ways no other step can (an outage, a ceiling, an answer that "
        "will not decode), and each of those has a different meaning on a "
        f"Decision Record. Classify it here with its row. Got {got!r}"
    )


def test_census_regexes_are_load_bearing():
    """A census over a regex that matches nothing is the ADR-guard defect
    (green while silently checking zero rows). Each census must see at least
    its known population."""
    assert sum(EXPECTED_EXECUTOR_CALLERS.values()) >= 5
    assert sum(EXPECTED_DIRECT_DISPATCH.values()) >= 10
    assert _census(r"dispatcher\.dispatch\(")  # non-empty by construction
    assert sum(EXPECTED_OUTSIDE_SERVICE_IMPORTS.values()) >= 2
    assert sum(EXPECTED_EXTERNAL_CLIENT_CONSUMERS.values()) >= 1
