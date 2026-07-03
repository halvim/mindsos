"""S3 — arc-solver worked example, end-to-end (ADR-0195 + ADR-0196).

The integration test: a **Local** arc-like consumer (mOS-AS) adopts the seam
for interpretation only. Demonstrates:

* cold-start ``"solve task 8"`` → ``NeedsInput`` (caller-controlled trigger:
  the arc-Local "ordering-established" marker is absent);
* stateless re-submit of the confirmed canonical request
  ``"solve task 05f2a901"`` → ``InterpretationResult{resolved: 05f2a901}``
  (the reference is already canonical → 0-step resolve, pass-through);
* once the arc-Local marker is set, an index request resolves silently
  (trigger is arc-Local policy, never core-hardcoded).

All arc bodies + DataStates + the task-pattern live in the consumer's **Local**
scope (task-patterns is dual-scope per ADR-0150 §am-8; Local capacities
reference the Global ``phase1.*`` DataStates via the ADR-0185 A2′ mirror).
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
from mindsos_intelligence import (
    InterpretationResult,
    L4Dispatcher,
    Phase1Profile,
    interpret,
)
from mindsos_intelligence.phase_1 import HINT_REFERENCE, HINT_REFERENCE_KIND

# arc-Local vocabulary.
ARC_INDEX_DS = datastate_iri("arc.index_ref")
ARC_CANON_DS = datastate_iri("arc.canonical_ref")
ARC_PATTERN = "task-pattern:arc:solve"
HINT_IRI = capacity_iri(CATEGORY_HINT, "arc")
MAP_IRI = capacity_iri(CATEGORY_DECISION, "arc_map")
RESOLVE_IRI = capacity_iri(CATEGORY_DECISION, "arc_resolve")

# arc-Local enumeration convention (train-split, 1-based) — authored Local data.
_ENUM = {8: "05f2a901", 9: "1b2c3d4e"}
_CANONICAL = set(_ENUM.values())


class _Session:
    def __init__(self, user_id="arc"):
        self.session_id = "s-arc"
        self.user_id = user_id
        self.capabilities = set()

    def has(self, cap):
        return cap in self.capabilities


def _ds(name):
    return DataState(name=name, shape=ShapeDescriptor.opaque(name))


def _hint_impl(**kw):
    """Parse ``solve task <ref>``: a bare int is an index reference; an
    already-canonical id maps to the canonical DataState (0-step resolve)."""
    text = kw[DS_STRUCTURED_INPUT]
    token = str(text).split()[-1]
    if token.isdigit():
        return {DS_HINT_SET: {HINT_REFERENCE_KIND: ARC_INDEX_DS, HINT_REFERENCE: int(token)}}
    return {DS_HINT_SET: {HINT_REFERENCE_KIND: ARC_CANON_DS, HINT_REFERENCE: token}}


def _build_arc(marker: set):
    """Local arc consumer. ``marker`` = the arc-Local 'ordering-established'
    flag; the resolve body asks only while it is empty (arc-Local policy)."""
    cl = CapacityLayer()
    install_phase1_v0(cl)  # Global v0 process/derive_goal defaults
    kl = KnowledgeLayer.bootstrap()
    session = _Session()

    # Local DataStates + arc bodies.
    cl.register_datastate(_ds("arc.index_ref"), session=session, allow_new_realm=True)
    cl.register_datastate(_ds("arc.canonical_ref"), session=session, allow_new_realm=True)

    cl.register_capacity(
        Capacity(
            name="arc", category=CATEGORY_HINT,
            inputs=(DS_STRUCTURED_INPUT,), outputs=(DS_HINT_SET,),
            implementation=_hint_impl,
        ),
        session=session,
    )
    cl.register_capacity(
        Capacity(
            name="arc_map", category=CATEGORY_DECISION,
            inputs=(DS_STRUCTURED_INPUT, DS_HINT_SET, DS_GOAL), outputs=(DS_MAPPING,),
            implementation=lambda **kw: {
                DS_MAPPING: {"task_pattern_iri": ARC_PATTERN, "mapping_confidence": 1.0}
            },
        ),
        session=session,
    )

    def _resolve_impl(**kw):
        idx = kw[ARC_INDEX_DS]
        canonical = _ENUM[idx]
        if marker:  # ordering established → resolve silently (arc-Local policy)
            return {ARC_CANON_DS: canonical}
        return NeedsInput(
            question=f"Read #{idx} as {canonical}?",
            missing=ARC_CANON_DS,
            choices={"yes": {"text": f"solve task {canonical}"}},
        )

    cl.register_capacity(
        Capacity(
            name="arc_resolve", category=CATEGORY_DECISION,
            inputs=(ARC_INDEX_DS,), outputs=(ARC_CANON_DS,),
            implementation=_resolve_impl,
        ),
        session=session,
    )

    # arc's Local task-pattern (map target; resolves Local per ADR-0150 §am-8).
    tp = next(
        g for g in kl.local_metagraph("arc").graphs.values()
        if g.role == ROLE_TASK_PATTERNS
    )
    tp.add_node(value=ARC_PATTERN, type_name="TaskPattern", node_id=ARC_PATTERN)

    profile = Phase1Profile(
        hint=HINT_IRI, map=MAP_IRI, resolve_target_datastate=ARC_CANON_DS
    )
    dispatcher = L4Dispatcher(cl, session=session, kl=kl, phase1_profile=profile)
    return dispatcher


def test_cold_start_asks_then_resubmit_resolves() -> None:
    marker: set = set()
    disp = _build_arc(marker)

    # Turn 1 — cold start: interpret asks (marker absent).
    r1 = interpret(disp, "solve task 8")
    assert isinstance(r1, NeedsInput)
    assert r1.missing == ARC_CANON_DS
    resubmit = r1.choices["yes"]["text"]
    assert resubmit == "solve task 05f2a901"

    # Turn 2 — stateless re-submit of the canonical request: the reference is
    # already canonical → 0-step resolve → InterpretationResult.
    r2 = interpret(disp, resubmit)
    assert isinstance(r2, InterpretationResult)
    assert r2.task_pattern_iri == ARC_PATTERN
    assert r2.resolved_reference == "05f2a901"


def test_marker_set_resolves_index_silently() -> None:
    """Caller-controlled trigger: once the arc-Local marker is set, an index
    request resolves without asking (core never hardcodes the trigger)."""
    marker = {"ordering-established"}
    disp = _build_arc(marker)

    r = interpret(disp, "solve task 9")
    assert isinstance(r, InterpretationResult)
    assert r.resolved_reference == "1b2c3d4e"


def test_arc_pattern_is_local_only() -> None:
    """The map target lives in the consumer's Local task-patterns, not Global."""
    disp = _build_arc(set())
    kl = disp.kl
    assert kl.local_view("arc").get_node(ROLE_TASK_PATTERNS, ARC_PATTERN) is not None
    assert kl.global_view().get_node(ROLE_TASK_PATTERNS, ARC_PATTERN) is None
