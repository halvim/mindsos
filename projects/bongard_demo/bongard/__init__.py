"""Bongard-LOGO solver demo — a standalone MindsOS instance.

Built ONLY on top of the pinned core (composition-lifecycle-s2-confirmed);
never edits ``mindsos_*`` (RULES §3). Milestone-1 perception runs fully
in-memory (a fresh ``CapacityLayer`` + a Local ``DuckSession``); FalkorDB
persistence is a milestone-2 (mint + restart) concern.

Design record: ``projects/bongard_demo/PLAN.md``.
"""

from __future__ import annotations

from .ontology import BONGARD_REALM, ONTOLOGY, register_ontology
from .harness import DuckSession, build_instance

__all__ = [
    "BONGARD_REALM",
    "ONTOLOGY",
    "register_ontology",
    "DuckSession",
    "build_instance",
]
