"""PROBE, not a guard, and REMOVED before this slice ships.

**The question step 2 cannot answer by reading.** Every member branch in
``dr_routing`` today is ONE level: ``exposure -> reader -> value``. A DATED
policy lookup needs ``exposure -> as-of reader -> as-of -> threshold lookup ->
threshold``, which is TWO. Two-deep composes on the LEAF road — ``dr_assessment``
does exactly that — and **no member road in this demo has ever done it.**

If this composes, step 2's threshold is read per exposure inside the map. If it
does not, the honest fallback is a weaker step 2 and the ship record says so.

**Composed by the build lane.** Everything printed after ``>`` is the tree's.
"""
from __future__ import annotations

import sys
import traceback

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.policy_lookup_v0 import (
    build_policy_limit_lookup,
    policy_limit_datastates,
)
from mindsos_capacity.builtins.structured_ingest_v0 import (
    build_structured_ingest_reader,
    structured_value_datastates,
)
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import (
    CATEGORY_DECISION,
    CATEGORY_DERIVATION,
    datastate_iri,
)
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult
from mindsos_knowledge.knowledge_layer import KnowledgeLayer
from mindsos_knowledge.policies import ROLE_POLICIES, write_policy_edition

from decision_records_demo.dr_routing import (
    CAP_ASSIGN,
    COVERAGE_INJURY,
    COVERAGE_VEHICLE,
    DETERMINED_BY,
    DS_CLAIM_EXPOSURES,
    DS_COVERAGE,
    DS_DESK,
    DS_DESKS,
    DS_EXPOSURE,
    EXPOSURE_REF,
    ROUTINE_DESK,
    SOURCE_PHRASE,
    SPECIALTY_UNIT,
    _Session,
    _assign,
    _exposure_ref,
)

DS_OFF_WORK = datastate_iri("drdemo.off_work_weeks")
DS_ROUTING_AS_OF = datastate_iri("drdemo.routing_as_of")
DS_THRESHOLD = datastate_iri("drdemo.specialty_threshold_weeks")
DS_ROUTING = datastate_iri("drdemo.claim_routing")

POLICY_ID = "policy:drdemo.injury_routing"
POLICY_PHRASE = "the injury-routing policy"
EDITION = dict(
    version="v2024.1",
    in_force_from="2024-01-01",
    in_force_to=None,
    stated_value=4,
    text="An injury exposure whose claimant is off work four weeks or more "
         "goes to the specialty injury unit.",
)

EXPOSURES = [
    {"claimant": "A. Silva", "coverage": COVERAGE_VEHICLE,
     "routing_as_of": "2026-06-03"},
    {"claimant": "C. Mensah", "coverage": COVERAGE_INJURY,
     "off_work_weeks": 6, "routing_as_of": "2026-06-03"},
]


def _route(context=None, **inputs):
    coverage = inputs.get(DS_COVERAGE)
    weeks = inputs.get(DS_OFF_WORK)
    threshold = inputs.get(DS_THRESHOLD)
    ref = _exposure_ref(inputs.get(DS_EXPOSURE), coverage)

    def _verdict(**fields):
        if ref:
            fields[EXPOSURE_REF] = ref
        return {DS_DESK: fields}

    if coverage == COVERAGE_VEHICLE:
        return _verdict(decision=ROUTINE_DESK, **{DETERMINED_BY: DS_COVERAGE})
    if weeks is None or threshold is None:
        return _verdict(decision=None, refusal_reason="field_absent")
    desk = SPECIALTY_UNIT if int(weeks) >= int(threshold) else ROUTINE_DESK
    return _verdict(decision=desk, **{DETERMINED_BY: DS_OFF_WORK})


def _reader(name, field, iri, elem, phrase, question):
    return build_structured_ingest_reader(
        name=name, field=field, value_datastate_iri=iri, value_elem=elem,
        source_datastate_iri=DS_EXPOSURE, source_identity_phrase=SOURCE_PHRASE,
        value_phrase=phrase, question=question,
    )


