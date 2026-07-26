"""Text phase-1 catalog (ADR-0197 §5) — the one real modality for v1.

Wires the shipped ``text.space_split`` (``text.raw`` → ``text.tokens``,
:mod:`mindsos_capacity.builtins.text`) as the Phase-1 ``process`` step, and
supplies trivial text-realm ``hint`` / ``derive_goal`` / ``map`` bodies that
consume ``text.tokens`` as this modality's *structured* input. That closes
the phase1↔text disconnect: ``text.tokens`` is now consumed **inside**
interpretation, by a capacity, instead of being produced and dropped.

The downstream bodies are intentionally trivial — they exist to prove the
modality wiring, not to do language understanding (a real consumer, e.g.
arc, supplies its own ``hint`` / ``map`` per ADR-0195). The ``hint`` body
reads the tokens (``n_tokens``) so token-flow through the seam is
observable.

Layering: this is an L3 catalog (capacities + DataStates). The L4
``Phase1Profile`` that names these IRIs, and the dispatcher
``{modality→Phase1Profile}`` table that selects it, live in
:mod:`mindsos_intelligence` — this module only exports the IRIs.
"""

from __future__ import annotations

from typing import Any, List

from ..capacity import Capacity
from ..exceptions import CapacityRegistrationError
from ..identifiers import (
    CATEGORY_DECISION,
    CATEGORY_HINT,
    CATEGORY_PERCEPTION,
    capacity_iri,
)
from .phase1_v0 import DS_GOAL, DS_HINT_SET, DS_MAPPING, install_phase1_v0
from .text import DS_RAW_TEXT, DS_TOKENS, install_text_capacities

# ── Public IRIs (the L4 text profile names these) ─────────────────────

#: The text ingress modality = the identity of the ``text.raw`` DataState.
TEXT_MODALITY_DS = DS_RAW_TEXT

TEXT_PROCESS_IRI = capacity_iri(CATEGORY_PERCEPTION, "text.space_split")
TEXT_HINT_IRI = capacity_iri(CATEGORY_HINT, "text")
TEXT_DERIVE_GOAL_IRI = capacity_iri(CATEGORY_DECISION, "text_derive_goal")
TEXT_MAP_IRI = capacity_iri(CATEGORY_DECISION, "text_map")

TEXT_REQUEST_PATTERN_IRI = "request-pattern:text:trivial"


# ── Capacity implementations (keyword-first, input-iri-keyed) ─────────


def _text_hint(**kwargs: Any) -> dict:
    tokens = kwargs.get(DS_TOKENS) or []
    return {DS_HINT_SET: {"n_tokens": len(tokens)}}


def _text_derive_goal(**kwargs: Any) -> dict:
    return {DS_GOAL: {"goal": "text:trivial-goal"}}


def _text_map(**kwargs: Any) -> dict:
    return {
        DS_MAPPING: {
            "request_pattern_iri": TEXT_REQUEST_PATTERN_IRI,
            "mapping_confidence": 1.0,
        }
    }


# ── Capacity factories ────────────────────────────────────────────────


def build_text_hint() -> Capacity:
    """``text.tokens`` → ``hint_set`` — reads tokens so flow is observable."""
    return Capacity(
        name="text",
        category=CATEGORY_HINT,
        inputs=(DS_TOKENS,),
        outputs=(DS_HINT_SET,),
        implementation=_text_hint,
        description="Text hint: token-count over text.tokens.",
    )


def build_text_derive_goal() -> Capacity:
    return Capacity(
        name="text_derive_goal",
        category=CATEGORY_DECISION,
        inputs=(DS_TOKENS, DS_HINT_SET),
        outputs=(DS_GOAL,),
        implementation=_text_derive_goal,
        description="Text derive-goal: trivial goal over text.tokens.",
    )


def build_text_map() -> Capacity:
    return Capacity(
        name="text_map",
        category=CATEGORY_DECISION,
        inputs=(DS_TOKENS, DS_HINT_SET, DS_GOAL),
        outputs=(DS_MAPPING,),
        implementation=_text_map,
        description="Text map: fixed text request-pattern, confidence 1.0.",
    )


# ── Installer (idempotent with partial-state detection) ──────────────

_CAP_IRIS = (TEXT_HINT_IRI, TEXT_DERIVE_GOAL_IRI, TEXT_MAP_IRI)


def install_phase1_text(capacity_layer) -> None:
    """Register the text phase-1 catalog on ``capacity_layer``.

    Ensures the dependencies first (both idempotent): ``install_phase1_v0``
    (the ``hint_set`` / ``goal`` / ``mapping`` output DataStates) and
    ``install_text_capacities`` (``text.raw`` / ``text.tokens`` + the
    ``text.space_split`` process capacity). Then registers the three
    text-realm downstream capacities.

    Idempotent with partial-state detection, matching the sibling
    installers: all three text caps present → no-op; some-but-not-all →
    :class:`CapacityRegistrationError`.
    """
    install_phase1_v0(capacity_layer)
    install_text_capacities(capacity_layer)

    mg = capacity_layer.global_metagraph()
    cap_index = capacity_layer._capacity_index[mg.metagraph_id]
    present = {iri for iri in _CAP_IRIS if iri in cap_index}
    if len(present) == len(_CAP_IRIS):
        return
    if present:
        raise CapacityRegistrationError(
            "install_phase1_text: partial install state detected — "
            f"present={sorted(present)}, "
            f"missing={sorted(set(_CAP_IRIS) - present)}"
        )
    capacity_layer.register_capacity(build_text_hint())
    capacity_layer.register_capacity(build_text_derive_goal())
    capacity_layer.register_capacity(build_text_map())


__all__ = [
    "TEXT_MODALITY_DS",
    "TEXT_PROCESS_IRI",
    "TEXT_HINT_IRI",
    "TEXT_DERIVE_GOAL_IRI",
    "TEXT_MAP_IRI",
    "TEXT_REQUEST_PATTERN_IRI",
    "build_text_hint",
    "build_text_derive_goal",
    "build_text_map",
    "install_phase1_text",
]
