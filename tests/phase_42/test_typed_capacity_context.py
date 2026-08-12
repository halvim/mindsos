"""Phase 42 — typed CapacityContext + handle Protocols + verdicts (ADR-0159)."""

from __future__ import annotations

import dataclasses
from types import MappingProxyType

import pytest

from mindsos_capacity import (
    CancelToken,
    CancelTokenView,
    CapacityContext,
    CapacityLayerHandle,
    GoalVerdict,
    KLHandle,
    MMHandle,
    PipelineFindVerdict,
    PromotionRuleVerdict,
    ReplanVerdict,
    TierVerdict,
)


def test_capacity_context_has_eleven_fields():
    # ADR-0180 (Phase 48) adds the 11th field ``writeable`` — the
    # pre-authorized, session-bound write capability injected by L4 dispatch.
    names = {f.name for f in dataclasses.fields(CapacityContext)}
    assert names == {
        "session_id",
        "user_id",
        "learned_parameters_snapshot",
        "mm_handle",
        "cancel_token",
        "current_request_iri",
        "current_pattern_iri",
        "version_snapshot",
        "kl",
        "cl",
        "writeable",
    }


def test_capacity_context_is_frozen():
    ctx = CapacityContext(session_id="s", user_id="u", learned_parameters_snapshot={})
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.session_id = "other"  # type: ignore[misc]


def test_version_snapshot_is_read_only_mapping():
    ctx = CapacityContext(
        session_id="s",
        user_id="u",
        learned_parameters_snapshot={"a": 1},
        version_snapshot={"iri:x": 3},
    )
    assert isinstance(ctx.version_snapshot, MappingProxyType)
    assert isinstance(ctx.learned_parameters_snapshot, MappingProxyType)
    assert ctx.version_snapshot["iri:x"] == 3
    with pytest.raises(TypeError):
        ctx.version_snapshot["iri:x"] = 9  # type: ignore[index]


def test_protocols_are_runtime_checkable():
    class _MM:
        def get_or_instantiate(self, node_iri): ...
        def find_instances_by_type(self, type_iri): ...
        def produces_of(self, capacity_instance): ...
        def consumes_of(self, data_state_instance): ...

    class _KL:
        def read_at_version(self, iri, version): ...
        def global_view(self): ...

    class _CL:
        def get_declaration(self, capacity_iri): ...

    class _Tok:
        def is_set(self): return False
        def request_cancel(self): ...

    assert isinstance(_MM(), MMHandle)
    assert isinstance(_KL(), KLHandle)
    assert isinstance(_CL(), CapacityLayerHandle)
    assert isinstance(_Tok(), CancelToken)
    assert not isinstance(object(), MMHandle)


def test_cancel_token_view_exposes_only_is_set():
    class _Tok:
        def __init__(self):
            self.cancelled = False
        def is_set(self):
            return self.cancelled
        def request_cancel(self):
            self.cancelled = True

    tok = _Tok()
    view = CancelTokenView(tok)
    assert view.is_set() is False
    tok.request_cancel()
    assert view.is_set() is True
    assert not hasattr(view, "request_cancel")


def test_five_verdict_types_are_frozen_dataclasses():
    verdicts = [
        TierVerdict(tier=None, rationale="r"),
        GoalVerdict(goal=None, rationale="r"),
        PipelineFindVerdict(pipeline_iri=None, rationale="r"),
        PromotionRuleVerdict(rule_iri=None, rationale="r"),
        ReplanVerdict(should_replan=False, rationale="r"),
    ]
    for v in verdicts:
        assert dataclasses.is_dataclass(v)
        with pytest.raises(dataclasses.FrozenInstanceError):
            v.rationale = "mutated"  # type: ignore[misc]
