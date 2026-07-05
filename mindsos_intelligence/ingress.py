"""Modality-aware input ingress (ADR-0197).

An :class:`InputEnvelope` carries the raw input value plus the stamped
**modality** — the ingress DataState IRI that drives capacity selection —
and the **source** — provenance metadata that must **never** be consulted
for selection (ADR-0197 §1). The boundary that admits an input stamps the
modality, *declared by the source* (RULES §7; the UI knows it fired an
action), never sniffed from bytes.

Modality is the *identity of the ingress DataState* (ADR-0197 §2): text →
``text.raw``, image → ``image.raw`` (future), action → ``action.event``
(future). There is no separate modality enum.

``interpret`` (``phase_1``) accepts either a raw value (legacy path →
construction-bound profile → all-v0, unchanged) or an ``InputEnvelope``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class InputEnvelope:
    """A modality-stamped task input (ADR-0197 §Build-decision-3).

    Attributes:
        value: The raw input value handed to Phase-1 interpretation.
        modality: The ingress DataState IRI naming the input's *type*
            (the capacity-selection key). ``None`` → no modality stamped;
            interpretation falls back to the construction-bound profile.
        source: Opaque provenance (which button / channel / API). Carried
            for audit; **never** read for capacity selection.
    """

    value: Any
    modality: Optional[str] = None
    source: Optional[Any] = None


__all__ = ["InputEnvelope"]
