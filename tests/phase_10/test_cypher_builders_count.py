"""M16 — 22 cypher builders ship in Phase 10."""

from __future__ import annotations

from mindsos_core.cypher import builders


PHASE_10_BUILDERS = [
    # 16 edge-side (4 ops × 4 element kinds)
    "build_set_edge_deprecated_at", "build_unset_edge_deprecated_at",
    "build_set_edge_disputed_at", "build_unset_edge_disputed_at",
    "build_set_hyperedge_deprecated_at", "build_unset_hyperedge_deprecated_at",
    "build_set_hyperedge_disputed_at", "build_unset_hyperedge_disputed_at",
    "build_set_metaedge_deprecated_at", "build_unset_metaedge_deprecated_at",
    "build_set_metaedge_disputed_at", "build_unset_metaedge_disputed_at",
    "build_set_metahyperedge_deprecated_at", "build_unset_metahyperedge_deprecated_at",
    "build_set_metahyperedge_disputed_at", "build_unset_metahyperedge_disputed_at",
    # 4 XRef
    "build_set_xref_target_stale", "build_unset_xref_target_stale",
    "build_set_xref_deprecated_at", "build_unset_xref_deprecated_at",
    # 2 impact-compute
    "build_query_incoming_xrefs_by_target",
    "build_query_intra_metagraph_ref_properties",
]


def test_all_22_builders_present() -> None:
    missing = [n for n in PHASE_10_BUILDERS if not hasattr(builders, n)]
    assert not missing, f"missing: {missing}"
    assert len(PHASE_10_BUILDERS) == 22


def test_builders_return_tuple_str_dict() -> None:
    sample = builders.build_set_edge_deprecated_at("g1", "e1", "2026-05-15T12:00:00+00:00")
    assert isinstance(sample, tuple)
    assert isinstance(sample[0], str)
    assert isinstance(sample[1], dict)


def test_edge_builder_cypher_shape() -> None:
    q, p = builders.build_set_edge_deprecated_at("g1", "e1", "ISO")
    assert "SET e.deprecated_at = $at" in q
    assert p == {"gid": "g1", "eid": "e1", "at": "ISO"}


def test_xref_target_stale_builder_emits_true() -> None:
    q, _ = builders.build_set_xref_target_stale("x1")
    assert "SET x.target_stale = true" in q


def test_metahyperedge_builder_labels_correctly() -> None:
    q, _ = builders.build_set_metahyperedge_deprecated_at("mg1", "mh1", "ISO")
    assert ":MetaHyperEdge" in q
    assert "metagraph_id" in q


def test_impact_query_scans_ref_prefix() -> None:
    q, p = builders.build_query_intra_metagraph_ref_properties("mg1", ["n1", "n2"])
    assert "STARTS WITH 'ref:'" in q
    assert p == {"mid": "mg1", "target_ids": ["n1", "n2"]}
