"""tests/_shared/cross_metagraph_fixture helper — RR-13."""

from __future__ import annotations

from tests._shared.cross_metagraph_fixture import (
    make_source_and_target_metagraphs,
)


def test_returns_two_distinct_metagraphs():
    source, target = make_source_and_target_metagraphs()
    assert source is not target
    assert source.metagraph_id != target.metagraph_id


def test_source_has_ontology_role_graph():
    source, _t = make_source_and_target_metagraphs()
    [g] = source.graphs.values()
    assert g.role == "ontology"
    assert "src-node-1" in g.nodes
    assert "src-node-2" in g.nodes


def test_target_has_lexicon_role_graph():
    _s, target = make_source_and_target_metagraphs()
    [g] = target.graphs.values()
    assert g.role == "lexicon"
    assert "tgt-node-1" in g.nodes
    assert "tgt-node-2" in g.nodes


def test_disjoint_identity_registries():
    source, target = make_source_and_target_metagraphs()
    # Source's nodes NOT registered in target's identity.
    assert source.identity.contains("src-node-1")
    assert not target.identity.contains("src-node-1")
    assert target.identity.contains("tgt-node-1")
    assert not source.identity.contains("tgt-node-1")


def test_deterministic_ids_for_test_predictability():
    """Test fixture stability — IDs do not change across invocations."""
    s1, t1 = make_source_and_target_metagraphs()
    s2, t2 = make_source_and_target_metagraphs()
    assert s1.metagraph_id == s2.metagraph_id == "mg-source-test"
    assert t1.metagraph_id == t2.metagraph_id == "mg-target-test"
