"""Shape (a) declarations and their static check (ADR-0209).

The DataState says its values may refuse (`refusal_capable`), the reducer
says it decodes that (`decodes_refusals`), and plan construction refuses the
mismatch BEFORE anything runs — on both entry roads (the planner path and
the direct-`PlanResult` path every current demo driver uses). Without the
check, "a member refuses in-band" is an unenforced convention: the exact
class the collection-iteration review called insufficient, and that ADR-0208
only escaped because its consumer was built in the same ship.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import (
    DataState,
    ShapeDescriptor,
    validate_datastate,
)
from mindsos_capacity.identifiers import (
    CATEGORY_DERIVATION,
    capacity_iri,
    datastate_iri,
)
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import (
    FoldReducerDecodeError,
    PlanResult,
    check_fold_reducer_decode,
)

DS_COLL = datastate_iri("sad.exposures")
DS_MEMBER = datastate_iri("sad.exposure")
DS_SUB = datastate_iri("sad.verdict")
DS_OUT = datastate_iri("sad.verdicts")
DS_AGG = datastate_iri("sad.claim_conclusion")

CAP_SOLVE = capacity_iri(CATEGORY_DERIVATION, "sad_decide_one")
CAP_REDUCE = capacity_iri(CATEGORY_DERIVATION, "sad_conclude")

MEMBER_CALLS: list = []


class FakeSession:
    session_id = "s"
    user_id = "u"
    actor_role = "user"
    capabilities: set = set()

    def has(self, capability: str) -> bool:
        return False


def _member_body(**kwargs):
    MEMBER_CALLS.append(kwargs.get(DS_MEMBER))
    return {DS_SUB: {"verdict": kwargs.get(DS_MEMBER)}}


def _reduce_body(**kwargs):
    return {DS_AGG: {"conclusion": kwargs.get(DS_OUT)}}


def _harness(*, refusal_capable: bool, decodes: bool):
    session = FakeSession()
    layer = CapacityLayer()
    specs = {
        "sad.exposures": dict(collection=True, member_ds=DS_MEMBER),
        "sad.exposure": {},
        "sad.verdict": dict(refusal_capable=refusal_capable),
        "sad.verdicts": dict(collection=True, member_ds=DS_SUB),
        "sad.claim_conclusion": {},
    }
    for name, extra in specs.items():
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description=f"({name})",
                provenance_category=CATEGORY_DERIVATION,
                **extra,
            ),
            session=session,
            allow_new_realm=True,
        )
    layer.register_capacity(
        Capacity(
            name="sad_decide_one",
            category=CATEGORY_DERIVATION,
            inputs=(DS_MEMBER,),
            outputs=(DS_SUB,),
            implementation=_member_body,
            description="one exposure -> its verdict",
        ),
        session=session,
    )
    layer.register_capacity(
        Capacity(
            name="sad_conclude",
            category=CATEGORY_DERIVATION,
            inputs=(DS_OUT,),
            outputs=(DS_AGG,),
            implementation=_reduce_body,
            description="the ordered verdicts -> the claim conclusion",
            decodes_refusals=decodes,
        ),
        session=session,
    )
    return L4Dispatcher(layer, session=session)


def _fold_specs():
    return {
        "mMap": {
            "kind": "map", "collection_ds": DS_COLL, "member_ds": DS_MEMBER,
            "sub_target": DS_SUB, "out_ds": DS_OUT,
        },
        "mFold": {"kind": "fold", "reducer_iri": CAP_REDUCE, "in_ds": DS_OUT},
    }


# ── the DataState half ────────────────────────────────────────────────


def test_refusal_capable_defaults_false_and_stays_off_the_node():
    ds = DataState(name="sad.plain", shape=ShapeDescriptor.opaque("p"))
    assert ds.refusal_capable is False
    assert "refusal_capable" not in ds.to_properties()


def test_refusal_capable_is_emitted_to_the_node_properties():
    ds = DataState(
        name="sad.maybe", shape=ShapeDescriptor.opaque("m"),
        refusal_capable=True,
    )
    assert ds.to_properties()["refusal_capable"] is True


def test_refusal_capable_is_free_standing_no_collection_tie():
    """§44 Q2: not restricted to a current member_ds — that tie would make
    registration order-dependent and block a future leaf consumer."""
    validate_datastate(
        DataState(
            name="sad.leaf", shape=ShapeDescriptor.opaque("l"),
            refusal_capable=True,
        )
    )


# ── the reducer half ──────────────────────────────────────────────────


def test_decodes_refusals_defaults_false_and_is_not_emitted():
    cap = Capacity(
        name="c", category=CATEGORY_DERIVATION, inputs=(), outputs=(),
    )
    assert cap.decodes_refusals is False
    assert "decodes_refusals" not in cap.to_properties()


# ── the static check ──────────────────────────────────────────────────


def test_a_fold_over_a_refusal_capable_member_set_requires_the_decode():
    dispatcher = _harness(refusal_capable=True, decodes=False)
    with pytest.raises(FoldReducerDecodeError) as exc:
        check_fold_reducer_decode(dispatcher, _fold_specs())
    assert "decodes_refusals" in str(exc.value)


def test_a_declared_decode_passes_the_check():
    dispatcher = _harness(refusal_capable=True, decodes=True)
    check_fold_reducer_decode(dispatcher, _fold_specs())


def test_a_non_refusal_capable_member_set_is_untouched():
    """Every plan that exists today: no refusal-capable type, no verdict."""
    dispatcher = _harness(refusal_capable=False, decodes=False)
    check_fold_reducer_decode(dispatcher, _fold_specs())


def test_a_nested_sub_plan_fold_is_checked_too():
    dispatcher = _harness(refusal_capable=True, decodes=False)
    specs = {
        "mOuter": {
            "kind": "map", "collection_ds": DS_COLL, "member_ds": DS_MEMBER,
            "sub_target": DS_AGG, "out_ds": datastate_iri("sad.outer_out"),
            "sub_plan": {
                "leaf_milestone_refs": ["s0"],
                "milestone_specs": _fold_specs(),
            },
        },
    }
    with pytest.raises(FoldReducerDecodeError):
        check_fold_reducer_decode(dispatcher, specs)


def test_the_check_holds_on_the_direct_plan_result_road_before_any_member_runs():
    """A hand-built PlanResult never passes through plan_construction.build —
    the road every current demo driver uses. The check refuses at run intake,
    statically: no member body executes."""
    MEMBER_CALLS.clear()
    dispatcher = _harness(refusal_capable=True, decodes=False)
    mm = MentalModel(session_id="s", user_id="u")
    writer = ChainArtifactWriter(mm, "t")
    request_run = writer.emit_request_run()
    plan = PlanResult(
        plan_ref="plan:sad",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mMap", "mFold"],
        pipeline_refs={"mMap": "pMap", "mFold": "pFold"},
        milestone_specs=_fold_specs(),
    )
    with pytest.raises(FoldReducerDecodeError):
        execution.run(
            dispatcher, writer, plan, request_run,
            mm=mm, solve_seed={DS_COLL: ["e0", "e1"]},
            capacity_graphs=[],
        )
    assert MEMBER_CALLS == []
