"""Write-side return-shape primitives (Phase 33; ADR-0146).

Ships the typed return surface for L3 write capacities (ADR-0146
symmetric write invocation contract):

- :class:`WriteResult` — frozen dataclass; successful write artefact
  (IRI + role + scope + timestamp + provenance extras).
- :data:`WriteOutcome` — type alias ``WriteResult | ProblemTraceRecord``
  documenting the union L3 write capacities return per ADR-0146.

**Phase 33 stub-phase carve-out (ADR-0146 §amendment-1 clause 1).**
Phase 33 ships write capacities whose ``KLWriteHandle`` is not wired
yet (Phase 34 wires it). At stub phase, capacities raise
:class:`WriteHandleNotWiredError` from
:meth:`KLWriteHandle.graph()`; :func:`mindsos_capacity.runtime.invoke`
catches and envelopes as ``InvocationResult(success=False,
error=WriteHandleNotWiredError)``. No ``WriteResult`` is produced at
Phase 33. The dataclass + alias ship as forward-compat surface so
Phase 34 capacity bodies can return ``WriteResult(...)`` without
introducing the type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Literal, Union

from .runtime import ProblemTraceRecord


@dataclass(frozen=True)
class WriteResult:
    """Successful write artefact produced by an L3 write capacity (ADR-0146).

    Returned by Phase 34+ working capacity bodies (e.g.,
    ``capacity:consolidate:mm`` on successful Local memory write). At
    Phase 33 stub phase, no capacity body returns this — capacities
    raise ``WriteHandleNotWiredError`` before reaching a return path.

    Attributes:
        iri: The IRI of the written node (or, for multi-node writes,
            the head/root IRI; capacity-specific convention).
        role: The role-graph role the write targeted (e.g.,
            ``"memories"`` for ``capacity:consolidate:mm``).
        scope: ``'local'`` (per-user) or ``'global'`` (shared).
        written_at: UTC timestamp at which the write committed.
        extras: Free-form provenance / side-effect metadata (audit
            timestamps, mutation_ids, retry counts, etc.); empty by
            default.
    """

    iri: str
    role: str
    scope: Literal["local", "global"]
    written_at: datetime
    extras: Dict[str, Any] = field(default_factory=dict)


#: Union return type for L3 write capacities per ADR-0146 §Decision.
#: Phase 33 stub-phase capacities never produce ``WriteResult`` — they
#: raise ``WriteHandleNotWiredError`` which ``runtime.invoke`` envelopes
#: as ``InvocationResult(success=False, error=...)``. Phase 34 wires the
#: success path.
WriteOutcome = Union[WriteResult, ProblemTraceRecord]


__all__ = ["WriteResult", "WriteOutcome"]
