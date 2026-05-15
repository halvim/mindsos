"""Write-Ahead Log for multi-statement write safety (ADR-0122 + Phase 07 P50 B).

FalkorDB has no multi-statement transactions; ``run_batch`` is sequential
(per ADR-0030 sequential-batch). A failure on statement N of M leaves
1..N-1 committed. ``MetagraphSnapshot`` (ADR-0027) covers Python-side
rollback; the WAL graph covers the FalkorDB-side rollback / replay
story.

**Primary surface — context-manager API (P50 B):**

::

    wal = WriteAheadLog(client, metagraph_id)
    with wal.entry(
        operation_id=str(uuid4()),
        kind="kl.propose_for_promotion",
        payload={"draft_id": "...", "target_role": "lexicon"},
    ) as op_id:
        # ... apply writes ...
        # __exit__ stamps committed=true on success;
        # on exception, the entry stays uncommitted for replay/compensate.

**Raw primitives** (``begin`` / ``commit`` / ``list_uncommitted`` /
``gc``) remain accessible for failure-injection tests
(``RaisesOnNthCall``) and direct programmatic use.

**Replayer registry — Phase 09 P51 + P61 + P66 (per-Client).** Each
:class:`Client` instance carries its own ``_replayers`` dict. The
module-level :func:`register_replayer` / :func:`clear_replayers` /
:func:`recover` functions take the client as their first positional
argument and read the dict off it. Test isolation is automatic:
distinct clients have distinct registries; no cross-test pollution
from a module-level global.

**Constraint** — WAL is per-Metagraph; ``WriteAheadLog`` instance
binds to a specific ``metagraph_id`` at construction.
"""

from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterator, List, Optional

from ..exceptions import PersistenceError, WALReplayerMissingError
from .client import Client


# Sentinel role for the WAL graph inside a metagraph (parity with v3).
WAL_ROLE = "_wal"

# Attribute name used on Client instances for the per-client replayer
# dict. We attach lazily on first registration so callers don't need
# to subclass Client to participate.
_REPLAYERS_ATTR = "_replayers"


def _get_replayers(
    client: Client,
) -> Dict[str, Callable[[Dict[str, Any]], None]]:
    """Return (lazy-initialising) the per-client replayer dict."""
    reg = getattr(client, _REPLAYERS_ATTR, None)
    if reg is None:
        reg = {}
        # Direct attribute set; Client is a Protocol so attribute is fine.
        setattr(client, _REPLAYERS_ATTR, reg)
    return reg


def register_replayer(
    client: Client,
    kind: str,
    replayer: Callable[[Dict[str, Any]], None],
) -> None:
    """Register a replayer for a WAL ``kind`` on ``client`` (ADR-0122).

    Phase 09 P51 + P61 — replayer registration is per-Client. The
    replayer runs during :func:`recover` for any uncommitted entry
    matching ``kind`` against ``client``. It receives the entry's
    payload as a dict.
    """
    _get_replayers(client)[kind] = replayer


def clear_replayers(client: Client) -> None:
    """Clear ``client``'s replayer registry. Tests use this between cases."""
    _get_replayers(client).clear()


@dataclass
class WALEntry:
    """A single WAL row (ADR-0122).

    Persisted as a ``:WALEntry`` node bound to a ``:Metagraph`` via
    :IN_METAGRAPH. ``payload`` is application-specific JSON; the
    replayer for ``kind`` knows how to interpret it.
    """

    operation_id: str
    kind: str
    payload: Dict[str, Any]
    started_at: datetime = field(default_factory=datetime.utcnow)
    committed: bool = False
    committed_at: Optional[datetime] = None


