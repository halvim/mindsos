"""MindsOS Admin Layer — Phase 15a surface.

Admin operations package — the permanent home for code that mutates
L1/L2 state outside the L4→L3→L1 cognitive loop. Per ADR-0140
§amendment-1 (Phase 15a): admin operations live in ``mindsos_admin/``,
not ``mindsos_server/``. Server (when built) imports admin for HTTP
endpoint handlers; admin code is not server code.

Phase 15a scope (this phase ships):

* :class:`ImportResult` — frozen dataclass returned by every importer
  ``run()``. Fields: ``role``, ``version``, ``source``, ``imported_at``,
  ``stats``.
* :class:`ImporterProtocol` — structural protocol every importer
  satisfies. Per Phase 15a PB-22, importers self-describe their target
  role-graphs via the ``target_roles: tuple[str, ...]`` class/instance
  attribute.
* :func:`bootstrap_global` — module-level helper (per Phase 15a PB-13).
  Builds a populated Global :class:`~mindsos_core.Metagraph` from a
  sequence of importer instances. Per Phase 15a PB-21, the returned
  Metagraph has all 6 Global named role-graphs ensured (parity with
  :meth:`KnowledgeLayer.bootstrap`'s output), with 3 of them populated
  by importer content when ontology/lexicon/concepts importers are
  passed.
* :class:`DolceImporter` — DOLCE-DUL 4.1 → ``ontology`` role-graph.
* :class:`OewnImporter` — Open English WordNet 2024 → ``lexicon``
  role-graph.
* :class:`FrameNetImporter` — FrameNet 1.7 → ``concepts`` role-graph.

Phase 15b will add :class:`AlignmentsImporter` (alignment pair-graphs
in Global per ADR-0150 §amendment-1).

Phase 16 will add ``mindsos_admin.promotion`` (``propose_for_promotion``
machinery per ADR-0140 §amendment-1 §Decision §2 supersession; was
ADR-0140 §Decision §2 routing to ``mindsos_server/``).

ADRs honoured:

* ADR-0010 (Accepted) — layer isolation. ``mindsos_admin`` imports
  ``mindsos_knowledge`` + ``mindsos_core`` (downward); imports no
  ``mindsos_server`` module.
* ADR-0042 (Accepted) + §amendment-1 (Phase 14) + §amendment-2
  (Phase 15a) — third first-install sequence: importer-built Global
  → :class:`~mindsos_knowledge.KnowledgeLayer` constructor.
* ADR-0043 (Accepted) — KL stays in-memory only. Admin is permitted
  file-I/O (parser modules under ``mindsos_admin/importers/`` read
  OWL/XML datasets directly).
* ADR-0044 (Accepted) — memories Local-per-user. Admin importers
  write Global only; never touch ``memories`` or ``capacity-state``.
* ADR-0045 (Accepted) — per-role IRI builders. Importers consume
  Phase 12's :mod:`mindsos_knowledge.identifiers` 14-builder surface
  verbatim.
* ADR-0140 (Proposed) + §amendment-1 (Phase 15a) — server owns admin
  operations; §Decision §1+§2 superseded — admin permanent home is
  ``mindsos_admin/``, not ``mindsos_server/``. Phase 37 row in
  PHASE_MAP retired.
* ADR-0150 (Accepted) + §amendment-1 (Phase 14) — closed role-set;
  alignment Global-only at v1 (Phase 15b consumer).
"""

from __future__ import annotations

__version__ = "0.0.0+phase15a"

from .bootstrap import (
    ImporterProtocol,
    ImportResult,
    bootstrap_global,
)
from .importers import (
    DolceImporter,
    FrameNetImporter,
    OewnImporter,
)

__all__ = [
    "__version__",
    "ImporterProtocol",
    "ImportResult",
    "bootstrap_global",
    "DolceImporter",
    "OewnImporter",
    "FrameNetImporter",
]
