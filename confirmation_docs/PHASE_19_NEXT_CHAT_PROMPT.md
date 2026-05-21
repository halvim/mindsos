══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 19 (Server: sessions)
══════════════════════════════════════════════════════════════════════

This prompt is intentionally lean. The phase chat reads files for
context; this prompt only points at them + locks process expectations.

Project: MindsOS — folder `halvim_mindsos/` under
`/Layered Intelligence/`. Branch off `origin/main` tip.

ROLE: Critical design reviewer + implementer. Read the project-level
CLAUDE.md at `/Layered Intelligence/CLAUDE.md` AND the MindsOS
sub-project CLAUDE.md if present. Follow strict picks-per-pushback
discipline (each pushback ends with a pick; final picks summary at
the end of every multi-pushback round; see
`feedback_pushback_format_with_picks.md`).

Phase 19 scope is locked at PHASE_MAP §Phase 19 row. Read it; do not
re-derive scope from training.

══════════════════════════════════════════════════════════════════════
REQUIRED READING (in this order)
══════════════════════════════════════════════════════════════════════

1. **`MEMORY.md`** — auto-loaded at chat start. Every `feedback_*`
   entry is a hard rule. Pay special attention to:
   * `feedback_pushback_format_with_picks.md`
   * `feedback_pre_impl_probe_check_existing_modules.md`
   * `feedback_l1_api_signature_probe_before_writing_tests.md`
   * `feedback_phase_baseline_literal_audit.md`
   * `feedback_lock_sh_reads_requirements_in.md`
   * `feedback_test_image_rebuild_after_source_change.md`
   * `feedback_stale_local_tag_silent_overwrite_failure.md`
   * `feedback_batch_fix_dont_iterate.md`
   * `feedback_sandbox_vs_mac_git_separation.md`
   * `user_two_machine_setup.md` (Mac/Linux split + commands)

