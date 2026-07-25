"""Phase 48 — L5 Slice 3: knowledge-MM writer + mm_handle + DQ-1 provenance XRef.

Umbrella CR "L5 has three rooms and only one door", Slice 3:

* ``MMResolver`` finishes instantiation INTO the graph — ``knowledge_mm`` gets a
  real writer (it was empty by construction before); pinned version-ref nodes.
* the body-facing MM read handle (``mm_handle``, ADR-0200) is the ``MMResolver``;
  a ``reads_mm=True`` body reads a value the writer put there.
* ``CapacityMMWriter.link_provenance`` writes the nullable
  ``capacity_mm``→``knowledge_mm`` ``INSTANCE_OF`` XRef (DQ-1 / T2 / M1): arc1
  supplies the pinned corpus-entry target; arc3 (``None``) writes no row.

Posture mirrors Slices A/C — inert in prod (no shipped ``reads_mm`` cap; solve-path
consolidation is out-of-CR Step 5), so the substrate is exercised synthetically.
The chain-writer non-leak invariant (``phase_47/test_chain_artifact_emit.py:79-80``)
is deliberately unchanged; the deep_copy fork provenance XRef is covered by
``phase_47/test_mm_fork_independence.py`` (CR test 4).
"""

from __future__ import annotations

import pytest

from mindsos_core import XRefIntegrityError

from mindsos_capacity import CapacityLayer, CATEGORY_PERCEPTION, DataState, ShapeDescriptor
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.identifiers import capacity_iri

from mindsos_intelligence.capacity_mm_writer import CapacityMMWriter
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.mm_resolver import (
    INSTANCE_GRAPH_ROLE,
    KnowledgeMMSource,
    MMResolver,
    NODE_TYPE_MM_INSTANCE,
    PROP_INSTANCE_TYPE,
    PROP_PIN_VERSION,
    SourceNode,
)

CORPUS_IRI = "ontology:arc.corpus.task7"
RAW_TASK = "datastate:arc.raw_task"

DS_IN = "datastate:test.in"
DS_OUT = "datastate:test.out"


class _Source:
    """Minimal MMSource over a fixed {iri -> SourceNode} table."""

    def __init__(self, nodes):
        self._nodes = nodes

    def get_node(self, iri):
        return self._nodes[iri]


def _corpus_source(payload="grid-7", version=4):
    return _Source(
        {
            CORPUS_IRI: SourceNode(
                iri=CORPUS_IRI,
                version=version,
                type_iri="ontology:ArcTask",
                payload=payload,
            )
        }
    )


def _mm():
    return MentalModel(session_id="s", user_id="u")


def _writer(mm):
    return CapacityMMWriter(
        mm, task_id="task-1", pipeline_run_ref="pipelinerun:task-1"
    )


# ── knowledge writer: MMResolver writes into the knowledge_mm graph ────────


def test_get_or_instantiate_writes_pinned_node_into_knowledge_mm():
    mm = _mm()
    r = MMResolver(mm, _corpus_source(payload="grid-7", version=4))
    # empty by construction before any instantiation
    assert sum(len(g.nodes) for g in mm.knowledge_mm.graphs.values()) == 0

    inst = r.get_or_instantiate(CORPUS_IRI)

    graphs = [
        g for g in mm.knowledge_mm.graphs.values() if g.role == INSTANCE_GRAPH_ROLE
    ]
    assert len(graphs) == 1
    node = graphs[0].nodes[CORPUS_IRI]
    assert node.type_name == NODE_TYPE_MM_INSTANCE
    assert node.value == "grid-7"
    assert node.properties[PROP_PIN_VERSION] == 4
    assert node.properties[PROP_INSTANCE_TYPE] == "ontology:ArcTask"
    assert inst.pin.version == 4
    # nothing leaked into the other two rooms
    assert sum(len(g.nodes) for g in mm.capacity_mm.graphs.values()) == 0
    assert sum(len(g.nodes) for g in mm.intelligence_mm.graphs.values()) == 0


def test_monotone_grow_one_graph_node_per_iri():
    mm = _mm()
    r = MMResolver(mm, _corpus_source())
    a = r.get_or_instantiate(CORPUS_IRI)
    b = r.get_or_instantiate(CORPUS_IRI)
    assert a is b
    graph = next(
        g for g in mm.knowledge_mm.graphs.values() if g.role == INSTANCE_GRAPH_ROLE
    )
    assert len(graph.nodes) == 1


def test_unroutable_iri_rejected_before_any_write():
    mm = _mm()
    r = MMResolver(mm, _Source({}))
    with pytest.raises(KeyError):
        r.get_or_instantiate("unknown:thing")
    assert sum(len(g.nodes) for g in mm.knowledge_mm.graphs.values()) == 0
    assert sum(len(g.nodes) for g in mm.capacity_mm.graphs.values()) == 0


