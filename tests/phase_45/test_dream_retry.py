"""Phase 45 — ``capacity:dream:retry`` (re_execute + replan-injection).

Replan-injection mechanism (ADR-0162 §5): on a **failed** episode the
emitted ``DreamDirective`` carries a populated ``ReplanInjectionDirective``;
on a non-failed episode the capacity returns ``None`` (retry applies only
to failures — OPTIONAL_RETURN dont-know).
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer, DreamCapacity
from mindsos_capacity.builtins.dream import (
    DS_DREAM_DIRECTIVE,
    DS_DREAM_TASK_REF,
    REPLAN_LEVEL_TASKRUN,
    DreamDirective,
    ReplanInjectionDirective,
    build_dream_retry,
    install_dream_capacities,
)
from mindsos_capacity.family_rules import FamilyDontKnowShape, family_rule_for

_FAILED = {"source_episode_iri": "ep:7", "task_run_iri": "tr:7", "failed": True}
_OK = {"source_episode_iri": "ep:7", "task_run_iri": "tr:7", "failed": False}


def test_declaration_shape():
    cap = build_dream_retry()
    assert isinstance(cap, DreamCapacity)
    assert cap.iri == "capacity:dream:retry"
    assert cap.execution_policy == "re_execute_capacities"


def test_failed_episode_emits_populated_replan_injection():
    cap = build_dream_retry()
    directive = cap.implementation(**{DS_DREAM_TASK_REF: _FAILED})
    assert isinstance(directive, DreamDirective)
    assert directive.execution_policy == "re_execute_capacities"
    inj = directive.replan_injection
    assert isinstance(inj, ReplanInjectionDirective)
    assert inj.replan_level == REPLAN_LEVEL_TASKRUN
    assert inj.source_episode_iri == "ep:7"
    assert inj.reason


def test_non_failed_episode_is_dont_know():
    cap = build_dream_retry()
    assert cap.implementation(**{DS_DREAM_TASK_REF: _OK}) is None


def test_missing_episode_is_dont_know():
    cap = build_dream_retry()
    assert cap.implementation(**{DS_DREAM_TASK_REF: {}}) is None


def test_family_rule_is_optional_return():
    assert (
        family_rule_for("capacity:dream:retry")
        is FamilyDontKnowShape.OPTIONAL_RETURN
    )


def test_registered_and_invokable_replan_executes():
    """Pass criterion: 'Replan-injection mechanism executes per spec' —
    the registered capacity, given a failed episode, emits a directive
    whose replan_injection is populated."""
    layer = CapacityLayer()
    install_dream_capacities(layer)
    result = layer.invoke(
        "capacity:dream:retry",
        {DS_DREAM_TASK_REF: _FAILED},
        task_id="dream-test",
    )
    assert result.success is True
    directive = result.outputs[DS_DREAM_DIRECTIVE]
    assert isinstance(directive, DreamDirective)
    assert isinstance(directive.replan_injection, ReplanInjectionDirective)


def test_registered_non_failed_surfaces_none():
    layer = CapacityLayer()
    install_dream_capacities(layer)
    result = layer.invoke(
        "capacity:dream:retry",
        {DS_DREAM_TASK_REF: _OK},
        task_id="dream-test",
    )
    assert result.success is True
    assert result.outputs[DS_DREAM_DIRECTIVE] is None
