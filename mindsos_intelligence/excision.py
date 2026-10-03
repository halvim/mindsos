"""Excision — the borrowed model is a removable stand-in (plan item I-12).

``docs/plans/MINDSOS_LLM_PLAN.md`` §1: every conclusion that leaned on the
borrowed model can be **identified** as such, **shown** (including what was
asked), and **re-run** without it. This module is the L4 half — it locates and
dispatches; judging agreement is L3's (plan R28, R39). I-12 ships in four
gates, one claim each (plan §6, 2026-09-29): IDENTIFY, SHOWN, the substitute
declaration (L3 only), and RE-RUN.

**Identified** (R26, R38): an origin record whose ``origin_method`` is
``read_by_model``, in every mode — a replayed answer is still the model's —
refusals the model produced included, and ``environment_fault`` refusals
excluded, because no reading happened. ⚠ Measured 2026-09-29: no reader writes
an ``environment_fault`` record today (``comprehension_v0`` raises on an
outage instead), so the exclusion filters nothing the tree emits. It stays:
the field is derived from the refusal reason, and a producer that one day
records its outage must not be listed as a reading.

**Domain** (R27): the run graphs of a persisted Episode — ``read_episode``'s
``capacity_run_graphs`` — the only place a conclusion's source text lives.
The walk reads nodes only, so it answers the same on a live graph and on one
reloaded from FalkorDB; ``tests/llm_seam/test_excision_identifies.py`` proves
the round trip.

**Shown** (R20, R24, R36, R40): the source text is found by the one walk the
graph offers — origin record ←PRODUCES— reader ←CONSUMES— source instance — and
the prompt words by the edition the record names in the ``prompts`` role. L3's
``predicate.shown_is_what_ran`` judges both (R39). What failed is named and
NOTHING is shown in its place: the words only when the stored edition's digest
matches what ran; the source text, schema, framing and model settings only
when the recomputed key matches, since the key hashes all of them.

**Re-run** (R19, R25, R37, R41, R42): every substitute paired with the reader
that produced the conclusion is dispatched on the inputs that reader consumed,
through a dispatcher with NO model bound — one with a client bound is refused,
so "without the model" is mechanical. L3's ``predicate.rederived_agrees``
judges each value against the model's. No substitute → not yet excisable.
Nothing is written: the calls bypass the grounding executor, a substitute that
declares ``writes`` is not run, and the report is returned, never stored.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from mindsos_capacity.builtins.excision_v0 import (
    DS_REDERIVED_CLAIM,
    DS_REDERIVED_VERDICT,
    DS_SHOWN_CLAIM,
    DS_SHOWN_VERDICT,
    REDERIVED_AGREES_IRI,
    SHOWN_IS_WHAT_RAN_IRI,
)

from mindsos_capacity.builtins.origin_v0 import (
    FIELD_ENVIRONMENT_FAULT,
    FIELD_ORIGIN_METHOD,
    ORIGIN_READ_BY_MODEL,
    origin_record_iri,
)
from mindsos_capacity.identifiers import (
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    PROP_CAPACITY_INSTANCE_TYPE,
    PROP_DATASTATE_INSTANCE_TYPE,
)
from mindsos_knowledge.prompts import PromptEditionNotFoundError, prompt_text

#: The suffix every origin-record DataState carries, taken from the one
#: function that makes it rather than spelled again here.
_ORIGIN_SUFFIX = origin_record_iri("")


@dataclass(frozen=True)
class ModelConclusion:
    """One conclusion the borrowed model produced, as found in a run graph."""

    graph_id: str
    record_node_id: str
    value_datastate: str
    record: Mapping[str, Any]


def _is_model_reading(record: Any) -> bool:
    return (
        isinstance(record, Mapping)
        and record.get(FIELD_ORIGIN_METHOD) == ORIGIN_READ_BY_MODEL
        and record.get(FIELD_ENVIRONMENT_FAULT) is not True
    )


def identify(graphs: Iterable[Any]) -> Tuple[ModelConclusion, ...]:
    """Every model-produced conclusion in ``graphs``, in a stable order."""
    found: List[ModelConclusion] = []
    for graph in graphs:
        for node in graph.nodes.values():
            if node.type_name != NODE_TYPE_DATASTATE_INSTANCE:
                continue
            instance_type = (node.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE)
            if not isinstance(instance_type, str) or not instance_type.endswith(_ORIGIN_SUFFIX):
                continue
            if not _is_model_reading(node.value):
                continue
            found.append(
                ModelConclusion(
                    graph_id=graph.graph_id,
                    record_node_id=node.node_id,
                    value_datastate=instance_type[: -len(_ORIGIN_SUFFIX)],
                    record=node.value,
                )
            )
    return tuple(sorted(found, key=lambda c: (c.graph_id, c.record_node_id)))


#: Named when the L3 check itself did not run — a verdict nobody reached is
#: not a verification.
SHOWN_CHECK_DID_NOT_RUN = "shown_check_did_not_run"

_FRAMING = ("tool_name", "tool_description", "max_tokens")
_MODEL = ("model_id", "model_version", "temperature")


@dataclass(frozen=True)
class ShownReport:
    """What was asked for one conclusion — only what verified (plan R40)."""

    conclusion: ModelConclusion
    verified: bool
    failures: Tuple[str, ...]
    prompt_text: Optional[str]
    source_text: Optional[str]
    extraction_schema: Optional[str]
    framing: Optional[Mapping[str, Any]]
    model: Optional[Mapping[str, Any]]


def _only_one(items: List[Any]) -> Optional[Any]:
    return items[0] if len(items) == 1 else None


def _producer_of(graph: Any, conclusion: ModelConclusion) -> Optional[Any]:
    """The one CapacityInstance that produced the conclusion's origin record."""
    return _only_one([
        e.source for e in graph.edges.values()
        if e.type_name == EDGE_PRODUCES
        and e.target.node_id == conclusion.record_node_id
        and e.source.type_name == NODE_TYPE_CAPACITY_INSTANCE
    ])


