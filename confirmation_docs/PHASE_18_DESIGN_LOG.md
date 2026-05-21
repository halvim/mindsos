---
phase: 18
phase_title: "Server: user store + auth"
layer: L0
status: design-locked
date_locked: 2026-05-21
branch: phase-18
tag_on_confirm: phase-18-confirmed
net_new: true   # supersedes PHASE_MAP §18 row "No"; first L0 pkg per ADR-0001
design_rounds: 4
total_picks: 38
prior_phase: 17  # RETIRED 2026-05-20 (design-only-with-code; no tag)
next_phase: 19
---

# Phase 18 Design Log — Server: user store + auth

## §0. Scope summary

Phase 18 introduces `mindsos_server/`, the first L0 (Server) top-level package
per ADR-0001. Ships the SQLite-backed user store (`server.db`), argon2id
password hashing per ADR-0003, the canonical capability roster + bundles per
ADR-0002, the `Session` dataclass + `Session.for_testing` shim per ADR-0040 +
ADR-0013, the universal audit writer + full event-constant enum per ADR-0013,
and CLI verbs `mindsos server user {create,list,verify}` + `mindsos server
bootstrap` (the bootstrap CLI is lifted from Phase 20 per round-3 PB-27).

This phase **does NOT** ship: sessions table or token issuance (Phase 19);
`LocalPersister` Protocol + `MetagraphDump` (Phase 19 first consumer per
PB-18); reset-admin or last-admin protection (Phase 20); audit query
reader (Phase 21); cross-user reads (Phase 22); promotion or release (Phase 24);
SessionProtocol seam in L2 (Phase 25); password change (Phase 22, admin only).

## §1. Round-by-round design ledger

The chat ran four rounds of pushbacks before locking. Picks per pushback +
final picks summary per `feedback_pushback_format_with_picks.md`. Phase 16's
five-round ledger was the precedent; round 5 was self-flagged as saturating
on impl detail and skipped.

### Round 1 — Handoff scope contradictions + ADR audit (PB-1..PB-10)

Pre-impl probe established that (a) `mindsos_server/` does not exist on
`origin/main` tip (`06ec866`), (b) no unexpected auth code lives in
`mindsos_*/` packages, (c) the Phase 17 retirement surfaces
(`versions_in_role` + ADR-0150 §amendment-3) are intact, (d) `_USER_ID_RE`
already lives at `mindsos_knowledge/identifiers.py:79` per ADR-0044 §am1.

Read ADRs 0001-0005, 0010-0013, 0040, 0041, 0044, 0046 to ground each
pushback.

**PB-1 — PHASE_MAP §18 row is stale ("Net-new? No"); contradicts probe + ADR-0001.**
Amend row to "Net-new: Yes (first L0 pkg per ADR-0001)". 7-site checklist runs.

**PB-2 — Dep "07 only" is incomplete; SQLite has no prior phase.**
Ship forward-only DDL + `schema_version` row + `init_or_migrate(conn)`. No
framework dep (no Alembic, no yoyo).

**PB-3 — Initial pick: v1 = `users` only.** (REVISED by PB-11 — see Round 2.)

**PB-4 — Capability casing drift between ADR-0002 (UPPER) and ADRs 0041/0046 (lower).**
Pick UPPER. ADR-0041 + ADR-0046 documentary §amendment-1 at Phase 18 ship.

**PB-5 — Capability roster: ship all seven from ADR-0002.**
USER_CAPS = empty, ADMIN_CAPS = all seven. (REVISED by PB-12.)

**PB-6 — Ship `Session` at Phase 18.** ADR-0041 capability parity test stops
auto-skipping at Phase 18 (good — fewer auto-skips).

**PB-7 — `mindsos_server` imports `_USER_ID_RE` from `mindsos_knowledge.identifiers`.**
ADR-0010 only forbids KL→server direction; server→KL is permitted.

**PB-8 — Don't declare `--password` CLI flag at all.** `--password-stdin` only.
Keeps plaintext out of argv/ps/shell-history.

**PB-9 — Internal `_insert_first_admin(conn, user_id, password)` helper at P18.**
(REVISED by PB-27 — bootstrap CLI verb lifts to P18 too.)

