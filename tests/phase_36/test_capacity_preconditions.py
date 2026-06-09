"""Phase 36 — capacity-body semantic-validator precondition integration.

ADR-0139 §Capacity-contract: L3 write capacities call semantic
validators as preconditions BEFORE invoking
``handle.write_and_validate(...)``. Phase 36 wires the 2 shipped
capacities (``capacity:consolidate:mm`` + ``capacity:trace:problem``)
to call ``handle.validate_node(...)`` and raise
:class:`SemanticValidationError` on ``not result.ok``.

This file exercises:

1. Happy-path: bootstrapped KL → validator chain returns ok → capacity
   body proceeds to write_and_validate and returns WriteResult.
2. Seeded-violation: monkeypatch validate_node to return ok=False →
   capacity body raises SemanticValidationError → write_and_validate
   is NOT reached (pre-mint timing per R3-PB-H).
3. Cross-validation: the SemanticValidationError carries the failed
   :class:`ValidationResult` on ``.result`` (R3-PB-B).

PHASE_MAP §36 Tests-line target (reframed by §inline-amendment per
R3-PB-F): "semantic catches a seeded violation that structural
misses; both run during write_and_validate critical section" —
semantic in capacity body precondition, structural in L1 add_node
called from write_and_validate.
"""

from __future__ import annotations

import pytest

from mindsos_capacity.builtins.consolidate import (
    DS_MM_COMPOSITE_INSTANCE,
    _consolidate_mm_impl,
)
from mindsos_capacity.builtins.trace import (
    DS_PROBLEM_TRACE_RECORD,
    _trace_problem_impl,
)
from mindsos_capacity.context import CapacityContext
from mindsos_capacity.write_outcome import WriteResult
from mindsos_knowledge import (
    KLWriteHandle,
    KnowledgeLayer,
    SemanticValidationError,
    ValidationResult,
)
from tests.phase_33._fixtures import build_session_with_caps


def _kl() -> KnowledgeLayer:
    return KnowledgeLayer.bootstrap()


def _ctx(kl, sess) -> CapacityContext:
    """Build a CapacityContext exposing an (ungated) ``writeable`` capability
    bound to ``sess`` (ADR-0180). These tests exercise the validator
    precondition, not the L4 write gate, so the capability is ungated."""
    return CapacityContext(
        session_id=sess.session_id,
        user_id=sess.user_id,
        learned_parameters_snapshot={},
        kl=kl,
        writeable=lambda *, role, scope, version="v1": kl.writeable(
            sess, role, scope, version=version
        ),
    )


# ── Happy path: bootstrap KL → validator ok → body returns WriteResult ─


def test_consolidate_mm_happy_path_returns_write_result():
    """Bootstrap KL has Local memories role-graph; validate_node chain
    returns ok; body proceeds to write_and_validate and returns
    WriteResult."""
    kl = _kl()
    sess = build_session_with_caps("alice", frozenset())
    ctx = _ctx(kl, sess)
    result = _consolidate_mm_impl(
        **{
            DS_MM_COMPOSITE_INSTANCE: {"episode_id": "e-happy", "value": "v"},
            "context": ctx,
        }
    )
    assert isinstance(result, WriteResult)
    assert result.role == "episodic_memories"
    assert result.scope == "local"
    assert "episodic-memories-v1:episode:alice:e-happy" == result.iri


def test_trace_problem_happy_path_returns_write_result():
    kl = _kl()
    sess = build_session_with_caps(
        "admin", frozenset({"CAN_WRITE_GLOBAL"})
    )
    ctx = _ctx(kl, sess)
    result = _trace_problem_impl(
        **{
            DS_PROBLEM_TRACE_RECORD: {"trace_id": "t-happy", "value": "v"},
            "context": ctx,
        }
    )
    assert isinstance(result, WriteResult)
    assert result.role == "problem-trace"
    assert result.scope == "global"
    assert "problem-trace-v1:entry:t-happy" == result.iri


# ── Seeded violation: validator fails → SemanticValidationError ───────


def test_consolidate_mm_raises_on_semantic_validation_fail(monkeypatch):
    """Monkeypatch validate_node to return a failed ValidationResult;
    capacity body raises SemanticValidationError carrying the result.
    The R2-PB-J wiring shape: ``vr = handle.validate_node(...); if not
    vr.ok: raise SemanticValidationError(vr)``.
    """
    seeded = ValidationResult.violated("seeded role-routing miss")
    monkeypatch.setattr(
        KLWriteHandle,
        "validate_node",
        lambda self, **kw: seeded,
    )

    kl = _kl()
    sess = build_session_with_caps("alice", frozenset())
    ctx = _ctx(kl, sess)
    with pytest.raises(SemanticValidationError) as exc_info:
        _consolidate_mm_impl(
            **{
                DS_MM_COMPOSITE_INSTANCE: {
                    "episode_id": "e-violated",
                    "value": "v",
                },
                "context": ctx,
            }
        )
    assert exc_info.value.result is seeded
    assert exc_info.value.result.violation == "seeded role-routing miss"


def test_trace_problem_raises_on_semantic_validation_fail(monkeypatch):
    """Symmetric test for trace:problem — semantic-validator gate raises
    SemanticValidationError; cap-denial gate is separately tested at
    Phase 34. R2-PB-J wiring."""
    seeded = ValidationResult.violated("seeded violation for trace")
    monkeypatch.setattr(
        KLWriteHandle,
        "validate_node",
        lambda self, **kw: seeded,
    )

    kl = _kl()
    sess = build_session_with_caps(
        "admin", frozenset({"CAN_WRITE_GLOBAL"})
    )
    ctx = _ctx(kl, sess)
    with pytest.raises(SemanticValidationError) as exc_info:
        _trace_problem_impl(
            **{
                DS_PROBLEM_TRACE_RECORD: {
                    "trace_id": "t-violated",
                    "value": "v",
                },
                "context": ctx,
            }
        )
    assert exc_info.value.result is seeded


# ── Pre-mint timing: validator gate fires BEFORE mint_iri ─────────────


def test_consolidate_mm_precondition_fires_before_mint(monkeypatch):
    """Validator runs in capacity precondition; on failure, mint_iri
    must NOT be called (R3-PB-H pre-mint timing — fail fast, no IRI
    churn). Compare against handle.graph()'s KeyError which would fire
    AFTER mint_iri in write_and_validate."""
    monkeypatch.setattr(
        KLWriteHandle,
        "validate_node",
        lambda self, **kw: ValidationResult.violated("pre-mint timing test"),
    )

    mint_called: list[bool] = []
    original_mint = KLWriteHandle.mint_iri

    def _track_mint(self, **kw):
        mint_called.append(True)
        return original_mint(self, **kw)

    monkeypatch.setattr(KLWriteHandle, "mint_iri", _track_mint)

    kl = _kl()
    sess = build_session_with_caps("alice", frozenset())
    ctx = _ctx(kl, sess)
    with pytest.raises(SemanticValidationError):
        _consolidate_mm_impl(
            **{
                DS_MM_COMPOSITE_INSTANCE: {
                    "episode_id": "e-timing",
                    "value": "v",
                },
                "context": ctx,
            }
        )
    assert mint_called == [], (
        "mint_iri was called despite validation failure — precondition "
        "gate must run BEFORE mint per ADR-0139 §Capacity-contract + "
        "R3-PB-H pre-mint timing."
    )
