"""LifecyclePhase 6 — failure diagnosis dispatch (D13 / ADR-0174).

On the failure path L4 dispatches the L3 ``phase6.attribute_blame``
capacity, which returns a BlameVerdict locating blame at a chain level +
step. At Phase 47 the body is a v0 skeleton; the concrete cross-validation
body is unbuilt CORE work (ADR-0206; **CORE-C4R8** — blame descends the
reconciled abstraction ladder). ⚠ ADR-0206 also retires the ``plan_subtree``
chain level: the planning loop covers it.
"""

from __future__ import annotations

from mindsos_capacity.builtins.orchestration_v0 import DS_BLAME, DS_BLAME_INPUT
from mindsos_capacity.identifiers import CATEGORY_PHASE6, capacity_iri

from .chain_artifacts import BlameVerdict

ATTRIBUTE_BLAME_IRI = capacity_iri(CATEGORY_PHASE6, "attribute_blame")


def diagnose(dispatcher, outcome=None) -> BlameVerdict:
    result = dispatcher.dispatch(ATTRIBUTE_BLAME_IRI, {DS_BLAME_INPUT: outcome or {}})
    b = result.outputs[DS_BLAME]
    return BlameVerdict(
        chain_level=b["chain_level"],
        blame_score=b["blame_score"],
        rationale=b["rationale"],
        milestone_ref=b.get("milestone_ref"),
        capacity_step_ref=b.get("capacity_step_ref"),
    )


__all__ = ["diagnose", "ATTRIBUTE_BLAME_IRI"]
