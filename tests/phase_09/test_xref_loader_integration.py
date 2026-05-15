"""XRefLoader integration — full persist + load round-trip with assert_xref_contents_equal."""

from __future__ import annotations

import pytest

from mindsos_core.cypher.builders import build_create_metagraph_anchor
from mindsos_core.models.xref import XRef
from mindsos_core.persistence.xref_repository import XRefRepository
from mindsos_core.reconstruction.xref_loader import XRefLoader
from tests._shared.metagraph_equality import assert_xref_contents_equal

pytestmark = pytest.mark.integration


def _seed_anchor(client, mid: str, name: str) -> None:
    q, p = build_create_metagraph_anchor(mid, name, props_json="{}")
    client.run_query(q, p)


def test_persist_then_load_into_round_trips(falkor_client):
    from mindsos_core import Metagraph

    _seed_anchor(falkor_client, "mg-rt-1", "rt-1")
    src = [
        XRef(
            source_metagraph_id="mg-rt-1",
            source_id=f"src-{i}",
            target_metagraph_id="mg-tgt",
            target_role="lex",
            target_id=f"tgt-{i}",
            ref_type="SPECIALISES",
            xref_id=f"xid-rt-{i}",
        )
        for i in range(3)
    ]
    repo = XRefRepository(falkor_client)
    for x in src:
        repo.persist(x)

    # Load into a fresh metagraph.
    mg_loaded = Metagraph(name="rt-1", metagraph_id="mg-rt-1")
    XRefLoader(falkor_client).load_into(mg_loaded)

    src_dict = {x.xref_id: x for x in src}
    assert_xref_contents_equal(src_dict, mg_loaded.xrefs)


def test_loader_filters_by_source_metagraph_id(falkor_client):
    """Loader query is scoped to source_metagraph_id; XRefs from other mgs ignored."""
    from mindsos_core import Metagraph

    _seed_anchor(falkor_client, "mg-mine", "mine")
    _seed_anchor(falkor_client, "mg-other", "other")

    repo = XRefRepository(falkor_client)
    repo.persist(XRef(
        source_metagraph_id="mg-mine", source_id="s1",
        target_metagraph_id="mg-tgt", target_role="r", target_id="t1",
        ref_type="SPECIALISES", xref_id="xid-mine",
    ))
    repo.persist(XRef(
        source_metagraph_id="mg-other", source_id="s2",
        target_metagraph_id="mg-tgt", target_role="r", target_id="t2",
        ref_type="SPECIALISES", xref_id="xid-other",
    ))

    mg = Metagraph(name="mine", metagraph_id="mg-mine")
    XRefLoader(falkor_client).load_into(mg)

    assert "xid-mine" in mg.xrefs
    assert "xid-other" not in mg.xrefs
