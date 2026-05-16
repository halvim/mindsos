"""Step 11 — loader signatures gain include_deprecated parameter (5 entry points)."""

from __future__ import annotations

import inspect

from mindsos_core.reconstruction.graph_loader import iter_load_graph, load_graph
from mindsos_core.reconstruction.metagraph_loader import (
    MetagraphLoader,
    load_metagraph,
)


def test_metagraph_loader_load_signature() -> None:
    assert "include_deprecated" in inspect.signature(MetagraphLoader.load).parameters


def test_metagraph_loader_refresh_signature() -> None:
    assert "include_deprecated" in inspect.signature(MetagraphLoader.refresh).parameters


def test_load_metagraph_signature() -> None:
    assert "include_deprecated" in inspect.signature(load_metagraph).parameters


def test_load_graph_signature() -> None:
    assert "include_deprecated" in inspect.signature(load_graph).parameters


def test_iter_load_graph_signature() -> None:
    assert "include_deprecated" in inspect.signature(iter_load_graph).parameters


def test_clear_soft_delete_dirty_helper() -> None:
    """PB-6a helper walks Metagraph + Graph buckets."""
    from mindsos_core import SoftDeleteKind
    from mindsos_core.reconstruction.metagraph_loader import _clear_soft_delete_dirty
    from tests._shared.soft_delete_fixture import make_metagraph_with_soft_delete

    mg, ids = make_metagraph_with_soft_delete()
    mg.graphs[ids["graph_ont"]].deprecate_edge(ids["edge"])
    mg.deprecate_metaedge(ids["metaedge"])
    _clear_soft_delete_dirty(mg)
    assert all(len(mg._soft_delete_dirty[k]) == 0 for k in mg._soft_delete_dirty)
    for g in mg.graphs.values():
        assert all(len(g._soft_delete_dirty[k]) == 0 for k in g._soft_delete_dirty)
