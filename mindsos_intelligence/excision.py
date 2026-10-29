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

**Re-run** (R19, R25, R37, R41, R42, R44, R45): every substitute paired with
the reader that produced the conclusion is dispatched on the inputs that
reader consumed — MINUS any the reader declares as carrying the model's
answer, which a substitute never declares (R44) — through a dispatcher with
NO model bound: one with a client bound is refused, so "without the model" is
mechanical. The pairing is checked again here, against the reader as declared
in the dispatcher's scope, and a substitute that no longer pairs is named and
not run (R45). ⚠ ``rerun`` alone does not check where a substitute's OTHER
inputs came from — one that is itself a model-read value is handed over as it
stands; :func:`prove` does (plan I-21). L3's
``predicate.rederived_agrees``
judges each value against the model's. No substitute → not yet excisable.
Nothing is written: the calls bypass the grounding executor, a substitute that
declares ``writes`` is not run, and the report is returned, never stored.

**The walk** (plan I-21 gate 2; R49, R50, R52, R62): :func:`walk` lists every
value of an Episode whose lineage holds a model value — a reading, a value a
producer declaring ``consults_llm`` made, a value a reader took as its declared
answer, an ``interpreted`` start whose interpretation used the model — and
every value whose lineage is not recorded, across run graphs by the
manifest's ``start_origins``.

**The proof** (plan I-21 gate 3; R47, R53, R55–R61): :func:`prove` reports a
value proven model-free only when every model value it descends from, through
a substitute's inputs, re-derives through its own substitute from proven
inputs with exact agreement; it names every reason it is not, and what it
relied on — the starts taken as premises and the stored roles read.
:func:`proven_walk` is the walk with each value's proof (R49).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from mindsos_capacity.admission import substitute_problems
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
    DECLARED_CONSULTS_LLM,
    DECLARED_MODEL_ANSWER_INPUTS,
    DECLARED_READS_MM,
    DECLARED_READS_ROLES,
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    MANIFEST_CAPACITY_DECLARATIONS,
    MANIFEST_START_ORIGINS,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    NODE_TYPE_RUN_MANIFEST,
    PROP_CAPACITY_INSTANCE_TYPE,
    PROP_DATASTATE_INSTANCE_TYPE,
    START_ORIGIN_GIVEN,
    START_ORIGIN_INTERPRETED,
    START_ORIGIN_PRODUCED,
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
#: The pairing held at registration and no longer does (plan R45): the reader
#: was re-declared since, or a Local reader shadows the one it was paired with.
RERUN_SUBSTITUTE_NO_LONGER_PAIRS = "substitute_no_longer_pairs"
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
    """Re-derive ``conclusion`` without the model (R19, R25, R37, R41–R45).

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
    # Plan R45 — the pairing is checked AGAIN, against the reader as declared
    # in this dispatcher's scope. Registration checked it once; an upsert of
    # the reader, or a Local reader shadowing it, can have changed which
    # inputs carry the model's answer since. A substitute is in scope only
    # where its reader is, and nothing unregisters a capacity, so the reader
    # resolves.
    reader = dispatcher.capacity_layer.resolve_declaration(reader_iri, session=dispatcher.session)
    runs: List[SubstituteRun] = []
    for substitute in substitutes:
        if substitute_problems(substitute, reader):
            runs.append(
                SubstituteRun(substitute.iri, None, None, RERUN_SUBSTITUTE_NO_LONGER_PAIRS)
            )
            continue
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


# ── the walk — what leaned on the model (plan I-21 gate 2; R49, R50, R52, R62) ──
#
# ``identify`` lists readings. A value a plain capacity computed FROM a reading
# leaned on the borrowed model too (§1), and nothing identified it. The walk
# lists every value whose lineage holds a model value, and every value whose
# lineage is NOT RECORDED — an unlisted value must mean *no model in its
# lineage*, never *we could not tell* (R62). The lineage is CONSUMES/PRODUCES
# inside a run graph and the manifest's ``start_origins`` between run graphs
# (ADR-0201 amendment 8). Declarations are read from each run's own snapshot,
# never today's registry (R52). Nodes only, so a stored Episode walks the same.
# Proof status is not here: whether a listed value is proven is gate 3's.

#: How a value is the model's (R52, R51).
WALK_READ_BY_MODEL = "read_by_model"
WALK_CONSULTS_LLM = "consults_llm"
WALK_ANSWER_INPUT = "answer_input"
WALK_INTERPRETED = "interpreted"

#: Why a value's lineage is not recorded.
GAP_ORIGINS_NOT_RECORDED = "origins_not_recorded"
GAP_ORIGIN_UNRECORDED = "origin_unrecorded"
GAP_NOT_IN_THE_EPISODE = "origin_not_in_the_episode"
GAP_DECLARATIONS_NOT_RECORDED = "declarations_not_recorded"


@dataclass(frozen=True)
class ValueRef:
    """One ``DataStateInstance``: the run graph it is in, and its node id."""

    graph_id: str
    instance_id: str


@dataclass(frozen=True)
class ModelValue:
    """A value in a lineage that is the model's, and how (R52)."""

    value: ValueRef
    datastate: str
    hows: Tuple[str, ...]


