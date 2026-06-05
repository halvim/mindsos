"""Phase 44 PR3 (S7) — Kahn topological-sort bootstrap scheduler.

Consumes the Phase-43 ``_APPLIES_AFTER_BY_ROLE`` declarations (L2-37
consumer split). The single v1 edge (``episodic_memories <- task-patterns``)
is cross-scope, so single-scope sorts reduce to alphabetical; the
scheduler enforces within-scope ordering for future edges and rejects
cycles.
"""

from __future__ import annotations

import pytest

from mindsos_knowledge.bootstrap import (
    _APPLIES_AFTER_BY_ROLE,
    _GLOBAL_NAMED_ROLES,
    _LOCAL_NAMED_ROLES,
    kahn_sort,
)
from mindsos_knowledge.exceptions import BootstrapCycleError


def test_respects_within_scope_edge() -> None:
    order = kahn_sort(
        {"task-patterns", "episodic_memories"},
        {"episodic_memories": frozenset({"task-patterns"})},
    )
    assert order.index("task-patterns") < order.index("episodic_memories")


def test_independent_roles_alphabetical() -> None:
    assert kahn_sort({"c", "a", "b"}, {}) == ("a", "b", "c")


def test_cross_scope_dependency_ignored() -> None:
    order = kahn_sort(
        {"episodic_memories", "capacity-state"},
        {"episodic_memories": frozenset({"task-patterns"})},
    )
    assert order == ("capacity-state", "episodic_memories")


def test_missing_declaration_is_no_constraint() -> None:
    assert kahn_sort({"x", "y"}, {}) == ("x", "y")


def test_cycle_raises() -> None:
    with pytest.raises(BootstrapCycleError):
        kahn_sort(
            {"a", "b"},
            {"a": frozenset({"b"}), "b": frozenset({"a"})},
        )


def test_real_declarations_reduce_to_alphabetical_per_scope() -> None:
    global_order = kahn_sort(_GLOBAL_NAMED_ROLES, _APPLIES_AFTER_BY_ROLE)
    local_order = kahn_sort(_LOCAL_NAMED_ROLES, _APPLIES_AFTER_BY_ROLE)
    assert global_order == tuple(sorted(_GLOBAL_NAMED_ROLES))
    assert local_order == tuple(sorted(_LOCAL_NAMED_ROLES))
