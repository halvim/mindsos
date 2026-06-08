"""Phase 45 — ``capacity:dream:maintenance`` (``replay_recorded`` policy).

Directive-emitter contract (ADR-0162): the body returns a
``DreamDirective`` declaring the ``replay_recorded`` policy under pinned
state; dont-know (OPTIONAL_RETURN) on a missing source episode.
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer, DreamCapacity
from mindsos_capacity.builtins.dream import (
    DS_DREAM_DIRECTIVE,
    DS_DREAM_TASK_REF,
    ENTRY_POINT_LATEST_ACTIVE_TASKRUN,
    DreamDirective,
    DreamExecutionPolicy,
    build_dream_maintenance,
    install_dream_capacities,
)
from mindsos_capacity.family_rules import FamilyDontKnowShape, family_rule_for

_EP = {"source_episode_iri": "ep:1", "task_run_iri": "tr:1", "failed": False}


def test_declaration_shape():
    cap = build_dream_maintenance()
    assert isinstance(cap, DreamCapacity)
    assert cap.iri == "capacity:dream:maintenance"
    assert cap.category == "dream"
    assert cap.execution_policy == DreamExecutionPolicy.REPLAY_RECORDED.value
    assert cap.entry_point == ENTRY_POINT_LATEST_ACTIVE_TASKRUN
    assert cap.concurrent is True  # L3-51 default
    assert cap.inputs == (DS_DREAM_TASK_REF,)
    assert cap.outputs == (DS_DREAM_DIRECTIVE,)


def test_to_properties_carries_policy_and_entry_point():
    props = build_dream_maintenance().to_properties()
    assert props["execution_policy"] == "replay_recorded"
    assert props["entry_point"] == ENTRY_POINT_LATEST_ACTIVE_TASKRUN


def test_body_emits_replay_recorded_directive():
    cap = build_dream_maintenance()
    directive = cap.implementation(**{DS_DREAM_TASK_REF: _EP})
    assert isinstance(directive, DreamDirective)
    assert directive.execution_policy == "replay_recorded"
    assert directive.source_episode_iri == "ep:1"
    assert directive.task_run_iri == "tr:1"
    assert directive.replan_injection is None  # maintenance never injects


def test_body_dont_know_on_missing_episode():
    cap = build_dream_maintenance()
    assert cap.implementation(**{DS_DREAM_TASK_REF: {}}) is None
    assert cap.implementation(**{DS_DREAM_TASK_REF: {"failed": False}}) is None


def test_family_rule_is_optional_return():
    assert (
        family_rule_for("capacity:dream:maintenance")
        is FamilyDontKnowShape.OPTIONAL_RETURN
    )


def test_registered_and_invokable():
    layer = CapacityLayer()
    install_dream_capacities(layer)
    decl = layer.get_declaration("capacity:dream:maintenance")
    assert decl.execution_policy == "replay_recorded"

    result = layer.invoke(
        "capacity:dream:maintenance",
        {DS_DREAM_TASK_REF: _EP},
        task_id="dream-test",
    )
    assert result.success is True
    directive = result.outputs[DS_DREAM_DIRECTIVE]
    assert isinstance(directive, DreamDirective)
    assert directive.execution_policy == "replay_recorded"


def test_invoke_dont_know_surfaces_none_not_failure():
    layer = CapacityLayer()
    install_dream_capacities(layer)
    result = layer.invoke(
        "capacity:dream:maintenance",
        {DS_DREAM_TASK_REF: {}},
        task_id="dream-test",
    )
    assert result.success is True
    assert result.outputs[DS_DREAM_DIRECTIVE] is None
