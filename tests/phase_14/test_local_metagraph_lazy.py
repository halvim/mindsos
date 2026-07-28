"""Phase 14 — lazy ``local_metagraph(user_id)`` auto-ensures the Local roles.

Per Phase 14 PB-9 lock: lazy access creates a fresh Local Metagraph
with every ``_LOCAL_NAMED_ROLES`` ensured before return (Phase 39 rename
per ADR-0044 §am-3; Phase 43 §am-5 adds 3; ADR-0150 §am-8 adds the
dual-scope ``request-patterns``).
Symmetric with Global bootstrap auto-ensuring the Global named roles.
"""

from __future__ import annotations

from mindsos_knowledge import (
    KnowledgeLayer,
    ROLE_CAPACITY_STATE,
    ROLE_EPISODIC_MEMORIES,
)


def test_lazy_local_creates_on_first_access() -> None:
    """First call mints a Local with the 6 Local-named role-graphs (Phase 43
    §am-5: 2 base + 3 dual-scope; ADR-0150 §am-8: + dual-scope request-patterns)."""
    from mindsos_knowledge import (
        ROLE_INSTALLED_CAPACITIES,
        ROLE_LEARNED_PARAMETERS,
        ROLE_LEARNED_PIPELINES,
        ROLE_PARAMETER_STAGING,
        ROLE_PENDING_PROMOTIONS,
        ROLE_REQUEST_PATTERNS,
    )
    kl = KnowledgeLayer.bootstrap()
    local = kl.local_metagraph("alice")
    observed_roles = {g.role for g in local.graphs.values()}
    assert observed_roles == {
        ROLE_EPISODIC_MEMORIES,
        ROLE_CAPACITY_STATE,
        ROLE_PARAMETER_STAGING,
        ROLE_PENDING_PROMOTIONS,
        ROLE_LEARNED_PARAMETERS,
        ROLE_REQUEST_PATTERNS,
        ROLE_LEARNED_PIPELINES,
        ROLE_INSTALLED_CAPACITIES,
    }


def test_lazy_local_canonical_name() -> None:
    """v3 design doc §2 — Local name is ``local_knowledge:<user_id>``."""
    kl = KnowledgeLayer.bootstrap()
    local = kl.local_metagraph("alice")
    assert local.name == "local_knowledge:alice"


def test_lazy_local_second_access_returns_same_reference() -> None:
    """Idempotent lazy-access (PB-9 symmetric with bootstrap)."""
    kl = KnowledgeLayer.bootstrap()
    a = kl.local_metagraph("alice")
    b = kl.local_metagraph("alice")
    assert a is b


def test_lazy_local_per_user_isolation() -> None:
    """Each user_id gets a distinct Local."""
    kl = KnowledgeLayer.bootstrap()
    alice = kl.local_metagraph("alice")
    bob = kl.local_metagraph("bob")
    assert alice is not bob
    assert alice.metagraph_id != bob.metagraph_id


def test_has_local_after_lazy_access() -> None:
    """``has_local`` flips True after lazy access."""
    kl = KnowledgeLayer.bootstrap()
    assert not kl.has_local("alice")
    kl.local_metagraph("alice")
    assert kl.has_local("alice")


def test_installed_user_ids_after_lazy_access() -> None:
    """``installed_user_ids`` includes lazy-created users."""
    kl = KnowledgeLayer.bootstrap()
    kl.local_metagraph("alice")
    kl.local_metagraph("bob")
    assert kl.installed_user_ids() == frozenset({"alice", "bob"})


def test_lazy_local_uses_kl_id_strategy() -> None:
    """The kl's ``_id_strategy`` propagates to the lazily-minted Local."""
    from mindsos_core.models.identity import IRIPassthroughStrategy

    strategy = IRIPassthroughStrategy()
    kl = KnowledgeLayer.bootstrap(id_strategy=strategy)
    local = kl.local_metagraph("alice")
    assert local.id_strategy is strategy