**PB-10 — `mindsos server user {create,list,verify}` single-binary verb group.**
ADR-0012 §amendment-1 documentary (verb name updates).

### Round 2 — ADR-0013/0118/0137 deep read + revisions (PB-11..PB-21)

Reading ADR-0013 (audit + Session.for_testing), ADR-0118 (Proposed —
per-user transactional promotion), and ADR-0137 (Proposed — user-facing
request_promotion) forced two revisions and surfaced six new concerns.

**PB-11 (REVISES PB-3) — Audit table MUST ship at Phase 18, not Phase 21.**
ADR-0013 mandates `EVT_ADMIN_CREATE_USER` audit row on user-create +
`PERMISSION_DENIED` audit on cap-check failure + bootstrap with OS-user
actor per ADR-0012. v1 ships `users` + `audit` tables; v2 (P19) adds
`sessions`.

**PB-12 (REVISES PB-5) — USER_CAPS strictly empty per ADR-0002.**
ADRs 0118/0137 are Proposed, not Accepted. Proposed-status capabilities
(`CAN_PROPOSE_MUTATION`, `CAN_APPROVE_RELEASE`, `CAN_REQUEST_PROMOTION`,
`CAN_REVIEW_PROMOTION_REQUESTS`) wait for their Accept-flip phase
(24/25) to land. Ship the original 7 from ADR-0002. ADR-0002
§amendment-1 (documentary) records this scope discipline.

**PB-13 — `verify(user_id, password) -> User`** (frozen dataclass);
raises `AuthFailedError` on `{unknown_user, bad_password, disabled}`.

**PB-14 — Explicit `params: Argon2Params` injection.**
`PRODUCTION_PARAMS` matches ADR-0003 verbatim; tests pass
`_TEST_FAST_PARAMS`. No env-driven global.

**PB-15 — `verify` honors `disabled=1`** via `AuthFailedError` (cause
internal). Avoids Phase 22 retrofit risk.

**PB-16 — `user_id TEXT PRIMARY KEY`.** No surrogate integer PK.
`sessions.user_id` (P19) and `audit.actor_user` reference by user_id-string.

**PB-17 — Default `~/.mindsos/server.db`** + manifest `[server] db_path`
field + env `MINDSOS_SERVER_DB` override + doctor reachability check
when present (absent = fine, fresh install).

**PB-18 — `LocalPersister` + `MetagraphDump` surface deferred to Phase 19**
(login = first real consumer). Phase 18 has no `persistence.py`.

**PB-19 — `PRAGMA journal_mode=WAL` + `foreign_keys=ON` + `busy_timeout=5000`**
on every connection open. Per-call short-lived connections; no pool.

**PB-20 — Password change deferred to Phase 22** (admin reset only at v1).
Phase 18 row says "create / list / verify"; no change verb.

**PB-21 — Doctor + parity test bumped to 6-pkg coverage.** Mandatory per
§1 doctor check (6) + 7-site checklist. Update `mindsos_cli/commands/doctor.py`
parity loop + the parity test in `tests/phase_02/` (probe at impl time
per `feedback_phase_baseline_literal_audit.md`).

### Round 3 — Security + boundary + scope-shift (PB-22..PB-30)

**PB-22 — Timing leak closure: `verify()` always runs argon2** against a
sentinel hash on user-not-found. Closes the user-enumeration attack.

**PB-23 — Single `AuthFailedError` class; uniform public message;
private `cause` enum** for internal audit-write. Tests inspect `.cause`;
callers see opaque "auth failed". HTTP layer (future) maps to single
status code.

**PB-24 — Frozen `User(user_id, actor_role, disabled, created_at)`.**
No `password_hash` field; never returned to callers.

**PB-25 — Hard dep `mindsos_knowledge` in `mindsos_server` pyproject.**
PB-7's import choice ratifies. Server-without-KL is not a real install target.

**PB-26 — Phase 18 ships `tests_server/integration/test_layer_isolation.py`**
per ADR-0010. Closes the I-S1 window from package creation onward (not
deferred to Phase 25).

