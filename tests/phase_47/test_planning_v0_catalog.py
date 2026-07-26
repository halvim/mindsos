"""Phase 47 — placeholder v0 catalogs ship, register, and are invokable.

Covers planning_v0 + phase1_v0 + orchestration_v0 (ADR-0172). Asserts:
registration, the ``placeholder=True`` marker, invoke output shapes, and
the test-configurable should_replan / sufficient verdicts (PB-C).
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.planning_v0 import (
    DS_CHILD_OUTPUTS,
    DS_MAPPING_RESULT,
    DS_MILESTONE,
    DS_PLAN,
    DS_IS_LEAF,
    DS_MILESTONE_LIST,
    DS_AGG_OUTPUT,
    install_planning_v0,
)
from mindsos_capacity.builtins.phase1_v0 import (
    DS_RAW_INPUT,
    DS_STRUCTURED_INPUT,
    DS_HINT_SET,
    DS_GOAL,
    DS_MAPPING,
    TRIVIAL_REQUEST_PATTERN_IRI,
    install_phase1_v0,
)
from mindsos_capacity.builtins.orchestration_v0 import (
    DS_SIGNAL,
    DS_TIER,
    DS_SCORE_INPUT,
    DS_SCORE,
    DS_REPLAN_STATE,
    DS_REPLAN_VERDICT,
    DS_SUFFICIENT_STATE,
    DS_SUFFICIENT,
    DS_BLAME_INPUT,
    DS_BLAME,
    install_orchestration_v0,
    set_should_replan_decision,
    set_sufficient_result,
    reset_v0_verdicts,
)
from mindsos_capacity.identifiers import (
    CATEGORY_DECISION,
    CATEGORY_PHASE6,
    CATEGORY_PLANNING,
    CATEGORY_PREDICATE,
    CATEGORY_PROCESS,
    CATEGORY_SCORING,
    capacity_iri,
)
from mindsos_capacity.tiers import TierEnum, default_score


def _layer():
    layer = CapacityLayer()
    install_planning_v0(layer)
    install_phase1_v0(layer)
    install_orchestration_v0(layer)
    return layer


def test_planning_v0_invokable_and_marked():
    layer = _layer()
    iri = capacity_iri(CATEGORY_PLANNING, "derive_initial_plan")
    decl = layer.get_declaration(iri)
    assert decl.placeholder is True

    r = layer.invoke(iri, {DS_MAPPING_RESULT: {"request_pattern_iri": "x"}})
    assert r.success
    plan = r.outputs[DS_PLAN]
    assert plan["single_milestone"] is True
    assert plan["root_milestone"]["is_leaf"] is True

    r2 = layer.invoke(
        capacity_iri(CATEGORY_PLANNING, "decompose"), {DS_MILESTONE: {}}
    )
    assert r2.outputs[DS_MILESTONE_LIST] == []

    r3 = layer.invoke(
        capacity_iri(CATEGORY_PLANNING, "is_leaf"), {DS_MILESTONE: {}}
    )
    assert r3.outputs[DS_IS_LEAF] is True

    r4 = layer.invoke(
        capacity_iri(CATEGORY_PLANNING, "aggregate_outputs"),
        {DS_CHILD_OUTPUTS: ["a", "b", "c"]},
    )
    assert r4.outputs[DS_AGG_OUTPUT] == "c"


def test_phase1_v0_five_step_chain():
    layer = _layer()
    raw = {"text": "hello"}

    s = layer.invoke(
        capacity_iri(CATEGORY_PROCESS, "identity"), {DS_RAW_INPUT: raw}
    )
    structured = s.outputs[DS_STRUCTURED_INPUT]
    assert structured == raw

    h = layer.invoke(
        capacity_iri("hint", "global"), {DS_STRUCTURED_INPUT: structured}
    )
    assert h.outputs[DS_HINT_SET] == {}

    g = layer.invoke(
        capacity_iri(CATEGORY_DECISION, "derive_goal"),
        {DS_STRUCTURED_INPUT: structured, DS_HINT_SET: {}},
    )
    assert "goal" in g.outputs[DS_GOAL]

    m = layer.invoke(
        capacity_iri(CATEGORY_DECISION, "map_to_task_pattern"),
        {DS_STRUCTURED_INPUT: structured, DS_HINT_SET: {}, DS_GOAL: {}},
    )
    mapping = m.outputs[DS_MAPPING]
    assert mapping["request_pattern_iri"] == TRIVIAL_REQUEST_PATTERN_IRI
    assert mapping["mapping_confidence"] == 1.0


def test_orchestration_v0_defaults():
    layer = _layer()
    reset_v0_verdicts()

    t = layer.invoke(
        capacity_iri(CATEGORY_DECISION, "signal_to_tier"),
        {DS_SIGNAL: {"tier": TierEnum.CRITICAL}},
    )
    assert t.outputs[DS_TIER] == TierEnum.CRITICAL

    sc = layer.invoke(
        capacity_iri(CATEGORY_SCORING, "attention_score"),
        {DS_SCORE_INPUT: TierEnum.BACKGROUND},
    )
    assert sc.outputs[DS_SCORE] == default_score(TierEnum.BACKGROUND)

    rp = layer.invoke(
        capacity_iri(CATEGORY_DECISION, "should_replan"), {DS_REPLAN_STATE: {}}
    )
    assert rp.outputs[DS_REPLAN_VERDICT]["decision"] == "continue"

    su = layer.invoke(
        capacity_iri(CATEGORY_PREDICATE, "sufficient"),
        {DS_SUFFICIENT_STATE: {}},
    )
    assert su.outputs[DS_SUFFICIENT] is True

    bl = layer.invoke(
        capacity_iri(CATEGORY_PHASE6, "attribute_blame"),
        {DS_BLAME_INPUT: {}},
    )
    assert bl.outputs[DS_BLAME]["chain_level"] == "pipeline"


def test_orchestration_v0_configurable_verdicts():
    layer = _layer()
    try:
        set_should_replan_decision("replan")
        set_sufficient_result(False)

        rp = layer.invoke(
            capacity_iri(CATEGORY_DECISION, "should_replan"),
            {DS_REPLAN_STATE: {}},
        )
        assert rp.outputs[DS_REPLAN_VERDICT]["decision"] == "replan"

        su = layer.invoke(
            capacity_iri(CATEGORY_PREDICATE, "sufficient"),
            {DS_SUFFICIENT_STATE: {}},
        )
        assert su.outputs[DS_SUFFICIENT] is False
    finally:
        reset_v0_verdicts()


def test_v0_installs_idempotent():
    layer = _layer()
    install_planning_v0(layer)
    install_phase1_v0(layer)
    install_orchestration_v0(layer)
