"""Durable appliance-state persistence — the STATE #5 slice (gate-level).

No Falkor: an EPHEMERAL boot gives a full Local with the ``learned-parameters``
role + an in-memory persister. These tests exercise the persistence LOGIC only
(persist/load/apply the three learned params), using a lightweight fake in place
of a real ``Solver`` — persistence reads just ``appliance_library`` /
``signature_norm`` / ``match_cutoff``, so no capacity registration is needed
(and none is duplicated). The live Falkor codec round-trip is the @integration
test ``test_durable_appliances_falkor.py``.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from mindsos_server.boot import boot_brain
from nilm_brain.persistence import (
    persist_appliance_state, load_appliance_state, apply_appliance_state,
)


@pytest.fixture
def kl():
    # Fresh ephemeral brain per test (in-memory, no Falkor) -> isolated Local.
    return boot_brain(None, user="nilm").kl


def _fake(library=None, norm=None, cutoff=None):
    return SimpleNamespace(appliance_library=library or [],
                           signature_norm=norm, match_cutoff=cutoff)


def _lib():
    return [{"name": "A", "form": "signature", "inst": 0, "vector": [0.1, 0.2, 0.3]},
            {"name": "B", "form": "signature", "inst": 1, "vector": [0.4, 0.5, 0.6]}]


def test_persist_load_roundtrip(kl):
    norm = {"mean": [0.25, 0.35, 0.45], "std": [0.15, 0.15, 0.15],
            "provenance": "library_fit:2refs"}
    cutoff = {"cutoff": 0.5, "provenance": "neg_aware"}
    s = _fake(_lib(), norm, cutoff)

    assert persist_appliance_state(kl, "nilm", s) is not None
    got = load_appliance_state(kl, "nilm")
    assert got["library"] == s.appliance_library
    assert got["signature_norm"] == norm
    assert got["match_cutoff"] == cutoff

    s2 = _fake()
    assert apply_appliance_state(s2, got) is True
    assert s2.appliance_library == s.appliance_library
    assert s2.match_cutoff == cutoff


def test_append_latest_wins(kl):
    persist_appliance_state(kl, "nilm", _fake([{"name": "A", "vector": [1.0]}],
                                              cutoff={"cutoff": 0.3}))
    persist_appliance_state(kl, "nilm", _fake(
        [{"name": "A", "vector": [1.0]}, {"name": "C", "vector": [2.0]}],
        cutoff={"cutoff": 0.4}))
    got = load_appliance_state(kl, "nilm")
    assert len(got["library"]) == 2
    assert got["match_cutoff"]["cutoff"] == 0.4


def test_refuse_unfit_cutoff(kl):
    s = _fake([{"name": "A", "vector": [1.0]}],
              cutoff={"cutoff": float("inf"), "provenance": "default:accept-all"})
    with pytest.raises(ValueError):
        persist_appliance_state(kl, "nilm", s)


def test_empty_is_noop(kl):
    assert persist_appliance_state(kl, "nilm", _fake()) is None
    assert load_appliance_state(kl, "nilm") is None
    assert apply_appliance_state(_fake(), None) is False
