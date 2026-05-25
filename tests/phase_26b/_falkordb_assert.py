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


def count_canonical_nodes_via_graph_traversal() -> int:
    """Count Node rows reachable via `Graph<-[:IN_GRAPH]-Node` from canonical.

    Per B-26b-T4 probe: `MetagraphRepository.persist()` (the importer
    persist path) stores Node rows with `id` + `graph_id` + an explicit
    `[:IN_GRAPH]` relationship to a Graph anchor. The Graph anchor in
    turn carries `metagraph_id` + `[:IN_METAGRAPH]` to the Metagraph
    anchor.

    Used to count importer-persisted content (step 5 in the scenario).
    """
    canonical_id = resolve_canonical_metagraph_id()
    if canonical_id is None:
        return 0
    with open_client() as client:
        result = client.run_query(
            "MATCH (g:Graph {metagraph_id: $mg_id})<-[:IN_GRAPH]-(n:Node) "
            "RETURN count(n) AS n",
            {"mg_id": canonical_id},
        )
        first = result.first()
        return 0 if first is None else int(first["n"])


def count_canonical_nodes_via_metagraph_id_property() -> int:
    """Count Node rows with direct `metagraph_id` property == canonical id.

    Property-based counter — counts every Node whose `metagraph_id`
    property matches the canonical id, regardless of relationship
    structure. Used to count release-shipped content (step 7b in the
    scenario) in a form that is stable across the §am3 → §am5
    transition.

    History: at Phase 26b ship, the §am3 `_RELEASE_MERGE_CYPHER`
    template lacked a closing `[:IN_GRAPH]` MERGE clause — released
    Node rows were orphan from the Graph traversal path. This counter
    sidestepped the gap by counting via property rather than via
    relationship. ADR-0118 §amendment-5 (Phase 28) closed that gap;
    the counter is kept (i) for forward-compat across the transition
    and (ii) as a forensic property-aware counter complementing the
    graph-traversal counter above.
    """
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


# Backward-compat alias for the scenario; defaults to graph-traversal
# (importer-persisted shape).
count_canonical_nodes = count_canonical_nodes_via_graph_traversal
