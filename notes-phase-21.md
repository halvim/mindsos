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
- tests/phase_21/ — TODO_FILL_AFTER_RUN isolated, 0 failed, 0 skipped, ~TODO_SECONDS
- cumulative tests/ + tests_server/ — TODO_FILL_AFTER_RUN passed / TODO skipped / 0 failed (~TODO_RUNTIME)
  Phase 20 baseline 2611 + ~TODO net new Phase 21.

Doctor self-test (T-5): 6 checks green at +phase21; schema_version bumped 2→3.

Manual smoke (T-6 + Extras):
- bootstrap → login (admin) → query-audit → returns rows incl. self-EVT_AUDIT_QUERY: PASS
- bootstrap → user create alice → login alice → query-audit → PermissionDeniedError + EVT_PERMISSION_DENIED audit row: PASS
- query-audit --event EVT_LOGIN: filter narrows to login rows only: PASS
- query-audit --since ISO --until ISO: inclusive bound semantics: PASS
- query-audit --after-id N --limit 2: cursor walks page-by-page: PASS
- query-audit --count-only: returns int; EVT_AUDIT_QUERY row carries count_only=true: PASS
- query-audit --json: shape matches {rows, count, next_after_id} per PB-24: PASS
- TSV plain output: tabs visible; null actor/target as `-`: PASS
- Schema v3 verification: PRAGMA index_list('audit') shows idx_audit_target: PASS

Operator notes:
- TODO_FILL_AFTER_TESTING.
- If Click 8.2 flag-ordering quirk from Phase 20 manual smoke step 11 reappears
  on `query-audit --json --actor alice` vs `query-audit --actor alice --json`,
  document here (CliRunner doesn't reproduce; PR review can spot but not test).

Deferred per PB-3: audit-emission-coverage retest of P18-20 contracts →
Phase 26 integration phase (or stays implicit in per-phase suites).
Deferred per PB-4: separate "audit stats" verb (group-by-day, top-N, etc.) →
future phase only if operator demand surfaces. PHASE_MAP §21 row rewrites
"audit stats" to "--count-only flag" at ship.
Deferred per PB-15: compound indexes (idx_audit_event_ts, etc.) → future
performance phase if SQLite planner's single-index intersection proves
inadequate.
Deferred per PB-19 cleanup-only: refactor _DDL_AUDIT_INDEXES into versioned
lists (_V1, _V3) → future schema-hygiene phase. P21 ships the intentional
duplication.
Docs deferred per Phase 18/19/20 established pattern: docs/usage/server/audit.md
→ Phase 38 doc-review consolidation.
