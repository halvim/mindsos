"""DM-5 — the embodiment-gate wiring over the shipped v0 dont-know path.

Installs, per embodied brain, the two overrides + the real feasibility
capacity that turn a wrong-gripper request into a genuine
``outcome_classification:"dont_know"`` Episode with a populated ``blame`` —
**zero ``mindsos_*`` edits** (design-log §23, PB-3 / PB-NEW).

The decision is computed in the arm's phase-1 ``map`` (which sees the
dispatched item) by *invoking* the real ``validate.feasibility`` capacity, and
stashed on the brain. The overridden ``predicate.sufficient`` reports the
stash (the predicate body itself gets no task context — ``state={}``); the
overridden ``phase6.attribute_blame`` rides the **sanitized** refusal reason
on ``blame.rationale``. Single-flight per arm (``max_workers=1``) makes the
brain-level stash race-free.

See :mod:`feasibility` for the gate logic; this module is the L4-path glue.
"""

from __future__ import annotations

from typing import Any, Optional

from mindsos_capacity.builtins.orchestration_v0 import (
    DS_BLAME,
    DS_SUFFICIENT,
)
from mindsos_intelligence.phase_6 import ATTRIBUTE_BLAME_IRI
from mindsos_intelligence.sufficient_predicate import SUFFICIENT_IRI

from .comms import install_override
from .feasibility import (
    DS_FEASIBILITY_REPORT,
    DS_FEASIBILITY_REQUEST,
    FeasibilityVerdict,
    build_feasibility_capacity,
    feasibility_iri,
)

_GATE_ATTR = "_gate_verdict"


# ── per-brain stash (single-flight; arms are max_workers=1) ────────────
def set_gate_verdict(brain: Any, verdict: Optional[FeasibilityVerdict]) -> None:
    setattr(brain, _GATE_ATTR, verdict)


def get_gate_verdict(brain: Any) -> Optional[FeasibilityVerdict]:
    return getattr(brain, _GATE_ATTR, None)


def clear_gate_verdict(brain: Any) -> None:
    setattr(brain, _GATE_ATTR, None)


def gate_item(brain: Any, item: Optional[str]) -> FeasibilityVerdict:
    """Invoke the brain's real ``validate.feasibility`` capacity for ``item``,
    stash + return the verdict. Called from the arm's phase-1 ``map`` (nested
    ``cl.invoke`` inside a phase override — the established DM-4 pattern).

    On any invoke failure the gate **fails open** (feasible=True) so a wiring
    bug can never silently refuse a valid order — a refusal must be a real
    embodiment verdict, never an error."""
    try:
        res = brain.cl.invoke(
            feasibility_iri(brain.device_id),
            {DS_FEASIBILITY_REQUEST: {"item": item}},
            session=None,
        )
        rep = res.outputs.get(DS_FEASIBILITY_REPORT, {}) if res.success else {}
    except Exception:  # noqa — fail open; never refuse on a wiring error
        rep = {}
    verdict = FeasibilityVerdict(
        feasible=bool(rep.get("feasible", True)),
        item=rep.get("item", item),
        item_kind=rep.get("item_kind"),
        reason=str(rep.get("reason", "")),
    )
    set_gate_verdict(brain, verdict)
    return verdict


# ── the two v0 overrides (per-CL — NOT the global toggle, PB-NEW) ──────
def _make_sufficient_impl(brain: Any):
    def sufficient_impl(context=None, **inputs):
        v = get_gate_verdict(brain)
        return {DS_SUFFICIENT: True if v is None else v.feasible}

    return sufficient_impl


def _make_blame_impl(brain: Any):
    def blame_impl(context=None, **inputs):
        v = get_gate_verdict(brain)
        rationale = (
            v.reason if (v is not None and v.gated and v.reason)
            else "could not complete the task"
        )
        return {
            DS_BLAME: {
                "chain_level": "pipeline",
                "milestone_ref": None,
                "capacity_step_ref": None,
                "blame_score": 1.0,
                "rationale": rationale,
            }
        }

    return blame_impl


def install_arm_gate(brain: Any) -> str:
    """Register the brain's ``validate.feasibility`` capacity + install the
    ``predicate.sufficient`` / ``phase6.attribute_blame`` overrides on its CL.

    Returns the feasibility IRI (for tests / roster checks). Idempotent."""
    brain.cl.register_capacity(
        build_feasibility_capacity(brain.kl, brain.device_id),
        session=None,
        if_exists="upsert",
    )
    install_override(brain.cl, SUFFICIENT_IRI, _make_sufficient_impl(brain))
    install_override(brain.cl, ATTRIBUTE_BLAME_IRI, _make_blame_impl(brain))
    clear_gate_verdict(brain)
    return feasibility_iri(brain.device_id)


__all__ = [
    "set_gate_verdict",
    "get_gate_verdict",
    "clear_gate_verdict",
    "gate_item",
    "install_arm_gate",
]
