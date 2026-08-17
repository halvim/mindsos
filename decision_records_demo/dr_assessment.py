"""dr_assessment — beat 4: what the policy pays, decided against the dated limit.

**The walk's second gap, and the one that showed worst.** On 2026-08-17 beat
4 put a page titled *Decision Record* in front of the owner containing two
lookups and no decision: a date in, a limit out. A versioned limit only
matters when something is decided against it, so the beat that the compliance
buyer is supposed to retell had nothing to retell. This module is that
decision (demo plan §0.3 item 8, ship B; walk gap 2).

**Why an AMOUNT, and why this fixture.** §0.3's acceptance splits into a
mechanical gate and a FIXTURE-DESIGN RULE — *every live case's expected
outcome must be derivable by mental arithmetic from values visible on
screen*. A claim of 400,000 against a limit of 350,000 is the only decision
in this demo the room finishes before the page renders. The same claim
assessed as of two dates lands on two editions and pays two different
amounts, which is also exactly the Screen-B comparison the script now
governs: change the date, re-run both, and the Record names the edition and
the window it decided under.

    the claim as filed ─┬─> claimed-amount reader ──────────────┐
                        └─> as-of reader ──> the policy lookup ─┴─> the
                                                assessment ──> what is payable

**Gate 4, checked in writing before anything registers (the restated form):**
no new capacity CATEGORY beyond ``origin_v0.DECISION_SHAPED_CATEGORIES`` and
no new ``FAMILY_RULES`` entry. The assessment registers in ``decision`` —
already in the frozenset, family dont-know shape ``VERDICT``, which is
ADR-0209 shape (a)'s refusal-as-verdict. Both readers register in
``retrieval`` via the shipped structured-ingest factory, and the limit lookup
is the shipped ``policy_lookup_v0`` factory, also ``retrieval``. Nothing else
is decision-shaped. PASS.

**⚠ THE ONE STRUCTURAL LIMIT, and it is a finding rather than a design
choice.** This decision can only refuse for a reason a READER recorded. A
refusal carries no prose of its own — ADR-0209 D1 puts the words in the
origin record, and ``dr_render`` RAISES on a refusing value whose record has
no stored words. So ``field_absent`` (the claim states no amount) and
``value_not_coercible`` (it states something that is not a number) refuse
honestly, because ``structured_ingest_v0`` wrote those words; but a
well-formed nonsense value — a negative claim, a date in 1850 — has no
refusal available to it and is simply decided on. **That is the boundary any
live-editing console inherits**, and it is why no negative-amount branch is
written here: a branch that could only raise is worse than none.

**Sourcing (do-not-invent, plan §2.5):** the dwelling-coverage limit and its
two editions are the ones already in this demo's policy store; the claim is
ours and the room is told so. Nothing here asserts what any carrier pays.

This module is demo code: it registers into its own layer and never edits
``mindsos_*`` (RULES §3).
"""

from __future__ import annotations

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
    capacity_iri,
    datastate_iri,
)
from mindsos_intelligence.plan_construction import PlanResult

from decision_records_demo.dr_dump import POLICY_ID, POLICY_PHRASE

DS_ASSESSED_CLAIM = datastate_iri("drdemo.assessed_claim")
DS_CLAIMED_AMOUNT = datastate_iri("drdemo.claimed_amount")
DS_ASSESSMENT_AS_OF = datastate_iri("drdemo.assessment_as_of")
DS_DWELLING_LIMIT = datastate_iri("drdemo.dwelling_limit")
DS_ASSESSMENT = datastate_iri("drdemo.amount_assessment")

CAP_ASSESS = capacity_iri(CATEGORY_DECISION, "drdemo_assess_amount")

SOURCE_PHRASE = "the claim as filed"

#: The demo-owned structural field naming WHICH INPUT determined a verdict —
#: the same field ``dr_routing``, ``dr_settlement`` and ``dr_render`` declare,
#: spelled as a literal in each because ``dr_render`` may import no demo
#: module (G1). The four spellings are pinned EQUAL test-side.
DETERMINED_BY = "determined_by"

