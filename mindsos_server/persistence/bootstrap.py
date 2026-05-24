"""KL bootstrap wrapper(s) — load Global from FalkorDB or mint + persist.

Phase 26a ship per Phase 26a design log R4-PB-1 (b) + R5-PB-4 (a) +
R6-PB-2 (b) + ADR-0118 §amendment-3.

Phase 26b extends with :func:`bootstrap_global_pair_from_falkordb` —
symmetric load-or-mint for the canonical + pending Global pair, used
by the CLI release-flow helper to close B-26a-T4 (ephemeral
metagraph_id gap). See ADR-0118 §amendment-4 §"Decision §1+§2".

Per Phase 25's ADR-0043 verbatim contract ("KL stays in-memory; server
owns I/O"), KL itself stays untouched at Phase 26a. The server-side
wrapper here is the load-or-mint seam — it tries to find an existing
canonical Global by name; if found, loads + installs into a fresh KL;
if not, mints a fresh KL via :meth:`KnowledgeLayer.bootstrap` and
persists it for next time.

Per Phase 07 P4 A ("CLI verbs open a client, run the verb, close. No
long-lived process-scope clients"), the caller is responsible for the
``Client`` lifecycle — typically via the ``_resolve_client()`` helper
in ``mindsos_cli/commands/server.py``.

Per Phase 26a design log R5-PB-1 (a) + R5-PB-2 (a):
- All Metagraphs (Global + pending + canonical + user Locals) coexist
  in one FalkorDB graph keyed by ``metagraph_id`` FK.
- ``MetagraphRepository.persist()`` is MERGE-idempotent at every step;
  re-persist of an already-persisted Metagraph is safe.

Per Phase 25 §am-impl R6-04 (a): the canonical Global name is
``_GLOBAL_METAGRAPH_NAME`` (a constant in
:mod:`mindsos_knowledge.knowledge_layer`); the wrapper uses this
constant directly via re-import, not a duplicated string literal.
"""

from __future__ import annotations

from mindsos_admin import (
    PENDING_GLOBAL_METAGRAPH_NAME,
    bootstrap_pending_global,
)
from mindsos_core import Metagraph
from mindsos_core.persistence.client import Client
from mindsos_core.persistence.metagraph_repository import MetagraphRepository
from mindsos_core.reconstruction.metagraph_loader import MetagraphLoader
from mindsos_knowledge.knowledge_layer import (
    _GLOBAL_METAGRAPH_NAME,
    KnowledgeLayer,
)


def bootstrap_kl_from_falkordb(client: Client) -> KnowledgeLayer:
    """Return a :class:`KnowledgeLayer` whose Global mirrors FalkorDB.

    Load-or-mint semantics:

    1. Lookup canonical Global by name via
       :meth:`MetagraphLoader.find_by_name` (cheap O(1) per ADR-0123
       §am1 index).
    2. If found: load the Metagraph via :meth:`MetagraphLoader.load`
       and construct ``KnowledgeLayer(global_metagraph=loaded)``.
    3. If not found: this is the first-ever bootstrap path. Mint a
       fresh KL via :meth:`KnowledgeLayer.bootstrap` (in-memory
       Global with 6 named role-graphs ensured), then persist the
       result via :meth:`MetagraphRepository.persist` so subsequent
       invocations take the load path.

    The wrapper does NOT close the ``client`` — that's the caller's
    responsibility per Phase 07 P4 A.

    Args:
        client: A live :class:`Client` (typically a
            :class:`FalkorClient` opened by ``_resolve_client()`` at
            the CLI envelope).

    Returns:
        A :class:`KnowledgeLayer` with Global populated either from
        FalkorDB load or fresh bootstrap + persist.

    Raises:
        PersistenceError: If FalkorDB lookup or load or persist fails
            (driver error). Missing-row at lookup is NOT an error —
            it triggers the mint path.
    """
    loader = MetagraphLoader(client)
    global_mg_id = loader.find_by_name(_GLOBAL_METAGRAPH_NAME)
    if global_mg_id is None:
        # First-ever bootstrap path: mint + persist.
        kl = KnowledgeLayer.bootstrap()
        repo = MetagraphRepository(client)
        repo.persist(kl.global_metagraph())
        return kl
    # Subsequent invocations: load from FalkorDB.
    global_mg = loader.load(global_mg_id)
    return KnowledgeLayer(global_metagraph=global_mg)


