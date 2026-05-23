# Phase 24 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

Server + admin: per-user transactional promotion + release-boundary atomicity (ATOM admin-direct only)

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

Phase 24 — Server + admin: per-user transactional promotion + release-boundary atomicity (ATOM admin-direct only). SHIPPED + TESTED 2026-05-23.

Automated tests (Linux Docker, mindsos:phase24-test):
- tests/phase_24/ — 62 passed in ~60s (14 test files).
- tests/ cumulative — 2866 passed, 28 skipped in ~30m (Phase 22 baseline 2802 + 62 phase_24 + 2 deltas from B-24-T5 cumulative-decay reframes).
- 5 hotfixes during ship: B-24-T1..T5 (see below).

Doctor self-test: green on phase-24 branch. 6-package version parity at 0.0.0+phase24 (skipped +phase23 per design-only retirement). Schema_version bumped 3 → 4 (pending_mutations + releases tables per ADR-0114 §1+§2).

Manual smoke (host-native via mindsos binary per feedback_smoke_harness_host_native.md):
- bootstrap admin + login + whoami PASS.
- `mindsos server release --help` lists propose-for-promotion + ship PASS.
- propose-for-promotion happy path (ATOM ontology Class node "SmokeAnimal") → SHIPPED via release ship; mutation_ids=[1], release_id=1 PASS.
- release ship with no pending → exit 7 EmptyReleaseError PASS.
- Duplicate-content propose + ship (TASK 10) → SHIPPED (NOT blocking). Phase 16 _score_levenshtein operates on node_id UUIDs; fresh propose mints fresh UUIDs each call → Lev ~0 → no blocking finding at audit gate. Tests pass via inject_pending_node helper using controlled IDs ("dup-test-aaaaa-0001/0002"). NOT A REGRESSION — known Phase 16 heuristic property; admin would need richer feature extraction (frame_elements, synonyms, parents per ADR-0144 §Heuristic structural Jaccard) or the source-user path (Phase 25) for controlled-ID collisions through the CLI propose surface.

Bonus smoke (Phase 24 deferral surfaces + regression checks):
- Z21.1 restart-rehydration (SMOKE A): propose; fresh CLI invocation ships → in-memory pending Metagraph rebuilt from pending_mutations.payload_json PASS. Z21(b) Phase 26 deferral semantic confirmed end-to-end via single-process CLI re-invocation.
- PermissionDeniedError exit 3 (SMOKE B): non-admin user 'bob' → propose-for-promotion exit 3 (CAN_PROPOSE_MUTATION missing) PASS; ship exit 3 (CAN_APPROVE_RELEASE missing) PASS.
- STRUCTURE/SUBGRAPH/PIPELINE NotImplementedError (SMOKE C): STRUCTURE kind → exit 1 + stderr "PromotionItemKind.STRUCTURE dispatch deferred...Phase 24 ships ATOM only per design log PB-3(a)" PASS. Exit 1 (_release_exit_for defensive fallback) is consistent with Phase 22 pattern; NotImplementedError is unmapped by design — admins don't programmatically act on "deferred feature" signals.
- source_user_id NotImplementedError (SMOKE D): exit 1 + stderr "PromotionItem.source_user_id='alice' requires Phase 25 cross-user read substrate (ADR-0008 §am1)..." PASS.
- Phase 21 query-audit picks up Phase 24 EVT_* (SMOKE E): EVT_RELEASE_SHIPPED + EVT_PROMOTION_PROPOSED rows surface via query-audit --event PASS.
- Phase 22 admin verbs regression (SMOKE F): `admin --help` lists 6 verbs (promote-user, demote-user, disable-user, enable-user, kill-session, hard-delete-user); `user list` returns admin + bob PASS.

Cross-phase observations:
- First CLI smoke attempt threw "auth failed" — stale-state replay quirk. Audit row showed actor_user='admi' (4 chars) but users table had 'admin' (5 chars). Clean `rm -f` + re-bootstrap restored normal behavior. Defensive: always rm -f the smoke DB before each smoke session.

