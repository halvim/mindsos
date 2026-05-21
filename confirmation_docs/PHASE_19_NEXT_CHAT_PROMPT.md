══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 19 (Server: sessions)
══════════════════════════════════════════════════════════════════════
Project: MindsOS — folder `halvim_mindsos/` under
`/Layered Intelligence/`. Branch off `origin/main` tip.

Phase 18 SHIPPED + TAGGED 2026-05-2N (TBD post-confirm).
Expected `origin/main` shape AFTER Phase 18 squash-merge + tag:
    git fetch origin && git log --oneline origin/main | head -4
* Line 1 = `<SQUASH_SHA> Phase 18 — L0 user store + auth (#NN)`
* Line 2 = `06ec866 Phase 17 retirement: backfill squash-merge SHA in design log`
* Line 3 = `6d6f8bc Phase 17 — RETIRED: vacuous against ADR-0150 ...`
* Line 4 = `58e76a5 Phase 16 — L2 admin similarity surface (read-only) (#25)`

If line 1 does NOT show the Phase 18 squash-merge SHA, STOP — Phase 18
hasn't merged yet; resolve before branching.

`phase-18-confirmed` tag MUST point at line 1's SHA (verify via
`git rev-parse phase-18-confirmed`).

ROLE: Critical design reviewer + implementer. Follow project-level
CLAUDE.md skeptical-default + terse + pros/cons + alternatives +
picks-per-pushback (per `feedback_pushback_format_with_picks.md`).
Phase 19 scope is locked at PHASE_MAP §Phase 19 row — read that row,
do not re-derive scope from training. Mirror Phase 18's 4-round
design pushback ledger discipline (5 rounds preferred if pushbacks
keep surfacing load-bearing concerns).

══════════════════════════════════════════════════════════════════════
REQUIRED READING — in this order; READ THE FILES, do not guess
══════════════════════════════════════════════════════════════════════

1. `MEMORY.md` (auto-loaded at chat start). Every `feedback_*` entry
   is a hard rule. Pay special attention to:
   * `feedback_pushback_format_with_picks.md`
   * `feedback_pre_impl_probe_check_existing_modules.md` — Phase 19
     extends `mindsos_server/`; pre-impl probe must verify nothing
     unexpected (no `sessions.py` already shipped, no `LocalPersister`
     module, no `session_from_token` function).
   * `feedback_l1_api_signature_probe_before_writing_tests.md` —
     Phase 19 consumes Phase 18 APIs (Session, User, AuthFailedError,
     verify(), open_db(), init_or_migrate). Grep before assuming
     signatures.
   * `feedback_phase_baseline_literal_audit.md` — Phase 19 is the
     first version bump after Phase 18 (`+phase18 → +phase19`).
   * `feedback_test_image_rebuild_after_source_change.md` /
     `feedback_stale_local_tag_silent_overwrite_failure.md` /
     `feedback_release_tag_after_squash_merge_only.md` — Phase 19 is
     a tagged shipped-phase.
   * `feedback_state_file_serializer_deserializer_symmetry.md` —
     v1 → v2 SQLite migration (Phase 19 adds `sessions` table); both
     `init_or_migrate` upgrade step AND any rollback path must pair.

2. Phase-recap memory entries:
   * `project_mindsos_phase_18_implemented.md` (write this at Phase
     18 ship — captures actual shipped state + carry-forwards).
   * `project_mindsos_auth_and_concerns.md`
   * `project_mindsos_l0_server_pivot.md`

3. `halvim_mindsos/confirmation_docs/PHASE_MAP.md`:
   * §0 (load-bearing read rule) + §1 (settled cross-cutting decisions).
   * §Phase 19 row — primary scope source-of-truth.
   * §Phase 17 (RETIRED) + §Phase 18 rows — two prior phases per §0.
   * §Phase 20 row (NARROWED at Phase 18 ship per PB-27) — confirm
     Phase 19 doesn't need to know about Phase 20's narrowing.

4. `halvim_mindsos/confirmation_docs/PHASE_18_DESIGN_LOG.md` —
   most recent design log (per §0 chain-read rule). Read in full:
   §0 scope summary + §2 final locks table + §3 cross-chat
   dependencies (Forward subsection — Phase 18 → Phase 19 deltas).

