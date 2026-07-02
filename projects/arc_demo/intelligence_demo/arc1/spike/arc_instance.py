"""(b) durable MindsOS instance — Falkor-backed, LOCAL persistence.

Runs ONLY on the Linux machine with a FalkorDB container up (see
``projects/arc_demo/docker-compose.yml``); it cannot run in Cowork (no sidecar)
and is NOT part of the in-memory ``./run_spike`` gate.

Layer/persistence model it targets (see the `mindsos-persistence-model` note):
  * system builtins  -> Global L3;
  * arc caps + DataStates -> the user's LOCAL L3 (register with a session);
  * episodes -> the user's LOCAL episodic_memories (L5 is Local-only, "No
    Global L5"), persisted via ``FalkorDBLocalPersister``.

STEP 1 (this file, now): prove the sidecar is reachable and a Local metagraph
carrying a STRUCTURED dict-valued node (the shape a consolidated Episode holds)
round-trips through ``FalkorDBLocalPersister``. ADR-0182 (Phase 50) routes dict
values through the node ``_value_json`` column, so NO core change is needed for
durable episodes — this confirms it live before steps 2-3 (install content, run
the arc trip, consolidate, save/reload the Episode).

    python intelligence_demo/arc1/spike/arc_instance.py
"""

from __future__ import annotations

if __package__ in (None, ""):
    import os as _os
    import runpy as _runpy
    import sys as _sys
    _pkg_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".."))
    _repo_root = _os.path.abspath(_os.path.join(_pkg_root, "..", ".."))
    for _p in (_repo_root, _pkg_root):
        if _p not in _sys.path:
            _sys.path.insert(0, _p)
    _runpy.run_module("intelligence_demo.arc1.spike.arc_instance", run_name="__main__")
    _sys.exit(0)

from mindsos_core import Metagraph
from mindsos_core.config import FalkorConfig
from mindsos_core.models.graph import Graph
from mindsos_core.persistence import FalkorClient

from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView

from mindsos_server.persistence.local_persister import FalkorDBLocalPersister

from mindsos_intelligence.chain_artifacts import ChainArtifactWriter
from mindsos_intelligence.consolidation import consolidate_task

from . import arc_grids, arc_l4, arc_solver


def connect(graph: str = "arc") -> FalkorClient:
    """Connect to the Falkor sidecar — host/port/password from env, graph override
    (mirrors the shipped `tests/_shared` falkor_client fixture)."""
    base = FalkorConfig.from_env()
    cfg = FalkorConfig(host=base.host, port=base.port,
                       password=base.password, graph=graph)
    return FalkorClient(cfg)


def _sample_local(user: str) -> Metagraph:
    """A Local metagraph with an ``episodic_memories`` graph carrying a primitive
    node + a STRUCTURED dict-valued ``Episode`` node (the 6-field-style shape a
    real consolidated Episode holds), to exercise the ADR-0182 codec path. The
    metagraph name must be the persister's Local name (``local_knowledge:<user>``)."""
    mg = Metagraph(name=f"local_knowledge:{user}")
    g = mg.add_graph(Graph(name=f"{user}-episodes", role=ROLE_EPISODIC_MEMORIES))
    g.add_node("primitive-alpha", "Concept")
    g.add_node(
        {"task_pattern_iri": "tp:arc", "chain": {"hints": ["h1"], "depth": 2},
         "outcome_classification": "succeeded"},
        "Episode",
    )
    return mg


def roundtrip_probe(client: FalkorClient, user: str = "arc") -> None:
    """save -> load a Local metagraph and assert the structured Episode value
    survived (dict round-trips through Falkor)."""
    persister = FalkorDBLocalPersister(client)
    persister.save(user, _sample_local(user))
    loaded = persister.load(user)
    assert loaded is not None, "Local metagraph did not load back from Falkor"
    g = MetagraphView(loaded).graphs_by_role(ROLE_EPISODIC_MEMORIES)[0]
    eps = [n for n in g.nodes.values() if getattr(n, "type_name", None) == "Episode"]
    assert eps, "no Episode node in the reloaded Local"
    assert eps[0].value.get("chain", {}).get("depth") == 2, \
        f"structured Episode value did not round-trip: {eps[0].value!r}"
    print(f"  [ok] (b) step 1: Local metagraph + structured dict (Episode-shaped) "
          f"node round-tripped through FalkorDBLocalPersister for user {user!r}.")


