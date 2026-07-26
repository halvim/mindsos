"""S1 — ADR-0195 Phase-1 interpretation seam (non-clarifying).

Exercises the standalone ``interpret`` surface + ``Phase1Profile`` + the
find_pipeline-composed ``resolve`` step, with a real (Global-scope, for
test simplicity) consumer fixture. The full Local arc-solver flow +
``needs_input`` are S3 / ADR-0196.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from mindsos_capacity import (
    Capacity,
    CapacityLayer,
    DataState,
    ShapeDescriptor,
)
from mindsos_capacity.builtins.phase1_v0 import (
    DS_GOAL,
    DS_HINT_SET,
    DS_MAPPING,
    DS_STRUCTURED_INPUT,
    TRIVIAL_REQUEST_PATTERN_IRI,
    install_phase1_v0,
)
from mindsos_capacity.identifiers import (
    CATEGORY_DECISION,
    CATEGORY_HINT,
    capacity_iri,
    datastate_iri,
)

from mindsos_knowledge import KnowledgeLayer, ROLE_REQUEST_PATTERNS

from mindsos_intelligence import (
    InterpretationError,
    L4Dispatcher,
    Phase1Profile,
    interpret,
)
from mindsos_intelligence.phase_1 import HINT_REFERENCE, HINT_REFERENCE_KIND

ARC_INDEX_DS = datastate_iri("arc.index_ref")
ARC_CANON_DS = datastate_iri("arc.canonical_ref")
ARC_PATTERN = "request-pattern:arc:solve"

HINT_IRI = capacity_iri(CATEGORY_HINT, "arc")
MAP_IRI = capacity_iri(CATEGORY_DECISION, "arc_map")
RESOLVE_IRI = capacity_iri(CATEGORY_DECISION, "arc_resolve")


def _ds(name: str) -> DataState:
    return DataState(name=name, shape=ShapeDescriptor.opaque(name))


def _build_consumer(*, write_pattern: bool = True):
    """A Global-scope arc-like consumer: v0 defaults for process/derive_goal,
    real hint/map/resolve bodies, plus (optionally) the Local... here Global
    request-pattern node the map targets."""
    cl = CapacityLayer()
    install_phase1_v0(cl)

    cl.register_datastate(_ds("arc.index_ref"), allow_new_realm=True)
    cl.register_datastate(_ds("arc.canonical_ref"), allow_new_realm=True)

    # hint → {reference_kind: <index DS>, reference: 8}
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
    # map → arc solve pattern, confidence 1.0
    cl.register_capacity(
        Capacity(
            name="arc_map",
            category=CATEGORY_DECISION,
            inputs=(DS_STRUCTURED_INPUT, DS_HINT_SET, DS_GOAL),
            outputs=(DS_MAPPING,),
            implementation=lambda **kw: {
                DS_MAPPING: {
                    "request_pattern_iri": ARC_PATTERN,
                    "mapping_confidence": 1.0,
                }
            },
        )
    )
    # resolve: index → canonical (int 8 → "id8")
    cl.register_capacity(
        Capacity(
            name="arc_resolve",
            category=CATEGORY_DECISION,
            inputs=(ARC_INDEX_DS,),
            outputs=(ARC_CANON_DS,),
            implementation=lambda **kw: {ARC_CANON_DS: f"id{kw[ARC_INDEX_DS]}"},
        )
    )

    kl = KnowledgeLayer.bootstrap()
    if write_pattern:
        tp_graph = next(
            g for g in kl.global_metagraph().graphs.values()
            if g.role == ROLE_REQUEST_PATTERNS
        )
        tp_graph.add_node(
            value=ARC_PATTERN, type_name="RequestPattern", node_id=ARC_PATTERN
        )
    return cl, kl


def _dispatcher(cl, kl, profile):
    return L4Dispatcher(cl, session=None, kl=kl, phase1_profile=profile)


# ── tests ──────────────────────────────────────────────────────────────


def test_v0_no_profile_returns_trivial_and_no_resolution() -> None:
    """All-v0 (no profile) path is unchanged: trivial pattern, no resolve,
    no KL check (so no pattern need exist)."""
    cl = CapacityLayer()
    install_phase1_v0(cl)
    disp = L4Dispatcher(cl)  # no profile, no kl
    r = interpret(disp, "anything")
    assert r.request_pattern_iri == TRIVIAL_REQUEST_PATTERN_IRI
    assert r.mapping_confidence == 1.0
    assert r.resolved_reference is None


def test_real_consumer_composes_and_resolves() -> None:
    """hint→map→[resolve] via find_pipeline+pipeline_execution → id8."""
    cl, kl = _build_consumer()
    profile = Phase1Profile(
        hint=HINT_IRI, map=MAP_IRI, resolve_target_datastate=ARC_CANON_DS
    )
    r = interpret(_dispatcher(cl, kl, profile), "solve task 8")
    assert r.request_pattern_iri == ARC_PATTERN
    assert r.mapping_confidence == 1.0
    assert r.resolved_reference == "id8"


def test_reference_already_canonical_passthrough() -> None:
    """When reference_kind == resolve target, no find_pipeline is composed —
    the reference passes through (post-confirm canonical case)."""
    cl, kl = _build_consumer()
    # Target == the reference's own type → 0-step / pass-through.
    profile = Phase1Profile(
        hint=HINT_IRI, map=MAP_IRI, resolve_target_datastate=ARC_INDEX_DS
    )
    r = interpret(_dispatcher(cl, kl, profile), "solve task 8")
    assert r.resolved_reference == 8


def test_no_resolve_target_returns_mapping_only() -> None:
    """A real map without a resolve target returns the mapping, no reference."""
    cl, kl = _build_consumer()
    profile = Phase1Profile(hint=HINT_IRI, map=MAP_IRI)
    r = interpret(_dispatcher(cl, kl, profile), "solve task 8")
    assert r.request_pattern_iri == ARC_PATTERN
    assert r.resolved_reference is None


def test_unresolvable_map_target_raises() -> None:
    """map target absent from request-patterns → InterpretationError."""
    cl, kl = _build_consumer(write_pattern=False)
    profile = Phase1Profile(hint=HINT_IRI, map=MAP_IRI)
    with pytest.raises(InterpretationError, match="does not resolve"):
        interpret(_dispatcher(cl, kl, profile), "solve task 8")


def test_run_wrapper_preserves_v0_behavior() -> None:
    """The full-lifecycle ``run`` wrapper still emits artifacts + returns the
    trivial Phase1Result when the dispatcher carries no profile."""
    from mindsos_intelligence.phase_1 import run

    cl = CapacityLayer()
    install_phase1_v0(cl)
    disp = L4Dispatcher(cl)

    class _Writer:
        def emit_hint_set(self, hints):
            return SimpleNamespace(iri="hintset:1")

        def emit_mapping_result(self, hs_iri, tp_iri, conf):
            assert tp_iri == TRIVIAL_REQUEST_PATTERN_IRI
            return SimpleNamespace(iri="mapping:1")

    result = run(disp, _Writer(), "anything")
    assert result.request_pattern_iri == TRIVIAL_REQUEST_PATTERN_IRI
    assert result.hint_set_ref == "hintset:1"
    assert result.mapping_result_ref == "mapping:1"
