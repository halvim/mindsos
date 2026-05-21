# Phase 18 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

Server: user store + auth

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

Phase 18 introduces `mindsos_server/`, the first L0 (Server) top-level
package per ADR-0001. **NEW CODE** despite PHASE_MAP §18 row originally
saying "Net-new: No" — row text was stale (written before retirement-era
ADR audit). PB-1 amends the row to "Net-new: Yes (first L0 pkg per
ADR-0001)" at this ship.

4-round design pass (38 picks; see
`confirmation_docs/PHASE_18_DESIGN_LOG.md`). Mirrors Phase 16's
5-round shape; round 5 was self-flagged as saturating on impl detail
and skipped at user confirmation.

Surface shipped:
- `mindsos_server/` package: `__init__`, `capabilities` (7 UPPER
  constants per PB-4 + ADR-0002 + USER_CAPS empty + ADMIN_CAPS all-7
  per PB-12), `errors` (`AuthFailedError` opaque-cause +
  `UserAlreadyExistsError` per PB-23 + PB-30), `session` (frozen
  Session matching SessionProtocol exactly per PB-33), `users`
  (`User` frozen dataclass + `insert_user` + `list_users` + `verify`
  + `_insert_first_admin` per PB-13/24/29; imports `_USER_ID_RE` from
  KL per PB-7), `audit` (full ADR-0013 event enum upfront per PB-34 +
  `write_audit` + `_now_utc_iso` per PB-35), `_argon2` (PRODUCTION +
  `_TEST_FAST` params per PB-14 + `_SENTINEL_HASH` precomputed
  constant per PB-22/PB-31), `_db` (WAL + foreign_keys + busy_timeout
  pragmas per PB-19), `_schema` (`_SCHEMA_VERSION=1` + v1 DDL with
  `users` + `audit` + `schema_version` tables per PB-2/PB-11/PB-28).
- `mindsos_cli/commands/server.py` (per PB-32 — convention with
  `admin.py`/`graph.py`/etc.): `server user {create,list,verify}` +
  `server bootstrap` (lifted from Phase 20 per PB-27). No
  `--password` flag declared per PB-8 — `--password-stdin` only.

NEW top-level pkg `mindsos_server/` — 7-site checklist applied:
- pyproject.toml: `mindsos_server` pkg + `argon2-cffi` dep +
  `mindsos_cli → mindsos_server` dep edge per PB-25 + PB-32.
- requirements.in: `argon2-cffi` line (per
  `feedback_lock_sh_reads_requirements_in.md` — pyproject alone
  doesn't trigger lock.sh).
- Dockerfile prod stage: `COPY mindsos_server/`.
- Dockerfile test stage: `COPY mindsos_server/ tests/phase_18/
  tests_server/`.
- SENTINEL_PATHS: `mindsos_server/__init__.py` runtime sentinel (NOT
  docs per `feedback_sentinel_paths_runtime_only.md`).
- doctor self-test: 5→6 pkg parity loop per PB-21 + PB-37 (also
  checks `server.db` schema_version=1 when present).
- [Linux] host pip refresh: `pip install -e . --user
  --break-system-packages` after pulling phase-18 branch per
  `feedback_host_pip_refresh_on_new_package.md`.

Version bump `+phase17 → +phase18` across 9 sites: `mindsos_core/`,
`mindsos_knowledge/`, `mindsos_admin/`, `mindsos_instances/`,
`mindsos_cli/`, `mindsos_server/` (NEW), `pyproject.toml`,
`docker-compose.yml`, `manifest.toml`.

ADR amendments at this ship (5):
- ADR-0002 §amendment-1 (documentary) — USER_CAPS strictly empty in
  v1; Proposed-status caps from 0118/0137 wait for Accept-flip phase
  per PB-12.
- ADR-0012 §amendment-1 — bootstrap CLI verb lifted from Phase 20 to
  Phase 18 per PB-27; Phase 20 narrows to reset-admin + last-admin.
- ADR-0041 §amendment-1 (documentary) — UPPER casing for capability
  constants per PB-4. Parity test stops auto-skipping at P18.
- ADR-0044 §amendment-2 — server inherits `_USER_ID_RE` via import
  per PB-7 (rather than duplication-with-parity-test).
- ADR-0046 §amendment-1 (documentary) — UPPER casing alignment per
  PB-4.

PHASE_MAP §18 row amended per PB-1: "Net-new: Yes (first L0 pkg per
ADR-0001)" + bootstrap CLI added to Features. §20 row narrowed per
PB-27: bootstrap dropped from Features; row keeps "reset-admin
recovery; last-admin removal blocked" only.

Tests/phase_18: ~9 isolated test files (counts: TBD post-Linux run).
tests_server/integration/test_layer_isolation.py ships per PB-26
(ADR-0010 I-S1 enforcement from package creation onward — not
deferred to Phase 25).

Cumulative test count: TBD (Phase 17 retirement baseline was
2236/19; expect +N from Phase 18 isolated additions, no regressions).

Hotfix ledger (B-18-T*): TBD post-Linux run.

Smoke test: TBD. Expected recipe:
1. `mindsos server bootstrap` (interactive; argon2id-hash + insert
   first admin row with full ADMIN_CAPS).
2. `mindsos server user list --json` (admin user shows; password_hash
   NEVER in output per PB-24).
3. `echo "$WRONG_PW" | mindsos server user verify <admin_user_id>
   --password-stdin` (exits non-zero with opaque "auth failed";
   audit row written with private cause=BAD_PASSWORD).
4. `echo "$CORRECT_PW" | mindsos server user verify <admin_user_id>
   --password-stdin` (exits 0; audit row written).
5. Inspect `~/.mindsos/server.db` via `sqlite3` to verify
   schema_version=1, WAL mode active, users + audit + schema_version
   tables present.

Deferred / out-of-scope (see DESIGN_LOG §6 for full list):
sessions table + tokens (P19), `LocalPersister` (P19), reset-admin
(P20), last-admin protection (P20), audit query reader (P21),
disable/enable verbs (P22), password change (P22 admin reset only),
promotion (P24), SessionProtocol seam in KL (P25).
