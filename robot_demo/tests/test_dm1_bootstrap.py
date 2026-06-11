"""DM-1 — per-device bootstrap + smoke scenario (mirrors tests/phase_49).

Two layers:
  * The **core** tests build the 4 device-instance stacks with a duck
    session (no ``mindsos_server`` → runs on any host, incl. the 3.10
    Cowork sandbox) and assert the DM-1 gate: 4 independent KLs, each
    consolidates one Episode through its own IL worker pool.
  * The **server** test exercises the real ``insert_user``/``login``
    bootstrap; it imports ``mindsos_server`` lazily and skips where the
    host can't run it (Python < 3.11 / argon2 missing).

DM-1 gate (plan §8): ``docker compose up`` → 4 brains start, 4 trivial
Episodes consolidate, idempotent re-boot.
"""

from __future__ import annotations

import pytest

from mindsos_intelligence.consolidation import consolidation_enabled
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView

from robot_demo.backend.brain import build_brain_stack
from robot_demo.backend.profiles import DEVICE_ORDER, DEVICE_PROFILES


class _DuckSession:
    """SessionProtocol-conforming session (no SQLite/argon2). The trivial
    consolidate writes the user's OWN Local — the ADR-0180 gate only fires
    on Global writes, so ``has() -> True`` is sound here."""

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.session_id = f"sess-{user_id}"
        self.actor_role = "user"
        self.capabilities = frozenset()

    def has(self, capability: str) -> bool:  # noqa: D401
        return True


def _episodes(brain):
    g = MetagraphView(brain.kl.local_metagraph(brain.device_id)).graphs_by_role(
        ROLE_EPISODIC_MEMORIES
    )[0]
    return [n for n in g.nodes.values() if getattr(n, "type_name", None) == "Episode"]


@pytest.fixture
def brains():
    built = {
        did: build_brain_stack(DEVICE_PROFILES[did], _DuckSession(did))
        for did in DEVICE_ORDER
    }
    yield built
    for b in built.values():
        b.il.stop()


def test_four_independent_device_instances(brains):
    assert set(brains) == set(DEVICE_ORDER)
    # Each device has its OWN KnowledgeLayer (distinct Global object + name).
    kls = [b.kl for b in brains.values()]
    assert len({id(kl) for kl in kls}) == 4
    names = {b.kl.global_metagraph().name for b in brains.values()}
    assert names == {p.kl_name for p in DEVICE_PROFILES.values()}


def test_consolidation_is_wired_per_brain(brains):
    # PB-Q: guard against a silent graceful-skip.
    for did, b in brains.items():
        assert consolidation_enabled(b.dispatcher) is True, did


def test_smoke_four_episodes_consolidate(brains):
    total = 0
    for did in DEVICE_ORDER:
        b = brains[did]
        out = b.il.enqueue(
            lambda b=b: b.orch.run_lifecycle(
                {"text": "dm1-smoke"}, task_id=f"smoke-{b.device_id}"
            )
        ).result(timeout=30)
        assert out.status == "succeeded", (did, out.status)
        eps = _episodes(b)
        assert len(eps) == 1, (did, len(eps))
        total += len(eps)
    assert total == 4


def test_local_isolation_no_cross_brain_episodes(brains):
    # Run only mgr; the other brains' Locals must stay empty (per-device L2).
    mgr = brains["mgr"]
    mgr.il.enqueue(
        lambda: mgr.orch.run_lifecycle({"text": "only-mgr"}, task_id="iso-mgr")
    ).result(timeout=30)
    assert len(_episodes(mgr)) == 1
    for did in ("arm1", "arm2", "conv"):
        assert len(_episodes(brains[did])) == 0, did


@pytest.mark.integration
def test_real_server_bootstrap_smoke(tmp_path):
    """Real mindsos_server path (insert_user/login + schema init). Skips
    where the host can't run mindsos_server (Python < 3.11 / argon2)."""
    pytest.importorskip("argon2")
    try:
        import mindsos_server  # noqa: F401
    except Exception as exc:  # pragma: no cover — host-dependent
        pytest.skip(f"mindsos_server unavailable: {exc}")

    from robot_demo.backend.bootstrap import bootstrap

    result = bootstrap(db_path=str(tmp_path / "server.db"))
    assert result.ok
    assert result.total_episodes == 4
    # Idempotent re-boot (P6): second bootstrap on the same server.db.
    result2 = bootstrap(db_path=str(tmp_path / "server.db"))
    assert result2.ok
    for b in list(result.brains.values()) + list(result2.brains.values()):
        b.il.stop()


if __name__ == "__main__":  # quick sandbox runner (no pytest needed)
    _b = {d: build_brain_stack(DEVICE_PROFILES[d], _DuckSession(d)) for d in DEVICE_ORDER}
    try:
        test_four_independent_device_instances(_b)
        test_consolidation_is_wired_per_brain(_b)
        test_smoke_four_episodes_consolidate(_b)
        print("DM-1 core scenario: PASS")
    finally:
        for _x in _b.values():
            _x.il.stop()
