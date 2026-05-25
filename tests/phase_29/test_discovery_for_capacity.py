"""Phase 29 — discover_for_capacity hook + intra-graph Edge writes."""

from __future__ import annotations

from mindsos_capacity import (
    CATEGORY_COMPREHENSION,
    CATEGORY_PERCEPTION,
    CapacityLayer,
    EDGE_TYPE_COMPAT,
)

from ._fixtures import (
    text_demo_capacity,
    text_join_capacity,
    text_raw_datastate,
    text_tokens_datastate,
)


def _layer():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION, CATEGORY_COMPREHENSION))
    cl.register_datastate(text_raw_datastate())
    cl.register_datastate(text_tokens_datastate())
    return cl


def test_first_capacity_emits_zero_edges():
    """Registering the FIRST capacity has no other capacities to pair with."""
    cl = _layer()
    cl.register_capacity(text_demo_capacity())
    g = cl.global_view().category_graph(CATEGORY_PERCEPTION)
    assert g is not None
    assert not any(e.type_name == EDGE_TYPE_COMPAT for e in g.edges.values())


def test_second_capacity_forward_match_writes_intra_graph_edge():
    """text.demo (out: tokens) → text.join (in: tokens) — same category."""
    cl = _layer()
    cl.register_capacity(text_demo_capacity())
    cl.register_capacity(text_join_capacity())
    g = cl.global_view().category_graph(CATEGORY_PERCEPTION)
    assert g is not None
    edges = [e for e in g.edges.values() if e.type_name == EDGE_TYPE_COMPAT]
    # Should have both directions: demo→join (via tokens) AND join→demo (via raw).
    assert len(edges) == 2
    for e in edges:
        assert e.properties["discovered_automatically"] is True
        assert e.properties["strictness"] == "strict"
        assert e.properties["via_datastate"] in (
            text_tokens_datastate().iri,
            text_raw_datastate().iri,
        )


def test_backward_match_when_new_capacity_consumes_existing_output():
    """Register join FIRST, then demo — demo's output should still match join's input."""
    cl = _layer()
    cl.register_capacity(text_join_capacity())  # consumes tokens, produces raw
    cl.register_capacity(text_demo_capacity())  # consumes raw, produces tokens
    g = cl.global_view().category_graph(CATEGORY_PERCEPTION)
    edges = [e for e in g.edges.values() if e.type_name == EDGE_TYPE_COMPAT]
    # 2 bidirectional edges (forward: demo→join, backward: join→demo).
    assert len(edges) == 2


def test_self_pair_skipped():
    """A capacity should not produce a TYPE_COMPAT edge to itself."""
    cl = _layer()
    cl.register_capacity(text_demo_capacity())
    g = cl.global_view().category_graph(CATEGORY_PERCEPTION)
    edges = [e for e in g.edges.values() if e.type_name == EDGE_TYPE_COMPAT]
    for e in edges:
        assert e.source.node_id != e.target.node_id
