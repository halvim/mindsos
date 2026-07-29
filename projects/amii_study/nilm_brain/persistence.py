"""Durable persistence for nilm's learned appliance state — the taught library
+ its signature normalizer + match cutoff.

Routed through the core learned-parameters family (CR merged, PR #94): the WRITE
is the L3 capacity ``capacity:learning-methods:learn_parameter`` (invoked via
``cl.invoke``, which auto-injects the pre-authorized ``writeable`` capability for
write-capacities when the CapacityLayer carries a ``kl``); the READ is core's
``read_learned_parameter_snapshot`` L4 plumbing (deliberately NOT a capacity —
it builds the context capacities run inside). nilm no longer hand-writes the
Local role-graph.

The three params bundle into ONE node value (co-fit: cutoff + normalizer are
meaningless without the library they were tuned on), addressed by the core
``(parameter_set, target)`` key. Discipline is the capacity's own:
OVERWRITE-IN-PLACE (latest-wins) — a re-teach replaces the node; no version
history (review decision). A non-finite cutoff (the accept-all default, before
any fit) is refused at the call site rather than persisted (the capacity has no
such guard). Values are plain lists/floats/str straight off the capacity bodies
(``.tolist()`` there) — JSON-clean, no numpy.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional

from mindsos_capacity import capacity_iri
from mindsos_capacity.identifiers import CATEGORY_LEARNING_METHODS
from mindsos_capacity.builtins.learn_parameter import DS_LEARNED_PARAMETER_WRITE
from mindsos_knowledge.learned_parameters_snapshot import (
    read_learned_parameter_snapshot,
    get_parameter,
)

#: (parameter_set, target) address for nilm's bundled appliance-state node in the
#: shared Local learned-parameters role.
PARAMETER_SET = "nilm.appliance_state"
TARGET = "appliance_state"

_LEARN_PARAMETER_IRI = capacity_iri(CATEGORY_LEARNING_METHODS, "learn_parameter")


def persist_appliance_state(cl: Any, session: Any, solver: Any) -> Optional[Any]:
    """Snapshot the Solver's current appliance state to the user's Local
    learned-parameters role via the core ``learn_parameter`` capacity.

    Returns the write outcome (truthy) on success, or ``None`` when there is
    nothing worth persisting (empty library). Raises ``ValueError`` on a
    non-finite (unfit accept-all) cutoff — call ``fit_appliance()`` first.
    Requires a ``cl`` whose CapacityLayer carries a ``kl`` (boot_brain does)."""
    lib = list(getattr(solver, "appliance_library", []) or [])
    if not lib:
        return None
    cutoff = getattr(solver, "match_cutoff", None) or {}
    if not math.isfinite(float(cutoff.get("cutoff", float("inf")))):
        raise ValueError(
            "persist_appliance_state: match_cutoff is non-finite "
            "(unfit accept-all); call fit_appliance() before persisting."
        )
    record = {
        "parameter_set": PARAMETER_SET,
        "target": TARGET,
        "value": {
            "library": lib,
            "signature_norm": getattr(solver, "signature_norm", None),
            "match_cutoff": cutoff,
        },
        "learned_by": getattr(session, "user_id", "nilm"),
        "reason": "teach_appliances",
    }
    r = cl.invoke(
        _LEARN_PARAMETER_IRI, {DS_LEARNED_PARAMETER_WRITE: record}, session=session
    )
    if not r.success:
        raise RuntimeError(
            f"persist_appliance_state: learn_parameter failed: {r.error!r}"
        )
    return getattr(r, "write_outcome", None) or True


def load_appliance_state(kl: Any, user: str) -> Optional[Dict[str, Any]]:
    """The latest persisted appliance state for ``user``, or ``None``.

    Reads the bundled node via the core snapshot reader (Local overrides Global
    per knob); returns ``{"library", "signature_norm", "match_cutoff"}``. nilm's
    pre-#94 hand-written nodes lack the capacity's key props, so the reader skips
    them — re-teach, not migrate."""
    bundle = get_parameter(
        read_learned_parameter_snapshot(kl, user), PARAMETER_SET, TARGET
    )
    if not bundle or not bundle.get("library"):
        return None
    return {
        "library": bundle.get("library", []),
        "signature_norm": bundle.get("signature_norm"),
        "match_cutoff": bundle.get("match_cutoff"),
    }


def apply_appliance_state(solver: Any, state: Optional[Dict[str, Any]]) -> bool:
    """Set the Solver's learned appliance params from a loaded state. Returns
    True if applied; no-op (False) on ``None``/empty — a fresh or ephemeral
    brain simply starts with an empty library, as before."""
    if not state or not state.get("library"):
        return False
    solver.appliance_library = list(state["library"])
    if state.get("signature_norm") is not None:
        solver.signature_norm = state["signature_norm"]
    if state.get("match_cutoff") is not None:
        solver.match_cutoff = state["match_cutoff"]
    return True