class WriteAheadLog:
    """Append intent records before applying multi-statement operations.

    Primary surface is the :meth:`entry` context manager (P50 B). Raw
    :meth:`begin` / :meth:`commit` are exposed for failure-injection
    tests.
    """

    def __init__(self, client: Client, metagraph_id: str) -> None:
        self._client = client
        self._mid = metagraph_id

    # ── primary context-manager API (P50 B) ──────────────────────────────

    @contextlib.contextmanager
    def entry(
        self,
        *,
        operation_id: str,
        kind: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Iterator[str]:
        """Context manager: begin on enter, commit on success, leave on error.

        On normal exit, stamps ``committed=true``. On exception, the
        entry stays ``committed=false`` and :func:`recover` will replay
        or compensate per the registered replayer at server start.

        Yields ``operation_id`` so callers can pass it to inner writes
        without re-passing the constant.
        """
        op_id = self.begin(
            operation_id=operation_id, kind=kind, payload=payload,
        )
        try:
            yield op_id
        except Exception:
            # Leave uncommitted; recover() handles it next time.
            raise
        else:
            self.commit(op_id)

    # ── raw primitives (failure-injection tests + direct use) ────────────

    def begin(
        self,
        *,
        operation_id: str,
        kind: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Insert a ``committed=false`` WAL entry; return ``operation_id``."""
        started_at = datetime.utcnow()
        payload_json = json.dumps(
            payload or {}, sort_keys=True, ensure_ascii=False, default=str,
        )
        q = (
            "MATCH (m:Metagraph {id: $mid}) "
            "MERGE (w:WALEntry {operation_id: $oid, metagraph_id: $mid}) "
            "SET w.kind = $kind, w.payload_json = $payload_json, "
            "    w.started_at = $started_at, w.committed = false "
            "MERGE (w)-[:IN_METAGRAPH]->(m) "
            "RETURN w.operation_id AS op_id"
        )
        self._client.run_query(
            q,
            {
                "mid": self._mid,
                "oid": operation_id,
                "kind": kind,
                "payload_json": payload_json,
                "started_at": started_at.isoformat(),
            },
        )
        return operation_id

    def commit(self, operation_id: str) -> None:
        """Stamp ``committed=true`` on the WAL entry."""
        q = (
            "MATCH (w:WALEntry {operation_id: $oid, metagraph_id: $mid}) "
            "SET w.committed = true, w.committed_at = $now "
            "RETURN w.operation_id AS op_id"
        )
        res = self._client.run_query(
            q,
            {
                "oid": operation_id,
                "mid": self._mid,
                "now": datetime.utcnow().isoformat(),
            },
        )
        if not res.rows:
            raise PersistenceError(
                f"WAL commit: entry {operation_id!r} not found in metagraph "
                f"{self._mid!r}"
            )

    def list_uncommitted(self) -> List[WALEntry]:
        """Return every uncommitted WAL entry for this metagraph."""
        q = (
            "MATCH (w:WALEntry {metagraph_id: $mid}) "
            "WHERE w.committed = false "
            "RETURN w.operation_id AS op_id, w.kind AS kind, "
            "       w.payload_json AS payload_json, "
            "       w.started_at AS started_at"
        )
        res = self._client.run_query(q, {"mid": self._mid})
        out: List[WALEntry] = []
        for row in res.rows:
            try:
                payload = json.loads(row.get("payload_json") or "{}")
            except (TypeError, ValueError):
                payload = {}
            started = (
                datetime.fromisoformat(row["started_at"])
                if row.get("started_at")
                else datetime.utcnow()
            )
            out.append(
                WALEntry(
                    operation_id=row["op_id"],
                    kind=row["kind"],
                    payload=payload,
                    started_at=started,
                    committed=False,
                )
            )
        # Phase 09 RPB-1 — FIFO across kinds. Sort by started_at so
        # multi-kind recovery preserves causal write-order.
        out.sort(key=lambda e: e.started_at)
        return out

    def count_uncommitted(self) -> int:
        """Cheap count of uncommitted WAL entries (used by ``diagnose``)."""
        q = (
            "MATCH (w:WALEntry {metagraph_id: $mid}) "
            "WHERE w.committed = false "
            "RETURN count(w) AS n"
        )
        res = self._client.run_query(q, {"mid": self._mid})
        row = res.first()
        return int(row.get("n", 0)) if row else 0

    def gc(self, *, older_than_seconds: int) -> int:
        """Delete committed WAL entries older than ``older_than_seconds``.

        Returns the number of entries deleted. Manual GC is intentional
        (per ADR-0122) — no daemon thread in v1.
        """
        cutoff = datetime.utcnow() - timedelta(seconds=older_than_seconds)
        q = (
            "MATCH (w:WALEntry {metagraph_id: $mid}) "
            "WHERE w.committed = true AND w.committed_at < $cutoff "
            "WITH w, w.operation_id AS oid "
            "DETACH DELETE w "
            "RETURN count(oid) AS n"
        )
        res = self._client.run_query(
            q, {"mid": self._mid, "cutoff": cutoff.isoformat()},
        )
        row = res.first()
        return int(row.get("n", 0)) if row else 0


def recover(client: Client, metagraph_id: str) -> int:
    """Run replay/compensate for every uncommitted WAL entry (ADR-0122).

    Called from :class:`MetagraphLoader.load` step 0. For each
    uncommitted entry, looks up the registered replayer for its
    ``kind`` (in ``client._replayers``) and invokes it. On replayer
    failure, the entry stays uncommitted; the next startup retries
    (replayers must be idempotent).

    **Phase 09 P62** — when a kind has NO registered replayer, raises
    :class:`WALReplayerMissingError` (no longer silently skipped). The
    Phase 08 narrow-catch in :class:`MetagraphLoader.load` was removed.

    **Phase 09 RPB-1** — FIFO across kinds. Entries replay in
    ``started_at`` order regardless of ``kind``.

    Returns the number of entries successfully replayed and committed.
    """
    wal = WriteAheadLog(client, metagraph_id)
    replayers = _get_replayers(client)
    replayed = 0
    for e in wal.list_uncommitted():
        replayer = replayers.get(e.kind)
        if replayer is None:
            raise WALReplayerMissingError(
                f"No replayer registered for WAL kind {e.kind!r} "
                f"(operation {e.operation_id!r}, metagraph {metagraph_id!r})"
            )
        try:
            replayer(e.payload)
        except Exception:
            # Replayer failed; leave uncommitted; next recover() retries.
            continue
        wal.commit(e.operation_id)
        replayed += 1
    return replayed


__all__ = [
    "WAL_ROLE",
    "WALEntry",
    "WriteAheadLog",
    "register_replayer",
    "clear_replayers",
    "recover",
]
