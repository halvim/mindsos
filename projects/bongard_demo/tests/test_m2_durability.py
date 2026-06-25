"""m2 durability de-risk: a nested COMPOSITE_DAG descriptor survives the
FalkorDBLocalPersister across a simulated restart and re-invokes with no
code registration of the composite itself.

The F9 round-trip test (tests/f9) only carried a flat ``steps`` list, so the
nested-dict-through-the-real-persister path is untested. This is the m2
first build (PLAN m2 SCOPE LOCKED 2026-06-23): fail fast on the only
unproven piece before the teach/naming layer is built on top.

Two tests:
  * codec round-trip (always-on, no DB) — the nested COMPOSITE_DAG dict
    survives the ADR-0182 node-value codec and Pipeline.from_dict.
  * durable restart (integration, live FalkorDB) — persist -> fresh
    KL/CL -> boot_local -> invoke the minted composite.
"""

from __future__ import annotations

import uuid

import pytest


CAPABILITY = "m2demo.shout"
REACTIVATION = "m2_composite"


@pytest.fixture
def falkor_client():
    """Fresh ephemeral FalkorDB graph per test; skips if no live sidecar.

    Self-contained: the demo gate's sys.path does not include the core
    ``tests/`` tree, so this does not import ``tests._shared``.
    """
    try:
        from mindsos_core.config import FalkorConfig
        from mindsos_core.persistence import FalkorClient
    except Exception as e:
        pytest.skip(f"FalkorClient import failed: {e}")
    base = FalkorConfig.from_env()
    config = FalkorConfig(
        host=base.host, port=base.port, password=base.password,
        graph=f"test_{uuid.uuid4().hex[:8]}",
    )
    try:
        client = FalkorClient(config)
    except Exception as e:
        pytest.skip(f"FalkorDB unreachable at {config.host}:{config.port}: {e}")
    try:
        yield client
    finally:
        try:
            client.run_query("MATCH (n) DETACH DELETE n")
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass


def _vocab():
    """Build the demo DataStates + leaf capacities + the composite Pipeline.

    Returns ``(datastates, leaves, pipeline, descriptor)`` where the
    descriptor is the learned-parameters value dict carrying the nested
    COMPOSITE_DAG. Leaf bodies are trivial string transforms; the point
    is the composite's persisted DAG, not the leaves.
    """
    from mindsos_capacity import (
        COMPOSITE_DAG,
        CATEGORY_PERCEPTION,
        Capacity,
        DAGEdge,
        DAGStep,
        DataState,
        Pipeline,
        REACTIVATION_KEY,
        ShapeDescriptor,
    )
    from mindsos_capacity.pipeline import START

    ds_in = DataState(name="m2demo.in", shape=ShapeDescriptor.scalar("str", opaque_tag="m2demo.in"))
    ds_mid = DataState(name="m2demo.mid", shape=ShapeDescriptor.scalar("str", opaque_tag="m2demo.mid"))
    ds_out = DataState(name="m2demo.out", shape=ShapeDescriptor.scalar("str", opaque_tag="m2demo.out"))

    i, m, o = ds_in.iri, ds_mid.iri, ds_out.iri
    leaf_a = Capacity(
        name="m2demo.upper", category=CATEGORY_PERCEPTION,
        inputs=(i,), outputs=(m,),
        implementation=lambda **kw: {m: kw[i].upper()},
    )
    leaf_b = Capacity(
        name="m2demo.exclaim", category=CATEGORY_PERCEPTION,
        inputs=(m,), outputs=(o,),
        implementation=lambda **kw: {o: kw[m] + "!"},
    )

    pipeline = Pipeline(
        start_datastates=(i,),
        target_datastate=o,
        steps=(
            DAGStep(leaf_a.iri, (i,), (m,)),
            DAGStep(leaf_b.iri, (m,), (o,)),
        ),
        edges=(DAGEdge(START, 0, i), DAGEdge(0, 1, m)),
    )
    descriptor = {
        "capability": CAPABILITY,
        REACTIVATION_KEY: REACTIVATION,
        "category": CATEGORY_PERCEPTION,
        "inputs": [i],
        "outputs": [o],
        "node_kind": "reactive",
        COMPOSITE_DAG: pipeline.to_dict(),
    }
    return (ds_in, ds_mid, ds_out), (leaf_a, leaf_b), pipeline, descriptor