2. **`halvim_mindsos/confirmation_docs/PHASE_MAP.md`** §0 (load-bearing
   read rule) + §1 (settled cross-cutting decisions — read in full;
   Phase 18 amended the Two-machine workflow row) + §Phase 17
   (RETIRED tombstone) + §Phase 18 (most recent shipped) + §Phase 19
   (own row — primary scope source) + §Phase 20 (narrowed scope per
   Phase 18 PB-27 — confirm Phase 19 doesn't cross into P20).

3. **`halvim_mindsos/confirmation_docs/PHASE_18_DESIGN_LOG.md`** —
   most recent design log. Read §0 scope summary + §2 final locks
   table + §3 cross-chat dependencies (Forward subsection — Phase
   18 → Phase 19 deltas) + §4 ADR delta + §6 out-of-scope. This is
   the durable contract for what Phase 19 inherits.

4. **`halvim_mindsos/confirmation_docs/PHASE_18_CONFIRMED.md`** —
   ground truth for the actually-shipped state at Phase 18 tag.
   Tester notes section captures B-18-T1 / B-18-T2 hotfixes +
   test counts + manual smoke. If the design log and the
   confirmation doc disagree, the confirmation doc wins (it's
   post-impl evidence).

5. **ADRs** at `/Layered Intelligence/docs/decisions/adr/`. Read in
   full at first probe — Phase 19 consumes many:
   * **ADR-0003** (password + token scheme). Phase 18 shipped the
     argon2id half; Phase 19 ships the token half (256-bit opaque +
     SHA-256-on-store + 8h sliding + 24h absolute TTL).
   * **ADR-0005** (refuse concurrent login). Phase 19 enforces.
     `AlreadyLoggedInError` payload shape locked here.
   * **ADR-0011** (LocalPersister Protocol + hydrate/flush) —
     **Phase 19 IS the first consumer** per Phase 18 PB-18
     deferral. Phase 18 did NOT ship `mindsos_server/persistence.py`;
     Phase 19 decides shipment scope.
   * **ADR-0002 §amendment-1** (Phase 18 ship) — USER_CAPS strictly
     empty; Proposed-status caps from 0118/0137 wait for their
     Accept-flip phase.
   * **ADR-0040** — Session matches SessionProtocol exactly (Phase
     18 PB-33). Phase 19 may expand fields OR keep slim + hold
     timestamps on the sessions row only.
   * **ADR-0013** — audit constants `EVT_LOGIN`,
     `EVT_LOGIN_REJECTED_CONCURRENT`, `EVT_LOGOUT` already shipped
     at Phase 18 per PB-34; Phase 19 wires consumers.
   * **ADR-0004** (split persistence) + **ADR-0012** (bootstrap §am1
     at Phase 18: bootstrap CLI lifted to P18; P20 narrowed).
   * **ADR-0118 + ADR-0137** are Proposed — do NOT ship their caps
     yet (Phase 18 PB-12 lock; wait for Accept-flip at P24/P25).

══════════════════════════════════════════════════════════════════════
PRE-IMPL PROBE (run BEFORE any design pushbacks)
══════════════════════════════════════════════════════════════════════

  cd halvim_mindsos
  # Verify Phase 18 squashed + tagged at main tip.
  git fetch origin && git log --oneline origin/main | head -5
  git rev-parse phase-18-confirmed 2>&1 | head -1

  # Verify Phase 18 surfaces intact.
  ls mindsos_server/
  grep -n "_SCHEMA_VERSION" mindsos_server/_schema.py
  grep -n "^EVT_LOGIN\|^EVT_LOGOUT\|^EVT_LOGIN_REJECTED" mindsos_server/audit.py
  grep -n "class Session" mindsos_server/session.py

  # Verify nothing Phase 19-shaped already shipped.
  ls mindsos_server/persistence.py mindsos_server/sessions.py 2>&1 | head -2
  grep -rn "session_from_token\|def login\b" mindsos_server/ 2>/dev/null | head -10

  # Version baseline.
  grep -rn '__version__ = "0\.0\.0+phase' --include="*.py" mindsos_*/__init__.py

If `mindsos_server/sessions.py` OR `mindsos_server/persistence.py`
already exists, surface as a reframe pushback (Phase 15b / Phase 17
retirement precedents).

══════════════════════════════════════════════════════════════════════
LIKELY PUSHBACK SURFACES (probe before locking scope)
══════════════════════════════════════════════════════════════════════

Each pushback ends with a pick. Final round closes with a Picks
summary.

1. **`sessions` table schema v2 migration** — Phase 18 locked
   `_SCHEMA_VERSION=1` (users + audit); Phase 19 bumps to 2. Append
   migration step in `init_or_migrate()` per the forward-only DDL
   pattern Phase 18 established.

2. **Token storage on host filesystem** — PHASE_MAP §19 Risks
   names the trade-off (in-memory `--token` vs `~/.mindsos/token`
   mode 0600). Pick.

3. **Session field expansion (PB-33 deferral resolution)** —
   Phase 18 shipped minimal `Session` matching SessionProtocol
   exactly. Phase 19 picks where `created_at` / `last_seen_at` /
   `expires_at` live (Session object OR sessions row only).

4. **`LocalPersister` shipment scope (PB-18 deferral resolution)**
   — Phase 18 deferred entire persister surface. Phase 19 picks
   (a) full Protocol + Memory + FalkorDB impl; (b) Protocol +
   InMemory only; (c) defer further.

5. **`AlreadyLoggedInError` payload shape per ADR-0005** — three
   fields: existing session_id, created_at, source. Lock.

6. **Sliding + absolute TTL implementation** — lazy at lookup
   only, or also background sweeper? Phase 19 is local-first CLI;
   sweeper likely overkill.

7. **`mindsos server login / logout / whoami` CLI verbs** —
   verb-group `server` (Phase 18 convention). Token output:
   stdout plaintext (pipe-friendly) or shielded prompt? `--json`
   form.

8. **Server-restart wipes sessions semantics** — ADR-0004 +
   ADR-0005 invariant says "sessions die on server restart". In
   the CLI-only context "server start" is ambiguous (no daemon).
   Pick: explicit `mindsos server reset-sessions` verb, OR rely
   on absolute TTL, OR document that sessions persist across CLI
   invocations and die only on tester-deletes-server.db.

══════════════════════════════════════════════════════════════════════
PROCESS DISCIPLINE
══════════════════════════════════════════════════════════════════════

Per `user_two_machine_setup.md` + PHASE_MAP §1 amended at Phase 18:

* **Mac**: code editing (Claude session), `git add/commit/push`,
  `gh pr create`, `gh pr merge --squash`, final `git tag` + push.
  Mac has NO docker. Mac Python 3.9.6 — do NOT `pip install -e .`
  on Mac.
* **Linux**: `git pull`, `docker compose --profile test build
  mindsos-test` (pre-build to avoid timeout), all `docker compose
  run --rm mindsos-test pytest ...` runs, all `docker compose run
  --rm mindsos <verb>` CLI exploration.
* **confirm-phase**: either host venv (canonical) OR docker with
  bind-mount `-v "$(pwd)/confirmation_docs:/app/confirmation_docs"`
  (Phase 18 B-18-T3-bindmount lesson — without the `-v`, the doc
  is written inside the container and lost on `--rm`). PHASE_MAP
  §1 row reflects this.

Branch: `phase-19` off `origin/main` tip. Notes: `notes-phase-19.md`
at repo root. Version bump `+phase18 → +phase19` across 9 sites
(6 pkg `__init__.py` + pyproject + docker-compose + manifest.toml).
Tag `phase-19-confirmed` AFTER squash-merge only; verify
`git rev-parse phase-19-confirmed` returns "unknown" BEFORE creating.

Known dep version pin from Phase 18: argon2-cffi>=23.0,<24.0 (in
requirements.in + pyproject.toml + locked requirements.txt). Click
version is 8.2+ (B-18-T2 removed `mix_stderr` kwarg from CliRunner;
use `result.output` not `result.stderr` in CLI tests).

══════════════════════════════════════════════════════════════════════
FIRST RESPONSE EXPECTATIONS
══════════════════════════════════════════════════════════════════════

1. Confirm cited files read; report any missing.
2. Run the pre-impl probe; report findings.
3. Surface 1-3 pre-design pushbacks (with picks) from §Likely
   pushback surfaces OR from the probe.
4. Ask the single highest-value missing-constraint question.

DO NOT write code in the first response. Phase 16's 5-round +
Phase 18's 4-round design pushback ledger pattern is the shape
this project favors — sign off the architecture first, then
implement.

══════════════════════════════════════════════════════════════════════
EXIT CRITERIA
══════════════════════════════════════════════════════════════════════

Phase 19 squash-merges to main; `phase-19-confirmed` tag pushed
AFTER merge; `release.yml` green; GitHub Release created. Phase
19 writes `confirmation_docs/PHASE_20_NEXT_CHAT_PROMPT.md` as
exit artifact (Phase 20 = "Server: reset-admin + last-admin
protection" per Phase 18 PB-27 narrowing; deps Phase 19 only).
══════════════════════════════════════════════════════════════════════
