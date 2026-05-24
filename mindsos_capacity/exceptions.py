"""Exception hierarchy for the Intellectual Capacity Layer (L3).

Phase 27 ships 3 classes — the base + 2 actually-raised at the
definition surface. Subsequent L3 phases append their own as they
ship the raisers:

- Phase 28 — ``ConstraintViolationError`` (via ``CapacityLayer.register``).
- Phase 30 — ``PipelineNotFoundError`` + ``ProblemTraceError``.
- Phase 31 — ``ResidentError``.

Per memory ``feedback_phase_baseline_literal_audit.md``: future phases
extend this module by appending; they do not rewrite shipped classes.
"""

from __future__ import annotations


class CapacityLayerError(Exception):
    """Base class for all L3 exceptions raised by user-facing code."""


class DataStateError(CapacityLayerError):
    """A DataState declaration is structurally invalid."""


class CapacityRegistrationError(CapacityLayerError):
    """A Capacity / Monitor / Adapter cannot be registered.

    Phase 27 raisers:

    - ``_CapacityBase.validate_for_registration`` — unknown input/output
      IRI, or non-callable ``implementation``.
    - ``call_capacity`` (Phase 30 lifts the export; raiser is in
      ``capacity.py`` from Phase 27 onward) — no implementation bound,
      or return-shape mismatch against declared outputs.
    """


__all__ = [
    "CapacityLayerError",
    "DataStateError",
    "CapacityRegistrationError",
]