@dataclass(frozen=True)
class LineageGap:
    """A value in a lineage whose provenance is not recorded, and why."""

    value: ValueRef
    datastate: str
    kind: str


@dataclass(frozen=True)
class Leaned:
    """One listed value: the model values and the gaps in its lineage."""

    value: ValueRef
    datastate: str
    model_values: Tuple[ModelValue, ...]
    gaps: Tuple[LineageGap, ...]


class _RunIndex:
    """One run graph, indexed for the walk."""

    def __init__(self, graph: Any) -> None:
        self.graph_id = graph.graph_id
        self.nodes = graph.nodes
        manifests = [n.value for n in graph.nodes.values() if n.type_name == NODE_TYPE_RUN_MANIFEST]
        self.manifest: Optional[Mapping[str, Any]] = (
            manifests[0] if len(manifests) == 1 and isinstance(manifests[0], Mapping) else None
        )
        self.producer: Dict[str, Any] = {}
        self.produced: Dict[str, List[Any]] = {}
        self.consumed: Dict[str, List[Any]] = {}
        self.consumers: Dict[str, List[Any]] = {}
        for e in graph.edges.values():
            if e.type_name == EDGE_PRODUCES and e.source.type_name == NODE_TYPE_CAPACITY_INSTANCE:
                self.producer[e.target.node_id] = e.source
                self.produced.setdefault(e.source.node_id, []).append(e.target)
            elif e.type_name == EDGE_CONSUMES and e.target.type_name == NODE_TYPE_CAPACITY_INSTANCE:
                self.consumed.setdefault(e.target.node_id, []).append(e.source)
                self.consumers.setdefault(e.source.node_id, []).append(e.target)

    def declaration(self, capacity_node: Any) -> Optional[Mapping[str, Any]]:
        """The capacity's entry as the run snapshotted it, or ``None``: not recorded."""
        if self.manifest is None:
            return None
        snapshot = self.manifest.get(MANIFEST_CAPACITY_DECLARATIONS)
        if not isinstance(snapshot, Mapping):
            return None
        entry = snapshot.get((capacity_node.properties or {}).get(PROP_CAPACITY_INSTANCE_TYPE))
        return entry if isinstance(entry, Mapping) else None


def _datastate_of(node: Any) -> Optional[str]:
    return (node.properties or {}).get(PROP_DATASTATE_INSTANCE_TYPE)


def _is_value(node: Any) -> bool:
    ds = _datastate_of(node) if node.type_name == NODE_TYPE_DATASTATE_INSTANCE else None
    return isinstance(ds, str) and not ds.endswith(_ORIGIN_SUFFIX)


