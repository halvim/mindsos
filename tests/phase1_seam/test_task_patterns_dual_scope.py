"""S0.5 — ``request-patterns`` is dual-scope (Global + Local), ADR-0150 §am-8.

Precursor to the Phase-1 interpretation seam (ADR-0195): a consumer's
``map`` body returns a ``request-pattern:*`` IRI authored in its Local scope.
This requires a Local ``request-patterns`` role-graph, which §am-8 adds by
making the role dual-scope (joining ``pending-promotions`` /
``learned-parameters``).
"""

from __future__ import annotations

from mindsos_core import Metagraph

from mindsos_knowledge import (
    KnowledgeLayer,
    ROLE_REQUEST_PATTERNS,
    ensure_local_role_graph,
)
from mindsos_knowledge.bootstrap import (
    _GLOBAL_NAMED_ROLES,
    _LOCAL_NAMED_ROLES,
    _APPLIES_AFTER_BY_ROLE,
)


def test_task_patterns_is_dual_scope() -> None:
    """§am-8 — request-patterns appears in BOTH the Global and Local named sets."""
    assert ROLE_REQUEST_PATTERNS in _GLOBAL_NAMED_ROLES
    assert ROLE_REQUEST_PATTERNS in _LOCAL_NAMED_ROLES


def test_ensure_local_creates_task_patterns() -> None:
    """ensure_local_role_graph no longer rejects request-patterns."""
    mg = Metagraph(name="local_t")
    g = ensure_local_role_graph(mg, ROLE_REQUEST_PATTERNS)
    assert g.role == ROLE_REQUEST_PATTERNS
    assert g.schema is not None


def test_lazy_local_contains_task_patterns() -> None:
    """A lazily-minted Local auto-ensures a request-patterns graph."""
    kl = KnowledgeLayer.bootstrap()
    local = kl.local_metagraph("alice")
    roles = {g.role for g in local.graphs.values()}
    assert ROLE_REQUEST_PATTERNS in roles


def test_global_still_has_task_patterns() -> None:
    """Widening scope must not drop the Global form."""
    kl = KnowledgeLayer.bootstrap()
    roles = {g.role for g in kl.global_metagraph().graphs.values()}
    assert ROLE_REQUEST_PATTERNS in roles


def test_applies_after_keys_cover_task_patterns() -> None:
    """The applies_after table still keys every named role (union invariant)."""
    assert set(_APPLIES_AFTER_BY_ROLE.keys()) == (
        _GLOBAL_NAMED_ROLES | _LOCAL_NAMED_ROLES
    )
