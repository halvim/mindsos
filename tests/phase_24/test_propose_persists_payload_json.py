"""payload_json is the authoritative restart-rehydration source (PB-Z21.1).

Per Z13(a) — propose's FalkorDB write is deferred to Phase 26; at v1,
the SQLite payload_json is the persistence layer for pending content.
Rehydration on CLI re-invocation rebuilds in-memory pending Metagraph
from these rows.
"""

from __future__ import annotations

import json

from mindsos_admin import (
    bootstrap_global,
    bootstrap_pending_global,
    propose_for_promotion,
    rehydrate_global_metagraphs,
    rehydrate_pending_global,
)


def test_payload_json_is_serialized_promotion_item(
    seeded_admin, admin_session_propose,
    pending_global_mg, atom_proposal_factory,
):
    """payload_json fully describes the candidate per PB-Z21.1."""
    proposal = atom_proposal_factory(
        node_type="Synset",
        value="dog.n.01",
        properties={"definition": "domestic dog"},
        target_role="lexicon",
    )
    result = propose_for_promotion(
        seeded_admin, session=admin_session_propose,
        proposal=proposal, pending_global_mg=pending_global_mg,
    )

    cur = seeded_admin.execute(
        "SELECT payload_json FROM pending_mutations WHERE mutation_id = ?",
        (result.mutation_ids[0],),
    )
    payload = json.loads(cur.fetchone()[0])
    assert payload["kind"] == "ATOM"
    assert "node_id" in payload
    assert payload["node"]["node_type"] == "Synset"
    assert payload["node"]["value"] == "dog.n.01"
    assert payload["node"]["properties"] == {"definition": "domestic dog"}
    assert payload["node"]["target_role"] == "lexicon"


def test_rehydrate_pending_rebuilds_in_memory_metagraph(
    seeded_admin, admin_session_propose,
    pending_global_mg, atom_proposal_factory,
):
    """rehydrate_pending_global rebuilds in-memory pending from SQLite."""
    # Propose three nodes.
    for value in ("Alpha", "Beta", "Gamma"):
        propose_for_promotion(
            seeded_admin, session=admin_session_propose,
            proposal=atom_proposal_factory(value=value, target_role="ontology"),
            pending_global_mg=pending_global_mg,
        )

    # Verify in-memory pending has 3 nodes.
    ontology_pending = next(
        g for g in pending_global_mg.graphs.values() if g.role == "ontology"
    )
    assert len(ontology_pending.nodes) == 3

    # Simulate CLI restart: build a fresh pending Metagraph + rehydrate.
    fresh_canonical = bootstrap_global(importers=())
    fresh_pending = bootstrap_pending_global(fresh_canonical)
    fresh_ontology = next(
        g for g in fresh_pending.graphs.values() if g.role == "ontology"
    )
    assert len(fresh_ontology.nodes) == 0  # starts empty

    added = rehydrate_pending_global(seeded_admin, fresh_pending)
    assert added == 3
    assert len(fresh_ontology.nodes) == 3
    # Same node_ids re-materialized.
    assert set(ontology_pending.nodes.keys()) == set(fresh_ontology.nodes.keys())


def test_rehydrate_global_metagraphs_combined(
    seeded_admin, admin_session_propose, admin_session_both,
    canonical_global_mg, pending_global_mg, atom_proposal_factory,
):
    """rehydrate_global_metagraphs rehydrates BOTH canonical + pending."""
    from mindsos_server.release import release_update

    # Propose A → SHIP.
    propose_for_promotion(
        seeded_admin, session=admin_session_propose,
        proposal=atom_proposal_factory(value="A"),
        pending_global_mg=pending_global_mg,
    )
    release_update(
        seeded_admin, session=admin_session_both,
        canonical_global_mg=canonical_global_mg,
        pending_global_mg=pending_global_mg,
    )
    # Propose B (unshipped).
    propose_for_promotion(
        seeded_admin, session=admin_session_propose,
        proposal=atom_proposal_factory(value="B"),
        pending_global_mg=pending_global_mg,
    )

    # Now simulate CLI restart: fresh metagraphs + rehydrate.
    fresh_canonical = bootstrap_global(importers=())
    fresh_pending = bootstrap_pending_global(fresh_canonical)
    canonical_added, pending_added = rehydrate_global_metagraphs(
        seeded_admin, fresh_canonical, fresh_pending,
    )
    assert canonical_added == 1  # A
    assert pending_added == 1  # B
