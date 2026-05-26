"""Phase 31 — install_text_capacities registers all 5 IRIs.

3 DataStates (text.raw / text.tokens / text.sentences) live in the
``capacity:datastates`` role-graph's nodes dict. 2 Capacities
(text.space_split / text.sentence_split) live in
``CapacityLayer._capacity_index`` (per-metagraph). B-31-T1 hotfix:
probe each in the correct index.
"""

from __future__ import annotations

from mindsos_capacity.bootstrap import ensure_datastate_graph
from mindsos_capacity.builtins import (
    DS_RAW_TEXT,
    DS_SENTENCES,
    DS_TOKENS,
    install_text_capacities,
)
from mindsos_capacity.identifiers import CATEGORY_PERCEPTION, capacity_iri

from ._fixtures import make_fresh_layer


def test_install_registers_3_datastates():
    layer = make_fresh_layer()
    install_text_capacities(layer)
    ds_graph = ensure_datastate_graph(layer.global_metagraph())
    for ds_iri in (DS_RAW_TEXT, DS_TOKENS, DS_SENTENCES):
        assert ds_iri in ds_graph.nodes


def test_install_registers_2_capacities():
    layer = make_fresh_layer()
    install_text_capacities(layer)
    cap_index = layer._capacity_index[layer.global_metagraph().metagraph_id]
    expected_caps = {
        capacity_iri(CATEGORY_PERCEPTION, "text.space_split"),
        capacity_iri(CATEGORY_PERCEPTION, "text.sentence_split"),
    }
    assert expected_caps.issubset(set(cap_index.keys()))
