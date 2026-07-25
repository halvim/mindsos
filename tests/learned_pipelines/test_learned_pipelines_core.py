"""ADR-0203 — learned-pipelines Local role + writer/reader (non-Falkor).

Covers the substrate that needs no live FalkorDB: role closure + scope,
schema shape, IRI round-trip, the ADR-0182 value-codec round-trip on a
**converging** DAG (the in-memory half of the save→reload gate), and the
``learn_pipeline`` append / ``iter_local_pipelines`` max-ordinal semantics.
The persist→reload half is the Falkor-gated
``test_learn_pipeline_roundtrip.py`` integration test.
"""

from __future__ import annotations

from mindsos_capacity.pipeline import DAGEdge, DAGStep, Pipeline, START
from mindsos_core.persistence.value_codec import (
    decode_node_value,
    encode_node_value,
)
from mindsos_knowledge import (
    ALL_ROLES,
    KnowledgeLayer,
    ROLE_LEARNED_PIPELINES,
    learned_pipeline_iri,
    parse_iri,
)
from mindsos_knowledge.bootstrap import (
    _GLOBAL_NAMED_ROLES,
    _LOCAL_NAMED_ROLES,
)
from mindsos_knowledge.schemas import schema_for_role
from mindsos_knowledge.schemas._base import Discipline
from mindsos_knowledge.schemas.learned_pipelines import (
    LEARNED_PIPELINE_CONTENT_FIELDS,
    LEARNED_PIPELINE_METADATA_FIELDS,
    NODE_LEARNED_PIPELINE,
    build_learned_pipelines_schema,
)
from mindsos_server.pipelines import (
    iter_local_pipelines,
    iter_pipelines,
    learn_pipeline,
)


def _converging_pipeline() -> Pipeline:
    """A real fan-in DAG: signature ← power_features + raw_harmonics.

    Two upstream producers converge on step 2 (distinct producers of
    distinct datastates). A linear fixture cannot exercise ``edges``.
    """
    return Pipeline(
        start_datastates=("ds:raw_power", "ds:raw_current"),
        target_datastate="ds:steady_signature",
        steps=(
            DAGStep("cap:featurize_power", ("ds:raw_power",), ("ds:power_features",)),
            DAGStep("cap:harmonics", ("ds:raw_current",), ("ds:raw_harmonics",)),
            DAGStep(
                "cap:signature",
                ("ds:power_features", "ds:raw_harmonics"),
                ("ds:steady_signature",),
            ),
        ),
        edges=(
            DAGEdge(START, 0, "ds:raw_power"),
            DAGEdge(START, 1, "ds:raw_current"),
            DAGEdge(0, 2, "ds:power_features"),
            DAGEdge(1, 2, "ds:raw_harmonics"),
        ),
    )


# ── role closure + scope ──────────────────────────────────────────────


def test_role_is_in_closed_set_and_local_only() -> None:
    assert ROLE_LEARNED_PIPELINES in ALL_ROLES
    assert len(ALL_ROLES) == 15
    assert ROLE_LEARNED_PIPELINES in _LOCAL_NAMED_ROLES
    assert ROLE_LEARNED_PIPELINES not in _GLOBAL_NAMED_ROLES


def test_schema_is_single_type_zero_edge_immutable_successor() -> None:
    s = build_learned_pipelines_schema()
    assert s.mutation_discipline == Discipline.IMMUTABLE_SUCCESSOR
    assert schema_for_role(ROLE_LEARNED_PIPELINES).mutation_discipline == (
        Discipline.IMMUTABLE_SUCCESSOR
    )
    # content/metadata partition: pipeline_name is frozen content; the
    # append ordinal is metadata.
    assert LEARNED_PIPELINE_CONTENT_FIELDS == frozenset({"pipeline_name"})
    assert "taught_seq" in LEARNED_PIPELINE_METADATA_FIELDS


