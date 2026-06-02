---
title: Release manifest + version DB schema (v1 narrow — pending_mutations + releases only)
status: Accepted
date: 2026-05-22
layer: L0
amends: []
related: [0002, 0006, 0007, 0013, 0118, 0141, 0144]
---

# ADR-0114: Release manifest + version DB schema (v1 narrow)

**Status:** Accepted (2026-05-22 — Phase 24 ship; `mindsos_server/_schema.py` schema v3 → v4 ships the locked DDL; `mindsos_server/release.py::release_update` consumes; `mindsos_admin/promotion.py::propose_for_promotion` consumes.)

**Date:** 2026-05-22

**Related:** [ADR-0118](0118-per-user-transactional-promotion.md) (atomicity model that owns these tables); [ADR-0115](0115-release-ship-audit-gate.md) (audit gate that reads from them); [ADR-0006](0006-promotion-locking.md) (RELEASE_SHIP_LOCK guards writes); [ADR-0013](0013-audit-and-test-shim.md) (audit_event_id FK target); [PIVOT_V1_SCOPE_2026-04-26.md](../../PIVOT_V1_SCOPE_2026-04-26.md) §7.5 (data shapes — narrowed at this ADR).

## Context

ADR-0118 §"Decision" §2 prescribes a `releases` row insert and a
`pending_mutations.shipped_in_release` stamp inside `release_update`.
PIVOT §7.5 sketches the data shapes plus two more tables
(`node_versions` + `peer_deps` per §7.7) that gate on Phase 24-deferred
features (version bumping under the hood per ADR-0113 deferred; peer
deps gate on STRUCTURE / PIPELINE PromotionItemKinds also deferred).
Phase 24 ships only what the admin-direct ATOM scope needs:
`pending_mutations` + `releases`. The other two tables defer to
their consumer phases.

Phase 24 design log §6 narrows scope to admin-direct ATOM only with
SHIPPED + FAILED release lifecycle states only. This ADR is the
schema-side record of that scope.

PIVOT §7.5 sits at the parent docs/ tree as the shared scope contract;
this ADR supersedes the table shapes in §7.5 with the narrowed v1
forms.

## Decision

Two new SQLite tables in `server.db`, added via forward-only migration
from `_SCHEMA_VERSION = 3` to `_SCHEMA_VERSION = 4`. Both tables FK
to `audit.id` (Phase 21 audit table) — both stores are the same
`server.db` database, so SQLite FK enforcement applies in-process.

### 1. `pending_mutations`

```sql
CREATE TABLE pending_mutations (
    mutation_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    proposer_admin_user_id   TEXT NOT NULL,
    source_user_id           TEXT NULL,                            -- NULL at v1 (admin-direct only)
    proposed_at              TEXT NOT NULL,                        -- ISO-8601 UTC ms
    mutation_type            TEXT NOT NULL CHECK (mutation_type IN ('PROMOTION')),
    payload_json             TEXT NOT NULL,                        -- serialized PromotionItem
    audit_event_id           INTEGER NOT NULL,
    frozen_user_local_node_id TEXT NULL,                           -- NULL at v1 (no source-user path)
    shipped_in_release       INTEGER NULL,                         -- NULL while pending; set at ship
    FOREIGN KEY (proposer_admin_user_id) REFERENCES users (user_id),
    FOREIGN KEY (audit_event_id)        REFERENCES audit (id),
    FOREIGN KEY (shipped_in_release)    REFERENCES releases (release_id)
);

CREATE INDEX idx_pending_mutations_unshipped
    ON pending_mutations (shipped_in_release) WHERE shipped_in_release IS NULL;

CREATE INDEX idx_pending_mutations_by_release
    ON pending_mutations (shipped_in_release) WHERE shipped_in_release IS NOT NULL;
```

