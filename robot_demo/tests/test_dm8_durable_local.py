"""DM-8 — durable per-device Local: a taught skill survives a reboot.

Consumer-stack gate over the pinned F9 core (``boot_local`` /
``FalkorDBLocalPersister`` / ``reactivate_from_descriptors``). A live
FalkorDB is required, so these are ``@integration`` and skip where no
client/server is present. Core proves the mechanism in ``tests/f9``; this
proves the demo wiring end-to-end: teach -> save -> fresh stack ->
boot_local -> invoke, and that ``reset_run_state`` keeps the skill.

Isolated to a dedicated Falkor graph (monkeypatched ``_DEMO_GRAPH``) so the
fixed ``arm1`` Local key cannot collide with a real bootstrap's data; the
fixture deletes the Local on entry and exit.
"""

from __future__ import annotations

import pytest

from mindsos_capacity.identifiers import capacity_iri
from robot_demo.backend.capacities import (
    CAT_MECHANISM,
    DS_MOTION_DONE,
    DS_POSE_TARGET,
)
from robot_demo.backend.installers import install_core_datastates
from robot_demo.backend.profiles import DEVICE_PROFILES
from robot_demo.backend.transfer import has_taught, teach_local
from robot_demo.backend.wiring import box_workaround_artifact

_DID = "arm1"
_CAP = capacity_iri(CAT_MECHANISM, "load_into_box")


class _Duck:
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self.session_id = f"s-{user_id}"
        self.actor_role = "user"
        self.capabilities = frozenset()

    def has(self, capability: str) -> bool:
        return True


def _stack(client):
    """A fresh per-device stack over ``client`` (a new 'process')."""
    from robot_demo.backend.brain import build_brain_stack
    from robot_demo.backend.persistence import load_or_mint_global

    profile = DEVICE_PROFILES[_DID]
    kl = load_or_mint_global(client, profile).kl
    brain = build_brain_stack(profile, _Duck(_DID), kl=kl)
    install_core_datastates(brain.cl)
    return brain


@pytest.fixture
def falkor(monkeypatch):
    pytest.importorskip("falkordb")
    try:
        import mindsos_server  # noqa: F401
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"mindsos_server unavailable: {exc}")

    from robot_demo.backend import persistence

    monkeypatch.setattr(persistence, "_DEMO_GRAPH", "robot_demo_dm8_test")
    try:
        client = persistence.open_client()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"FalkorDB unavailable: {exc}")

    persister = persistence.build_local_persister(client)
    persister.delete(_DID)
    try:
        yield client, persister
    finally:
        persister.delete(_DID)
        if hasattr(client, "close"):
            client.close()


@pytest.mark.integration
def test_taught_skill_survives_reboot(falkor):
    from mindsos_server.local_boot import boot_local
    from robot_demo.backend.bootstrap import _register_taught_factory

    client, persister = falkor
    _register_taught_factory()

    b1 = _stack(client)
    try:
        _, minted, _ = boot_local(
            b1.cl, b1.kl, persister, _DID, session=b1.session
        )
        assert minted is True
        teach_local(b1, box_workaround_artifact())
        assert has_taught(b1, "load_into_box")
        persister.save(_DID, b1.kl.local_metagraph(_DID))
    finally:
        b1.il.stop()

    b2 = _stack(client)
    try:
        _, minted2, reactivated = boot_local(
            b2.cl, b2.kl, persister, _DID, session=b2.session
        )
        assert minted2 is False
        assert reactivated
        assert has_taught(b2, "load_into_box")
        decl = b2.cl.get_declaration(_CAP)
        assert decl is not None
        out = decl.implementation(
            **{DS_POSE_TARGET: {"item": "carrier"}}
        )[DS_MOTION_DONE]
        assert out["taught"] is True and out["composite"] is True
        assert len(out["steps"]) == 4
    finally:
        b2.il.stop()


@pytest.mark.integration
def test_reset_run_state_keeps_skill(falkor):
    from mindsos_server.local_boot import boot_local
    from robot_demo.backend.bootstrap import _register_taught_factory

    client, persister = falkor
    _register_taught_factory()

    b1 = _stack(client)
    try:
        boot_local(b1.cl, b1.kl, persister, _DID, session=b1.session)
        teach_local(b1, box_workaround_artifact())
        persister.save(_DID, b1.kl.local_metagraph(_DID))
    finally:
        b1.il.stop()

    assert persister.reset_run_state(_DID) is True

    b2 = _stack(client)
    try:
        boot_local(b2.cl, b2.kl, persister, _DID, session=b2.session)
        assert has_taught(b2, "load_into_box")
        assert b2.cl.get_declaration(_CAP) is not None
    finally:
        b2.il.stop()
