"""Phase 43 PR2 — bootstrap.py ``applies_after`` field declarations.

Per Phase 43 R0b §1.2 + NPB6-6 + L2-37 split (NPB11-1): field-only at
Phase 43; Kahn topological-sort scheduler defers to Phase 44.

This test asserts the declaration shape, NOT scheduler behavior
(NPB11-5: Phase 43 explicitly does not enforce ordering).
"""

from __future__ import annotations

import inspect

from mindsos_knowledge.bootstrap import (
    _APPLIES_AFTER_BY_ROLE,
    _GLOBAL_NAMED_ROLES,
    _LOCAL_NAMED_ROLES,
    ensure_global_role_graph,
    ensure_local_role_graph,
)
from mindsos_knowledge.identifiers import (
    ROLE_EPISODIC_MEMORIES,
    ROLE_REQUEST_PATTERNS,
)


def test_applies_after_kwarg_on_ensure_global() -> None:
    sig = inspect.signature(ensure_global_role_graph)
    assert "applies_after" in sig.parameters


def test_applies_after_kwarg_on_ensure_local() -> None:
    sig = inspect.signature(ensure_local_role_graph)
    assert "applies_after" in sig.parameters


def test_applies_after_default_is_empty_frozenset() -> None:
    for func in (ensure_global_role_graph, ensure_local_role_graph):
        param = inspect.signature(func).parameters["applies_after"]
        assert param.default == frozenset(), (
            f"{func.__name__}.applies_after default {param.default!r} "
            f"!= frozenset()"
        )


def test_applies_after_table_covers_all_12_named_roles() -> None:
    """13 declarations table covers 12 named role-graphs (alignment is
    prefix-keyed; not enumerated here)."""
    assert set(_APPLIES_AFTER_BY_ROLE.keys()) == (
        _GLOBAL_NAMED_ROLES | _LOCAL_NAMED_ROLES
    )


def test_episodic_memories_soft_edge_on_task_patterns() -> None:
    """Per NPB6-6: episodic_memories depends on request-patterns (Episodes
    carry ``request_pattern_iri`` so request-patterns must exist first)."""
    assert _APPLIES_AFTER_BY_ROLE[ROLE_EPISODIC_MEMORIES] == frozenset(
        {ROLE_REQUEST_PATTERNS}
    )


def test_all_other_roles_have_empty_applies_after_at_phase_43() -> None:
    """Phase 43 R0b §1.2: only the episodic_memories ← request-patterns
    soft edge is declared. Other roles are independent at Phase 43 scope.
    """
    for role, deps in _APPLIES_AFTER_BY_ROLE.items():
        if role == ROLE_EPISODIC_MEMORIES:
            continue
        assert deps == frozenset(), (
            f"{role!r} has non-empty applies_after {deps!r} but only "
            f"episodic_memories should at Phase 43 scope"
        )
