"""CR: capacity_mm persist Slice B — persist the per-run grounding graphs into
the Episode (reopen DQ-8 / ADR-0202).

Two layers:

* **Unit** (no Falkor): the PB-1 ``encode`` dispatch and the PB-2 index-graph
  orchestration, against a fake persister.
* **Integration** (``@pytest.mark.integration``, live Falkor): the PB-4
  edge-aware round-trip — a writer ``.graph`` (nodes + PRODUCES/CONSUMES edges)
  persists and reloads with edges + encoded payloads intact — and the
  ``capacity_root_ref`` index graph resolves to its run graphs.

Inert-until-Step-5 (PB-3): nothing in this CR threads run graphs into
``consolidate_task``; these tests drive :mod:`mindsos_intelligence.capacity_persister`
directly, the same posture as the Slice-A writer test.
"""

from __future__ import annotations

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture

from mindsos_core.exceptions import PersistenceError
from mindsos_core.models.graph import Graph
from mindsos_intelligence.capacity_persister import (
    CapacityStreamSink,
    NODE_TYPE_CAPACITY_RUN_REF,
    build_capacity_index,
    default_encode,
    index_graph_role,
    make_node_value_encoder,
    persist_capacity_mm,
)
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.capacity_mm_writer import CapacityMMWriter
from mindsos_capacity.identifiers import (
    EDGE_CONSUMES,
    EDGE_PRODUCES,
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    PROP_DATASTATE_INSTANCE_TYPE,
)


# ── unit: PB-1 encode dispatch ──────────────────────────────────────────────


class _Node:
    def __init__(self, value, type_name, properties=None):
        self.value = value
        self.type_name = type_name
        self.properties = properties or {}


class _NonCodecSafe:
    """A domain value the ADR-0182 codec cannot take (not primitive/dict/list)."""


def test_default_encode_passes_codec_safe_and_rejects_others():
    for v in ["s", 1, 1.5, True, None, {"a": 1}, [[1, 2]]]:
        assert default_encode(v) == v
    with pytest.raises(PersistenceError):
        default_encode(_NonCodecSafe())


def test_encoder_dispatch_registered_default_and_capacity():
    enc = make_node_value_encoder({"datastate:grid": lambda v: {"rows": v.n}})

    obj = _NonCodecSafe()
    obj.n = [[1, 2]]
    registered = _Node(obj, NODE_TYPE_DATASTATE_INSTANCE, {PROP_DATASTATE_INSTANCE_TYPE: "datastate:grid"})
    assert enc(registered) == {"rows": [[1, 2]]}

    # No encoder for this type → value must already be codec-safe.
    plain = _Node([[9]], NODE_TYPE_DATASTATE_INSTANCE, {PROP_DATASTATE_INSTANCE_TYPE: "datastate:other"})
    assert enc(plain) == [[9]]

    # Unregistered + non-codec-safe → PersistenceError (default A).
    bad = _Node(_NonCodecSafe(), NODE_TYPE_DATASTATE_INSTANCE, {PROP_DATASTATE_INSTANCE_TYPE: "datastate:x"})
    with pytest.raises(PersistenceError):
        enc(bad)

    # CapacityInstance value is its capacity IRI — a primitive, passes through.
    cap = _Node("capacity:derivation:one", NODE_TYPE_CAPACITY_INSTANCE, {})
    assert enc(cap) == "capacity:derivation:one"


def test_encoder_result_must_be_codec_safe():
    """A brain encoder that returns a non-codec-safe result still fails loud."""
    enc = make_node_value_encoder({"datastate:z": lambda v: _NonCodecSafe()})
    node = _Node(1, NODE_TYPE_DATASTATE_INSTANCE, {PROP_DATASTATE_INSTANCE_TYPE: "datastate:z"})
    with pytest.raises(PersistenceError):
        enc(node)


# ── unit: PB-2 index orchestration (fake persister) ─────────────────────────


class _FakePersister:
    def __init__(self):
        self.calls = []  # (graph, node_value_encoder-is-set)

    def persist(self, metagraph, graph, *, node_value_encoder=None):
        self.calls.append((graph, node_value_encoder is not None))


def _run_graph(role):
    g = Graph(name=role, role=role)
    g.add_node("capacity:derivation:one", NODE_TYPE_CAPACITY_INSTANCE)
    return g


