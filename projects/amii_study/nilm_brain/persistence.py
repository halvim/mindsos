"""Durable persistence for nilm's LEARNED PARAMETERS — the taught appliance
library + its signature normalizer + match cutoff.

These are learned *parameters* (references/weights fit off data), not learned
*pipelines* (recipe structure — persisted separately by ``learn_pipeline``).
Core ships no ``learn_parameter`` writer (only ``learn_pipeline``), so — as a
CONSUMER — nilm writes/reads the shipped ``learned-parameters`` Local role
itself, exactly the way ``learn_pipeline`` uses ``learned-pipelines``. A core
``learn_parameter``/``iter_local_parameters`` helper is the right long-term
home — CR out.

Discipline (mirrors ADR-0203 / ``learn_pipeline``): APPEND-ONLY, latest-wins.
Each persist appends one ``LearnedParameter`` node stamped with the next
``taught_seq``; the reader returns the max-ordinal nilm node. Appliance state
MUTATES as you teach (the library grows; norm/cutoff refit), so — unlike the
composed pipelines — there is NO persist-once guard: every save snapshots the
current Solver state.

The three params bundle into ONE node value (co-fit: the cutoff and normalizer
are meaningless without the library they were tuned on). Values are plain
lists/floats/str straight off the capacity bodies (``.tolist()`` there) —
JSON-clean, no numpy. A non-finite cutoff (the accept-all default, before any
fit) is refused rather than persisted, mirroring ``learn_pipeline``'s
round-trip guard.

nilm's nodes carry NO ``reactivation_key``, so core's boot-time reactivation
walk (``reactivate_from_descriptors``) skips them — they ride the shared role
without being mistaken for re-activatable capacities. Read-back is nilm's own
job (below), done explicitly at boot.

Contamination rule: the library vectors ARE capacity-extracted learned
references, so persisting them is sanctioned; throwaway numpy probe/eval
results are never persisted.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mindsos_knowledge.identifiers import (
    ROLE_LEARNED_PARAMETERS,
    learned_parameter_iri,
)
from mindsos_knowledge.schemas.learned_parameters import NODE_LEARNED_PARAMETER

#: this brain's kind tag inside the shared learned-parameters role.
KIND = "nilm.appliance_state"
_VERSION = "v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _role_graph(kl: Any, user: str):
    """The user's Local ``learned-parameters`` role-graph (lazy-ensured)."""
    mg = kl.local_metagraph(user)  # ensures the 5 Local roles incl. learned-parameters
    for g in mg.graphs.values():
        if getattr(g, "role", None) == ROLE_LEARNED_PARAMETERS:
            return g
    return None


def _nilm_nodes(g) -> List[Any]:
    """nilm's appliance-state nodes in the role-graph, taught_seq-ascending."""
    if g is None:
        return []
    ns = [n for n in g.nodes.values()
          if isinstance(n.value, dict) and n.value.get("kind") == KIND]
    ns.sort(key=lambda n: int((n.properties or {}).get("taught_seq", 0)))
    return ns


def persist_appliance_state(kl: Any, user: str, solver: Any) -> Optional[Any]:
    """Append the Solver's current appliance state as one node; return it.

    Returns ``None`` if there is nothing worth persisting (empty library).
    Raises ``ValueError`` on a non-finite (unfit accept-all) cutoff — call
    ``fit_appliance()`` first. Best-effort by contract: callers guard it so a
    write failure never bricks the brain."""
    lib = list(getattr(solver, "appliance_library", []) or [])
    if not lib:
        return None
    cutoff = getattr(solver, "match_cutoff", None) or {}
    if not math.isfinite(float(cutoff.get("cutoff", float("inf")))):
        raise ValueError(
            "persist_appliance_state: match_cutoff is non-finite "
            "(unfit accept-all); call fit_appliance() before persisting."
        )
    value = {
        "kind": KIND,
        "library": lib,
        "signature_norm": getattr(solver, "signature_norm", None),
        "match_cutoff": cutoff,
    }
    g = _role_graph(kl, user)
    if g is None:  # pragma: no cover — lazy-ensure guarantees presence
        raise KeyError(
            f"persist_appliance_state: no {ROLE_LEARNED_PARAMETERS!r} role-graph "
            f"in Local for user {user!r}."
        )
    existing = _nilm_nodes(g)
    seq = (int((existing[-1].properties or {}).get("taught_seq", 0)) + 1
           if existing else 1)
    iri = learned_parameter_iri(_VERSION, parameter_id=f"{KIND}:{seq}")
    return g.add_node(
        value,
        NODE_LEARNED_PARAMETER,
        properties={"parameter_kind": KIND, "taught_seq": seq,
                    "recorded_at": _now_iso(), "storage_mode": "inline"},
        node_id=iri,
    )


def load_appliance_state(kl: Any, user: str) -> Optional[Dict[str, Any]]:
    """The latest persisted appliance state for ``user``, or ``None``.

    Returns ``{"library", "signature_norm", "match_cutoff"}`` from the
    max-``taught_seq`` nilm node — the last snapshot saved."""
    nodes = _nilm_nodes(_role_graph(kl, user))
    if not nodes:
        return None
    v = nodes[-1].value
    return {"library": v.get("library", []),
            "signature_norm": v.get("signature_norm"),
            "match_cutoff": v.get("match_cutoff")}


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
