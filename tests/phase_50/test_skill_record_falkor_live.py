"""Phase 50 (SA-1) — install-record durability through FalkorDB (live).

The provenance half of the pass criterion, durable edition: the
``installed-skills`` record's structured ``value`` — the first
production consumer of ADR-0182 — survives a real persist → load
round-trip, and the bundle-tagged L2 content rides along with its
``installed_by`` provenance tag intact.

Uses the ``tests/_shared`` ``falkor_client`` fixture (per-test fresh
graph; skips without a sidecar).
"""

from __future__ import annotations

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture

pytestmark = pytest.mark.integration


def test_live_install_record_round_trip(falkor_client) -> None:  # noqa: F811
    from mindsos_capacity import CapacityLayer
    from mindsos_capacity.builtins.text import install_text_capacities
    from mindsos_core.persistence import MetagraphRepository
    from mindsos_core.reconstruction import MetagraphLoader
    from mindsos_knowledge import (
        KnowledgeLayer,
        ROLE_INSTALLED_SKILLS,
    )
    from mindsos_server.skills import install_skill, parse_manifest
    from tests.fixtures.skill_bundle_ref import MANIFEST_PATH

    kl = KnowledgeLayer.bootstrap()
    cl = CapacityLayer()
    install_text_capacities(cl)
    manifest = parse_manifest(MANIFEST_PATH)
    result = install_skill(manifest, kl=kl, cl=cl, current_phase=50)
    assert result.record is not None

    global_mg = kl.global_metagraph()
    MetagraphRepository(falkor_client).persist(global_mg)

    loader = MetagraphLoader(falkor_client)
    mid = loader.find_by_name(global_mg.name)
    assert mid is not None
    loaded = loader.load(mid)

    # Record graph + node survived; structured value decoded (ADR-0182).
    record_graph = next(
        g for g in loaded.graphs.values() if g.role == ROLE_INSTALLED_SKILLS
    )
    record = record_graph.nodes[result.record.iri]
    assert isinstance(record.value, dict)
    assert record.value["l3_capacities"] == [
        "capacity:perception:text.ref_shout"
    ]
    assert record.value["l4_slots"] == {
        "demo_slot": "ref-skill-opaque-l4-fill"
    }
    # Rule-5 flat lifts queryable without decoding.
    assert record.properties.get("bundle_name") == "ref-skill"
    assert record.properties.get("status") == "installed"
    assert "_value_json" not in record.properties

    # Bundle-tagged content + provenance tag round-tripped.
    concepts = next(
        g for g in loaded.graphs.values() if g.role == "concepts"
    )
    node = concepts.nodes["ref-skill-0.1.0:concept:shouting"]
    assert node.properties.get("installed_by") == "ref-skill@0.1.0"
