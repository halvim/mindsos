import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FAIL = "FAIL"
PASS = "PASS"

try:
    from mindsos_core.config import FalkorConfig
    from mindsos_core.persistence.client import FalkorClient
    from mindsos_capacity.identifiers import EDGE_PRODUCES, EDGE_CONSUMES
    from mindsos_capacity.views import CapacityLayerView
    from mindsos_capacity.exceptions import WriteHandleNotWiredError
    from mindsos_knowledge.knowledge_layer import _local_metagraph_name
    from mindsos_server.persistence.local_persister import FalkorDBLocalPersister
    from mindsos_knowledge.schemas.concepts import build_concepts_schema
    from mindsos_knowledge.schemas.task_patterns import build_task_patterns_schema
    from tests.phase_30._fixtures import build_branching_capacity_layer
except Exception:
    print("IMPORT-STAGE FAILED — a §13 symbol moved; fix the import before probing")
    traceback.print_exc()
    sys.exit(2)

PROBE_USER = "__skillverify_probe__"


def count_bipartite(mg):
    prod = 0
    cons = 0
    for edge in mg.iter_intergraph_edges():
        if edge.type_name == EDGE_PRODUCES:
            prod += 1
        elif edge.type_name == EDGE_CONSUMES:
            cons += 1
    return prod, cons


def first_producer_id(mg):
    for edge in mg.iter_intergraph_edges():
        if edge.type_name == EDGE_PRODUCES:
            return edge.source_node_id
    return None


def probe_roundtrip(persister):
    print("=== P2/P3 — bipartite round-trip through FalkorDBLocalPersister ===")
    cl = build_branching_capacity_layer()
    mg = cl.global_metagraph()
    mg.name = _local_metagraph_name(PROBE_USER)

    base_prod, base_cons = count_bipartite(mg)
    print(f"[baseline]   in-memory   PRODUCES={base_prod}  CONSUMES={base_cons}")

    persister.save(PROBE_USER, mg)
    reloaded = persister.load(PROBE_USER)
    if reloaded is None:
        print("[reloaded]   None — persister.load returned nothing")
        return FAIL, base_prod, base_cons, 0, 0

    re_prod, re_cons = count_bipartite(reloaded)
    print(f"[reloaded]   from-Falkor PRODUCES={re_prod}  CONSUMES={re_cons}")

    cap_id = first_producer_id(reloaded)
    view = CapacityLayerView(reloaded)
    read_outputs = view.outputs_of(cap_id) if cap_id is not None else []
    print(f"[read-path]  CapacityLayerView.outputs_of({cap_id!r}) -> {read_outputs}")

    edges_ok = (
        re_prod == base_prod and re_cons == base_cons and re_prod > 0 and re_cons > 0
    )
    read_ok = bool(read_outputs)
    verdict = PASS if (edges_ok and read_ok) else FAIL
    return verdict, base_prod, base_cons, re_prod, re_cons


def probe_schema():
    print("=== P-schema — Schema.validate_node_properties reachable standalone ===")
    verdict = PASS
    for name, builder in (
        ("concepts", build_concepts_schema),
        ("task-patterns", build_task_patterns_schema),
    ):
        schema = builder(strict=True)
        try:
            schema.validate_node_properties("Concept", {"iri": "probe://x"})
            print(f"[{name}] returned cleanly — reachable, no write-gate")
        except WriteHandleNotWiredError:
            print(f"[{name}] {FAIL} — hit WriteHandleNotWiredError (D7 surface wrong)")
            verdict = FAIL
        except Exception as exc:
            print(f"[{name}] reachable — {type(exc).__name__} (not the write-gate)")
    return verdict


def main():
    client = FalkorClient(FalkorConfig.from_env())
    persister = FalkorDBLocalPersister(client)

    roundtrip_verdict = FAIL
    try:
        roundtrip_verdict, bp, bc, rp, rc = probe_roundtrip(persister)
    except Exception:
        print("[P2/P3] EXCEPTION during round-trip probe")
        traceback.print_exc()
    finally:
        try:
            persister.delete(PROBE_USER)
            print(f"[cleanup]    deleted probe Local {PROBE_USER!r}")
        except Exception:
            print("[cleanup]    delete failed — remove the probe Local manually")

    schema_verdict = FAIL
    try:
        schema_verdict = probe_schema()
    except Exception:
        print("[P-schema] EXCEPTION during schema probe")
        traceback.print_exc()

    print("=== VERDICT ===")
    print(f"P2/P3 bipartite round-trip : {roundtrip_verdict}")
    print(f"P-schema validation path   : {schema_verdict}")
    if roundtrip_verdict == PASS:
        print(
            "Bipartite edges DO round-trip. Approach C is technically viable, BUT the "
            "standard boot (bootstrap_kl_from_falkordb + boot_local) persists only "
            "local_knowledge and REACTIVATES L3 — so the verifier must either "
            "explicitly persist+read the capacity metagraph or reactivate. Prefer C'."
        )
    else:
        print(
            "Bipartite edges do NOT survive the persister round-trip. Approach C is "
            "dead as written — adopt C' (boot via boot_local, reactivate, read views)."
        )


if __name__ == "__main__":
    main()
