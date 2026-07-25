"""Phase 45 — ``capacity:dream:exploration`` (``re_execute_capacities``).

Directive-emitter contract (ADR-0162): the body returns a
``DreamDirective`` declaring the ``re_execute_capacities`` policy (drift
detection vs current L2/L3); dont-know (OPTIONAL_RETURN) on a missing
source episode.
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer, DreamCapacity
from mindsos_capacity.builtins.dream import (
    DS_DREAM_DIRECTIVE,
    DS_DREAM_TASK_REF,
    ENTRY_POINT_LATEST_ACTIVE_TASKRUN,
    DreamDirective,
    DreamExecutionPolicy,
    build_dream_exploration,
    install_dream_capacities,
)
from mindsos_capacity.family_rules import FamilyDontKnowShape, family_rule_for

_EP = {"source_episode_iri": "ep:9", "request_run_iri": "tr:9", "failed": False}


def test_declaration_shape():
    cap = build_dream_exploration()
    assert isinstance(cap, DreamCapacity)
    assert cap.iri == "capacity:dream:exploration"
    assert cap.execution_policy == DreamExecutionPolicy.RE_EXECUTE_CAPACITIES.value
    assert cap.entry_point == ENTRY_POINT_LATEST_ACTIVE_TASKRUN
    assert cap.concurrent is True


def test_body_emits_re_execute_directive():
    cap = build_dream_exploration()
    directive = cap.implementation(**{DS_DREAM_TASK_REF: _EP})
    assert isinstance(directive, DreamDirective)
    assert directive.execution_policy == "re_execute_capacities"
    assert directive.source_episode_iri == "ep:9"
    assert directive.replan_injection is None  # exploration never injects


def test_body_dont_know_on_missing_episode():
    cap = build_dream_exploration()
    assert cap.implementation(**{DS_DREAM_TASK_REF: {}}) is None


def test_family_rule_is_optional_return():
    assert (
        family_rule_for("capacity:dream:exploration")
        is FamilyDontKnowShape.OPTIONAL_RETURN
    )


def test_registered_and_invokable():
    layer = CapacityLayer()
    install_dream_capacities(layer)
    result = layer.invoke(
        "capacity:dream:exploration",
        {DS_DREAM_TASK_REF: _EP},
        request_id="dream-test",
    )
    assert result.success is True
    directive = result.outputs[DS_DREAM_DIRECTIVE]
    assert isinstance(directive, DreamDirective)
    assert directive.execution_policy == "re_execute_capacities"
