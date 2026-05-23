# Phase 24 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

Server + admin: per-user transactional promotion + release-boundary atomicity (ATOM admin-direct only)

## tester_notes

Phase 24 lands the ADR-0118 pivot model in code at the narrowest shippable
surface: admin-direct ATOM `propose_for_promotion` + `release_update` with
two-pass audit gate, RELEASE_SHIP_LOCK, release manifest, FAILED-row
forensics + rerun-recovery suppression set, schema v3→v4, 2 new caps,
4 new EVT_* events, `mindsos server release {propose-for-promotion,ship}`
CLI subgroup.

**44 picks across 6 design rounds** (28 original Rounds 1-5 + 16 Round 0
pre-impl refinements PB-Z1..Z22). Round 0 surfaced after the design-lock
chat when the implementer asked for re-analysis; six iterations produced:

- Z1 + Z7 + Z8 + Z9 — rerun-recovery substrate: MERGE-on-id Cypher
  template (Phase 26 contract) + audit-gate suppression set sourced
  from FAILED `manifest_json.failed_release_canonical_node_ids` +
  after-all-roles-clear inside admin_tx + node-id-scoped DELETE template.
- Z3 — two admin_tx blocks pattern: outer wraps happy path; on
  exception, second admin_tx writes FAILED row with Python-local
  roles_shipped tracking. KeyboardInterrupt window admitted in §6.
- Z11 + Z12 + Z13 — pending Metagraph topology: single
  `pending_global` Metagraph parallel to canonical, built via new
  `bootstrap_pending_global` helper (~10 LOC), reuses existing
  `ensure_global_role_graph`. Incremental Cypher MERGE at propose
  (Phase 26 contract; in-memory `add_node` at Phase 24).
- Z15 — rerun detection watermark: suppression set = union over
  FAILED rows with `release_id > (SELECT MAX FROM SHIPPED)`. SHIPPED
  advances the watermark; older FAILEDs naturally retire.
- Z16 — `EmptyComparisonError` propagates as FAILED with
  `error_class="empty_comparison"`; closed enum locks in ADR-0114 §am3.
- Z20 — node-id-scoped DELETE Cypher template (NOT graph-wide)
  preserves PB-26(b) lock-free propose under concurrent writes.
