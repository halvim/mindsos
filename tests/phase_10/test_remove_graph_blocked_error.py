"""RPB-10 — RemoveGraphBlockedError class shape + .impact carry."""

from __future__ import annotations

from mindsos_core import (
    BlockedReason,
    CoreError,
    RemovalImpact,
    RemoveGraphBlockedError,
)


def test_blocked_error_is_core_error() -> None:
    assert issubclass(RemoveGraphBlockedError, CoreError)


def test_blocked_error_carries_impact_and_reason() -> None:
    impact = RemovalImpact(
        incoming_ref_properties=[("n1", "ref:lex")],
        blocked_reason="dangling-refs",
    )
    err = RemoveGraphBlockedError(
        graph_id="g1",
        impact=impact,
        blocked_reason=BlockedReason.DANGLING_REFS,
    )
    assert err.graph_id == "g1"
    assert err.impact is impact
    assert err.blocked_reason is BlockedReason.DANGLING_REFS
    assert "dangling-refs" in str(err)


def test_blocked_error_message_format() -> None:
    err = RemoveGraphBlockedError(
        graph_id="g2",
        impact=RemovalImpact(),
        blocked_reason=BlockedReason.INCIDENT_META_EDGES_CASCADE_FALSE,
    )
    assert "g2" in str(err)
    assert "incident-meta-edges-cascade-false" in str(err)


def test_blocked_reason_enum_values() -> None:
    assert BlockedReason.DANGLING_REFS.value == "dangling-refs"
    assert BlockedReason.INCIDENT_META_EDGES_CASCADE_FALSE.value == "incident-meta-edges-cascade-false"
    # str-Enum behavior
    assert BlockedReason.DANGLING_REFS == "dangling-refs"
