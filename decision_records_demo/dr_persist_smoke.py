"""dr_persist_smoke — persist real Decision Records grounding graphs, read them back, raw.

This is the persistence-smoke item's command (RULES §12 / plan §2.11 next-item):
it runs the SAME real machinery `dr_dump` runs (`execution.run` →
`execute_pipeline`), then closes each run the way production closes one —
`consolidate_request` → `persist_capacity_mm` → a real FalkorDB — and prints
what comes BACK from the store, unedited.

THE ACCEPTANCE (critic §24, the sixth renderer-bank requirement): no grounding
graph carries WHEN the run happened; the date arrives on the **Episode** at
persistence. This smoke must SHOW `consolidated_at` arriving — it prints the
Episode's properties raw, and exits non-zero if the field is absent.

RULES §11 seam, stated up front: the section headers, the `graph[n]` / `node`
/ `edge` prefixes, the LIVE/PERSISTED labels and the field ordering are THIS
SCRIPT'S framing. Every value after a colon is `repr()` of what the system
emitted or what FalkorDB returned, with nothing translated, prettified or
omitted.

What one pass does, per case (`claim` = 3 exposures + fold; `boundary` = zero
exposures, the reducer refuses):

    1. run the case through `execution.run` (real graphs in `capacity_mm`)
    2. `consolidate_request(... mm_persister=FalkorMMPersister, capacity_graphs=...)`
       — the production close: run graphs + task index to Falkor, Episode
       upserted into the KL's episodic_memories role with `consolidated_at` /
       `capacity_root_ref` / `outcome_classification`
    3. print the Episode node raw (properties included — the acceptance)
    4. `load_graph` the `capacity_root_ref` index BACK from Falkor, raw
    5. `load_graph` every referenced run graph BACK from Falkor, raw
    6. ASSERT live==persisted per node id — value AND properties equality —
       which pins the verdicts LIST order (member identity, §14), the refusal
       wording and the trimmed conclusion; plus edge-set and count equality
       (critic §27: a displayed value is not a checked value)

A real FalkorDB is REQUIRED (`FALKORDB_HOST`/`FALKORDB_PORT`, default
localhost:6379). If it is unreachable the smoke prints the raw probe error and
exits 3 — an unreachable store is a result, not a skip. The smoke runs on the
HOST (the test image deliberately does not bake `decision_records_demo/` — a
demo is not in the core image, RULES §1 — and the compose falkordb service
publishes no host port since the 2026-07-04 `-p` isolation fix), so on the
Linux box it is a standalone container — on host port 6382, because 6379 is
held by a stray container there and 6380/6381 by the arc demos (S-2,
coordination §51.2: this box previously said 6379 and failed on the reference
machine — docs that fail cold are operator intervention):

    docker run --rm -d --name drdemo-falkor -p 6382:6379 falkordb/falkordb
    PYTHONPATH=. FALKORDB_PORT=6382 /tmp/drdemo-venv/bin/python decision_records_demo/dr_persist_smoke.py
    docker rm -f drdemo-falkor

This file is demo code (RULES §3): it registers its own vocabulary plus the
core `consolidate` builtin family into its own layer instance and never edits
`mindsos_*`. It needs the `falkordb` driver (requirements-demo.in) — unlike
`dr_dump.py`, which stays zero-dep.
"""

from __future__ import annotations

import sys

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.consolidate import install_consolidate_capacities
from mindsos_capacity.context import make_writeable
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.identifiers import CATEGORY_DERIVATION
from mindsos_core.config import FalkorConfig
from mindsos_core.persistence.client import FalkorClient
from mindsos_core.reconstruction.graph_loader import load_graph
from mindsos_intelligence import execution
from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.consolidation import consolidate_request
from mindsos_intelligence.dispatch import L4Dispatcher
from mindsos_intelligence.mm import MentalModel
from mindsos_intelligence.mm_persister import FalkorMMPersister
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.knowledge_layer import KnowledgeLayer

from decision_records_demo.dr_dump import (
    COLLECTIONS,
    DESCRIPTIONS,
    DS_CLAIM_EXPOSURES,
    EXPOSURES,
    _Session,
    _claim_plan,
    _conclude_declaration,
    _decide,
    _decide_declaration,
)


