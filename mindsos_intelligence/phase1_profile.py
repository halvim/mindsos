"""Phase1Profile — per-consumer selection of interpretation bodies (ADR-0195).

The Phase-1 interpretation flow (``phase_1.interpret``) dispatches four
steps — ``process`` / ``hint`` / ``derive_goal`` / ``map`` — each of which
falls back to the shipped v0 placeholder (``phase1_v0.py``) when the
corresponding slot is unset. A real consumer supplies at least ``hint`` +
``map`` (the only generic default is v0 → trivial).

**Dispatcher-level binding, no metagraph scope-mix (ADR-0195 hard
constraint a).** A profile is a *dispatch-time selection of which capacity
IRI to invoke*, held on the :class:`~mindsos_intelligence.dispatch.L4Dispatcher`.
It is NOT a registration that co-locates Global DataStates with Local
capacities in one metagraph. A consumer registers its real bodies +
DataStates + request-patterns into its own (Local) scope; the profile merely
names the IRIs to dispatch.

**resolve is composed, not slotted (ADR-0195 §Decision.3).** Reference
resolution (e.g. an index ``8`` → a canonical id) is not a fixed profile
slot: it is discovered by the shipped bipartite ``find_pipeline``
(ADR-0156) from the reference's DataState *type* to the canonical
``resolve_target_datastate``, then run via the shipped
``pipeline_execution`` executor. The profile only needs the target type;
the start type comes from the hint body's ``reference_kind`` at runtime.
For the arc consumer that composed chain is length-1 (``[resolve]``); a
request whose reference is already canonical composes a 0-step pipeline
(pass-through).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Phase1Profile:
    """Construction-bound interpretation binding for one consumer.

    Every field is optional. An unset step slot falls back to the v0
    placeholder IRI. ``resolve_target_datastate`` unset means the consumer
    performs no reference resolution (interpret returns the mapping only).
    """

    process: Optional[str] = None
    hint: Optional[str] = None
    derive_goal: Optional[str] = None
    map: Optional[str] = None
    resolve_target_datastate: Optional[str] = None


__all__ = ["Phase1Profile"]
