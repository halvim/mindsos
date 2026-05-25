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

    Phase 28 raisers (via ``CapacityLayer``):

    - ``register_datastate`` — duplicate IRI in the target DataState graph.
    - ``register_capacity`` — duplicate IRI, IRI collision with existing
      node id in target category graph, unknown DataState in inputs/outputs,
      reserved-property-key collision, ``ref_to_global`` without ``user_id``,
      ``ref_to_global`` without ``ref_type`` (or vice versa), ``ref_type``
      not in ``REF_TYPES``, ``ref_to_global`` does not resolve to a Global
      capacity, declaration is not ``_CapacityBase``-derived.
    - ``get_declaration`` — no declaration registered for the given IRI.
    - ``start_resident`` (Phase 30 lifts the surface) — capacity is not
      a ``Monitor``.
    """


class ConstraintViolationError(CapacityLayerError):
    """A CONSTRAINT edge declaration violates an L3 invariant.

    Phase 28 raisers (via ``CapacityLayer.add_constraint``):

    - Unknown ``kind`` (not in ``CONSTRAINT_KINDS``).
    - Endpoint not registered (source or target IRI absent from the
      target metagraph's ``_capacity_index``).
    - Endpoints in different category graphs (cross-category constraints
      are deferred to a phase-2 concern per ADR-0085 §Implementation;
      Phase 28 v1 requires same-category).

    Future phases may add raisers when constraint enforcement runtime
    arrives (Phase 29 ships TYPE_COMPAT auto-discovery; constraint
    enforcement at invoke-time is a Phase 30+ concern).
    """


__all__ = [
    "CapacityLayerError",
    "DataStateError",
    "CapacityRegistrationError",
    "ConstraintViolationError",
]
