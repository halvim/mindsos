"""dr_settlement — beat 3: the missing document, and what to go fetch.

Beat 2 refuses ONE EXPOSURE while its siblings route. Beat 3 refuses THE
CLAIM: nothing can be settled until a required document arrives, and the
Record names which one in the words the reader stored. Stated plainly
because the room deserves it: **the mechanism is the same in-band refusal
beat 2 uses** (ADR-0209 shape (a), a `structured_ingest_v0` reader refusing
`field_absent`). What differs is the scope and the consequence — one desk
cannot be chosen, versus this claim cannot proceed — not the substrate.

The version that would differ in substrate is the `NeedsInput` stop, where
the run halts and asks. It does not render today: `NeedsInput.missing` is a
DataState IRI, the renderer suppresses IRI-valued stop details (G6), and no
manifest field maps an arbitrary DataState IRI to its registered
description. That is a `capacity_mm_writer` change — core, `main`, a
`feat/*` lane — and it is filed rather than smuggled in here (RULES §3: a
demo never edits `mindsos_*`).

**Gate 4, checked in writing before anything registers (the restated
form):** no new capacity CATEGORY beyond `origin_v0.DECISION_SHAPED_CATEGORIES`
and no new `FAMILY_RULES` entry. The settlement decision registers in
`decision` — already in the frozenset, family dont-know shape `VERDICT`,
which is shape (a)'s refusal-as-verdict. The reader registers in `retrieval`
via the shipped structured-ingest factory. PASS.

**Sourcing (do-not-invent, plan §2.5):** the document is a *proof of loss* —
a named instrument in Canadian property claims, not a category this lane
made up — and the demo shows THAT a required document gates settlement,
never what any particular carrier requires.

    claim intake ──> proof-of-loss reader ──> the document, or a refusal
                              └──> the settlement decision ──> verdict

The reader refuses IN-BAND on an absent field: value ``None`` plus an origin
record naming the missing item in prose. The decision, seeing the ``None``,
returns the shape-(a) refusal verdict — ``decision: None`` plus the
structural marker, NO prose. The words come from the reader's record
(ADR-0209 D1). This module is demo code: it registers into its own layer and
never edits ``mindsos_*`` (RULES §3).
"""

from __future__ import annotations

from mindsos_capacity.builtins.origin_v0 import REFUSAL_FIELD_ABSENT
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

DS_CLAIM_INTAKE = datastate_iri("drdemo.claim_intake")
DS_PROOF_OF_LOSS = datastate_iri("drdemo.proof_of_loss")
DS_SETTLEMENT = datastate_iri("drdemo.settlement_verdict")

CAP_SETTLE = capacity_iri(CATEGORY_DECISION, "drdemo_settle_claim")

SOURCE_PHRASE = "the claim as filed"
SETTLEMENT_PAYABLE = "payable under the policy"

#: The demo-owned structural field naming WHICH INPUT determined a verdict —
#: the same field ``dr_routing`` and ``dr_render`` declare. It is spelled as a
#: literal in all THREE places by necessity, not by sloppiness: ``dr_render``
#: may import neither demo module (G1 allows stdlib + ``mindsos_core`` only),
#: so a shared constant is impossible. The three spellings are pinned EQUAL
#: test-side, exactly as the origin field names are — unpinned, a rename here
#: would silently stop the deciding fact rendering instead of failing, which is
#: the guard-that-cannot-go-red shape.
DETERMINED_BY = "determined_by"

#: The words THIS capacity uses for what it could not do. Coordination §100
#: Q2: the renderer may describe the Record's limits and never the case's
#: outcome, so *"cannot be settled"* is ours to say, not the page layout's.
#: Spelled as a literal here and in ``dr_render`` (G1 forbids the import);
#: pinned equal test-side.
REFUSAL_PHRASE = "refusal_phrase"

#: What this capacity says when the document it needs was not filed.
CANNOT_SETTLE = "cannot be settled"

#: Beat 3 — the claim arrives without the document settlement depends on.
CASE_MISSING_DOCUMENT = {
    "claimant": "E. Nakamura",
    "loss": "water damage, 2 June",
}


def _settle(context=None, **inputs):
    proof = inputs.get(DS_PROOF_OF_LOSS)
    if proof is None:
        # The reader refused; nothing can be settled. Structural marker
        # only — the words live in the reader's origin record.
        return {DS_SETTLEMENT: {"decision": None,
                                "refusal_reason": REFUSAL_FIELD_ABSENT,
                                REFUSAL_PHRASE: CANNOT_SETTLE}}
    # The filed document is what allows the claim to be settled, so it is
    # the determining input. Beat 3's shipped case never reaches here — it
    # refuses — but a refusal carries no determining input by design, and
    # the answering branch must not be the one that is untested.
    return {DS_SETTLEMENT: {"decision": SETTLEMENT_PAYABLE,
                            DETERMINED_BY: DS_PROOF_OF_LOSS}}


def settlement_datastates():
    proof_pair = structured_value_datastates(
        value_name="drdemo.proof_of_loss",
        value_elem="str",
        value_description="the proof of loss filed for this claim",
    )
    return [
        DataState(
            name="drdemo.claim_intake",
            shape=ShapeDescriptor.opaque("drdemo.claim_intake"),
            description="the claim as it arrived",
        ),
        DataState(
            name="drdemo.settlement_verdict",
            shape=ShapeDescriptor.opaque("drdemo.settlement_verdict"),
            description="whether this claim can be settled",
            refusal_capable=True,
        ),
    ] + proof_pair


def settlement_capacities():
    reader = build_structured_ingest_reader(
        name="drdemo_read_proof_of_loss",
        field="proof_of_loss",
        value_datastate_iri=DS_PROOF_OF_LOSS,
        value_elem="str",
        source_datastate_iri=DS_CLAIM_INTAKE,
        source_identity_phrase=SOURCE_PHRASE,
        value_phrase="a proof of loss",
        question="Which proof of loss was filed for this claim?",
    )
    settle = Capacity(
        name="drdemo_settle_claim",
        category=CATEGORY_DECISION,
        inputs=(DS_PROOF_OF_LOSS,),
        outputs=(DS_SETTLEMENT,),
        implementation=_settle,
        description="the filed document -> whether the claim can be settled",
        printable_phrase="settling the claim on what was filed",
    )
    return [reader, settle]


def settlement_plan() -> PlanResult:
    return PlanResult(
        plan_ref="plan:drdemo-settlement",
        root_milestone_ref="m0",
        leaf_milestone_refs=["mLeaf"],
        pipeline_refs={"mLeaf": "pLeaf"},
        leaf_targets={"mLeaf": {
            "start_datastate": DS_CLAIM_INTAKE,
            "target_datastate": DS_SETTLEMENT,
        }},
    )