**CHECK constraint at v1:** `mutation_type IN ('PROMOTION')`. PIVOT
§7.5 lists `'PROMOTION' | 'EDGE_ADD' | 'EDGE_DEPRECATE' | ...`; only
PROMOTION ships at P24 (no direct edge ops). Phase 18 PB-28 precedent
(`actor_role` CHECK enumerates only shipped values + extends via
forward-only migration when future values land).

**`shipped_in_release IS NULL` is the natural pending predicate** —
Phase 24 design log PB-26(b) audit-gate snapshot pattern uses this
predicate as the cut-point. The partial index `idx_pending_mutations_
unshipped` makes the `SELECT ... WHERE shipped_in_release IS NULL`
fast at any pending volume.

**`source_user_id` + `frozen_user_local_node_id` are NULL at v1.**
Both are reserved for the Phase 25 source-user-Local propose path.
The columns ship at v4 because retrofitting on a populated table is
wasteful.

### 2. `releases`

```sql
CREATE TABLE releases (
    release_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_release_id         INTEGER NULL,                        -- previous SHIPPED release_id; NULL for first
    proposer_admin_user_id    TEXT NOT NULL,                       -- who invoked release_update
    approver_admin_user_ids_json TEXT NULL,                        -- NULL at v1 (no separate approve step)
    proposed_at               TEXT NOT NULL,                       -- ISO-8601 UTC ms; == shipped_at or failed_at
    shipped_at                TEXT NULL,                           -- ISO-8601 UTC ms when status = SHIPPED
    failed_at                 TEXT NULL,                           -- ISO-8601 UTC ms when status = FAILED
    manifest_json             TEXT NOT NULL,                       -- forensic + lazy-migration content
    audit_event_id            INTEGER NOT NULL,                    -- EVT_RELEASE_SHIPPED or EVT_RELEASE_FAILED
    status                    TEXT NOT NULL CHECK (status IN ('SHIPPED', 'FAILED')),
    FOREIGN KEY (parent_release_id)      REFERENCES releases (release_id),
    FOREIGN KEY (proposer_admin_user_id) REFERENCES users (user_id),
    FOREIGN KEY (audit_event_id)         REFERENCES audit (id)
);

CREATE INDEX idx_releases_status_shipped_at
    ON releases (status, shipped_at);

CREATE INDEX idx_releases_parent
    ON releases (parent_release_id);
```

**Status CHECK = `('SHIPPED', 'FAILED')`.** Phase 24 design log
PB-10(a). PIVOT §7.5 5-state lifecycle (PROPOSED / APPROVED /
SHIPPED / REJECTED / WITHDRAWN) is v2; v1 has no separate approve
step (ADR-0118 §Tradeoffs override-path-is-v2). Future v2 phases
extend the CHECK via forward-only migration.

**`parent_release_id`** is populated at SHIPPED by `SELECT MAX
(release_id) FROM releases WHERE status = 'SHIPPED'` immediately
before INSERT. FAILED rows do not become parents of subsequent
releases (no canonical state was committed by a FAILED release).

**`approver_admin_user_ids_json` NULL at v1.** Reserved for v2
quorum-approve (ADR-0118 §Tradeoffs). Column ships at v4 to avoid
retrofitting; v1 always writes NULL.

**`shipped_at` XOR `failed_at` — never both, never neither.** The
CHECK constraint doesn't enforce this (CHECK on multi-column
predicates is messy in SQLite); enforced by `release_update`'s write
logic + test (`tests/phase_24/test_releases_schema.py`).

### 3. `manifest_json` content shapes

Two shapes, distinguished by `releases.status`. Phase 24 design log
PB-22(a) (SHIPPED) + PB-28(a) (FAILED).

#### SHIPPED shape

```json
{
  "included_mutation_ids": [12, 14, 15],
  "rewrite_map": {},
  "roles_affected": ["ontology", "lexicon"],
  "audit_event_id": 482,
  "shipped_at": "2026-05-22T14:32:10.123Z"
}
```

- `included_mutation_ids`: the `pending_mutations.mutation_id` rows
  stamped `shipped_in_release = this.release_id`. Snapshot of the
  audit-gate set per PB-26(b).
