"""Live Falkor round-trip for the durable appliance library (@integration).

Mirrors core's ``test_durable_roundtrip``: persist the appliance state, ``save``,
boot a SECOND brain for the same user, assert it survived the ADR-0182 codec +
Falkor reload. SKIPS cleanly when no FalkorDB sidecar is reachable (the connect
happens at client construction), so it never breaks the synthetic gate.
"""
from __future__ import annotations

import pytest

from mindsos_server.boot import boot_brain
from nilm_brain.persistence import persist_appliance_state, load_appliance_state


def _client_or_skip():
    from mindsos_core.config import FalkorConfig
    from mindsos_core.persistence.client import FalkorClient
    try:
        return FalkorClient(FalkorConfig.from_env())
    except Exception as e:  # no sidecar -> not a failure of this slice
        pytest.skip(f"no live FalkorDB for round-trip: {type(e).__name__}: {e}")


@pytest.mark.integration
def test_appliance_state_survives_falkor_roundtrip():
    from types import SimpleNamespace

    user = "nilm_durable_test"
    s = SimpleNamespace(
        appliance_library=[{"name": "A", "form": "signature", "inst": 0,
                            "vector": [0.1, 0.2, 0.3]}],
        signature_norm={"mean": [0.1, 0.2, 0.3], "std": [0.1, 0.1, 0.1],
                        "provenance": "t"},
        match_cutoff={"cutoff": 0.42, "provenance": "neg_aware"})

    client = _client_or_skip()
    try:
        stack = boot_brain(client, user=user)
        assert persist_appliance_state(stack.kl, user, s) is not None
        stack.save()
    finally:
        client.close()

    client2 = _client_or_skip()
    try:
        stack2 = boot_brain(client2, user=user)
        got = load_appliance_state(stack2.kl, user)
        assert got is not None, "appliance state did not survive the Falkor round-trip"
        assert got["library"][0]["vector"] == [0.1, 0.2, 0.3]
        assert got["match_cutoff"]["cutoff"] == 0.42
        assert got["signature_norm"]["mean"] == [0.1, 0.2, 0.3]
    finally:
        client2.close()
