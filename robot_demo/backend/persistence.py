"""DM-2 — per-device named Falkor persistence (PB-J / PB-AA / PB-Z, G-5).

The shipped ``mindsos_server.persistence.bootstrap.bootstrap_kl_from_falkordb``
is single-Global-by-name (``_GLOBAL_METAGRAPH_NAME``) — unusable for the
demo's four co-resident per-device Globals. This module mirrors it with a
**per-device named** load-or-mint built from the Core primitives
(``MetagraphLoader.find_by_name`` + ``MetagraphRepository.persist``), so
4 distinctly-named Globals coexist in the one shared FalkorDB keyed by
metagraph_id.

Scope (PB-Z): **Globals are persisted** (bundle seeds + install records
survive → ``install_skill`` no-ops on re-boot). **Locals stay in-memory**
and are re-seeded idempotently each boot — this keeps the DM-1 smoke's
per-brain Episode count exact and keeps the G-11 reset trivial. The G-5
episode flush is an **isolated round-trip probe** (below), not "Local is
the durable boot store."

**Surfaced (PB-AA):** install records (``_roster_value``) and Episodes are
both dict-valued, so Global-persist idempotency and G-5 ride the *same*
ADR-0182 ``_value_json`` codec — one mechanism, two payoffs.

All FalkorDB work is Linux-gated (the 3.10 Cowork sandbox has no live
FalkorDB and no ``falkordb`` driver); callers degrade to the DM-1
in-memory path when no client is supplied.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional, Tuple

log = logging.getLogger("robot_demo.persistence")


#: Dedicated FalkorDB graph keyspace for ALL demo persistence (PB-JJ).
#: ``FalkorConfig.from_env()`` hard-codes ``graph="mindsos"`` (P86 B: graph
#: is never env-sourced), which would put the 4 per-device Globals + the
#: G-5 probe in the same keyspace a real MindsOS server uses for its
#: canonical Global. A dedicated graph isolates demo data (trivially
#: droppable; zero risk to any real Global). Override via DEMO_FALKOR_GRAPH.
_DEMO_GRAPH = os.environ.get("DEMO_FALKOR_GRAPH", "robot_demo")


def open_client() -> Any:
    """Open a FalkorClient from env (FALKORDB_HOST/PORT/PASSWORD) on the
    demo's dedicated graph (PB-JJ). Caller owns the lifecycle (Phase-07
    P4 A: open → use → close; no process-scope client).

    Raises:
        PersistenceError: driver missing or connect failure (surfaced so
            the bootstrap can decide to fall back to in-memory).
    """
    from dataclasses import replace

    from mindsos_core.config import FalkorConfig
    from mindsos_core.persistence.client import FalkorClient

    config = replace(FalkorConfig.from_env(), graph=_DEMO_GRAPH)
    return FalkorClient(config)


@dataclass
class GlobalLoadResult:
    kl: Any
    minted: bool  # True = first-ever (caller must install+seed+persist)


def load_or_mint_global(client: Any, profile: Any) -> GlobalLoadResult:
    """Per-device named load-or-mint for a device's Global.

    * ``find_by_name(profile.kl_name)`` hit → load + wrap (``minted=False``).
    * miss → ``KnowledgeLayer.bootstrap()`` + set the per-device Global
      name (``minted=True``); the caller installs bundles + persists so
      the next boot takes the load path.
    """
    from mindsos_core.persistence.metagraph_repository import MetagraphRepository  # noqa: F401
    from mindsos_core.reconstruction.metagraph_loader import MetagraphLoader
    from mindsos_knowledge import KnowledgeLayer

    loader = MetagraphLoader(client)
    mg_id = loader.find_by_name(profile.kl_name)
    if mg_id is None:
        kl = KnowledgeLayer.bootstrap()
        kl.global_metagraph().name = profile.kl_name
        return GlobalLoadResult(kl=kl, minted=True)

    global_mg = loader.load(mg_id)
    kl = KnowledgeLayer(global_metagraph=global_mg)
    return GlobalLoadResult(kl=kl, minted=False)


def build_local_persister(client: Any) -> Any:
    """DM-8: a durable KL-Local persister bound to the demo's client, or
    ``None`` when no FalkorDB client is available (in-memory fallback)."""
    if client is None:
        return None
    from mindsos_server.persistence import FalkorDBLocalPersister

    return FalkorDBLocalPersister(client)


def persist_global(client: Any, kl: Any) -> None:
    """Persist a device's Global (MERGE-idempotent at every step)."""
    from mindsos_core.persistence.metagraph_repository import MetagraphRepository

    MetagraphRepository(client).persist(kl.global_metagraph())


