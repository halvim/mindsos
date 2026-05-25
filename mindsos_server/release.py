"""Release-ship orchestrator (Phase 24 — ADR-0118 §"Decision" §2).

Per ADR-0118 + ADR-0114 + ADR-0115 + ADR-0006 §am1 + ADR-0144 §am2 +
Phase 24 design log Rounds 1-5 PB-1..PB-28 + Round 0 PB-Z1..PB-Z22.

This module ships :func:`release_update` — admin's release-ship
entry-point. The release half of the ADR-0118 pivot model; the propose
half is in :mod:`mindsos_admin.promotion` (``propose_for_promotion``).

**Lock + transaction order:**

1. ``RELEASE_SHIP_LOCK.acquire()`` (threading.RLock per ADR-0006 §am1).
2. Build suppression set: ``SELECT manifest_json FROM releases WHERE
   status='FAILED' AND release_id > last_shipped_id`` (PB-Z15(a)).
3. ``admin_tx`` BEGIN IMMEDIATE on ``conn``:
   3a. SELECT snapshot set (``WHERE shipped_in_release IS NULL`` per
       PB-26(b)).
   3b. If empty → raise :class:`EmptyReleaseError` (PB-21(a)).
   3c. ``audit_gate.run(...)`` two-pass with suppression set (PB-24
       + PB-Z7). On blocking → raise (caught in outer); on Empty-
       ComparisonError → raise (caught in outer).
   3d. For each role in snapshot: per-role copy via in-memory
       ``add_node`` (PB-Z21.2; Cypher MERGE template documented in
       ADR-0118 §am2 for Phase 26). Track each succeeded role's
       canonical node_ids in Python local list per PB-Z3(a).
   3e. After all roles succeed: clear pending_global_mg's nodes for
       the snapshot set (PB-Z8(a) — SHIPPED path only; FAILED leaves
       pending intact for rerun).
   3f. INSERT ``releases`` SHIPPED row with full manifest_json per
       PB-22(a) + ADR-0114 §3.
   3g. UPDATE ``pending_mutations.shipped_in_release`` for snapshot.
   3h. Write ``EVT_RELEASE_SHIPPED`` audit row.
   3i. admin_tx __exit__ commits.
4. ``RELEASE_SHIP_LOCK.release()`` (try/finally).

**FAILED path (PB-Z3(a) — two admin_tx blocks):**

If a per-role copy raises (e.g. ``IdentityError`` on collision NOT
caught by Z7 suppression — would only happen on bug), OR audit gate
raises ``BlockingFindingError`` / ``EmptyComparisonError``: the
outer admin_tx ROLLBACKs (no SHIPPED row, no stamp). A SECOND
admin_tx then writes the FAILED row with manifest_json per ADR-0114
§3 FAILED shape (including ``failed_release_canonical_node_ids``
per Z7(a) from the Python-local roles_shipped tracking list).

**Rerun recovery per PB-Z1(b) + PB-Z7 + PB-Z15:**

On rerun after FAILED, the suppression set from PB-Z15 watermark
query excludes already-shipped canonical node_ids from cross-mg
audit-gate findings. The pending_global_mg still contains the
unsuccessful-batch nodes (FAILED path didn't clear). The per-role
copy uses in-memory ``add_node`` with the SAME pending node_id;
suppression prevented gate-failure; ``add_node`` raises
``IdentityError`` if the node already exists in canonical — caught
in the per-role loop with a "skip-if-already-present" check per
Z21.2 idempotency contract.

ADR cross-references: ADR-0118 §"Decision" §2 + §am2 (release-ship
+ Cypher template Phase 26 deferral); ADR-0114 §1 + §2 + §am3
(schema + manifest_json shapes); ADR-0115 (audit gate); ADR-0006
§am1 (RELEASE_SHIP_LOCK substrate); Phase 24 design log §1 PB-1 +
PB-10 + PB-12 + PB-20 + PB-21 + PB-22 + PB-25 + PB-26 + PB-27 +
PB-28 + Round 0 PB-Z1 + PB-Z3 + PB-Z7 + PB-Z8 + PB-Z15 + PB-Z20 +
PB-Z21 + PB-Z22.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Literal, Optional

from mindsos_core import Metagraph
from mindsos_core.persistence.client import Client

from mindsos_admin import audit_gate
from mindsos_admin.audit_gate import PendingMutationRow
from mindsos_admin.exceptions import (
    BlockingFindingError,
    EmptyComparisonError,
    EmptyReleaseError,
)
from mindsos_server.admin import admin_tx
from mindsos_server.audit import (
    EVT_RELEASE_FAILED,
    EVT_RELEASE_SHIPPED,
    write_audit,
)
from mindsos_server.authz import _require_or_audit
from mindsos_server.capabilities import CAN_APPROVE_RELEASE
from mindsos_server.locks import RELEASE_SHIP_LOCK
from mindsos_server.session import Session


__all__ = [
    "ReleaseResult",
    "ReleaseStatus",
    "release_update",
]


ReleaseStatus = Literal["SHIPPED", "FAILED"]


# ─── §1 ReleaseResult ───────────────────────────────────────────────────


@dataclass(frozen=True)
class ReleaseResult:
    """Return value from :func:`release_update`.

    Phase 24 design log PB-18(a) result-dataclass precedent.

    Attributes:
        release_id: ``releases.release_id`` of the row written
            (SHIPPED or FAILED).
        status: ``"SHIPPED"`` or ``"FAILED"``.
        mutations_shipped_count: For SHIPPED, number of pending rows
            stamped; for FAILED, always 0 per ADR-0114 §3.
        roles_affected: For SHIPPED, roles where canonical gained
            content; for FAILED, ``roles_shipped_before_failure``.
        audit_event_id: The EVT_RELEASE_SHIPPED or EVT_RELEASE_FAILED
            row.
        manifest_json: Full manifest_json content (SHIPPED or FAILED
            shape per ADR-0114 §3 + §am3).
        parent_release_id: For SHIPPED, the prior SHIPPED's
            release_id; for FAILED, None.
        error_class: For FAILED, one of the closed enum per ADR-
            0114 §am3 §4; for SHIPPED, None.
    """

    release_id: int
    status: ReleaseStatus
    mutations_shipped_count: int
    roles_affected: tuple[str, ...]
    audit_event_id: int
    manifest_json: dict[str, Any]
    parent_release_id: Optional[int] = None
    error_class: Optional[str] = None


# ─── §2 release_update ──────────────────────────────────────────────────


def release_update(
    conn: sqlite3.Connection,
    client: Optional[Client] = None,
    *,
    session: Session,
    canonical_global_mg: Metagraph,
    pending_global_mg: Metagraph,
) -> ReleaseResult:
    """Ship pending → canonical for the audit-gate-snapshot set.

    Per ADR-0118 §"Decision" §2 + ADR-0114 + ADR-0115 + Phase 24
    design log §1. Single admin command; SHIPPED+FAILED-only release
    lifecycle per PB-10(a).

    Phase 24 scope per design log §6:

    * SQLite + in-memory Metagraph only per PB-Z21(b). Cypher MERGE
      template deferred to Phase 26.
    * SHIPPED + FAILED CHECK constraint at v4 per PB-10(a).
    * No force-override (v2 per ADR-0118 §Tradeoffs).
    * Source-user-Local path deferred to Phase 25 (only ATOM admin-
      direct propose at v1).

    Args:
        conn: SQLite connection on ``server.db`` (WAL +
            foreign_keys ON per Phase 18 PB-19).
        session: Admin :class:`Session`. ``CAN_APPROVE_RELEASE``
            capability required per ADR-0002 §am2.
        canonical_global_mg: In-memory canonical-Global
            :class:`Metagraph` (Phase 14 KL bootstrap output OR
            Phase 15a ``bootstrap_global`` output). Mutated by the
            per-role copy (in-memory ``add_node``).
        pending_global_mg: In-memory pending-Global
            :class:`Metagraph` per PB-Z11(a). Read by audit gate;
            on SHIPPED path, nodes from the snapshot set are
            removed after canonical copy succeeds (PB-Z8(a)).

    Returns:
        :class:`ReleaseResult` with SHIPPED or FAILED status.

    Raises:
        PermissionDeniedError: ``session`` lacks
            ``CAN_APPROVE_RELEASE``.
        EmptyReleaseError: No unshipped pending_mutations rows
            (PB-21(a)). CLI exit code 7.
        BlockingFindingError: Audit gate found ≥1 blocking finding
            (PB-20(c)). FAILED row written before raise; CLI exit
            code 8.
        EmptyComparisonError: ``compute_similarity`` raised on a
            degenerate pair (ADR-0144 §am2; PB-Z16(a)). FAILED row
            written with ``error_class="empty_comparison"``;
            re-raised as BlockingFindingError-equivalent to caller.
    """
    # ── Step 0: capability check ────────────────────────────────────
    _require_or_audit(
        conn, session, CAN_APPROVE_RELEASE, verb="release_update"
    )

    # ── Step 1: acquire RELEASE_SHIP_LOCK (outer; threading) ────────
    with RELEASE_SHIP_LOCK:
        return _release_update_locked(
            conn,
            client,
            session=session,
            canonical_global_mg=canonical_global_mg,
            pending_global_mg=pending_global_mg,
        )


def _release_update_locked(
    conn: sqlite3.Connection,
    client: Optional[Client],
    *,
    session: Session,
    canonical_global_mg: Metagraph,
    pending_global_mg: Metagraph,
) -> ReleaseResult:
    """Body of :func:`release_update` inside RELEASE_SHIP_LOCK.

    Two admin_tx blocks pattern per PB-Z3(a):

    * Outer: SELECT snapshot + audit gate + per-role copy +
      pending clear + INSERT SHIPPED + UPDATE stamps.
    * Inner FAILED-path: on outer exception, second admin_tx
      writes FAILED row + EVT_RELEASE_FAILED.

    Python-local ``roles_shipped`` + ``shipped_canonical_node_ids``
    track per-role progress across the exception boundary so the
    FAILED-row manifest_json can populate
    ``failed_release_canonical_node_ids`` per Z7(a).
    """
    proposed_at_iso = _utcnow_iso()
    proposer = session.user_id

    # ── Step 2: Build suppression set from prior-FAILED rows ────────
    # PB-Z15(a) — watermark query: FAILED rows since last SHIPPED.
    suppression: dict[str, list[str]] = _build_suppression_set(conn)

    # Python-local tracking for FAILED-path manifest content.
    roles_shipped_before_failure: list[str] = []
    shipped_canonical_node_ids: dict[str, list[str]] = {}

    # Snapshot info needed by FAILED-row writer in case of exception.
    snapshot_rows: list[PendingMutationRow] = []
    snapshot_mutations_attempted = 0
    failed_at_role: Optional[str] = None
    error_class: Optional[str] = None
    failure_to_raise: Optional[Exception] = None

    try:
        with admin_tx(conn):
            # 2a. SELECT snapshot set (PB-26(b) — `shipped_in_release
            # IS NULL` is the natural pending predicate).
            snapshot_rows = _select_snapshot(conn)
            snapshot_mutations_attempted = len(snapshot_rows)

            # 2b. Empty release → strict-fail per PB-21(a).
            if not snapshot_rows:
                raise EmptyReleaseError()

            # 2c. Audit gate (two-pass per PB-24; suppression per Z7).
            try:
                gate_result = audit_gate.run(
                    session,
                    client,
                    pending_mutations=snapshot_rows,
                    canonical_global_mg=canonical_global_mg,
                    pending_global_mg=pending_global_mg,
                    prior_failed_canonical_ids=suppression,
                )
            except EmptyComparisonError as exc:
                # PB-Z16(a) — propagate as FAILED with error_class.
                error_class = "empty_comparison"
                # Capture rough role from snapshot's first row (Empty-
                # Comparison doesn't carry role; best-effort attribution).
                failed_at_role = snapshot_rows[0].target_role if snapshot_rows else None
                failure_to_raise = exc
                raise

            if not gate_result.passed:
                # Blocking findings — auto-abort per PB-20(c).
                error_class = "blocking_similarity_findings"
                failed_at_role = (
                    gate_result.blocking_findings[0].role
                    if gate_result.blocking_findings else None
                )
                failure_to_raise = BlockingFindingError(
                    list(gate_result.blocking_findings)
                )
                raise failure_to_raise

            # 2d. Per-role copy: pending → canonical via in-memory
            # add_node per PB-Z21.2. Group snapshot rows by target_role.
            rows_by_role: dict[str, list[PendingMutationRow]] = {}
            for row in snapshot_rows:
                rows_by_role.setdefault(row.target_role, []).append(row)

            try:
                for role, role_rows in rows_by_role.items():
                    failed_at_role = role  # update on each iteration
                    role_node_ids = _copy_role_pending_to_canonical(
                        client=client,
                        role=role,
                        role_rows=role_rows,
                        canonical_global_mg=canonical_global_mg,
                        pending_global_mg=pending_global_mg,
                        suppression=suppression.get(role, []),
                    )
                    shipped_canonical_node_ids[role] = role_node_ids
                    roles_shipped_before_failure.append(role)
                # All roles succeeded; clear failed_at_role.
                failed_at_role = None
            except Exception as exc:
                error_class = type(exc).__name__
                failure_to_raise = exc
                raise

            # 2e. Clear pending nodes for snapshot set (PB-Z8(a) +
            # PB-Z20(a) — node-id-scoped, NOT graph-wide). FAILED
            # path skips this (handled by exception above).
            _clear_pending_for_snapshot(
                pending_global_mg=pending_global_mg,
                snapshot_rows=snapshot_rows,
            )

            # 2f. INSERT SHIPPED releases row.
            parent_release_id = _query_last_shipped_release_id(conn)
            shipped_manifest = _build_shipped_manifest_json(
                snapshot_rows=snapshot_rows,
                shipped_canonical_node_ids=shipped_canonical_node_ids,
                shipped_at_iso=proposed_at_iso,
                audit_event_id_placeholder=-1,  # patched at step 2h
            )

            # Pre-write the EVT_RELEASE_SHIPPED audit row so we have
            # audit_event_id for the releases row FK + manifest_json.
            shipped_event_extra: dict[str, Any] = {
                "release_id": -1,  # patched after INSERT releases
                "mutations_shipped_count": len(snapshot_rows),
                "roles_affected": sorted(shipped_canonical_node_ids.keys()),
                "parent_release_id": parent_release_id,
            }
            write_audit(
                conn,
                actor=proposer,
                event=EVT_RELEASE_SHIPPED,
                target=None,
                extra=shipped_event_extra,
            )
            audit_event_id = int(_lastrowid(conn))
            shipped_manifest["audit_event_id"] = audit_event_id

            cur = conn.execute(
                """
                INSERT INTO releases (
                    parent_release_id,
                    proposer_admin_user_id,
                    approver_admin_user_ids_json,
                    proposed_at,
                    shipped_at,
                    failed_at,
                    manifest_json,
                    audit_event_id,
                    status
                ) VALUES (?, ?, NULL, ?, ?, NULL, ?, ?, 'SHIPPED')
                """,
                (
                    parent_release_id,
                    proposer,
                    proposed_at_iso,
                    proposed_at_iso,
                    json.dumps(shipped_manifest, sort_keys=True),
                    audit_event_id,
                ),
            )
            release_id = int(cur.lastrowid)

            # Patch the audit row's extra_json with the now-known release_id.
            shipped_event_extra["release_id"] = release_id
            conn.execute(
                "UPDATE audit SET extra_json = ? WHERE id = ?",
                (json.dumps(shipped_event_extra, sort_keys=True), audit_event_id),
            )

            # 2g. UPDATE pending_mutations stamps.
            mutation_ids = [row.mutation_id for row in snapshot_rows]
            conn.executemany(
                "UPDATE pending_mutations SET shipped_in_release = ? "
                "WHERE mutation_id = ?",
                [(release_id, mid) for mid in mutation_ids],
            )

            # admin_tx __exit__ commits.

        # Outer try-block path: SHIPPED.
        return ReleaseResult(
            release_id=release_id,
            status="SHIPPED",
            mutations_shipped_count=len(snapshot_rows),
            roles_affected=tuple(sorted(shipped_canonical_node_ids.keys())),
            audit_event_id=audit_event_id,
            manifest_json=shipped_manifest,
            parent_release_id=parent_release_id,
            error_class=None,
        )

    except EmptyReleaseError:
        # Strict-fail per PB-21(a): no row written; admin_tx already
        # rolled back via __exit__; just re-raise to CLI.
        raise

    except (BlockingFindingError, EmptyComparisonError, Exception) as exc:
        # admin_tx __exit__ rolled back. Second admin_tx writes FAILED.
        # `error_class` and `failed_at_role` were captured above.
        if error_class is None:
            error_class = type(exc).__name__
        failed_at_iso = _utcnow_iso()

        failed_manifest = _build_failed_manifest_json(
            snapshot_rows=snapshot_rows,
            roles_shipped_before_failure=roles_shipped_before_failure,
            shipped_canonical_node_ids=shipped_canonical_node_ids,
            failed_at_role=failed_at_role,
            error_class=error_class,
            mutations_attempted_count=snapshot_mutations_attempted,
            failed_at_iso=failed_at_iso,
            audit_event_id_placeholder=-1,
        )

        with admin_tx(conn):
            failed_event_extra: dict[str, Any] = {
                "release_id": None,  # patched after INSERT releases
                "failed_at_role": failed_at_role,
                "error_class": error_class,
                "mutations_attempted_count": snapshot_mutations_attempted,
                "roles_shipped_before_failure": list(roles_shipped_before_failure),
            }
            write_audit(
                conn,
                actor=proposer,
                event=EVT_RELEASE_FAILED,
                target=None,
                extra=failed_event_extra,
            )
            audit_event_id_failed = int(_lastrowid(conn))
            failed_manifest["audit_event_id"] = audit_event_id_failed

            cur = conn.execute(
                """
                INSERT INTO releases (
                    parent_release_id,
                    proposer_admin_user_id,
                    approver_admin_user_ids_json,
                    proposed_at,
                    shipped_at,
                    failed_at,
                    manifest_json,
                    audit_event_id,
                    status
                ) VALUES (NULL, ?, NULL, ?, NULL, ?, ?, ?, 'FAILED')
                """,
                (
                    proposer,
                    proposed_at_iso,
                    failed_at_iso,
                    json.dumps(failed_manifest, sort_keys=True),
                    audit_event_id_failed,
                ),
            )
            failed_release_id = int(cur.lastrowid)

            failed_event_extra["release_id"] = failed_release_id
            conn.execute(
                "UPDATE audit SET extra_json = ? WHERE id = ?",
                (json.dumps(failed_event_extra, sort_keys=True), audit_event_id_failed),
            )

        # FAILED row written + committed. Re-raise the original
        # exception so the CLI exit-code mapper can distinguish
        # blocking-vs-empty-vs-FalkorDB.
        if isinstance(exc, BlockingFindingError):
            raise
        if isinstance(exc, EmptyComparisonError):
            # Promote to BlockingFindingError per ADR-0144 §am2 + PB-
            # Z16(a) — caller treats as a strict-default failure.
            # Carry the original cause.
            raise BlockingFindingError(
                blocking_findings=[]
            ) from exc
        raise


# ─── §3 Helpers ─────────────────────────────────────────────────────────


def _build_suppression_set(
    conn: sqlite3.Connection,
) -> dict[str, list[str]]:
    """Build the rerun-suppression set per PB-Z15(a).

    Query: FAILED rows since last SHIPPED. Union their
    ``failed_release_canonical_node_ids`` per role.
    """
    cur = conn.execute(
        """
        SELECT manifest_json
          FROM releases
         WHERE status = 'FAILED'
           AND release_id > COALESCE(
             (SELECT MAX(release_id) FROM releases WHERE status = 'SHIPPED'),
             0
           )
        """
    )
    suppression: dict[str, list[str]] = {}
    for (manifest_str,) in cur:
        manifest = json.loads(manifest_str)
        per_role = manifest.get("failed_release_canonical_node_ids", {})
        for role, ids in per_role.items():
            suppression.setdefault(role, []).extend(ids)
    return suppression


def _select_snapshot(conn: sqlite3.Connection) -> list[PendingMutationRow]:
    """SELECT the unshipped pending_mutations snapshot per PB-26(b).

    Snapshot is ordered by ``mutation_id`` ASC (AUTOINCREMENT
    order; deterministic per Phase 24 design log clause 5 + ADR-
    0114 §am3).
    """
    cur = conn.execute(
        """
        SELECT mutation_id,
               proposer_admin_user_id,
               source_user_id,
               payload_json
          FROM pending_mutations
         WHERE shipped_in_release IS NULL
         ORDER BY mutation_id
        """
    )
    rows: list[PendingMutationRow] = []
    for mutation_id, proposer_id, source_user_id, payload_json in cur:
        payload = json.loads(payload_json)
        node = payload["node"]
        rows.append(
            PendingMutationRow(
                mutation_id=mutation_id,
                proposer_admin_user_id=proposer_id,
                target_role=node["target_role"],
                node_id=payload["node_id"],
                node_type=node["node_type"],
                source_user_id=source_user_id,
            )
        )
    return rows


_RELEASE_MERGE_CYPHER = (
    "MERGE (dst:Node {node_id: $node_id, "
    "                  metagraph_id: $canonical_mg_id, "
    "                  graph_id: $canonical_graph_id}) "
    "ON CREATE SET dst += $props "
    "ON MATCH SET dst += $props "
    "WITH dst "
    "MATCH (g:Graph {id: $canonical_graph_id}) "
    "MERGE (dst)-[:IN_GRAPH]->(g)"
)
"""Phase 26a §am3 release-time MERGE template (§am5 :IN_GRAPH closure at Phase 28).

