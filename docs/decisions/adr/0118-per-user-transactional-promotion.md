---
title: Per-user transactional promotion + release-boundary atomicity
status: Accepted
date: 2026-04-26
layer: Server
supersedes: [0007]
---

# ADR-0118: Per-user transactional promotion + release-boundary atomicity

**Status:** Accepted (2026-05-22 — Phase 24 ship; admin-direct ATOM scope only at v1 per §amendment-1; source-user-Local propose path + lazy migration deferred to Phase 25.)

**Date:** 2026-04-26 (proposed), 2026-05-22 (accepted)

**Supersedes:** [ADR-0007](0007-metagraph-snapshot-rollback.md) (in full).
**Related:** [ADR-0006](0006-promotion-locking.md) (amended; see §"Consequences"),
[ADR-0027](0027-metagraph-snapshot-restore-in-place.md) (retained, narrowed).
**Companion docs:** `PIVOT_V1_SCOPE_2026-04-26.md` §7
(implementation specs); `HANDOFF_SERVER_PIVOT_2026-04-26.md`;
the release-model design notes.

## Context

The shipped promotion model (ADR-0006 + ADR-0007) treats promotion as a single
logical operation that mutates the Global metagraph and one or more authors' Local
metagraphs together, with `GLOBAL_PROMOTE_LOCK` serializing across users and
`MetagraphSnapshot` providing in-memory rollback if any per-Local flush fails.

The 2026-04-25 architectural review (`docs/decisions/adr/REVIEW-2026-04-25.md`)
identified three load-bearing problems with this model:

1. **Phantom-promotion bug.** During a multi-author promotion, if Alice's flush
   succeeds and Bob's fails, Alice's FalkorDB-side Local is ahead of the
   rolled-back in-memory state. A server crash before reconciliation hydrates a
   Local with `ref:global_*` pointers to Global nodes that were rolled back. The
   "best-effort logging" rollback story is data corruption with a paper trail.
2. **`GLOBAL_PROMOTE_LOCK` is a known scale wall.** Held on every promotion, it
   serializes per-user authoring across the entire user base. Sharding by
   role-graph was free but not chosen.
3. **The "real-time-shared Global" framing forces eager cross-user consistency**
   that doesn't fit the use case. Users would prefer predictable releases over
   real-time visibility into other users' edits.

The 2026-04-26 multi-session design conversation produced a model pivot to
admin-curated Globals shipped via discrete admin-triggered releases, with
per-user transactional promotion into a `pending_global` buffer and lazy
per-user migration after release ship. The full v1 scope contract is in
`docs/PIVOT_V1_SCOPE_2026-04-26.md`. This ADR locks the **promotion atomicity
model** that the pivot introduces.

## Decision

Replace the cross-user atomic promotion model with two **independent** atomicity
boundaries, both narrowly scoped.

### 1. Per-user transactional `propose_for_promotion` (admin-initiated)

A new admin-only API replaces the user-callable `kl.promote()`:

```python
kl.propose_for_promotion(
    admin_session: SessionProtocol,  # requires CAN_PROPOSE_MUTATION
    proposal: PromotionProposal,     # see PIVOT §7.1
) -> PromotionResult
```

The full `PromotionProposal` shape, the `CAN_PROPOSE_MUTATION` capability, the
`PromotionItemKind` registry, and the from-user-Local vs admin-direct paths are
specified in **PIVOT_V1_SCOPE_2026-04-26.md §7.1**. This ADR does not duplicate
that spec.

The atomicity boundary of a single `propose_for_promotion` call is one user's
Local plus one set of pending-Global writes:

- If `proposal.items[*].source_user_id` is set, the source user's Local node(s)
  are **frozen** (uneditable, still readable by the source user; audit event
  `DRAFT_FROZEN`).
- The pre-ship audit gate runs (see ADR-0115 [Proposed]).
- On approval, the proposal items' content is **copied** into the appropriate
  `mindsos_pending_global_<role>` FalkorDB graph(s) (PIVOT §7.2). The source
  user's frozen draft stays in their Local as their record.
- On rejection or admin withdrawal, the source user's drafts are **unfrozen**
  (audit event `DRAFT_UNFROZEN`); no pending-Global state is changed.

The whole call is one SQLite transaction (over `pending_mutations` and audit
event rows) plus a bounded set of FalkorDB writes to one user's Local and one
pending graph. No cross-user state is mutated; no `GLOBAL_PROMOTE_LOCK` is
held.

### 2. Release-boundary atomic `release_update` (admin command)

A new admin command ships pending → canonical:

```python
mindsos_server.release_update(
    admin_session: SessionProtocol,  # requires CAN_APPROVE_RELEASE (see ADR-0115)
) -> ReleaseResult
```

The atomicity boundary is the canonical Global at FalkorDB graph level plus the
`releases` row in SQLite:

