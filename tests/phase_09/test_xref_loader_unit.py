"""XRefLoader unit tests — clear-first semantics (PB-9 + P55 + P64)."""

from __future__ import annotations

from mindsos_core import Graph, Metagraph
from mindsos_core.models.xref import XRef
from mindsos_core.persistence import InMemoryClient
from mindsos_core.reconstruction.xref_loader import XRefLoader


def _seed_mg_with_stale_xref() -> Metagraph:
    """Build mg with one pre-populated XRef so we can verify clear-first."""
    mg = Metagraph(name="m", metagraph_id="mg-1")
    g = Graph(name="g", role="r")
    mg.add_graph(g)
    g.add_node("n1", type_name="X", node_id="n1")
    stale = XRef(
        source_metagraph_id="mg-1",
        source_id="n1",
        target_metagraph_id="mg-tgt",
        target_role="lex",
        target_id="OLD-TARGET",
        ref_type="SPECIALISES",
        xref_id="stale-xid",
    )
    mg.identity.register(stale.xref_id)
    mg.xrefs[stale.xref_id] = stale
    mg._xrefs_by_source.setdefault("n1", set()).add(stale.xref_id)
    mg._xrefs_by_target.setdefault(("mg-tgt", "OLD-TARGET"), set()).add(
        stale.xref_id
    )
    mg._xrefs_dirty.add(stale.xref_id)
    return mg


def test_load_into_clears_existing_xrefs_first_pb_9():
    """PB-9 — load_into clears mg.xrefs + inverse + identity BEFORE re-populating."""
    mg = _seed_mg_with_stale_xref()
    c = InMemoryClient()
    # Empty fetch → no new rows.
    c.script([])
    XRefLoader(c).load_into(mg)

    # Stale XRef gone.
    assert "stale-xid" not in mg.xrefs
    assert "stale-xid" not in mg._xrefs_by_source.get("n1", set())
    assert "stale-xid" not in mg._xrefs_by_target.get(("mg-tgt", "OLD-TARGET"), set())
    assert not mg.identity.contains("stale-xid")


def test_load_into_clears_dirty_set_p55():
    """P55 — refresh blanks _xrefs_dirty alongside mg.xrefs.

    Loaded XRefs are by definition already-persisted; the dirty set
    must NOT carry over old entries (would cause silent re-write on
    next persist).
    """
    mg = _seed_mg_with_stale_xref()
    c = InMemoryClient()
    c.script([])
    XRefLoader(c).load_into(mg)
    assert mg._xrefs_dirty == set()


def test_load_into_repopulates_from_db_rows():
    """Populate pass — DB rows become XRef instances + inverse-index entries."""
    mg = _seed_mg_with_stale_xref()
    c = InMemoryClient()
    c.script([
        {
            "id": "new-xid",
            "smid": "mg-1",
            "sid": "n1",
            "tmid": "mg-tgt",
            "trole": "lex",
            "tid": "NEW-TARGET",
            "ref_type": "INSTANCE_OF",
            "props": {
                # Core fields filtered; user props pass through.
                "id": "new-xid",
                "source_metagraph_id": "mg-1",
                "source_id": "n1",
                "target_metagraph_id": "mg-tgt",
                "target_role": "lex",
                "target_id": "NEW-TARGET",
                "ref_type": "INSTANCE_OF",
                "user_prop_1": "hello",
            },
        }
    ])
    XRefLoader(c).load_into(mg)

    assert "new-xid" in mg.xrefs
    new_x = mg.xrefs["new-xid"]
    assert new_x.target_id == "NEW-TARGET"
    assert new_x.ref_type == "INSTANCE_OF"
    # User property survived; core fields filtered out of properties.
    assert new_x.properties == {"user_prop_1": "hello"}
    # Inverse indexes populated.
    assert "new-xid" in mg._xrefs_by_source["n1"]
    assert "new-xid" in mg._xrefs_by_target[("mg-tgt", "NEW-TARGET")]
    # Dirty set still empty post-load (P64).
    assert mg._xrefs_dirty == set()


def test_load_into_emits_indexed_query_p63_alignment():
    """Loader query uses ``:XRef {source_metagraph_id: $mid}`` index."""
    mg = Metagraph(name="m", metagraph_id="mg-1")
    c = InMemoryClient()
    c.script([])
    XRefLoader(c).load_into(mg)
    queries = [q for q, _ in c.calls]
    assert any(":XRef {source_metagraph_id: $mid}" in q for q in queries), queries
