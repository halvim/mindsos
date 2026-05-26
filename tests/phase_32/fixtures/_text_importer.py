"""Phase 32 minimal text-realm fixture importer — 1 Frame node into `concepts`.

Per Phase 32 R0-PB-2 (c) + R1-PB-5: implements the
``ImporterProtocol`` (``target_roles`` + ``run``) so the integration
scenario substep 1c can populate canonical Global content via the
same pattern as production importers (DolceImporter / OewnImporter /
FrameNetImporter), without the heavyweight cost of the real ones.

Single-node payload — sufficient to prove KL bootstrap + import
co-resides with L3 invocation; substrate-co-residency is the only
property tested.

Schema constraint (B-26b-T2): ``concepts`` role uses FrameNet-shaped
schema; node_type MUST be ``Frame`` / ``FrameElement`` / ``LexicalUnit``
/ ``SemanticType``. ``Frame`` chosen here (minimal required schema).
"""

from __future__ import annotations

from mindsos_core import Metagraph
from mindsos_knowledge.bootstrap import ensure_global_role_graph
from mindsos_knowledge.identifiers import ROLE_CONCEPTS


class TextFixtureImporter:
    """Phase 32 scenario fixture importer — 1 Frame row into `concepts`.

    Naming per R2-PB-6 (a): ``_text_importer.py`` + class
    ``TextFixtureImporter`` describes role (text-realm) not test-
    machinery. Underscore prefix avoids pytest auto-collection
    (B-26b-T3 class).
    """

    target_roles: tuple[str, ...] = (ROLE_CONCEPTS,)

    def __init__(self) -> None:
        # No sibling source file — Phase 32 ships a single hardcoded
        # node payload (decoupled from 26b's TSV fixture; integration
        # is only proving co-residency, not import-shape parity).
        pass

    def run(self, metagraph: Metagraph) -> None:
        """Add one Frame node into the `concepts` role-graph."""
        ensure_global_role_graph(metagraph, ROLE_CONCEPTS)
        graph = next(
            g for g in metagraph.graphs.values() if g.role == ROLE_CONCEPTS
        )
        graph.add_node(
            "phase32_fixture_frame",
            "Frame",
            properties={},
        )