**PB-27 (AMENDS PB-9 + PB-10) — Phase 18 also ships `mindsos server bootstrap` CLI verb.**
Lifted from Phase 20. Phase 18's user-create CLI verb is unusable without
an admin caller, so the bootstrap verb is a natural pair with the helper.
Phase 20 row narrows to "reset-admin recovery; last-admin removal blocked"
(two Features instead of three). ADR-0012 §amendment-1 records the lift.

**PB-28 — `actor_role TEXT NOT NULL CHECK (actor_role IN ('user','admin'))`.**
DB-level enforcement mirrors the `Literal` type annotation. Two-layer
defense; cost = zero.

**PB-29 — Idempotency at CLI-verb caller level**, not helper. Helper
`_insert_first_admin(conn, user_id, password)` is pure insert; raises on
UNIQUE conflict. CLI verb checks `SELECT COUNT(*) FROM users WHERE
actor_role='admin'` and exits 0 with message if ≥1. Both layers
independently testable.

**PB-30 — Distinct `UserAlreadyExistsError`** for create-path UNIQUE
violations. Create errors are not auth errors; security-leak concerns
from PB-23 don't apply.

### Round 4 — Impl-detail saturation check (PB-31..PB-38)

**PB-31 — Precomputed `_SENTINEL_HASH` module constant** (argon2id of a
fixed nonsense string baked into source). Argon2's one-wayness makes the
bake-in safe. No startup tax.

**PB-32 — CLI verbs at `mindsos_cli/commands/server.py`.** Convention
continuity. `mindsos_cli` pyproject adds `mindsos_server` dep edge.
(User explicitly confirmed PB-32 pick A in round 4 closure.)

**PB-33 — Minimal `Session` matching SessionProtocol exactly**:
`Session(session_id, user_id, actor_role, capabilities)` + `has()`.
Sessions table (P19) holds timestamps; Session object stays slim +
immutable + parity-matched with the Protocol.

**PB-34 — Ship full ADR-0013 audit event enum upfront** at
`mindsos_server/audit.py`. Constants are strings; centralized roster
matches ADR-0013 §Decision; future phases just import + use.

**PB-35 — TEXT ISO-8601 UTC millisecond timestamps.**
`_now_utc_iso() -> str` helper; tests assert format invariance.

**PB-36 — `mindsos server user verify` CLI verb exists** (documented as
diagnostic; `--password-stdin`). Row Features list literal honored.
Post-bootstrap smoke test use case.

**PB-37 — doctor checks `server.db` schema_version** matches code
constant `_SCHEMA_VERSION = 1`. Drift exits non-zero.

**PB-38 — `mindsos_server/__init__.py` exports**: `Session`,
`AuthFailedError`, `UserAlreadyExistsError`, `User`, the 7 capability
constants, `USER_CAPS`, `ADMIN_CAPS`, `__version__`. Internal modules
(`_db`, `_schema`, `_argon2`) underscore-prefixed and excluded from
`__all__`. `audit`, `users` submodules accessible but not re-exported.

## §2. Final locks consolidated (38-pick reference)