def test_persist_capacity_mm_empty_is_noop():
    fp = _FakePersister()
    assert persist_capacity_mm(fp, object(), [], request_id="T") is None
    assert persist_capacity_mm(fp, object(), [None], request_id="T") is None
    assert fp.calls == []


def test_persist_capacity_mm_persists_runs_then_index():
    g1 = _run_graph("capacity:run:T:1")
    g2 = _run_graph("capacity:run:T:2")
    fp = _FakePersister()
    root = persist_capacity_mm(fp, object(), [g1, g2], request_id="T")

    # Two run persists (with the per-DataState encoder) + one index persist
    # (default encoder — index node values are graph-id primitives).
    assert [enc_set for _, enc_set in fp.calls] == [True, True, False]
    index_graph = fp.calls[-1][0]
    assert index_graph.role == index_graph_role("T")
    assert root == index_graph.graph_id

    refs = [n for n in index_graph.nodes.values() if n.type_name == NODE_TYPE_CAPACITY_RUN_REF]
    assert {n.value for n in refs} == {g1.graph_id, g2.graph_id}


# ── integration: PB-4 edge-aware round-trip + index resolve (live Falkor) ───


def _writer_run_graph(mm):
    """A realistic per-run grounding graph: a seed input, one capacity
    invocation, one produced output — CapacityInstance + DataStateInstance
    nodes wired by intra-graph CONSUMES/PRODUCES edges."""
    w = CapacityMMWriter(mm, "t1", "pipelinerun:t1:1")
    w.seed("datastate:a", [[1, 2], [3, 4]])            # codec-safe already
    w.record("capacity:derivation:one", ["datastate:a"], {"datastate:b": {"cells": [[1]]}})
    return w.graph


@pytest.mark.integration
def test_capacity_persist_round_trip(falkor_client):
    from mindsos_core.reconstruction import load_graph
    from mindsos_intelligence.mm_persister import FalkorMMPersister

    mm = MentalModel(session_id="s", user_id="u")
    graph = _writer_run_graph(mm)

    # Sanity: the live graph carries both node-types + the two edges.
    assert any(n.type_name == NODE_TYPE_CAPACITY_INSTANCE for n in graph.nodes.values())
    edge_types = sorted(e.type_name for e in graph.edges.values())
    assert edge_types == [EDGE_CONSUMES, EDGE_PRODUCES]

    encoders = {"datastate:b": lambda v: {"encoded": v}}
    persister = FalkorMMPersister(falkor_client)
    root_ref = persist_capacity_mm(
        persister, mm.capacity_mm, [graph], request_id="t1", encoders=encoders
    )
    assert root_ref is not None

    # Run graph reloads WITH its intra-graph edges (PB-4).
    loaded = load_graph(falkor_client, graph.graph_id)
    assert set(loaded.nodes) == set(graph.nodes)
    live_edges = {
        (e.type_name, e.source.node_id, e.target.node_id) for e in graph.edges.values()
    }
    loaded_edges = {
        (e.type_name, e.source.node_id, e.target.node_id) for e in loaded.edges.values()
    }
    assert loaded_edges == live_edges

    # Payloads survive: the encoded output value round-trips (PB-1); the
    # unencoded seed value round-trips unchanged.
    by_ds_type = {
        n.properties.get(PROP_DATASTATE_INSTANCE_TYPE): n.value
        for n in loaded.nodes.values()
        if n.type_name == NODE_TYPE_DATASTATE_INSTANCE
    }
    assert by_ds_type["datastate:a"] == [[1, 2], [3, 4]]
    assert by_ds_type["datastate:b"] == {"encoded": {"cells": [[1]]}}

    # capacity_root_ref resolves to the index graph, which references the run
    # graph (PB-2).
    index = load_graph(falkor_client, root_ref)
    assert index.role == index_graph_role("t1")
    refs = [n for n in index.nodes.values() if n.type_name == NODE_TYPE_CAPACITY_RUN_REF]
    assert [n.value for n in refs] == [graph.graph_id]


