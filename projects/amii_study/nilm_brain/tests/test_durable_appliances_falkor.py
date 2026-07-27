"""Live Falkor round-trip for the durable appliance library (@integration).

Mirrors core's ``test_durable_roundtrip``: boot a durable brain, persist the
appliance state, ``save``; boot a SECOND brain for the same user and assert the
state survived the ADR-0182 dict-value codec + Falkor reload. SKIPS cleanly when
no FalkorDB sidecar is reachable, so it never breaks the synthetic gate.
"""
from __future__ import annotations

import pytest

from mindsos_server.boot import boot_brain
from nilm_brain.control import Solver
from nilm_brain.persistence import persist_appliance_state, load_appliance_state


@pytest.mark.integration
def test_appliance_state_survives_falkor_roundtrip():
    from mindsos_core.config import FalkorConfig
    from mindsos_core.persistence.client import FalkorClient

    user = "nilm_durable_test"
    lib = [{"name": "A", "form": "signature", "inst": 0, "vector": [0.1, 0.2, 0.3]}]
    norm = {"mean": [0.1, 0.2, 0.3], "std": [0.1, 0.1, 0.1], "provenance": "t"}
    cutoff = {"cutoff": 0.42, "provenance": "neg_aware"}

    # ── First brain: persist + save (skip if no live Falkor) ───────────
    client = FalkorClient(FalkorConfig.from_env())
    try:
        try:
            stack = boot_brain(client, user=user)
        except Exception as e:  # no sidecar -> not a failure of this slice
            pytest.skip(f"no live FalkorDB for round-trip: {type(e).__name__}: {e}")
        s = Solver(user, cl=stack.cl, session=stack.session)
        s.appliance_library = lib
        s.signature_norm = norm
        s.match_cutoff = cutoff
        assert persist_appliance_state(stack.kl, user, s) is not None
        stack.save()
    finally:
        client.close()

    # ── Second brain: reload + assert survival ─────────────────────────
    client2 = FalkorClient(FalkorConfig.from_env())
    try:
        stack2 = boot_brain(client2, user=user)
        got = load_appliance_state(stack2.kl, user)
        assert got is not None, "appliance state did not survive the Falkor round-trip"
        assert got["library"][0]["vector"] == [0.1, 0.2, 0.3]
        assert got["match_cutoff"]["cutoff"] == 0.42
        assert got["signature_norm"]["mean"] == [0.1, 0.2, 0.3]
    finally:
        client2.close()