# ── G-5 episode→Falkor round-trip probe ────────────────────────────────

@dataclass
class EpisodeRoundTripResult:
    ok: bool
    flushed: int
    detail: str


#: Stable id+name for the throwaway G-5 probe metagraph. Fixed so the
#: MERGE-idempotent persist OVERWRITES the same anchor every boot (no
#: per-boot orphan accumulation — there is no shipped scoped-delete).
_G5_PROBE_MG_ID = "robot-demo::g5-episode-probe"
_G5_PROBE_GRAPH_ID = "robot-demo::g5-episode-probe::episodes"


def probe_episode_roundtrip(
    client: Any, kl: Any, device_id: str
) -> EpisodeRoundTripResult:
    """Round-trip the brain's real Episode ``value`` dict(s) through Falkor
    in an **isolated** throwaway metagraph, and assert they survive intact.

    Proves the ADR-0182 ``_value_json`` codec carries dict-valued Episode
    nodes (the Phase-49 PB-RT / L0-26 gap that descoped the flush) WITHOUT
    persisting the live Local (PB-Z: Locals stay in-memory) and WITHOUT
    leaking — the probe metagraph has a fixed id, so each boot overwrites
    the same Falkor anchor instead of accumulating orphans.

    Never raises (any persist/load failure → ``ok=False``) so the caller
    falls back to in-memory episodes and documents it (G-5 fallback).
    """
    try:
        from mindsos_core import Metagraph
        from mindsos_core.models.graph import Graph
        from mindsos_core.persistence.metagraph_repository import MetagraphRepository
        from mindsos_core.reconstruction.metagraph_loader import MetagraphLoader
        from mindsos_knowledge.identifiers import ROLE_EPISODIC_MEMORIES
        from mindsos_knowledge.metagraph_view import MetagraphView

        local_mg = kl.local_metagraph(device_id)
        ep_graph = MetagraphView(local_mg).graphs_by_role(
            ROLE_EPISODIC_MEMORIES
        )[0]
        before = {
            nid: n.value
            for nid, n in ep_graph.nodes.items()
            if getattr(n, "type_name", None) == "Episode"
        }
        if not before:
            return EpisodeRoundTripResult(False, 0, "no Episode to round-trip")

        # Build an isolated, fixed-id probe metagraph holding ONLY the real
        # Episode value dicts (no schema → "Episode" type accepted as-is).
        probe_mg = Metagraph(
            name="robot-demo::g5-episode-probe", metagraph_id=_G5_PROBE_MG_ID
        )
        g = Graph(
            name="episodes",
            role=ROLE_EPISODIC_MEMORIES,
            graph_id=_G5_PROBE_GRAPH_ID,
        )
        for nid, value in before.items():
            g.add_node(value, "Episode", node_id=f"g5:{nid}")
        probe_mg.add_graph(g)

        MetagraphRepository(client).persist(probe_mg)  # MERGE-idempotent
        reloaded = MetagraphLoader(client).load(_G5_PROBE_MG_ID)
        re_graph = MetagraphView(reloaded).graphs_by_role(
            ROLE_EPISODIC_MEMORIES
        )[0]
        after = {
            n.node_id: n.value
            for n in re_graph.nodes.values()
            if getattr(n, "type_name", None) == "Episode"
        }

        expected = {f"g5:{nid}": v for nid, v in before.items()}
        mismatches = [k for k, v in expected.items() if after.get(k) != v]
        if mismatches or len(after) < len(expected):
            return EpisodeRoundTripResult(
                False, len(before),
                f"round-trip mismatch: {len(mismatches)} value diff(s), "
                f"{len(expected)}→{len(after)} nodes",
            )
        return EpisodeRoundTripResult(
            True, len(before),
            f"{len(before)} dict-valued Episode(s) round-tripped intact",
        )
    except Exception as exc:  # codec/persist/load failure → documented fallback
        return EpisodeRoundTripResult(False, 0, f"probe resisted: {exc!r}")


__all__ = [
    "open_client",
    "GlobalLoadResult",
    "load_or_mint_global",
    "build_local_persister",
    "persist_global",
    "EpisodeRoundTripResult",
    "probe_episode_roundtrip",
]