@pytest.mark.integration
def test_member_graph_ids_order_survives_the_store_at_end_state(falkor_client):
    """ADR-0201 am-5 end-state cell: the fold manifest's ordered id LIST
    (S-F1) is re-read from the store ALONE, AFTER a later unrelated write —
    the RULES 12 end-state-reader row class: a per-case read at persist time
    structurally cannot see what a later write does to the end state."""
    from mindsos_core.reconstruction import load_graph
    from mindsos_intelligence.mm_persister import FalkorMMPersister
    from mindsos_capacity.identifiers import (
        MANIFEST_MEMBER_GRAPH_IDS,
        NODE_TYPE_RUN_MANIFEST,
    )

    mm = MentalModel(session_id="s", user_id="u")
    fold_writer = CapacityMMWriter(mm, "t3", "pipelinerun:t3:fold:0")
    ids = ["gid-zulu", "gid-alpha", "gid-mike"]
    fold_writer.manifest(
        declared_starts={}, capacity_phrases={}, member_graph_ids=ids,
    )
    fold_writer.seed("datastate:t3in", [])
    persister = FalkorMMPersister(falkor_client)
    persist_capacity_mm(
        persister, mm.capacity_mm, [fold_writer.graph], request_id="t3",
        encoders={},
    )

    # The LATER write: a different run persists after the fold graph.
    mm2 = MentalModel(session_id="s", user_id="u")
    later = _writer_run_graph(mm2)
    persist_capacity_mm(
        persister, mm2.capacity_mm, [later], request_id="t3-later",
        encoders={"datastate:b": lambda v: {"encoded": v}},
    )

    # End-state read: the store alone, after the last write.
    loaded = load_graph(falkor_client, fold_writer.graph.graph_id)
    manifests = [
        n for n in loaded.nodes.values()
        if n.type_name == NODE_TYPE_RUN_MANIFEST
    ]
    assert len(manifests) == 1
    assert manifests[0].value[MANIFEST_MEMBER_GRAPH_IDS] == ids


# ── Dream PRE-0 Slice 2: build_capacity_index (index-only) + streaming sink ──


def test_build_capacity_index_persists_index_only():
    """Slice 2: at close the run graphs are already streamed, so
    ``build_capacity_index`` persists ONLY the index (one call, no run-graph
    re-persist) and returns its graph_id."""
    g1 = _run_graph("capacity:run:T:1")
    g2 = _run_graph("capacity:run:T:2")
    fp = _FakePersister()
    root = build_capacity_index(fp, object(), [g1, g2], request_id="T")

    assert len(fp.calls) == 1  # index only — NOT the two run graphs
    index_graph, enc_set = fp.calls[0]
    assert enc_set is False
    assert index_graph.role == index_graph_role("T")
    assert root == index_graph.graph_id
    refs = [n for n in index_graph.nodes.values() if n.type_name == NODE_TYPE_CAPACITY_RUN_REF]
    assert {n.value for n in refs} == {g1.graph_id, g2.graph_id}


def test_build_capacity_index_empty_is_noop():
    fp = _FakePersister()
    assert build_capacity_index(fp, object(), [], request_id="T") is None
    assert build_capacity_index(fp, object(), [None], request_id="T") is None
    assert fp.calls == []


def test_capacity_stream_sink_persists_each_run_on_append():
    """Slice 2: the sink IS the per-run list; appending a run graph persists it
    immediately (graph-scoped, with the node encoder) — the streaming spine."""
    mm = MentalModel(session_id="s", user_id="u")
    fp = _FakePersister()
    sink = CapacityStreamSink(mm, fp)
    assert sink.streamed is True

    g = _run_graph("capacity:run:T:1")
    sink.append(g)
    assert list(sink) == [g]  # still behaves as the capacity_graphs list
    assert len(fp.calls) == 1
    graph, enc_set = fp.calls[0]
    assert graph is g and enc_set is True


def test_capacity_stream_sink_best_effort_on_persist_error():
    """A failed stream-flush must never fail the solve; the graph is retained in
    the list so the close-time index still references it."""

    class _Boom:
        def persist(self, *a, **k):
            raise PersistenceError("boom")

    mm = MentalModel(session_id="s", user_id="u")
    sink = CapacityStreamSink(mm, _Boom())
    g = _run_graph("capacity:run:T:1")
    sink.append(g)  # must NOT raise
    assert list(sink) == [g]


def test_capacity_stream_sink_plain_list_without_persister():
    """No persister → behaves as a plain list (byte-identical to the
    simplified / no-Falkor path)."""
    sink = CapacityStreamSink(None, None)
    g = _run_graph("capacity:run:T:1")
    sink.append(g)
    assert list(sink) == [g]
