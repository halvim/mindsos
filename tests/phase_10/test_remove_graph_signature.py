"""Phase 10 M4 — remove_graph signature + return type."""

from __future__ import annotations

import inspect

from mindsos_core import Metagraph, RemovalImpact


def test_remove_graph_signature() -> None:
    sig = inspect.signature(Metagraph.remove_graph)
    params = sig.parameters
    assert "graph_id" in params
    assert params["cascade"].default is True   # P67
    assert params["force"].default is False    # M4
    assert params["cascade"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["force"].kind is inspect.Parameter.KEYWORD_ONLY


def test_remove_graph_returns_removal_impact_on_clean_path() -> None:
    from tests._shared.soft_delete_fixture import make_metagraph_with_soft_delete
    mg, ids = make_metagraph_with_soft_delete()
    # Clean removal of g_conc (nothing references it).
    impact = mg.remove_graph(ids["graph_conc"])
    # NB: g_conc IS a member of the metahyperedge in the fixture, so removal
    # cascades remove the metahyperedge. The MetaEdge between ont and lex is
    # NOT incident on g_conc → survives. Impact has no incoming refs → proceeds.
    assert isinstance(impact, RemovalImpact)
    assert impact.proceeded is True
    assert impact.incoming_xrefs == []
    assert impact.incoming_ref_properties == []
