"""Admin importer modules (Phase 15a + 15b).

Phase 15a (this phase): :class:`DolceImporter`, :class:`OewnImporter`,
:class:`FrameNetImporter` — three independent source importers writing
to ``ontology``, ``lexicon``, ``concepts`` Global role-graphs.

Phase 15b: :class:`AlignmentsImporter` — parametric writer to
``alignment:<role-a>:<role-b>`` pair-graphs in Global per ADR-0150
§amendment-1.

All importers satisfy :class:`mindsos_admin.ImporterProtocol`:

* ``target_roles: tuple[str, ...]`` class/instance attribute.
* ``run(mg: Metagraph) -> ImportResult`` method.
"""

from __future__ import annotations

from .dolce import DolceImporter
from .framenet import FrameNetImporter
from .oewn import OewnImporter

__all__ = [
    "DolceImporter",
    "OewnImporter",
    "FrameNetImporter",
]