- `rewrite_map`: source_local_node_id → canonical_global_node_id.
  Empty `{}` at admin-direct ATOM (no source-user drafts). Phase 25
  populates when source-user path ships.
- `roles_affected`: canonical role-graphs that received new content.
- `audit_event_id`: the `EVT_RELEASE_SHIPPED` row in audit.
- `shipped_at`: redundant with `releases.shipped_at` for forensic
  self-contained inspection.

#### FAILED shape

```json
{
  "included_mutation_ids": [],
  "rewrite_map": {},
  "roles_affected": ["ontology"],
  "failed_at_role": "lexicon",
  "error_class": "FalkorDBWriteError",
  "mutations_attempted_count": 4,
  "audit_event_id": 489,
  "shipped_at": null,
  "failed_at": "2026-05-22T14:38:55.041Z"
}
```

- `included_mutation_ids`: empty `[]` on FAILED — no pending rows
  are stamped (admin reruns to retry).
- `roles_affected`: roles where the FalkorDB-side copy **did land
  before the failure**. Per-role independence per ADR-0118 §"Decision"
  §2 + ADR-0129 §am2 means partial state is real; this list is the
  forensic record. Admin uses it to reason about retry vs manual
  canonical cleanup.
- `failed_at_role`: the role that triggered the failure.
- `error_class`: exception type name.
- `mutations_attempted_count`: the size of the audit-gate-snapshot set
  per PB-26(b) — what release_update intended to ship.

### 4. Schema migration v3 → v4

Forward-only per Phase 18-22 pattern (`mindsos_server/_schema.py`
existing migration framework):

```python
def _migrate_v3_to_v4(conn: sqlite3.Connection) -> None:
    """Add pending_mutations + releases tables at Phase 24 ship."""
    conn.executescript(_DDL_RELEASES)               # releases first (PK FK target)
    conn.executescript(_DDL_PENDING_MUTATIONS)      # pending_mutations second (FKs releases)
    conn.execute(
        "INSERT OR REPLACE INTO schema_version (key, version) VALUES ('schema_version', 4)"
    )
```

DDL ordering matters: `releases` ships first because
`pending_mutations.shipped_in_release` FKs to `releases.release_id`.

### 5. v1 deferred tables

Two tables from PIVOT §7.7 defer to future phases (they don't ship
at v4):

- **`node_versions`** — gates on ADR-0113 (mutation auto-bumps
  version under the hood; Phase 24 design log §6 defers). Ships at
  the version-bumping phase.
- **`peer_deps`** — gates on STRUCTURE / PIPELINE PromotionItemKinds
  (Phase 24 design log §6 defers). Ships at the first STRUCTURE
  phase or post-L3 PIPELINE phase.

When those tables ship, the schema bumps v4 → v5 → … via forward-
only migration. No v1 columns ship for those tables; no retrofit
debt.

## Rationale

- **Two tables only at v1.** Phase 24 admin-direct ATOM scope needs
  pending tracking + release manifest; doesn't need version bumping
  or peer-dep tracking. Shipping unused tables ships dead schema.
- **`server.db` not separate `version_db/`.** CLAUDE.md mentioned a
  potential `version_db/` directory; the design discussion settled
  on `server.db` because `pending_mutations.audit_event_id` FKs to
  `audit.id` (Phase 21 table in server.db). Cross-database FKs don't
  work in SQLite. One database, one schema_version, one migration
  path.
- **AUTOINCREMENT on PKs.** SQLite's default ROWID can be reused
  after deletes; AUTOINCREMENT guarantees monotonic non-reused IDs.
  Release IDs are referenced by `pending_mutations.shipped_in_release`
  + `releases.parent_release_id` + `manifest_json.included_mutation_
  ids`; reuse would create cross-reference hazards.
