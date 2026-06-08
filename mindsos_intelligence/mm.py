"""Three-sub-MM container + thin root (ADR-0165 / Chat B D-B10/B11).

A Mental Model is a metagraph of three sub-metagraphs — knowledge-MM
(L2 instances), capacity-MM (L3 CapacityInstance/DataStateInstance with
produces/consumes edges), intelligence-MM (L4-authored chain artifacts) —
plus a thin root holding pointers only. L4 invariant: no shadow state
outside the MM. ``deep_copy`` produces the fresh independent MM a dream
re-executes against (ADR-0162).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional

from mindsos_core import Metagraph
import mindsos_instances as mi

from .rwlock import RWLock

KNOWLEDGE_PREFIXES = (
    "ontology:",
    "lexicon:",
    "concept:",
    "alignment:",
    "episodic:",
    "episode:",
    "memory:",
)
CAPACITY_PREFIXES = ("capacity:", "datastate:")
INTELLIGENCE_PREFIXES = (
    "hintset:",
    "mappingresult:",
    "plan:",
    "milestone:",
    "pipeline:",
    "pipelinerun:",
    "taskrun:",
)


@dataclass
class MMRoot:
    """Thin root — pointers only (D-B10)."""

    task_run_ref: Optional[str] = None
    problem_trace_ref: Optional[str] = None
    outcome_ref: Optional[str] = None


def _new_sub_mm(name: str) -> Metagraph:
    mg = Metagraph(name=name)
    mi.attach_registry(mg)
    return mg


class MentalModel:
    def __init__(self, *, session_id: str, user_id: str) -> None:
        self.session_id = session_id
        self.user_id = user_id
        self.knowledge_mm = _new_sub_mm("mm:knowledge")
        self.capacity_mm = _new_sub_mm("mm:capacity")
        self.intelligence_mm = _new_sub_mm("mm:intelligence")
        self.root = MMRoot()
        self.lock = RWLock()

    def sub_mm_for_iri(self, iri: str) -> Metagraph:
        if iri.startswith(KNOWLEDGE_PREFIXES):
            return self.knowledge_mm
        if iri.startswith(CAPACITY_PREFIXES):
            return self.capacity_mm
        if iri.startswith(INTELLIGENCE_PREFIXES):
            return self.intelligence_mm
        raise KeyError(f"no sub-MM owns IRI namespace for {iri!r}")

    def deep_copy(self) -> "MentalModel":
        clone = MentalModel.__new__(MentalModel)
        clone.session_id = self.session_id
        clone.user_id = self.user_id
        clone.knowledge_mm = copy.deepcopy(self.knowledge_mm)
        clone.capacity_mm = copy.deepcopy(self.capacity_mm)
        clone.intelligence_mm = copy.deepcopy(self.intelligence_mm)
        clone.root = copy.deepcopy(self.root)
        clone.lock = RWLock()
        return clone


__all__ = [
    "MentalModel",
    "MMRoot",
    "KNOWLEDGE_PREFIXES",
    "CAPACITY_PREFIXES",
    "INTELLIGENCE_PREFIXES",
]