def _own(runs: Mapping[str, _RunIndex], run: _RunIndex, node: Any):
    """A value's own marks (R52), gaps, lineage parents, and the value it is a
    copy of, if any — what the walk knows about it before following anything."""
    ds = _datastate_of(node)
    hows: List[str] = []
    gaps: List[str] = []
    parents: List[ValueRef] = []
    copy_of: Optional[ValueRef] = None
    producer = run.producer.get(node.node_id)
    if producer is not None:
        entry = run.declaration(producer)
        if entry is None or DECLARED_CONSULTS_LLM not in entry:
            gaps.append(GAP_DECLARATIONS_NOT_RECORDED)
        elif entry[DECLARED_CONSULTS_LLM]:
            hows.append(WALK_CONSULTS_LLM)
        for sibling in run.produced.get(producer.node_id, ()):
            if _datastate_of(sibling) == origin_record_iri(ds) and _is_model_reading(sibling.value):
                hows.append(WALK_READ_BY_MODEL)
        parents = [ValueRef(run.graph_id, n.node_id) for n in run.consumed.get(producer.node_id, ())]
    else:
        origins = None if run.manifest is None else run.manifest.get(MANIFEST_START_ORIGINS)
        origin = origins.get(ds) if isinstance(origins, Mapping) else None
        kind = origin.get("kind") if isinstance(origin, Mapping) else None
        if not isinstance(origins, Mapping):
            gaps.append(GAP_ORIGINS_NOT_RECORDED)
        elif kind == START_ORIGIN_GIVEN:
            pass
        elif kind == START_ORIGIN_INTERPRETED:
            used = origin.get("model_capacities")
            if used is None:
                gaps.append(GAP_DECLARATIONS_NOT_RECORDED)
            elif used:
                hows.append(WALK_INTERPRETED)
        elif kind == START_ORIGIN_PRODUCED and origin.get("by"):
            for by in origin["by"]:
                ref = ValueRef(by.get("graph_id"), by.get("instance_id"))
                there = runs.get(ref.graph_id)
                if there is None or ref.instance_id not in there.nodes:
                    gaps.append(GAP_NOT_IN_THE_EPISODE)
                else:
                    parents.append(ref)
            # A copy carried into this run is the SAME value as the one that
            # produced it: same DataState, one producing instance. An element
            # of a collection (another DataState) or an assembled list is not.
            if len(parents) == 1 and len(origin["by"]) == 1:
                source = runs[parents[0].graph_id].nodes[parents[0].instance_id]
                if _datastate_of(source) == ds:
                    copy_of = parents[0]
        else:
            gaps.append(GAP_ORIGIN_UNRECORDED)
    for consumer in run.consumers.get(node.node_id, ()):
        entry = run.declaration(consumer)
        if entry is None or DECLARED_MODEL_ANSWER_INPUTS not in entry:
            gaps.append(GAP_DECLARATIONS_NOT_RECORDED)
        elif ds in (entry[DECLARED_MODEL_ANSWER_INPUTS] or ()):
            hows.append(WALK_ANSWER_INPUT)
    return tuple(sorted(set(hows))), tuple(sorted(set(gaps))), tuple(parents), copy_of


class _Lineage:
    """The lineage facts of one Episode, computed once: each value's own marks,
    gaps and parents (:func:`_own`), and which values are copies of one another."""

    def __init__(self, graphs: Iterable[Any]) -> None:
        self.runs = {g.graph_id: _RunIndex(g) for g in graphs}
        self.own: Dict[ValueRef, Tuple[str, Tuple[str, ...], Tuple[str, ...], Tuple[ValueRef, ...]]] = {}
        self._alias: Dict[ValueRef, ValueRef] = {}
        for run in self.runs.values():
            for node in run.nodes.values():
                if not _is_value(node):
                    continue
                ref = ValueRef(run.graph_id, node.node_id)
                hows, gaps, parents, copy_of = _own(self.runs, run, node)
                self.own[ref] = (_datastate_of(node), hows, gaps, parents)
                if copy_of is not None:
                    a, b = self.root(ref), self.root(copy_of)
                    if a != b:
                        self._alias[a] = b
        # A mark found on any copy of a value is the value's (R52: "a reader
        # consumed IT as a declared answer input").
        self.marks: Dict[ValueRef, List[ModelValue]] = {}
        for ref, (ds, hows, _gaps, _parents) in self.own.items():
            if hows:
                self.marks.setdefault(self.root(ref), []).append(ModelValue(ref, ds, hows))

    def root(self, ref: ValueRef) -> ValueRef:
        while self._alias.get(ref, ref) != ref:
            ref = self._alias[ref]
        return ref

    def node(self, ref: ValueRef) -> Any:
        return self.runs[ref.graph_id].nodes[ref.instance_id]

    def leaned(self, ref: ValueRef) -> Optional[Leaned]:
        ds = self.own[ref][0]
        seen = {ref}
        stack = [ref]
        model: Dict[ValueRef, ModelValue] = {}
        gaps: Dict[Tuple[ValueRef, str], LineageGap] = {}
        while stack:
            at = stack.pop()
            if at not in self.own:
                continue
            at_ds, _h, at_gaps, at_parents = self.own[at]
            for m in self.marks.get(self.root(at), ()):
                model[m.value] = m
            for kind in at_gaps:
                gaps[(at, kind)] = LineageGap(at, at_ds, kind)
            for parent in at_parents:
                if parent not in seen:
                    seen.add(parent)
                    stack.append(parent)
        if not (model or gaps):
            return None
        return Leaned(
            value=ref,
            datastate=ds,
            model_values=tuple(sorted(model.values(), key=lambda m: (m.value.graph_id, m.value.instance_id))),
            gaps=tuple(sorted(gaps.values(), key=lambda g: (g.value.graph_id, g.value.instance_id, g.kind))),
        )

    def walk(self) -> Tuple[Leaned, ...]:
        listed = [e for e in (self.leaned(ref) for ref in self.own) if e is not None]
        return tuple(sorted(listed, key=lambda e: (e.value.graph_id, e.value.instance_id)))


