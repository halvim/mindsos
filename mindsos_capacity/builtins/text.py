"""Text-processing built-ins used by the L3 vertical slice (Phase 31).

Ships three DataStates (``raw_text``, ``tokens``, ``sentences``) and
two capacities (``text.space_split``, ``text.sentence_split``) that
together prove the vertical slice end-to-end via
``mindsos capacity invoke``.

The implementations are intentionally boring — they exist only to
prove the slice. Real language processing (Unicode normalisation,
regex-based sentence boundaries, locale awareness, etc.) is out of
scope.

Halvim divergences from parent:

- :func:`install_text_capacities` is **idempotent with partial-state
  detection** per R1 PB-12 lock: all-present → no-op return;
  some-present-some-missing → ``CapacityRegistrationError``
  ("partial install state detected"); none-present → install.
  Parent's installer is fire-and-fail on any duplicate.
- ``install_text_capacities`` is **opt-in** at Phase 31 per pre-R0
  PB-ε lock (CLI's fresh-layer init calls it explicitly; L3 bootstrap
  ``create_global`` does NOT auto-install).
"""

from __future__ import annotations

import re
from typing import Any, List

from ..bootstrap import ensure_datastate_graph
from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..exceptions import CapacityRegistrationError
from ..identifiers import (
    CATEGORY_PERCEPTION,
    capacity_iri,
    datastate_iri,
)


# ── DataState IRIs (stable public constants) ──────────────────────────

DS_RAW_TEXT = datastate_iri("text.raw")
DS_TOKENS = datastate_iri("text.tokens")
DS_SENTENCES = datastate_iri("text.sentences")


def text_datastates() -> List[DataState]:
    """Return the three DataStates needed by the text pipeline."""
    return [
        DataState(
            name="text.raw",
            shape=ShapeDescriptor.scalar("str", opaque_tag="text.raw"),
            description="An uninterpreted string of text.",
            provenance_category=CATEGORY_PERCEPTION,
        ),
        DataState(
            name="text.tokens",
            shape=ShapeDescriptor.list_of("str", opaque_tag="text.tokens"),
            description="A list of whitespace-delimited surface tokens.",
            provenance_category=CATEGORY_PERCEPTION,
        ),
        DataState(
            name="text.sentences",
            shape=ShapeDescriptor.list_of("str", opaque_tag="text.sentences"),
            description="A list of sentence strings.",
            provenance_category=CATEGORY_PERCEPTION,
        ),
    ]


# ── Capacity implementations ──────────────────────────────────────────


def _space_split(*, text: str, context: Any = None, **_: Any) -> List[str]:
    """Split on whitespace. Empty input → empty list."""
    if text is None:
        return []
    if not isinstance(text, str):
        raise TypeError(f"space_split expects str, got {type(text).__name__}")
    return text.split()


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def _sentence_split(*, text: str, context: Any = None, **_: Any) -> List[str]:
    """Split on sentence-terminal punctuation followed by whitespace.

    Empty input → empty list. Trailing whitespace is stripped from each
    sentence. No newline handling beyond what the regex captures — the
    point is to prove the vertical slice, not to be linguistically
    correct.
    """
    if text is None or text == "":
        return []
    if not isinstance(text, str):
        raise TypeError(f"sentence_split expects str, got {type(text).__name__}")
    parts = [p.strip() for p in _SENTENCE_BOUNDARY.split(text)]
    return [p for p in parts if p]


# ── Capacity factories ────────────────────────────────────────────────


def build_space_split() -> Capacity:
    """Capacity: ``text.raw`` → ``text.tokens`` via whitespace splitting."""
    return Capacity(
        name="text.space_split",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_RAW_TEXT,),
        outputs=(DS_TOKENS,),
        implementation=_space_split_callable,
        description="Whitespace-tokeniser. text.raw → text.tokens.",
        cost_prior=1.0,
        latency_ms_prior=1.0,
    )


