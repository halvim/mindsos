"""Reconstruct :class:`XRef` rows for a :class:`Metagraph` (Phase 09).

Two surfaces:

* :class:`XRefLoader` — class form. ``load_into(mg)`` does the actual
  DB read + in-memory wiring. Per **Phase 09 PB-9** clears
  ``mg.xrefs`` + inverse indexes + identity-unregisters every prior
  XRef id BEFORE re-populating from the DB. Per **Phase 09 P55**
  also clears ``mg._xrefs_dirty`` so refresh-then-persist doesn't
  re-write loaded rows. Per **Phase 09 P64** leaves
  ``mg._xrefs_dirty`` empty after rebuild — state-file-shaped data
  that lands in ``mg.xrefs`` is by definition already persisted.
* :func:`attach_xref_loader` — **Phase 09 M18** helper. Subscribes
  the loader as a :meth:`Metagraph.register_after_load_observer`
  callback. The observer reads ``mg._persist_client`` at fire time
  (transient set by :meth:`MetagraphLoader.load` line 226 + ``.refresh``
  line 324). Idempotent — re-attach is a no-op so test fixtures or
  Phase 06 attach_registry-style consumers can call it safely.

**Phase 09 P53 — 8 fields.** v3's ``target_stale`` /
``deprecated_at`` are NOT read or projected; both ship in Phase 10
with their setters. The Cypher query projects 7 columns + ``properties(x)``;
the row-to-XRef constructor passes 7 named fields + filtered ``properties``.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .._observers import ObserverHandle
from ..models.xref import XRef

if TYPE_CHECKING:
    from ..models.metagraph import Metagraph
    from ..persistence.client import Client


def _parse_iso(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 datetime string or pass through (Phase 10 helper)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None
    return None


#: Core-owned fields the loader must NOT pass through as
#: ``XRef.properties``. Phase 09 P53 dropped ``target_stale`` and
#: ``deprecated_at``; they remain in this filter set so an old row
#: written by v3 substrate (carrying those columns) is still
#: accepted on load — the values are simply not surfaced in
#: ``XRef.properties``.
_CORE_XREF_FIELDS = frozenset({
    "id",
    "source_metagraph_id",
    "source_id",
    "target_metagraph_id",
    "target_role",
    "target_id",
    "ref_type",
    # P53 deferred — kept in the filter set as forward-compat for
    # legacy rows; not surfaced as XRef fields in Phase 09.
    "target_stale",
    "deprecated_at",
})


#: Sentinel attribute on :class:`Metagraph` instances signalling that
#: ``attach_xref_loader`` already wired its after-load observer.
#: Phase 06 P49 B idempotent-helper precedent.
_ATTACH_FLAG_ATTR = "_xref_loader_attached"


class XRefLoader:
    """Reconstruct :class:`XRef` rows for a metagraph (PB-9 clear-first)."""

    def __init__(self, client: "Client") -> None:
        self._client = client

    def load_into(self, mg: "Metagraph") -> None:
        """Clear ``mg``'s existing XRef state, then re-populate from DB.

        **Clear pass (PB-9 + P55):**
          1. Identity-unregister every existing ``xref_id`` so the
             registry doesn't reject the re-registration in the
             populate pass.
          2. Empty ``mg.xrefs`` + ``mg._xrefs_by_source`` +
             ``mg._xrefs_by_target``.
          3. Empty ``mg._xrefs_dirty`` — loaded XRefs are by
             definition already in DB, so the dirty set must be
             empty post-load (P64 + P55 — loaders never produce
             dirty entries).

        **Populate pass:**
          4. ``MATCH (x:XRef {source_metagraph_id: $mid})`` query.
          5. For each row: construct :class:`XRef`, identity-register,
             insert into ``mg.xrefs`` + both inverse indexes.

        Note: the population path does NOT call
        :meth:`Metagraph.add_xref` — that would trigger inline DB
        writes (M16) we don't want during a load. Direct dict
        assignment per RR-18 deserializer pattern.
        """
        # Clear pass — PB-9 + P55 + P64.
        for old_id in list(mg.xrefs.keys()):
            try:
                mg.identity.unregister(old_id)
            except Exception:
                # Identity may already be missing the id (e.g. fresh
                # registry between refresh cycles); tolerate silently.
                pass
        mg.xrefs.clear()
        mg._xrefs_by_source.clear()
        mg._xrefs_by_target.clear()
        mg._xrefs_dirty.clear()

        # Populate pass.
        for row in self._fetch_xrefs(mg.metagraph_id):
            xref = self._row_to_xref(row)
            mg.identity.register(xref.xref_id)
            mg.xrefs[xref.xref_id] = xref
            mg._xrefs_by_source.setdefault(xref.source_id, set()).add(
                xref.xref_id
            )
            mg._xrefs_by_target.setdefault(
                (xref.target_metagraph_id, xref.target_id), set()
            ).add(xref.xref_id)

    def _fetch_xrefs(self, metagraph_id: str) -> List[Dict[str, Any]]:
        """Run the indexed XRef read against ``:XRef {source_metagraph_id}``.

        Phase 10 P53 reversal — query no longer needs new columns since
        ``properties(x)`` already returns the whole row including the
        restored ``target_stale`` + ``deprecated_at`` columns; the
        row-to-XRef projector reads them from there.
        """
        q = (
            "MATCH (x:XRef {source_metagraph_id: $mid}) "
            "RETURN x.id AS id, x.source_metagraph_id AS smid, "
            "       x.source_id AS sid, x.target_metagraph_id AS tmid, "
            "       x.target_role AS trole, x.target_id AS tid, "
            "       x.ref_type AS ref_type, properties(x) AS props"
        )
        return self._client.run_query(q, {"mid": metagraph_id}).rows

    def _row_to_xref(self, row: Dict[str, Any]) -> XRef:
        """Project a raw DB row to a Phase-10-shape :class:`XRef` (10 fields).

        Phase 10 P53 reversal — restores ``target_stale`` + ``deprecated_at``
        from row properties. v3-legacy rows missing these columns get
        sensible defaults (False / None).
        """
        raw_props = row.get("props") or {}
        # Phase 10 P53 — extract restored fields from props before strip.
        target_stale = bool(raw_props.get("target_stale") or False)
        deprecated_at = _parse_iso(raw_props.get("deprecated_at"))
        props = {
            k: v
            for k, v in raw_props.items()
            if k not in _CORE_XREF_FIELDS
        }
        return XRef(
            xref_id=row["id"],
            source_metagraph_id=row["smid"],
            source_id=row["sid"],
            target_metagraph_id=row["tmid"],
            target_role=row["trole"],
            target_id=row["tid"],
            ref_type=row["ref_type"],
            properties=props,
            target_stale=target_stale,
            deprecated_at=deprecated_at,
        )


def attach_xref_loader(mg: "Metagraph") -> ObserverHandle:
    """Subscribe an :class:`XRefLoader` to ``mg``'s after-load observer (M18).

    Idempotent — calling twice on the same metagraph wires the
    observer exactly once (Phase 06 P49 B precedent). Returns the
    :class:`ObserverHandle` the first time; the same handle on
    subsequent calls.

    The subscribed callback reads ``mg._persist_client`` at fire
    time (transient — set by :meth:`MetagraphLoader.load` /
    ``.refresh`` BEFORE the after-load dispatch). Per Phase 09 PB-7
    the loader re-fires on every refresh, clearing + re-populating
    ``mg.xrefs`` (PB-9 single-mode semantic).
    """
    existing = getattr(mg, _ATTACH_FLAG_ATTR, None)
    if existing is not None:
        return existing  # idempotent re-attach

    def _on_after_load(loaded_mg: "Metagraph") -> None:
        client = getattr(loaded_mg, "_persist_client", None)
        if client is None:
            # Loader-attached path requires _persist_client; fresh-
            # in-memory metagraphs (no client attached) have nothing
            # to load. Silent no-op preserves PB-9 single-mode
            # semantics for the non-loaded case.
            return
        XRefLoader(client).load_into(loaded_mg)

    handle = mg.register_after_load_observer(_on_after_load)
    setattr(mg, _ATTACH_FLAG_ATTR, handle)
    return handle


__all__ = [
    "XRefLoader",
    "attach_xref_loader",
]
