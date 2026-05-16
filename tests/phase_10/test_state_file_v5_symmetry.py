"""B-09-T4 — serializer + deserializer symmetric for v=5 soft-delete fields."""

from __future__ import annotations

import os
import tempfile

import pytest

from mindsos_core import SoftDeleteKind


@pytest.fixture
def state_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".mindsos").mkdir(exist_ok=True)
    return tmp_path


def test_graph_v5_round_trip(state_home) -> None:
    """Edge + HyperEdge soft-delete fields survive serialize → deserialize."""
    from mindsos_cli.commands.graph import _graph_to_state, _state_to_graph
    from tests._shared.soft_delete_fixture import make_metagraph_with_soft_delete

    mg, ids = make_metagraph_with_soft_delete()
    g = mg.graphs[ids["graph_ont"]]
    g.deprecate_edge(ids["edge"])
    g.dispute_edge(ids["edge"])
    g.deprecate_hyperedge(ids["hyperedge"])

    state = _graph_to_state(g, schema_name=None, metagraph_name=mg.name)
    restored_g, _, _ = _state_to_graph(state)

    e = restored_g.edges[ids["edge"]]
    assert e.deprecated_at is not None
    assert e.disputed_at is not None

    h = restored_g.hyperedges[ids["hyperedge"]]
    assert h.deprecated_at is not None


def test_p64_mirror_dirty_buckets_empty_after_deserialize(state_home) -> None:
    """P64 mirror — _soft_delete_dirty must be empty after state-file deserialize."""
    from mindsos_cli.commands.graph import _graph_to_state, _state_to_graph
    from tests._shared.soft_delete_fixture import make_metagraph_with_soft_delete

    mg, ids = make_metagraph_with_soft_delete()
    g = mg.graphs[ids["graph_ont"]]
    g.deprecate_edge(ids["edge"])
    state = _graph_to_state(g, schema_name=None, metagraph_name=mg.name)
    restored_g, _, _ = _state_to_graph(state)
    assert all(len(restored_g._soft_delete_dirty[k]) == 0 for k in restored_g._soft_delete_dirty)


def test_metagraph_v5_round_trip(state_home) -> None:
    """MetaEdge + MetaHyperEdge + XRef soft-delete fields survive round-trip."""
    from mindsos_cli import state as state_mod
    from mindsos_cli.commands.graph import _graph_to_state
    from mindsos_cli.commands.metagraph import _metagraph_to_state, _state_to_metagraph
    from tests._shared.soft_delete_fixture import make_metagraph_with_soft_delete
    from tests._shared.metagraph_equality import assert_metagraphs_equal

    mg, ids = make_metagraph_with_soft_delete()
    mg.deprecate_metaedge(ids["metaedge"])
    mg.dispute_metahyperedge(ids["metahyperedge"])
    mg.mark_xref_stale(ids["xref"])
    mg.deprecate_xref(ids["xref"])
    # Edge-side soft-delete on the contained graph too
    g_ont = mg.graphs[ids["graph_ont"]]
    g_ont.deprecate_edge(ids["edge"])

    for gname in ("ontology", "lexicon", "concepts"):
        g_obj = next(g for g in mg.graphs.values() if g.name == gname)
        state_mod.save_graph_state(gname, _graph_to_state(g_obj, schema_name=None, metagraph_name=mg.name))
    state_mod.save_metagraph_state(mg.name, _metagraph_to_state(mg))

    loaded = state_mod.load_metagraph_state(mg.name)
    mg_b = _state_to_metagraph(loaded)
    assert_metagraphs_equal(mg, mg_b)


def test_serialize_deserialize_serialize_byte_stable(state_home) -> None:
    """B-09-T4 — second serialization byte-equals first."""
    from mindsos_cli.commands.graph import _graph_to_state, _state_to_graph
    from tests._shared.soft_delete_fixture import make_metagraph_with_soft_delete

    mg, ids = make_metagraph_with_soft_delete()
    g = mg.graphs[ids["graph_ont"]]
    g.deprecate_edge(ids["edge"])
    s1 = _graph_to_state(g, schema_name=None, metagraph_name=mg.name)
    g2, _, _ = _state_to_graph(s1)
    s2 = _graph_to_state(g2, schema_name=None, metagraph_name=mg.name)
    assert s1 == s2