- Z21(b) + Z21.1 + Z21.2 — **FalkorDB persistence deferred to Phase
  26**: Phase 24 ships SQLite ledger + in-memory Metagraph only;
  `pending_mutations.payload_json` is the authoritative restart-
  rehydration source; `release_update`'s per-role copy is in-memory
  `canonical_global_mg.graphs[role].add_node(...)`. Symmetric with
  ADR-0043 + Phase 15a precedent ("server-driven persistence at
  Phase 26").
- Z22 — **ADR-0010 §am1 DAG correction**: Z5(b)'s initial "admin →
  server FORBIDDEN" was wrong; admin needs server's `admin_tx` +
  `_require_or_audit` + `write_audit` + `Session` + capability
  constants. Revised to ALLOWED at Round 0 PB-Z22 mid-implementation.

**ADR delta — 13 touches** (was 11 at Round-5 lock; Round 0 added 2):

- 3 new drafts: 0114 (release manifest + version DB schema), 0115
  (audit gate), 0120 (Proposed; impl at Phase 25).
- 4 Status flips: 0007 → Superseded; 0118 + 0141 → Accepted; 0144 →
  fully Accepted.
- 3 indirect Supersessions (per Phase 16 §am1 lock): 0049 + 0053 +
  0056. All pre-flipped at Z6(c) for design-pass-Status uniformity.
- 5 documentary §amendments: 0010 §am1 (DAG enumeration; revised at
  Z22), 0129 §am2 (snapshot vestigial), 0118 §am1 + §am2 (admin
  location + Cypher templates + Z21 Phase 26 deferral clause), 0141
  §am1, 0144 §am2.
- 1 cap-roster §amendment: 0002 §am2 (+2 caps; 7 → 9).
- 1 rename-ratification §amendment: 0006 §am1 (RELEASE_SHIP_LOCK).

**Tests/phase_24/ surface — 14 files** (~80 tests estimated; cumulative
green target = Phase 22's 2802 + Phase 24 isolated count). Coverage:

- Schema (2): pending_mutations + releases tables, CHECK constraints,
  indexes, v3→v4 migration.
- Bootstrap (1): pending_global topology + role parity with canonical.
- Promotion (4): ATOM happy + source_user deferred + kinds dispatch +
  capability denial + payload_json restart rehydration.
- Release (8): happy + empty + audit-gate blocking + audit-gate
  cross-mg + concurrent-propose-survives-clear + manifest_json shapes
  (SHIPPED + FAILED) + rerun-after-failed + merge-idempotent-on-rerun
  + release-ship-lock + capability denial.
- Architecture (2): import-isolation (ADR-0010 §am1 revised) +
  MetagraphSnapshot zero-consumers assertion.
- CLI (1): release subgroup happy path + empty exit code 7.

**FalkorDB persistence deferred to Phase 26** per Z21(b). The Cypher
MERGE-on-id template (Z9 + Z13) is documented in ADR-0118 §am2 as
the contract for Phase 26 to consume; at Phase 24, the in-memory
Metagraph + SQLite ledger together replicate the contract's behavior
without the wiring distraction.

**Source-user-Local propose + lazy migration deferred to Phase 25**
per ADR-0008 §am1 + ADR-0011 §am1 + ADR-0042 §am1 (cross-user read
substrate). Phase 24 admin-direct ATOM only; `source_user_id != None`
raises `NotImplementedError`. STRUCTURE / SUBGRAPH / PIPELINE
PromotionItemKind values ship for forward-shape contract per
PB-3(a) + PB-18(a) but raise `NotImplementedError` on dispatch.

Manual smoke required (host-native per `feedback_smoke_harness_host_
native.md`):

- `mindsos server bootstrap admin` + `mindsos server login admin` PASS.
- `mindsos server release propose-for-promotion --input-json <file>`
  with ATOM proposal PASS.
- `mindsos server release ship --json` SHIPPED PASS.
- `mindsos server release ship` on empty pending → exit 7 PASS.
- Duplicate propose + ship → BlockingFindingError exit 8 + FAILED
  row written PASS.
- After-FAILED rerun: delete one duplicate from pending_mutations →
  ship → SHIPPED PASS.
- Non-admin session → exit 3 PermissionDenied PASS (both verbs).

Architecture:
- mindsos_admin/promotion.py NEW (~500 LOC) — PromotionItemKind +
  NodeSpec + PromotionItem + PromotionProposal + PromotionResult
  dataclasses + propose_for_promotion + rehydrate_pending_global +
  rehydrate_canonical_global + rehydrate_global_metagraphs.
- mindsos_admin/audit_gate.py NEW (~250 LOC) — SimilarityWarning +
  ReleaseSummary + AuditGateResult + PendingMutationRow dataclasses
  + `run(...)` two-pass entry-point.
- mindsos_admin/bootstrap.py EXTENDED — `bootstrap_pending_global` +
  PENDING_GLOBAL_METAGRAPH_NAME.
- mindsos_admin/exceptions.py EXTENDED — BlockingFindingError +
  EmptyReleaseError + PendingMutationNotFoundError +
  DuplicateProposalError.
- mindsos_server/release.py NEW (~600 LOC) — release_update +
  ReleaseResult + ReleaseStatus + helper functions.
- mindsos_server/locks.py NEW (~120 LOC) — RELEASE_SHIP_LOCK +
  UserMutexRegistry.
- mindsos_server/_schema.py EXTENDED — v3→v4 migration step.
- mindsos_server/capabilities.py EXTENDED — +CAN_PROPOSE_MUTATION +
  CAN_APPROVE_RELEASE; ADMIN_CAPS roster 7 → 9.
- mindsos_server/audit.py RECONCILED — Phase 18 placeholders
  (EVT_PROMOTION_COMMITTED, EVT_PROMOTION_REJECTED_STALE_REPORT,
  EVT_PROMOTION_FAILED) replaced with PB-11(a) slate (EVT_PROMOTION_
  PROPOSED + EVT_PROMOTION_REJECTED + EVT_RELEASE_SHIPPED +
  EVT_RELEASE_FAILED).
- mindsos_cli/commands/server.py EXTENDED — `release_app` Typer
  subgroup; exit codes 7-8 mapper.