- `RELEASE_SHIP_LOCK` (renamed from `GLOBAL_PROMOTE_LOCK`) is acquired.
- Release-level audit gate runs.
- For each role with pending content: the release atomically copies
  `mindsos_pending_global_<role>` → `mindsos_global_<role>`, then clears
  pending. (Backed by FalkorDB's per-graph atomicity guarantee.)
- A `releases` row is inserted (PIVOT §7.5) with `shipped_at` and a
  `manifest_json` snapshot of the included mutations.
- `pending_mutations` rows are stamped `shipped_in_release = N`.
- `RELEASE_SHIP_LOCK` is released.

If a FalkorDB write fails partway through the per-role copy: `MetagraphSnapshot`
of the affected canonical Global graph is taken **before** the copy and used to
restore canonical (ADR-0027 retained for this narrow purpose). Pending stays
intact for retry. No cross-user state needs rollback because no user state was
touched.

### 3. Per-user migration runs lazily, independently

`release_update` does **not** synchronously walk every user's Local. Each user's
session-start path checks `last_synced_release_id < current_release_id` and
applies the rewrite map of every release between (PIVOT §7.3). For a user whose
draft was promoted: their frozen draft is deleted from their Local and refs are
rewritten to canonical id (PIVOT §7.4). Migration is idempotent and atomic
**per user**.

If a user's migration fails, only that user is affected — they retain
pre-release sync state until next attempt. No multi-Local rollback is needed.

## Rationale

Three independent atomicity scopes (propose, release-ship, migrate) replace
the original one shared scope (cross-user promote-with-rollback). Each is
small, transactional within its own store, and decoupled from the others.

- **Per-user propose** is bounded in size (one user's Local + the proposal
  items) and runs without holding any global lock.
- **Release-ship** is admin-rare and FalkorDB-graph-atomic per role; its lock
  no longer serializes the per-promotion path.
- **Per-user migrate** runs at user pace, not admin pace; failures contain to
  one user.

The phantom-promotion bug from the original model is structurally impossible:
canonical Global is never written until release-ship, and release-ship doesn't
touch user Locals.

## Consequences

**Good:**

- The phantom-promotion bug is structurally gone.
- Per-promotion path no longer holds `GLOBAL_PROMOTE_LOCK`. Per-user
  promotions parallelize across users.
- Scale wall narrows from "every promotion" to "release ship" — admin-triggered,
  rare. The original critique of the lock is moot at that frequency.
- Multi-Local rollback complexity is gone. There is no cross-user rollback path.
- Audit trail is richer: `DRAFT_FROZEN`, `DRAFT_UNFROZEN`, `PROMOTION_PROPOSED`,
  `PROMOTION_APPROVED`, `PROMOTION_REJECTED`, `RELEASE_SHIPPED`,
  `MIGRATION_APPLIED`, `MIGRATION_FAILED` (full enum in PIVOT §7.6).
- The model survives server crashes between any two atomicity boundaries
  cleanly — at worst, a release sits in pending until next ship; a user sits
  on a stale `last_synced_release_id` until next session.

**Tradeoffs:**

- Adds the version DB (SQLite, in `mindsos_server/version_db/`) as a
  load-bearing storage system alongside FalkorDB. Schema is in PIVOT §7.5 +
  §7.7.
- Adds `mindsos_pending_global_<role>` graphs to FalkorDB — roughly one per
  role-graph (~10 extra at v1 scope). Manageable; isolated from canonical.
- Lazy migration introduces a per-session check on the read path. Cost is a
  single SQLite SELECT against `releases.release_id` vs the user's
  `last_synced_release_id`; a new code path but cheap.
- The `kl.promote()` surface is renamed/replaced by `kl.propose_for_promotion()`.
  Old `kl.promote()` keeps current behavior with `DeprecationWarning` during the
  v1 transition; removed in v2 (PIVOT §6.1).
- Admin gains a new operation (`release_update()`); v1 has no override path,
  so a buggy release ships only if quorum-approved (`CAN_APPROVE_RELEASE`,
  see ADR-0115). Override path is v2 (PIVOT roadmap).

**Coordinated changes to other ADRs:**

- **ADR-0006** is amended in place: per-user mutex retained as-is;
  `GLOBAL_PROMOTE_LOCK` renamed to `RELEASE_SHIP_LOCK` and held only inside
  `release_update`. The original ordering rationale (lex-order across users to
  avoid deadlock) is preserved for the per-user mutex; release-ship holds only
  the global lock and never multiple per-user mutexes simultaneously, so
  deadlock concerns narrow.
- **ADR-0009** is superseded by ADR-0115 (Proposed) — the freshness-id
  mechanism is dropped; similarity becomes part of the audit gate.
- **ADR-0027** (Metagraph snapshot restore in place) is retained but its
  use-site narrows to canonical-Global rollback during `release_update` only.
  The developer guide (`docs/dev/internals/server.md`) must reflect the
  narrowed scope.
- **ADR-0024** (Capacity layer; ADR-024 in the L3 numbering — pre-renumber
  alias `capacity-ADR-024`) is superseded by the unified release-model design;
  L3 promotion follows this ADR's pattern via the same code path
  (PIVOT §6.B.5).

## Alternatives considered

1. **Keep the shipped model, fix the phantom-promotion bug with a write-ahead
   log.** Rejected. The WAL is bigger infrastructure than the pivot, and the
   cross-user atomicity premise still doesn't fit the use case (users would
   prefer predictable releases over real-time visibility into others' edits).
2. **Real-time-shared Globals with eager cross-user migration.** Rejected.
   Keeps the `GLOBAL_PROMOTE_LOCK` scale wall and the multi-Local rollback
   complexity. Doesn't address the framing problem.
3. **Continuous releases — every approved promotion ships immediately, no
   pending buffer.** Rejected. Admin loses the curation step. Single-mutation
   reviews scale poorly; release-level batch review is the use case.
4. **Synchronous per-user migration at `release_update`.** Rejected. Blocks
   the admin command linearly with user count. Hostile to large user bases
   and to offline users. PIVOT §7.3 selected lazy migration.
5. **Per-user transactional promotion with stamp-not-delete (current
   `kl.promote()` behavior).** Rejected by `HANDOFF_L2_DESIGN_CONTINUATION.md`
   §5.6 and reaffirmed by the 2026-04-26 design. Stamp-not-delete leaves Local
   metagraphs growing monotonically with promotion count and forces every
   reverse-traversal to scan every Local. Move semantics (delete + redirect)
   is structurally cleaner.
6. **Two-store transaction across SQLite + FalkorDB.** Rejected. There is no
   such transaction primitive that crosses both stores. The decision splits
   the atomicity boundaries instead, with each store atomic-within-itself.
   Coordination across stores is bounded to the release-ship operation, which
   is admin-rare and protected by `RELEASE_SHIP_LOCK` plus `MetagraphSnapshot`.

## Implementation references

The implementation surface for this ADR is enumerated in **PIVOT_V1_SCOPE_2026-04-26.md
§6.A** (code change summary by category) and **§7** (implementation specs).
This ADR governs the atomicity model; PIVOT §7 governs the data shapes;
the audit gate is governed by ADR-0115 [Proposed]; the release manifest +
version DB schema is governed by ADR-0114 [Proposed].

ADR moves from Proposed to Accepted when the corresponding code lands and at
least one user-facing document (handoff, architecture doc, or usage guide)
reflects the decision (per `docs/decisions/about.md`).

## Revisions

### amendment-1 (Phase 24 ship — 2026-05-22) — surface relocated to mindsos_admin; v1 narrow scope; lazy migration + source-user defer to P25

**Status flip:** Proposed → Accepted at Phase 24 ship. `release_update`
+ admin-direct ATOM `propose_for_promotion` + RELEASE_SHIP_LOCK + audit
gate + release manifest ship at P24; the architectural commitments of
§Decision are honoured at this code ship. Banner-on-banner promises
from ADR-0007's supersession-in-progress also close at this ship
(ADR-0007 flips Superseded).

This amendment records the documentary corrections + scope narrowings
the Phase 24 design rounds locked.

**§Decision §1 surface location correction:** §1 names
`kl.propose_for_promotion(admin_session, proposal)` on
`KnowledgeLayer`. The canonical surface at Phase 24 ship is
**`mindsos_admin.propose_for_promotion(admin_session, proposal)`** —
a top-level function in `mindsos_admin/promotion.py`, NOT a method on
`KnowledgeLayer`. Rationale: ADR-0140 §am1 relocated admin-owned
surfaces to `mindsos_admin/`; ADR-0144 §am1 followed for similarity;
ADR-0138 keeps KL with no write API (Phase 14 PB-6 honoured by
absence); the same logic applies to propose. ADR-0141 §am1 (Phase 24
ship) records the parallel correction (it had drifted to
`mindsos_server.propose_for_promotion`).

**§Decision §1 v1 scope narrow — admin-direct ATOM only:**

* `PromotionItem.source_user_id is not None` (admin-on-behalf-of-user
  path) raises `NotImplementedError` at Phase 24. The path gates on
  cross-user read substrate (ADR-0008 §am1 Phase 25). Phase 25 ships
  the source-user path alongside `MindsOSServer._installed_locals` +
  `LocalPersister.load` + `KL.install_local_metagraph`.
* `PromotionItemKind` enum ships with all four values (ATOM /
  STRUCTURE / SUBGRAPH / PIPELINE) for forward-shape contract; only
  ATOM has a validator at Phase 24. STRUCTURE / SUBGRAPH / PIPELINE
  dispatch raises `NotImplementedError`. Substrate gates: STRUCTURE
  needs `CompositionalMetaEdge` (Phase 05a Dropped); PIPELINE needs
  L3 ship (Phases 33-35 unshipped); SUBGRAPH needs a subgraph
  extractor (no halvim precedent).
* `register_promotion_kind()` extensibility registry (PIVOT §7.1)
  deferred — hardcoded ATOM dispatch at Phase 24; registry retrofits
  at first multi-kind phase. PIVOT §7.1 amends documentary.
* Audit-event slate at v1 ships **4 events** (not PIVOT §7.6's 8):
  `EVT_PROMOTION_PROPOSED` + `EVT_PROMOTION_REJECTED` +
  `EVT_RELEASE_SHIPPED` + `EVT_RELEASE_FAILED`. The 4 deferred
  events (`EVT_DRAFT_FROZEN` + `EVT_DRAFT_UNFROZEN` +
  `EVT_MIGRATION_APPLIED` + `EVT_MIGRATION_FAILED`) gate on source-
  user-Local path + lazy migration — both Phase 25.

**§Decision §3 lazy migration deferred to Phase 25:** Lazy per-user
migration code path requires `MindsOSServer.start_session(user_id)`
session-start hook + `LocalPersister.load` + per-layer
`apply_rewrite_map` handlers — all Phase 25 substrates (ADR-0008
§am1 + ADR-0011 §am1 + ADR-0042 §am1). Phase 24 ships the data
contract (`releases.manifest_json` shape per ADR-0114 §3) that Phase
25 consumes; the code path itself is Phase 25.

The Phase 24 design log §6 records that lazy migration's first-
consumer phase shift from "Phase 24" (§Decision §3 implied) to
"Phase 25" is honoured-by-absence — Phase 14 PB-6 precedent for
defining behaviour by its absence rather than stubbing dead code.

**§Decision §2 release-ship FalkorDB-side semantics correction:**
§"Decision" §2 says "If a FalkorDB write fails partway through the
per-role copy: `MetagraphSnapshot` of the affected canonical Global
graph is taken **before** the copy and used to restore canonical."
The Phase 24 design log PB-1(b) + PB-7(a) probe demonstrated this is
**incorrect** at the FalkorDB level: per-graph atomicity is per-
graph, not per-loop; the in-memory `MetagraphSnapshot` doesn't roll
back FalkorDB-side committed per-role copies.

The corrected v1 semantics (per ADR-0129 §am2): per-role
independence. Each role's pending → canonical FalkorDB copy is
independent; partial completion stays in canonical; admin reruns
`release_update` against the unshipped subset (rerun is idempotent
because pending_global content is unchanged). `MetagraphSnapshot` is
NOT used in `release_update` — the in-memory mirror per ADR-0125
lazy hydration re-hydrates on demand from whatever FalkorDB committed.

The FAILED `releases` row + `manifest_json.roles_shipped_before_
failure` (ADR-0114 §3 FAILED shape) provides the forensic detail
admin needs to reason about retry vs manual canonical cleanup.

**§"Tradeoffs" ADR-0007 / ADR-0009 supersessions:** Both close at
Phase 24 ship per their respective banner promises. ADR-0007
status: Accepted (with supersession-in-progress banner) → Superseded.
ADR-0009 status: Superseded by ADR-0115 (drafted at Phase 24
alongside this ship per §Implementation references). The
"`kl.promote()` keeps current behavior with `DeprecationWarning`
during the v1 transition" clause is **vacuous in halvim**: KL never
ported `promote()` per Phase 14 PB-6 + ADR-0138 honoured by absence;
the migration window has nothing to migrate from. Documentary debt
closed by this amendment.

**§"Coordinated changes to other ADRs" — ADR-0024 supersession
unchanged:** §Decision §"Coordinated changes" §ADR-0024 reference
holds. ADR-0024 supersession by unified release-model design lands
when L3 ships (Phases 33-35).

**§Implementation references — Phase 24 file layout:**

* `mindsos_admin/promotion.py` (NEW at Phase 24) — `propose_for_
  promotion(admin_session, proposal) -> PromotionResult`; admin-
  direct ATOM dispatch; source-user path raises NotImplementedError.
* `mindsos_admin/audit_gate.py` (NEW at Phase 24) — release-ship
  audit gate per ADR-0115; two-pass `compute_similarity` per Phase
  24 design log PB-24.
* `mindsos_server/release.py` (NEW at Phase 24) — `release_update
  (admin_session) -> ReleaseResult`; `threading.RLock` outer +
  `admin_tx` inner; audit-gate snapshot set per PB-26.
* `mindsos_server/locks.py` (NEW at Phase 24) — `RELEASE_SHIP_LOCK
  = threading.RLock()` per ADR-0006 §am1.
* `mindsos_server/_schema.py` (MODIFIED) — schema v3 → v4 per ADR-
  0114.

**Phase 24 design log:** `halvim_mindsos/confirmation_docs/PHASE_24_
DESIGN_LOG.md` §1 rounds 1-5 picks PB-1 through PB-28; §2 final
locks (28-pick consolidation); §4 ADR delta. The 11-touch ADR delta
at Phase 24 ship absorbs this amendment, ADR-0141 §am1, ADR-0144
§am2, ADR-0129 §am2, ADR-0002 §am2, ADR-0006 §am1, ADR-0007 Status
flip, and three new drafts (ADR-0114, ADR-0115, ADR-0120).

### amendment-2 (Phase 24 ship — 2026-05-22) — Round 0 PB-Z9 + PB-Z13: MERGE-on-id Cypher template + incremental propose-time write

**Trigger:** Phase 24 design log Round 0 PB-Z9(a) + PB-Z13(a). The
§"Decision" §2 release-ship semantics correction in §amendment-1
locked per-role independence + admin rerun on partial-ship. PB-Z9
+ PB-Z13 pin the Cypher template that makes rerun structurally
idempotent at the FalkorDB level.

**§"Decision" §1 propose-time write semantics (PB-Z13(a)):**

`mindsos_admin.propose_for_promotion` writes the pending-side FalkorDB
node via **incremental Cypher MERGE-on-node_id**, NOT a full
`MetagraphRepository.persist(pending_global_mg)` call:

```cypher
MERGE (n {node_id: $pending_node_id})
ON CREATE SET n = $props
ON MATCH SET n += $props
```

executed against the `mindsos_pending_global_<role>` FalkorDB graph
for the target role. The in-memory pending_global Metagraph also
gains the node via `add_node()` for the audit-gate consumer (PB-Z11(a)
single pending_global Metagraph parallel to canonical).

Rationale: full `persist()` iterates all nodes/edges of the metagraph
(probe-confirmed via Phase 24 design log §3 implementation references
on `MetagraphRepository.persist`); admin-batch proposes of N
mutations would cost O(N²) cumulative. Incremental Cypher is O(1)
per propose. Symmetric with PB-Z9(a)'s release-time MERGE-on-id
template.

**§"Decision" §2 release-ship per-role copy Cypher template (PB-Z9(a)):**

For each role with content in the snapshot set, `release_update`
issues a per-role MERGE-on-node_id Cypher copy from
`mindsos_pending_global_<role>` to `mindsos_global_<role>`:

```cypher
MATCH (src) IN mindsos_pending_global_<role>
 WHERE src.node_id IN $snapshot_node_ids_for_role
WITH src
MERGE (dst {node_id: src.node_id}) IN mindsos_global_<role>
  ON CREATE SET dst = properties(src)
  ON MATCH SET dst += properties(src)
```

(Pseudo-syntax; actual FalkorDB Cypher uses per-graph context, not
inline graph names.)

Pending node_id IS canonical node_id — the identity is preserved
through the lifecycle. On rerun after partial FAILED, the MERGE
matches the prior-shipped canonical node and SETs properties (no-op
if unchanged). No duplicate canonical nodes are created on rerun.

Rationale: probe confirmed `mindsos_admin/similarity.py:271` cross-mg
form does NOT self-exclude by node_id match (requires
`comparison_mg is mg` which is False on cross-mg). On rerun, even
with preserved node_id, cross-mg compute_similarity fires findings
unless the audit gate's suppression set (PB-Z7(a) +
`failed_release_canonical_node_ids` in FAILED manifest_json) drops
them. PB-Z9(a) + PB-Z7(a) together close the rerun-recovery loop:
MERGE-on-id at FalkorDB level + suppression at audit-gate level.

**§"Decision" §3 — unchanged.** Lazy migration still defers to Phase
25 per §amendment-1.

**FalkorDB persistence deferral (PB-Z21(b)):** Phase 24 v1 ships the
SQLite ledger + in-memory Metagraph mutation only. The Cypher MERGE-
on-id templates in clauses 1 + 2 of this amendment are **documentary
contracts for Phase 26** (the server-driven-persistence wiring
phase per ADR-0043 + Phase 15a precedent), NOT active code at Phase
24. Matches the established carry-forward: "Phase 15a does NOT
persist the resulting Metagraph — server-driven persistence ships at
Phase 18+ [carried to Phase 26]."

At Phase 24:

* ``mindsos_admin.propose_for_promotion`` writes (i) ``pending_
  mutations`` SQLite row, (ii) ``pending_global_mg.graphs[role].add_
  node(...)`` in-memory only. No ``Client.run_query`` call.
* ``mindsos_server.release.release_update`` per-role copy is
  ``canonical_global_mg.graphs[role].add_node(...)`` in-memory only
  (PB-Z21.2). Suppression set from PB-Z7(a) prevents collision on
  rerun. No ``Client.run_query`` call.
* ``pending_mutations.payload_json`` is the authoritative restart-
  rehydration source (PB-Z21.1) — on CLI re-invocation, the in-
  memory pending Metagraph is rebuilt from ``WHERE shipped_in_
  release IS NULL`` rows.

When Phase 26 wires server-driven FalkorDB persistence, the Cypher
templates in clauses 1 + 2 above become active code via a ``client:
Client`` parameter added to the propose / release / audit_gate
signatures. No clause-1-or-2 contract change at that ship — only
wiring.

**Coordinated changes at this amendment:**

* ``mindsos_admin/promotion.py`` — in-memory propose write +
  payload_json serialization (Phase 24); Cypher MERGE template
  documented for Phase 26.
* ``mindsos_server/release.py`` — in-memory per-role ``add_node``
  copy (Phase 24); Cypher MERGE template documented for Phase 26.
* ``tests/phase_24/test_release_update_merge_idempotent_on_rerun.py``
  (NEW per Round 6) — asserts rerun's in-memory ``add_node`` against
  prior-shipped canonical is suppressed by Z7(a) (no
  ``IdentityError`` raised; no duplicate canonical nodes).
* ``tests/phase_24/test_propose_persists_payload_json.py`` (renamed
  from ``test_propose_incremental_write.py`` per Z21(b) — Phase 24
  asserts SQLite payload_json content, NOT FalkorDB Cypher write).

**Phase 24 design log:** `halvim_mindsos/confirmation_docs/PHASE_24_
DESIGN_LOG.md` §1 Round 0 PB-Z9 + PB-Z13 picks + §4 ADR delta (13
touches post-Round-0).

### amendment-3 (Phase 26a ship — 2026-05-23) — FalkorDB persistence wired; §am2 Cypher templates corrected to metagraph_id+graph_id FK form

**Trigger:** §amendment-2 closing line read "*When Phase 26 wires
server-driven FalkorDB persistence, the Cypher templates in clauses
1 + 2 above become active code via a `client: Client` parameter
added to the propose / release / audit_gate signatures.*" Phase 26a
was the wiring phase named by §amendment-2 + by the
`mindsos_cli/commands/admin.py` importer docstring + by Phase 14a
round-3 lock — three independent documentary commitments to Phase
26 as the persistence-wiring slot. Phase 26 was split into 26a
(wiring) + 26b (Integration A scenario) per Phase 26a design log
R1-PB-1 (c).

**Phase 26a multi-round design re-litigation surfaced TWO substrate
facts §amendment-2 did not account for:**

1. **§am2 Cypher templates assumed per-FalkorDB-graph-per-role
   layout (`mindsos_pending_global_<role>` as separate FalkorDB
   graph names). The actual substrate (Phase 07 `MetagraphRepository`
   + Phase 07 `Client` Protocol per ADR-0030) is single-FalkorDB-graph
   keyed by `metagraph_id` FK.** `Client.run_query(query, params)`
   takes no `graph_name` parameter; one `FalkorClient` instance
   connects to one FalkorDB graph (per `FalkorConfig.graph =
   DEFAULT_GRAPH`); ALL Metagraphs (global, pending_global, per-user
   Locals) coexist in that one FalkorDB graph distinguished by
   `metagraph_id`. Contained role-graphs distinguished by `graph_id`
   property on nodes/edges. §amendment-2 Cypher templates would
   `PersistenceError` on first call as written.

2. **`KL.bootstrap()` is pure in-memory (verified at
   `mindsos_knowledge/knowledge_layer.py:154`).** Mints a fresh
   `Metagraph(name=_GLOBAL_METAGRAPH_NAME, ...)` and calls
   `ensure_global_role_graph` for each role. Zero FalkorDB. Cross-
   subprocess scenarios (Phase 26b integration script) require
   load-from-FalkorDB on KL init — a seam the original §amendment-2
   wiring scope did not include.

This amendment ships Phase 26a wiring across both findings.

**§"Decision" §1 propose-time write — corrected Cypher (supersedes
§amendment-2 §"Decision §1" PB-Z13 template):**

`mindsos_admin.propose_for_promotion(conn, client, *, session,
proposal, pending_global_mg)` writes pending-side via incremental
Cypher keyed on (metagraph_id, graph_id, node_id) instead of the
per-FalkorDB-graph-context form §amendment-2 wrote:

```cypher
MERGE (n:Node {node_id: $pending_node_id,
               metagraph_id: $pending_mg_id,
               graph_id: $role_graph_id})
ON CREATE SET n += $props
ON MATCH SET n += $props
```

executed against the single FalkorDB graph configured by
`FalkorConfig.graph`. `$pending_mg_id` resolves from
`pending_global_mg.metagraph_id`; `$role_graph_id` resolves from
the pending Metagraph's role-graph for `proposal.items[*].role`
via the existing `_find_role_graph(metagraph, role)` pattern
(`mindsos_server/release.py:731`).

The in-memory `pending_global_mg.graphs[role].add_node(...)` mirror
remains (audit-gate consumer reads it). Phase 24 SQLite
`pending_mutations` row write is unchanged.

**§"Decision" §2 release-ship per-role copy — corrected Cypher
(supersedes §amendment-2 §"Decision §2" PB-Z9 template):**

For each role with content in the snapshot set,
`mindsos_server.release.release_update(conn, client, *, session,
canonical_global_mg, pending_global_mg)` issues:

```cypher
MATCH (src:Node {metagraph_id: $pending_mg_id,
                 graph_id: $pending_role_graph_id})
WHERE src.node_id IN $snapshot_node_ids_for_role
WITH src, properties(src) AS srcprops
MERGE (dst:Node {node_id: src.node_id,
                 metagraph_id: $canonical_mg_id,
                 graph_id: $canonical_role_graph_id})
ON CREATE SET dst += apoc.map.removeKeys(srcprops, ['metagraph_id', 'graph_id'])
ON MATCH SET dst += apoc.map.removeKeys(srcprops, ['metagraph_id', 'graph_id'])
```

(FalkorDB v4.18.3 does not ship `apoc`; Round 7 §am-impl substitutes
explicit property-list enumeration via parameter-substituted property
maps — implementation detail in `mindsos_server/release.py`. The
semantics are: copy all properties from src to dst, overriding
metagraph_id + graph_id to canonical values.)

Per-role independence preserved: each role's MERGE-on-(canonical_mg_id,
canonical_role_graph_id, node_id) is independent; partial-completion
+ admin rerun is idempotent because MERGE is no-op when dst exists
with unchanged properties; PB-Z7 suppression set (`failed_release_
canonical_node_ids` in FAILED manifest_json) still works at the
audit-gate layer.

