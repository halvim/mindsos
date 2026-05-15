"""State-file xrefs[] round-trip — RR-8 + RR-18 (deserializer direct-assign)."""

from __future__ import annotations

from mindsos_core import Graph, Metagraph
from mindsos_cli.commands.metagraph import (
    _metagraph_to_state, _state_to_metagraph,
)


def _seed_mg_with_xref() -> Metagraph:
    mg = Metagraph(name="rt", metagraph_id="mg-rt")
    g = Graph(name="g", role="ontology")
    mg.add_graph(g)
    g.add_node("n1", type_name="C", node_id="n1")
    mg.add_xref(
        source_id="n1", target_metagraph_id="mg-tgt", target_role="lex",
        target_id="t1", ref_type="SPECIALISES",
    )
    return mg


def test_serialize_to_state_includes_xrefs_array_rr_8(tmp_path, monkeypatch):
    """RR-8 — state-file shape carries xrefs[] with 8-field dict per entry."""
    from mindsos_cli import state as state_mod
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(tmp_path))

    mg = _seed_mg_with_xref()
    state = _metagraph_to_state(mg)
    assert "xrefs" in state
    assert len(state["xrefs"]) == 1
    x_dict = state["xrefs"][0]
    assert set(x_dict.keys()) == {
        "xref_id", "source_metagraph_id", "source_id",
        "target_metagraph_id", "target_role", "target_id",
        "ref_type", "properties",
    }


def test_round_trip_through_save_and_load(tmp_path, monkeypatch):
    """End-to-end: save → load → compare in-memory XRef state."""
    from mindsos_cli import state as state_mod
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(tmp_path))

    mg_in = _seed_mg_with_xref()
    # Save graph state too — _state_to_metagraph walks contained graphs.
    from mindsos_cli.commands.graph import _save_or_die as _g_save
    g_in = next(iter(mg_in.graphs.values()))
    _g_save("g", g_in, schema_name=None, metagraph_name="rt")

    state_mod.save_metagraph_state("rt", _metagraph_to_state(mg_in))
    loaded_state = state_mod.load_metagraph_state("rt")
    mg_out = _state_to_metagraph(loaded_state)

    assert len(mg_out.xrefs) == 1
    [x] = list(mg_out.xrefs.values())
    assert x.source_id == "n1"
    assert x.target_id == "t1"
    assert x.ref_type == "SPECIALISES"


def test_deserializer_leaves_dirty_empty_p64(tmp_path, monkeypatch):
    """P64 — RR-18 deserializer rebuilds inverse indexes WITHOUT marking dirty."""
    from mindsos_cli import state as state_mod
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(tmp_path))

    mg_in = _seed_mg_with_xref()
    from mindsos_cli.commands.graph import _save_or_die as _g_save
    _g_save("g", next(iter(mg_in.graphs.values())), schema_name=None,
            metagraph_name="rt-dirty")

    state_mod.save_metagraph_state("rt-dirty", _metagraph_to_state(mg_in))
    loaded = state_mod.load_metagraph_state("rt-dirty")
    mg_out = _state_to_metagraph(loaded)

    # Loaded XRef present; dirty set EMPTY.
    assert len(mg_out.xrefs) == 1
    assert mg_out._xrefs_dirty == set()


def test_deserializer_rebuilds_inverse_indexes_rr_18(tmp_path, monkeypatch):
    """RR-18 — deserializer manually rebuilds _xrefs_by_source / _xrefs_by_target."""
    from mindsos_cli import state as state_mod
    monkeypatch.setenv("MINDSOS_STATE_DIR", str(tmp_path))

    mg_in = _seed_mg_with_xref()
    from mindsos_cli.commands.graph import _save_or_die as _g_save
    _g_save("g", next(iter(mg_in.graphs.values())), schema_name=None,
            metagraph_name="rt-idx")

    state_mod.save_metagraph_state("rt-idx", _metagraph_to_state(mg_in))
    mg_out = _state_to_metagraph(state_mod.load_metagraph_state("rt-idx"))
    [x] = list(mg_out.xrefs.values())

    # Inverse indexes populated by the deserializer.
    assert x.xref_id in mg_out._xrefs_by_source["n1"]
    assert x.xref_id in mg_out._xrefs_by_target[("mg-tgt", "t1")]


def test_serialized_xrefs_are_sorted_by_xref_id():
    """RR-8 — xrefs[] sorted by xref_id for stable round-trip diffs."""
    mg = Metagraph(name="m", metagraph_id="mg-1")
    g = Graph(name="g", role="r")
    mg.add_graph(g)
    g.add_node("n1", type_name="C", node_id="n1")
    # Add multiple XRefs.
    mg.add_xref(source_id="n1", target_metagraph_id="m", target_role="r",
                target_id="t1", ref_type="SPECIALISES")
    mg.add_xref(source_id="n1", target_metagraph_id="m", target_role="r",
                target_id="t2", ref_type="SPECIALISES")
    mg.add_xref(source_id="n1", target_metagraph_id="m", target_role="r",
                target_id="t3", ref_type="SPECIALISES")
    state = _metagraph_to_state(mg)
    xref_ids = [d["xref_id"] for d in state["xrefs"]]
    assert xref_ids == sorted(xref_ids)