def _consumed(graph: Any, producer: Any, datastate: Any) -> Optional[Any]:
    """The one instance of ``datastate`` that ``producer`` consumed."""
    return _only_one([
        e.source for e in graph.edges.values()
        if e.type_name == EDGE_CONSUMES
        and e.target.node_id == producer.node_id
        and (e.source.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE) == datastate
    ])


def _produced(graph: Any, producer: Any, datastate: Any) -> Optional[Any]:
    """The one instance of ``datastate`` that ``producer`` produced."""
    return _only_one([
        e.target for e in graph.edges.values()
        if e.type_name == EDGE_PRODUCES
        and e.source.node_id == producer.node_id
        and (e.target.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE) == datastate
    ])


def source_text_of(graph: Any, conclusion: ModelConclusion) -> Optional[str]:
    """The text the reader consumed, or ``None`` unless the walk is unambiguous.

    record ←PRODUCES— CapacityInstance ←CONSUMES— source instance of the
    record's ``source_datastate`` (R27; the premise guard is
    ``tests/llm_seam/test_a_reading_reaches_its_source_text.py``).
    """
    producer = _producer_of(graph, conclusion)
    if producer is None:
        return None
    source = _consumed(graph, producer, conclusion.record.get("source_datastate"))
    return None if source is None else source.value


def _edition_text(view: Any, record: Mapping[str, Any]) -> Optional[str]:
    try:
        return prompt_text(
            view,
            prompt_iri=record.get("prompt_iri"),
            prompt_version=record.get("prompt_version"),
        )
    except PromptEditionNotFoundError:
        return None


def show(
    conclusion: ModelConclusion,
    graphs: Iterable[Any],
    *,
    view: Any,
    dispatcher: Any,
) -> ShownReport:
    """Show what was asked for ``conclusion``, verified (R20, R24, R36, R40).

    ``view`` is the L2 view holding the ``prompts`` role; ``dispatcher``
    reaches L3's ``predicate.shown_is_what_ran``
    (``mindsos_capacity.builtins.excision_v0.install_excision_v0``).
    """
    by_id = {g.graph_id: g for g in graphs}
    graph = by_id.get(conclusion.graph_id)
    record = conclusion.record
    source = None if graph is None else source_text_of(graph, conclusion)
    edition = _edition_text(view, record)
    result = dispatcher.dispatch(
        SHOWN_IS_WHAT_RAN_IRI,
        {DS_SHOWN_CLAIM: {"record": dict(record), "source_text": source, "edition_text": edition}},
    )
    if not getattr(result, "success", False):
        return ShownReport(conclusion, False, (SHOWN_CHECK_DID_NOT_RUN,), None, None, None, None, None)
    verdict: Dict[str, Any] = result.outputs[DS_SHOWN_VERDICT]
    key_ok = bool(verdict["key_verified"])
    return ShownReport(
        conclusion=conclusion,
        verified=bool(verdict["verified"]),
        failures=tuple(verdict["failures"]),
        prompt_text=edition if verdict["edition_verified"] else None,
        source_text=source if key_ok else None,
        extraction_schema=record.get("extraction_schema") if key_ok else None,
        framing={k: record.get(k) for k in _FRAMING} if key_ok else None,
        model={k: record.get(k) for k in _MODEL} if key_ok else None,
    )


#: The failures *re-run* can name (plan R41). A failed re-run is never a
#: disagreement: ``agrees`` stays ``None``.
RERUN_NOT_IN_THE_GROUNDING_GRAPH = "conclusion_not_in_the_grounding_graph"
RERUN_SUBSTITUTE_WRITES = "substitute_declares_writes"
RERUN_VALUE_NOT_PRODUCED = "substitute_does_not_produce_the_value"
RERUN_SUBSTITUTE_FAILED = "substitute_did_not_run"
RERUN_CHECK_DID_NOT_RUN = "agreement_check_did_not_run"


