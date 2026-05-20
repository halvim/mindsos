"""Phase 14 — ``install_local_metagraph`` / ``extract_local_metagraph``.

Per ADR-0042 §Decision + Phase 14 PB-5/PB-9 locks. Covers:

* Install + extract round-trip; object identity preserved.
* ``AlreadyInstalledError`` on install-while-installed.
* ``NotInstalledError`` on extract-while-not-installed.
* Install of a bare Metagraph auto-ensures the 2 Local-named roles.
* Install of a Metagraph that already has the 2 roles is idempotent.
* Extract pops the user_id (subsequent extract raises).
"""

from __future__ import annotations

import pytest

from mindsos_core import Metagraph

from mindsos_knowledge import (
    AlreadyInstalledError,
    KnowledgeLayer,
    NotInstalledError,
    ROLE_CAPACITY_STATE,
    ROLE_MEMORIES,
    ensure_local_role_graph,
)


def test_install_then_extract_round_trip_preserves_identity() -> None:
    """ADR-0042 §Consequences — object-identity preserved."""
    kl = KnowledgeLayer.bootstrap()
    mg = Metagraph(name="prepared")
    kl.install_local_metagraph("alice", mg)
    extracted = kl.extract_local_metagraph("alice")
    assert extracted is mg


def test_install_twice_raises_already_installed() -> None:
    """ADR-0042 §Decision — refuses with AlreadyInstalledError."""
    kl = KnowledgeLayer.bootstrap()
    kl.install_local_metagraph("alice", Metagraph(name="first"))
    with pytest.raises(AlreadyInstalledError, match="already installed"):
        kl.install_local_metagraph("alice", Metagraph(name="second"))


def test_extract_uninstalled_raises_not_installed() -> None:
    """ADR-0042 §Decision — raises NotInstalledError on miss."""
    kl = KnowledgeLayer.bootstrap()
    with pytest.raises(NotInstalledError, match="No Local metagraph"):
        kl.extract_local_metagraph("alice")


def test_install_auto_ensures_missing_local_roles() -> None:
    """Phase 14 PB-9 — install auto-ensures memories + capacity-state."""
    kl = KnowledgeLayer.bootstrap()
    bare = Metagraph(name="bare")
    assert len(bare.graphs) == 0
    kl.install_local_metagraph("alice", bare)
    # Both Local-named role-graphs are now present.
    observed = {g.role for g in bare.graphs.values()}
    assert observed == {ROLE_MEMORIES, ROLE_CAPACITY_STATE}


def test_install_idempotent_on_already_ensured_local() -> None:
    """Pre-ensured Local install doesn't duplicate role-graphs."""
    kl = KnowledgeLayer.bootstrap()
    pre = Metagraph(name="pre")
    ensure_local_role_graph(pre, ROLE_MEMORIES)
    ensure_local_role_graph(pre, ROLE_CAPACITY_STATE)
    assert len(pre.graphs) == 2
    kl.install_local_metagraph("alice", pre)
    # Same 2 role-graphs; no duplicates.
    assert len(pre.graphs) == 2


def test_extract_pops_user_id() -> None:
    """After extract, the user_id is no longer installed."""
    kl = KnowledgeLayer.bootstrap()
    kl.install_local_metagraph("alice", Metagraph(name="t"))
    assert kl.has_local("alice")
    kl.extract_local_metagraph("alice")
    assert not kl.has_local("alice")


def test_extract_then_install_round_trip() -> None:
    """Reinstallation after extract works (no residue)."""
    kl = KnowledgeLayer.bootstrap()
    mg = Metagraph(name="t")
    kl.install_local_metagraph("alice", mg)
    kl.extract_local_metagraph("alice")
    # Reinstall: same user, different Metagraph object.
    mg2 = Metagraph(name="t2")
    kl.install_local_metagraph("alice", mg2)
    assert kl.local_metagraph("alice") is mg2


def test_multiple_users_install_extract_independent() -> None:
    """Per-user isolation."""
    kl = KnowledgeLayer.bootstrap()
    kl.install_local_metagraph("alice", Metagraph(name="a"))
    kl.install_local_metagraph("bob", Metagraph(name="b"))
    assert kl.installed_user_ids() == frozenset({"alice", "bob"})
    kl.extract_local_metagraph("alice")
    assert kl.installed_user_ids() == frozenset({"bob"})


def test_lazy_then_install_collision() -> None:
    """Lazy-access creates a Local; install for same user_id raises."""
    kl = KnowledgeLayer.bootstrap()
    kl.local_metagraph("alice")  # lazy create
    with pytest.raises(AlreadyInstalledError):
        kl.install_local_metagraph("alice", Metagraph(name="other"))
