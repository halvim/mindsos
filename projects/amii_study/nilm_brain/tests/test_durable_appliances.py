"""Durable appliance-state persistence — the STATE #5 slice (gate-level).

No Falkor: an EPHEMERAL boot gives a full Local with the ``learned-parameters``
role and an in-memory persister. These tests exercise the persistence LOGIC
directly (set the Solver's learned params, persist, read back) — deliberately
NOT through ``teach_appliance``, so they need no PLAID record and no segment
run. The live Falkor codec round-trip is covered by the ``@integration`` test
``test_durable_appliances_falkor.py`` (not collected by the default gate).
"""
from __future__ import annotations

import pytest

from mindsos_server.boot import boot_brain
from nilm_brain.control import Solver
from nilm_brain.persistence import (
    persist_appliance_state, load_appliance_state, apply_appliance_state,
)


@pytest.fixture(scope="module")
def stack():
    # Ephemeral: in-memory Global + InMemoryLocalPersister, no Falkor needed.
    return boot_brain(None, user="nilm_dur")


def _solver(stack, user):
    return Solver(user, cl=stack.cl, session=stack.session)


def _lib():
    return [{"name": "A", "form": "signature", "inst": 0, "vector": [0.1, 0.2, 0.3]},
            {"name": "B", "form": "signature", "inst": 1, "vector": [0.4, 0.5, 0.6]}]


def test_persist_load_roundtrip(stack):
    u = "nilm_t1"
    s = _solver(stack, u)
    s.appliance_library = _lib()
    s.signature_norm = {"mean": [0.25, 0.35, 0.45], "std": [0.15, 0.15, 0.15],
                        "provenance": "library_fit:2refs"}
    s.match_cutoff = {"cutoff": 0.5, "provenance": "neg_aware"}

    assert persist_appliance_state(stack.kl, u, s) is not None
    got = load_appliance_state(stack.kl, u)
    assert got["library"] == s.appliance_library
    assert got["signature_norm"] == s.signature_norm
    assert got["match_cutoff"] == s.match_cutoff

    # applying into a fresh Solver restores the learned state
    s2 = _solver(stack, u)
    assert apply_appliance_state(s2, got) is True
    assert s2.appliance_library == s.appliance_library
    assert s2.match_cutoff == s.match_cutoff


def test_append_latest_wins(stack):
    u = "nilm_t2"
    s = _solver(stack, u)
    s.appliance_library = [{"name": "A", "vector": [1.0]}]
    s.match_cutoff = {"cutoff": 0.3}
    persist_appliance_state(stack.kl, u, s)

    s.appliance_library = [{"name": "A", "vector": [1.0]}, {"name": "C", "vector": [2.0]}]
    s.match_cutoff = {"cutoff": 0.4}
    persist_appliance_state(stack.kl, u, s)

    got = load_appliance_state(stack.kl, u)
    assert len(got["library"]) == 2
    assert got["match_cutoff"]["cutoff"] == 0.4


def test_refuse_unfit_cutoff(stack):
    u = "nilm_t3"
    s = _solver(stack, u)
    s.appliance_library = [{"name": "A", "vector": [1.0]}]
    s.match_cutoff = {"cutoff": float("inf"), "provenance": "default:accept-all"}
    with pytest.raises(ValueError):
        persist_appliance_state(stack.kl, u, s)


def test_empty_is_noop(stack):
    u = "nilm_t4"
    s = _solver(stack, u)
    assert persist_appliance_state(stack.kl, u, s) is None
    assert load_appliance_state(stack.kl, u) is None
    assert apply_appliance_state(s, None) is False