def _composite_factory(cl):
    """Reactivation factory that rebuilds the composite, binding a closure
    that runs the stored DAG via ``cl.invoke`` (the executor is re-supplied
    at boot, never serialized — the F9 pattern). The session is read from
    the read-path context dict; the sub-capacities are resolved Local."""
    from mindsos_capacity import COMPOSITE_DAG, Capacity, Pipeline

    def factory(desc):
        pipeline = Pipeline.from_dict(desc[COMPOSITE_DAG])
        in_iri = desc["inputs"][0]
        out_iri = desc["outputs"][0]

        def run(**kw):
            ctx = kw.get("context") or {}
            session = ctx.get("session")
            values = {in_iri: kw[in_iri]}
            for step in pipeline.steps:
                inputs = {ds: values[ds] for ds in step.input_datastates}
                result = cl.invoke(step.capacity_iri, inputs, session=session)
                if not result.success:
                    raise result.error
                values.update(result.outputs)
            return {out_iri: values[out_iri]}

        return Capacity(
            name=desc["capability"],
            category=desc["category"],
            inputs=tuple(desc["inputs"]),
            outputs=tuple(desc["outputs"]),
            implementation=run,
        )

    return factory


def _write_descriptor(kl, user_id, descriptor):
    """Write the learned-parameters descriptor node into the user's Local
    (mirrors tests/f9 _write_descriptor); the dict value carries the nested
    COMPOSITE_DAG that the ADR-0182 codec must round-trip."""
    from mindsos_knowledge import (
        ROLE_LEARNED_PARAMETERS,
        ensure_local_role_graph,
        learned_parameter_iri,
    )
    from mindsos_knowledge.schemas.learned_parameters import NODE_LEARNED_PARAMETER

    local_mg = kl.local_metagraph(user_id)
    g = ensure_local_role_graph(local_mg, ROLE_LEARNED_PARAMETERS)
    node_iri = learned_parameter_iri("v1", descriptor["capability"])
    g.add_node(
        dict(descriptor),
        NODE_LEARNED_PARAMETER,
        properties={
            "parameter_set_iri": f"taught:{descriptor['capability']}",
            "confidence": 1.0,
        },
        node_id=node_iri,
    )
    return local_mg


def test_nested_composite_dag_codec_roundtrip():
    """Always-on (no DB): the nested COMPOSITE_DAG dict survives the
    ADR-0182 node-value codec and rebuilds an identical Pipeline."""
    from mindsos_capacity import COMPOSITE_DAG, Pipeline
    from mindsos_core.persistence.value_codec import (
        decode_node_value,
        encode_node_value,
    )

    _, _, pipeline, descriptor = _vocab()
    raw, value_json = encode_node_value(descriptor)
    assert raw is None and value_json is not None  # stored as nested JSON
    decoded = decode_node_value(raw, value_json)
    assert Pipeline.from_dict(decoded[COMPOSITE_DAG]) == pipeline


@pytest.mark.integration
def test_durable_local_roundtrip_reactivates_composite(falkor_client):
    """Persist a composite descriptor -> fresh KL/CL (restart) -> boot_local
    re-activates it from the durable descriptor -> invoke runs the stored DAG
    with NO code registration of the composite."""
    from mindsos_capacity import (
        CapacityLayer,
        CATEGORY_PERCEPTION,
        register_reactivation_factory,
        unregister_reactivation_factory,
    )
    from mindsos_knowledge import KnowledgeLayer
    from mindsos_server.local_boot import boot_local
    from mindsos_server.persistence import FalkorDBLocalPersister
    from mindsos_server.session import Session

    user_id = "m2user"
    (ds_in, ds_mid, ds_out), (leaf_a, leaf_b), _, descriptor = _vocab()
    persister = FalkorDBLocalPersister(falkor_client)

    # Pre-restart: write the durable descriptor + persist the Local.
    kl1 = KnowledgeLayer.bootstrap()
    local_mg = _write_descriptor(kl1, user_id, descriptor)
    persister.save(user_id, local_mg)

    # Simulated restart: fresh KL/CL (empty declarations + index).
    kl2 = KnowledgeLayer.bootstrap()
    cl2 = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    # The atoms (DataStates + leaf capacities) are re-registered from code
    # each boot; only the learned composite re-activates from its descriptor.
    session = Session.for_testing(user_id)
    cl2.register_datastate(ds_in, session=session, allow_new_realm=True)
    cl2.register_datastate(ds_mid, session=session, allow_new_realm=True)
    cl2.register_datastate(ds_out, session=session, allow_new_realm=True)
    cl2.register_capacity(leaf_a, session=session)
    cl2.register_capacity(leaf_b, session=session)
    register_reactivation_factory(REACTIVATION, _composite_factory(cl2), if_exists="upsert")
    try:
        mg, minted, reactivated = boot_local(cl2, kl2, persister, user_id, session=session)
        assert minted is False
        assert reactivated == [f"capacity:{CATEGORY_PERCEPTION}:{CAPABILITY}"]

        result = cl2.invoke(
            f"capacity:{CATEGORY_PERCEPTION}:{CAPABILITY}",
            {ds_in.iri: "hi"},
            session=session,
        )
        assert result.success, result.error
        assert result.outputs[ds_out.iri] == "HI!"
    finally:
        unregister_reactivation_factory(REACTIVATION)
        persister.delete(user_id)