| # | Pick | ADR cite |
|---|---|---|
| 1 | PHASE_MAP §18 row Net-new: Yes amendment | ADR-0001 |
| 2 | Forward-only DDL + `schema_version` row + `init_or_migrate()` | ADR-0004 |
| 3 | (revised by PB-11) | — |
| 4 | UPPER capability constants | ADR-0002 (canonical) |
| 5 | (revised by PB-12) | — |
| 6 | `Session` ships at P18 | ADR-0040 + ADR-0041 |
| 7 | Import `_USER_ID_RE` from KL | ADR-0044 §am1 |
| 8 | No `--password` flag declared | ADR-0003 ethos |
| 9 | `_insert_first_admin()` internal helper | ADR-0012 |
| 10 | `mindsos server user {create,list,verify}` verb group | §1 single-binary |
| 11 | v1 DDL: `users` + `audit` (sessions=v2/P19) | ADR-0013 |
| 12 | USER_CAPS empty; only 7 ADR-0002 caps shipped | ADR-0002 + ADR-0010 |
| 13 | `verify() -> User`; `AuthFailedError` on 3 causes | ADR-0003 |
| 14 | `Argon2Params` injection; PRODUCTION + _TEST_FAST | ADR-0003 |
| 15 | `verify` honors `disabled=1` | ADR-0012 chain |
| 16 | `user_id TEXT PRIMARY KEY` | ADR-0044 §am1 |
| 17 | `~/.mindsos/server.db` + manifest + env override | Phase 07 B-07-T2 pattern |
| 18 | `LocalPersister` deferred to P19 | ADR-0011 |
| 19 | WAL + foreign_keys=ON + busy_timeout=5000 | ADR-0004 |
| 20 | Password change deferred to P22 admin reset | ADR-0003 + PHASE_MAP §22 |
| 21 | Doctor + parity test 6-pkg | §1 doctor check (6) |
| 22 | `_SENTINEL_HASH` always-verify | ADR-0003 ethos |
| 23 | Single `AuthFailedError` + private cause | ADR-0003 + security baseline |
| 24 | Frozen `User(user_id, actor_role, disabled, created_at)` | ADR-0004 schema |
| 25 | `mindsos_knowledge` hard dep in server pyproject | ADR-0010 |
| 26 | `tests_server/integration/test_layer_isolation.py` ships P18 | ADR-0010 |
| 27 | `mindsos server bootstrap` CLI lifts to P18 | ADR-0012 §am1 |
| 28 | `actor_role` CHECK constraint | ADR-0002 + ADR-0004 |
| 29 | Bootstrap idempotency at CLI caller, not helper | ADR-0012 |
| 30 | Distinct `UserAlreadyExistsError` | ADR-0004 schema |
| 31 | Precomputed `_SENTINEL_HASH` constant | ADR-0003 |
| 32 | CLI verbs at `mindsos_cli/commands/server.py` | §1 CLI convention |
| 33 | Minimal `Session` matching Protocol | ADR-0040 |
| 34 | Full ADR-0013 audit enum upfront | ADR-0013 |
| 35 | TEXT ISO-8601 UTC ms timestamps | ADR-0004 schema |
| 36 | `mindsos server user verify` CLI exists (diagnostic) | PHASE_MAP §18 Features |
| 37 | doctor checks `server.db` schema_version | §1 doctor check (6) |
| 38 | `__init__.py` exports (see PB-38) | — |

## §3. Cross-chat dependencies

### Backward (Phase 18 inherits from earlier phases)

- **ADR-0044 §am1 `_USER_ID_RE`** — Phase 12 lock at
  `mindsos_knowledge/identifiers.py:79`. Phase 18 imports verbatim per PB-7.
- **Phase 07 B-07-T2 manifest-fallback pattern** — env > manifest > hard-coded.
  Phase 18 `[server] db_path` config follows.
- **Phase 17 retirement surfaces intact** — `versions_in_role` + ADR-0150
  §amendment-3. Phase 18 doesn't touch these but the +phase18 bump applies
  to `metagraph_view.py` headers and similar.
- **PHASE_MAP §1 single-binary rule** — `mindsos <subcommand>`. Phase 18
  ships `mindsos server …` group, not a separate `mindsos-server` binary.
- **`feedback_pushback_format_with_picks.md`** — every pushback ended with
  a pick (4 rounds × ~9 picks).

### Forward (Phase 18 → later phases)

- **Phase 19 (sessions)** consumes the v2 migration slot, adds `sessions`
  table + `session_from_token` + `login()` returning `Session`. Login calls
  Phase 18 `verify()` → `User`, then constructs Session + token + sessions row.
  PB-18 deferral lands here: `LocalPersister` + `MetagraphDump` first-consumed
  on login hydration.
- **Phase 20 (bootstrap CLI narrowed)** — bootstrap verb lifted to P18 per
  PB-27. P20 now ships only reset-admin recovery + last-admin protection.
  Update PHASE_MAP §20 row Features at Phase 18 ship.
- **Phase 21 (audit reader)** consumes the audit table already shipped at
  P18 v1 per PB-11. Adds `admin_query_audit()` + `CAN_VIEW_AUDIT_LOG` gating.
- **Phase 22 (admin ops)** ships disable/enable verbs (Phase 18's verify
  already honors `disabled=1` per PB-15) + password change (deferred per PB-20).