**§"Decision" §3 lazy migration — unchanged.** Per-user migration
still defers; no consumer at Phase 26a/26b (admin-direct ATOM-only
scope at v1 — admin path doesn't touch user Locals; no rewrite_map
consumer).

**Server-side bootstrap wrapper (NEW at Phase 26a — Phase 26a R4-PB-1 (b)
+ R5-PB-4 (a) + R6-PB-2 (b)):**

`mindsos_server/persistence/bootstrap.py::bootstrap_kl_from_falkordb(
client) -> KnowledgeLayer` is the load-or-mint seam:

```python
def bootstrap_kl_from_falkordb(client: Client) -> KnowledgeLayer:
    loader = MetagraphLoader(client)
    global_mg_id = loader.find_by_name(_GLOBAL_METAGRAPH_NAME)
    if global_mg_id is None:
        # first-ever bootstrap; mint + persist
        kl = KnowledgeLayer.bootstrap()
        repo = MetagraphRepository(client)
        repo.persist(kl.global_metagraph())
        return kl
    # subsequent invocations; load from FalkorDB
    global_mg = loader.load(global_mg_id)
    return KnowledgeLayer(global_metagraph=global_mg)
```

`MetagraphLoader.find_by_name(name) -> str | None` is a NEW Loader
method (Phase 26a; see ADR-0123 §amendment-1 for the supporting
index addition).

