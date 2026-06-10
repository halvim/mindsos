"""Phase 15a — dimensional snapshot per `feedback_dimension_table_cross_check.md`.

EXPECTED counts derived from `len(parser(fixture))` output during
Step-0 probe, NOT hand-tabulated. This module's tables were built by
running each parser against its synthetic fixture and capturing the
output.

Snapshot covers:
* per-importer parser-output dimensions (synset count, frame count, etc.)
* per-importer builder-output dimensions (graph node/edge/hyperedge counts)
* `bootstrap_global` shape — 6 named Global role-graphs
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mindsos_admin import (
    DolceImporter,
    FrameNetImporter,
    OewnImporter,
    bootstrap_global,
)
from mindsos_admin.importers.dolce import _parse_dolce
from mindsos_admin.importers.framenet import _parse_framenet
from mindsos_admin.importers.oewn import _parse_oewn


FIXTURE_DIR = Path(__file__).parent / "fixtures"

DOLCE_FIXTURE = FIXTURE_DIR / "dolce_synth.owl"
OEWN_FIXTURE = FIXTURE_DIR / "oewn_synth.xml"
FRAMENET_FIXTURE = FIXTURE_DIR / "framenet_synth.xml"


# ── Parser-output dimensions ───────────────────────────────────────────


def test_dolce_parser_dimensions() -> None:
    parsed = _parse_dolce(DOLCE_FIXTURE)
    # Step-0 probe yielded:
    assert len(parsed.classes) == 7
    assert len(parsed.individuals) == 2
    assert len(parsed.object_properties) == 3
    assert len(parsed.data_properties) == 2
    assert len(parsed.annotation_properties) == 1
    assert len(parsed.restrictions) == 2
    assert len(parsed.datatypes) == 1


def test_oewn_parser_dimensions() -> None:
    parsed = _parse_oewn(OEWN_FIXTURE)
    assert len(parsed.synsets) == 4
    assert len(parsed.lemmas) == 3
    assert len(parsed.senses) == 4
    assert len(parsed.synset_relations) == 4
    assert len(parsed.sense_relations) == 1


def test_framenet_parser_dimensions() -> None:
    parsed = _parse_framenet(FRAMENET_FIXTURE)
    assert len(parsed.frames) == 3
    assert len(parsed.frame_elements) == 6
    assert len(parsed.lexical_units) == 5
    assert len(parsed.frame_relations) == 2


# ── Builder-output dimensions ──────────────────────────────────────────


def test_dolce_builder_dimensions() -> None:
    mg = bootstrap_global(importers=())
    DolceImporter(source=DOLCE_FIXTURE).run(mg)
    ontology = next(g for g in mg.graphs.values() if g.role == "ontology")
    # 7 classes + 2 individuals + 3 obj props + 2 data props + 1 ann
    # prop + 2 restrictions + 1 datatype = 18 nodes
    assert len(ontology.nodes) == 18


def test_oewn_builder_dimensions() -> None:
    mg = bootstrap_global(importers=())
    OewnImporter(source=OEWN_FIXTURE).run(mg)
    lexicon = next(g for g in mg.graphs.values() if g.role == "lexicon")
    # 4 synsets + 3 lemmas + 4 senses = 11 nodes
    assert len(lexicon.nodes) == 11


def test_framenet_builder_dimensions() -> None:
    mg = bootstrap_global(importers=())
    FrameNetImporter(source=FRAMENET_FIXTURE).run(mg)
    concepts = next(g for g in mg.graphs.values() if g.role == "concepts")
    # 3 frames + 6 FEs + 5 LUs = 14 nodes
    assert len(concepts.nodes) == 14


# ── bootstrap_global shape ─────────────────────────────────────────────


def test_bootstrap_global_six_role_graphs() -> None:
    """PB-21: bootstrap_global([]) ensures all Global named role-graphs
    (10 since Phase 50 ADR-0150 §am-6)."""
    mg = bootstrap_global(importers=())
    assert len(mg.graphs) == 10


def test_bootstrap_global_three_importer_combined_shape() -> None:
    """3-importer end-to-end: 10 role-graphs; 3 of them populated."""
    mg = bootstrap_global(importers=[
        DolceImporter(source=DOLCE_FIXTURE),
        OewnImporter(source=OEWN_FIXTURE),
        FrameNetImporter(source=FRAMENET_FIXTURE),
    ])
    assert len(mg.graphs) == 10
    populated_roles = {
        g.role for g in mg.graphs.values() if len(g.nodes) > 0
    }
    assert populated_roles == {"ontology", "lexicon", "concepts"}