def walk(graphs: Iterable[Any]) -> Tuple[Leaned, ...]:
    """Every value in ``graphs`` that leaned on the model, or whose lineage is
    not recorded, in a stable order (plan R49, R50, R52, R62).

    ``graphs`` are one Episode's run graphs (``read_episode``'s
    ``capacity_run_graphs``, R27). Origin records are not listed — they are
    the readings ``identify`` lists.
    """
    return _Lineage(graphs).walk()


# ── the proof — a re-run proven model-free, or why not (plan I-21 gate 3) ──
#
# R47: a value is proven model-free when every model value it descends from —
# through a substitute's INPUTS only (R56) — re-derives, through its own
# substitute and from its own proven inputs, with exact agreement (R41), and
# what is computed from those values stands as recorded. Only substitutes run.
# Everything else that could leave it *not proven* is read from the record
# (R58). The report names what it relied on (R61) and is returned, never
# stored (R42).

#: Why a value is not proven (beside the walk's gap kinds, which are reasons
#: too, and the re-run failures a substitute's run can name).
PROOF_NOT_YET_EXCISABLE = "not_yet_excisable"
PROOF_SUBSTITUTE_DISAGREES = "substitute_disagrees"
PROOF_NO_SUBSTITUTE_AGREED = "no_substitute_agreed"
PROOF_INTERPRETED_WITH_THE_MODEL = "interpreted_with_the_model"
PROOF_INTERPRETATION_NOT_RECORDED = "interpretation_declarations_not_recorded"
PROOF_READS_THE_MENTAL_MODEL = "reads_the_mental_model"
PROOF_READS_NOT_RECORDED = "reads_not_recorded"
PROOF_CONSUMED_AN_ORIGIN_RECORD = "consumed_an_origin_record"
PROOF_MODEL_ANSWER_NOT_EXCISABLE = "model_answer_not_excisable"
PROOF_LINEAGE_LOOPS = "lineage_loops"
#: A substitute named and not run at proof (R53, R55, R47).
RERUN_SUBSTITUTE_READS_MM = "substitute_reads_the_mental_model"
RERUN_SUBSTITUTE_TAKES_A_WITHHELD_ANSWER = "substitute_takes_an_answer_the_run_withheld"
RERUN_INPUTS_NOT_PROVEN = "substitute_inputs_not_proven"

_MODEL_MADE = frozenset({WALK_READ_BY_MODEL, WALK_CONSULTS_LLM})


@dataclass(frozen=True)
class NotProven:
    """A value in the lineage that stops the proof, and why."""

    value: ValueRef
    datastate: str
    reason: str


