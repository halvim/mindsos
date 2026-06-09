"""LifecyclePhase goal-verification — sufficient-predicate dispatch (D41).

L4 dispatches the L3 ``predicate.sufficient`` capacity; the per-pattern
predicate decides whether the task has produced enough to succeed. At
Phase 47 the body is the v0 stub (test-configurable). ADR-0174.
"""

from __future__ import annotations

from mindsos_capacity.builtins.orchestration_v0 import DS_SUFFICIENT, DS_SUFFICIENT_STATE
from mindsos_capacity.identifiers import CATEGORY_PREDICATE, capacity_iri

SUFFICIENT_IRI = capacity_iri(CATEGORY_PREDICATE, "sufficient")


def evaluate(dispatcher, state=None) -> bool:
    result = dispatcher.dispatch(SUFFICIENT_IRI, {DS_SUFFICIENT_STATE: state or {}})
    return bool(result.outputs[DS_SUFFICIENT])


__all__ = ["evaluate", "SUFFICIENT_IRI"]