def build_sentence_split() -> Capacity:
    """Capacity: ``text.raw`` → ``text.sentences`` via regex punctuation."""
    return Capacity(
        name="text.sentence_split",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_RAW_TEXT,),
        outputs=(DS_SENTENCES,),
        implementation=_sentence_split_callable,
        description="Regex sentence-splitter. text.raw → text.sentences.",
        cost_prior=1.2,
        latency_ms_prior=1.5,
    )


# ── Callable wrappers: keyword-first, input-iri-first ────────────────
#
# The runtime calls declarations with ``**inputs`` where keys are the
# **DataState IRIs**. The implementations above use human-friendly
# Python kwargs for readability; these wrappers translate.


def _space_split_callable(**kwargs: Any) -> dict:
    text = kwargs.get(DS_RAW_TEXT)
    context = kwargs.get("context")
    return {DS_TOKENS: _space_split(text=text, context=context)}


def _sentence_split_callable(**kwargs: Any) -> dict:
    text = kwargs.get(DS_RAW_TEXT)
    context = kwargs.get("context")
    return {DS_SENTENCES: _sentence_split(text=text, context=context)}


# ── Convenience installer (idempotent with partial-state detection) ──


# Public capacity IRIs for the two text capacities (computed once;
# tests + the partial-state probe rely on these literal strings).
_SPACE_SPLIT_IRI = capacity_iri(CATEGORY_PERCEPTION, "text.space_split")
_SENTENCE_SPLIT_IRI = capacity_iri(CATEGORY_PERCEPTION, "text.sentence_split")
_DS_IRIS = (DS_RAW_TEXT, DS_TOKENS, DS_SENTENCES)
_CAP_IRIS = (_SPACE_SPLIT_IRI, _SENTENCE_SPLIT_IRI)
_TEXT_FAMILY_IRIS = _DS_IRIS + _CAP_IRIS


def install_text_capacities(capacity_layer) -> None:
    """Register every text-realm DataState and capacity on ``capacity_layer``.

    Idempotent with partial-state detection per R1 PB-12:

    - All 5 IRIs present → no-op (silent return).
    - Some present, some missing → ``CapacityRegistrationError``
      ("partial install state detected"). Layer state is corrupted
      (or someone manually inserted some-but-not-all of the family).
    - None present → install all 5 (3 DataStates + 2 capacities).

    Always targets Global. No ``session`` argument — install is an
    admin/bootstrap concern; CLI's fresh-layer init calls it sessionless.

    Note (B-31-T1 hotfix): DataStates and Capacities live in different
    indexes — DataStates in the ``capacity:datastates`` role-graph's
    ``nodes`` dict; Capacities in ``CapacityLayer._capacity_index``
    keyed by metagraph id. Probe both per type.

    Raises:
        CapacityRegistrationError: Partial install state detected.
    """
    mg = capacity_layer.global_metagraph()
    cap_index = capacity_layer._capacity_index[mg.metagraph_id]
    ds_graph = ensure_datastate_graph(mg, strict=capacity_layer._strict)

    ds_present = {iri for iri in _DS_IRIS if iri in ds_graph.nodes}
    cap_present = {iri for iri in _CAP_IRIS if iri in cap_index}
    present_total = len(ds_present) + len(cap_present)

    if present_total == len(_TEXT_FAMILY_IRIS):
        return  # all present — no-op
    if present_total > 0:
        raise CapacityRegistrationError(
            "install_text_capacities: partial install state detected — "
            f"datastates_present={sorted(ds_present)}, "
            f"capacities_present={sorted(cap_present)}, "
            f"missing="
            f"{sorted(set(_TEXT_FAMILY_IRIS) - ds_present - cap_present)}"
        )
    # None present — install all 5 (DataStates first per
    # _CapacityBase.validate_for_registration's forward-ref restriction).
    for ds in text_datastates():
        capacity_layer.register_datastate(ds)
    capacity_layer.register_capacity(build_space_split())
    capacity_layer.register_capacity(build_sentence_split())


__all__ = [
    "DS_RAW_TEXT",
    "DS_TOKENS",
    "DS_SENTENCES",
    "text_datastates",
    "build_space_split",
    "build_sentence_split",
    "install_text_capacities",
]
