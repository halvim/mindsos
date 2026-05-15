"""MetagraphRepository.persist drains _xrefs_dirty (RR-17 + P54)."""

from __future__ import annotations

from mindsos_core import Graph, Metagraph
from mindsos_core.persistence import InMemoryClient, MetagraphRepository


def _seed_mg() -> Metagraph:
    mg = Metagraph(name="m", metagraph_id="mg-1")
    g = Graph(name="g", role="ontology")
    mg.add_graph(g)
    g.add_node("n1", type_name="C", node_id="n1")
    return mg


def test_persist_writes_dirty_xrefs():
    """RR-17 — persist iterates mg._xrefs_dirty + calls XRefRepository.persist."""
    mg = _seed_mg()
    # Programmatic add (no _persist_client) → dirty mark.
    x = mg.add_xref(
        source_id="n1", target_metagraph_id="mg-tgt", target_role="lex",
        target_id="t1", ref_type="SPECIALISES",
    )
    assert x.xref_id in mg._xrefs_dirty

    c = InMemoryClient()
    # Anchor write + 1 XRef WAL begin + MERGE + WAL commit.
    # The InMemoryClient script-by-script just needs each query to
    # return SOMETHING; we don't assert specific row contents.
    for _ in range(20):
        c.script([{"any": "row"}])

    MetagraphRepository(c).persist(mg)

    queries = [q for q, _ in c.calls]
    # XRef MERGE happened.
    assert any("MERGE (x:XRef" in q for q in queries), queries
    # P54 — dirty set cleared on success (atomic at end).
    assert mg._xrefs_dirty == set()


def test_persist_no_op_when_dirty_empty():
    """P54 — dirty empty ⇒ no XRef writes."""
    mg = _seed_mg()
    c = InMemoryClient()
    for _ in range(10):
        c.script([{"any": "row"}])
    MetagraphRepository(c).persist(mg)
    queries = [q for q, _ in c.calls]
    assert not any("MERGE (x:XRef" in q for q in queries)


def test_persist_skips_removed_xref_in_dirty():
    """If an xref is in dirty but absent from mg.xrefs (removed between add
    and persist), persist drops it from dirty and does NOT crash.
    """
    mg = _seed_mg()
    x = mg.add_xref(
        source_id="n1", target_metagraph_id="mg-tgt", target_role="lex",
        target_id="t1", ref_type="SPECIALISES",
    )
    # Manually nuke from xrefs but leave in dirty (simulating mid-flight
    # removal that didn't unwire dirty correctly).
    mg.xrefs.pop(x.xref_id)
    # _xrefs_dirty still contains x.xref_id.
    assert x.xref_id in mg._xrefs_dirty

    c = InMemoryClient()
    for _ in range(10):
        c.script([{"any": "row"}])
    # Should not raise.
    MetagraphRepository(c).persist(mg)
    assert mg._xrefs_dirty == set()
