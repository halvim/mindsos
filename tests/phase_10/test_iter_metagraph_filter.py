"""Iterator filter on Metagraph (iter_metaedges / iter_metahyperedges / iter_xrefs)."""

from __future__ import annotations

from tests._shared.soft_delete_fixture import make_metagraph_with_soft_delete


def test_iter_metaedges_filter() -> None:
    mg, ids = make_metagraph_with_soft_delete()
    mg.deprecate_metaedge(ids["metaedge"])
    assert len(list(mg.iter_metaedges())) == 0
    assert len(list(mg.iter_metaedges(include_deprecated=True))) == 1


def test_iter_metahyperedges_filter() -> None:
    mg, ids = make_metagraph_with_soft_delete()
    mg.deprecate_metahyperedge(ids["metahyperedge"])
    assert len(list(mg.iter_metahyperedges())) == 0
    assert len(list(mg.iter_metahyperedges(include_deprecated=True))) == 1


def test_iter_xrefs_filter() -> None:
    mg, ids = make_metagraph_with_soft_delete()
    mg.deprecate_xref(ids["xref"])
    assert len(list(mg.iter_xrefs())) == 0
    assert len(list(mg.iter_xrefs(include_deprecated=True))) == 1


def test_iter_xrefs_target_stale_not_filtered() -> None:
    """ADR-0128 amendment-3: target_stale does NOT filter."""
    mg, ids = make_metagraph_with_soft_delete()
    mg.mark_xref_stale(ids["xref"])
    rows = list(mg.iter_xrefs())
    assert len(rows) == 1 and rows[0].target_stale is True


def test_iter_xrefs_and_composed_with_include_deprecated() -> None:
    """include_deprecated AND-composes with other predicates."""
    mg, ids = make_metagraph_with_soft_delete()
    mg.deprecate_xref(ids["xref"])
    src = mg.xrefs[ids["xref"]].source_id
    assert len(list(mg.iter_xrefs(source_id=src))) == 0
    assert len(list(mg.iter_xrefs(source_id=src, include_deprecated=True))) == 1