`MetagraphRepository.persist()` is MERGE-idempotent at every step
(verified at builders.py lines 62/83/100/155/267/343) — re-persist
after partial earlier persist is safe; no special "is this the first
bootstrap?" flag needed.

**Client lifecycle locked to Phase 07 P4 A invariant (Phase 26a
R5-PB-3 (a)):**

`_resolve_client()` in `mindsos_cli/commands/server.py` opens a
fresh `FalkorClient` per CLI invocation; caller closes via
try/finally. No module-level client singleton — Phase 07 P4 A
("CLI verbs open a client, run the verb, close. No long-lived
process-scope clients") explicitly forbids it. `_resolve_kl()`
calls `bootstrap_kl_from_falkordb(client)` then returns the KL +
the client to the caller for orchestrated close.

**Per-Metagraph storage mapping (R5-PB-2 (a) lock):**

Pending and canonical Metagraphs persist as one in-memory
`Metagraph` each, keyed by their respective `metagraph_id`, both
in the same FalkorDB graph. No split-by-role at the Repository
boundary; per-role atomicity preserved at the MERGE-key level (via
metagraph_id + graph_id + node_id). The in-memory
`pending_global_mg: Metagraph` shape (Phase 24) is unchanged.

**Importer wiring (Phase 26a R3-PB-2 (c) + R7-F3):**

`mindsos admin import {dolce,oewn,framenet}` CLI verbs at Phase 26a:

1. `_resolve_client()` opens fresh Client.
2. `_resolve_kl()` calls `bootstrap_kl_from_falkordb(client)` →
   returns KL with Global either loaded or freshly minted+persisted.
3. `Importer.import_into(kl)` mutates KL's in-memory Global per
   `target_roles`.
4. `MetagraphRepository.persist(kl.global_metagraph())` flushes
   importer output to FalkorDB (MERGE-idempotent over existing
   rows; new nodes ADD; existing nodes SET).
5. Client closes.

Phase 14a round-3 lock + the `mindsos_cli/commands/admin.py` "Phase
15a does NOT persist the resulting Metagraph — persistence of the
imported Global is deferred to Phase 26" docstring close at this
ship. The docstring is updated to reflect the new persistence path.

**§"Concurrency caveats" (Phase 26a R2-PB-5 (c) — NEW subsection):**

Phase 26a wiring does NOT add cross-graph or cross-Metagraph
transaction primitives. Two CLI subprocesses both running
`mindsos admin import dolce` concurrently have no FalkorDB-side
coordination:

- **Per-graph atomicity** (FalkorDB intrinsic): single Cypher query
  is atomic; concurrent queries against the same graph serialize
  at the storage engine.
- **No cross-graph multi-statement transaction**: FalkorDB does
  not expose transactions; ADR-0030 Client Protocol notes
  "`run_batch` is sequential — a failure on statement N of M
  leaves 1..N-1 committed and N+1..M unwritten."
- **`admin_tx` (Phase 24)** wraps SQLite only, not FalkorDB.
- **`UserMutexRegistry` (Phase 06 / Phase 25)** is per-user, not
  per-Global.
- **`RELEASE_SHIP_LOCK` (Phase 24)** serializes release_update
  only, not propose / import.

Concurrent admin imports may produce interleaved property writes;
because all writes are MERGE-on-id with the same node_ids, the
post-condition is "every node has at least one writer's properties
set" — not corruption, but not guaranteed last-writer-wins per
property either. Production deployments should serialize admin
imports at the operator level (single admin CLI session at a time).

Phase 32 (Integration B) or a dedicated concurrency-discipline phase
addresses. NOT a Phase 26a/26b blocker.

**§"FalkorDB persistence deferral" (§amendment-2 closing clause) —
CLOSED at this ship.** The deferral clause that read "*The Cypher
MERGE-on-id templates in clauses 1 + 2 of this amendment are
documentary contracts for Phase 26 ... NOT active code at Phase 24*"
closes here: at Phase 26a ship, the (corrected) templates above are
active code in `mindsos_admin/promotion.py` + `mindsos_server/
release.py` + `mindsos_admin/audit_gate.py` + the import CLI verbs.

**Coordinated changes at this amendment (Phase 26a ship):**

- `mindsos_admin/promotion.py` — `propose_for_promotion(conn, client,
  *, ...)` adds positional `client: Client` second-arg; in-memory
  add_node mirror unchanged; Cypher MERGE write per §"Decision §1"
  corrected template.
- `mindsos_server/release.py` — `release_update(conn, client, *, ...)`
  adds positional `client: Client` second-arg; per-role MERGE copy
  per §"Decision §2" corrected template; rerun-recovery suppression
  via Z7 unchanged.
- `mindsos_admin/audit_gate.py` — `run(admin_session, client, *, ...)`
  adds positional `client: Client` second-arg; reads pending content
  via in-memory Metagraph (no Cypher read needed at audit gate; the
  in-memory pending_global_mg is the audit-gate source-of-truth per
  PB-Z11(a) "single pending_global Metagraph parallel to canonical").
- `mindsos_admin/importers/__init__.py` — `ImporterProtocol`
  unchanged at Phase 26a; importer mutates KL's in-memory Global;
  caller (CLI) does the `repo.persist()` flush.
- `mindsos_cli/commands/admin.py` — `_resolve_client()` helper; CLI
  verbs persist KL's Global after import.
- `mindsos_cli/commands/server.py` — `_resolve_client()` helper
  (per Phase 25 `_resolve_persister` / `_resolve_kl` pattern); `_resolve_kl()`
  uses `bootstrap_kl_from_falkordb` wrapper.
- `mindsos_server/persistence/bootstrap.py` (NEW) — wrapper module
  per R6-PB-2 (b); `bootstrap_kl_from_falkordb(client)` first
  function; symmetric with sibling `local_persister.py`.
- `mindsos_core/reconstruction/metagraph_loader.py` — NEW method
  `find_by_name(name) -> str | None`.
- `mindsos_core/persistence/bootstrap.py` — `DEFAULT_INDEXES` gains
  19th entry `("node", "Metagraph", "name")` per ADR-0123 §am1.

**ADR cascade at Phase 26a ship:**

- ADR-0118 §am3 (this amendment).
- ADR-0010 §am2 (admin → core ALLOWED).
- ADR-0123 §am1 (Metagraph.name index).
- ADR-0043, 0121, 0114, 0011, 0125 — UNCHANGED.

**Phase 26a design log:** `halvim_mindsos/confirmation_docs/PHASE_26a_
DESIGN_LOG.md` §1 Rounds 0-7 picks consolidated.

### amendment-4 (Phase 26b ship — 2026-05-24) — Two-store decomposition; canonical flips to FalkorDB-authoritative; pending stays SQLite-rehydrated; closes B-26a-T4

**Trigger:** Phase 26a §amendment-3 wired FalkorDB persistence for
propose + release + audit_gate writes (`client: Client` kwarg
cascade; corrected metagraph_id+graph_id+node_id MERGE templates).
The CLI helper
`mindsos_cli/commands/server.py:_build_global_metagraphs(conn)` was
flagged at Phase 26a ship as the **B-26a-T4 candidate** carried to
Phase 26b — it built ephemeral in-memory Metagraphs via
`bootstrap_global(importers=()) → bootstrap_pending_global(canonical_mg)
→ rehydrate_global_metagraphs(conn, ...)`, minting brand-new random
`metagraph_id` values for canonical + pending on every CLI
invocation. Each invocation's §am3 Cypher MERGE writes landed in
FalkorDB but were keyed on ephemeral ids that no subsequent
invocation referenced — effectively orphaned writes.

Phase 26b closes the rewire per Phase 26b design log Round 1 R1-PB-1
(b) + R1-PB-4 (a) + Round 6 R6-PB-1 (a).

**Three-clause decomposition:**

**§"Decision" §1 — canonical content authority = FalkorDB.**

Canonical Global content is loaded from FalkorDB on CLI invocation
start via the Phase 26b pair helper
`mindsos_server.persistence.bootstrap_global_pair_from_falkordb(client)
-> tuple[KnowledgeLayer, Metagraph]`. The pair helper extends
Phase 26a's `bootstrap_kl_from_falkordb` with a symmetric load-or-
mint path for the pending Metagraph. Both anchors persist on first-
ever bootstrap so subsequent CLI invocations resolve stable
`metagraph_id` values via `MetagraphLoader.find_by_name`.

§am3's canonical Cypher MERGE write
(`mindsos_server/release.py:_RELEASE_MERGE_CYPHER`) **remains load-
bearing** — it produces the FalkorDB state that subsequent CLI
invocations load. The CLI helper
`_build_global_metagraphs(conn, client)` now threads `client`
through; signature change closes B-26a-T4.

**§"Decision" §2 — pending content authority = SQLite.**

Pending Global content remains SQLite-rehydrated per Phase 24 Z21.1
(`mindsos_admin/promotion.py::rehydrate_pending_global`). The pair
helper loads the pending **anchor** from FalkorDB (for stable
`metagraph_id`) but the caller is expected to immediately call
`rehydrate_pending_global(conn, pending_mg)` to populate the
contained pending nodes from the SQLite ledger (`pending_mutations.
payload_json` where `shipped_in_release IS NULL`).

§am3's pending Cypher MERGE write
(`mindsos_admin/promotion.py:_PROPOSE_MERGE_CYPHER`) is **RETAINED
in code but DEMOTED from load-bearing to forensic-only** — no
reader at Phase 26b. Future L4/L5 readers may consume the FalkorDB-
side pending content; until then it is a write-without-reader gap
documented here.

The pending Metagraph anchor IS persisted on first-ever bootstrap
(per Phase 26b R6-PB-1 (a)) for `metagraph_id` stability across
CLI invocations; the contained nodes are NOT loaded back at
bootstrap (SQLite rehydrate populates them per Z21.1).

**§"Decision" §3 — ship-manifest authority = SQLite.**

SQLite `pending_mutations` + `releases` rows remain authoritative
for the ship manifest. `mindsos_server/release.py:_select_snapshot`
reads `WHERE shipped_in_release IS NULL` from `pending_mutations`
per Phase 24 PB-26(b) + ADR-0114 §3. §am3 did not displace this;
§am4 does not either. The `_RELEASE_MERGE_CYPHER` write occurs in
addition to the SQLite stamp, not instead of it.

**Phase 24 unit-test Optional[Client]=None hatch preserved.**

Phase 26a B-26a-T3 relaxed `client: Optional[Client] = None` on
`propose_for_promotion` + `release_update` + `audit_gate.run` (with
`if client is not None:` guards around the Cypher writes) so Phase
24 tests that exercise the SQLite-only path keep passing. Phase 26b
preserves the hatch per Phase 26b R0-PB-8 (a) + R1-PB-5 (a):
production CLI MUST pass live Client (the §am4 §"Decision §1"
canonical-load semantics depend on it); Phase 24 unit tests pass
`client=None` and exercise the library functions over SQLite alone.

**Eager-load cost.**

`bootstrap_kl_from_falkordb` + the pair helper load the **full**
canonical Metagraph (`MetagraphLoader.load(metagraph_id)` per
ADR-0125 still-Proposed eager semantics) on every invocation —
eager-by-design. Phase 26b scenario uses a lightweight 10-row test
importer; production heavy-Global cost (e.g., post-Dolce import)
defers to ADR-0125 lazy-hydration promotion. Per Phase 26b
R2-PB-7 (a)+(d).

**Coordinated changes:**

* `mindsos_server/persistence/bootstrap.py` — adds
  `bootstrap_global_pair_from_falkordb(client) -> tuple[KnowledgeLayer,
  Metagraph]`.
* `mindsos_server/persistence/__init__.py` — re-exports the new
  helper alongside `bootstrap_kl_from_falkordb`.
* `mindsos_cli/commands/server.py` — `_build_global_metagraphs`
  signature gains positional `client`; body rewritten to call the
  pair helper + `rehydrate_pending_global` (pending only; canonical
  is FalkorDB-loaded). Propose + ship callsites reorder
  `client = _resolve_client()` open BEFORE `_build_global_metagraphs`
  so the helper has the client; try/finally envelopes both helper
  call + library call. Read-local callsite UNCHANGED (Phase 25
  diagnostic; in-memory KL sufficient per R5-F7 probe).

**ADR cascade at Phase 26b ship:**

- ADR-0118 §am4 (this).
- ADR-0010, ADR-0123, ADR-0114, ADR-0043, ADR-0121, ADR-0011 —
  UNCHANGED. (§am1 + §am2 of ADR-0010 already enumerate `server →
  admin` + `admin → core` allowed; pair-helper imports resolve
  without new layer-isolation amendment.)

**Phase 26b design log:** `halvim_mindsos/confirmation_docs/PHASE_26b_
DESIGN_LOG.md` §1 Rounds 0-6 picks consolidated.

### amendment-5 (Phase 28 ship — 2026-05-24) — Cypher MERGE :IN_GRAPH closure (B-26b-T5)

**Trigger:** Phase 26b ship (R5 B-26b-T5 finding) surfaced that §amendment-3's `_RELEASE_MERGE_CYPHER` (`mindsos_server/release.py`) and the symmetric §amendment-3's `_PROPOSE_MERGE_CYPHER` (`mindsos_admin/promotion.py`) both write `Node` rows keyed on `(node_id, metagraph_id, graph_id)` properties **without** creating the `[:IN_GRAPH]` relationship to the Graph anchor. Consequence: `MetagraphLoader.load(canonical_id)` (which traverses `[:IN_METAGRAPH]→[:IN_GRAPH]`) does not surface release-shipped content. This is honest at Phase 26b ship (the Integration A scenario sidesteps with a property-traversal counter `count_canonical_nodes_via_metagraph_id_property`), but it is a substrate gap — any future consumer that reads released L3/L2 content via `MetagraphLoader.load` would silently see zero released Nodes.

Phase 27 R0 PB-3 deferred to "first phase consumer reads released content via load." Phase 28 R1 PB-19 flipped that deferral: the fix is a mechanical 2-line patch, has zero blast radius outside Phase 26b's own helpers (R5 PB-49 grep + manual inspection confirmed at Phase 28 design close), and the longer this gap stays the more accidental forensic-only reasoning compounds. Ship the fix at Phase 28 alongside the L3 CapacityLayer.

**Amended templates:**

`mindsos_server/release.py:_RELEASE_MERGE_CYPHER` (supersedes §amendment-3 §"Decision §1" form):

```
MERGE (dst:Node {node_id: $node_id,
                 metagraph_id: $canonical_mg_id,
                 graph_id: $canonical_graph_id})
ON CREATE SET dst += $props
ON MATCH SET dst += $props
WITH dst
MATCH (g:Graph {id: $canonical_graph_id})
MERGE (dst)-[:IN_GRAPH]->(g)
```

`mindsos_admin/promotion.py:_PROPOSE_MERGE_CYPHER` (symmetric add):

```
MERGE (n:Node {node_id: $node_id,
               metagraph_id: $metagraph_id,
               graph_id: $graph_id})
ON CREATE SET n += $props
ON MATCH SET n += $props
WITH n
MATCH (g:Graph {id: $graph_id})
MERGE (n)-[:IN_GRAPH]->(g)
```

The `MERGE (...)-[:IN_GRAPH]->(g)` clause is idempotent: re-running propose/release with the same node MERGEs the same relationship without duplication. `MATCH (g:Graph {id: ...})` requires the Graph anchor row to already exist — which is guaranteed by the pair-helper's bootstrap (it materializes the canonical Graph anchors via `MetagraphLoader.load` ON LOAD).

**Invariants preserved:**

* **§amendment-3 forensic-only demotion stands** (pending writes via `_PROPOSE_MERGE_CYPHER` are still forensic; canonical writes via `_RELEASE_MERGE_CYPHER` still happen at release-ship). No semantic change beyond closure of the `[:IN_GRAPH]` gap.
* **§amendment-4 two-store decomposition stands** (SQLite remains ship-manifest authority; FalkorDB remains canonical-content authority). The §am5 fix only changes what gets written when FalkorDB is touched.
* **§am4 §"Eager-load cost"** subsection unchanged; ADR-0125 lazy hydration still Proposed.

**Coordinated changes at this amendment:**

* `mindsos_server/release.py` `_RELEASE_MERGE_CYPHER` — 3-line append per template above.
* `mindsos_admin/promotion.py` `_PROPOSE_MERGE_CYPHER` — symmetric 3-line append.
* `tests/phase_28/test_release_cypher_in_graph_link.py` (NEW) — string-assertion that both templates contain `[:IN_GRAPH]` post-§am5.
* `tests/phase_26b/test_integration_a.py` — stale-comment cleanup at lines 332-334 + 414-415 ("release writes orphan nodes" comment was true under §am3; under §am5 it's false; replace with "release shipping links via :IN_GRAPH per §am5").
* `tests/phase_26b/_falkordb_assert.py` — stale-docstring cleanup on `count_canonical_nodes_via_metagraph_id_property` (was "honest gap documented as carry-forward"; under §am5 the gap is closed; the helper still works, kept as forensic counter).

**Test impact** (R5 PB-49 grep + R5 PB-46 cleanup analysis):

* `test_integration_a.py:178` (≥10 graph-traversal nodes POST-IMPORT): unaffected — runs before release; importer already writes `:IN_GRAPH` via `MetagraphRepository.persist`.
* `test_integration_a.py:416` (==1 metagraph_id-property nodes POST-SHIP): unaffected — counter via property; agnostic to relationship.
* Zero other tests assert "released Node is orphan from :IN_GRAPH"; §am5 introduces no assertion flips.

**Memory closure:** `[[feedback-release-cypher-orphan-node]]` migrates from carry-forward to RESOLVED at Phase 28.

**Phase 28 design log:** `halvim_mindsos/confirmation_docs/PHASE_28_DESIGN_LOG.md` §"Round 1 PB-19" (R0 PB-6 flip) + §"Round 5 PB-46/PB-49" (impl-time blast-radius probe).
