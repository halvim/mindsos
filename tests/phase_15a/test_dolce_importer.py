"""Phase 15a — DolceImporter parser + builder + smoke tests.

Per Phase 15a PB-3-i: tests run against synthetic-shape fixture at
``tests/phase_15a/fixtures/dolce_synth.owl``; real-dataset integration
is Phase 26's beat.

Per `feedback_dimension_table_cross_check.md` (B-13-T1 lock):
EXPECTED counts are derived from ``len(parser(fixture))`` output
during the Step-0 probe, NOT hand-tabulated. This module's
``EXPECTED_STATS`` was built by running the parser against the
fixture and capturing the output.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mindsos_core import Metagraph
from mindsos_admin import DolceImporter, ImportResult, bootstrap_global
from mindsos_admin.importers.dolce import SOURCE_NAME, _parse_dolce


FIXTURE = Path(__file__).parent / "fixtures" / "dolce_synth.owl"


# Derived from the synthetic fixture per Phase 15a PB-3-i +
# `feedback_dimension_table_cross_check.md`. Values captured from the
# parser's actual output during Step-0 probe — DO NOT hand-edit; update
# the fixture and re-derive instead.
EXPECTED_STATS = {
    "classes": 7,                              # Entity, PhysicalObject, AbstractObject, Event, Process, Action, PhysicalAction
    "individuals": 2,                          # alice, bob
    "object_properties": 3,                    # participatesIn, hasPart, properPart
    "data_properties": 2,                      # hasMass, hasName
    "annotation_properties": 1,                # authorNote
    "restrictions": 2,                         # 2 bnode restrictions on PhysicalObject (synthetic fragments)
    "datatypes": 1,                            # PositiveInt
    "subclass_of_edges": 4,                    # 4 class→class (bnode-restriction subclass edges filtered: _frag(bnode)=None)
    "subproperty_of_edges": 1,                 # properPart subPropertyOf hasPart
    "domain_edges": 2,                         # participatesIn, hasPart
    "range_edges": 2,                          # participatesIn, hasPart
    "disjoint_edges": 1,                       # PhysicalObject disjointWith AbstractObject
    "equivalent_edges": 2,                     # Process equivalentClass Action + participatesIn equivalentProperty hasPart
    "intersection_hyperedges": 1,              # PhysicalAction = PhysicalObject ⊓ Process
    "property_chain_hyperedges": 1,            # hasPart ∘ hasPart
    "all_disjoint_classes_hyperedges": 1,      # {Event, AbstractObject, PhysicalObject}
}


def test_fixture_exists() -> None:
    """The synthetic DOLCE fixture is reachable."""
    assert FIXTURE.exists(), f"synthetic fixture missing: {FIXTURE}"


def test_parser_yields_expected_nodes() -> None:
    """Parser counts match the fixture per dimension-table cross-check."""
    parsed = _parse_dolce(FIXTURE)
    assert len(parsed.classes) == 7  # 6 + PhysicalAction (intersection head)
    assert len(parsed.individuals) == 2
    assert len(parsed.object_properties) == 3
    assert len(parsed.data_properties) == 2
    assert len(parsed.annotation_properties) == 1
    assert len(parsed.datatypes) == 1
    assert len(parsed.restrictions) == 2


def test_parser_yields_expected_hyperedges() -> None:
    parsed = _parse_dolce(FIXTURE)
    assert len(parsed.intersection_of) == 1
    assert len(parsed.property_chain) == 1
    assert len(parsed.all_disjoint_classes) == 1


def test_target_roles_attribute() -> None:
    """PB-22: DolceImporter self-describes target_roles."""
    assert DolceImporter.target_roles == ("ontology",)


def test_importer_smoke_against_synthetic_fixture() -> None:
    """End-to-end: build mg → run importer → ontology populated."""
    mg = bootstrap_global(importers=())
    importer = DolceImporter(source=FIXTURE, version="synth-test")
    result = importer.run(mg)

    assert isinstance(result, ImportResult)
    assert result.role == "ontology"
    assert result.version == "synth-test"
    assert result.source == SOURCE_NAME
    # Per PB-3-i: stats must be deterministic against synthetic fixture.
    # Spot-check load-bearing keys.
    assert result.stats["individuals"] == 2
    assert result.stats["object_properties"] == 3
    assert result.stats["data_properties"] == 2
    assert result.stats["datatypes"] == 1
    assert result.stats["intersection_hyperedges"] == 1
    assert result.stats["property_chain_hyperedges"] == 1
    assert result.stats["all_disjoint_classes_hyperedges"] == 1


def test_run_writes_only_to_ontology_role_graph() -> None:
    """ADR-0044 boundary — DolceImporter never touches memories/capacity-state."""
    mg = bootstrap_global(importers=())
    importer = DolceImporter(source=FIXTURE)
    importer.run(mg)

    # Ontology role-graph populated; lexicon/concepts empty.
    ontology = next(g for g in mg.graphs.values() if g.role == "ontology")
    lexicon = next(g for g in mg.graphs.values() if g.role == "lexicon")
    concepts = next(g for g in mg.graphs.values() if g.role == "concepts")

    assert len(ontology.nodes) > 0
    assert len(lexicon.nodes) == 0
    assert len(concepts.nodes) == 0


def test_auto_ensure_role_graph_on_direct_call() -> None:
    """PB-14: direct caller without bootstrap_global still gets role-graph."""
    mg = Metagraph(name="raw")  # NO ensure_global_role_graph yet
    importer = DolceImporter(source=FIXTURE)
    result = importer.run(mg)
    assert result.role == "ontology"
    # ontology role-graph now exists (importer auto-ensured it).
    roles = {g.role for g in mg.graphs.values()}
    assert "ontology" in roles


def test_source_override_at_run_time() -> None:
    """source kwarg on run() overrides constructor source."""
    importer = DolceImporter(source=None)
    mg = bootstrap_global(importers=())
    result = importer.run(mg, source=FIXTURE)
    assert result.role == "ontology"


def test_missing_source_raises() -> None:
    """No constructor source + no run-source → ValueError."""
    importer = DolceImporter(source=None)
    mg = bootstrap_global(importers=())
    with pytest.raises(ValueError, match="source must be supplied"):
        importer.run(mg)