def build():
    session = _Session()
    layer = CapacityLayer()
    pairs = (
        structured_value_datastates(
            value_name="drdemo.exposure_coverage", value_elem="str",
            value_description="the coverage this exposure was filed under")
        + structured_value_datastates(
            value_name="drdemo.off_work_weeks", value_elem="int",
            value_description="the weeks off work this exposure states")
        + structured_value_datastates(
            value_name="drdemo.routing_as_of", value_elem="str",
            value_description="the date this exposure is routed as of")
        + policy_limit_datastates(
            limit_name="drdemo.specialty_threshold_weeks", limit_elem="int",
            limit_description="the off-work threshold in force")
    )
    base = [
        DataState(name="drdemo.routed_claim_exposures",
                  shape=ShapeDescriptor.opaque("drdemo.routed_claim_exposures"),
                  description="the exposures the claim was split into",
                  collection=True, member_ds=DS_EXPOSURE),
        DataState(name="drdemo.routed_exposure",
                  shape=ShapeDescriptor.opaque("drdemo.routed_exposure"),
                  description="one exposure, as filed"),
        DataState(name="drdemo.desk_verdict",
                  shape=ShapeDescriptor.opaque("drdemo.desk_verdict"),
                  description="which desk this exposure goes to",
                  refusal_capable=True),
        DataState(name="drdemo.desk_verdicts",
                  shape=ShapeDescriptor.opaque("drdemo.desk_verdicts"),
                  description="each exposure's desk, in order",
                  collection=True, member_ds=DS_DESK),
        DataState(name="drdemo.claim_routing",
                  shape=ShapeDescriptor.opaque("drdemo.claim_routing"),
                  description="where this claim's exposures were sent"),
    ]
    for ds in base + list(pairs):
        layer.register_datastate(ds, session=session, allow_new_realm=True)

    for cap in (
        _reader("drdemo_read_coverage", "coverage", DS_COVERAGE, "str",
                "a coverage", "Which coverage was this exposure filed under?"),
        _reader("drdemo_read_off_work", "off_work_weeks", DS_OFF_WORK, "int",
                "a period off work",
                "How many weeks off work does this exposure state?"),
        _reader("drdemo_read_routing_as_of", "routing_as_of", DS_ROUTING_AS_OF,
                "str", "a date to route as of",
                "As of what date is this exposure being routed?"),
        build_policy_limit_lookup(
            name="drdemo_lookup_off_work_threshold", policy_id=POLICY_ID,
            source_identity_phrase=POLICY_PHRASE,
            question="What off-work threshold sent an injury to the specialty "
                     "unit on {as_of}?",
            limit_datastate_iri=DS_THRESHOLD,
            as_of_datastate_iri=DS_ROUTING_AS_OF),
        Capacity(name="drdemo_route_exposure", category=CATEGORY_DECISION,
                 inputs=(DS_COVERAGE, DS_OFF_WORK, DS_THRESHOLD, DS_EXPOSURE),
                 outputs=(DS_DESK,), implementation=_route,
                 description="one exposure -> one desk",
                 printable_phrase="choosing the desk for one exposure"),
        Capacity(name="drdemo_assign_claim", category=CATEGORY_DERIVATION,
                 inputs=(DS_DESKS,), outputs=(DS_ROUTING,),
                 implementation=_assign, decodes_refusals=True,
                 description="the desks -> the claim's assignment",
                 printable_phrase="assigning the claim from its exposures"),
    ):
        layer.register_capacity(cap, session=session)

    kl = KnowledgeLayer.bootstrap()
    write_policy_edition(kl.writeable(None, ROLE_POLICIES, "global"),
                         policy_id=POLICY_ID, **EDITION)
    mm = MentalModel(session_id="drdemo-session", user_id="drdemo-user")
    dispatcher = L4Dispatcher(layer, session=session, kl=kl)
    writer = ChainArtifactWriter(mm, "drdemo-probe")
    return mm, dispatcher, writer, writer.emit_request_run()


def main():
    mm, dispatcher, writer, request_run = build()
    plan = PlanResult(
        plan_ref="plan:drdemo-routing", root_milestone_ref="m0",
        leaf_milestone_refs=["mMap", "mFold"],
        pipeline_refs={"mMap": "pMap", "mFold": "pFold"},
        milestone_specs={
            "mMap": {"kind": "map", "collection_ds": DS_CLAIM_EXPOSURES,
                     "member_ds": DS_EXPOSURE, "sub_target": DS_DESK,
                     "out_ds": DS_DESKS, "finder": "conjunction"},
            "mFold": {"kind": "fold", "reducer_iri": CAP_ASSIGN,
                      "in_ds": DS_DESKS},
        })
    graphs = []
    try:
        execution.run(dispatcher, writer, plan, request_run, mm=mm,
                      solve_seed={DS_CLAIM_EXPOSURES: [dict(e) for e in EXPOSURES]},
                      capacity_graphs=graphs, case_label="probe")
    except Exception:
        print("> TWO-DEEP MEMBER BRANCH: DID NOT COMPOSE")
        traceback.print_exc()
        return 1
    print("> TWO-DEEP MEMBER BRANCH: COMPOSED")
    print("> graphs:", len(graphs))
    # ⚠ COMPOSED alone proves only that nothing raised. It would print the same
    # if every exposure had REFUSED — which is what a failed reader looks like
    # from here. The page is the answer: it names the desks, the deciding fact
    # and the edition, or it does not.
    from decision_records_demo.dr_render import render_from_graphs

    page = render_from_graphs(graphs, {
        "capacity_root_ref": "unused-by-render_from_graphs",
        "consolidated_at": "2026-08-17T12:00:00.000000+00:00",
        "outcome_classification": "completed",
    })
    print("> ---- PAGE, rendered from the graphs, verbatim ----")
    print(page)
    print("> ---- end ----")
    print("> specialty reached:", SPECIALTY_UNIT in page)
    print("> routine reached:", ROUTINE_DESK in page)
    print("> edition named:", "v2024.1" in page)
    return 0


if __name__ == "__main__":
    sys.exit(main())
