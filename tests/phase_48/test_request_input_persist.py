"""PRE-1 — request-input persistence (the Dream's reload anchor).

Two layers, mirroring the capacity_mm persist tests:

* **Unit** (no Falkor): the codec-safe encode discipline + the one-node
  ``RequestInput`` graph shape, against a fake persister.
* **Integration** (``@pytest.mark.integration``, live Falkor): the round-trip
  — persist an input value + modality, reload it by ``request_input_root_ref``
  via :func:`load_request_input`, and get the value + modality back. PRE-1
  ships this reader (unlike ``capacity_root_ref``, write-only until dream
  reconstruction) because the anchor's whole point is that it reads back.
"""

from __future__ import annotations

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture

from mindsos_core.exceptions import PersistenceError
from mindsos_intelligence.request_input_persister import (
    NODE_TYPE_REQUEST_INPUT,
    PROP_INPUT_MODALITY,
    input_graph_role,
    persist_request_input,
    load_request_input,
)


class _NonCodecSafe:
    """A domain value the ADR-0182 codec cannot take (not primitive/dict/list)."""


class _FakePersister:
    """Captures the graph handed to ``persist`` without touching Falkor."""

    def __init__(self):
        self.calls = []  # (metagraph, graph)

    def persist(self, metagraph, graph, *, node_value_encoder=None):
        self.calls.append((metagraph, graph))


# ── unit: graph shape ───────────────────────────────────────────────────────


def test_persist_builds_single_request_input_node_with_modality():
    fp = _FakePersister()
    root = persist_request_input(
        fp, object(), scope="task:T1", value=[[1, 2]], modality="grid"
    )
    assert len(fp.calls) == 1
    _, graph = fp.calls[0]
    assert graph.role == input_graph_role("task:T1")
    assert root == graph.graph_id

    nodes = list(graph.nodes.values())
    assert len(nodes) == 1
    node = nodes[0]
    assert node.type_name == NODE_TYPE_REQUEST_INPUT
    assert node.value == [[1, 2]]
    assert (node.properties or {}).get(PROP_INPUT_MODALITY) == "grid"


def test_persist_omits_modality_property_when_none():
    fp = _FakePersister()
    persist_request_input(fp, object(), scope="task:T2", value="hi", modality=None)
    _, graph = fp.calls[0]
    node = next(iter(graph.nodes.values()))
    assert PROP_INPUT_MODALITY not in (node.properties or {})


# ── unit: encode discipline ─────────────────────────────────────────────────


def test_non_codec_safe_value_without_encode_raises():
    fp = _FakePersister()
    with pytest.raises(PersistenceError):
        persist_request_input(fp, object(), scope="task:T3", value=_NonCodecSafe())
    assert fp.calls == []  # nothing persisted on failure


def test_encode_hint_reduces_value():
    fp = _FakePersister()
    obj = _NonCodecSafe()
    obj.n = [[7]]
    root = persist_request_input(
        fp, object(), scope="task:T4", value=obj, encode=lambda v: {"rows": v.n}
    )
    _, graph = fp.calls[0]
    node = next(iter(graph.nodes.values()))
    assert node.value == {"rows": [[7]]}
    assert root == graph.graph_id


def test_encode_result_must_be_codec_safe():
    fp = _FakePersister()
    with pytest.raises(PersistenceError):
        persist_request_input(
            fp, object(), scope="task:T5", value=1, encode=lambda v: _NonCodecSafe()
        )


def test_input_graph_role_rejects_empty_scope():
    with pytest.raises(ValueError):
        input_graph_role("")


# ── integration: live Falkor round-trip ─────────────────────────────────────


@pytest.mark.integration
def test_request_input_round_trip(falkor_client):
    from mindsos_intelligence.mm import MentalModel
    from mindsos_intelligence.mm_persister import FalkorMMPersister

    mm = MentalModel(session_id="s", user_id="u")
    persister = FalkorMMPersister(falkor_client)

    value = [[1, 2], [3, 4]]
    root = persist_request_input(
        persister, mm.intelligence_mm, scope="task:RT", value=value, modality="grid"
    )
    assert root is not None

    got_value, got_modality = load_request_input(falkor_client, root)
    assert got_value == value
    assert got_modality == "grid"


@pytest.mark.integration
def test_load_request_input_missing_node_raises(falkor_client):
    from mindsos_intelligence.mm import MentalModel
    from mindsos_intelligence.mm_persister import FalkorMMPersister
    from mindsos_core.models.graph import Graph

    mm = MentalModel(session_id="s", user_id="u")
    persister = FalkorMMPersister(falkor_client)
    empty = Graph(name="request:input:none", role="request:input:none")
    empty.add_node(value="x", type_name="NotAnInput")
    persister.persist(mm.intelligence_mm, empty)

    with pytest.raises(PersistenceError):
        load_request_input(falkor_client, empty.graph_id)
