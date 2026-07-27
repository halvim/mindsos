"""Exception hierarchy for the Intellectual Capacity Layer (L3).

Phase 27 shipped 3 classes — the base + 2 actually-raised at the
definition surface. Subsequent L3 phases append their own as they
ship the raisers:

- Phase 28 — ``ConstraintViolationError`` (via ``CapacityLayer.add_constraint``).
- Phase 30 — ``PipelineNotFoundError`` + ``ProblemTraceError``.

(Phase 31's monitor-lifecycle exception was retired in Phase 41 when the
monitor lifecycle relocated to the L4 substrate per ADR-0155.)

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
    """


class InputContractError(CapacityRegistrationError):
    """Invoke inputs violate the declared ``CONSUMES`` contract (ADR-0072
    §amendment-2 / composition-lifecycle Slice 2 Part 6).

    ``kind`` is ``"missing_required"`` (an ``all_required`` input absent,
    or ``any_of`` satisfied by none) or ``"unexpected_input"`` (a key not
    in the declared inputs). Validated against the declaration's input
    set, respecting ``input_group``; ``fold`` is not enforced at v1 (its
    operand multiplicity is Slice 2 Part 5).

    On the ``invoke`` path it is caught into the ADR-0072 envelope
    (``success=False``) and the problem-trace record is tagged
    ``error_kind="input_contract:<kind>"``. Direct ``call_capacity`` and
    the write-bypass raise it. Subclasses ``CapacityRegistrationError`` so
    existing registration-family handlers still catch it.
    """

    def __init__(self, message: str, *, kind: str) -> None:
        super().__init__(message)
        self.kind = kind


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
    arrives (constraint enforcement at invoke-time is a Phase 30+
    concern; L4 filters constraints post-hoc).
    """


class PipelineNotFoundError(CapacityLayerError):
    """BFS pipeline-finder exhausted without reaching the target.

    Phase 30 raisers:

    - ``mindsos_capacity.pipeline.find_pipeline`` — BFS over the
      bipartite PRODUCES/CONSUMES edge set (ADR-0071 + ADR-0156)
      exhausted without finding a chain from ``start_datastate`` to
      ``target_datastate`` within ``max_depth`` steps.

    Raised (not enveloped) because "no path exists" is an L3 invariant
    of the requested query, not an implementation error in a bound
    capacity callable. ADR-0072 §Decision's "L3 raises for its own
    invariants" carve-out applies.
    """


class ProblemTraceError(CapacityLayerError):
    """Problem-trace emission is malformed.

    Phase 30 raisers:

    - ``mindsos_capacity.runtime.emit_problem_trace`` — empty
      ``request_id`` or empty ``error_kind`` argument.

    Kept thin — problem-trace records themselves are free-form, but
    the required keys must be present per ADR-0074.
    """


class WriteHandleNotWiredError(CapacityLayerError):
    """Stub-phase failure when an L3 write capacity reaches a
    :class:`KLWriteHandle` method whose body is not yet wired.

    Phase 33 ships :class:`KLWriteHandle` (``mindsos_knowledge.write_handle``)
    as a partial stub: ``metagraph()`` returns the real L1 Metagraph;
    every other method (``graph``, ``mint_iri``, ``validate_node``,
    ``validate_xref``) raises this exception. Phase 34 (ADR-0146) wires
    the working bodies + deletes the raise sites.

    Direct subclass of :class:`CapacityLayerError` — wire-state is a
    lifecycle concern distinct from registration.

    Phase 33 raisers:

    - ``KLWriteHandle.graph()`` — L1 mutation surface (Phase 34).
    - ``KLWriteHandle.mint_iri(**content)`` — version handling
      deferred post-Phase 17 retirement (ADR-0150 §amendment-3 lock).
    - ``KLWriteHandle.validate_node(...)`` — KL semantic validators
      (Phase 36; ADR-0139).
    - ``KLWriteHandle.validate_xref(...)`` — KL cross-metagraph ref
      validators (Phase 36).

    Surfaces via :func:`mindsos_capacity.runtime.invoke`'s envelope as
    ``InvocationResult(success=False, error=WriteHandleNotWiredError)``
    per ADR-0146 §amendment-1 clause 1 (Phase 33 stub-phase raise-then-
    envelope carve-out; Phase 34+ shifts to return ``ProblemTraceRecord``).
    """


class CapabilityDeniedError(CapacityLayerError):
    """Session lacks the capability an L3 write capacity requires.

    Raised by write-capacity bodies that target Global writes when the
    invoking session does not hold the required server capability
    (e.g., ``CAN_WRITE_GLOBAL`` for ``capacity:trace:problem``).

    Direct subclass of :class:`CapacityLayerError` — capability denial
    is a runtime authorisation fact, not a registration or lifecycle
    failure.

    Phase 33 raisers:

    - ``capacity:trace:problem`` body — when ``session is not None and
      not session.has(CAN_WRITE_GLOBAL)``. ``session is None`` skips
      the gate per ADR-0080 bootstrap carve-out.
    - (Local-targeting write capacities such as ``capacity:consolidate:mm``
      do NOT raise this — Local writes are ungated per ADR-0080. A
      missing session on a ``scope='local'`` write surfaces as
      ``ValueError`` from ``KnowledgeLayer.writeable`` instead.)

    Surfaces via :func:`mindsos_capacity.runtime.invoke`'s envelope as
    ``InvocationResult(success=False, error=CapabilityDeniedError)``.
    Phase 33 stub-phase carve-out per ADR-0146 §amendment-1 clause 1
    — Phase 34+ may shift to return ``ProblemTraceRecord(kind=
    "CAPABILITY_DENIED")`` per ADR-0146 §Decision once the failure-mode
    surface stabilises.
    """


__all__ = [
    "CapacityLayerError",
    "DataStateError",
    "CapacityRegistrationError",
    "InputContractError",
    "ConstraintViolationError",
    "PipelineNotFoundError",
    "ProblemTraceError",
    "WriteHandleNotWiredError",
    "CapabilityDeniedError",
]