def bootstrap_global_pair_from_falkordb(
    client: Client,
) -> tuple[KnowledgeLayer, Metagraph]:
    """Load-or-mint canonical Global + pending Global from FalkorDB.

    Phase 26b ship per Phase 26b design log R4-PB-1 (a) + R1-PB-1 (b)
    + R6-PB-1 (a) + ADR-0118 §amendment-4 §"Decision §1+§2".

    Closes B-26a-T4 (the ephemeral-metagraph_id gap surfaced at Phase
    26a host smoke). Canonical + pending Metagraph anchors persist on
    first-ever bootstrap so subsequent CLI invocations resolve stable
    ``metagraph_id`` values via :meth:`MetagraphLoader.find_by_name`.

    Two-store semantics per §amendment-4:

    * **Canonical content authority = FalkorDB.** ``loader.load(...)``
      reconstructs the full Metagraph (nodes + edges + cross-graph
      edges) — the §am3 ``_RELEASE_MERGE_CYPHER`` writes from prior
      release-ship invocations land back here.
    * **Pending content authority = SQLite.** ``loader.load(...)`` on
      the pending side returns the persisted anchor + role-graph
      topology; contained pending NODES are NOT loaded here (caller
      runs :func:`mindsos_admin.promotion.rehydrate_pending_global`
      against the SQLite ledger per Z21.1). The §am3
      ``_PROPOSE_MERGE_CYPHER`` writes to FalkorDB are forensic-only
      at Phase 26b — retained in code but unread by the production
      path. Future L4/L5 readers may consume.

    Per R6-PB-1 (a) — pending-mint path persists the empty pending
    Metagraph so subsequent invocations resolve a stable
    ``metagraph_id``; symmetric with canonical.

    The wrapper does NOT close the ``client`` — caller's
    responsibility per Phase 07 P4 A invariant.

    Args:
        client: A live :class:`Client` (typically a
            :class:`FalkorClient` opened by ``_resolve_client()`` at
            the CLI envelope).

    Returns:
        ``(canonical_kl, pending_mg)`` — canonical wrapped in
        :class:`KnowledgeLayer`; pending returned as a bare
        :class:`Metagraph` (the propose / release callers pass it
        directly to :func:`propose_for_promotion` /
        :func:`release_update`).

    Raises:
        PersistenceError: FalkorDB lookup / load / persist driver
            failure. Missing-row at lookup is NOT an error — it
            triggers the mint path.
    """
    loader = MetagraphLoader(client)
    repo = MetagraphRepository(client)

    # Canonical — identical to bootstrap_kl_from_falkordb.
    canonical_id = loader.find_by_name(_GLOBAL_METAGRAPH_NAME)
    if canonical_id is None:
        canonical_kl = KnowledgeLayer.bootstrap()
        repo.persist(canonical_kl.global_metagraph())
    else:
        canonical_kl = KnowledgeLayer(
            global_metagraph=loader.load(canonical_id)
        )

    # Pending — symmetric load-or-mint + persist-on-mint per R6-PB-1 (a).
    pending_id = loader.find_by_name(PENDING_GLOBAL_METAGRAPH_NAME)
    if pending_id is None:
        pending_mg = bootstrap_pending_global(canonical_kl.global_metagraph())
        repo.persist(pending_mg)
    else:
        pending_mg = loader.load(pending_id)

    return canonical_kl, pending_mg


__all__ = [
    "bootstrap_kl_from_falkordb",
    "bootstrap_global_pair_from_falkordb",
]
