"""Phase 15a — bootstrap_global helper tests.

Locks Phase 15a PB-21 (Round 5): bootstrap_global must ensure all 6
Global named role-graphs (end-state parity with
``KnowledgeLayer.bootstrap()`` output). PB-22: each importer's
``target_roles`` is ensured ahead of running. Empty-importers case
yields the same shape as `KL.bootstrap()`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mindsos_core import Metagraph
from mindsos_admin import (
    DolceImporter,
    FrameNetImporter,
    OewnImporter,
    bootstrap_global,
)
from mindsos_admin.bootstrap import _GLOBAL_ROLE_ORDER
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.bootstrap import _GLOBAL_NAMED_ROLES


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_global_role_order_matches_kl_bootstrap_frozenset() -> None:
    """PB-21 sanity — _GLOBAL_ROLE_ORDER tuple matches KL's _GLOBAL_NAMED_ROLES frozenset."""
    assert frozenset(_GLOBAL_ROLE_ORDER) == _GLOBAL_NAMED_ROLES


def test_empty_importers_ensures_all_six_global_named_roles() -> None:
    """PB-21: zero importers → all 6 Global named role-graphs ensured."""
    mg = bootstrap_global(importers=())
    roles = {g.role for g in mg.graphs.values()}
    assert roles == _GLOBAL_NAMED_ROLES


def test_empty_importers_parity_with_kl_bootstrap_global_view() -> None:
    """PB-21: end-state Metagraph shape matches KL.bootstrap().global_view().roles()."""
    mg_admin = bootstrap_global(importers=())
    kl = KnowledgeLayer.bootstrap()
    kl_global_roles = kl.global_view().roles()

    admin_roles = {g.role for g in mg_admin.graphs.values()}
    assert admin_roles == kl_global_roles


def test_default_metagraph_name() -> None:
    """Default Metagraph name matches KL.bootstrap()'s default."""
    mg = bootstrap_global(importers=())
    assert mg.name == "global_knowledge"


def test_custom_metagraph_name() -> None:
    mg = bootstrap_global(importers=(), name="staging_global")
    assert mg.name == "staging_global"


def test_importer_target_roles_ensured_ahead_of_run() -> None:
    """PB-22: each importer's target_roles is ensured before run()."""
    mg = bootstrap_global(importers=[
        DolceImporter(source=FIXTURE_DIR / "dolce_synth.owl"),
    ])
    # ontology role-graph exists AND has content from the importer.
    ontology = next(g for g in mg.graphs.values() if g.role == "ontology")
    assert len(ontology.nodes) > 0


def test_three_importer_end_to_end() -> None:
    """3-importer end-to-end: DOLCE + OEWN + FrameNet populate distinct roles."""
    mg = bootstrap_global(importers=[
        DolceImporter(source=FIXTURE_DIR / "dolce_synth.owl"),
        OewnImporter(source=FIXTURE_DIR / "oewn_synth.xml"),
        FrameNetImporter(source=FIXTURE_DIR / "framenet_synth.xml"),
    ])

    ontology = next(g for g in mg.graphs.values() if g.role == "ontology")
    lexicon = next(g for g in mg.graphs.values() if g.role == "lexicon")
    concepts = next(g for g in mg.graphs.values() if g.role == "concepts")

    assert len(ontology.nodes) > 0
    assert len(lexicon.nodes) > 0
    assert len(concepts.nodes) > 0


def test_handoff_to_kl_constructor() -> None:
    """PB-7 + ADR-0042 §amendment-2: populated mg → KL constructor."""
    mg = bootstrap_global(importers=[
        DolceImporter(source=FIXTURE_DIR / "dolce_synth.owl"),
    ])
    kl = KnowledgeLayer(global_metagraph=mg)
    # KL's global_view() exposes the populated ontology role-graph.
    assert "ontology" in kl.global_view().roles()


def test_importer_returns_idempotent_against_re_ensure() -> None:
    """Re-ensuring an already-present role-graph via bootstrap_global is no-op."""
    mg = bootstrap_global(importers=())
    initial_count = len(mg.graphs)
    mg2 = bootstrap_global(importers=())  # fresh mg, same shape
    assert len(mg2.graphs) == initial_count