#: Beat 4 — one claim, one amount, two dates. 400,000 against 350,000 and
#: against 375,000: both over, and both subtractions are done in the room
#: before the page appears.
CLAIMED_AMOUNT = 400000

CASE_ASSESSED_PRIOR = {
    "claimant": "F. Okafor",
    "loss": "hail, 12 March",
    "claimed_amount": CLAIMED_AMOUNT,
    "assessed_as_of": "2023-06-01",
}
CASE_ASSESSED_CURRENT = dict(CASE_ASSESSED_PRIOR, assessed_as_of="2024-06-01")


def _assess(context=None, **inputs):
    claimed = inputs.get(DS_CLAIMED_AMOUNT)
    limit = inputs.get(DS_DWELLING_LIMIT)
    if claimed is None or limit is None:
        # A reader refused. Structural marker only — the words live in that
        # reader's origin record (ADR-0209 D1), which is the ONLY source of
        # refusal prose available to this capacity.
        from mindsos_capacity.builtins.origin_v0 import REFUSAL_FIELD_ABSENT

        return {DS_ASSESSMENT: {"decision": None,
                                "refusal_reason": REFUSAL_FIELD_ABSENT}}
    if claimed > limit:
        # The LIMIT is what capped it: had the limit been higher, the answer
        # would have been higher. The amount was merely the thing measured.
        return {DS_ASSESSMENT: {
            # NAMES ITS OWN OPERAND (coordination §101.3(2)). The room is
            # asked to check 400000 - 350000 = 50000, and the page said
            # 400000 only as an unlabelled item in the intake line. The whole
            # arithmetic now sits on the line the room reads, in the words of
            # the capacity that did it — outcome content belongs to the
            # capacity (§100 Q2), and the bare copy above drops out by the
            # echo rule's third door.
            "decision": (
                f"{claimed} claimed, {limit} payable, "
                f"{claimed - limit} above the limit"
            ),
            DETERMINED_BY: DS_DWELLING_LIMIT,
        }}
    # Under the limit the limit is not doing any work: the claim is paid
    # because of what was CLAIMED, and the Record must credit that input.
    return {DS_ASSESSMENT: {
        "decision": f"{claimed} claimed, payable in full",
        DETERMINED_BY: DS_CLAIMED_AMOUNT,
    }}


def assessment_datastates():
    amount_pair = structured_value_datastates(
        value_name="drdemo.claimed_amount",
        value_elem="int",
        value_description="the amount claimed on this claim",
    )
    as_of_pair = structured_value_datastates(
        value_name="drdemo.assessment_as_of",
        value_elem="str",
        value_description="the date this claim is assessed as of",
    )
    limit_pair = policy_limit_datastates(
        limit_name="drdemo.dwelling_limit",
        limit_elem="int",
        limit_description="the dwelling coverage limit in force",
    )
    return [
        DataState(
            name="drdemo.assessed_claim",
            shape=ShapeDescriptor.opaque("drdemo.assessed_claim"),
            description="the claim as it arrived",
        ),
        DataState(
            name="drdemo.amount_assessment",
            shape=ShapeDescriptor.opaque("drdemo.amount_assessment"),
            description="what the policy pays on this claim",
            refusal_capable=True,
        ),
    ] + amount_pair + as_of_pair + limit_pair


