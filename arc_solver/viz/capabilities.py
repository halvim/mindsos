"""arc-viz communication capacities — DataStates, bodies, and registration.

`ingest_solve` adapts the solver's output DataStates (`arc.*`, plain dicts) into a
general, producer-agnostic **expressible record** (typed content blocks + an
outcome enum + a hard-encoded decision path, per ARC_VIZ_CONTRACT_SPEC.md §1/§7).
`express` finalizes that record into a **communication artifact** (blocks + a
templated NL summary in the solver's vocabulary — no free generation).

Code-independent of the solver: the `arc.*` IRIs are re-declared via
`datastate_iri` (a MindsOS-core function), NOT imported from `arc_solver.spike`.
"""

from __future__ import annotations

from typing import Any, List

from mindsos_capacity.capacity import Capacity
from mindsos_capacity.capacity_layer import CapacityLayer
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import capacity_iri, datastate_iri

# ── category (arbitrary string; lazily-created category graph, per dream.*) ──
CATEGORY_COMMUNICATION = "communication"

# ── DataStates arc-viz CONSUMES (the solver's outputs, by IRI — no import) ──
DS_PROFILE = datastate_iri("arc.profile")
DS_RULES = datastate_iri("arc.rules")
DS_SELECTION = datastate_iri("arc.selection")
DS_SOLVE = datastate_iri("arc.solve")
DS_ENCLOSED = datastate_iri("arc.enclosed")

# ── DataStates arc-viz PRODUCES (new `comm` realm) ──────────────────────────
DS_EXPRESSIBLE_RECORD = datastate_iri("comm.expressible_record")
DS_ARTIFACT = datastate_iri("comm.artifact")

# ── the solver's reasoning caps (hard-encoded decision path, v1 LOCKED §7) ──
_CAP_EMIT = capacity_iri("reasoning", "emit_candidates")
_CAP_SELECT = capacity_iri("reasoning", "select_rules")
_CAP_APPLY = capacity_iri("reasoning", "apply_solution")

# ── outcome enum (§2) ───────────────────────────────────────────────────────
OUTCOME_VERIFIED = "verified"
OUTCOME_SOLVED_UNVERIFIED = "solved_unverified"
OUTCOME_WRONG = "wrong"
OUTCOME_ABSTAINED = "abstained"
OUTCOME_INAPPLICABLE = "inapplicable"

ABSTAIN_TEXT = "I don't know how to solve this task"


def _outcome(selection, solve) -> str:
    if selection is None:
        return OUTCOME_ABSTAINED
    if solve is None:
        return OUTCOME_INAPPLICABLE
    matches = solve.get("matches_withheld")
    if matches is True:
        return OUTCOME_VERIFIED
    if matches is False:
        return OUTCOME_WRONG
    return OUTCOME_SOLVED_UNVERIFIED


def _decision_path() -> List[dict]:
    # v1 LOCKED: the solver's reasoning sequence, real IRIs + produced DataState.
    return [
        {"capability": _CAP_EMIT, "produced": DS_RULES},
        {"capability": _CAP_SELECT, "produced": DS_SELECTION},
        {"capability": _CAP_APPLY, "produced": DS_SOLVE},
    ]


def _blocks(profile, selection, solve, enclosed, outcome) -> List[dict]:
    """The presentation-agnostic content IR (§3), ordered for reading:
    train delta(s) -> rule -> test input -> answer -> outcome (-> note)."""
    blocks: List[dict] = []
    train = (profile or {}).get("train") or []
    enc_train = (enclosed or {}).get("train") or []
    for i, pair in enumerate(train):
        gin = (pair.get("input") or {}).get("cells")
        gout = (pair.get("output") or {}).get("cells")
        payload = {"in": gin, "out": gout, "label": f"train pair {i + 1}"}
        if i < len(enc_train) and enc_train[i]:
            payload["enclosed"] = enc_train[i]
        blocks.append({"kind": "grid_pair", "payload": payload})
    if selection is not None:
        blocks.append({"kind": "rule", "payload": {
            "text": selection.get("text"), "complete": selection.get("size") == 1}})
    test = (profile or {}).get("test") or []
    if test:
        tin = (test[0].get("input") or {}).get("cells")
        blocks.append({"kind": "grid_single", "payload": {"grid": tin, "label": "test input"}})
    if solve and solve.get("output") is not None:
        blocks.append({"kind": "grid_single", "payload": {
            "grid": solve.get("output"), "label": "produced answer"}})
    detail = ABSTAIN_TEXT if outcome == OUTCOME_ABSTAINED else outcome
    blocks.append({"kind": "outcome", "payload": {"value": outcome, "detail": detail}})
    if outcome == OUTCOME_ABSTAINED:
        blocks.append({"kind": "note", "payload": {
            "text": "No candidate rule set reproduces the demos."}})
    return blocks