5. ADRs (in `/Layered Intelligence/docs/decisions/adr/`):
   * **ADR-0003** (password + token scheme) — Phase 18 shipped the
     argon2id half; Phase 19 ships the token half (256-bit opaque +
     SHA-256-on-store + 8h sliding + 24h absolute TTL).
   * **ADR-0005** (refuse concurrent login) — Phase 19 enforces.
     `AlreadyLoggedInError` payload shape locked here.
   * **ADR-0002** (capability model) — Phase 19 may need to add
     `Session` construction with token. §amendment-1 from Phase 18
     ship: USER_CAPS strictly empty.
   * **ADR-0004** (split persistence) — `sessions` table schema.
   * **ADR-0011** (LocalPersister Protocol + hydrate/flush) —
     **Phase 19 IS the first consumer** per Phase 18 PB-18 deferral.
     Phase 18 did NOT ship `mindsos_server/persistence.py`; Phase 19
     decides whether to ship the protocol + `InMemoryLocalPersister`
     stub + `FalkorDBLocalPersister` thin wrapper now or defer
     individual implementations.
   * **ADR-0040** (SessionProtocol duck-typing) — Phase 18 shipped
     concrete `Session` matching exactly per PB-33. Phase 19 may
     expand the dataclass OR keep it slim + hold timestamps on the
     sessions row only.
   * **ADR-0013** (audit + Session.for_testing) — Phase 19 adds
     `EVT_LOGIN` + `EVT_LOGIN_REJECTED_CONCURRENT` + `EVT_LOGOUT`
     consumers; constants already shipped at Phase 18 per PB-34.
   * **ADR-0118** (per-user transactional promotion) — Proposed;
     not consumed at Phase 19 but the `CAN_PROPOSE_MUTATION` cap
     should NOT ship at Phase 19 either (per Phase 18 PB-12 strict
     ADR-0002 stance; wait for ADR-0118 Accept-flip at Phase 24).

══════════════════════════════════════════════════════════════════════
PRE-IMPL PROBE (run BEFORE any design pushbacks)
══════════════════════════════════════════════════════════════════════
    cd halvim_mindsos
    # Verify Phase 18 surfaces intact at main tip.
    git fetch origin && git log --oneline origin/main | head -4
    ls mindsos_server/
    grep -n "_SCHEMA_VERSION" mindsos_server/_schema.py
    grep -n "^EVT_LOGIN\|^EVT_LOGOUT\|^EVT_LOGIN_REJECTED" mindsos_server/audit.py
    grep -n "class Session" mindsos_server/session.py
    # Verify nothing Phase 19-shaped already shipped.
    ls mindsos_server/persistence.py mindsos_server/sessions.py 2>&1 | head -2
    grep -rn "session_from_token\|login\b" mindsos_server/ 2>/dev/null | head -10
    # Verify version baseline post-Phase 18.
    grep -rn '__version__ = "0\.0\.0+phase' --include="*.py" mindsos_*/ | head -10
    # Confirm Phase 18 audit event constants shipped + ready for consumption.
    grep -n "ALL_AUDIT_EVENTS\|EVT_LOGIN" mindsos_server/audit.py | head -5

If `mindsos_server/sessions.py` OR `mindsos_server/persistence.py`
already exists, surface as a reframe pushback (Phase 15b / Phase 17
retirement precedents).

══════════════════════════════════════════════════════════════════════
LIKELY PUSHBACK SURFACES (probe before locking scope)
══════════════════════════════════════════════════════════════════════

1. **`sessions` table schema v2 migration.** Phase 18 PB-2/PB-11
   locked forward-only DDL + `_SCHEMA_VERSION` row + `init_or_migrate`
   idempotent. Phase 19 bumps `_SCHEMA_VERSION = 2` + adds the v1→v2
   DDL step. Columns per ADR-0004 sketch: `session_id PK`, `user_id`
   (FK to users), `token_hash` (SHA-256 hex), `created_at`,
   `last_seen_at`, `expires_at`, `source` (CLI / future HTTP).

2. **Token storage on host filesystem.** PHASE_MAP §19 Risks names
   "in-memory only with `--token` argument, or restricted-perms
   volume". Phase 19 picks. Trade-offs: --token arg every call is
   high-friction; ~/.mindsos/token (mode 0600) is convenient but a
   shell-history risk if mishandled.

