"""Admin promotion entry-point (Phase 24 — ATOM admin-direct only).

Per ADR-0118 + ADR-0141 §am1 + ADR-0144 §am2 + Phase 24 design log
Round 1 PB-1..PB-6 (scope-shaping) + Round 4 PB-18..PB-23 (data shapes)
+ Round 0 PB-Z1..PB-Z21 (rerun-recovery + persistence deferral).

This module ships :func:`propose_for_promotion` — admin's entry-point
for adding a candidate to the pending-Global buffer. The function is
the propose half of the ADR-0118 pivot model; the release half ships
in :mod:`mindsos_server.release` (``release_update``).

**Scope at Phase 24 (v1 narrow):**

* **ATOM admin-direct only.** ``PromotionItem.source_user_id is not
  None`` (admin-on-behalf-of-user) raises :class:`NotImplementedError`
  (Phase 24 design log PB-11(a)); the source-user-Local path defers
  to Phase 25 alongside cross-user read substrate per ADR-0008 §am1.
* **STRUCTURE / SUBGRAPH / PIPELINE** dispatch raises
  :class:`NotImplementedError` per Phase 24 design log PB-3(a):
  STRUCTURE gates on Core ``CompositionalMetaEdge`` (Phase 05a
  Dropped); PIPELINE gates on L3 ship (Phases 33-35 unshipped);
  SUBGRAPH has no extractor precedent.
* **SQLite + in-memory Metagraph only** per Phase 24 design log PB-
  Z21(b). Cypher MERGE-on-id template documented in ADR-0118 §am2 as
  *Phase 26 contract*, NOT active code at Phase 24. Restart
  rehydration is via ``pending_mutations.payload_json`` per PB-Z21.1.

**Two-store write per PB-25(a):**

1. ``admin_tx`` BEGIN IMMEDIATE on ``server.db``.
2. INSERT ``pending_mutations`` row (payload_json serialized).
3. ``pending_global_mg.graphs[role].add_node(...)`` in-memory.
4. Write ``EVT_PROMOTION_PROPOSED`` audit row.
5. COMMIT.

On any failure between steps 2 and 4, ``admin_tx`` ROLLBACK undoes
the SQLite side; the in-memory ``add_node`` (step 3) is reverted via
``remove_node`` in a finally block.

**Capability check** (Phase 21 ``_require_or_audit`` pattern):
``CAN_PROPOSE_MUTATION`` gated; denial writes ``EVT_PERMISSION_DENIED``
audit row + raises :class:`PermissionDeniedError`.

**Audit payload** per Phase 24 design log PB-27(a) +
:data:`mindsos_server.audit.EVT_PROMOTION_PROPOSED` docstring.

ADR cross-references: ADR-0118 §am1 + §am2 (surface location +
Cypher templates); ADR-0141 §am1 (admin-relocation); ADR-0114 §1 +
§am3 (pending_mutations schema + payload_json shape); ADR-0002 §am2
(CAN_PROPOSE_MUTATION); Phase 24 design log §1 PB-3 + PB-8 + PB-11 +
PB-18 + PB-19 + PB-23 + PB-25 + PB-27 + PB-Z21.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional, Sequence

from mindsos_core import Metagraph
from mindsos_core.persistence.client import Client

from mindsos_admin.exceptions import AdminError
from mindsos_server.audit import EVT_PROMOTION_PROPOSED, write_audit
from mindsos_server.authz import _require_or_audit
from mindsos_server.capabilities import CAN_PROPOSE_MUTATION
from mindsos_server.session import Session


# ─── §0 §am3 Cypher template (Phase 26a) ────────────────────────────────
#
# Per ADR-0118 §amendment-3 §"Decision §1" — incremental MERGE keyed on
# (metagraph_id, graph_id, node_id) into the SINGLE FalkorDB graph
# configured by FalkorConfig.graph. Supersedes §am2's per-FalkorDB-
# graph-per-role naming (substrate-incompatible per Phase 26a R5-PB-1).
_PROPOSE_MERGE_CYPHER = (
    "MERGE (n:Node {node_id: $node_id, "
    "               metagraph_id: $metagraph_id, "
    "               graph_id: $graph_id}) "
    "ON CREATE SET n += $props "
    "ON MATCH SET n += $props "
    "WITH n "
    "MATCH (g:Graph {id: $graph_id}) "
    "MERGE (n)-[:IN_GRAPH]->(g)"
)
"""Phase 24/26a §am3 propose-time MERGE template (§am5 :IN_GRAPH closure at Phase 28).

