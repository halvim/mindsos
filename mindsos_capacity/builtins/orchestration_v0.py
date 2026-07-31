"""Placeholder orchestration v0 catalog (Phase 47, ADR-0172 / PB-C).

The L4 orchestrator dispatches five L3 decision/scoring points whose real
bodies are unbuilt CORE work (RULES §8). Phase 47 ships placeholders so the
control paths (including the replan + dont-know branches) are exercised:

- ``decision.signal_to_tier``   → tier hint on the signal, else FOREGROUND
  (replaces the Phase-46 ``signal_triage`` passthrough stub).
- ``scoring.attention_score``   → cold-start constant from
  ``tiers.DEFAULT_TIER_SCORES`` (learned-parameters empty at Phase 47).
- ``decision.should_replan``    → configurable verdict (default continue).
- ``predicate.sufficient``      → configurable bool (default True).
- ``phase6.attribute_blame``    → fixed BlameVerdict shape.

``should_replan`` and ``sufficient`` verdicts are **test-configurable**
(``set_should_replan_decision`` / ``set_sufficient_result``) so the
ReplanRecord-emit + invalidate-at-and-below path and the dont-know path
are exercisable — constant stubs would dead-ship those paths. All carry
``placeholder=True``; install is opt-in; CORE-C4R1/C4R9 replaces.
"""

from __future__ import annotations

from typing import Any, List

from ..bootstrap import ensure_datastate_graph
from ..capacity import Capacity
from ..datastate import DataState, ShapeDescriptor
from ..exceptions import CapacityRegistrationError
from ..identifiers import (
    CATEGORY_DECISION,
    CATEGORY_PHASE6,
    CATEGORY_PREDICATE,
    CATEGORY_SCORING,
    capacity_iri,
    datastate_iri,
)
from ..tiers import TierEnum, default_score


DS_SIGNAL = datastate_iri("orchestration.signal")
DS_TIER = datastate_iri("orchestration.tier")
DS_SCORE_INPUT = datastate_iri("orchestration.score_input")
DS_SCORE = datastate_iri("orchestration.score")
DS_REPLAN_STATE = datastate_iri("orchestration.replan_state")
DS_REPLAN_VERDICT = datastate_iri("orchestration.replan_verdict")
DS_SUFFICIENT_STATE = datastate_iri("orchestration.sufficient_state")
DS_SUFFICIENT = datastate_iri("orchestration.sufficient")
DS_BLAME_INPUT = datastate_iri("orchestration.blame_input")
DS_BLAME = datastate_iri("orchestration.blame_verdict")


# ── Test-configurable verdict state (PB-C) ────────────────────────────

_DEFAULT_REPLAN_DECISION = "continue"
_DEFAULT_SUFFICIENT_RESULT = True

_should_replan_decision = _DEFAULT_REPLAN_DECISION
_sufficient_result = _DEFAULT_SUFFICIENT_RESULT


def set_should_replan_decision(decision: str) -> None:
    """Force ``decision.should_replan`` to return ``decision`` (one of
    ``"continue"`` / ``"replan"`` / ``"abort"``). Test-only."""
    global _should_replan_decision
    _should_replan_decision = decision


def set_sufficient_result(result: bool) -> None:
    """Force ``predicate.sufficient`` to return ``result``. Test-only."""
    global _sufficient_result
    _sufficient_result = result


def reset_v0_verdicts() -> None:
    """Restore default v0 verdicts (continue / True)."""
    global _should_replan_decision, _sufficient_result
    _should_replan_decision = _DEFAULT_REPLAN_DECISION
    _sufficient_result = _DEFAULT_SUFFICIENT_RESULT


# ── Classifier reused by signal-triage (replaces passthrough stub) ────


def classify_signal_to_tier(signal: Any) -> TierEnum:
    """v0 signal classifier: route a tier hint carried on the signal,
    else FOREGROUND. Replaces the Phase-46 passthrough stub."""
    tier = getattr(signal, "tier", None)
    if isinstance(tier, TierEnum):
        return tier
    if isinstance(signal, dict) and isinstance(signal.get("tier"), TierEnum):
        return signal["tier"]
    return TierEnum.FOREGROUND


def _signal_to_tier(**kwargs: Any) -> dict:
    return {DS_TIER: classify_signal_to_tier(kwargs.get(DS_SIGNAL))}


def _attention_score(**kwargs: Any) -> dict:
    inp = kwargs.get(DS_SCORE_INPUT)
    tier = inp if isinstance(inp, TierEnum) else None
    if tier is None and isinstance(inp, dict) and isinstance(inp.get("tier"), TierEnum):
        tier = inp["tier"]
    if tier is None:
        tier = TierEnum.FOREGROUND
    return {DS_SCORE: default_score(tier)}


def _should_replan(**kwargs: Any) -> dict:
    return {
        DS_REPLAN_VERDICT: {
            "decision": _should_replan_decision,
            "verified": True,
            "divergence": 0.0,
        }
    }


def _sufficient(**kwargs: Any) -> dict:
    return {DS_SUFFICIENT: _sufficient_result}


def _attribute_blame(**kwargs: Any) -> dict:
    return {
        DS_BLAME: {
            "chain_level": "pipeline",
            "milestone_ref": None,
            "capacity_step_ref": None,
            "blame_score": 1.0,
            "rationale": "v0 placeholder blame verdict",
        }
    }


