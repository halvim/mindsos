"""Phase 15a — FrameNetImporter parser + builder + smoke tests.

Synthetic fixture only (Phase 15a PB-3-i — FrameNet 1.7 Berkeley
click-through blocks repo-checked-in real-data extracts).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mindsos_core import Metagraph
from mindsos_admin import FrameNetImporter, ImportResult, bootstrap_global
from mindsos_admin.importers.framenet import SOURCE_NAME, _parse_framenet


FIXTURE = Path(__file__).parent / "fixtures" / "framenet_synth.xml"


def test_fixture_exists() -> None:
    assert FIXTURE.exists(), f"synthetic fixture missing: {FIXTURE}"


def test_parser_yields_expected_frames() -> None:
    parsed = _parse_framenet(FIXTURE)
    # 3 frames in fixture: Motion, Self_motion, Cause_motion.
    assert len(parsed.frames) == 3
    # 6 FEs: 3 in Motion (Theme, Path, Goal), 2 in Self_motion
    # (Self_mover, Path), 1 in Cause_motion (Agent).
    assert len(parsed.frame_elements) == 6
    # 5 LUs: move/travel in Motion; walk/run in Self_motion; push in Cause_motion.
    assert len(parsed.lexical_units) == 5


def test_parser_yields_expected_relations() -> None:
    parsed = _parse_framenet(FIXTURE)
    # 2 frame relations: Inheritance (Motion → Self_motion),
    # Causative_of (Motion → Cause_motion).
    assert len(parsed.frame_relations) == 2
    # The Inheritance relation has 2 FERelation children.
    inheritance = next(r for r in parsed.frame_relations if r[2] == "Inheritance")
    assert len(inheritance[3]) == 2


def test_target_roles_attribute() -> None:
    assert FrameNetImporter.target_roles == ("concepts",)


def test_importer_smoke_against_synthetic_fixture() -> None:
    mg = bootstrap_global(importers=())
    importer = FrameNetImporter(source=FIXTURE, version="synth-test")
    result = importer.run(mg)

    assert isinstance(result, ImportResult)
    assert result.role == "concepts"
    assert result.version == "synth-test"
    assert result.source == SOURCE_NAME
    assert result.stats["frames"] == 3
    assert result.stats["frame_elements"] == 6
    assert result.stats["lexical_units"] == 5
    assert result.stats["has_fe_edges"] == 6
    assert result.stats["evokes_edges"] == 5
    assert result.stats["frame_relations"] == 2
    assert result.stats["fe_mappings_edges"] == 2


def test_run_writes_only_to_concepts_role_graph() -> None:
    mg = bootstrap_global(importers=())
    FrameNetImporter(source=FIXTURE).run(mg)

    ontology = next(g for g in mg.graphs.values() if g.role == "ontology")
    lexicon = next(g for g in mg.graphs.values() if g.role == "lexicon")
    concepts = next(g for g in mg.graphs.values() if g.role == "concepts")

    assert len(concepts.nodes) > 0
    assert len(ontology.nodes) == 0
    assert len(lexicon.nodes) == 0


def test_auto_ensure_role_graph_on_direct_call() -> None:
    mg = Metagraph(name="raw")
    FrameNetImporter(source=FIXTURE).run(mg)
    assert any(g.role == "concepts" for g in mg.graphs.values())


def test_missing_source_raises() -> None:
    importer = FrameNetImporter(source=None)
    mg = bootstrap_global(importers=())
    with pytest.raises(ValueError, match="source must be supplied"):
        importer.run(mg)
