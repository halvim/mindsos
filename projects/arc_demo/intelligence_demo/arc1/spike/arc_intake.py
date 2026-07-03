"""arc-solver INTAKE — the real "ask" front end (ADR-0195 seam + ADR-0196 needs_input).

A user asks ``"solve task <ref>"`` (``<ref>`` = a canonical 8-char ARC id OR a
1-based sorted-train index). This module supplies arc's Local Phase-1 bodies so
the shipped ``interpret()`` turns that request into an ``InterpretationResult``:

    hint (parse) -> map (-> arc-solve task-pattern) -> resolve (index -> id8)

``resolve`` is composed by ``find_pipeline`` from the hint's ``reference_kind``
(the input DataState type) to ``resolve_target_datastate``: an index request
runs ``[resolve -> solve]``; an already-canonical id is a 0-step passthrough.

Cold-start policy (arc-Local, caller-controlled — core never hardcodes it): while
the Local "ordering-established" marker is absent, an index request returns a
``NeedsInput`` clarification (propose the id8, user confirms, re-submits the
canonical request). Once the marker is set, an index resolves silently.

All arc bodies + DataStates + the task-pattern live in the consumer's LOCAL scope
(task-patterns is dual-scope, ADR-0150 §am-8). Interpretation-only: the seam stops
at ``resolved_reference`` (id8), which feeds the existing bespoke solver
(``arc_l4.solve_through_layer``) — no core TaskRun/Episode chain (ADR-0195).
"""

from __future__ import annotations

from typing import Any, Optional

from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.builtins.phase1_v0 import (
    DS_GOAL,
    DS_HINT_SET,
    DS_MAPPING,
    DS_STRUCTURED_INPUT,
)
from mindsos_capacity.identifiers import (
    CATEGORY_DECISION,
    CATEGORY_HINT,
    capacity_iri,
    datastate_iri,
)
from mindsos_capacity.needs_input import NeedsInput
from mindsos_knowledge import ROLE_TASK_PATTERNS
from mindsos_intelligence import L4Dispatcher, Phase1Profile, interpret
from mindsos_intelligence.phase_1 import HINT_REFERENCE, HINT_REFERENCE_KIND

from . import arc_grids
from . import arc_l4

# ── arc-Local intake vocabulary ────────────────────────────────────────
ARC_INDEX_DS = datastate_iri("arc.index_ref")       # a 1-based sorted-train index
ARC_CANON_DS = datastate_iri("arc.canonical_ref")   # a canonical 8-char ARC id
ARC_PATTERN = "task-pattern:arc:solve"
HINT_IRI = capacity_iri(CATEGORY_HINT, "arc")
MAP_IRI = capacity_iri(CATEGORY_DECISION, "arc_map")
RESOLVE_IRI = capacity_iri(CATEGORY_DECISION, "arc_resolve")

_MARKER = "ordering-established"


def _ds(name: str) -> DataState:
    return DataState(name=name, shape=ShapeDescriptor.opaque(name))


def canonical_for_index(dataset: dict, idx: int) -> str:
    """Pinned enumeration: canonical ARC order = task ids sorted ascending,
    1-based (matches ``run_spike``/``arc_viewer.html``; #8 == 05f2a901)."""
    return sorted(dataset["train"])[idx - 1]


def _hint_impl(**kw: Any) -> dict:
    """Parse ``solve task <ref>``. A short all-digit token is a sorted-train
    INDEX; anything else (an 8-char id) is already CANONICAL (0-step resolve).
    Length guard so an all-digit 8-char id is not misread as an index."""
    token = str(kw[DS_STRUCTURED_INPUT]).split()[-1]
    if token.isdigit() and len(token) < 8:
        return {DS_HINT_SET: {HINT_REFERENCE_KIND: ARC_INDEX_DS,
                              HINT_REFERENCE: int(token)}}
    return {DS_HINT_SET: {HINT_REFERENCE_KIND: ARC_CANON_DS,
                          HINT_REFERENCE: token}}


def _map_impl(**kw: Any) -> dict:
    # Single-target consumer: every "solve" request maps to the arc-solve pattern.
    return {DS_MAPPING: {"task_pattern_iri": ARC_PATTERN, "mapping_confidence": 1.0}}


def build_intake(dataset: dict, *, ordering_established: bool = False):
    """Stand up a Local arc instance (the proven ``build_instance`` recipe) with
    the intake bodies + task-pattern registered on top, and a Phase1Profile-bound
    dispatcher. ``ordering_established`` seeds the arc-Local cold-start marker.

    Returns the ``build_instance`` namespace with ``.dispatcher`` rebound to carry
    the Phase1Profile (so ``interpret`` + ``solve_through_layer`` share one layer).
    """
    inst = arc_l4.build_instance(arc_local=True)
    cl, kl, session = inst.layer, inst.kl, inst.session
    marker = {_MARKER} if ordering_established else set()

    cl.register_datastate(_ds("arc.index_ref"), session=session, allow_new_realm=True)
    cl.register_datastate(_ds("arc.canonical_ref"), session=session, allow_new_realm=True)

    cl.register_capacity(
        Capacity(name="arc", category=CATEGORY_HINT,
                 inputs=(DS_STRUCTURED_INPUT,), outputs=(DS_HINT_SET,),
                 implementation=_hint_impl),
        session=session,
    )
    cl.register_capacity(
        Capacity(name="arc_map", category=CATEGORY_DECISION,
                 inputs=(DS_STRUCTURED_INPUT, DS_HINT_SET, DS_GOAL), outputs=(DS_MAPPING,),
                 implementation=_map_impl),
        session=session,
    )

    def _resolve_impl(**kw: Any):
        idx = kw[ARC_INDEX_DS]
        canonical = canonical_for_index(dataset, idx)
        if marker:                      # ordering established -> resolve silently
            return {ARC_CANON_DS: canonical}
        return NeedsInput(              # cold start -> ask (arc-Local policy)
            question=f"Read task {idx} as {canonical}?",
            missing=ARC_CANON_DS,
            choices={"yes": {"text": f"solve task {canonical}"}},
        )

    cl.register_capacity(
        Capacity(name="arc_resolve", category=CATEGORY_DECISION,
                 inputs=(ARC_INDEX_DS,), outputs=(ARC_CANON_DS,),
                 implementation=_resolve_impl),
        session=session,
    )

    # arc's Local task-pattern (map target; resolves Local per ADR-0150 §am-8).
    tp = next(g for g in kl.local_metagraph(inst.user).graphs.values()
              if g.role == ROLE_TASK_PATTERNS)
    if ARC_PATTERN not in tp.nodes:
        tp.add_node(value=ARC_PATTERN, type_name="TaskPattern", node_id=ARC_PATTERN)

    profile = Phase1Profile(hint=HINT_IRI, map=MAP_IRI,
                            resolve_target_datastate=ARC_CANON_DS)
    inst.dispatcher = L4Dispatcher(cl, session=session, kl=kl, phase1_profile=profile)
    return inst


def solve_task(inst, request: str, dataset: dict):
    """The front door. Interpret ``request`` ("solve task <ref>"); on cold-start
    index it returns a ``NeedsInput`` for the caller to surface + re-submit.
    Otherwise feed the resolved id8 into the bespoke solver.

    Returns ``NeedsInput`` OR the ``solve_through_layer`` result (dispatched answer,
    inline answer)."""
    r = interpret(inst.dispatcher, request)
    if isinstance(r, NeedsInput):
        return r
    return arc_l4.solve_through_layer(inst.dispatcher, r.resolved_reference, dataset)