def build_signal_to_tier() -> Capacity:
    return Capacity(
        name="signal_to_tier",
        category=CATEGORY_DECISION,
        inputs=(DS_SIGNAL,),
        outputs=(DS_TIER,),
        implementation=_signal_to_tier,
        description="v0 placeholder: tier hint or FOREGROUND.",
        placeholder=True,
    )


def build_attention_score() -> Capacity:
    return Capacity(
        name="attention_score",
        category=CATEGORY_SCORING,
        inputs=(DS_SCORE_INPUT,),
        outputs=(DS_SCORE,),
        implementation=_attention_score,
        description="v0 placeholder: cold-start constant per tier.",
        placeholder=True,
    )


def build_should_replan() -> Capacity:
    return Capacity(
        name="should_replan",
        category=CATEGORY_DECISION,
        inputs=(DS_REPLAN_STATE,),
        outputs=(DS_REPLAN_VERDICT,),
        implementation=_should_replan,
        description="v0 placeholder: configurable replan verdict.",
        placeholder=True,
    )


def build_sufficient() -> Capacity:
    return Capacity(
        name="sufficient",
        category=CATEGORY_PREDICATE,
        inputs=(DS_SUFFICIENT_STATE,),
        outputs=(DS_SUFFICIENT,),
        implementation=_sufficient,
        description="v0 placeholder: configurable sufficiency.",
        placeholder=True,
    )


def build_attribute_blame() -> Capacity:
    return Capacity(
        name="attribute_blame",
        category=CATEGORY_PHASE6,
        inputs=(DS_BLAME_INPUT,),
        outputs=(DS_BLAME,),
        implementation=_attribute_blame,
        description="v0 placeholder: fixed BlameVerdict.",
        placeholder=True,
    )


_DS_IRIS = (
    DS_SIGNAL,
    DS_TIER,
    DS_SCORE_INPUT,
    DS_SCORE,
    DS_REPLAN_STATE,
    DS_REPLAN_VERDICT,
    DS_SUFFICIENT_STATE,
    DS_SUFFICIENT,
    DS_BLAME_INPUT,
    DS_BLAME,
)
_CAP_IRIS = (
    capacity_iri(CATEGORY_DECISION, "signal_to_tier"),
    capacity_iri(CATEGORY_SCORING, "attention_score"),
    capacity_iri(CATEGORY_DECISION, "should_replan"),
    capacity_iri(CATEGORY_PREDICATE, "sufficient"),
    capacity_iri(CATEGORY_PHASE6, "attribute_blame"),
)


def install_orchestration_v0(capacity_layer) -> None:
    mg = capacity_layer.global_metagraph()
    cap_index = capacity_layer._capacity_index[mg.metagraph_id]
    ds_graph = ensure_datastate_graph(mg, strict=capacity_layer._strict)

    ds_present = {iri for iri in _DS_IRIS if iri in ds_graph.nodes}
    cap_present = {iri for iri in _CAP_IRIS if iri in cap_index}
    present_total = len(ds_present) + len(cap_present)

    if present_total == len(_DS_IRIS) + len(_CAP_IRIS):
        return
    if present_total > 0:
        raise CapacityRegistrationError(
            "install_orchestration_v0: partial install state detected — "
            f"datastates_present={sorted(ds_present)}, "
            f"capacities_present={sorted(cap_present)}"
        )
    for ds in _orchestration_datastates():
        capacity_layer.register_datastate(ds, allow_new_realm=True)
    capacity_layer.register_capacity(build_signal_to_tier())
    capacity_layer.register_capacity(build_attention_score())
    capacity_layer.register_capacity(build_should_replan())
    capacity_layer.register_capacity(build_sufficient())
    capacity_layer.register_capacity(build_attribute_blame())


def _orchestration_datastates() -> List[DataState]:
    names = {
        DS_SIGNAL: "orchestration.signal",
        DS_TIER: "orchestration.tier",
        DS_SCORE_INPUT: "orchestration.score_input",
        DS_SCORE: "orchestration.score",
        DS_REPLAN_STATE: "orchestration.replan_state",
        DS_REPLAN_VERDICT: "orchestration.replan_verdict",
        DS_SUFFICIENT_STATE: "orchestration.sufficient_state",
        DS_SUFFICIENT: "orchestration.sufficient",
        DS_BLAME_INPUT: "orchestration.blame_input",
        DS_BLAME: "orchestration.blame_verdict",
    }
    return [
        DataState(
            name=name,
            shape=ShapeDescriptor.opaque(name),
            description="v0 orchestration DataState.",
            provenance_category=CATEGORY_DECISION,
        )
        for name in names.values()
    ]


__all__ = [
    "DS_SIGNAL",
    "DS_TIER",
    "DS_SCORE_INPUT",
    "DS_SCORE",
    "DS_REPLAN_STATE",
    "DS_REPLAN_VERDICT",
    "DS_SUFFICIENT_STATE",
    "DS_SUFFICIENT",
    "DS_BLAME_INPUT",
    "DS_BLAME",
    "classify_signal_to_tier",
    "set_should_replan_decision",
    "set_sufficient_result",
    "reset_v0_verdicts",
    "build_signal_to_tier",
    "build_attention_score",
    "build_should_replan",
    "build_sufficient",
    "build_attribute_blame",
    "install_orchestration_v0",
]