def assessment_capacities():
    amount_reader = build_structured_ingest_reader(
        name="drdemo_read_claimed_amount",
        field="claimed_amount",
        value_datastate_iri=DS_CLAIMED_AMOUNT,
        value_elem="int",
        source_datastate_iri=DS_ASSESSED_CLAIM,
        source_identity_phrase=SOURCE_PHRASE,
        value_phrase="an amount claimed",
        question="What amount was claimed on this claim?",
    )
    as_of_reader = build_structured_ingest_reader(
        name="drdemo_read_assessed_as_of",
        field="assessed_as_of",
        value_datastate_iri=DS_ASSESSMENT_AS_OF,
        value_elem="str",
        source_datastate_iri=DS_ASSESSED_CLAIM,
        source_identity_phrase=SOURCE_PHRASE,
        value_phrase="a date this claim is assessed as of",
        # ⚠ NEUTRAL BETWEEN THE TWO CASES BY NECESSITY. One reader asks one
        # question, and beat 4's pair are the SAME claim at two moments —
        # when it was submitted and when it was assessed. A question naming
        # either moment would be false on the other page, so the question
        # names neither and the CASE LABEL carries the framing (walk gap 2's
        # second sentence, ship B).
        question="As of what date is this claim being considered?",
    )
    lookup = build_policy_limit_lookup(
        name="drdemo_lookup_limit_for_assessment",
        policy_id=POLICY_ID,
        source_identity_phrase=POLICY_PHRASE,
        question="What dwelling coverage limit was in force on {as_of}?",
        limit_datastate_iri=DS_DWELLING_LIMIT,
        as_of_datastate_iri=DS_ASSESSMENT_AS_OF,
    )
    assess = Capacity(
        name="drdemo_assess_amount",
        category=CATEGORY_DECISION,
        inputs=(DS_CLAIMED_AMOUNT, DS_DWELLING_LIMIT),
        outputs=(DS_ASSESSMENT,),
        implementation=_assess,
        description="the claimed amount and the limit in force -> what is payable",
        printable_phrase="assessing the claimed amount against the limit in force",
    )
    return [amount_reader, as_of_reader, lookup, assess]


def assessment_harness(*editions):
    """A no-store harness for the guards: the assessment layer over a KL
    holding whichever editions the caller names. Mirrors
    ``dr_routing.routing_harness`` — the pages driver has its own, because it
    also consolidates."""
    from mindsos_capacity import CapacityLayer
    from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
    from mindsos_intelligence.dispatch import L4Dispatcher
    from mindsos_intelligence.mm import MentalModel

    from decision_records_demo.dr_dump import (
        EDITION_2023, EDITION_2024, _build_kl, _Session,
    )

    session = _Session()
    layer = CapacityLayer()
    for ds in assessment_datastates():
        layer.register_datastate(ds, session=session, allow_new_realm=True)
    for cap in assessment_capacities():
        layer.register_capacity(cap, session=session)
    kl = _build_kl(*(editions or (EDITION_2023, EDITION_2024)))
    mm = MentalModel(session_id="drdemo-session", user_id="drdemo-user")
    dispatcher = L4Dispatcher(layer, session=session, kl=kl)
    writer = ChainArtifactWriter(mm, "drdemo-assessment")
    return mm, dispatcher, writer, writer.emit_request_run()


def assessment_plan() -> PlanResult:
    """One start, two levels of composition.

    The claim is the only start: the amount and the as-of date are READ from
    it, and the limit is looked up from the date.

    ⚠ **``finder`` IS DECLARED, and the default would be wrong here.**
    ``execution._select_finder`` derives the strategy from START ARITY — one
    start yields ``BFSFinder``, which wires a single chain and cannot fan
    in — so this leaf composed nothing at all until the key was added
    (*bfs_exhausted*, on a 3-hop route against ``max_depth=8``; the depth in
    that message is a red herring). ``dr_routing``'s map spec declares the
    same key for the same reason. **The arity rule is right and the surprise
    is real:** a leaf with ONE start and a MULTI-INPUT decision is a shape
    the derivation cannot see, because arity describes the entry point and
    the fan-in happens downstream of it.

    The fallback this docstring used to name — seed the as-of date as a
    second start and drop its reader — is NOT taken: it was written against
    the wrong diagnosis, and it would have cost the page its *"As of what
    date is this claim assessed?"* line to work around a missing keyword.
    """
    return PlanResult(
        plan_ref="plan:drdemo-assessment",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mLeaf"],
        pipeline_refs={"mLeaf": "pLeaf"},
        leaf_targets={"mLeaf": {
            "start_datastate": DS_ASSESSED_CLAIM,
            "target_datastate": DS_ASSESSMENT,
            "finder": "conjunction",
        }},
    )
