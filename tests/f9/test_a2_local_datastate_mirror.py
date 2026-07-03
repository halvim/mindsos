"""F9 — ADR-0185 §A2′: Local capacity registration mirrors Global DataStates.

A Local capacity may reference Global-only DataStates; ``register_capacity``
mirrors them into the Local DataState graph so validation + the ADR-0156
PRODUCES/CONSUMES edges succeed Local-side. Pure-L3, no live DB.
"""

from __future__ import annotations

from mindsos_capacity import Capacity, CapacityLayer, CATEGORY_PERCEPTION
from mindsos_capacity.bootstrap import ensure_datastate_graph

from ._fixtures import DuckSession, raw_ds, tokens_ds


def _cap():
    return Capacity(
        name="text.demo",
        category=CATEGORY_PERCEPTION,
        inputs=(raw_ds().iri,),
        outputs=(tokens_ds().iri,),
        implementation=lambda **kw: {tokens_ds().iri: kw[raw_ds().iri].split()},
    )


def test_local_register_mirrors_global_datastates_and_emits_edges():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    # DataStates exist ONLY on Global.
    cl.register_datastate(raw_ds())
    cl.register_datastate(tokens_ds())

    alice = DuckSession("alice")
    # Register the capacity on the Local WITHOUT registering DataStates Local.
    cl.register_capacity(_cap(), session=alice)

    local_mg = cl.local_metagraph("alice")
    lds = ensure_datastate_graph(local_mg)
    assert raw_ds().iri in lds.nodes
    assert tokens_ds().iri in lds.nodes

    edge_types = {e.type_name for e in local_mg.intergraph_edges.values()}
    assert "PRODUCES" in edge_types
    assert "CONSUMES" in edge_types

    res = cl.invoke("capacity:perception:text.demo", {raw_ds().iri: "a b"}, session=alice)
    assert res.success and res.outputs[tokens_ds().iri] == ["a", "b"]


def test_mirror_is_idempotent_when_datastates_already_local():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl.register_datastate(raw_ds())
    cl.register_datastate(tokens_ds())
    alice = DuckSession("alice")
    # Pre-register DataStates Local explicitly.
    cl.register_datastate(raw_ds(), session=alice)
    cl.register_datastate(tokens_ds(), session=alice)
    lds = ensure_datastate_graph(cl.local_metagraph("alice"))
    before = len(lds.nodes)

    cl.register_capacity(_cap(), session=alice)
    assert len(lds.nodes) == before  # no double-add


def test_global_registration_unaffected():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl.register_datastate(raw_ds())
    cl.register_datastate(tokens_ds())
    # No session → Global; mirror branch must not run.
    node = cl.register_capacity(_cap())
    assert node.node_id == "capacity:perception:text.demo"
