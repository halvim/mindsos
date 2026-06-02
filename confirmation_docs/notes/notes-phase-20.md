# Phase 20 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

Server: admin reset (narrowed twice)

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

Phase 20 reset-admin shipped per ADR-0012 §am2 + design log 13-pick lock.

Automated tests (T-3 / T-4):
- tests/phase_20/ — 48 isolated, 0 failed, 0 skipped, 39.6s
- cumulative tests/ + tests_server/ — 2612 passed / 28 skipped / 0 failed (23:25)
  Phase 19 baseline 2562 + 50 net new Phase 20.

Doctor self-test (T-5): 6 checks green at +phase20.

Manual smoke (T-6 + Extras):
- bootstrap → login → reset-admin (rotate + kill session) → re-login: PASS
- UserNotFoundError on missing target: PASS
- NotAnAdminError on non-admin target: PASS
- reset-admin --json output shape: PASS ({"status":"reset", "user_id", "sessions_killed", "was_disabled"})
- Disabled-admin recovery (Extra 2): PASS — reset-admin re-enables disabled admin
  + EVT_ADMIN_ENABLE_USER first-fire confirmed via direct DB inspection.
- Audit-row eyeball (Extra 1): PASS — EVT_RESET_ADMIN + EVT_KILL_SESSION
  emitted with correct actor=os-user + extra_json shape per PB-D/AA/BB.
- A/B targeted re-run: PASS on both enabled-target and disabled-target paths
  (rotation persists; login with new password works on both paths).

Operator notes:
- Manual smoke step 11 required `--json` BEFORE positional to parse correctly
  (`reset-admin --json alice` worked; `reset-admin alice --json` returned
  "Missing argument USER_ID"). Tests pass with positional-first; root cause
  appears to be shell-level (Click 8.2 parsing not reproducible in
  CliRunner). Non-blocking; documented as a known oddity.
- Initial Extra 2 attempt failed with stale-password ("auth failed" after
  reset). Root cause: state-pollution from prior rounds; bootstrap's
  idempotency made the fresh-state command a no-op. Resolved by clean
  `rm -f ~/.mindsos/server.db` before each test sequence. Reset-admin
  itself confirmed correct via the targeted A/B above.

Deferred per PB-B: _assert_not_sole_admin helper + LastAdminError class →
Phase 22. Docs deferred to Phase 38 doc-review per established pattern.
