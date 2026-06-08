"""Phase 46 — ALS subsystem registry (D9.1; v0 empty catalog)."""

from __future__ import annotations

import pytest

from mindsos_intelligence.als_registry import (
    ALSSubsystemRegistration,
    ALSSubsystemRegistry,
)


def _reg():
    return ALSSubsystemRegistration(
        parameter_set_iri="learned-parameters:priority-scorer",
        signal_sources=(("signal:S6", 1.0), ("signal:S9", 0.5)),
        update_mechanisms={"bayesian_update": "mechanism:bayes"},
        validation_methods=("validate:V1", "validate:V3"),
        audit_policy="batched-summary",
        eligible_audit_scopes=frozenset({"local", "global"}),
    )


def test_v0_catalog_is_empty():
    assert len(ALSSubsystemRegistry()) == 0


def test_register_and_get():
    reg = ALSSubsystemRegistry()
    reg.register("priority-scorer", _reg())
    assert len(reg) == 1
    assert reg.keys() == ("priority-scorer",)
    assert reg.get("priority-scorer").parameter_set_iri == (
        "learned-parameters:priority-scorer"
    )


def test_duplicate_registration_raises():
    reg = ALSSubsystemRegistry()
    reg.register("priority-scorer", _reg())
    with pytest.raises(ValueError):
        reg.register("priority-scorer", _reg())


def test_invalid_audit_policy_rejected():
    bad = ALSSubsystemRegistration(
        parameter_set_iri="x",
        signal_sources=(),
        update_mechanisms={},
        validation_methods=(),
        audit_policy="auto-magic",
        eligible_audit_scopes=frozenset({"local"}),
    )
    with pytest.raises(ValueError):
        ALSSubsystemRegistry().register("x", bad)
