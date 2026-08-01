"""Phase 44 PR3 (S7) — Kahn topological-sort bootstrap scheduler.

Consumes the Phase-43 ``_APPLIES_AFTER_BY_ROLE`` declarations (L2-37
consumer split). The single v1 edge (``episodic_memories <- request-patterns``)
was cross-scope until ADR-0150 §am-8 made ``request-patterns`` dual-scope; it
is now **within-Local-scope**, so the Local sort orders ``request-patterns``
before ``episodic_memories`` (Global still reduces to alphabetical — it has
no within-scope edge). The scheduler enforces within-scope ordering and
rejects cycles.
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
        {"request-patterns", "episodic_memories"},
        {"episodic_memories": frozenset({"request-patterns"})},
    )
    assert order.index("request-patterns") < order.index("episodic_memories")


def test_independent_roles_alphabetical() -> None:
    assert kahn_sort({"c", "a", "b"}, {}) == ("a", "b", "c")


def test_cross_scope_dependency_ignored() -> None:
    order = kahn_sort(
        {"episodic_memories", "capacity-state"},
        {"episodic_memories": frozenset({"request-patterns"})},
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


def test_real_declarations_order_per_scope() -> None:
    # Global has no within-scope edge (episodic_memories is Local) → alphabetical.
    global_order = kahn_sort(_GLOBAL_NAMED_ROLES, _APPLIES_AFTER_BY_ROLE)
    assert global_order == tuple(sorted(_GLOBAL_NAMED_ROLES))
    # Local: ADR-0150 §am-8 made request-patterns dual-scope, so the
    # episodic_memories <- request-patterns edge is within-Local; request-patterns
    # is emitted before episodic_memories, otherwise alphabetical tie-break.
    local_order = kahn_sort(_LOCAL_NAMED_ROLES, _APPLIES_AFTER_BY_ROLE)
    assert set(local_order) == set(_LOCAL_NAMED_ROLES)
    assert local_order.index("request-patterns") < local_order.index("episodic_memories")
    assert local_order == (
        "capacity-state",
        "installed-capacities",
        # CORE-C2R1 (ADR-0150 §am-11) — installed-skills is dual-scope.
        "installed-skills",
        "learned-parameters",
        "learned-pipelines",
        "parameter-staging",
        "pending-promotions",
        "request-patterns",
        "episodic_memories",
    )