Symmetric to ``mindsos_server.release._RELEASE_MERGE_CYPHER``. Per
ADR-0118 §amendment-5 (Phase 28, B-26b-T5 closure): the trailing
``MATCH (g:Graph {id: $graph_id}) MERGE (n)-[:IN_GRAPH]->(g)`` clause
links the proposed Node to its Graph anchor so the pending state is
graph-traversal-reachable on the forensic-only side too. Idempotent on
re-propose; MATCH requires the Graph anchor row (bootstrap-on-load
guarantee).
"""


__all__ = [
    "PromotionItemKind",
    "NodeSpec",
    "PromotionItem",
    "PromotionProposal",
    "PromotionResult",
    "propose_for_promotion",
    "rehydrate_pending_global",
    "rehydrate_canonical_global",
    "rehydrate_global_metagraphs",
]


# ─── §1 Enum ────────────────────────────────────────────────────────────


class PromotionItemKind(str, Enum):
    """Kind of promotion item per PIVOT §7.1 + ADR-0118.

    Phase 24 ships all four enum values for forward-shape contract per
    Phase 24 design log PB-3(a) + PB-18(a) — but only :attr:`ATOM` has
    a validator at Phase 24. The other three raise
    :class:`NotImplementedError` when dispatched via
    :func:`propose_for_promotion`:

    * :attr:`STRUCTURE` — needs Core ``CompositionalMetaEdge`` (Phase
      05a Dropped); validator ships at post-Core-retrofit phase.
    * :attr:`SUBGRAPH` — needs subgraph extractor (no halvim
      precedent); validator ships at own phase.
    * :attr:`PIPELINE` — cross-layer L3+L2 (L3 unshipped); validator
      ships at post-L3 phase (33-35).

    PIVOT §7.1's ``register_promotion_kind()`` extensibility registry
    deferred to first multi-kind phase per Phase 24 design log PB-
    16(a) — hardcoded dispatch in :func:`propose_for_promotion` at
    Phase 24.
    """

    ATOM = "ATOM"
    STRUCTURE = "STRUCTURE"
    SUBGRAPH = "SUBGRAPH"
    PIPELINE = "PIPELINE"


# ─── §2 NodeSpec ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NodeSpec:
    """Specification of a single node for an ATOM promotion.

    Per Phase 24 design log PB-19(b) — NodeSpec is the only spec
    dataclass that ships at Phase 24; ``EdgeSpec`` /
    ``MetaEdgeSpec`` are PEP 563 forward-refs in :class:`PromotionItem`
    and ship at STRUCTURE phase.

    Attributes:
        node_type: NodeType name in the target role-graph's schema.
            ``Graph.add_node`` validates against the attached
            :class:`mindsos_core.Schema`.
        value: Primary display value per
            :meth:`mindsos_core.Graph.add_node`.
        properties: Open property bag forwarded to ``add_node``.
        target_role: The role-graph in the pending-Global Metagraph
            that the node lands in. One of the 6 named Global roles
            (``ontology``, ``lexicon``, ``concepts``, etc.) — REJECTED
            for Local-only roles by ``ensure_global_role_graph``.
    """

    node_type: str
    value: Any
    properties: Mapping[str, Any]
    target_role: str

    def to_payload_dict(self) -> dict[str, Any]:
        """Serialise to JSON-safe dict for ``payload_json`` storage.

        Per Phase 24 design log PB-Z21.1 — ``pending_mutations.
        payload_json`` is the authoritative restart-rehydration
        source. Shape locks at this method.
        """
        return {
            "node_type": self.node_type,
            "value": self.value,
            "properties": dict(self.properties),
            "target_role": self.target_role,
        }

    @classmethod
    def from_payload_dict(cls, d: Mapping[str, Any]) -> "NodeSpec":
        """Deserialise from ``payload_json`` content. Inverse of
        :meth:`to_payload_dict`.

        Per PB-Z21.1 — consumed by :func:`rehydrate_pending_global`
        on CLI re-invocation.
        """
        return cls(
            node_type=d["node_type"],
            value=d["value"],
            properties=dict(d["properties"]),
            target_role=d["target_role"],
        )


# ─── §3 PromotionItem ───────────────────────────────────────────────────


@dataclass(frozen=True)
class PromotionItem:
    """A single item within a :class:`PromotionProposal`.

    Per Phase 24 design log PB-18(a) — full PIVOT §7.1 shape ships at
    Phase 24 for forward-shape contract. ATOM populates :attr:`node`;
    future kinds populate the EdgeSpec / MetaEdgeSpec / pipeline_iri /
    subgraph_iri forward-refs at their ship phase.

    Attributes:
        kind: Which :class:`PromotionItemKind` this item is. Phase 24
            validates only :attr:`PromotionItemKind.ATOM`.
        node: Required for ATOM kind; None for other kinds.
        edges: Forward-ref ``list[EdgeSpec]`` for STRUCTURE / SUBGRAPH;
            empty at Phase 24 ATOM-only.
        meta_edges: Forward-ref ``list[MetaEdgeSpec]`` for STRUCTURE;
            empty at Phase 24.
        pipeline_iri: Forward-ref for PIPELINE; None at Phase 24.
        subgraph_iri: Forward-ref for SUBGRAPH; None at Phase 24.
        source_user_id: When set, admin-on-behalf-of-user path —
            **raises NotImplementedError at Phase 24** per PB-11(a).
            v1 ATOM admin-direct only.
    """

    kind: PromotionItemKind
    node: Optional[NodeSpec] = None
    edges: tuple = field(default_factory=tuple)         # list["EdgeSpec"] forward-ref
    meta_edges: tuple = field(default_factory=tuple)    # list["MetaEdgeSpec"] forward-ref
    pipeline_iri: Optional[str] = None                  # PIPELINE forward-ref
    subgraph_iri: Optional[str] = None                  # SUBGRAPH forward-ref
    source_user_id: Optional[str] = None                # Phase 25 path

    def __post_init__(self) -> None:
        # Phase 24 validator: ATOM requires node; other kinds raise on
        # dispatch (handled in propose_for_promotion).
        if self.kind == PromotionItemKind.ATOM and self.node is None:
            raise ValueError(
                "PromotionItem(kind=ATOM) requires node: NodeSpec; got None."
            )


# ─── §4 PromotionProposal ───────────────────────────────────────────────


@dataclass(frozen=True)
class PromotionProposal:
    """Batched set of :class:`PromotionItem` per
    :func:`propose_for_promotion` call.

    Per Phase 24 design log PB-18(a) — full PIVOT §7.1 shape. v1
    proposals are admin-direct ATOM-only batches; size unbounded.

    Attributes:
        items: One or more :class:`PromotionItem`. Empty proposal
            raises ``ValueError`` at :func:`propose_for_promotion`.
        reason: Free-text rationale; copied to audit row's
            ``extra_json.reason``.
    """

    items: Sequence[PromotionItem]
    reason: str = ""


# ─── §5 PromotionResult ─────────────────────────────────────────────────


@dataclass(frozen=True)
class PromotionResult:
    """Return value from :func:`propose_for_promotion`.

    Per Phase 24 design log PB-18(a) — result dataclass precedent
    inherited from Phase 18-22.

    Attributes:
        mutation_ids: ``pending_mutations.mutation_id`` rows created
            by this call (AUTOINCREMENT order; same as
            ``items``-order at propose).
        audit_event_id: ``audit.id`` of the
            :data:`EVT_PROMOTION_PROPOSED` row.
        proposed_at: ISO-8601 UTC timestamp of the propose call.
    """

    mutation_ids: tuple[int, ...]
    audit_event_id: int
    proposed_at: str


# ─── §6 propose_for_promotion ───────────────────────────────────────────


def propose_for_promotion(
    conn: sqlite3.Connection,
    client: Optional[Client] = None,
    *,
    session: Session,
    proposal: PromotionProposal,
    pending_global_mg: Metagraph,
) -> PromotionResult:
    """Add a batch of pending mutations + write them into pending_global.

    Per ADR-0118 + ADR-0141 §am1 — admin's entry-point for adding
    candidates to the pending-Global buffer. The propose half of the
    pivot model; the release half (canonical ship) is in
    :func:`mindsos_server.release.release_update`.

    Phase 24 scope per design log §6 (out-of-scope at this ship):

    * ATOM admin-direct only — :class:`PromotionItemKind.STRUCTURE` /
      ``SUBGRAPH`` / ``PIPELINE`` dispatch raises
      :class:`NotImplementedError` (PB-3(a)).
    * ``source_user_id is not None`` raises :class:`NotImplementedError`
      (PB-11(a)).
    * SQLite + in-memory Metagraph writes only — FalkorDB Cypher
      template documented in ADR-0118 §am2 as Phase 26 contract
      (PB-Z21(b)).

    Args:
        conn: SQLite connection on ``server.db``. Must be opened via
            :func:`mindsos_server._db.open_db` (WAL + foreign_keys +
            busy_timeout pragmas set per Phase 18 PB-19).
        session: Admin :class:`mindsos_server.session.Session`.
            ``CAN_PROPOSE_MUTATION`` capability required per ADR-0002
            §am2 + Phase 24 design log PB-23(a).
        proposal: :class:`PromotionProposal` with ≥1 ATOM item.
        pending_global_mg: The in-memory pending-Global
            :class:`Metagraph` parallel to canonical per PB-Z11(a) +
            PB-15(a). Mutations write here; canonical is NOT touched
            by propose.

    Returns:
        :class:`PromotionResult` with the assigned ``mutation_ids`` +
        ``audit_event_id``.

    Raises:
        PermissionDeniedError: ``session`` lacks
            ``CAN_PROPOSE_MUTATION`` per ADR-0002 §am2.
        NotImplementedError: Item kind is not ``ATOM``, OR
            ``item.source_user_id is not None`` (defer to P25).
        ValueError: Empty proposal (``len(items) == 0``).

    Two-store write ordering per Phase 24 design log PB-25(a):

    1. ``admin_tx`` BEGIN IMMEDIATE on ``conn``.
    2. For each item: INSERT ``pending_mutations`` row (payload_json
       serialized via :meth:`NodeSpec.to_payload_dict`).
    3. For each item: ``pending_global_mg.graphs[role].add_node(...)``
       in-memory; node_id = ``payload_json["node_id"]`` (minted at
       step 2's INSERT post-RETURNING-id pattern via lastrowid).

       Actually node_id is minted BEFORE both stores per PB-Z9(a) —
       pending node_id IS canonical node_id, preserved through the
       lifecycle. So order is: mint UUID → store in payload_json →
       INSERT pending_mutations → add_node(node_id=...).

    4. Write ``EVT_PROMOTION_PROPOSED`` audit row.
    5. COMMIT.

    On any failure within the loop, ``admin_tx`` ROLLBACK undoes the
    SQLite side; the in-memory ``add_node`` calls are reverted via
    ``Graph.remove_node`` in a try/finally.
    """
    # ── Step 0: capability check (denial-path audit + raise) ────────
    _require_or_audit(
        conn, session, CAN_PROPOSE_MUTATION, verb="propose_for_promotion"
    )

    # ── Step 1: validate proposal shape (caller-side errors; cheap)
    if not proposal.items:
        raise ValueError(
            "PromotionProposal.items is empty; nothing to propose."
        )

    # Per PB-11(a) — source-user path defers to Phase 25.
    for item in proposal.items:
        if item.source_user_id is not None:
            raise NotImplementedError(
                f"PromotionItem.source_user_id={item.source_user_id!r} "
                f"requires Phase 25 cross-user read substrate (ADR-0008 "
                f"§am1). Phase 24 ships admin-direct ATOM only per "
                f"design log PB-11(a)."
            )
        # Per PB-3(a) — non-ATOM kinds defer.
        if item.kind != PromotionItemKind.ATOM:
            raise NotImplementedError(
                f"PromotionItemKind.{item.kind.value} dispatch deferred. "
                f"Phase 24 ships ATOM only per design log PB-3(a). "
                f"STRUCTURE → post-Core-CompositionalMetaEdge phase; "
                f"PIPELINE → post-L3 phases 33-35; SUBGRAPH → own phase."
            )
        # ATOM-specific: node must be present (already validated in
        # PromotionItem.__post_init__, but defensive check).
        if item.node is None:
            raise ValueError(
                f"PromotionItem(kind=ATOM) has node=None; should have "
                f"been caught at construction time."
            )

    # ── Step 2: mint node_ids + serialize payloads (pre-tx; cheap)
    # Per PB-Z9(a) — pending node_id IS canonical node_id; minted at
    # propose-time and preserved through release-time per-role copy.
    item_records: list[tuple[PromotionItem, str, dict[str, Any]]] = []
    for item in proposal.items:
        assert item.node is not None  # for type narrowing
        node_id = _mint_node_id()
        payload = {
            "kind": item.kind.value,
            "node_id": node_id,
            "node": item.node.to_payload_dict(),
            "source_user_id": item.source_user_id,  # None at v1
        }
        item_records.append((item, node_id, payload))

    proposed_at_iso = _utcnow_iso()
    proposer = session.user_id

    # ── Step 3: two-store write (admin_tx + in-memory) ──────────────
    # In-memory writes happen INSIDE admin_tx so a SQL exception can
    # be caught + in-memory reverted (rollback symmetry per PB-25(a)).
    #
    # Late import to break the pre-existing
    # ``mindsos_server.admin`` <-> ``mindsos_server.persistence`` <->
    # ``mindsos_admin`` import cycle (L0-24; PHASE_44_DESIGN_LOG.md §12).
    # A module-top import here is reached while ``admin.py`` is mid-init
    # on a cold ``mindsos_server`` import (paused at its persistence
    # import, before ``admin_tx`` is defined). Pattern precedent:
    # ``mindsos_core/persistence/client.py`` late bootstrap import.
    from mindsos_server.admin import admin_tx

    inserted_mutation_ids: list[int] = []
    added_to_pending: list[tuple[str, str]] = []  # (target_role, node_id)
    audit_event_id: int = -1

    try:
        with admin_tx(conn):
            # 3a. Pre-write EVT_PROMOTION_PROPOSED audit row (need
            # audit_event_id to FK into pending_mutations.audit_event_id).
            #
            # Per ADR-0114 §1 — pending_mutations.audit_event_id FKs
            # to audit.id. The audit row must exist BEFORE the FK
            # write. We write the audit row first, capture its id via
            # lastrowid, then use it in pending_mutations.
            extra: dict[str, Any] = {
                "proposer_admin_user_id": proposer,
                "mutation_ids": [],  # populated below (assigned at 3d)
                "items_count": len(proposal.items),
                "kinds": sorted({rec[0].kind.value for rec in item_records}),
                "roles_affected": sorted(
                    {rec[0].node.target_role for rec in item_records}
                ),
            }
            if proposal.reason:
                extra["reason"] = proposal.reason

            write_audit(
                conn,
                actor=proposer,
                event=EVT_PROMOTION_PROPOSED,
                target=None,
                extra=extra,
            )
            audit_event_id = int(_lastrowid(conn))

            # 3b. INSERT pending_mutations rows.
            for item, node_id, payload in item_records:
                cur = conn.execute(
                    """
                    INSERT INTO pending_mutations (
                        proposer_admin_user_id,
                        source_user_id,
                        proposed_at,
                        mutation_type,
                        payload_json,
                        audit_event_id,
                        frozen_user_local_node_id,
                        shipped_in_release
                    ) VALUES (?, ?, ?, 'PROMOTION', ?, ?, NULL, NULL)
                    """,
                    (
                        proposer,
                        item.source_user_id,  # NULL at v1
                        proposed_at_iso,
                        json.dumps(payload, sort_keys=True),
                        audit_event_id,
                    ),
                )
                inserted_mutation_ids.append(int(cur.lastrowid))

            # 3c. In-memory pending_global_mg additions per item.
            for item, node_id, payload in item_records:
                assert item.node is not None
                target_graph = _find_role_graph(
                    pending_global_mg, item.node.target_role
                )
                if target_graph is None:
                    raise AdminError(
                        f"pending_global_mg has no role-graph for "
                        f"{item.node.target_role!r}; expected eager "
                        f"bootstrap per PB-15(a) to have ensured all "
                        f"canonical roles. Run "
                        f"``mindsos_admin.bootstrap_pending_global`` "
                        f"alongside ``bootstrap_global`` at install."
                    )
                target_graph.add_node(
                    item.node.value,
                    item.node.node_type,
                    properties=dict(item.node.properties),
                    node_id=node_id,
                )
                added_to_pending.append((item.node.target_role, node_id))

                # 3c-Falkor (Phase 26a — ADR-0118 §am3). Incremental
                # MERGE into the single FalkorDB graph; idempotent on
                # rerun via (metagraph_id, graph_id, node_id) key.
                # Per Phase 25 hard_delete_user persister=None
                # precedent, `client is None` means caller wants
                # SQLite + in-memory only (Phase 24 contract); the
                # Cypher write is opt-in via passing a live Client.
                if client is not None:
                    falkor_props: dict[str, Any] = {
                        "value": item.node.value,
                        "node_type": item.node.node_type,
                    }
                    for pk, pv in item.node.properties.items():
                        falkor_props[f"prop_{pk}"] = pv
                    client.run_query(
                        _PROPOSE_MERGE_CYPHER,
                        {
                            "node_id": node_id,
                            "metagraph_id": pending_global_mg.metagraph_id,
                            "graph_id": target_graph.graph_id,
                            "props": falkor_props,
                        },
                    )

            # 3d. UPDATE audit row's extra_json with the assigned
            # mutation_ids (couldn't be known at 3a since INSERT order
            # determines them). One-shot UPDATE on the row at
            # audit_event_id.
            extra["mutation_ids"] = list(inserted_mutation_ids)
            conn.execute(
                "UPDATE audit SET extra_json = ? WHERE id = ?",
                (json.dumps(extra, sort_keys=True), audit_event_id),
            )

            # 3e. admin_tx auto-commits on __exit__.

    except Exception:
        # SQLite side rolled back by admin_tx __exit__ on exception;
        # in-memory side needs explicit revert.
        for target_role, node_id in added_to_pending:
            graph = _find_role_graph(pending_global_mg, target_role)
            if graph is not None:
                try:
                    graph.remove_node(node_id)
                except Exception:
                    # Best-effort revert per Phase 24 design log §6
                    # KeyboardInterrupt-window admission; logged but
                    # not re-raised (would mask original exception).
                    pass
        raise

    return PromotionResult(
        mutation_ids=tuple(inserted_mutation_ids),
        audit_event_id=audit_event_id,
        proposed_at=proposed_at_iso,
    )


# ─── §7 rehydrate_pending_global ────────────────────────────────────────


def rehydrate_pending_global(
    conn: sqlite3.Connection,
    pending_global_mg: Metagraph,
) -> int:
    """Rebuild in-memory pending_global from SQLite payload_json rows.

    Per Phase 24 design log PB-Z21.1 — ``pending_mutations.payload_
    json`` is the authoritative restart-rehydration source. CLI re-
    invocation (admin runs ``mindsos server release ship`` after a
    prior session) calls this to repopulate the in-memory
    pending_global Metagraph from the SQLite ledger.

    Reads rows where ``shipped_in_release IS NULL`` (natural pending
    predicate per PB-26(b)) — already-shipped mutations are NOT
    rehydrated (they live in canonical; pending is the propose
    buffer).

    Args:
        conn: SQLite connection on ``server.db``.
        pending_global_mg: In-memory :class:`Metagraph` built via
            :func:`mindsos_admin.bootstrap_pending_global`. Must have
            role-graphs already ensured (empty); rehydration adds
            nodes via ``add_node``.

    Returns:
        Number of nodes added to ``pending_global_mg``.

    Raises:
        AdminError: payload_json references a role-graph absent from
            ``pending_global_mg`` (indicates bootstrap drift).
    """
    cur = conn.execute(
        """
        SELECT mutation_id, payload_json
          FROM pending_mutations
         WHERE shipped_in_release IS NULL
         ORDER BY mutation_id
        """
    )
    added = 0
    for row in cur:
        mutation_id, payload_json = row
        payload = json.loads(payload_json)
        # v1: ATOM only per PB-3(a); other kinds raised NotImplementedError
        # at propose so they shouldn't be present in pending_mutations.
        if payload.get("kind") != PromotionItemKind.ATOM.value:
            raise AdminError(
                f"pending_mutations row {mutation_id} has kind="
                f"{payload.get('kind')!r}; only ATOM is supported at "
                f"v1 per Phase 24 design log PB-3(a). Inconsistent "
                f"pending_mutations content."
            )
        node_payload = payload["node"]
        node_spec = NodeSpec.from_payload_dict(node_payload)
        node_id = payload["node_id"]
        graph = _find_role_graph(pending_global_mg, node_spec.target_role)
        if graph is None:
            raise AdminError(
                f"pending_mutations row {mutation_id} references "
                f"role={node_spec.target_role!r} absent from "
                f"pending_global_mg; bootstrap drift."
            )
        graph.add_node(
            node_spec.value,
            node_spec.node_type,
            properties=dict(node_spec.properties),
            node_id=node_id,
        )
        added += 1
    return added


def rehydrate_canonical_global(
    conn: sqlite3.Connection,
    canonical_global_mg: Metagraph,
) -> int:
    """Rebuild in-memory canonical_global from SHIPPED pending rows.

    Symmetric with :func:`rehydrate_pending_global` per Phase 24
    design log PB-Z21.1; reads rows where ``shipped_in_release IS NOT
    NULL`` (post-ship). Phase 24's audit-gate cross-mg pass needs a
    populated canonical_global_mg to compare against; this function
    rebuilds it from the SQLite ledger at CLI invocation startup.

    Args:
        conn: SQLite connection on ``server.db``.
        canonical_global_mg: In-memory canonical-Global
            :class:`Metagraph` built via
            :func:`mindsos_admin.bootstrap_global`. Role-graphs must be
            ensured (empty); rehydration adds nodes via ``add_node``.

    Returns:
        Number of nodes added to ``canonical_global_mg``.
    """
    cur = conn.execute(
        """
        SELECT mutation_id, payload_json
          FROM pending_mutations
         WHERE shipped_in_release IS NOT NULL
         ORDER BY mutation_id
        """
    )
    added = 0
    for mutation_id, payload_json in cur:
        payload = json.loads(payload_json)
        if payload.get("kind") != PromotionItemKind.ATOM.value:
            raise AdminError(
                f"pending_mutations row {mutation_id} has kind="
                f"{payload.get('kind')!r}; only ATOM at v1."
            )
        node_payload = payload["node"]
        node_spec = NodeSpec.from_payload_dict(node_payload)
        node_id = payload["node_id"]
        graph = _find_role_graph(canonical_global_mg, node_spec.target_role)
        if graph is None:
            raise AdminError(
                f"pending_mutations row {mutation_id} references "
                f"role={node_spec.target_role!r} absent from "
                f"canonical_global_mg; bootstrap drift."
            )
        # Idempotent: if a prior rehydrate within the same session
        # already added this node_id, skip rather than raise.
        if node_id in graph.nodes:
            continue
        graph.add_node(
            node_spec.value,
            node_spec.node_type,
            properties=dict(node_spec.properties),
            node_id=node_id,
        )
        added += 1
    return added


def rehydrate_global_metagraphs(
    conn: sqlite3.Connection,
    canonical_global_mg: Metagraph,
    pending_global_mg: Metagraph,
) -> tuple[int, int]:
    """Rehydrate both canonical + pending from the SQLite ledger.

    Convenience wrapper combining :func:`rehydrate_canonical_global`
    and :func:`rehydrate_pending_global`. CLI release verbs call this
    at invocation start.

    Returns:
        ``(canonical_added, pending_added)`` — node counts added to
        each metagraph.
    """
    canonical_added = rehydrate_canonical_global(conn, canonical_global_mg)
    pending_added = rehydrate_pending_global(conn, pending_global_mg)
    return canonical_added, pending_added


# ─── §8 Helpers ─────────────────────────────────────────────────────────


def _mint_node_id() -> str:
    """Mint a fresh node_id (UUID4). Per ADR-0035 non-deterministic.

    Per PB-Z9(a) — pending node_id IS canonical node_id; preserved
    through release-time per-role copy via in-memory ``add_node`` at
    Phase 24, future Cypher MERGE-on-node_id at Phase 26.
    """
    return str(uuid.uuid4())


def _utcnow_iso() -> str:
    """Current UTC timestamp ISO-8601 with millisecond precision.

    Matches Phase 18 PB-35 + :func:`mindsos_server.audit._now_utc_iso`
    convention.
    """
    now = datetime.now(timezone.utc)
    return now.isoformat(timespec="milliseconds")


def _lastrowid(conn: sqlite3.Connection) -> int:
    """Return the SQLite ``lastrowid`` of the most recent INSERT on
    ``conn``. Helper to avoid per-callsite ``.lastrowid`` access.
    """
    cur = conn.execute("SELECT last_insert_rowid()")
    row = cur.fetchone()
    if row is None or row[0] is None:
        raise AdminError(
            "SQLite last_insert_rowid() returned NULL; expected a "
            "post-INSERT rowid."
        )
    return int(row[0])


def _find_role_graph(metagraph: Metagraph, role: str):
    """Find the :class:`mindsos_core.Graph` in ``metagraph`` with the
    given role. Returns ``None`` if not found.

    Reuses Phase 14's lookup pattern from
    :mod:`mindsos_knowledge.bootstrap`. Phase 24 doesn't expose a
    cross-package helper; inline here for module independence.
    """
    for g in metagraph.graphs.values():
        if g.role == role:
            return g
    return None
