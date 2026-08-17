"""dr_routing — the routing content: exposures to desks, on the Guidewire-sourced model.

Beat 1 of the demo script (one claim, two desks), and the shape-(a)
consumption that makes beat 2 (a refusal beside an answer) renderable.
Design: coordination §71 (this lane), §72 (critic), owner rulings D5 (demo
consumption) and the §50.4 Gate-4 restatement.

**Gate 4, checked in writing before anything registers (the restated form):**
no new capacity CATEGORY beyond ``origin_v0.DECISION_SHAPED_CATEGORIES`` and
no new ``FAMILY_RULES`` entry was needed. The routing decision registers in
``decision`` — already in the frozenset — whose family dont-know shape is
``VERDICT``, which is exactly shape (a)'s refusal-as-verdict (ADR-0209). The
readers register in ``retrieval`` via the shipped structured-ingest factory.
Nothing else is decision-shaped. PASS.

**Sourcing (do-not-invent, plan §2.5):** the desks are Guidewire's own
worked example — vehicle exposures to a routine group, the injury exposure
to a specialty group; the coverage words are the taxonomy §3 unit names
(Auto Physical Damage, Bodily Injury); an off-work TIER as the deciding axis
is §3's "severity tier dominates", expressed as the stated fact the tier is
computed from rather than as the conclusion. The demo shows THAT routing
happens and does not assert what every carrier does.

⚠ **THE RULE LIVES IN THE STORE, NOT IN THIS FILE** (plan §0.4 item 7 step 2).
``_route`` compares a claimant's stated weeks off work against a THRESHOLD read
from a dated policy edition by ``policy_lookup_v0`` — the same capacity beat 4
uses for the dwelling limit. There is no threshold literal in this module, and
a guard pins that. **Two editions ship**: eight weeks in 2023, four from 2024,
so the same exposure reaches different desks under different editions and the
routing beats gain beat 4's *"which edition governed"* without a second
fixture.

**The member pipeline** (composed by the ConjunctionFinder — the map spec
sets ``finder: conjunction`` because the decision is genuinely multi-input,
a diamond from the one member start):

    exposure ──> coverage reader ──> the coverage this exposure was filed under
             ├─> off-work reader ──> the weeks this exposure states
             └─> as-of reader ──> a date ──> threshold lookup ──> the rule
                       all three ──> the routing decision ──> desk verdict

⚠ The third branch is TWO DEEP, which no member pipeline in this demo had ever
been. It was PROBED before a guard was written — it composes.

Each reader is the shipped ``structured_ingest_v0`` factory: on an absent
field it refuses IN-BAND — value ``None`` plus an origin record naming the
missing item — and the decision, seeing the ``None`` where it needed a
value, returns the shape-(a) refusal verdict: ``decision: None`` plus the
structural ``refusal_reason`` marker, NO prose. The prose lives in the
reader's origin record (ADR-0209 D1: the type governs decoding; the record
carries the words). A vehicle exposure routes on coverage alone, so the
off-work reader's refusal on it is recorded but decides nothing.

``drdemo.desk_verdict`` is the first ``refusal_capable`` DataState anywhere;
the reducer declares ``decodes_refusals`` and
``plan_construction.check_fold_reducer_decode`` enforces the pair statically
on the direct-``PlanResult`` road this module drives (ADR-0209 D4).

Desk verdict VALUES carry the decision, the determining input, and the
words that NAME the exposure they are about
(``{"decision": <desk>, "determined_by": <input>, "exposure_ref": <words>}``).
⚠ **The third field was added 2026-08-17 (ship B slice 1) and this
paragraph was corrected WITH it** — it previously said the values carried
"nothing else", and shipping the field without the sentence is the
docstring-describing-code-that-no-longer-exists defect this lane has now
recorded eight times.

**Why the field exists, and the premise that had to be corrected first.**
The claim-level line said *"1 cannot be assigned yet - see the exposure
above"*, which is ambiguous over four exposures (a §11 page defect, promoted
into ship B by coordination §91 Q5). §91 proposed the fix on the premise
that *"the verdict values embed the exposure"* — TRUE of ``dr_dump._decide``,
**FALSE here**. The reducer's only input is the ordered desk verdicts, so
before this field it could not name D. Laurent from anything it received.
The premise was checked against the source before the fix was written.

⚠ **A consequence, stated rather than discovered later: two routine-desk
verdicts are no longer byte-identical**, because each now names its own
exposure. That is a LOSS of fixture coverage, not a gain — the identical-bare-
verdict correlation path (ADR-0201 am-5, N-F2 defused, position correlates
them) was exercised live by this module and now is not. It stays covered by
``test_identical_bare_verdicts_render_by_position`` on the ``dr_dump``
fixtures, and that is now its ONLY cover.

This module is demo code: it registers into its own layer and never edits
``mindsos_*`` (RULES §3).

**Gate 4, re-checked for THIS slice (the restated form).** It registers
nothing new: no ``Capacity``, no ``DataState``, no capacity CATEGORY beyond
``origin_v0.DECISION_SHAPED_CATEGORIES``, no ``FAMILY_RULES`` entry. What
changes is two implementation bodies and one declared input tuple. PASS —
and it is the weakest form of this check the lane has run, which is worth
saying rather than letting a trivial pass read like a real one.
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.origin_v0 import (
    REFUSAL_FIELD_ABSENT,
    REFUSAL_NO_SOURCE_IN_FORCE,
)
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
    capacity_iri,
    datastate_iri,
)
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.plan_construction import PlanResult

DS_CLAIM_EXPOSURES = datastate_iri("drdemo.routed_claim_exposures")
DS_EXPOSURE = datastate_iri("drdemo.routed_exposure")
DS_COVERAGE = datastate_iri("drdemo.exposure_coverage")
DS_OFF_WORK = datastate_iri("drdemo.off_work_weeks")
DS_ROUTING_AS_OF = datastate_iri("drdemo.routing_as_of")
DS_THRESHOLD = datastate_iri("drdemo.specialty_threshold_weeks")
DS_DESK = datastate_iri("drdemo.desk_verdict")
DS_DESKS = datastate_iri("drdemo.desk_verdicts")
DS_ROUTING = datastate_iri("drdemo.claim_routing")

CAP_ROUTE = capacity_iri(CATEGORY_DECISION, "drdemo_route_exposure")
CAP_ASSIGN = capacity_iri(CATEGORY_DERIVATION, "drdemo_assign_claim")

#: The routing policy, stored in the ``policies`` L2 role and read the way the
#: dwelling limit is (plan §0.4 item 7 step 2). ⚠ **It is not "severe →
#: specialty", which would restate a Python conditional.** It is a THRESHOLD a
#: claims manager can read, disagree with, and ask to have changed — which is
#: also what gives the staged parry something specific to decline.
ROUTING_POLICY_ID = "policy:drdemo.injury_routing"
ROUTING_POLICY_PHRASE = "the injury-routing policy"

#: ⚠ **ONE threshold, not the disjunction** (plan §0.5 item 4). *"Transferred
#: from scene, OR off work four weeks or more"* is withdrawn for v1 because the
#: chosen fixture satisfies BOTH for the same claimant, ``DETERMINED_BY`` holds
#: exactly one DataState, and the page would have stated a reason that is not
#: counterfactually the reason.
ROUTING_EDITION_2023 = dict(
    version="v2023.1",
    in_force_from="2023-01-01",
    in_force_to="2023-12-31",
    stated_value=8,
    text="An injury exposure whose claimant is off work eight weeks or more "
         "goes to the specialty injury unit.",
)
ROUTING_EDITION_2024 = dict(
    version="v2024.1",
    in_force_from="2024-01-01",
    in_force_to=None,
    stated_value=4,
    text="An injury exposure whose claimant is off work four weeks or more "
         "goes to the specialty injury unit.",
)

ROUTINE_DESK = "the routine claims desk"
SPECIALTY_UNIT = "the specialty injury unit"
SOURCE_PHRASE = "the intake record for this exposure"

#: The demo-owned structural field naming WHICH INPUT determined a verdict.
#: Same shape and same discipline as ADR-0209's ``refusal_reason``: it names a
#: DataState, so it is **branch-only and never printed** (G6 bans IRIs from the
#: page). The renderer uses it to SELECT which stored question and answer to
#: show. Demo vocabulary on an opaque demo DataState — core is untouched
#: (RULES §3), and Gate 4's restated form is unaffected: no new capacity
#: category, no new ``FAMILY_RULES`` entry.
DETERMINED_BY = "determined_by"

#: The demo-owned field carrying the WORDS that name one exposure — the
#: claimant as filed plus the coverage that was read. Unlike
#: :data:`DETERMINED_BY` this one is **printed**: the claim-level line is
#: built out of it. What must never print is the field NAME, exactly as for
#: every other structural key, and a guard pins that.
EXPOSURE_REF = "exposure_ref"

#: The demo-owned structural field naming WHICH STORED RULE a verdict was
#: measured against. Same shape and discipline as :data:`DETERMINED_BY` — it
#: names a DataState, so it is **branch-only and never printed**. The renderer
#: uses it to select the rule's stored question, its answer, and the EDITION
#: behind it.
#:
#: ⚠ **Why it exists, and it was found by a probe rather than by design.**
#: Moving the rule into the store made the page say NOTHING about it: the
#: renderer surfaces the deciding fact and THAT fact's source, and the deciding
#: fact is the claimant's weeks off work, whose source is the intake record.
#: The threshold reached the decision and never reached the page. **Stored is
#: not shown**, and a step that only stores changes nothing a room can see —
#: beat 4's transfer line would have had nothing to point at on beats 1 and 2.
MEASURED_AGAINST = "measured_against"

#: Coverage words: taxonomy §3 unit names, verbatim.
COVERAGE_VEHICLE = "Auto Physical Damage"
COVERAGE_INJURY = "Bodily Injury"

#: Beat 1 — one claim, three exposures, two desks (Guidewire's worked case).
CASE_A_EXPOSURES = [
    {"claimant": "A. Silva", "coverage": COVERAGE_VEHICLE,
     "loss": "collision, 3 June", "routed_as_of": "2026-06-03"},
    {"claimant": "B. Osei", "coverage": COVERAGE_VEHICLE,
     "loss": "collision, 3 June", "routed_as_of": "2026-06-03"},
    # ⚠ SIX WEEKS, a STATED FACT, not "severe" — a conclusion (plan §0.4 item
    # 3a). The stored policy tiers it. Six is deliberately between the two
    # editions' thresholds (8 in 2023, 4 in 2024), so the SAME exposure reaches
    # different desks under different editions and the routing beats gain
    # beat 4's "which edition governed" without a second fixture.
    {"claimant": "C. Mensah", "coverage": COVERAGE_INJURY,
     "loss": "collision, 3 June", "routed_as_of": "2026-06-03",
     "off_work_weeks": 6},
]

#: The same claim routed as of a date the OLDER edition was in force. Six weeks
#: cleared the 2024 threshold of four; it does not clear the 2023 threshold of
#: eight, so C. Mensah goes to the ROUTINE desk and the page says which edition
#: sent him there.
CASE_A_EXPOSURES_2023 = [
    dict(exposure, routed_as_of="2023-06-03") for exposure in CASE_A_EXPOSURES
]

#: Beat 2 — the same claim, one more injury exposure whose off-work period is
#: ABSENT: a refusal beside answers on the same page. ⚠ The policy cannot tier
#: a fact that was never stated, and the Record names the MISSING COMPONENT
#: rather than supplying one — which is the contrast plan §0.4 item 3a says
#: exists BECAUSE of the extraction contract rather than in spite of it.
CASE_B_EXPOSURES = CASE_A_EXPOSURES + [
    {"claimant": "D. Laurent", "coverage": COVERAGE_INJURY,
     "loss": "collision, 3 June", "routed_as_of": "2026-06-03"},
]


class _Session:
    session_id = "drdemo-session"
    user_id = "drdemo-user"
    actor_role = "user"
    capabilities: set = set()

    def has(self, capability: str) -> bool:
        return False


def _exposure_ref(exposure, coverage):
    """The words that NAME one exposure, for the claim-level line.

    Composed by the decision because the REDUCER never sees an exposure —
    its only input is the ordered desk verdicts (see the module docstring
    for the corrected §91 premise).

    ``None`` when the exposure states no claimant. An exposure the record
    cannot name is a thing the reducer must REFUSE over, not paper over with
    a count — so the absence is returned rather than filled with a
    placeholder, and :func:`_assign` raises on it.
    """
    if not isinstance(exposure, dict):
        return None
    claimant = exposure.get("claimant")
    if not claimant:
        return None
    if coverage:
        return f"{claimant}, {coverage}"
    return str(claimant)


def _route(context=None, **inputs):
    coverage = inputs.get(DS_COVERAGE)
    weeks = inputs.get(DS_OFF_WORK)
    threshold = inputs.get(DS_THRESHOLD)
    ref = _exposure_ref(inputs.get(DS_EXPOSURE), coverage)

    def _verdict(**fields):
        # The identity rides on EVERY branch, answered and refused alike.
        # Carrying it only where the claim line happens to need it today —
        # the refusals — is the shape that produced five of ship A's six
        # findings: a rule unambiguous only while its domain has one member.
        if ref:
            fields[EXPOSURE_REF] = ref
        return {DS_DESK: fields}

    if coverage == COVERAGE_VEHICLE:
        # A vehicle exposure routes on coverage alone: the off-work reader's
        # refusal on it decides nothing (§76), so the coverage is what
        # determined this desk and the Record must say so and say only that.
        # ⚠ NO rule line here either — no stored rule was applied, and a page
        # citing an authority it did not consult is the same defect as a
        # renderer composing an outcome word.
        return _verdict(decision=ROUTINE_DESK, **{DETERMINED_BY: DS_COVERAGE})
    if weeks is None:
        # The reader refused; the desk cannot be chosen. Structural marker
        # only — the words live in the reader's origin record. NO
        # determining input: nothing determined an outcome there is not one of.
        return _verdict(decision=None, refusal_reason=REFUSAL_FIELD_ABSENT)
    if threshold is None:
        # A DIFFERENT refusal with a DIFFERENT reason: the fact arrived and the
        # RULE did not. ``policy_lookup_v0`` returns None with its own origin
        # record when no edition covers the date, so the words are the lookup's
        # and never ours. Collapsing this into field_absent would tell a room
        # their document was incomplete when it was our policy set that was.
        return _verdict(decision=None,
                        refusal_reason=REFUSAL_NO_SOURCE_IN_FORCE)
    desk = SPECIALTY_UNIT if int(weeks) >= int(threshold) else ROUTINE_DESK
    # The coverage selected this branch; the claimant's WEEKS OFF WORK chose
    # the desk within it. The determining input is the one that moved the
    # answer, not every input that was consulted.
    #
    # ⚠ **The threshold is NOT the deciding fact, and it is not nothing
    # either.** *"Because he is off work six weeks"* is what a room hears;
    # *"because the threshold is four"* is the RULE, and it belongs on its own
    # line with the edition that stated it. Two fields, two lines, one page.
    return _verdict(decision=desk,
                    **{DETERMINED_BY: DS_OFF_WORK,
                       MEASURED_AGAINST: DS_THRESHOLD})


def _assign(context=None, **inputs):
    verdicts = inputs.get(DS_DESKS) or []
    if not verdicts:
        raise ValueError(
            "refusing to assign a claim from zero desk verdicts"
        )
    refused = [
        v for v in verdicts
        if isinstance(v, dict) and v.get("refusal_reason")
    ]
    routine = sum(
        1 for v in verdicts
        if isinstance(v, dict) and v.get("decision") == ROUTINE_DESK
    )
    specialty = sum(
        1 for v in verdicts
        if isinstance(v, dict) and v.get("decision") == SPECIALTY_UNIT
    )
    pending = []
    for verdict in refused:
        ref = verdict.get(EXPOSURE_REF)
        if not ref:
            # G2's posture inside a capacity: a claim line that says only HOW
            # MANY cannot be assigned, over a list of four, is the ambiguity
            # this slice exists to remove. Refuse rather than emit the count.
            raise ValueError(
                "a desk verdict refused without naming its exposure - "
                "refusing to publish a count where the page needs a name"
            )
        pending.append(ref)
    parts = []
    if routine:
        # The "(s)" read as software on the buyer's screen (walk gap 6); it
        # rides along here because this ship already edits this line.
        parts.append(
            f"{routine} exposure{'' if routine == 1 else 's'} to {ROUTINE_DESK}"
        )
    if specialty:
        parts.append(f"{specialty} to {SPECIALTY_UNIT}")
    if pending:
        parts.append(f"{len(pending)} not yet assigned: {'; '.join(pending)}")
    return {DS_ROUTING: {"claim_decision": "; ".join(parts)}}


def routing_datastates():
    coverage_pair = structured_value_datastates(
        value_name="drdemo.exposure_coverage",
        value_elem="str",
        value_description="the coverage this exposure was filed under",
    )
    off_work_pair = structured_value_datastates(
        value_name="drdemo.off_work_weeks",
        value_elem="int",
        value_description="the weeks off work this exposure states",
    )
    as_of_pair = structured_value_datastates(
        value_name="drdemo.routing_as_of",
        value_elem="str",
        value_description="the date this exposure is routed as of",
    )
    threshold_pair = policy_limit_datastates(
        limit_name="drdemo.specialty_threshold_weeks",
        limit_elem="int",
        limit_description="the off-work threshold in force",
    )
    return [
        DataState(
            name="drdemo.routed_claim_exposures",
            shape=ShapeDescriptor.opaque("drdemo.routed_claim_exposures"),
            description="the exposures the claim was split into",
            collection=True,
            member_ds=DS_EXPOSURE,
        ),
        DataState(
            name="drdemo.routed_exposure",
            shape=ShapeDescriptor.opaque("drdemo.routed_exposure"),
            description="one exposure, as filed",
        ),
        DataState(
            name="drdemo.desk_verdict",
            shape=ShapeDescriptor.opaque("drdemo.desk_verdict"),
            description="which desk this exposure goes to",
            refusal_capable=True,
        ),
        DataState(
            name="drdemo.desk_verdicts",
            shape=ShapeDescriptor.opaque("drdemo.desk_verdicts"),
            description="each exposure's desk, in order",
            collection=True,
            member_ds=DS_DESK,
        ),
        DataState(
            name="drdemo.claim_routing",
            shape=ShapeDescriptor.opaque("drdemo.claim_routing"),
            description="where this claim's exposures were sent",
        ),
    ] + coverage_pair + off_work_pair + as_of_pair + threshold_pair


def routing_capacities(*, decodes_refusals: bool = True):
    coverage_reader = build_structured_ingest_reader(
        name="drdemo_read_coverage",
        field="coverage",
        value_datastate_iri=DS_COVERAGE,
        value_elem="str",
        source_datastate_iri=DS_EXPOSURE,
        source_identity_phrase=SOURCE_PHRASE,
        value_phrase="the coverage this exposure was filed under",
        question="Which coverage was this exposure filed under?",
    )
    off_work_reader = build_structured_ingest_reader(
        name="drdemo_read_off_work",
        field="off_work_weeks",
        value_datastate_iri=DS_OFF_WORK,
        value_elem="int",
        source_datastate_iri=DS_EXPOSURE,
        source_identity_phrase=SOURCE_PHRASE,
        value_phrase="a period off work",
        question="How many weeks off work does this exposure state?",
    )
    as_of_reader = build_structured_ingest_reader(
        name="drdemo_read_routed_as_of",
        field="routed_as_of",
        value_datastate_iri=DS_ROUTING_AS_OF,
        value_elem="str",
        source_datastate_iri=DS_EXPOSURE,
        source_identity_phrase=SOURCE_PHRASE,
        value_phrase="a date to route as of",
        question="As of what date is this exposure being routed?",
    )
    # ⚠ A TWO-DEEP MEMBER BRANCH — exposure -> as-of reader -> lookup -> the
    # threshold — and it was PROBED before a guard was written. Every other
    # member branch in this module is one level; two-deep was known to work on
    # the LEAF road (dr_assessment) and had never run inside a map. It
    # composes: `_probe_member_depth.py`, run on the gate box 2026-08-17,
    # removed from the tree in the same ship that made it unnecessary.
    threshold_lookup = build_policy_limit_lookup(
        name="drdemo_lookup_off_work_threshold",
        policy_id=ROUTING_POLICY_ID,
        source_identity_phrase=ROUTING_POLICY_PHRASE,
        question="What off-work threshold sent an injury exposure to the "
                 "specialty unit on {as_of}?",
        limit_datastate_iri=DS_THRESHOLD,
        as_of_datastate_iri=DS_ROUTING_AS_OF,
    )
    route = Capacity(
        name="drdemo_route_exposure",
        category=CATEGORY_DECISION,
        # DS_EXPOSURE is declared because the decision NAMES the exposure it
        # decided about; it never DETERMINES the desk, and a guard pins that
        # the determining input is never the exposure. Named fallback if the
        # ConjunctionFinder will not satisfy a member start as a direct input:
        # read the claimant with a third structured-ingest reader.
        inputs=(DS_COVERAGE, DS_OFF_WORK, DS_THRESHOLD, DS_EXPOSURE),
        outputs=(DS_DESK,),
        implementation=_route,
        description="one exposure's read facts -> which desk handles it",
        printable_phrase="choosing the desk for one exposure",
    )
    assign = Capacity(
        name="drdemo_assign_claim",
        category=CATEGORY_DERIVATION,
        inputs=(DS_DESKS,),
        outputs=(DS_ROUTING,),
        implementation=_assign,
        description="the ordered desk verdicts -> where the claim was sent",
        printable_phrase="assigning each exposure to its desk",
        decodes_refusals=decodes_refusals,
    )
    return [coverage_reader, off_work_reader, as_of_reader,
            threshold_lookup, route, assign]


def routing_kl(*editions):
    """A KnowledgeLayer holding whichever routing editions the caller names.

    Defaults to BOTH, because the demo's routing claim is now the same one
    beat 4 makes about the dwelling limit: which edition governed. A harness
    holding one edition can never show that.
    """
    from mindsos_knowledge.knowledge_layer import KnowledgeLayer
    from mindsos_knowledge.policies import ROLE_POLICIES, write_policy_edition

    kl = KnowledgeLayer.bootstrap()
    handle = kl.writeable(None, ROLE_POLICIES, "global")
    for edition in editions or (ROUTING_EDITION_2023, ROUTING_EDITION_2024):
        write_policy_edition(handle, policy_id=ROUTING_POLICY_ID, **edition)
    return kl


def routing_harness(*, decodes_refusals: bool = True, editions=None):
    session = _Session()
    layer = CapacityLayer()
    for ds in routing_datastates():
        layer.register_datastate(ds, session=session, allow_new_realm=True)
    for cap in routing_capacities(decodes_refusals=decodes_refusals):
        layer.register_capacity(cap, session=session)
    mm = MentalModel(session_id="drdemo-session", user_id="drdemo-user")
    # ⚠ The dispatcher now carries a KL. Without one ``policy_lookup_v0``
    # raises ``PolicyStoreUnreachableError`` — our outage — and every injury
    # exposure would stop rather than route. That is the correct behaviour and
    # it is why the harness gained an argument rather than a default of None.
    dispatcher = L4Dispatcher(layer, session=session,
                              kl=routing_kl(*(editions or ())))
    writer = ChainArtifactWriter(mm, "drdemo-task")
    return mm, dispatcher, writer, writer.emit_request_run()


def routing_plan() -> PlanResult:
    return PlanResult(
        plan_ref="plan:drdemo-routing",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mMap", "mFold"],
        pipeline_refs={"mMap": "pMap", "mFold": "pFold"},
        milestone_specs={
            "mMap": {
                "kind": "map",
                "collection_ds": DS_CLAIM_EXPOSURES,
                "member_ds": DS_EXPOSURE,
                "sub_target": DS_DESK,
                "out_ds": DS_DESKS,
                "finder": "conjunction",
            },
            "mFold": {
                "kind": "fold",
                "reducer_iri": CAP_ASSIGN,
                "in_ds": DS_DESKS,
            },
        },
    )