@dataclass(frozen=True)
class Rederivation:
    """One model value re-derived at proof: the reader that made it, each
    substitute's run, and the roles each substitute declares now (R61)."""

    value: ValueRef
    datastate: str
    reader_iri: Optional[str]
    runs: Tuple[SubstituteRun, ...]
    substitute_roles: Tuple[Tuple[str, Tuple[str, ...]], ...]


@dataclass(frozen=True)
class ProofReport:
    """Whether a value is proven model-free (R47), and what it relied on (R61):
    the starts taken as premises and the stored roles read on the way."""

    value: ValueRef
    datastate: str
    proven: bool
    not_proven: Tuple[NotProven, ...]
    rederived: Tuple[Rederivation, ...]
    premises: Tuple[ValueRef, ...]
    roles: Tuple[str, ...]


@dataclass
class _Partial:
    not_proven: Dict[Tuple[ValueRef, str], NotProven] = field(default_factory=dict)
    rederived: Dict[ValueRef, Rederivation] = field(default_factory=dict)
    premises: set = field(default_factory=set)
    roles: set = field(default_factory=set)

    def add(self, other: "_Partial") -> None:
        self.not_proven.update(other.not_proven)
        self.rederived.update(other.rederived)
        self.premises |= other.premises
        self.roles |= other.roles

    def stop(self, ref: ValueRef, ds: str, reason: str) -> None:
        self.not_proven[(ref, reason)] = NotProven(ref, ds, reason)


def _reads(partial: _Partial, ref: ValueRef, ds: str, entry: Mapping[str, Any]) -> None:
    """A step's declared reads, as recorded (R48, R58)."""
    if DECLARED_READS_ROLES not in entry or DECLARED_READS_MM not in entry:
        partial.stop(ref, ds, PROOF_READS_NOT_RECORDED)
        return
    if entry[DECLARED_READS_MM]:
        partial.stop(ref, ds, PROOF_READS_THE_MENTAL_MODEL)
    partial.roles |= set(entry[DECLARED_READS_ROLES] or ())


