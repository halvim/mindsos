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

from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
from mindsos_knowledge.metagraph_view import MetagraphView

from mindsos_server.persistence.local_persister import FalkorDBLocalPersister


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


def main() -> int:
    client = connect()
    try:
        roundtrip_probe(client)
    finally:
        try:
            client.run_query("MATCH (n) DETACH DELETE n")
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
