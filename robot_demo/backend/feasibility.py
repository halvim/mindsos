"""DM-5 — the embodiment gate (Seam C feasibility; scenario §5.2).

The on-camera "I can't grab it" beat, made REAL: an arm refuses an item its
end-effector can't grasp, and the refusal flows through the **shipped v0
dont-know path** (no ``mindsos_*`` edit) → a real
``outcome_classification:"dont_know"`` Episode + a real ``blame``.

**Grounded mechanism (design-log §23, probed not assumed):**

* ``Orchestrator._simplified`` defaults ``False`` and ``brain.py`` never sets
  it, so ``run_lifecycle`` reaches the dont-know branch:
  ``sufficient = sufficient_predicate.evaluate(...)`` → if ``False`` and
  ``should_replan`` is ``"continue"`` (the v0 default) →
  ``phase_6.diagnose`` (blame) → ``task_run.status="failed"`` →
  ``consolidate(outcome_classification="dont_know")``.
* The lever is the **per-CL override** of ``predicate.sufficient`` (PB-NEW —
  NOT the module-global ``set_sufficient_result``, which is shared by all four
  brains in the one process and is concurrency-unsafe). The predicate body gets
  **no task context** (``state={}``), so the feasibility decision is computed
  in the arm's phase-1 ``map`` (which sees the dispatched item) and stashed on
  the brain; the overridden predicate just reports it. Safe because arms run
  ``max_workers=1`` (single-flight per arm).
* ``phase6.attribute_blame`` is overridden too so the rich, **sanitized**
  refusal reason rides ``blame.rationale`` (the shipped ``dont_know_reason`` is
  the hardcoded "INSUFFICIENT" — unused on the wire).

This module is the MindsOS-honest surface: a real ``validate.feasibility``
capacity that reads the brain's seeded embodiment bag (:mod:`seeds`) and
checks ``item.acceptable_grasps ∩ body.provides``. MuJoCo-free / sandbox-
testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, FrozenSet, Optional

from mindsos_capacity import Capacity
from mindsos_capacity.identifiers import capacity_iri, datastate_iri

from .seeds import read_local_embodiment

# ── item → the grasp affordances that can pick it up (scenario §2/§5.2) ──
#: Box = dual-graspable carrier (suction OR jaw); Sheet = suction-only cargo;
#: Tube = jaw-only cargo. The gate is satisfied when the body provides ANY
#: acceptable grasp.
ITEM_ACCEPTABLE_GRASPS: Dict[str, FrozenSet[str]] = {
    "box": frozenset({"grasp:suction", "grasp:jaw"}),
    "sheet": frozenset({"grasp:suction"}),
    "tube": frozenset({"grasp:jaw"}),
}

#: A body item-id (``box1``/``tube1``/``sheet1``/``box2``) → its kind. The sim
#: carries numbered bodies; the gate reasons over kinds.
def item_kind(item: Optional[str]) -> Optional[str]:
    """``"tube1"`` → ``"tube"``; unknown → ``None``."""
    if not item:
        return None
    low = str(item).lower()
    for kind in ITEM_ACCEPTABLE_GRASPS:
        if low.startswith(kind):
            return kind
    return None


# ── §4.0 DataState IRIs (DM-2 registered set; reuse the diag request shape) ──
DS_FEASIBILITY_REQUEST = datastate_iri("robot.diag_request")
DS_FEASIBILITY_REPORT = datastate_iri("robot.diag_report")

CAT_VALIDATE = "validate"


@dataclass(frozen=True)
class FeasibilityVerdict:
    """The gate result. ``reason`` is already behavior-level / sanitized — it
    rides ``blame.rationale`` to the wire, so it must not name affordance codes,
    capacities, or layer architecture (policy B)."""

    feasible: bool
    item: Optional[str]
    item_kind: Optional[str]
    reason: str

    @property
    def gated(self) -> bool:
        return not self.feasible


def check_feasibility(item: Optional[str], body_provides) -> FeasibilityVerdict:
    """Does this body provide a grasp that can pick this item up?

    ``body_provides``: the brain's embodiment ``provides`` list (e.g.
    ``["grasp:suction"]``). **Fail-open / conservative gate:** a refusal is only
    a *real embodiment verdict* — it fires only when we positively know BOTH the
    item's required grasp AND the body's provided grasps and they don't
    intersect. Missing the body model (no seeded embodiment) or an unrecognized
    item is **insufficient information, not infeasibility** → feasible, so a
    config gap can never masquerade as an honest "I can't" on camera."""
    provides = {str(p) for p in (body_provides or [])}
    kind = item_kind(item)
    if kind is None or not provides:
        return FeasibilityVerdict(True, item, kind, "")  # no info → don't gate
    acceptable = ITEM_ACCEPTABLE_GRASPS[kind]
    if acceptable & provides:
        return FeasibilityVerdict(True, item, kind, "")
    # Infeasible — name the behavior, not the affordance code (policy B).
    return FeasibilityVerdict(
        False, item, kind, f"blocked — this gripper can't grasp a {kind} (wrong gripper)"
    )


def feasibility_for_brain(kl: Any, device_id: str, item: Optional[str]) -> FeasibilityVerdict:
    """Read the brain's seeded embodiment bag and gate ``item`` against it.

    A body-less brain (manager) or a missing bag → infeasible/honest; only the
    embodied arms ever run a pick, so the gate is consulted only there."""
    bag = read_local_embodiment(kl, device_id) or {}
    return check_feasibility(item, bag.get("provides"))


# ── the real validate.feasibility capacity (graph-honest) ─────────────────
def feasibility_name(device_id: str) -> str:
    """The capacity short-name for a device (``a1.feasibility`` for the arms)."""
    if device_id == "arm1":
        return "a1.feasibility"
    if device_id == "arm2":
        return "a2.feasibility"
    return f"{device_id}.feasibility"


def feasibility_iri(device_id: str) -> str:
    """The full ``capacity:validate:<name>`` IRI for a device's gate."""
    return capacity_iri(CAT_VALIDATE, feasibility_name(device_id))