3. **Session field expansion (PB-33 deferral resolution).**
   Phase 18 shipped minimal Session matching SessionProtocol exactly
   (4 fields). Phase 19 needs `created_at` / `last_seen_at` /
   `expires_at` SOMEWHERE — on Session object? On the sessions
   table only? PB-33 punted; Phase 19 decides.

4. **`LocalPersister` shipment scope (PB-18 deferral resolution).**
   Phase 18 deferred entire persister surface. Phase 19 picks:
   (a) full Protocol + InMemoryLocalPersister + FalkorDBLocalPersister;
   (b) Protocol + InMemoryLocalPersister only (FalkorDB wrapper later);
   (c) defer further (Phase 22+ when admin cross-user reads need it).
   `login()` per ADR-0011 calls `persister.load(user_id)` — so login
   needs at least an `InMemoryLocalPersister` for tests.

5. **`AlreadyLoggedInError` payload shape per ADR-0005.** Three
   fields: existing session_id, created_at, source. Lock these now.

6. **Sliding + absolute TTL implementation.** Lazy check at lookup
   per ADR-0003 §Decision. Decision: where does the check live —
   `session_from_token()` only, or also a background sweeper thread?
   Phase 19 is local-first CLI; sweeper may be overkill.

7. **`mindsos server login / logout / whoami` CLI verbs.** Same
   verb-group as Phase 18 (`mindsos server`). Token output: stdout
   plaintext (pipe-friendly) or shielded prompt? `--json` form.

8. **Server restart wipes sessions.** ADR-0004 + ADR-0005 invariant.
   How: `DELETE FROM sessions` at server start, or rely on absolute
   TTL? Phase 19 has no daemon; "server start" is ambiguous in the
   CLI-only context. Probably: every fresh `mindsos server ...`
   invocation does NOT count as a server start (would wipe sessions
   on every command); instead, document that sessions die when the
   tester deletes `server.db` or when the absolute TTL expires.

══════════════════════════════════════════════════════════════════════
PROCESS DISCIPLINE — see MEMORY.md feedback entries
══════════════════════════════════════════════════════════════════════
Branch: `phase-19` off `origin/main` tip (verify Phase 18 squash-SHA
+ `phase-18-confirmed` tag first via `git log`).
Notes file: `notes-phase-19.md` at repo root.
`mindsos confirm-phase --init-notes 19` runs ONCE (overwrites).
Pre-build test image (`docker compose --profile test build
mindsos-test`) BEFORE confirm-phase AND after every hotfix.
Version bump `+phase18 → +phase19` across all version-bearing sites
(now 9 sites: 6 pkg `__init__.py` + pyproject + docker-compose tags
+ manifest.toml — count established at Phase 18 ship).
**No new top-level package expected at Phase 19** — extends
`mindsos_server/` only (sessions.py + possibly persistence.py +
sessions.py-related modules). 7-site checklist does NOT apply
again unless Phase 19 adds a 7th top-level pkg (not expected).
Tag `phase-19-confirmed` AFTER squash-merge only; verify
`git rev-parse phase-19-confirmed` returns "unknown" BEFORE creating.

══════════════════════════════════════════════════════════════════════
FIRST RESPONSE IN THE NEW CHAT SHOULD
══════════════════════════════════════════════════════════════════════
1. Confirm cited files read; report any missing.
2. Verify `git log --oneline origin/main | head -4` shows Phase 18
   squash at tip AND `git rev-parse phase-18-confirmed` resolves.
3. Run the pre-impl probe above; report findings.
4. Surface 1-3 pre-design pushbacks from §Likely pushback surfaces.
   **Each pushback ends with a pick per
   `feedback_pushback_format_with_picks.md`.**
5. Ask the single highest-value missing-constraint question.

DO NOT write code in the first response. Phase 16's 5-round +
Phase 18's 4-round design pushback ledger pattern is the shape this
project favors — sign off the architecture first, then implement.

══════════════════════════════════════════════════════════════════════
HANDOFF EXIT CRITERIA
══════════════════════════════════════════════════════════════════════
Phase 19 squash-merges to main; `phase-19-confirmed` tag pushed
AFTER merge; `release.yml` runs green; GitHub Release created.
Phase 19 writes `confirmation_docs/PHASE_20_NEXT_CHAT_PROMPT.md`
as exit artifact (Phase 20 = "Server: reset-admin + last-admin
protection" per Phase 18 PB-27 narrowing; deps Phase 19 only).
══════════════════════════════════════════════════════════════════════
