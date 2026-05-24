"""Phase 26b test ImporterProtocol — 10-row TSV into `concepts` role.

Per Phase 26b design log R3-PB-6 (c) + R5-F4 + R7-F3 (Phase 26a).
Implements the ``ImporterProtocol`` (``target_roles`` + ``run``) so the
scenario step 4 can populate canonical Global content via the same
pattern as production importers (DolceImporter / OewnImporter /
FrameNetImporter).

The sibling ``_test_importer_data.tsv`` is read at ``run`` time per
R3-PB-6 (c) — mirrors real importers reading source files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from mindsos_core import Metagraph
from mindsos_knowledge.bootstrap import ensure_global_role_graph
from mindsos_knowledge.identifiers import ROLE_CONCEPTS


class TestImporter:
    """Phase 26b scenario test importer — 10 rows into `concepts`."""

    target_roles: tuple[str, ...] = (ROLE_CONCEPTS,)

    def __init__(self, source: Optional[Path] = None) -> None:
        # Phase 15a precedent: ``source`` defaults to a sibling fixture
        # file when omitted.
        self._source = (
            source if source is not None
            else Path(__file__).parent / "_test_importer_data.tsv"
        )

    def run(self, metagraph: Metagraph) -> None:
        """Read the TSV + add 10 ConceptNode rows into `concepts` role."""
        ensure_global_role_graph(metagraph, ROLE_CONCEPTS)
        graph = next(
            g for g in metagraph.graphs.values() if g.role == ROLE_CONCEPTS
        )
        with open(self._source, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        # Skip header (first line); each subsequent row: node_id\tvalue\tproperties
        for line in lines[1:]:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            node_id, value, props_json = parts[0], parts[1], parts[2]
            properties = json.loads(props_json) if props_json.strip() else {}
            graph.add_node(
                value,
                "ConceptNode",
                properties=properties,
                node_id=node_id,
            )
