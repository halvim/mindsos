"""Invocation runtime + problem-trace primitives (Phase 30).

The vertical slice implements reactive invocation end-to-end
(:func:`invoke`). Residents (``start_resident`` / ``stop_resident`` /
``ResidentSubscription``) defer to Phase 31 per PHASE_MAP §31 and
`mindsos_capacity/exceptions.py` Phase 30 docstring inventory.

Problem-trace emission is plumbed through :func:`emit_problem_trace` so
exceptions caught during ``invoke`` generate trace entries that L4 can
consume. Successful execution does not go through the trace path
(ADR-0074 anomaly-only).

ADR cross-references:
- ADR-0072 §amendment-1 (Phase 30) — InvocationResult field rename
  (``failed`` → ``success``; ``exception`` → ``error``).
- ADR-0074 §Implementation (Phase 30) — in-memory anomaly-only sink.
- ADR-0066 §Implementation (Phase 30) — InvocationResult + call_capacity
  exports lifted from ``capacity.py`` (Phase 27 layout-parity ship).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional

from .capacity import InvocationResult, _CapacityBase, call_capacity
from .exceptions import ProblemTraceError


# ── ProblemTraceRecord (in-memory; per ADR-0074) ──────────────────────


@dataclass
class ProblemTraceRecord:
    """Thin anomaly record (ADR-0074).

    Mirrors the shape the L4 ``problem-trace`` role-graph will persist.
    Held in memory for the vertical slice; writes to L2 happen through
    an L4 lifecycle process that isn't part of this package.

    Fields:
        task_id: Caller-supplied task identifier. Required.
        error_kind: Free-form classification
            (``"exception:RuntimeError"``, ``"latency"``,
            ``"low_confidence"``, …). Required.
        step_id: Optional pipeline step identifier (L4-supplied).
        mm_ref: Optional Mental Model reference (L5-shape-forward;
            never populated at Phase 30 per PHASE_MAP §0 L5-out-of-scope).
        capacity_iri: Optional IRI of the capacity whose execution
            triggered the record.
        payload: Free-form dict; multi-tenant provenance (e.g.
            ``user_id``) belongs here per R2 PB-29 single-sink lock.
        timestamp: Wall-clock seconds since epoch (default = now).
        entry_id: UUID4 string (default = fresh per construction).
    """

    task_id: str
    error_kind: str
    step_id: Optional[str] = None
    mm_ref: Optional[str] = None
    capacity_iri: Optional[str] = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class ProblemTraceSink:
    """In-memory anomaly sink per ADR-0074.

    Callers consult via :meth:`records` (read-only snapshot) and drain
    via :meth:`drain` (L4 lifecycle hook; consumes the buffer).

    Per ``CapacityLayer`` instance — single sink across all sessions.
    Multi-tenant filtering is L4's concern (filter on payload-side
    ``user_id`` provenance). Bounded-memory variant deferred per
    ADR-0074 §Alternatives B3 open-concern.
    """

    def __init__(self) -> None:
        self._records: List[ProblemTraceRecord] = []

    def emit(self, record: ProblemTraceRecord) -> None:
        """Append ``record`` to the in-memory buffer."""
        self._records.append(record)

    def records(self) -> List[ProblemTraceRecord]:
        """Return a read-only snapshot (list copy) of current records."""
        return list(self._records)

    def drain(self) -> List[ProblemTraceRecord]:
        """Return + clear the entire buffer. L4 lifecycle hook."""
        drained = self._records
        self._records = []
        return drained

    def __len__(self) -> int:
        return len(self._records)


def emit_problem_trace(
    sink: ProblemTraceSink,
    *,
    task_id: str,
    error_kind: str,
    step_id: Optional[str] = None,
    mm_ref: Optional[str] = None,
    capacity_iri: Optional[str] = None,
    payload: Optional[Mapping[str, Any]] = None,
) -> ProblemTraceRecord:
    """Validate inputs and push one anomaly record onto ``sink``.

    Args:
        sink: The problem-trace sink (owned by :class:`CapacityLayer`).
        task_id: Caller-supplied task identifier. Required (non-empty).
        error_kind: Free-form classification. Required (non-empty).
        step_id / mm_ref / capacity_iri / payload: see
            :class:`ProblemTraceRecord`.

    Raises:
        ProblemTraceError: If ``task_id`` or ``error_kind`` is empty.

    Returns:
        The constructed (and emitted) :class:`ProblemTraceRecord`.
    """
    if not task_id:
        raise ProblemTraceError("problem-trace record requires task_id")
    if not error_kind:
        raise ProblemTraceError("problem-trace record requires error_kind")
    record = ProblemTraceRecord(
        task_id=task_id,
        error_kind=error_kind,
        step_id=step_id,
        mm_ref=mm_ref,
        capacity_iri=capacity_iri,
        payload=dict(payload or {}),
    )
    sink.emit(record)
    return record


# ── Reactive invocation (ADR-0072) ────────────────────────────────────


def invoke(
    declaration: _CapacityBase,
    inputs: Mapping[str, Any],
    *,
    context: Optional[Mapping[str, Any]] = None,
    task_id: Optional[str] = None,
    step_id: Optional[str] = None,
    problem_trace_sink: Optional[ProblemTraceSink] = None,
) -> InvocationResult:
    """Run a reactive capacity with concrete ``inputs``.

    On exception (raised by the bound implementation OR by
    :func:`call_capacity` for shape mismatch), the exception is caught,
    a problem-trace record is emitted (when both ``problem_trace_sink``
    and ``task_id`` are non-None), and the returned
    :class:`InvocationResult` has ``success=False`` with ``error`` set.

    This gives L4 a single well-defined code path regardless of whether
    the capacity raised — see ADR-0072 §amendment-1 (field rename) and
    §Implementation footer.

    **Foot-gun (Phase 30 R1 PB-16 lock):** ``task_id=None`` short-
    circuits problem-trace emission. The exception is still enveloped
    in ``InvocationResult(success=False)`` but NO trace record is
    created. L4's lifecycle process is the canonical caller and will
    always pass ``task_id``.
    """
    start = time.perf_counter()
    try:
        outputs = call_capacity(declaration, inputs, context=context)
        duration_ms = (time.perf_counter() - start) * 1000.0
        return InvocationResult(
            outputs=outputs,
            duration_ms=duration_ms,
            success=True,
            trace={
                "capacity": declaration.iri,
                "inputs_keys": list(inputs.keys()),
                "outputs_keys": list(outputs.keys()),
            },
        )
    except Exception as exc:  # noqa: BLE001 — ADR-0072 envelope contract
        duration_ms = (time.perf_counter() - start) * 1000.0
        if problem_trace_sink is not None and task_id is not None:
            emit_problem_trace(
                problem_trace_sink,
                task_id=task_id,
                error_kind=f"exception:{type(exc).__name__}",
                step_id=step_id,
                capacity_iri=declaration.iri,
                payload={"message": str(exc)},
            )
        return InvocationResult(
            outputs={},
            duration_ms=duration_ms,
            success=False,
            error=exc,
            trace={"capacity": declaration.iri},
        )


__all__ = [
    "ProblemTraceRecord",
    "ProblemTraceSink",
    "emit_problem_trace",
    "invoke",
]