def build_record(profile, rules, selection, solve, enclosed) -> dict:
    outcome = _outcome(selection, solve)
    claim = selection.get("text") if selection else ABSTAIN_TEXT
    return {
        "producer": "arc-solver",
        "subject": {"kind": "arc_task", "id": (profile or {}).get("task_id")},
        "outcome": outcome,
        "claim": claim,
        "decision_path": _decision_path(),
        "content": _blocks(profile, selection, solve, enclosed, outcome),
    }


def _summary(record) -> str:
    outcome, claim = record["outcome"], record["claim"]
    if outcome == OUTCOME_VERIFIED:
        return f"Solved by {claim}; answer matches the withheld test."
    if outcome == OUTCOME_SOLVED_UNVERIFIED:
        return f"Solved by {claim}."
    if outcome == OUTCOME_WRONG:
        return f"Applied {claim}, but the answer does not match the test."
    if outcome == OUTCOME_INAPPLICABLE:
        return f"Found a rule set ({claim}) but it did not apply to the test input."
    return f"{ABSTAIN_TEXT} — no rule set reproduces the demos."


def build_artifact(record) -> dict:
    return {
        "header": {"producer": record["producer"], "subject": record["subject"],
                   "outcome": record["outcome"]},
        "summary": _summary(record),
        "content": record["content"],
        "format_version": 1,
    }


# ── capacity bodies (**kw keyed by input DataState IRI -> {output IRI: value}) ──
def _ingest_solve(**kw: Any) -> dict:
    record = build_record(kw.get(DS_PROFILE), kw.get(DS_RULES), kw.get(DS_SELECTION),
                          kw.get(DS_SOLVE), kw.get(DS_ENCLOSED))
    return {DS_EXPRESSIBLE_RECORD: record}


def _express(**kw: Any) -> dict:
    return {DS_ARTIFACT: build_artifact(kw.get(DS_EXPRESSIBLE_RECORD))}


# ── declarations ────────────────────────────────────────────────────────────
def viz_capacities() -> List[Capacity]:
    return [
        Capacity(
            name="ingest_solve", category=CATEGORY_COMMUNICATION,
            inputs=(DS_PROFILE, DS_RULES, DS_SELECTION, DS_SOLVE, DS_ENCLOSED),
            outputs=(DS_EXPRESSIBLE_RECORD,), implementation=_ingest_solve,
            description="Adapt the arc solve outputs -> the general expressible record.",
        ),
        Capacity(
            name="express", category=CATEGORY_COMMUNICATION,
            inputs=(DS_EXPRESSIBLE_RECORD,),
            outputs=(DS_ARTIFACT,), implementation=_express,
            description="Finalize the expressible record -> a communication artifact.",
        ),
    ]


def _ds(name: str, desc: str) -> DataState:
    return DataState(name=name, shape=ShapeDescriptor.opaque(name),
                     description=desc, provenance_category=CATEGORY_COMMUNICATION)


def viz_datastates() -> List[DataState]:
    return [
        _ds("comm.expressible_record",
            "General, producer-agnostic record of what a producer did (blocks + outcome)."),
        _ds("comm.artifact",
            "Finalized communication artifact (ordered blocks + templated NL summary)."),
    ]


def arc_input_datastates() -> List[DataState]:
    """Opaque stubs for the solver output DataStates arc-viz consumes — ONLY for
    the standalone fixtures gate. The combined run gets the real ones from
    ``install_arc`` (same IRIs), so this is NOT called there."""
    return [_ds(n, f"(stub) {n}") for n in
            ("arc.profile", "arc.rules", "arc.selection", "arc.solve", "arc.enclosed")]


def install_viz(cl: CapacityLayer, session: Any = None) -> None:
    """Register the comm DataStates + the two viz caps. Assumes the ``arc.*``
    input DataStates are already registered (combined run: ``install_arc`` first)."""
    for datastate in viz_datastates():
        cl.register_datastate(datastate, allow_new_realm=True, session=session)
    for cap in viz_capacities():
        cl.register_capacity(cap, session=session)


def install_viz_standalone(cl: CapacityLayer, session: Any = None) -> None:
    """Fixtures gate: register the arc.* input stubs first, then the viz surface."""
    for datastate in arc_input_datastates():
        cl.register_datastate(datastate, allow_new_realm=True, session=session)
    install_viz(cl, session=session)