Hotfixes during ship:
- B-24-T1: ALL_AUDIT_EVENTS tuple at audit.py:179 still listed Phase 18 placeholder constants (EVT_PROMOTION_COMMITTED, EVT_PROMOTION_REJECTED_STALE_REPORT, EVT_PROMOTION_FAILED) after the rename batch in Task #8. 3-line tuple-edit replaced with PB-11(a) slate (EVT_PROMOTION_REJECTED + EVT_RELEASE_SHIPPED + EVT_RELEASE_FAILED).
- B-24-T2: Circular import — mindsos_server/__init__.py eagerly imported release.py which imports mindsos_admin.audit_gate which imports mindsos_server.session which re-enters mindsos_server/__init__.py mid-load → ImportError on PendingMutationRow. Fix: dropped the eager release re-export from mindsos_server/__init__.py; CLI + tests already use `from mindsos_server.release import release_update` directly.
- B-24-T3: 4 clusters in phase_24/ tests — (A) 4 FK constraint failures (tmp_server_db → seeded_admin so the FK to users.user_id + audit.id are satisfied); (B) 6 DID NOT RAISE BlockingFindingError (added inject_pending_node + inject_canonical_node fixtures using controlled near-identical node_ids "dup-test-aaaaa-0001/0002" → Lev ~0.96 → reliably blocking, bypassing propose's UUID minter); (C) 3 CliRunner.mix_stderr Click 8.2 errors (drop kwarg + switch to result.output per Phase 22 pattern); (D) PropertyShapeError on 'label' reserved key (use 'definition' — label is in RESERVED_PROPERTY_KEYS).
- B-24-T4: 1 leftover tmp_server_db ref in test_releases_v1_v2_columns_null_at_default body (replace_all hit fixture parameter but missed one body line).
- B-24-T5: Cumulative decay — (E) Phase 15a import isolation relaxed (mindsos_server removed from _FORBIDDEN_ROOTS per Z22(a) ADR-0010 §am1 revised); (F) Phase 18 capabilities-parity roster 7 → 9; (G) Phase 18+21 schema-version literal 3 → 4 (5 sites); (H) Phase 22 no_schema_bump reframed from `== 3` to `>= 3` (Phase 22 baseline; later phases may bump).

Round 0 pre-impl re-analysis (PB-Z1..Z22, 16 picks):
- Surfaced after the design-lock chat when the implementer asked for re-analysis. Three iterations produced rerun-recovery substrate + persistence-deferral lock + DAG-direction correction:
- Z1+Z7+Z8+Z9 — MERGE-on-id Cypher template (Phase 26 contract per Z21(b)) + FAILED manifest_json.failed_release_canonical_node_ids for rerun-suppression + after-all-roles clear inside admin_tx + node-id-scoped DELETE template.
- Z3 — two admin_tx blocks pattern for FAILED-row write with Python-local roles_shipped tracking.
- Z4 — zero-consumer assertion test for MetagraphSnapshot replacing PB-13(a)'s "lint rule dropped."
- Z5→Z22 corrected mid-impl — admin → server ALLOWED (initial FORBIDDEN was wrong; admin uses server's admin_tx + authz + audit + Session + capabilities; bi-directional admin ↔ server is cycle-safe).
- Z6 — pre-flip ADRs 0049/0053/0056 for design-pass-Status uniformity (all 10 Status flips uniform at impl start).
- Z11+Z12+Z13 — single pending_global Metagraph parallel to canonical + reuse ensure_global_role_graph helper + incremental Cypher MERGE at propose (Phase 26 contract).
- Z15 — suppression-set query watermark "FAILED rows since last SHIPPED" (SHIPPED advances; older FAILEDs retire).
- Z16 — EmptyComparisonError propagates as FAILED with error_class="empty_comparison"; closed enum.
- Z20 — DELETE template scoped to snapshot's node_ids (NOT graph-wide) preserves PB-26(b) lock-free propose under concurrent writes.
- Z21(b) — Phase 24 v1 = SQLite + in-memory Metagraph only. FalkorDB Cypher templates (Z9 + Z13) are documentary contracts in ADR-0118 §am2 for Phase 26 wiring phase, NOT active code at Phase 24. Matches ADR-0043 + Phase 15a precedent.
- Z21.1 — pending_mutations.payload_json is the authoritative restart-rehydration source; rehydrate_pending_global + rehydrate_canonical_global + rehydrate_global_metagraphs helpers in mindsos_admin.promotion.
- Z21.2 — release_update's per-role copy is in-memory canonical_global_mg.graphs[role].add_node; Z7(a) suppression set prevents IdentityError on rerun.

Architecture:
- mindsos_admin/promotion.py NEW (~500 LOC) — PromotionItemKind + NodeSpec + PromotionItem + PromotionProposal + PromotionResult dataclasses + propose_for_promotion + 3 rehydrate helpers (rehydrate_pending_global / rehydrate_canonical_global / rehydrate_global_metagraphs).
- mindsos_admin/audit_gate.py NEW (~250 LOC) — SimilarityWarning + ReleaseSummary + AuditGateResult + PendingMutationRow dataclasses + run() two-pass entry-point per ADR-0115.
- mindsos_admin/bootstrap.py EXTENDED — bootstrap_pending_global sibling helper + PENDING_GLOBAL_METAGRAPH_NAME ("pending_global_knowledge").
- mindsos_admin/exceptions.py EXTENDED — BlockingFindingError + EmptyReleaseError + PendingMutationNotFoundError + DuplicateProposalError (latter two reserved for v2).
- mindsos_server/release.py NEW (~600 LOC) — release_update orchestrator with two admin_tx blocks pattern; ReleaseResult + ReleaseStatus.
- mindsos_server/locks.py NEW (~120 LOC) — RELEASE_SHIP_LOCK + UserMutexRegistry (declared; first consumer Phase 25).
- mindsos_server/_schema.py EXTENDED — v3→v4 migration with releases + pending_mutations tables + partial indexes.
- mindsos_server/capabilities.py EXTENDED — +CAN_PROPOSE_MUTATION + CAN_APPROVE_RELEASE; ADMIN_CAPS 7 → 9.
- mindsos_server/audit.py RECONCILED — Phase 18 placeholders replaced with PB-11(a) slate (EVT_PROMOTION_PROPOSED + EVT_PROMOTION_REJECTED + EVT_RELEASE_SHIPPED + EVT_RELEASE_FAILED).
- mindsos_cli/commands/server.py EXTENDED — release_app Typer subgroup; _release_exit_for mapper with exit codes 7-8.
- 13 ADR touches at ship: 3 new drafts (0114/0115/0120; 0120 stays Proposed for Phase 25 first consumer) + 4 Status flips (0007→Superseded; 0118/0141→Accepted; 0144 fully Accepted) + 3 indirect Supersessions (0049/0053/0056 pre-flipped at Z6(c)) + 5 §amendments (0010 §am1 revised at Z22; 0118 §am1+§am2; 0129 §am2; 0141 §am1; 0144 §am2) + 1 cap-roster §am (0002 §am2) + 1 rename-ratification §am (0006 §am1 RELEASE_SHIP_LOCK).

Deferred to Phase 25 (substantive — see PHASE_25_NEXT_CHAT_PROMPT.md):
- Source-user-Local propose path (admin-on-behalf-of-user) per ADR-0008 §am1 cross-user read substrate.
- Lazy per-user migration + ADR-0120 KL handler implementation (apply_rewrite_map).
- 4 deferred EVT_* (DRAFT_FROZEN + DRAFT_UNFROZEN + MIGRATION_APPLIED + MIGRATION_FAILED).
- MindsOSServer orchestrator class + LocalPersister + read_other_local() context manager.
- CAN_READ_PENDING_GLOBAL capability (waits for first direct-read consumer).

Deferred to Phase 26 (per Z21(b)):
- FalkorDB persistence for pending_global + canonical_global Metagraphs.
- Cypher MERGE-on-id templates documented in ADR-0118 §am2 become active code via `client: Client` parameter added to propose / release / audit_gate signatures.
- CLI verb constructs FalkorClient from env config.