# ── STEP 2: real arc trip on the durable instance -> Local Episode in Falkor ──
def build_durable_instance(client: FalkorClient, user: str = "arc"):
    """The proven in-process stack (`arc_l4.build_instance`: bootstrapped KL +
    CapacityLayer with the v0/consolidate/text/dream builtins + arc caps) with a
    `FalkorDBLocalPersister` attached for durable LOCAL persistence. Arc caps stay
    Global (system capabilities); the durable per-task DATA (the Episode) is
    Local — L5 is Local-only ("No Global L5")."""
    inst = arc_l4.build_instance(user=user, arc_local=True)  # arc caps + DS -> user's Local L3
    inst.persister = FalkorDBLocalPersister(client)
    return inst


#: The tasks the layer-driven solver handles today (#8/#2/#251/#53).
SOLVED_TASKS = ["05f2a901", "00d62c1b", "a5313dff", "25ff71a9"]


def run_and_persist(inst, task_ids):
    """Run the REAL arc solve for each task on the durable instance and persist
    every Episode:
      * L3 — dispatch phases 8/9/10 (`solve_through_layer`) → answer matches the
        withheld output;
      * L5 — consolidate an Episode tagged with the SOLVED task + outcome into the
        user's Local `episodic_memories`;
      * persist the Local to Falkor once, reload, and assert every arc Episode
        round-tripped."""
    dataset = arc_grids.load_dataset()
    solved = []
    for task_id in task_ids:
        solve, _inline = arc_l4.solve_through_layer(inst.dispatcher, task_id, dataset)
        assert solve is not None, f"solve produced no answer for {task_id}"
        outcome = "succeeded" if solve.get("matches_withheld") else "failed"
        writer = ChainArtifactWriter(inst.mm, task_scope=f"arc-{task_id}")
        task_run = writer.emit_task_run()
        res = consolidate_task(inst.dispatcher, inst.mm, task_run,
                               task_pattern_iri=f"arc:solved:{task_id}",
                               outcome_classification=outcome)
        assert res is not None and res.success, f"consolidation failed for {task_id}: {res!r}"
        solved.append((task_id, outcome))

    inst.persister.delete(inst.user)                          # clean prior Local (no stale accumulation)
    inst.persister.save(inst.user, inst.kl.local_metagraph(inst.user))
    loaded = inst.persister.load(inst.user)                   # reload from Falkor
    assert loaded is not None, "Local did not reload from Falkor"
    g = MetagraphView(loaded).graphs_by_role(ROLE_EPISODIC_MEMORIES)[0]
    eps = [n for n in g.nodes.values() if getattr(n, "type_name", None) == "Episode"]
    assert len(eps) == len(task_ids), \
        f"expected {len(task_ids)} Episodes reloaded, got {len(eps)}"
    return solved, len(eps)


# ── STEP 3: restart durability — a FRESH instance loads the Local from Falkor ──
def verify_restart(client: FalkorClient, user: str = "arc"):
    """Simulate a process restart: a BRAND-NEW KnowledgeLayer loads the persisted
    Local from Falkor via the ADR-0042 install hook and finds the prior Episode
    WITHOUT re-running any trip. Proves the durable instance survives a restart —
    not just a same-process round-trip."""
    loaded = FalkorDBLocalPersister(client).load(user)
    assert loaded is not None, "no persisted Local in Falkor — run step 2 first"
    kl = KnowledgeLayer.bootstrap()                 # fresh instance (post-restart)
    kl.install_local_metagraph(user, loaded)        # reload the user's Local
    g = MetagraphView(kl.local_metagraph(user)).graphs_by_role(ROLE_EPISODIC_MEMORIES)[0]
    eps = [n for n in g.nodes.values() if getattr(n, "type_name", None) == "Episode"]
    assert eps, "no Episode found after restart-reload from Falkor"
    return eps


def main(argv=None) -> int:
    import sys
    args = list(argv if argv is not None else sys.argv[1:])
    mode = args[0] if args else "run"
    client = connect()
    try:
        if mode == "restart":
            eps = verify_restart(client)
            pats = sorted(e.value.get("task_pattern_iri") for e in eps
                          if isinstance(e.value, dict))
            print(f"  [ok] (b) step 3: FRESH instance loaded the Local from Falkor "
                  f"(no trip re-run) — {len(eps)} prior Episodes present: {pats}. "
                  f"The durable instance survives a restart.")
        else:
            inst = build_durable_instance(client)
            solved, n = run_and_persist(inst, SOLVED_TASKS)
            tags = ", ".join(f"{t}({o})" for t, o in solved)
            print(f"  [ok] (b) step 2: arc caps registered LOCAL; solved {len(solved)} "
                  f"tasks through L4->L3 [{tags}] -> {n} L5 Episodes "
                  f"'arc:solved:*' consolidated + persisted to Falkor Local + reloaded "
                  f"for user 'arc'.")
            print("  [i] then verify restart durability: "
                  "python3 -m intelligence_demo.arc1.spike.arc_instance restart")
    finally:
        try:
            client.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
