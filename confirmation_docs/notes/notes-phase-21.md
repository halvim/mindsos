# Phase 21 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

Server: audit log reader

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

Phase 21 audit log reader shipped per ADR-0013 §am2 + design log 20-pick lock.

Automated tests (T-3 / T-4):
- tests/phase_21/ — 83 isolated, 0 failed, 0 skipped, 84.81s (after B-21-T1 hotfix).
- cumulative tests/ + tests_server/ — 2696 passed / 28 skipped / 0 failed (25:22).
  Phase 20 baseline 2611 + 85 net new Phase 21.

Doctor self-test (T-5): 6 checks green at +phase21; schema_version bumped 2→3.

Manual smoke (T-6 + T-extra, host-native via `mindsos` binary — `docker compose
run --rm` has no persistent ~/.mindsos/server.db mount, so host-native is the
canonical smoke harness; matches Phase 19/20 implicit convention):
- bootstrap admin → login admin → query-audit returns BOOTSTRAP+LOGIN: PASS
- --event EVT_LOGIN narrows to 1 row: PASS
- --json --limit 2 → {"rows": [...], "count": 2, "next_after_id": 2}: PASS
- --count-only → "count=5" (5 rows existed before this call): PASS
- --since/--until broad window → all rows; each EVT_AUDIT_QUERY row carries
  sparse filters snapshot per PB-17: PASS
- --since "not a date" → ValueError + exit=2: PASS
- non-admin denial: alice login → query-audit → exit=3 + EVT_PERMISSION_DENIED
  audit row with {capability, verb} payload per PB-13: PASS
- Schema v3 + idx_audit_target present (sqlite_master query): PASS
- --actor / --target filter separation (PB-2) works at CLI: PASS
- --after-id N cursor walks forward correctly: PASS
- --count-only --json → {"count": N}; no rows/next_after_id keys: PASS
- Empty result --json → {"rows": [], "count": 0, "next_after_id": null}: PASS

Hotfixes:
- B-21-T1 (caught at T-5): 7 test expectations assumed self-emitted
  EVT_AUDIT_QUERY would appear in the calling result. Implementation does
  SELECT → write EVT_AUDIT_QUERY → return (read-then-write), so the row is
  only visible to SUBSEQUENT calls. PB-16i ("included in default reader
  output") delivers transparency ACROSS calls, not within a single call.
  Tests adjusted to the two-call pattern. Implementation unchanged.

Operator notes:
- `mindsos --version` is NOT a flag (use `mindsos doctor --self-test` to
  confirm phase). Tester recipe corrected mid-smoke.
- `docker compose run --rm` has no ~/.mindsos volume mount; state dies with
  --rm. Host-native invocation is the canonical smoke harness (per
  `feedback_confirm_phase_invocation_paths.md`). Phase 22+ smoke recipes
  should default to host-native unless deliberately testing the in-container
  path with a persistent volume.

Deferred per PB-3: audit-emission-coverage retest of P18-20 contracts →
Phase 26 integration phase (or stays implicit in per-phase suites).
Deferred per PB-4: separate "audit stats" verb (group-by-day, top-N, etc.) →
future phase only if operator demand surfaces. PHASE_MAP §21 row rewrites
"audit stats" to "--count-only flag" at ship.
Deferred per PB-15: compound indexes (idx_audit_event_ts, etc.) → future
performance phase if SQLite planner's single-index intersection proves
inadequate.
Deferred per PB-19 cleanup-only: refactor _DDL_AUDIT_INDEXES into versioned
lists → future schema-hygiene phase. Phase 21 ships the intentional
duplication.
Docs deferred per Phase 18/19/20 established pattern:
docs/usage/server/audit.md → Phase 38 doc-review consolidation.
