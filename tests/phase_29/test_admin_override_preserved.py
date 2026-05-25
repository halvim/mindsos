"""Phase 29 R1 PB-16 — ADR-0086 admin-override-preserved invariant.

Admin authors a manual TYPE_COMPAT edge (omitting
``discovered_automatically``); rediscover_all preserves it. Manual
edge for the same source/target/datastate triple BLOCKS auto-discovery
re-emitting a duplicate.

Admin path at Phase 29 is direct ``Graph.add_edge`` per ADR-0086
§Implementation — no ``CapacityLayer.add_type_compat`` method.
"""

from __future__ import annotations

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    CapacityLayer,
    EDGE_TYPE_COMPAT,
    rediscover_all,
)

from ._fixtures import (
    text_demo_capacity,
    text_join_capacity,
    text_raw_datastate,
    text_tokens_datastate,
)


def _populated_layer_with_pair():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl.register_datastate(text_raw_datastate())
    cl.register_datastate(text_tokens_datastate())
    cl.register_capacity(text_demo_capacity())
    cl.register_capacity(text_join_capacity())
    return cl


def test_manual_edge_survives_rediscover():
    cl = _populated_layer_with_pair()
    mg = cl.global_metagraph()
    g = cl.global_view().category_graph(CATEGORY_PERCEPTION)
    demo_iri = text_demo_capacity().iri
    join_iri = text_join_capacity().iri
    demo_node = g.nodes[demo_iri]
    join_node = g.nodes[join_iri]

    # Admin authors a MANUAL TYPE_COMPAT edge with a distinctive
    # `via_datastate` value (not one auto-discovery would emit).
    manual_props = {
        "via_datastate": "admin:custom-manual-route",
        "strictness": "strict",
        "admin_note": "manual override for spike scenario",
    }
    manual = g.add_edge(
        demo_node, join_node, EDGE_TYPE_COMPAT, properties=manual_props
    )
    assert "discovered_automatically" not in manual.properties

    rediscover_all(mg, capacity_index=cl._capacity_index[mg.metagraph_id])

    surviving = [
        e for e in g.edges.values()
        if e.edge_id == manual.edge_id
    ]
    assert len(surviving) == 1
    assert surviving[0].properties["via_datastate"] == "admin:custom-manual-route"


def test_manual_edge_blocks_auto_re_emission_for_same_triple():
    """If admin manually edges A→B via DS, rediscover does NOT add a duplicate."""
    cl = _populated_layer_with_pair()
    mg = cl.global_metagraph()
    g = cl.global_view().category_graph(CATEGORY_PERCEPTION)
    demo_iri = text_demo_capacity().iri
    join_iri = text_join_capacity().iri
    demo_node = g.nodes[demo_iri]
    join_node = g.nodes[join_iri]
    tokens_iri = text_tokens_datastate().iri

    # First, drop all auto edges so we start clean.
    auto_ids = [
        eid for eid, e in g.edges.items()
        if e.type_name == EDGE_TYPE_COMPAT
        and e.properties.get("discovered_automatically") is True
    ]
    for eid in auto_ids:
        g.remove_edge(eid)

    # Admin authors a MANUAL edge that shadows what auto-discovery
    # would emit (demo→join via tokens).
    g.add_edge(
        demo_node,
        join_node,
        EDGE_TYPE_COMPAT,
        properties={"via_datastate": tokens_iri, "strictness": "strict"},
    )

    rediscover_all(mg, capacity_index=cl._capacity_index[mg.metagraph_id])

    # Count TYPE_COMPAT edges from demo→join via tokens.
    matches = [
        e for e in g.edges.values()
        if e.type_name == EDGE_TYPE_COMPAT
        and e.source.node_id == demo_iri
        and e.target.node_id == join_iri
        and e.properties.get("via_datastate") == tokens_iri
    ]
    # Manual edge present; auto did NOT add a duplicate.
    assert len(matches) == 1
    assert "discovered_automatically" not in matches[0].properties