def test_iri_round_trips() -> None:
    iri = learned_pipeline_iri("v1", pipeline_name="sig", record_id="3")
    assert iri == "learned-pipelines-v1:pipeline:sig:3"
    p = parse_iri(iri)
    assert p.full == iri
    assert p.role == ROLE_LEARNED_PIPELINES
    assert p.version == "v1"
    assert p.kind == "pipeline"


# ── ADR-0182 value-codec round-trip on a converging DAG ───────────────


def test_converging_dag_survives_value_codec() -> None:
    """The exact persist serialization (encode → decode) is lossless for a
    converging DAG: ``edges`` + ``start_datastates`` survive."""
    p = _converging_pipeline()
    raw, vjson = encode_node_value(p.to_dict())
    assert raw is None and vjson is not None  # structured → _value_json
    loaded = Pipeline.from_dict(decode_node_value(raw, vjson))
    assert loaded == p
    assert loaded.edges == p.edges
    assert loaded.start_datastates == p.start_datastates
    fanin = [e for e in loaded.edges if e.consumer == 2]
    assert len(fanin) == 2 and {e.producer for e in fanin} == {0, 1}


# ── writer append + reader max-ordinal (in-memory KL, no persist) ─────


def test_learn_pipeline_appends_and_reader_returns_it() -> None:
    kl = KnowledgeLayer.bootstrap()
    p = _converging_pipeline()
    node = learn_pipeline(kl, "alice", "appliance_signature", p)
    assert node.type_name == NODE_LEARNED_PIPELINE
    assert node.properties["pipeline_name"] == "appliance_signature"
    assert node.properties["taught_seq"] == 1

    got = list(iter_local_pipelines(kl, "alice"))
    assert len(got) == 1
    # the full to_dict blob (incl edges) round-trips off the stored node
    assert Pipeline.from_dict(got[0].value) == p

    # iter_pipelines(scope=...) contract stable: ("learned", node)
    both = list(iter_pipelines(kl, "alice", "both"))
    assert ("learned", got[0]) in both
    assert list(iter_pipelines(kl, "alice", "local")) == [("learned", got[0])]


def test_two_teaches_of_one_name_accumulate_reader_returns_max_ordinal() -> None:
    kl = KnowledgeLayer.bootstrap()
    v1 = _converging_pipeline()
    # a distinct second version of the SAME name (extra start datastate)
    v2 = Pipeline(
        start_datastates=v1.start_datastates + ("ds:ambient_temp",),
        target_datastate=v1.target_datastate,
        steps=v1.steps,
        edges=v1.edges,
    )
    learn_pipeline(kl, "alice", "appliance_signature", v1)
    learn_pipeline(kl, "alice", "appliance_signature", v2)

    # BOTH nodes persist (append, not replace) — immutable_successor.
    from mindsos_server.pipelines import _iter_learned_pipeline_nodes
    all_nodes = _iter_learned_pipeline_nodes(kl, "alice")
    assert len(all_nodes) == 2
    assert [n.properties["taught_seq"] for n in all_nodes] == [1, 2]

    # reader returns exactly one row (the max-ordinal = latest teach).
    latest = list(iter_local_pipelines(kl, "alice"))
    assert len(latest) == 1
    assert latest[0].properties["taught_seq"] == 2
    assert Pipeline.from_dict(latest[0].value) == v2


def test_distinct_names_each_yield_latest() -> None:
    kl = KnowledgeLayer.bootstrap()
    p = _converging_pipeline()
    learn_pipeline(kl, "alice", "sig", p)
    learn_pipeline(kl, "alice", "cyc", p)
    learn_pipeline(kl, "alice", "sig", p)  # re-teach sig → seq 3
    latest = list(iter_local_pipelines(kl, "alice"))
    names = [n.properties["pipeline_name"] for n in latest]
    assert names == ["cyc", "sig"]  # name-sorted, one row per name
    by_name = {n.properties["pipeline_name"]: n for n in latest}
    assert by_name["sig"].properties["taught_seq"] == 3