def _harness_with_consolidation(scope: str = "drdemo-task"):
    """The dr_dump claim harness + the core consolidate builtin + a KL.

    Rebuilt here rather than reusing ``dr_dump._harness`` because consolidation
    needs the layer instance (to install the builtin family) and a
    KnowledgeLayer on the dispatcher (the Episode write handle comes from
    ``context.writeable``).

    ``scope`` is the ChainArtifactWriter's request scope, and callers that
    PERSIST must pass a case-unique value (the episode id): node ids in the
    store are deterministic from ``(scope, run_ref, seq)`` and the persister
    MERGEs nodes globally by id (``builders.py:164``), so two persisted cases
    sharing a scope silently steal each other's nodes — coordination §55, found
    by the first from-root render. Core's own contract says the caller passes a
    task-unique scope (``chain_artifacts.py:198–201``).
    """
    session = _Session()
    layer = CapacityLayer()
    for name, description in DESCRIPTIONS.items():
        layer.register_datastate(
            DataState(
                name=name,
                shape=ShapeDescriptor.opaque(name),
                description=description,
                provenance_category=CATEGORY_DERIVATION,
                **COLLECTIONS.get(name, {}),
            ),
            session=session,
            allow_new_realm=True,
        )
    layer.register_capacity(_decide_declaration(_decide), session=session)
    layer.register_capacity(_conclude_declaration(), session=session)
    install_consolidate_capacities(layer)
    kl = KnowledgeLayer.bootstrap()
    mm = MentalModel(session_id="drdemo-session", user_id="drdemo-user")
    dispatcher = L4Dispatcher(layer, session=session, kl=kl)
    writer = ChainArtifactWriter(mm, scope)
    return session, kl, mm, dispatcher, writer, writer.emit_request_run()


def _dump_loaded_graph(tag: str, graph) -> None:
    print(f"{tag} graph_id={graph.graph_id!r} role={graph.role!r}")
    for node in graph.nodes.values():
        print(f"  node type={node.type_name!r}")
        print(f"       properties={node.properties!r}")
        print(f"       value={node.value!r}")
    for edge in graph.edges.values():
        print(
            f"  edge {edge.source.type_name!r}"
            f" -[{edge.type_name}]-> {edge.target.type_name!r}"
        )


def _graph_value_failures(live, loaded) -> int:
    """Assert the loaded graph equals the live one where it matters (critic §27).

    Per node id: value equality (pins LIST order — member identity under the
    §14 ruling — plus the refusal wording and the trimmed conclusion) and
    properties equality. Plus edge-set equality on (source, type, target).
    Dict KEY order is legitimately not preserved by the store and dict ``==``
    ignores it; list ``==`` does not — exactly the asymmetry S-F1 recorded.
    Returns the number of failures, printing each raw.
    """
    failures = 0
    if set(live.nodes.keys()) != set(loaded.nodes.keys()):
        print(f"VALUE FAIL: node id sets differ live={sorted(live.nodes)!r} loaded={sorted(loaded.nodes)!r}")
        return 1
    for node_id, live_node in live.nodes.items():
        loaded_node = loaded.nodes[node_id]
        if (loaded_node.value != live_node.value
                or (loaded_node.properties or {}) != (live_node.properties or {})):
            print(f"VALUE FAIL node id={node_id!r} type={live_node.type_name!r}")
            print(f"  live      value={live_node.value!r} properties={live_node.properties!r}")
            print(f"  persisted value={loaded_node.value!r} properties={loaded_node.properties!r}")
            failures += 1
    live_edges = {(e.source.node_id, e.type_name, e.target.node_id) for e in live.edges.values()}
    loaded_edges = {(e.source.node_id, e.type_name, e.target.node_id) for e in loaded.edges.values()}
    if live_edges != loaded_edges:
        print(f"VALUE FAIL: edge sets differ live={sorted(live_edges)!r} loaded={sorted(loaded_edges)!r}")
        failures += 1
    return failures


