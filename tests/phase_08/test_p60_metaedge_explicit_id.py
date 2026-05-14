"""P60 — add_metaedge / add_metahyperedge explicit-id kwargs."""

from __future__ import annotations

import pytest

from mindsos_core.exceptions import IdentityError
from mindsos_core.models.graph import Graph
from mindsos_core.models.identity import IdentityRegistry
from mindsos_core.models.metagraph import Metagraph


def _build_mg_with_two_graphs() -> Metagraph:
    mg = Metagraph(name="m1", identity=IdentityRegistry())
    g1 = Graph(name="g1", role="lex", identity=mg.identity)
    g2 = Graph(name="g2", role="ont", identity=mg.identity)
    mg.add_graph(g1)
    mg.add_graph(g2)
    return mg


def test_add_metaedge_accepts_explicit_edge_id() -> None:
    """P60 — explicit edge_id round-trips into the constructed MetaEdge."""
    mg = _build_mg_with_two_graphs()
    gids = list(mg.graphs.keys())
    me = mg.add_metaedge(
        source_graph_id=gids[0],
        target_graph_id=gids[1],
        type_name="LINKS_TO",
        edge_id="me-explicit-123",
    )
    assert me.edge_id == "me-explicit-123"
    assert me.edge_id in mg.metaedges


def test_add_metaedge_no_edge_id_mints_uuid() -> None:
    """Backwards-compat — without edge_id, a fresh UUID is generated."""
    mg = _build_mg_with_two_graphs()
    gids = list(mg.graphs.keys())
    me = mg.add_metaedge(
        source_graph_id=gids[0],
        target_graph_id=gids[1],
        type_name="LINKS_TO",
    )
    # UUID-like (36 chars with hyphens).
    assert len(me.edge_id) == 36
    assert me.edge_id.count("-") == 4


def test_add_metaedge_explicit_id_collision_raises_identity_error() -> None:
    """Explicit edge_id colliding with an existing id raises IdentityError."""
    mg = _build_mg_with_two_graphs()
    gids = list(mg.graphs.keys())
    mg.add_metaedge(
        source_graph_id=gids[0],
        target_graph_id=gids[1],
        type_name="LINKS_TO",
        edge_id="me-1",
    )
    with pytest.raises(IdentityError):
        mg.add_metaedge(
            source_graph_id=gids[0],
            target_graph_id=gids[1],
            type_name="OTHER",
            edge_id="me-1",
        )


def test_add_metaedge_validate_false_tolerates_namespaced_props() -> None:
    """P60 — _validate=False bypasses user-property validator.

    The user-properties validator rejects keys starting with underscore;
    reconstruction-path callers pass namespaced keys (e.g. core-reserved
    keys that slipped through the persist serializer).
    """
    mg = _build_mg_with_two_graphs()
    gids = list(mg.graphs.keys())
    # With _validate=True, namespaced keys would raise. With False, accepted.
    me = mg.add_metaedge(
        source_graph_id=gids[0],
        target_graph_id=gids[1],
        type_name="LINKS_TO",
        properties={"_internal_namespace_key": "value"},
        edge_id="me-1",
        _validate=False,
    )
    assert me.properties.get("_internal_namespace_key") == "value"


def test_add_metahyperedge_accepts_explicit_edge_id() -> None:
    """P60 — symmetric explicit-id kwarg on add_metahyperedge."""
    mg = _build_mg_with_two_graphs()
    gids = list(mg.graphs.keys())
    mhe = mg.add_metahyperedge(
        graph_ids=gids,
        type_name="MHE_TYPE",
        edge_id="mhe-explicit",
    )
    assert mhe.edge_id == "mhe-explicit"
    assert mhe.edge_id in mg.metahyperedges


def test_add_metahyperedge_validate_false_tolerates_namespaced_props() -> None:
    """_validate=False on add_metahyperedge also bypasses validation."""
    mg = _build_mg_with_two_graphs()
    gids = list(mg.graphs.keys())
    mhe = mg.add_metahyperedge(
        graph_ids=gids,
        type_name="MHE_TYPE",
        properties={"_internal_key": "value"},
        edge_id="mhe-1",
        _validate=False,
    )
    assert mhe.properties.get("_internal_key") == "value"
