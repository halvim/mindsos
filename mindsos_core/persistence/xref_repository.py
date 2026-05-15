"""XRef persistence (Phase 09 — ADR-0128 + M16 WAL + P51 per-Client + RR-16).

Two surfaces:

* :class:`XRefRepository` — programmatic write API. ``persist(xref)``
  and ``remove(xref_id, source_metagraph_id)`` each open a
  :class:`WriteAheadLog` context (M16 crash-safety) before the actual
  Cypher write.
* :func:`register_xref_replayers` — registers ``xref_add`` +
  ``xref_remove`` replayer callbacks onto a :class:`Client` (per
  Phase 09 P51 per-Client replayer dict + RR-16 per-kind module
  ownership). Composed into
  :func:`mindsos_core.persistence.bootstrap.register_all_l1_replayers`
  which :class:`FalkorClient.__init__` calls.

**WAL payload shapes (Phase 09 RR-1):**

* ``xref_add`` payload — 8-field dict matching
  :class:`mindsos_core.models.xref.XRef` shape (P53 dropped
  ``target_stale`` + ``deprecated_at``).
* ``xref_remove`` payload — ``{"xref_id": "..."}``.

**Replayer body** captures ``client`` via closure and re-runs the
MERGE-based builder (PB-8 — MERGE handles idempotency for re-runs;
DETACH DELETE is a no-op on missing rows).
"""

from __future__ import annotations

from typing import Any, Dict
from uuid import uuid4

from ..cypher.builders import build_create_xref, build_remove_xref
from ..models.xref import XRef
from .client import Client
from .wal import WriteAheadLog, register_replayer


_KIND_ADD = "xref_add"
_KIND_REMOVE = "xref_remove"


def _xref_payload(xref: XRef) -> Dict[str, Any]:
    """Serialise an :class:`XRef` to its WAL ``xref_add`` payload (RR-1).

    8-field dict per Phase 09 P53 (no ``target_stale`` / ``deprecated_at``).
    Mirrors the state-file ``xrefs[]`` entry shape per RR-8 symmetry.
    """
    return {
        "xref_id": xref.xref_id,
        "source_metagraph_id": xref.source_metagraph_id,
        "source_id": xref.source_id,
        "target_metagraph_id": xref.target_metagraph_id,
        "target_role": xref.target_role,
        "target_id": xref.target_id,
        "ref_type": xref.ref_type,
        "properties": dict(xref.properties),
    }


class XRefRepository:
    """Persist + remove :class:`XRef` rows with WAL crash-safety (M16)."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def persist(self, xref: XRef) -> None:
        """Persist one XRef + commit its WAL entry on success (M16).

        Opens a :class:`WriteAheadLog` context bound to the XRef's
        source metagraph, writes the ``xref_add`` begin entry, runs
        the MERGE-based :func:`build_create_xref`, then commits on
        clean exit. On exception the entry stays uncommitted; the
        next :func:`mindsos_core.persistence.wal.recover` retries.
        """
        wal = WriteAheadLog(self._client, xref.source_metagraph_id)
        with wal.entry(
            operation_id=str(uuid4()),
            kind=_KIND_ADD,
            payload=_xref_payload(xref),
        ):
            q, p = build_create_xref(
                xref_id=xref.xref_id,
                source_metagraph_id=xref.source_metagraph_id,
                source_id=xref.source_id,
                target_metagraph_id=xref.target_metagraph_id,
                target_role=xref.target_role,
                target_id=xref.target_id,
                ref_type=xref.ref_type,
                properties=xref.properties,
            )
            self._client.run_query(q, p)

    def remove(self, xref_id: str, *, source_metagraph_id: str) -> None:
        """DETACH DELETE one XRef + commit its WAL entry on success (M16).

        ``source_metagraph_id`` is required because :class:`WriteAheadLog`
        binds at construction; the caller (e.g. ``Metagraph.remove_xref``)
        already has it on hand.
        """
        wal = WriteAheadLog(self._client, source_metagraph_id)
        with wal.entry(
            operation_id=str(uuid4()),
            kind=_KIND_REMOVE,
            payload={"xref_id": xref_id},
        ):
            q, p = build_remove_xref(xref_id)
            self._client.run_query(q, p)


def register_xref_replayers(client: Client) -> None:
    """Register ``xref_add`` + ``xref_remove`` replayers on ``client`` (RR-16).

    Per Phase 09 P51 + P61 — replayers live on ``client._replayers``
    (per-Client dict; tests get isolation for free; no module-level
    pollution). Per Phase 09 PB-8 — MERGE-based for ``xref_add``,
    DETACH DELETE for ``xref_remove`` (both idempotent).

    Replayer body captures ``client`` via closure (the
    :class:`mindsos_core.persistence.wal.recover` callable signature
    is ``(payload) -> None``; it does NOT pass the client back).
    """

    def _replay_add(payload: Dict[str, Any]) -> None:
        q, p = build_create_xref(
            xref_id=payload["xref_id"],
            source_metagraph_id=payload["source_metagraph_id"],
            source_id=payload["source_id"],
            target_metagraph_id=payload["target_metagraph_id"],
            target_role=payload["target_role"],
            target_id=payload["target_id"],
            ref_type=payload["ref_type"],
            properties=payload.get("properties") or {},
        )
        client.run_query(q, p)

    def _replay_remove(payload: Dict[str, Any]) -> None:
        q, p = build_remove_xref(payload["xref_id"])
        client.run_query(q, p)

    register_replayer(client, _KIND_ADD, _replay_add)
    register_replayer(client, _KIND_REMOVE, _replay_remove)


__all__ = [
    "XRefRepository",
    "register_xref_replayers",
]
