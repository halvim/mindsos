"""``NeedsInput`` — the user-clarification capacity verdict (ADR-0196).

A capacity body returns :class:`NeedsInput` when it cannot proceed without
asking the user — the recoverable sibling of ``dont_know`` ("I can proceed
*if you answer this*", vs "I can't do this"). The trigger is **caller-
controlled** (ADR-0196 §Decision.1): core defines the verdict and how it is
raised (a body returns it), never *when* — the decision to ask is policy
inside the body.

``call_capacity`` short-circuits output validation when a body returns this
(it is not an outputs mapping); ``runtime.invoke`` envelopes it onto
``InvocationResult.needs_input`` (parallel to the write-body
``write_outcome`` bypass). It is **import-isolated** — a plain dataclass with
no cross-layer imports — so it lives inside ``mindsos_capacity``.

Not exported from ``mindsos_capacity.__all__`` (export-slate parity, the
``InputContractError`` precedent) — reachable via
``mindsos_capacity.needs_input``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class NeedsInput:
    """A recoverable request for user input (ADR-0196 §Decision.2).

    Attributes:
        question: The human-readable question to render.
        missing: The DataState IRI whose value the answer supplies.
        choices: ``{label -> task_input}`` — each value is a **ready-to-
            re-submit** ``task_input`` so a UI re-submits directly without
            reconstructing the request. Empty for free-text answers.
        template: Optional free-text answer template (used in place of
            enumerated ``choices``).
    """

    question: str
    missing: str
    choices: Mapping[str, Any] = field(default_factory=dict)
    template: Optional[str] = None


__all__ = ["NeedsInput"]