- **Partial indexes on `shipped_in_release`.** Pending volume can
  grow (admin batches multiple proposes); the unshipped predicate is
  the hot path (audit-gate snapshot + release-update set selection).
  Partial index on `WHERE shipped_in_release IS NULL` keeps the
  pending-side scan O(pending), not O(history).
- **CHECK constraints enforce v1 scope at the schema level.**
  `mutation_type IN ('PROMOTION')` + `status IN ('SHIPPED', 'FAILED')`
  catch implementation drift in tests + at first runtime mis-write.
  Forward-only ALTER TABLE to extend the enum is the Phase 18-22
  pattern.
- **`manifest_json` is the lazy-migration contract anchor.** Phase
  25 lazy migration consumes `included_mutation_ids` + `rewrite_map`
  to determine per-user rewrite work. Shipping the full shape at P24
  (with empty `rewrite_map` at admin-direct) sets the contract
  immutably; P25 populates `rewrite_map` without schema or shape
  change.

## Consequences

**Good:**

- Two tables, two CHECK constraints, two partial indexes. Minimal
  surface; tested cleanly at P24.
- `manifest_json` shapes are immutable contracts; Phase 25 plugs in
  rewrite_map population without ALTER.
- `shipped_in_release IS NULL` is a natural pending predicate that
  doubles as the PB-26(b) cut-point; one mechanism, two consumers.
- FAILED-row forensic detail enables admin reasoning about partial-
  ship recovery without inspecting FalkorDB directly.

**Tradeoffs:**

- `manifest_json` is denormalized — `included_mutation_ids` could be
  reconstructed via `SELECT mutation_id FROM pending_mutations WHERE
  shipped_in_release = ?`; `roles_affected` could be reconstructed
  via JOIN on payload_json. Storing in JSON loses query
  composability for those fields. Worth it for self-contained audit
  reads (one row tells the whole release story).
- `releases.proposer_admin_user_id` is misleading at v1: no separate
  propose-then-approve step; the field is "who invoked release_update."
  Rename considered + rejected: column rename is a breaking change
  per Phase 22 PB-17 cap-name-rename pattern; v2 quorum-approve adds
  `approver_admin_user_ids_json` semantic.
- `approver_admin_user_ids_json` ships as a NULL column with no v1
  use. Wastes ~5 bytes per row. v1 value: avoiding a v5 ALTER TABLE
  to add it.

**Coordinated changes:**

- `mindsos_server/_schema.py` — `_SCHEMA_VERSION = 4`; `_DDL_PENDING_
  MUTATIONS` + `_DDL_RELEASES` + `_migrate_v3_to_v4` step.
- `mindsos_server/release.py` — `release_update` writes both tables
  inside `admin_tx`.
- `mindsos_admin/promotion.py` — `propose_for_promotion` writes
  `pending_mutations` row inside `admin_tx`.
- `tests/phase_24/test_pending_mutations_schema.py` + `test_releases_
  schema.py` — assert columns + indexes + CHECK constraints + FK
  enforcement.

## Alternatives considered

1. **Ship all 4 PIVOT §7.5 + §7.7 tables at v4.** Rejected — `node_
   versions` + `peer_deps` have no v1 consumer; ships dead schema
   that drifts from actual usage as ADR-0113 + STRUCTURE phase
   designs evolve.
2. **Separate `version_db/` SQLite database for release tables.**
   Rejected — cross-database FK doesn't work in SQLite;
   `pending_mutations.audit_event_id → audit.id` requires same-db
   placement. One database is also one migration path, simpler ops.
3. **Use `mutation_type TEXT` without CHECK constraint.** Rejected —
   CHECK catches implementation drift; extending via forward-only
   ALTER is the established Phase 18-22 pattern.
4. **Normalize `manifest_json` into a `release_mutations` join
   table.** Rejected at v1 — admin-direct ATOM scope has small
   release sizes; JSON denormalization wins on read simplicity. v2
   may revisit at scale.
