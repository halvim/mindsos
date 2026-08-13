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
from typing import Dict, Optional

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
#: ``runstopped:`` / ``runmanifest:`` are here because both node types live IN
#: the per-run capacity graph and had no room at all: ``sub_mm_for_iri`` raised
#: ``KeyError`` on either. Instance IRIs keep the ``datastate:`` / ``capacity:``
#: prefix ONLY so this routing works (see ``identifiers`` §Instance-IRI
#: vocabulary), and the terminal node and the manifest each invented a new
#: top-level prefix without joining the table. Neither had met the router:
#: ``RunStopped`` is only written on a non-success, and the manifest was minted
#: one layer above ``execute_pipeline`` until now. Found by the routing guard
#: below going red the moment the manifest moved into the executor.
CAPACITY_PREFIXES = ("capacity:", "datastate:", "runstopped:", "runmanifest:")
INTELLIGENCE_PREFIXES = (
    "hintset:",
    "mappingresult:",
    "plan:",
    "milestone:",
    "pipeline:",
    "pipelinerun:",
    "requestrun:",
)


@dataclass
class MMRoot:
    """Thin root — pointers only (D-B10)."""

    request_run_ref: Optional[str] = None
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

        # Fork independence (ADR-0201 / CR#4 Slice 1). ``copy.deepcopy``
        # preserves ids verbatim, so the clone would collide with the origin
        # (same metagraph_id / graph_id / identity entries) and its XRefs
        # would resolve back to the origin's metagraphs. Regenerate each
        # sub-MM's own ids (core) + reid its L1 instances (mindsos_instances),
        # accumulating one merged {old -> new} map, then fix cross-sub-MM XRef
        # targets so the fork's provenance links point within the fork.
        sub_mms = (clone.knowledge_mm, clone.capacity_mm, clone.intelligence_mm)
        id_map: Dict[str, str] = {}
        for sub in sub_mms:
            sub_map = sub.regenerate_ids()
            registry = getattr(sub, "element_registry", None)
            if registry is not None:
                registry.remap_ids(sub_map)
            id_map.update(sub_map)
        for sub in sub_mms:
            sub.remap_xref_targets(id_map)
        return clone


__all__ = [
    "MentalModel",
    "MMRoot",
    "KNOWLEDGE_PREFIXES",
    "CAPACITY_PREFIXES",
    "INTELLIGENCE_PREFIXES",
]
