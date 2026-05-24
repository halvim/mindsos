"""Phase 26b direct-Cypher assertion helper.

Per Phase 26b design log R1-PB-6 (a) — substep 10 asserts canonical
``metagraph_id`` stability across CLI subprocesses + node counts
match by reading FalkorDB directly. Lives in tests/ because no CLI
verb exposes ``metagraph_id`` (deferred to PHASE_MAP §38 per R1-PB-8
(b)).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from mindsos_core.config import FalkorConfig
from mindsos_core.persistence.client import FalkorClient
from mindsos_knowledge.knowledge_layer import _GLOBAL_METAGRAPH_NAME
from mindsos_admin import PENDING_GLOBAL_METAGRAPH_NAME


@contextmanager
def open_client() -> Iterator[FalkorClient]:
    """Open a fresh FalkorClient against env-configured FalkorDB; close on exit."""
    client = FalkorClient(FalkorConfig.from_env())
    try:
        yield client
    finally:
        client.close()


def resolve_canonical_metagraph_id() -> Optional[str]:
    """Return the canonical Global ``metagraph_id`` from FalkorDB; None if absent."""
    with open_client() as client:
        result = client.run_query(
            "MATCH (m:Metagraph {name: $name}) RETURN m.id AS id LIMIT 1",
            {"name": _GLOBAL_METAGRAPH_NAME},
        )
        first = result.first()
        return None if first is None else first["id"]


def resolve_pending_metagraph_id() -> Optional[str]:
    """Return the pending Global ``metagraph_id`` from FalkorDB; None if absent."""
    with open_client() as client:
        result = client.run_query(
            "MATCH (m:Metagraph {name: $name}) RETURN m.id AS id LIMIT 1",
            {"name": PENDING_GLOBAL_METAGRAPH_NAME},
        )
        first = result.first()
        return None if first is None else first["id"]


def count_canonical_nodes() -> int:
    """Return the total Node-row count under the canonical Global metagraph_id."""
    canonical_id = resolve_canonical_metagraph_id()
    if canonical_id is None:
        return 0
    with open_client() as client:
        result = client.run_query(
            "MATCH (n:Node {metagraph_id: $mg_id}) RETURN count(n) AS n",
            {"mg_id": canonical_id},
        )
        first = result.first()
        return 0 if first is None else int(first["n"])
