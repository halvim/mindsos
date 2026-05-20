"""Phase 15a — OewnImporter parser + builder + smoke tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from mindsos_core import Metagraph
from mindsos_admin import ImportResult, OewnImporter, bootstrap_global
from mindsos_admin.importers.oewn import SOURCE_NAME, _parse_oewn


FIXTURE = Path(__file__).parent / "fixtures" / "oewn_synth.xml"


def test_fixture_exists() -> None:
    assert FIXTURE.exists(), f"synthetic fixture missing: {FIXTURE}"


def test_parser_yields_expected_synsets() -> None:
    parsed = _parse_oewn(FIXTURE)
    # 4 synsets in fixture: dog-mammal, cat-mammal, mammal, dog-person.
    assert len(parsed.synsets) == 4
    # 3 distinct lemmas: dog, cat, mammal.
    assert len(parsed.lemmas) == 3
    # 4 senses: s-dog-1, s-dog-2, s-cat-1, s-mammal-1.
    assert len(parsed.senses) == 4


def test_parser_yields_expected_relations() -> None:
    parsed = _parse_oewn(FIXTURE)
    # Synset relations: dog→mammal (hypernym), cat→mammal (hypernym),
    # mammal→dog (hyponym), mammal→cat (hyponym). 4 total.
    assert len(parsed.synset_relations) == 4
    # Sense relations: s-dog-1 antonym s-cat-1. 1 total.
    assert len(parsed.sense_relations) == 1


def test_target_roles_attribute() -> None:
    assert OewnImporter.target_roles == ("lexicon",)


def test_importer_smoke_against_synthetic_fixture() -> None:
    mg = bootstrap_global(importers=())
    importer = OewnImporter(source=FIXTURE, version="synth-test")
    result = importer.run(mg)

    assert isinstance(result, ImportResult)
    assert result.role == "lexicon"
    assert result.version == "synth-test"
    assert result.source == SOURCE_NAME
    assert result.stats["synsets"] == 4
    assert result.stats["lemmas"] == 3
    assert result.stats["senses"] == 4
    assert result.stats["has_sense_edges"] == 4
    assert result.stats["in_synset_edges"] == 4
    assert result.stats["synset_relations"] == 4
    assert result.stats["sense_relations"] == 1


def test_run_writes_only_to_lexicon_role_graph() -> None:
    mg = bootstrap_global(importers=())
    OewnImporter(source=FIXTURE).run(mg)

    ontology = next(g for g in mg.graphs.values() if g.role == "ontology")
    lexicon = next(g for g in mg.graphs.values() if g.role == "lexicon")
    concepts = next(g for g in mg.graphs.values() if g.role == "concepts")

    assert len(lexicon.nodes) > 0
    assert len(ontology.nodes) == 0
    assert len(concepts.nodes) == 0


def test_auto_ensure_role_graph_on_direct_call() -> None:
    mg = Metagraph(name="raw")
    OewnImporter(source=FIXTURE).run(mg)
    assert any(g.role == "lexicon" for g in mg.graphs.values())


def test_missing_source_raises() -> None:
    importer = OewnImporter(source=None)
    mg = bootstrap_global(importers=())
    with pytest.raises(ValueError, match="source must be supplied"):
        importer.run(mg)
