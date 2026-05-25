"""Phase 29 R1 PB-15 sentinel — discover_for_datastate emits zero edges at v1.

Under the Phase 28-29 forward-ref restriction
(``_CapacityBase.validate_for_registration`` forbids inputs/outputs
referencing unregistered DataStates), `register_capacity` is always
called AFTER the relevant DataStates are registered. So
`discover_for_datastate` triggered at end of `register_datastate`
walks the capacity index and finds no pair referencing the
just-registered DataState — emits zero edges.

Function is shipped for parent parity + future-scope (a phase that
relaxes the forward-ref restriction can rely on this hook).
"""

from __future__ import annotations

from mindsos_capacity import (
    CATEGORY_PERCEPTION,
    CapacityLayer,
    EDGE_TYPE_COMPAT,
    discover_for_datastate,
)

from ._fixtures import (
    text_demo_capacity,
    text_raw_datastate,
    text_tokens_datastate,
)


def test_register_datastate_emits_no_type_compat_edges_at_v1():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl.register_datastate(text_raw_datastate())
    cl.register_datastate(text_tokens_datastate())
    cl.register_capacity(text_demo_capacity())

    # Snapshot count BEFORE the third register_datastate call.
    mg = cl.global_metagraph()
    before_intra = sum(
        1 for g in mg.graphs.values()
        for e in g.edges.values() if e.type_name == EDGE_TYPE_COMPAT
    )
    before_meta = sum(
        1 for me in mg.metaedges.values() if me.type_name == EDGE_TYPE_COMPAT
    )

    # Call discover_for_datastate directly with the existing DataState
    # IRI — it walks the index and finds no NEW match (the existing
    # text.demo capacity references text.tokens but has no peer).
    created = discover_for_datastate(
        mg,
        text_tokens_datastate().iri,
        capacity_index=cl._capacity_index[mg.metagraph_id],
    )
    assert created == []

    after_intra = sum(
        1 for g in mg.graphs.values()
        for e in g.edges.values() if e.type_name == EDGE_TYPE_COMPAT
    )
    after_meta = sum(
        1 for me in mg.metaedges.values() if me.type_name == EDGE_TYPE_COMPAT
    )
    assert (after_intra, after_meta) == (before_intra, before_meta)