class _Prover:
    def __init__(self, lineage: _Lineage, dispatcher: Any) -> None:
        self.lineage = lineage
        self.dispatcher = dispatcher
        self.done: Dict[ValueRef, _Partial] = {}
        self.busy: set = set()

    def prove(self, ref: ValueRef) -> _Partial:
        if ref not in self.lineage.own:
            # An origin record a step consumed: not a value, and the step that
            # consumed it is already named for it (R58).
            return _Partial()
        if ref in self.done:
            return self.done[ref]
        ds = self.lineage.own[ref][0]
        if ref in self.busy:
            p = _Partial()
            p.stop(ref, ds, PROOF_LINEAGE_LOOPS)
            return p
        self.busy.add(ref)
        try:
            result = self._prove(ref)
        finally:
            self.busy.discard(ref)
        self.done[ref] = result
        return result

    def _prove(self, ref: ValueRef) -> _Partial:
        lineage = self.lineage
        ds, hows, gaps, parents = lineage.own[ref]
        run = lineage.runs[ref.graph_id]
        node = lineage.node(ref)
        out = _Partial()
        for kind in gaps:
            out.stop(ref, ds, kind)
        producer = run.producer.get(node.node_id)
        if producer is not None and _MODEL_MADE & set(hows):
            out.add(self._rederive(ref, ds, run, producer))
            return out
        marks = {h for m in lineage.marks.get(lineage.root(ref), ()) for h in m.hows}
        if WALK_ANSWER_INPUT in marks:
            leaned = lineage.leaned(ref)
            made = [m for m in (leaned.model_values if leaned else ()) if _MODEL_MADE & set(m.hows)]
            if not made:
                out.stop(ref, ds, PROOF_MODEL_ANSWER_NOT_EXCISABLE)
        if producer is not None:
            entry = run.declaration(producer)
            if entry is not None:
                _reads(out, ref, ds, entry)
            for consumed in run.consumed.get(producer.node_id, ()):
                if (_datastate_of(consumed) or "").endswith(_ORIGIN_SUFFIX):
                    out.stop(ref, ds, PROOF_CONSUMED_AN_ORIGIN_RECORD)
            for parent in parents:
                out.add(self.prove(parent))
            return out
        origins = None if run.manifest is None else run.manifest.get(MANIFEST_START_ORIGINS)
        origin = origins.get(ds) if isinstance(origins, Mapping) else None
        kind = origin.get("kind") if isinstance(origin, Mapping) else None
        if kind == START_ORIGIN_GIVEN:
            out.premises.add(ref)
        elif kind == START_ORIGIN_INTERPRETED:
            if origin.get("model_capacities"):
                out.stop(ref, ds, PROOF_INTERPRETED_WITH_THE_MODEL)
            snapshot = origin.get(MANIFEST_CAPACITY_DECLARATIONS)
            if not isinstance(snapshot, Mapping):
                out.stop(ref, ds, PROOF_INTERPRETATION_NOT_RECORDED)
            else:
                for entry in snapshot.values():
                    _reads(out, ref, ds, entry)
                out.premises.add(ref)
        for parent in parents:
            out.add(self.prove(parent))
        return out

    def _rederive(self, ref: ValueRef, ds: str, run: "_RunIndex", producer: Any) -> _Partial:
        """R47, R53, R55, R57, R59 — the model value re-derives through its
        producer's substitute, from proven inputs, with exact agreement."""
        dispatcher = self.dispatcher
        out = _Partial()
        reader_iri = (producer.properties or {}).get(PROP_CAPACITY_INSTANCE_TYPE)
        substitutes = dispatcher.capacity_layer.substitutes_for(reader_iri, session=dispatcher.session)
        if not substitutes:
            out.stop(ref, ds, PROOF_NOT_YET_EXCISABLE)
            out.rederived[ref] = Rederivation(ref, ds, reader_iri, (), ())
            return out
        reader = dispatcher.capacity_layer.resolve_declaration(reader_iri, session=dispatcher.session)
        entry = run.declaration(producer) or {}
        withheld = set(entry.get(DECLARED_MODEL_ANSWER_INPUTS) or ())
        node = self.lineage.node(ref)
        consumed_by_ds: Dict[str, List[Any]] = {}
        for c in run.consumed.get(producer.node_id, ()):
            consumed_by_ds.setdefault(_datastate_of(c), []).append(c)
        runs: List[SubstituteRun] = []
        roles: List[Tuple[str, Tuple[str, ...]]] = []
        agreed: List[_Partial] = []
        disagreed = False
        blocked: List[_Partial] = []
        for substitute in substitutes:
            def named(reason: str) -> None:
                runs.append(SubstituteRun(substitute.iri, None, None, reason))

            if getattr(substitute, "reads_mm", False):
                named(RERUN_SUBSTITUTE_READS_MM)
                continue
            if substitute_problems(substitute, reader):
                named(RERUN_SUBSTITUTE_NO_LONGER_PAIRS)
                continue
            if withheld & set(substitute.inputs):
                named(RERUN_SUBSTITUTE_TAKES_A_WITHHELD_ANSWER)
                continue
            found = {d: consumed_by_ds.get(d, []) for d in substitute.inputs}
            if any(len(v) != 1 for v in found.values()):
                out.stop(ref, ds, RERUN_NOT_IN_THE_GROUNDING_GRAPH)
                named(RERUN_NOT_IN_THE_GROUNDING_GRAPH)
                continue
            inputs = _Partial()
            for d, (c,) in found.items():
                inputs.add(self.prove(ValueRef(run.graph_id, c.node_id)))
            if inputs.not_proven:
                blocked.append(inputs)
                named(RERUN_INPUTS_NOT_PROVEN)
                continue
            result = _run_substitute(
                substitute, {d: c.value for d, (c,) in found.items()}, node.value, ds, dispatcher
            )
            runs.append(result)
            if result.agrees is True:
                inputs.roles |= set(getattr(substitute, "reads_roles", ()) or ())
                roles.append((substitute.iri, tuple(sorted(getattr(substitute, "reads_roles", ()) or ()))))
                agreed.append(inputs)
            elif result.agrees is False:
                disagreed = True
        if disagreed:
            out.stop(ref, ds, PROOF_SUBSTITUTE_DISAGREES)
        elif not agreed:
            if blocked:
                for b in blocked:
                    out.add(b)
            else:
                out.stop(ref, ds, PROOF_NO_SUBSTITUTE_AGREED)
        else:
            for a in agreed:
                out.add(a)
        out.rederived[ref] = Rederivation(ref, ds, reader_iri, tuple(runs), tuple(roles))
        return out