- **Phase 24 (promotion)** lands `CAN_PROPOSE_MUTATION` + `CAN_APPROVE_RELEASE`
  capability constants per ADR-0118 Accept-flip. Phase 18's USER_CAPS empty
  may amend at this point if ADR-0137 also Accept-flips (adding
  `CAN_REQUEST_PROMOTION` to user default).
- **Phase 25 (SessionProtocol seam)** ships `mindsos_knowledge/types.py`
  Protocol + `mindsos_knowledge/capabilities.py` constants. The ADR-0041
  parity test (now non-skipping per PB-6) becomes the enforcement gate.

## §4. ADR delta at Phase 18 ship

| ADR | Action | Reason |
|---|---|---|
| **0001** | Status unchanged (Accepted) | First L0 pkg materializes here; no amendment needed. |
| **0002** | §amendment-1 (documentary) | USER_CAPS strictly empty in v1; Proposed-status caps from 0118/0137 wait for Accept-flip phase per PB-12. |
| **0003** | Status unchanged (Accepted) | Phase 18 implements verbatim. |
| **0004** | Status unchanged (Accepted) | v1 = `users` + `audit`; `sessions` at P19; `version_db` at P24. |
| **0010** | Status unchanged (Accepted) | Layer-isolation test ships at P18 per PB-26. |
| **0011** | Status unchanged (Proposed) | Deferred to P19 per PB-18; no Phase 18 surface. |
| **0012** | §amendment-1 | Bootstrap CLI verb lifted from Phase 20 to Phase 18 per PB-27; Phase 20 narrows to reset-admin + last-admin. |
| **0013** | Status unchanged (Accepted) | Universal audit + `Session.for_testing` ship at P18. Full event-constant enum upfront per PB-34. |
| **0040** | Status unchanged (Accepted) | `Session` concrete dataclass matches Protocol exactly per PB-33. |
| **0041** | §amendment-1 (documentary) | UPPER casing for capability constants per PB-4. Parity test stops auto-skipping at P18. |
| **0044** | §amendment-2 | Server inherits `_USER_ID_RE` via import per PB-7 (rather than duplication-with-parity-test). Documentary conformance note. |
| **0046** | §amendment-1 (documentary) | UPPER casing alignment per PB-4. |

## §5. Implementation references

```
mindsos_server/                        # NEW top-level package (6th)
├── __init__.py                        # __version__ + PB-38 exports
├── capabilities.py                    # 7 UPPER constants + USER_CAPS + ADMIN_CAPS (PB-4 + PB-12)
├── errors.py                          # AuthFailedError + UserAlreadyExistsError (PB-23 + PB-30)
├── session.py                         # Session frozen dataclass + for_testing (PB-33 + PB-6)
├── users.py                           # User + insert/list/verify + _insert_first_admin (PB-13/24/29)
├── audit.py                           # Full ADR-0013 event enum + write_audit (PB-34)
├── _argon2.py                         # PRODUCTION + _TEST_FAST + _SENTINEL_HASH (PB-14 + PB-22 + PB-31)
├── _db.py                             # _open() with WAL pragmas (PB-19)
└── _schema.py                         # _SCHEMA_VERSION = 1 + DDL + init_or_migrate (PB-2 + PB-11)

mindsos_cli/commands/server.py         # NEW; CLI verbs (PB-32)
mindsos_cli/app.py                     # add_typer(server_app, name="server")

tests/phase_18/
├── test_argon2.py                     # PB-14 + PB-22 + PB-31
├── test_db_schema.py                  # PB-2 + PB-11 + PB-19 + PB-28
├── test_users.py                      # PB-13 + PB-15 + PB-23 + PB-24 + PB-30
├── test_session.py                    # PB-33
├── test_audit.py                      # PB-34 + PB-35
├── test_capabilities_parity.py        # PB-4 + PB-12 (now non-skipping)
├── test_cli_server_user.py            # PB-8 + PB-10 + PB-36
├── test_bootstrap_cli.py              # PB-27 + PB-29
└── test_doctor_6pkg_parity.py         # PB-21

tests_server/integration/
└── test_layer_isolation.py            # PB-26 (ADR-0010 I-S1 enforcement)

docs/usage/server/
└── auth.md                            # PHASE_MAP §18 Docs entry; mkdocs last_confirmed_phase: 18

# Modified outside mindsos_server/:
pyproject.toml                         # +mindsos_server pkg, +argon2-cffi, +cli→server dep (PB-25 + PB-32)
requirements.in                        # +argon2-cffi (feedback_lock_sh_reads_requirements_in.md)
Dockerfile                             # COPY mindsos_server/ in prod+test stages
mindsos_cli/_sentinel_paths.py         # +mindsos_server sentinels (runtime-only)
mindsos_cli/commands/doctor.py         # 5→6 pkg parity loop (PB-21 + PB-37)
docker-compose.yml                     # phase17→phase18 tag bump
manifest.toml                          # +[server] db_path field (PB-17)
confirmation_docs/PHASE_MAP.md         # §18 row Net-new amendment; §20 narrowing (PB-1 + PB-27)
docs/decisions/adr/0002-…              # §amendment-1 documentary
docs/decisions/adr/0012-…              # §amendment-1 bootstrap lift
docs/decisions/adr/0041-…              # §amendment-1 UPPER + parity unskip
docs/decisions/adr/0044-…              # §amendment-2 server inherits regex via import
docs/decisions/adr/0046-…              # §amendment-1 UPPER alignment

# Version bump +phase17 → +phase18 across 9 sites:
mindsos_core/__init__.py
mindsos_knowledge/__init__.py
mindsos_admin/__init__.py
mindsos_instances/__init__.py
mindsos_cli/__init__.py
mindsos_server/__init__.py             # NEW
pyproject.toml [project] version
docker-compose.yml image tags
manifest.toml [mindsos] version
```