def _run_case(name: str, exposures, episode_id: str, client):
    """Run one case end to end.

    Returns ``(failures, capacity_root_ref, live_by_id)`` so ``main`` can run
    the END-STATE re-verify (s55): a later case must not have stolen this
    case's nodes, and only a reader that comes back AFTER the last write can
    see that."""
    print(f"== case: {name} ==")
    session, kl, mm, dispatcher, writer, request_run = _harness_with_consolidation(scope=episode_id)
    graphs: list = []
    execution.run(
        dispatcher, writer, _claim_plan(), request_run,
        mm=mm,
        solve_seed={DS_CLAIM_EXPOSURES: list(exposures)},
        capacity_graphs=graphs,
        case_label=f"claim CLM-2041 ({name})",
    )
    live_by_id = {g.graph_id: g for g in graphs}
    print(f"live run graphs: {len(graphs)}")
    for g in graphs:
        print(f"  live graph_id={g.graph_id!r} role={g.role!r} nodes={len(g.nodes)} edges={len(g.edges)}")

    outcome = "completed" if name == "claim" else "stopped"
    result = consolidate_request(
        dispatcher, mm, request_run,
        episode_id=episode_id,
        request_pattern_iri=None,
        outcome_classification=outcome,
        mm_persister=FalkorMMPersister(client),
        capacity_graphs=graphs,
    )
    print(f"consolidate dispatch result: {type(result).__name__ if result is not None else None!r}")

    failures = 0

    print("-- the Episode, raw from the KL episodic_memories role --")
    handle = make_writeable(kl, session)(
        role=ROLE_EPISODIC_MEMORIES, scope="local", version="v1"
    )
    episodes = [
        n for n in handle.graph().nodes.values()
        if getattr(n, "type_name", None) == "Episode"
    ]
    capacity_root_ref = None
    for node in episodes:
        print(f"node type={node.type_name!r}")
        print(f"     properties={node.properties!r}")
        print(f"     value={node.value!r}")
        props = node.properties or {}
        if not props.get("consolidated_at"):
            print("ACCEPTANCE FAIL: consolidated_at is absent or empty")
            failures += 1
        # S-1 (coordination §51.2/§52): displayed is not checked — the critic's
        # §27 class, caught here a second time. The renderer CONSUMES
        # outcome_classification (the §30 Q2 raise), so a wrong stored value
        # reaches the page unchallenged unless this asserts it.
        if props.get("outcome_classification") != outcome:
            print(
                f"ACCEPTANCE FAIL: outcome_classification "
                f"{props.get('outcome_classification')!r} != expected {outcome!r}"
            )
            failures += 1
        if props.get("state") != "closed":
            print(f"ACCEPTANCE FAIL: state {props.get('state')!r} != 'closed'")
            failures += 1
        capacity_root_ref = props.get("capacity_root_ref") or capacity_root_ref
    if not episodes:
        print("ACCEPTANCE FAIL: no Episode node was written")
        failures += 1
    if not capacity_root_ref:
        print("ACCEPTANCE FAIL: capacity_root_ref is absent - nothing to load back")
        failures += 1
        print()
        return failures, None, {}

    print("-- the task index, loaded BACK from FalkorDB --")
    index_graph = load_graph(client, capacity_root_ref)
    _dump_loaded_graph("index", index_graph)
    run_graph_ids = [
        node.value for node in index_graph.nodes.values()
        if node.type_name == "CapacityRunRef"
    ]

    print("-- every run graph, loaded BACK from FalkorDB --")
    for graph_id in run_graph_ids:
        loaded = load_graph(client, graph_id)
        _dump_loaded_graph("persisted", loaded)

    print("-- live vs persisted, per graph_id (values ASSERTED, not displayed) --")
    for graph_id in run_graph_ids:
        live = live_by_id.get(graph_id)
        loaded = load_graph(client, graph_id)
        live_counts = (len(live.nodes), len(live.edges)) if live else None
        loaded_counts = (len(loaded.nodes), len(loaded.edges))
        marker = "" if live_counts == loaded_counts else "  <-- MISMATCH"
        print(f"graph_id={graph_id!r} live={live_counts!r} persisted={loaded_counts!r}{marker}")
        if live_counts != loaded_counts:
            failures += 1
        if live is None:
            print(f"VALUE FAIL: index references a graph the live run never collected")
            failures += 1
        else:
            failures += _graph_value_failures(live, loaded)
    persisted_only = [g for g in run_graph_ids if g not in live_by_id]
    live_only = [g for g in live_by_id if g not in run_graph_ids]
    print(f"index covers {len(run_graph_ids)} graphs; live collected {len(live_by_id)}; "
          f"persisted-only={persisted_only!r} live-only={live_only!r}")
    if persisted_only or live_only:
        failures += 1
    print()
    return failures, capacity_root_ref, live_by_id


def main() -> int:
    try:
        client = FalkorClient(FalkorConfig.from_env())
        client.run_query("RETURN 1 AS ok", {})
    except Exception as exc:  # noqa: BLE001 — the raw error IS the output
        print(f"FalkorDB unreachable: {type(exc).__name__}: {exc}")
        print("a real store is REQUIRED here; start it and re-run "
              "(docker run --rm -d --name drdemo-falkor -p 6379:6379 falkordb/falkordb)")
        return 3
    try:
        failures = 0
        cases = []
        for name, exposures, episode_id in (
            ("claim", EXPOSURES, "drdemo-episode-claim"),
            ("boundary n=0", [], "drdemo-episode-boundary"),
        ):
            case_failures, root_ref, live_by_id = _run_case(
                name, exposures, episode_id, client
            )
            failures += case_failures
            cases.append((name, root_ref, live_by_id))
        print("-- END-STATE re-verify (s55): every case re-loaded AFTER the last write --")
        for name, root_ref, live_by_id in cases:
            if not root_ref:
                continue
            index_graph = load_graph(client, root_ref)
            run_graph_ids = [
                node.value for node in index_graph.nodes.values()
                if node.type_name == "CapacityRunRef"
            ]
            end_failures = 0
            for graph_id in run_graph_ids:
                live = live_by_id.get(graph_id)
                if live is None:
                    print(f"END-STATE FAIL {name!r}: index references {graph_id!r}, never collected live")
                    end_failures += 1
                    continue
                end_failures += _graph_value_failures(live, load_graph(client, graph_id))
            print(f"end-state {name!r}: {len(run_graph_ids)} graphs re-checked, {end_failures} failures")
            failures += end_failures
        print(f"acceptance failures: {failures}")
        return 0 if failures == 0 else 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
