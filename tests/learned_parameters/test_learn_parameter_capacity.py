"""Unit tests for the learned-parameters CR (write capacity + snapshot reader).

Light fakes (no falkor / no full stack) exercise the pure logic:
overwrite-in-place, provenance stamping, Local-overrides-Global, and the
reactivation-skip invariant. Integration through real L4 dispatch is covered
by the gate's dispatch suite once the wiring in WIRING.md lands.
"""

from __future__ import annotations

import pytest

from mindsos_capacity.builtins.learn_parameter import (
    DS_LEARNED_PARAMETER_WRITE,
    _learn_parameter_impl,
    build_learn_parameter,
)
from mindsos_knowledge.identifiers import ROLE_LEARNED_PARAMETERS
from mindsos_knowledge.schemas.learned_parameters import NODE_LEARNED_PARAMETER
from mindsos_knowledge.learned_parameters_snapshot import (
    get_parameter,
    read_learned_parameter_snapshot,
)


# ── fakes ──────────────────────────────────────────────────────────────


class _FakeNode:
    def __init__(self, value, type_name, properties, node_id):
        self.value = value
        self.type_name = type_name
        self.properties = properties
        self.node_id = node_id


class _FakeGraph:
    def __init__(self, role):
        self.role = role
        self.nodes = {}

    def remove_node(self, node_id, *, cascade=True):
        del self.nodes[node_id]

    def add_node(self, *, value, type_name, properties=None, node_id=None):
        if node_id in self.nodes:
            raise AssertionError("add_node must not overwrite a live id")
        n = _FakeNode(value, type_name, dict(properties or {}), node_id)
        self.nodes[node_id] = n
        return n


class _FakeHandle:
    def __init__(self, graph):
        self._g = graph

    def mint_iri(self, type_, **content):
        assert type_ == NODE_LEARNED_PARAMETER
        return f"learned-parameters-v1:parameter:{content['parameter_id']}"

    def graph(self):
        return self._g


class _FakeContext:
    def __init__(self, graph):
        self._g = graph
        self.user_id = "u1"

    def writeable(self, *, role, scope, version):
        assert role == ROLE_LEARNED_PARAMETERS
        assert scope == "local"
        return _FakeHandle(self._g)


class _FakeMetagraph:
    def __init__(self, graphs):
        self.graphs = {i: g for i, g in enumerate(graphs)}


class _FakeKL:
    def __init__(self, global_graphs, local_graphs):
        self._g = _FakeMetagraph(global_graphs)
        self._l = _FakeMetagraph(local_graphs)

    def global_metagraph(self):
        return self._g

    def local_metagraph(self, user):
        return self._l


def _record(**kw):
    return kw


# ── write capacity ─────────────────────────────────────────────────────


def test_write_stamps_labels_and_provenance():
    g = _FakeGraph(ROLE_LEARNED_PARAMETERS)
    ctx = _FakeContext(g)
    res = _learn_parameter_impl(
        context=ctx,
        **{
            DS_LEARNED_PARAMETER_WRITE: _record(
                parameter_set="als.sense-correlations",
                target="cutoff",
                value=0.42,
                confidence=0.9,
                learned_by="dream",
                reason="refit",
            )
        },
    )
    (node,) = g.nodes.values()
    assert node.value == 0.42
    assert node.type_name == NODE_LEARNED_PARAMETER
    p = node.properties
    assert p["parameter_set_iri"] == "als.sense-correlations"
    assert p["target_parameter_iri"] == "cutoff"
    assert p["confidence"] == 0.9
    assert p["learned_by"] == "dream"
    assert p["reason"] == "refit"
    assert p["recorded_at"] and p["applied_at"]
    assert "reactivation_key" not in p  # reactivation-skip invariant
    assert res.role == ROLE_LEARNED_PARAMETERS and res.scope == "local"
    assert res.iri == node.node_id


def test_rewrite_overwrites_in_place_no_history():
    g = _FakeGraph(ROLE_LEARNED_PARAMETERS)
    ctx = _FakeContext(g)
    base = dict(parameter_set="s", target="t", learned_by="dream")
    _learn_parameter_impl(context=ctx, **{DS_LEARNED_PARAMETER_WRITE: _record(value=1, **base)})
    _learn_parameter_impl(context=ctx, **{DS_LEARNED_PARAMETER_WRITE: _record(value=2, **base)})
    assert len(g.nodes) == 1  # one node per (set,target): overwrite, no history
    (node,) = g.nodes.values()
    assert node.value == 2  # latest wins


def test_optional_fields_omitted_when_absent():
    g = _FakeGraph(ROLE_LEARNED_PARAMETERS)
    ctx = _FakeContext(g)
    _learn_parameter_impl(
        context=ctx,
        **{DS_LEARNED_PARAMETER_WRITE: _record(
            parameter_set="s", target="t", value=1, learned_by="nilm"
        )},
    )
    (node,) = g.nodes.values()
    assert "confidence" not in node.properties  # None omitted, not stored
    assert "reason" not in node.properties


def test_write_without_dispatch_context_raises():
    class _NoWriteCtx:
        writeable = None
    with pytest.raises(RuntimeError):
        _learn_parameter_impl(
            context=_NoWriteCtx(),
            **{DS_LEARNED_PARAMETER_WRITE: _record(
                parameter_set="s", target="t", value=1, learned_by="x"
            )},
        )


def test_capacity_declaration_is_write_terminator():
    cap = build_learn_parameter()
    assert cap.outputs == ()
    assert cap.inputs == (DS_LEARNED_PARAMETER_WRITE,)


# ── snapshot reader ────────────────────────────────────────────────────


def _param_node(pset, target, value):
    return _FakeNode(
        value,
        NODE_LEARNED_PARAMETER,
        {"parameter_set_iri": pset, "target_parameter_iri": target},
        f"learned-parameters-v1:parameter:{pset}:{target}",
    )


def test_reader_local_overrides_global_per_knob():
    gg = _FakeGraph(ROLE_LEARNED_PARAMETERS)
    lg = _FakeGraph(ROLE_LEARNED_PARAMETERS)
    # Global has two knobs in set "s"
    for n in (_param_node("s", "a", 1), _param_node("s", "b", 2)):
        gg.nodes[n.node_id] = n
    # Local overrides only "a"
    n = _param_node("s", "a", 99)
    lg.nodes[n.node_id] = n
    kl = _FakeKL([gg], [lg])
    snap = read_learned_parameter_snapshot(kl, "u1")
    assert snap == {"s": {"a": 99, "b": 2}}  # per-knob override, "b" survives
    assert get_parameter(snap, "s", "a") == 99
    assert get_parameter(snap, "s", "missing", default="d") == "d"


def test_reader_skips_nodes_without_labels():
    g = _FakeGraph(ROLE_LEARNED_PARAMETERS)
    labelled = _param_node("s", "a", 1)
    g.nodes[labelled.node_id] = labelled
    # A legacy opaque node (e.g. nilm pre-migration) with no label props
    opaque = _FakeNode({"kind": "nilm"}, NODE_LEARNED_PARAMETER, {}, "opaque:1")
    g.nodes[opaque.node_id] = opaque
    kl = _FakeKL([g], [_FakeGraph(ROLE_LEARNED_PARAMETERS)])
    snap = read_learned_parameter_snapshot(kl, "u1")
    assert snap == {"s": {"a": 1}}  # opaque node skipped, not guessed


def test_reader_returns_empty_when_kl_is_none():
    # L4 dispatch may build a context with no KL (some lifecycle paths);
    # the snapshot fill must degrade to empty, not crash.
    assert read_learned_parameter_snapshot(None, "u1") == {}