5. **Store `manifest_json` content in a binary format (msgpack /
   cbor) for size.** Rejected — JSON is grep-able + human-readable
   for forensic inspection; release sizes are admin-batch-bounded,
   so size is not a concern.

## Implementation references

- `mindsos_server/_schema.py` — DDL + migration v3 → v4.
- `mindsos_server/release.py::release_update` — both-table writes
  inside admin_tx; manifest_json shaping (SHIPPED + FAILED branches).
- `mindsos_admin/promotion.py::propose_for_promotion` —
  pending_mutations row write inside admin_tx (Phase 24 design log
  PB-25(a) ordering: SQLite first, FalkorDB inside admin_tx body).
- `tests/phase_24/test_pending_mutations_schema.py` — column +
  index + CHECK + FK assertions.
- `tests/phase_24/test_releases_schema.py` — same for releases.
- `tests/phase_24/test_manifest_json_shipped_shape.py` — SHIPPED
  shape lock.
- `tests/phase_24/test_manifest_json_failed_shape.py` — FAILED
  shape lock + partial-failure forensic content.

ADR moves Proposed → Accepted at Phase 24 ship (this row).

## Revisions

### amendment-1 (Phase 24 ship — 2026-05-22) — Round 0 PB-Z7 + PB-Z8 + PB-Z15 + PB-Z16 + PB-Z20: rerun-recovery substrate locks

**Trigger:** Phase 24 design log Round 0 PB-Z1(b) accepted "MERGE-on-id
+ audit-gate suppression on rerun." PB-Z7/Z8/Z15/Z16/Z20 follow-on
locks pin the implementation surface this ADR's tables consume.

This amendment records five clauses that tighten the §3 manifest_json
shape + the §"Coordinated changes" `release_update` write semantics.

**1. FAILED `manifest_json` shape extended (PB-Z7(a)):**

The FAILED shape per §3 gains `failed_release_canonical_node_ids`:

```json
{
  "included_mutation_ids": [],
  "rewrite_map": {},
  "roles_affected": ["ontology"],
  "failed_at_role": "lexicon",
  "error_class": "FalkorDBWriteError",
  "mutations_attempted_count": 4,
  "audit_event_id": 489,
  "shipped_at": null,
  "failed_at": "2026-05-22T14:38:55.041Z",
  "failed_release_canonical_node_ids": {
    "ontology": ["c1", "c2"]
  }
}
```

`failed_release_canonical_node_ids: Mapping[role_name, list[canonical_
node_id]]` records the node_ids that landed in canonical_global_<role>
**before the failure** for each role. Populated from `release_update`'s
Python-local tracking list (PB-Z3(a)) per-role inside the copy loop;
written into manifest_json by the second admin_tx (FAILED-row writer).

`roles_affected` (existing) and `failed_release_canonical_node_ids`
(this amendment) are complementary: `roles_affected` is the role-name
set; `failed_release_canonical_node_ids` is per-role node-id detail
for rerun-suppression consumption.

**2. Rerun suppression-set query (PB-Z15(a)):**

`release_update` on entry queries:

```sql
SELECT manifest_json FROM releases
 WHERE status = 'FAILED'
   AND release_id > COALESCE(
     (SELECT MAX(release_id) FROM releases WHERE status = 'SHIPPED'),
     0
   );
```

The suppression set is the union of `failed_release_canonical_node_ids`
values across the returned rows (grouped by role). The query's
watermark — "FAILED rows newer than the last SHIPPED" — naturally
retires older FAILEDs' contribution once a successful SHIP advances
the watermark. A clean system (no FAILED rows) returns an empty
suppression set.

Cost: one SELECT per `release_update` invocation; admin-rare frequency.

**3. After-all-roles clear, node-id-scoped DELETE (PB-Z8(a) + PB-Z20(a)):**

On the SHIPPED happy path, pending FalkorDB nodes for the snapshot set
are cleared via Cypher DELETE **inside the same admin_tx**, **after
all per-role copies succeed**, **before the `INSERT releases SHIPPED`
+ `UPDATE pending_mutations stamps` writes**. The DELETE template is
node-id-scoped (NOT graph-wide):