def _report(ref: ValueRef, ds: str, partial: _Partial) -> ProofReport:
    def by_ref(r: ValueRef) -> Tuple[str, str]:
        return (r.graph_id, r.instance_id)

    return ProofReport(
        value=ref,
        datastate=ds,
        proven=not partial.not_proven,
        not_proven=tuple(sorted(partial.not_proven.values(), key=lambda n: (by_ref(n.value), n.reason))),
        rederived=tuple(partial.rederived[r] for r in sorted(partial.rederived, key=by_ref)),
        premises=tuple(sorted(partial.premises, key=by_ref)),
        roles=tuple(sorted(partial.roles)),
    )


def _check_no_model(dispatcher: Any) -> None:
    if dispatcher.llm is not None:
        raise ModelBoundError(
            "a proof needs a dispatcher with no model client bound: a re-run "
            "that could reach the model is not a re-run without it (plan R41)."
        )


def prove(value: ValueRef, graphs: Iterable[Any], *, dispatcher: Any) -> ProofReport:
    """Whether ``value`` is proven model-free (plan R47, R53, R55–R61).

    ``dispatcher`` must have NO model client bound and reach L3's
    ``predicate.rederived_agrees`` (``install_excision_v0``); its capacity
    layer and session say which substitutes are in scope. Nothing is written.
    """
    _check_no_model(dispatcher)
    lineage = _Lineage(graphs)
    if value not in lineage.own:
        raise KeyError(f"{value!r} is not a value of these run graphs")
    return _report(value, lineage.own[value][0], _Prover(lineage, dispatcher).prove(value))


def proven_walk(graphs: Iterable[Any], *, dispatcher: Any) -> Tuple[Tuple[Leaned, ProofReport], ...]:
    """The walk, each listed value with its proof (plan R49): what leaned on
    the model, and whether it is proven by R47. One prover, so a substitute
    shared by several values is judged once."""
    _check_no_model(dispatcher)
    lineage = _Lineage(graphs)
    prover = _Prover(lineage, dispatcher)
    return tuple(
        (entry, _report(entry.value, entry.datastate, prover.prove(entry.value)))
        for entry in lineage.walk()
    )

__all__ = [
    "NotProven",
    "PROOF_CONSUMED_AN_ORIGIN_RECORD",
    "PROOF_INTERPRETATION_NOT_RECORDED",
    "PROOF_INTERPRETED_WITH_THE_MODEL",
    "PROOF_LINEAGE_LOOPS",
    "PROOF_MODEL_ANSWER_NOT_EXCISABLE",
    "PROOF_NO_SUBSTITUTE_AGREED",
    "PROOF_NOT_YET_EXCISABLE",
    "PROOF_READS_NOT_RECORDED",
    "PROOF_READS_THE_MENTAL_MODEL",
    "PROOF_SUBSTITUTE_DISAGREES",
    "ProofReport",
    "RERUN_INPUTS_NOT_PROVEN",
    "RERUN_SUBSTITUTE_READS_MM",
    "RERUN_SUBSTITUTE_TAKES_A_WITHHELD_ANSWER",
    "Rederivation",
    "prove",
    "proven_walk",
    "GAP_DECLARATIONS_NOT_RECORDED",
    "GAP_NOT_IN_THE_EPISODE",
    "GAP_ORIGIN_UNRECORDED",
    "GAP_ORIGINS_NOT_RECORDED",
    "Leaned",
    "LineageGap",
    "ModelValue",
    "ValueRef",
    "WALK_ANSWER_INPUT",
    "WALK_CONSULTS_LLM",
    "WALK_INTERPRETED",
    "WALK_READ_BY_MODEL",
    "ModelBoundError",
    "ModelConclusion",
    "RERUN_CHECK_DID_NOT_RUN",
    "RERUN_NOT_IN_THE_GROUNDING_GRAPH",
    "RERUN_SUBSTITUTE_FAILED",
    "RERUN_SUBSTITUTE_NO_LONGER_PAIRS",
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
    "walk",
]