Per ADR-0118 §amendment-3 §"Decision §2" — supersedes §am2's per-
FalkorDB-graph form (substrate-incompatible per Phase 26a R5-PB-1).
Idempotent on rerun: MERGE-on-(canonical_mg_id, canonical_graph_id,
node_id) is no-op when dst exists with unchanged properties; SET on
existing dst with identical props produces no write.

Per ADR-0118 §amendment-5 (Phase 28, B-26b-T5 closure): the trailing
``MATCH (g:Graph {id: $canonical_graph_id}) MERGE (dst)-[:IN_GRAPH]->(g)``
clause links the released Node to its canonical Graph anchor so that
``MetagraphLoader.load(canonical_id)`` (which traverses
``[:IN_METAGRAPH]→[:IN_GRAPH]``) surfaces release-shipped content.
The MERGE is idempotent — re-running release on the same node MERGEs
the same relationship without duplication. The MATCH requires the
Graph anchor row to already exist (guaranteed by the pair-helper's
bootstrap-on-load).
"""


def _copy_role_pending_to_canonical(
    *,
    client: Optional[Client],
    role: str,
    role_rows: list[PendingMutationRow],
    canonical_global_mg: Metagraph,
    pending_global_mg: Metagraph,
    suppression: Iterable[str],
) -> list[str]:
    """Copy one role's pending nodes into canonical via in-memory
    ``add_node`` (PB-Z21.2). Returns the canonical node_ids landed.

    Per PB-Z9(a) — pending node_id IS canonical node_id. Suppression
    set elements (canonical IDs from prior FAILED) are SKIPPED here
    (already in canonical from prior FAILED's partial-ship; re-adding
    would raise IdentityError). On rerun, ``add_node`` is called only
    for pending IDs NOT in the suppression set.

    The Cypher MERGE-on-node_id template documented in ADR-0118 §am2
    is the Phase 26 contract for the FalkorDB-backed version.

    Args:
        role: Target role-graph name.
        role_rows: PendingMutationRows for this role.
        canonical_global_mg: Mutated by add_node.
        pending_global_mg: Read by node-lookup (NodeSpec value /
            properties / type are stored at pending side).
        suppression: Canonical node_ids known-shipped from prior
            FAILED — skipped to avoid IdentityError on re-add.

    Returns:
        List of canonical node_ids that landed in canonical_global_mg
        on THIS invocation (excludes suppression-skipped, since they
        landed on a prior call).
    """
    suppression_set = frozenset(suppression)
    canonical_graph = _find_role_graph(canonical_global_mg, role)
    pending_graph = _find_role_graph(pending_global_mg, role)
    if canonical_graph is None:
        raise RuntimeError(
            f"canonical_global_mg has no role-graph for {role!r}; "
            f"expected eager bootstrap parity with pending."
        )
    if pending_graph is None:
        raise RuntimeError(
            f"pending_global_mg has no role-graph for {role!r}; "
            f"propose+ship topology drift."
        )

    landed: list[str] = []
    for row in role_rows:
        node_id = row.node_id
        if node_id in suppression_set:
            # Already landed in canonical on a prior FAILED partial-ship.
            # Skip; canonical state is correct per PB-Z9(a) MERGE
            # idempotence.
            continue
        # Look up the candidate node in pending side.
        pending_node = pending_graph.nodes.get(node_id)
        if pending_node is None:
            raise RuntimeError(
                f"pending_global_mg.{role} missing node {node_id!r} "
                f"declared in pending_mutations snapshot; in-memory "
                f"drift from SQLite ledger. Restart server to "
                f"rehydrate via mindsos_admin.promotion."
                f"rehydrate_pending_global()."
            )
        canonical_graph.add_node(
            pending_node.value,
            pending_node.type_name,
            properties=dict(pending_node.properties),
            node_id=node_id,
        )

        # Phase 26a §am3 — release-time FalkorDB MERGE. Per-role
        # independence preserved: MERGE-on-(canonical_mg_id,
        # canonical_graph_id, node_id) is idempotent on rerun.
        # Per Phase 25 hard_delete_user persister=None precedent,
        # `client is None` means caller wants in-memory only (Phase
        # 24 contract); Cypher write opt-in via passing live Client.
        if client is not None:
            falkor_props: dict[str, Any] = {
                "value": pending_node.value,
                "node_type": pending_node.type_name,
            }
            for pk, pv in pending_node.properties.items():
                falkor_props[f"prop_{pk}"] = pv
            client.run_query(
                _RELEASE_MERGE_CYPHER,
                {
                    "node_id": node_id,
                    "canonical_mg_id": canonical_global_mg.metagraph_id,
                    "canonical_graph_id": canonical_graph.graph_id,
                    "props": falkor_props,
                },
            )

        landed.append(node_id)
    return landed


def _clear_pending_for_snapshot(
    *,
    pending_global_mg: Metagraph,
    snapshot_rows: list[PendingMutationRow],
) -> None:
    """Remove the snapshot's pending nodes from pending_global_mg.

    Per PB-Z8(a) + PB-Z20(a) — node-id-scoped removal (NOT graph-
    wide). Only called on SHIPPED happy path; FAILED path leaves
    pending intact for rerun-recovery.

    Concurrent ``propose_for_promotion`` adding new nodes between
    snapshot-SELECT and this clear is preserved (different node_id;
    survives the removal loop).
    """
    by_role: dict[str, list[str]] = {}
    for row in snapshot_rows:
        by_role.setdefault(row.target_role, []).append(row.node_id)
    for role, node_ids in by_role.items():
        graph = _find_role_graph(pending_global_mg, role)
        if graph is None:
            continue  # defensive; shouldn't happen if topology consistent
        for nid in node_ids:
            # Best-effort: skip if already removed (idempotent).
            if nid in graph.nodes:
                graph.remove_node(nid)


def _build_shipped_manifest_json(
    *,
    snapshot_rows: list[PendingMutationRow],
    shipped_canonical_node_ids: dict[str, list[str]],
    shipped_at_iso: str,
    audit_event_id_placeholder: int,
) -> dict[str, Any]:
    """SHIPPED manifest_json per ADR-0114 §3 + §am3 clause 5.

    `included_mutation_ids` is AUTOINCREMENT order from the snapshot
    SELECT (mutation_id ASC); replaces ADR-0056's input-order
    semantic per Z6(c).
    """
    return {
        "included_mutation_ids": [row.mutation_id for row in snapshot_rows],
        "rewrite_map": {},  # empty at admin-direct ATOM (PB-22(a))
        "roles_affected": sorted(shipped_canonical_node_ids.keys()),
        "audit_event_id": audit_event_id_placeholder,  # patched by caller
        "shipped_at": shipped_at_iso,
    }


def _build_failed_manifest_json(
    *,
    snapshot_rows: list[PendingMutationRow],
    roles_shipped_before_failure: list[str],
    shipped_canonical_node_ids: dict[str, list[str]],
    failed_at_role: Optional[str],
    error_class: str,
    mutations_attempted_count: int,
    failed_at_iso: str,
    audit_event_id_placeholder: int,
) -> dict[str, Any]:
    """FAILED manifest_json per ADR-0114 §3 + §am3 clause 1.

    ``failed_release_canonical_node_ids`` is the per-role node-id
    map for PB-Z7(a) suppression on rerun.
    """
    return {
        "included_mutation_ids": [],
        "rewrite_map": {},
        "roles_affected": list(roles_shipped_before_failure),
        "failed_at_role": failed_at_role,
        "error_class": error_class,
        "mutations_attempted_count": mutations_attempted_count,
        "audit_event_id": audit_event_id_placeholder,  # patched by caller
        "shipped_at": None,
        "failed_at": failed_at_iso,
        "failed_release_canonical_node_ids": dict(shipped_canonical_node_ids),
    }


def _query_last_shipped_release_id(
    conn: sqlite3.Connection,
) -> Optional[int]:
    """SELECT MAX(release_id) FROM releases WHERE status='SHIPPED'.

    Returns None if no prior SHIPPED row exists (first release).
    """
    cur = conn.execute(
        "SELECT MAX(release_id) FROM releases WHERE status = 'SHIPPED'"
    )
    row = cur.fetchone()
    if row is None or row[0] is None:
        return None
    return int(row[0])


def _find_role_graph(metagraph: Metagraph, role: str):
    """Find the Graph in ``metagraph`` whose ``role`` matches.

    Mirrors the helper in :mod:`mindsos_admin.promotion`. Returns
    None if no match.
    """
    for g in metagraph.graphs.values():
        if g.role == role:
            return g
    return None


def _utcnow_iso() -> str:
    """Current UTC timestamp ISO-8601 with millisecond precision."""
    now = datetime.now(timezone.utc)
    return now.isoformat(timespec="milliseconds")


def _lastrowid(conn: sqlite3.Connection) -> int:
    """Return the most-recent INSERT's rowid on ``conn``."""
    cur = conn.execute("SELECT last_insert_rowid()")
    row = cur.fetchone()
    if row is None or row[0] is None:
        raise RuntimeError(
            "SQLite last_insert_rowid() returned NULL post-INSERT."
        )
    return int(row[0])
