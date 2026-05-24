"""KL bootstrap wrapper — load Global from FalkorDB or mint + persist.

Phase 26a ship per Phase 26a design log R4-PB-1 (b) + R5-PB-4 (a) +
R6-PB-2 (b) + ADR-0118 §amendment-3.

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


__all__ = ["bootstrap_kl_from_falkordb"]
