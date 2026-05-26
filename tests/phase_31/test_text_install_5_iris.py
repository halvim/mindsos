"""Phase 31 — install_text_capacities registers all 5 IRIs.

3 DataStates (text.raw / text.tokens / text.sentences) + 2 capacities
(text.space_split / text.sentence_split).
"""

from __future__ import annotations

from mindsos_capacity.builtins import (
    DS_RAW_TEXT,
    DS_SENTENCES,
    DS_TOKENS,
)
from mindsos_capacity.identifiers import CATEGORY_PERCEPTION, capacity_iri

from ._fixtures import make_fresh_layer
from mindsos_capacity.builtins import install_text_capacities


def test_install_registers_all_5():
    layer = make_fresh_layer()
    install_text_capacities(layer)
    global_index = layer._capacity_index[layer.global_metagraph().metagraph_id]
    expected = {
        DS_RAW_TEXT,
        DS_TOKENS,
        DS_SENTENCES,
        capacity_iri(CATEGORY_PERCEPTION, "text.space_split"),
        capacity_iri(CATEGORY_PERCEPTION, "text.sentence_split"),
    }
    assert expected.issubset(set(global_index.keys()))