# ── mm_handle: a reads_mm=True body reads a written value (CR test 1) ──────


class _FakeSession:
    session_id = "s-1"
    user_id = "u-1"
    actor_role = "user"
    capabilities: set = set()

    def has(self, capability: str) -> bool:
        return False


def _reads_mm_layer(target_iri):
    layer = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    layer.register_datastate(
        DataState(name="test.in", shape=ShapeDescriptor.scalar("str")),
        allow_new_realm=True,
    )
    layer.register_datastate(
        DataState(name="test.out", shape=ShapeDescriptor.scalar("str")),
        allow_new_realm=True,
    )

    def _body(**kwargs):
        # read the corpus entry through the injected MM handle
        inst = kwargs["context"].mm_handle.get_or_instantiate(target_iri)
        return {DS_OUT: inst.payload}

    layer.register_capacity(
        Capacity(
            name="read_corpus",
            category=CATEGORY_PERCEPTION,
            inputs=(DS_IN,),
            outputs=(DS_OUT,),
            reads_mm=True,
            implementation=_body,
        )
    )
    return layer, capacity_iri(CATEGORY_PERCEPTION, "read_corpus")


def test_reads_mm_body_reads_written_value_via_mmresolver_handle():
    mm = _mm()
    resolver = MMResolver(mm, _corpus_source(payload="grid-7"))
    layer, iri = _reads_mm_layer(CORPUS_IRI)
    dispatcher = L4Dispatcher(layer, session=_FakeSession(), mm_handle=resolver)

    result = dispatcher.dispatch(iri, {DS_IN: "ignored"})

    assert result.success
    assert result.outputs[DS_OUT] == "grid-7"
    # the read populated knowledge_mm through the handle
    assert any(CORPUS_IRI in g.nodes for g in mm.knowledge_mm.graphs.values())


# ── DQ-1 provenance XRef: arc1 target / arc3 None ─────────────────────────


def test_link_provenance_arc1_writes_instance_of_xref():
    mm = _mm()
    # the knowledge writer mints the corpus-entry instance (the XRef target)
    MMResolver(mm, _corpus_source()).get_or_instantiate(CORPUS_IRI)
    w = _writer(mm)
    root = w.root(RAW_TASK, value="ingress")

    xref = w.link_provenance(
        root, target_id=CORPUS_IRI, target_role=INSTANCE_GRAPH_ROLE
    )

    assert xref is not None
    assert xref.ref_type == "INSTANCE_OF"
    assert xref.source_id == root
    assert xref.target_id == CORPUS_IRI
    assert xref.target_metagraph_id == mm.knowledge_mm.metagraph_id
    assert xref.xref_id in mm.capacity_mm.xrefs


def test_link_provenance_arc3_none_writes_no_row():
    mm = _mm()
    w = _writer(mm)
    root = w.root(RAW_TASK, value="ingress")

    assert (
        w.link_provenance(root, target_id=None, target_role=INSTANCE_GRAPH_ROLE)
        is None
    )
    assert mm.capacity_mm.xrefs == {}


def test_link_provenance_requires_existing_knowledge_target():
    mm = _mm()
    w = _writer(mm)
    root = w.root(RAW_TASK, value="ingress")
    # no knowledge instance minted -> target absent under the role (P59
    # validate-before-WAL rejects; no row leaks)
    with pytest.raises(XRefIntegrityError):
        w.link_provenance(root, target_id=CORPUS_IRI, target_role=INSTANCE_GRAPH_ROLE)
    assert mm.capacity_mm.xrefs == {}


# ── KnowledgeMMSource adapter (KL-backed) ─────────────────────────────────


class _KLNode:
    def __init__(self, node_id, value, type_name, version):
        self.node_id = node_id
        self.value = value
        self.type_name = type_name
        self.properties = {"version": version}


class _FakeKL:
    def __init__(self, node):
        self._node = node

    def read_at_version(self, iri, version):
        return self._node if self._node.node_id == iri else None


def test_knowledge_mm_source_reads_kl_node():
    src = KnowledgeMMSource(
        _FakeKL(_KLNode(CORPUS_IRI, "grid", "ontology:ArcTask", 5))
    )
    sn = src.get_node(CORPUS_IRI)
    assert sn.iri == CORPUS_IRI
    assert sn.version == 5
    assert sn.type_iri == "ontology:ArcTask"
    assert sn.payload == "grid"
    with pytest.raises(KeyError):
        src.get_node("ontology:missing")