```cypher
MATCH (n)
 WHERE n.node_id IN $snapshot_node_ids
DETACH DELETE n
```

Node-ids are extracted from `pending_mutations.payload_json` for the
snapshot set, grouped by `target_role`. One DELETE per role-graph.

Rationale: graph-wide `MATCH (n) DETACH DELETE n` would delete nodes
written by a concurrent `propose_for_promotion` between snapshot-
SELECT and the DELETE — silently breaking PB-26(b)'s lock-free propose
guarantee. Node-id-scoped preserves the lock-free propose contract.

FAILED path does NOT clear: partial-FalkorDB-state stays for rerun-
recovery; the suppression set from PB-Z15(a) handles the audit-gate
cross-mg findings on rerun.

**4. `error_class` enum closure (PB-Z16(a)):**

The FAILED manifest_json `error_class` field is a closed enum at v1:

```python
ErrorClass = Literal[
    "blocking_similarity_findings",   # audit gate found ≥1 blocking finding (PB-20(c))
    "empty_comparison",               # EmptyComparisonError propagated from compute_similarity (ADR-0144 §am2 default)
    "FalkorDBWriteError",             # per-role copy raised during pending → canonical MERGE
]
```

`EmptyComparisonError` propagates per ADR-0144 §am2 default ("v1
default is to propagate") — `release_update` catches at the outer
boundary, writes FAILED with `error_class="empty_comparison"`,
re-raises as `BlockingFindingError` to admin caller (so CLI exit
code mapping treats it as a strict-default failure path identical to
blocking findings).

Adding new error_class values to the enum requires an ADR §amendment.

**5. SHIPPED `manifest_json.included_mutation_ids` ordering (PB-Z6 + ADR-
0056 supersession documentary):**

Per ADR-0056 supersession at Phase 24 ship, `included_mutation_ids`
is **append-order from `pending_mutations.mutation_id` AUTOINCREMENT**
(SQLite INSERT order), NOT propose-time input order. This is the
natural snapshot-set order from PB-26(b)'s `SELECT mutation_id …
WHERE shipped_in_release IS NULL ORDER BY mutation_id`. ADR-0056's
input-order semantic doesn't apply to the multi-propose batch model.

**Coordinated changes at this amendment:**

* `mindsos_server/release.py::release_update` — implements the
  suppression-set query (clause 2), node-id-scoped DELETE (clause 3),
  error_class enum (clause 4).
* `mindsos_server/release.py::_build_failed_manifest_json` — populates
  `failed_release_canonical_node_ids` (clause 1).
* `tests/phase_24/test_manifest_json_failed_shape.py` — extends
  assertion to include `failed_release_canonical_node_ids`.
* `tests/phase_24/test_release_update_concurrent_propose_survives_clear.py`
  (NEW per Round 6) — asserts concurrent propose's new node survives
  node-id-scoped DELETE.
* `tests/phase_24/test_release_update_empty_comparison_propagates.py`
  (NEW per Round 6) — asserts EmptyComparisonError → FAILED row with
  `error_class="empty_comparison"`.
* `tests/phase_24/test_release_update_rerun_after_failed.py` (NEW per
  Round 6) — asserts rerun after FAILED uses suppression set + ships
  successfully via MERGE-on-id idempotency.

**Phase 24 design log:** `halvim_mindsos/confirmation_docs/PHASE_24_
DESIGN_LOG.md` §1 Round 0 PB-Z1/Z3/Z7/Z8/Z15/Z16/Z20 picks + §4 ADR
delta (13 touches).

### amendment-4 (Phase 25 ship — 2026-05-23) — Phase 24 latent FK gap closure (`pending_mutations.proposer_admin_user_id` + `releases.proposer_admin_user_id` NO ACTION semantics)

**Trigger:** Phase 25 Round 3 Probe A (re-litigation cascade) discovered a latent Phase 24 schema bug: both `pending_mutations.proposer_admin_user_id` and `releases.proposer_admin_user_id` are declared `REFERENCES users (user_id)` with NO `ON DELETE` clause → SQLite default `NO ACTION` (effectively RESTRICT). A `hard_delete_user` of an admin with promotion history would bubble a raw `sqlite3.IntegrityError` — uncatchable by `_admin_exit_for`, surfaced to the operator as an unhandled traceback.

The gap was not enumerated in Phase 24's design log §3 forward dependencies. It was discovered during Phase 25 design's UNION-pre-check audit (PB-30); the closure ships at Phase 25.

**Amended behavior:**

* **`hard_delete_user` gains a UNION ALL pre-check inside `admin_tx`** that scans `pending_mutations` + `releases` for rows referencing the target's `user_id`. If any rows exist, raises `UserHasPromotionHistoryError(target_user_id, pending_ids, release_ids)` BEFORE any DELETE is attempted. The check sits between the sole-admin invariant assertion and the session-id capture; the rollback semantics are admin_tx-clean (no partial state mutation).

* **`UserHasPromotionHistoryError` ships at `mindsos_server.errors`** with three attributes: `user_id: str`, `pending_ids: list[int]` (rows from `pending_mutations.mutation_id`), `release_ids: list[int]` (rows from `releases.release_id`). Constructor message includes counts but not the IDs themselves (avoids brittle text-assertion patterns).

* **CLI exit code 10** (NEW) maps `UserHasPromotionHistoryError`. The slot is the first new exit code since Phase 24's 7 (`EmptyReleaseError`) + 8 (`BlockingFindingError`). Slot 9 is reserved for `FlushFailedError` per Phase 25 PB-37 deferral (the cap-of-9 marker keeps the roster contiguous; no v1 code path raises `FlushFailedError` to the CLI).

* **No schema change.** The FK definitions remain `NO ACTION`. The gap is closed at the application layer via the pre-check, not via a CASCADE / SET NULL migration — audit-bearing rows MUST NOT silently disappear when a user is removed (ADR-0013 §Consequences "audit MUST outlive subjects"; the `proposer_admin_user_id` is the only handle the audit reader has to those rows). The recourse for admins with promotion history is the soft-retire pair: `admin-demote-user` + `admin-disable-user`.

**Coordinated changes at this amendment:**

* `mindsos_server/errors.py` — `UserHasPromotionHistoryError` (NEW).
* `mindsos_server/admin.py::hard_delete_user` — UNION ALL pre-check inside admin_tx; `UserHasPromotionHistoryError` raised before SELECT/DELETE.
* `mindsos_cli/commands/server.py::_admin_exit_for` — adds `UserHasPromotionHistoryError → 10` mapping.
* `mindsos_cli/commands/server.py::admin_hard_delete_user_cmd` — adds `UserHasPromotionHistoryError` to the except tuple.
* `tests/phase_25/test_hard_delete_user_pending_blocks.py` — seeds `pending_mutations` row, asserts UserHasPromotionHistoryError + user row survives the rollback.
* `tests/phase_25/test_hard_delete_user_releases_blocks.py` — seeds `releases` row, parallel assertion + clean-admin sanity case.

**Out-of-scope:** `ON DELETE` schema migration (SET NULL or CASCADE alternatives) — rejected per the audit-outlives-subjects invariant. WITHDRAWN / REJECTED release lifecycle states + admin reject-pending verb defer to the v2 quorum-approve phase.

**Phase 24 retroactive note:** This closure is the seventh Phase 24 carry-forward NOT enumerated in Phase 24's design log §3 — discovered during Phase 25 PB-30 probe.

**Phase 25 design log:** `halvim_mindsos/confirmation_docs/PHASE_25_DESIGN_LOG.md` §1 Round 3 PB-30 (UNION pre-check + UserHasPromotionHistoryError) + Round 3 Probe A (FK definition probe) + §4 ADR delta.