class ModelBoundError(RuntimeError):
    """*Re-run* was handed a dispatcher with a model client bound (plan R41)."""


@dataclass(frozen=True)
class SubstituteRun:
    """One substitute's re-derivation. ``agrees`` is ``None`` when it failed."""

    substitute_iri: str
    agrees: Optional[bool]
    value: Any
    failure: Optional[str]


@dataclass(frozen=True)
class RerunReport:
    """One conclusion re-run without the model. ``excisable`` is ``False``
    when no substitute is paired with its reader — not yet excisable (R25)."""

    conclusion: ModelConclusion
    reader_iri: Optional[str]
    excisable: bool
    failure: Optional[str]
    runs: Tuple[SubstituteRun, ...]


def _run_substitute(
    substitute: Any, inputs: Mapping[str, Any], model_value: Any, value_datastate: str, dispatcher: Any
) -> SubstituteRun:
    def failed(reason: str) -> SubstituteRun:
        return SubstituteRun(substitute.iri, None, None, reason)

    if getattr(substitute, "writes", False):
        return failed(RERUN_SUBSTITUTE_WRITES)
    if value_datastate not in substitute.outputs:
        return failed(RERUN_VALUE_NOT_PRODUCED)
    result = dispatcher.dispatch(substitute.iri, inputs)
    if not getattr(result, "success", False) or value_datastate not in result.outputs:
        return failed(RERUN_SUBSTITUTE_FAILED)
    value = result.outputs[value_datastate]
    judged = dispatcher.dispatch(
        REDERIVED_AGREES_IRI,
        {DS_REDERIVED_CLAIM: {"model_value": model_value, "rederived_value": value}},
    )
    if not getattr(judged, "success", False):
        return SubstituteRun(substitute.iri, None, value, RERUN_CHECK_DID_NOT_RUN)
    return SubstituteRun(
        substitute.iri, bool(judged.outputs[DS_REDERIVED_VERDICT]["agrees"]), value, None
    )


def rerun(
    conclusion: ModelConclusion,
    graphs: Iterable[Any],
    *,
    dispatcher: Any,
) -> RerunReport:
    """Re-derive ``conclusion`` without the model (R19, R25, R37, R41, R42).

    ``dispatcher`` must have NO model client bound and reach L3's
    ``predicate.rederived_agrees`` (``install_excision_v0``); its capacity
    layer and session say which substitutes are in scope.
    """
    if dispatcher.llm is not None:
        raise ModelBoundError(
            "re-run needs a dispatcher with no model client bound: a re-run "
            "that could reach the model is not a re-run without it (plan R41)."
        )
    graph = {g.graph_id: g for g in graphs}.get(conclusion.graph_id)
    producer = None if graph is None else _producer_of(graph, conclusion)
    if producer is None:
        return RerunReport(conclusion, None, False, RERUN_NOT_IN_THE_GROUNDING_GRAPH, ())
    reader_iri = (producer.properties or {}).get(PROP_CAPACITY_INSTANCE_TYPE)
    substitutes = dispatcher.capacity_layer.substitutes_for(
        reader_iri, session=dispatcher.session
    )
    if not substitutes:
        return RerunReport(conclusion, reader_iri, False, None, ())
    value_node = _produced(graph, producer, conclusion.value_datastate)
    if value_node is None:
        return RerunReport(conclusion, reader_iri, True, RERUN_NOT_IN_THE_GROUNDING_GRAPH, ())
    runs: List[SubstituteRun] = []
    for substitute in substitutes:
        consumed = {ds: _consumed(graph, producer, ds) for ds in substitute.inputs}
        if any(node is None for node in consumed.values()):
            return RerunReport(conclusion, reader_iri, True, RERUN_NOT_IN_THE_GROUNDING_GRAPH, ())
        runs.append(
            _run_substitute(
                substitute,
                {ds: node.value for ds, node in consumed.items()},
                value_node.value,
                conclusion.value_datastate,
                dispatcher,
            )
        )
    return RerunReport(conclusion, reader_iri, True, None, tuple(runs))


__all__ = [
    "ModelBoundError",
    "ModelConclusion",
    "RERUN_CHECK_DID_NOT_RUN",
    "RERUN_NOT_IN_THE_GROUNDING_GRAPH",
    "RERUN_SUBSTITUTE_FAILED",
    "RERUN_SUBSTITUTE_WRITES",
    "RERUN_VALUE_NOT_PRODUCED",
    "RerunReport",
    "ShownReport",
    "SHOWN_CHECK_DID_NOT_RUN",
    "SubstituteRun",
    "identify",
    "rerun",
    "show",
    "source_text_of",
]
