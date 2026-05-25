"""Phase 28 — CapacityLayer.__init__ + per-Local invariant tests."""

from __future__ import annotations

from mindsos_capacity import (
    CapacityLayer,
    CapacityLayerView,
    CATEGORY_PATH_FINDING,
    CATEGORY_PERCEPTION,
    FUNCTIONAL_CATEGORIES,
    ROLE_DATASTATES,
    category_role,
    create_global,
)


def test_construct_default_categories():
    cl = CapacityLayer()
    roles = {g.role for g in cl.global_metagraph().graphs.values()}
    assert ROLE_DATASTATES in roles
    for cat in FUNCTIONAL_CATEGORIES:
        assert category_role(cat) in roles


def test_construct_with_pre_built_global():
    custom = create_global(categories=(CATEGORY_PERCEPTION,))
    cl = CapacityLayer(global_metagraph=custom, categories=(CATEGORY_PATH_FINDING,))
    roles = {g.role for g in cl.global_metagraph().graphs.values()}
    assert category_role(CATEGORY_PERCEPTION) in roles
    assert category_role(CATEGORY_PATH_FINDING) not in roles


def test_construct_with_limited_categories():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION, CATEGORY_PATH_FINDING))
    roles = {g.role for g in cl.global_metagraph().graphs.values()}
    assert roles == {
        ROLE_DATASTATES,
        category_role(CATEGORY_PERCEPTION),
        category_role(CATEGORY_PATH_FINDING),
    }


def test_local_metagraph_is_lazy_and_cached():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    a1 = cl.local_metagraph("alice")
    a2 = cl.local_metagraph("alice")
    assert a1 is a2


def test_local_view_returns_capacity_layer_view():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    v = cl.local_view("alice")
    assert isinstance(v, CapacityLayerView)
    assert v.name.endswith("alice")


def test_capacity_index_initialized_for_global_at_construct():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    gmg = cl.global_metagraph()
    assert gmg.metagraph_id in cl._capacity_index
    assert cl._capacity_index[gmg.metagraph_id] == {}


def test_capacity_index_initialized_atomically_with_local_metagraph():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    lmg = cl.local_metagraph("alice")
    assert lmg.metagraph_id in cl._capacity_index
    assert cl._capacity_index[lmg.metagraph_id] == {}


def test_problem_trace_attribute_present_at_phase_30():
    """Phase 28 sentinel FLIPPED at Phase 30 (R0 PB-9(a) + R3 PB-37(a)).

    Original Phase 28 sentinel asserted ``problem_trace`` attribute was
    NOT present on ``CapacityLayer``. Phase 30 lifts it per ADR-0074
    §Implementation (Phase 30 footer). Function rename only (file
    contains other unrelated init tests).
    """
    from mindsos_capacity import ProblemTraceSink

    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    assert hasattr(cl, "problem_trace"), (
        "problem_trace must be present on CapacityLayer at Phase 30 "
        "per ADR-0074 §Implementation (Phase 30) ship footer."
    )
    assert isinstance(cl.problem_trace, ProblemTraceSink)
    assert len(cl.problem_trace) == 0


def test_repr_shape():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    r = repr(cl)
    assert "CapacityLayer" in r
    assert "global=" in r
    assert "locals=0" in r
    assert "capacities=0" in r