## §6. Scope boundaries (out-of-scope at Phase 18 ship)

- **Sessions table / token issuance / login** — Phase 19. v2 migration slot
  reserved per PB-11.
- **`LocalPersister` Protocol + `MetagraphDump`** — Phase 19 first-consumer
  per PB-18.
- **`reset-admin` CLI verb** — Phase 20 (narrowed scope post-PB-27).
- **Last-admin protection (`_assert_not_sole_admin`)** — Phase 20.
- **`admin_query_audit` reader + `CAN_VIEW_AUDIT_LOG` gating** — Phase 21.
- **Cross-user reads (`read_other_local`)** — Phase 22.
- **`disable_user` / `enable_user` CLI verbs** — Phase 22. (Phase 18 verify
  honors the column per PB-15; verbs land at 22.)
- **Password change** — Phase 22 (admin reset only); user-self change later
  per PB-20.
- **Promotion (`propose_for_promotion`, `release_update`)** — Phase 24
  (ADR-0118 Accept-flip).
- **User-facing `request_promotion`** — when ADR-0137 Accept-flips (likely
  alongside or after Phase 24).
- **SessionProtocol + capability constants in `mindsos_knowledge`** — Phase 25.
  Phase 18's `tests/phase_18/test_capabilities_parity.py` ships the test
  but its KL-side counterpart (`mindsos_knowledge/capabilities.py`) lands
  at Phase 25; until then the test skips on `ImportError` for the KL side.
  (Update on round-4 reflection: actually, the parity test ASSERTS the
  server-side roster shape standalone at P18; the KL-side parity comparison
  is what activates at P25. This is the precision PB-6 intended.)
- **HTTP transport** — Phase 1 framing; no roadmap.
- **`version_db/` SQLite (release manifest)** — Phase 24 per memory
  `project_mindsos_l1_redesign`. Phase 18 does NOT pre-declare its path
  in manifest (per round-4 open-question pick: wait for the consumer).

## §7. Design saturation note

Four rounds (38 picks). Round 5 was self-flagged at the close of round 4 as
likely impl-detail (CLI exit codes, `--json` shape, list sort order, test
fixture organization). The user confirmed lock at round 4. Implementation
proceeds per the task list in this chat. Any new pushback surfaced during
implementation is recorded as a B-18-TN hotfix in the confirmation doc, not
a retroactive PB-NN entry.
