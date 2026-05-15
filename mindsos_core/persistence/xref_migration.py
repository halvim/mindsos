"""One-time migration: ``ref:global_*`` properties → :class:`XRef` rows (ADR-0128).

The pre-redesign convention stored cross-metagraph references as
``ref:global_<role>`` properties on Local nodes plus a ``ref_type``
property carrying the relationship semantic. Under the hybrid model
(ADR-0128), cross-metagraph refs are first-class :class:`XRef` rows;
intra-metagraph refs continue to use the property-string convention.

This module migrates an in-memory :class:`Metagraph`'s existing
property-string cross-metagraph refs to XRef rows. Idempotent: a
running with no matching properties is a no-op.

**Phase 09 — locked picks reflected here:**

* **M5 / RPB-4** — programmatic-only callable; no CLI verb. Caller
  invokes explicitly after ``load_metagraph``. Server first-start
  hook (P18+) is the production trigger.
* **M9** — flag key renamed from v3's ``server:xref_migrated_at`` to
  ``mg.properties["xref:migrated_at"]``. ``server:`` prefix implied
  Server-set; the L1 migration code itself sets it, so the namespace
  was wrong. ``xref:`` namespace added to ADR-0130 convention this
  phase (item H).
* **PB-4** — v3-verbatim signature
  ``migrate_in_memory(mg, *, target_metagraph_id, default_ref_type="SPECIALISES")``.
  Caller supplies ``target_metagraph_id`` explicitly; tests pass
  synthetic value; Server consumer (P18+) supplies real value.
* **RPB-2** — bare ``mg.add_xref`` calls; each inherits WAL crash
  safety per M16 (when ``mg._persist_client`` is set, inline WAL+DB
  write fires; otherwise dirty-mark for next persist per P54).
  Crash mid-migration → next ``recover()`` replays partial entries →
  re-run completes the rest (per-XRef ``already`` skip + flag-set on
  whole-loop completion).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..models.metagraph import Metagraph


_REF_GLOBAL_PREFIX = "ref:global_"
#: M9 — ``xref:`` namespace key. Added to ADR-0130 namespacing
#: convention this phase.
MIGRATION_FLAG = "xref:migrated_at"


def migrate_in_memory(
    mg: "Metagraph",
    *,
    target_metagraph_id: str,
    default_ref_type: str = "SPECIALISES",
) -> int:
    """Walk every node in ``mg`` and convert ``ref:global_<role>`` properties
    to :class:`XRef` rows pointing at ``target_metagraph_id``.

    Args:
        mg: in-memory :class:`Metagraph` to migrate.
        target_metagraph_id: id of the Global metagraph these refs
            point to. Caller supplies explicitly (PB-4).
        default_ref_type: ref_type to use when the source node lacks
            an explicit ``ref_type`` property.

    Returns:
        The number of XRefs created (skipped duplicates do not count).

    Idempotency:
      * Whole-metagraph short-circuit via ``mg.properties[MIGRATION_FLAG]``;
        a flagged migration returns 0 immediately.
      * Per-XRef content-tuple skip via ``mg.iter_xrefs(source_id=...)``
        — pre-existing XRefs matching ``(target_role, target_id)``
        are not re-created. The migrated property is still dropped.
      * Re-run with the flag cleared (e.g. partial-crash recovery)
        scans every node again; per-XRef skip avoids duplicates.
    """
    if MIGRATION_FLAG in mg.properties:
        return 0  # already migrated

    created = 0
    for graph in mg.graphs.values():
        for node in graph.nodes.values():
            ref_type = node.properties.get("ref_type", default_ref_type)
            keys_to_drop: List[str] = []
            for key, value in list(node.properties.items()):
                if not key.startswith(_REF_GLOBAL_PREFIX):
                    continue
                target_role = key[len(_REF_GLOBAL_PREFIX):]
                target_id = value
                # Per-XRef content-tuple dedup (idempotency).
                already = any(
                    x.target_role == target_role
                    and x.target_id == target_id
                    and x.target_metagraph_id == target_metagraph_id
                    for x in mg.iter_xrefs(source_id=node.node_id)
                )
                if already:
                    keys_to_drop.append(key)
                    continue
                mg.add_xref(
                    source_id=node.node_id,
                    target_metagraph_id=target_metagraph_id,
                    target_role=target_role,
                    target_id=target_id,
                    ref_type=str(ref_type),
                )
                created += 1
                keys_to_drop.append(key)
            # Drop the migrated property strings + ``ref_type`` if any
            # were migrated.
            for k in keys_to_drop:
                del node.properties[k]
            if keys_to_drop and "ref_type" in node.properties:
                del node.properties["ref_type"]

    mg.properties[MIGRATION_FLAG] = datetime.utcnow().isoformat()
    return created


__all__ = [
    "MIGRATION_FLAG",
    "migrate_in_memory",
]
