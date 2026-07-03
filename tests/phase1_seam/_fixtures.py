"""Shared phase1-seam fixtures — a Global-scope arc-like interpretation
consumer (v0 process/derive_goal + real hint/map/resolve bodies).

Registered Global (``session=None``) for test simplicity, so dispatchers
use ``session=None`` (``find_pipeline`` resolves the Global view). The real
Local arc flow is exercised by the S3 integration test.
"""

from __future__ import annotations

from mindsos_capacity import Capacity, CapacityLayer, DataState, ShapeDescriptor
from mindsos_capacity.builtins.phase1_v0 import (
    DS_GOAL,
    DS_HINT_SET,
    DS_MAPPING,
    DS_STRUCTURED_INPUT,
    install_phase1_v0,
)
from mindsos_capacity.identifiers import (
    CATEGORY_DECISION,
    CATEGORY_HINT,
    capacity_iri,
    datastate_iri,
)
from mindsos_capacity.needs_input import NeedsInput

from mindsos_knowledge import KnowledgeLayer, ROLE_TASK_PATTERNS
from mindsos_intelligence import L4Dispatcher, Phase1Profile
from mindsos_intelligence.phase_1 import HINT_REFERENCE, HINT_REFERENCE_KIND

ARC_INDEX_DS = datastate_iri("arc.index_ref")
ARC_CANON_DS = datastate_iri("arc.canonical_ref")
ARC_PATTERN = "task-pattern:arc:solve"

HINT_IRI = capacity_iri(CATEGORY_HINT, "arc")
MAP_IRI = capacity_iri(CATEGORY_DECISION, "arc_map")


def _ds(name: str) -> DataState:
    return DataState(name=name, shape=ShapeDescriptor.opaque(name))


def _default_resolve(**kw):
    return {ARC_CANON_DS: f"id{kw[ARC_INDEX_DS]}"}


def build_consumer(*, resolve_impl=None, write_pattern: bool = True):
    """Return ``(cl, kl, profile)`` for a Global-scope arc-like consumer.

    ``resolve_impl`` overrides the resolve body (e.g. to return a
    :class:`NeedsInput`); default maps ``int 8 -> "id8"``.
    """
    cl = CapacityLayer()
    install_phase1_v0(cl)
    cl.register_datastate(_ds("arc.index_ref"), allow_new_realm=True)
    cl.register_datastate(_ds("arc.canonical_ref"), allow_new_realm=True)

    cl.register_capacity(
        Capacity(
            name="arc",
            category=CATEGORY_HINT,
            inputs=(DS_STRUCTURED_INPUT,),
            outputs=(DS_HINT_SET,),
            implementation=lambda **kw: {
                DS_HINT_SET: {HINT_REFERENCE_KIND: ARC_INDEX_DS, HINT_REFERENCE: 8}
            },
        )
    )
    cl.register_capacity(
        Capacity(
            name="arc_map",
            category=CATEGORY_DECISION,
            inputs=(DS_STRUCTURED_INPUT, DS_HINT_SET, DS_GOAL),
            outputs=(DS_MAPPING,),
            implementation=lambda **kw: {
                DS_MAPPING: {"task_pattern_iri": ARC_PATTERN, "mapping_confidence": 1.0}
            },
        )
    )
    cl.register_capacity(
        Capacity(
            name="arc_resolve",
            category=CATEGORY_DECISION,
            inputs=(ARC_INDEX_DS,),
            outputs=(ARC_CANON_DS,),
            implementation=resolve_impl or _default_resolve,
        )
    )

    kl = KnowledgeLayer.bootstrap()
    if write_pattern:
        g = next(
            gr for gr in kl.global_metagraph().graphs.values()
            if gr.role == ROLE_TASK_PATTERNS
        )
        g.add_node(value=ARC_PATTERN, type_name="TaskPattern", node_id=ARC_PATTERN)

    profile = Phase1Profile(
        hint=HINT_IRI, map=MAP_IRI, resolve_target_datastate=ARC_CANON_DS
    )
    return cl, kl, profile


def dispatcher_for(cl, kl, profile):
    return L4Dispatcher(cl, session=None, kl=kl, phase1_profile=profile)


def cold_start_resolve(question="Read 8 as id8?"):
    """A resolve body that always asks (test stand-in for arc cold-start)."""

    def _impl(**kw):
        return NeedsInput(
            question=question,
            missing=ARC_CANON_DS,
            choices={"yes": {"text": "solve task id8"}},
        )

    return _impl
