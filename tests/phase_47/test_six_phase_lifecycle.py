"""Phase 47 — six-phase lifecycle outcomes (ADR-0171 / D12).

Drives the four outcome branches: succeeded (default), dont_know (sufficient
-> False -> Phase 6 blame), aborted (should_replan -> abort), and bounded
replan (should_replan -> replan exhausts budget then completes).
"""

from __future__ import annotations

from mindsos_capacity.builtins.orchestration_v0 import (
    reset_v0_verdicts,
    set_should_replan_decision,
    set_sufficient_result,
)

from mindsos_intelligence.chain_artifacts import TYPE_REPLAN_RECORD, iter_chain_artifacts

from ._fixtures import make_orchestrator


def test_succeeded_default_path():
    orch, _mm, _layer = make_orchestrator()
    assert orch.run_lifecycle({"x": 1}).status == "succeeded"


def test_dont_know_when_insufficient():
    orch, _mm, _layer = make_orchestrator()
    try:
        set_sufficient_result(False)
        outcome = orch.run_lifecycle({"x": 1})
    finally:
        reset_v0_verdicts()
    assert outcome.status == "dont_know"
    assert outcome.dont_know_reason == "INSUFFICIENT"
    assert outcome.blame is not None
    assert outcome.blame.chain_level == "pipeline"


def test_conceded_on_abort_verdict():
    # Dream PRE-0 Slice 1b (D4): a reached abort is a DECISION → "conceded"
    # (was the misleading "aborted"/"failed"); "failed" is reserved for a crash.
    orch, mm, _layer = make_orchestrator()
    try:
        set_should_replan_decision("abort")
        outcome = orch.run_lifecycle({"x": 1})
    finally:
        reset_v0_verdicts()
    assert outcome.status == "conceded"
    assert len(list(iter_chain_artifacts(mm, TYPE_REPLAN_RECORD))) == 1


def test_replan_exhausts_budget_then_completes():
    orch, mm, _layer = make_orchestrator(budget=3)
    try:
        set_should_replan_decision("replan")
        outcome = orch.run_lifecycle({"x": 1})
    finally:
        reset_v0_verdicts()
    assert outcome.status == "succeeded"
    assert outcome.replans_used == 3
    assert len(list(iter_chain_artifacts(mm, TYPE_REPLAN_RECORD))) == 3
