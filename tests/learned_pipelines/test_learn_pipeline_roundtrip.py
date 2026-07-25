"""ADR-0203 — learned-pipeline durable save→reload round-trip (the gate).

Integration: ``learn_pipeline`` a converging DAG into a Local →
``FalkorDBLocalPersister.save`` → fresh KL (simulated restart) →
``persister.load`` + ``install_local_metagraph`` → ``iter_local_pipelines``
returns the pipeline with ``edges`` + ``start_datastates`` INTACT, and two
teaches of one name reload to the max-ordinal node.

Marked ``@pytest.mark.integration``; auto-skipped when no live FalkorDB
sidecar is reachable (the cumulative Linux gate provides one). A linear-only
fixture would be insufficient — the converging fan-in is the point.
"""

from __future__ import annotations

import pytest

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture

pytestmark = pytest.mark.integration


def _converging_pipeline():
    from mindsos_capacity.pipeline import DAGEdge, DAGStep, Pipeline, START

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


def _reload(persister, user_id):
    """Simulate a restart: fresh KL, load the persisted Local into it."""
    from mindsos_knowledge import KnowledgeLayer

    kl2 = KnowledgeLayer.bootstrap()
    dump = persister.load(user_id)
    assert dump is not None, "persisted Local not found on reload"
    kl2.install_local_metagraph(user_id, dump)
    return kl2


def test_converging_dag_survives_save_reload(falkor_client):
    from mindsos_capacity.pipeline import Pipeline
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_server.persistence import FalkorDBLocalPersister
    from mindsos_server.pipelines import iter_local_pipelines, learn_pipeline

    user_id = "alice"
    persister = FalkorDBLocalPersister(falkor_client)
    try:
        kl1 = KnowledgeLayer.bootstrap()
        original = _converging_pipeline()
        learn_pipeline(kl1, user_id, "appliance_signature", original)
        persister.save(user_id, kl1.local_metagraph(user_id))

        kl2 = _reload(persister, user_id)
        rows = list(iter_local_pipelines(kl2, user_id))
        assert len(rows) == 1
        reloaded = Pipeline.from_dict(rows[0].value)

        assert reloaded == original
        assert reloaded.edges == original.edges  # converging structure intact
        assert reloaded.start_datastates == original.start_datastates
        fanin = [e for e in reloaded.edges if e.consumer == 2]
        assert len(fanin) == 2 and {e.producer for e in fanin} == {0, 1}
    finally:
        persister.delete(user_id)


def test_two_teaches_reload_to_max_ordinal(falkor_client):
    from mindsos_capacity.pipeline import Pipeline
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_server.persistence import FalkorDBLocalPersister
    from mindsos_server.pipelines import (
        _iter_learned_pipeline_nodes,
        iter_local_pipelines,
        learn_pipeline,
    )

    user_id = "bob"
    persister = FalkorDBLocalPersister(falkor_client)
    try:
        kl1 = KnowledgeLayer.bootstrap()
        v1 = _converging_pipeline()
        v2 = Pipeline(
            start_datastates=v1.start_datastates + ("ds:ambient_temp",),
            target_datastate=v1.target_datastate,
            steps=v1.steps,
            edges=v1.edges,
        )
        learn_pipeline(kl1, user_id, "appliance_signature", v1)
        learn_pipeline(kl1, user_id, "appliance_signature", v2)
        persister.save(user_id, kl1.local_metagraph(user_id))

        kl2 = _reload(persister, user_id)
        # both immutable nodes survive the reload (append, not replace).
        assert len(_iter_learned_pipeline_nodes(kl2, user_id)) == 2
        # reader returns exactly the max-ordinal (latest) teach.
        latest = list(iter_local_pipelines(kl2, user_id))
        assert len(latest) == 1
        assert latest[0].properties["taught_seq"] == 2
        assert Pipeline.from_dict(latest[0].value) == v2
    finally:
        persister.delete(user_id)