def make_feasibility_impl(kl: Any, device_id: str) -> Callable[..., dict]:
    """A ``validate.feasibility`` body: reads the embodiment bag + the item from
    its input and returns the verdict. Registered so the gate is a real L3
    capacity (``find_pipeline`` + the graph tab see it), not a side check."""

    def impl(context=None, **inputs):
        req = inputs.get(DS_FEASIBILITY_REQUEST) or {}
        item = req.get("item") if isinstance(req, dict) else None
        v = feasibility_for_brain(kl, device_id, item)
        return {
            DS_FEASIBILITY_REPORT: {
                "feasible": v.feasible,
                "item": v.item,
                "item_kind": v.item_kind,
                "reason": v.reason,
                "kind": "feasibility",
            }
        }

    return impl


def build_feasibility_capacity(kl: Any, device_id: str) -> Capacity:
    """The ``validate.feasibility`` declaration for an embodied brain."""
    return Capacity(
        name=feasibility_name(device_id),
        category=CAT_VALIDATE,
        inputs=(DS_FEASIBILITY_REQUEST,),
        outputs=(DS_FEASIBILITY_REPORT,),
        implementation=make_feasibility_impl(kl, device_id),
        description=f"DM-5 embodiment gate (feasibility) for {device_id}.",
    )


__all__ = [
    "ITEM_ACCEPTABLE_GRASPS",
    "item_kind",
    "FeasibilityVerdict",
    "check_feasibility",
    "feasibility_for_brain",
    "feasibility_name",
    "feasibility_iri",
    "make_feasibility_impl",
    "build_feasibility_capacity",
    "DS_FEASIBILITY_REQUEST",
    "DS_FEASIBILITY_REPORT",
    "CAT_VALIDATE",
]
