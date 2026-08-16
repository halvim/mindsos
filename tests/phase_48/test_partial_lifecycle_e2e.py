"""The partial record through the FULL lifecycle (critic §67's merge
condition): ``run_lifecycle`` over a partial map classifies ``conceded`` from
the record, and a targeted re-exec cycle — repeated — heals it to
``succeeded``.

The one seam #166 shipped with no direct test was the wiring across the
deleted ``MemberAbortError`` catch: run → terminal-attempt classifier →
outcome. This file drives it with a REAL registered planner override (the
`test_planner_override_e2e` road) emitting seeder-leaf + map + fold, a REAL
upsert-overridden ``should_replan`` returning targeted verdicts, and the
stock v0 catalogs everywhere else.
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins import (
    install_orchestration_v0,
    install_phase1_v0,
    install_planning_v0,
    reset_v0_verdicts,
)
from mindsos_capacity.builtins.orchestration_v0 import (
    DS_REPLAN_STATE,
    DS_REPLAN_VERDICT,
    set_sufficient_result,
)
from mindsos_capacity.builtins.planning_v0 import DS_MAPPING_RESULT, DS_PLAN
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DECISION,
    CATEGORY_DERIVATION,
    CATEGORY_PLANNING,
    capacity_iri,
    datastate_iri,
)
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.orchestrator import Orchestrator

REQ = datastate_iri("ple.request")
COLL = datastate_iri("ple.exposures")
MEMBER = datastate_iri("ple.exposure")
SUB = datastate_iri("ple.verdict")
OUT = datastate_iri("ple.verdicts")
AGG = datastate_iri("ple.claim_conclusion")

CAP_SEED = capacity_iri(CATEGORY_DERIVATION, "ple_seed")
CAP_SOLVE = capacity_iri(CATEGORY_DERIVATION, "ple_decide_one")
CAP_REDUCE = capacity_iri(CATEGORY_DERIVATION, "ple_conclude")

MEMBERS = ["e0", "e1", "e2"]

MEMBER_CALLS: list = []
REDUCER_CALLS: list = []
FLAKY = {"broken": False}


class _FakeSession:
    session_id = "s"
    user_id = "u"
    actor_role = "user"
    capabilities: set = set()

    def has(self, capability):
        return False


def _seed_body(**kw):
    return {COLL: list(MEMBERS)}


def _member_body(**kw):
    v = kw.get(MEMBER)
    MEMBER_CALLS.append(v)
    if v == "e1" and FLAKY["broken"]:
        raise RuntimeError("exposure e1 machinery failure")
    return {SUB: {"verdict": v}}


def _reduce_body(**kw):
    REDUCER_CALLS.append(kw.get(OUT))
    return {AGG: {"conclusion": kw.get(OUT)}}


def _make_orchestrator(replan_verdicts=None):
    """A full v0 orchestrator whose planner is upsert-overridden to emit
    seeder-leaf + map + fold, and whose ``should_replan`` (when
    ``replan_verdicts`` is given) is upsert-overridden to pop one verdict
    dict per check, defaulting to ``continue`` when exhausted."""
    session = _FakeSession()
    layer = CapacityLayer()
    install_planning_v0(layer)
    install_phase1_v0(layer)
    install_orchestration_v0(layer)
    reset_v0_verdicts()

    specs = {
        "ple.exposures": dict(collection=True, member_ds=MEMBER),
        "ple.verdicts": dict(collection=True, member_ds=SUB),
    }
    for name in (
        "ple.request", "ple.exposures", "ple.exposure", "ple.verdict",
        "ple.verdicts", "ple.claim_conclusion",
    ):
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description=name,
                provenance_category=CATEGORY_DERIVATION,
                **specs.get(name, {}),
            ),
            session=session,
            allow_new_realm=True,
        )
    for name, ins, outs, impl in (
        ("ple_seed", (REQ,), (COLL,), _seed_body),
        ("ple_decide_one", (MEMBER,), (SUB,), _member_body),
        ("ple_conclude", (OUT,), (AGG,), _reduce_body),
    ):
        layer.register_capacity(
            Capacity(
                name=name, category=CATEGORY_DERIVATION,
                inputs=ins, outputs=outs, implementation=impl,
                description=name,
            ),
            session=session,
        )

    map_spec = {
        "kind": "map", "collection_ds": COLL, "member_ds": MEMBER,
        "sub_target": SUB, "out_ds": OUT,
    }
    fold_spec = {"kind": "fold", "reducer_iri": CAP_REDUCE, "in_ds": OUT}

    def _planner_override(**kw):
        return {DS_PLAN: {
            "solve_target": {
                "start_datastate": REQ, "target_datastate": AGG,
            },
            "milestones": [
                {"spec": None, "leaf_target": {
                    "start_datastate": REQ, "target_datastate": COLL,
                }},
                {"spec": map_spec},
                {"spec": fold_spec},
            ],
        }}

    layer.register_capacity(
        Capacity(
            name="derive_initial_plan", category=CATEGORY_PLANNING,
            inputs=(DS_MAPPING_RESULT,), outputs=(DS_PLAN,),
            implementation=_planner_override,
            description="e2e override: seeder leaf + map/fold milestones",
        ),
        session=session, if_exists="upsert",
    )

    if replan_verdicts is not None:
        queue = list(replan_verdicts)

        def _replan_override(**kw):
            verdict = queue.pop(0) if queue else {"decision": "continue"}
            return {DS_REPLAN_VERDICT: verdict}

        layer.register_capacity(
            Capacity(
                name="should_replan", category=CATEGORY_DECISION,
                inputs=(DS_REPLAN_STATE,), outputs=(DS_REPLAN_VERDICT,),
                implementation=_replan_override,
                description="e2e override: scripted targeted verdicts",
            ),
            session=session, if_exists="upsert",
        )

    mm = MentalModel(session_id="s", user_id="u")
    dispatcher = L4Dispatcher(layer, session=session)
    return Orchestrator(
        dispatcher, mm, request_scope="ple-req",
        per_request_replan_budget=5,
    ), mm


def test_a_partial_run_classifies_conceded_through_the_full_lifecycle():
    """The seam across the deleted catch: one member crashes at the cap, the
    run COMPLETES, and the terminal-attempt classifier — not a caught
    exception — decides ``conceded`` from the record. (``sufficient`` is
    forced False as the v0 stand-in for 'the conclusion is missing'; the v0
    default True would mask the classifier entirely.)"""
    MEMBER_CALLS.clear()
    REDUCER_CALLS.clear()
    FLAKY["broken"] = True
    orch, _mm = _make_orchestrator()
    try:
        set_sufficient_result(False)
        outcome = orch.run_lifecycle({"x": 1})
    finally:
        reset_v0_verdicts()
        FLAKY["broken"] = False
    assert outcome.status == "conceded"
    assert "e2" in MEMBER_CALLS, "the sibling after the crash ran"
    assert REDUCER_CALLS == [], "no conclusion from a truncated domain"


def test_repeated_targeted_reexec_heals_the_partial_to_succeeded():
    """The splice's REPEATED case, end-to-end: the member fails its first
    cycle, a targeted verdict re-runs it (still broken — splice pass 1 keeps
    the stop in place), a second targeted verdict re-runs it healed (splice
    pass 2 inserts the value), the fold concludes over the ordered full
    domain, and the lifecycle completes ``succeeded`` with two replans."""
    MEMBER_CALLS.clear()
    REDUCER_CALLS.clear()
    FLAKY["broken"] = True
    targeted = {"decision": "replan", "replan_level": "map", "target_ref": "1:m1"}
    orch, _mm = _make_orchestrator(
        replan_verdicts=[dict(targeted), dict(targeted)],
    )

    real_member = _member_body
    calls = {"n": 0}

    def _heal_on_second_retarget(**kw):
        if kw.get(MEMBER) == "e1":
            calls["n"] += 1
            # Heal on the member's THIRD run — the initial cycle, then the
            # first targeted re-exec, then this one — which is what "heals
            # on the second targeted cycle" means and is all this test is
            # about.
            #
            # **This threshold was 5, and 5 was two-attempts-per-cycle
            # arithmetic** rather than a statement of intent: blanket
            # member retry meant each cycle called e1 twice. ADR-0201 am-7
            # made retry a declared property and this capacity does not
            # declare it, so a cycle is now one call and the number is
            # simply the cycle. The coupling was incidental — this test is
            # about the replan splice, not about retry — so it is removed
            # rather than restored by declaring the fixture retryable.
            if calls["n"] >= 3:
                FLAKY["broken"] = False
        return real_member(**kw)

    orch._dispatcher.capacity_layer.register_capacity(
        Capacity(
            name="ple_decide_one", category=CATEGORY_DERIVATION,
            inputs=(MEMBER,), outputs=(SUB,),
            implementation=_heal_on_second_retarget,
            description="flaky member healing on the second targeted cycle",
        ),
        session=orch._dispatcher.session, if_exists="upsert",
    )
    try:
        outcome = orch.run_lifecycle({"x": 1})
    finally:
        reset_v0_verdicts()
        FLAKY["broken"] = False
    assert outcome.status == "succeeded"
    assert outcome.replans_used == 2
    assert len(REDUCER_CALLS) == 1
    assert REDUCER_CALLS[0] == [
        {"verdict": "e0"}, {"verdict": "e1"}, {"verdict": "e2"},
    ]
