══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 21 (Server: audit log reader)
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

Phase 21 scope is locked at PHASE_MAP §Phase 21 row. Read the row;
do not re-derive scope from training.

══════════════════════════════════════════════════════════════════════
REQUIRED READING (in this order)
══════════════════════════════════════════════════════════════════════

1. **`MEMORY.md`** — auto-loaded at chat start. Every `feedback_*`
   entry is a hard rule. Pay special attention to:
   * `feedback_pushback_format_with_picks.md`
   * `feedback_pre_impl_probe_check_existing_modules.md`
   * `feedback_l1_api_signature_probe_before_writing_tests.md`
   * `feedback_phase_baseline_literal_audit.md`
   * `feedback_test_image_rebuild_after_source_change.md`
   * `feedback_stale_local_tag_silent_overwrite_failure.md`
   * `feedback_batch_fix_dont_iterate.md`
   * `feedback_sandbox_vs_mac_git_separation.md`
   * `user_two_machine_setup.md` (Mac/Linux split + commands)

2. **`halvim_mindsos/confirmation_docs/PHASE_MAP.md`** §0 (load-bearing
   read rule) + §1 (settled cross-cutting decisions — read in full) +
   §Phase 19 (sessions; audit-callers shipped here) + §Phase 20
   (reset-admin; new admin.py module + first-fires of EVT_KILL_SESSION
   + EVT_ADMIN_ENABLE_USER) + §Phase 21 (own row — scope source) +
   §Phase 22 (admin ops; confirm Phase 21 doesn't cross into P22's
   admin_kill_session / admin_disable_user wiring).

3. **`halvim_mindsos/confirmation_docs/PHASE_20_DESIGN_LOG.md`** —
   most recent design log. Read §0 scope summary + §2 final locks
   table + §3 cross-chat dependencies (Forward subsection — Phase 20
   → Phase 21 deltas) + §4 ADR delta + §6 out-of-scope. This is the
   durable contract for what Phase 21 inherits — especially the
   audit-row payload shapes that Phase 21's reader needs to
   deserialize.

4. **`halvim_mindsos/confirmation_docs/PHASE_20_CONFIRMED.md`** —
   ground truth for the actually-shipped state at Phase 20 tag.
   Tester notes section captures any B-20-T* hotfixes + test counts
   + manual smoke. If design log and confirmation doc disagree, the
   confirmation doc wins (post-impl evidence).

5. **ADRs** at `/Layered Intelligence/docs/decisions/adr/`. Read in
   full at first probe — Phase 21 consumes:
   * **ADR-0013** (audit constants + Session.for_testing).
     §Decision says "Admins query audits via
     `admin_query_audit(session, *, actor=None, event=None,
     target=None, since=None, limit=...)`, gated on
     `CAN_VIEW_AUDIT_LOG`." Phase 21 ships this verb. §Decision also
     names `extra_json` filtering via SQLite `json_extract` — Phase
     21 picks whether to expose extra_json filtering at v1 or defer.
   * **ADR-0002** (capability model). Phase 21 enforces
     `CAN_VIEW_AUDIT_LOG` per the §Decision capability roster + Phase
     18 §amendment-1 strict-USER_CAPS lock. The cap is in `ADMIN_CAPS`
     only at v1.
   * **ADR-0012** (+ §am1 + §am2). Phase 21's reader is the first
     external consumer of Phase 20's EVT_RESET_ADMIN /
     EVT_KILL_SESSION / EVT_ADMIN_ENABLE_USER rows. PB-BB's
     denormalized `sessions_killed` field on EVT_RESET_ADMIN.extra_json
     is intended to save the reader from JOIN/COUNT against
     EVT_KILL_SESSION — Phase 21 picks whether to surface this as a
     "reset-admin summary" query or treat all events uniformly.
   * **ADR-0010** (layer isolation). Phase 21 is L0 only; no KL /
     L2-L4 imports.

══════════════════════════════════════════════════════════════════════
PRE-IMPL PROBE (run BEFORE any design pushbacks)
══════════════════════════════════════════════════════════════════════

```
cd halvim_mindsos
# Verify Phase 20 squashed + tagged at main tip.
git fetch origin && git log --oneline origin/main | head -5
git rev-parse phase-20-confirmed 2>&1 | head -1

# Verify Phase 20 surfaces intact.
ls mindsos_server/admin.py                                 # Phase 20 — should exist
grep -n "reset_admin\|ResetAdminResult" mindsos_server/admin.py | head -10
grep -n "UserNotFoundError\|NotAnAdminError" mindsos_server/errors.py | head -5

# Verify audit substrate from Phase 18.
grep -n "^def write_audit\|class AuditRow\|^EVT_" mindsos_server/audit.py | head -20
grep -n "audit" mindsos_server/_schema.py | head -10

# Verify CAN_VIEW_AUDIT_LOG already declared (Phase 18 PB-4).
grep -n "CAN_VIEW_AUDIT_LOG" mindsos_server/capabilities.py mindsos_server/__init__.py

# Verify Session shape (Phase 18 PB-33 + Phase 19 LoginResult).
grep -n "^class Session\|capabilities\|has(" mindsos_server/session.py | head -10

# Verify nothing Phase 21-shaped already shipped.
grep -rn "admin_query_audit\|query_audit\|AuditQuery" \
    mindsos_server/ mindsos_cli/ 2>/dev/null | head -10

# Version baseline.
grep -rn '__version__ = "0\.0\.0+phase' --include="*.py" mindsos_*/__init__.py
```

If `mindsos_server/admin.py` already has `admin_query_audit` or
anything reader-shaped already exists, surface as a reframe pushback
(Phase 15b / Phase 17 retirement precedents).

══════════════════════════════════════════════════════════════════════
LIKELY PUSHBACK SURFACES (probe before locking scope)
══════════════════════════════════════════════════════════════════════

Each pushback ends with a pick. Final round closes with a Picks
summary.

1. **Function placement — `admin.py` vs new `audit_reader.py`?**
   Phase 20 PB-Z established `mindsos_server/admin.py` as the home
   for admin verbs. `admin_query_audit` fits the "admin verb"
   pattern but is read-only (no mutation, no session-killing).
   Picks: (a) extend admin.py (PB-Z precedent — admin verbs cluster);
   (b) new mindsos_server/audit_reader.py module (separates read /
   write concerns); (c) extend audit.py itself (where the writer
   lives — co-locate reader with writer).

2. **Query parameter shape — kwargs vs `AuditQuery` dataclass?**
   ADR-0013 §Decision lists kwargs: `actor=None, event=None,
   target=None, since=None, limit=...`. ADR doesn't lock the shape;
   five-kwarg signature could grow ugly with future filters
   (until, limit, offset, extra_json_filter). Picks: (a) literal
   kwargs per ADR; (b) `AuditQuery` frozen dataclass packing all
   filters; (c) kwargs at P21 with comment "convert to dataclass at
   P22 if filter set grows."

3. **Pagination model — `limit + offset` vs cursor-based (id > X)?**
   Audit table is monotonically increasing `id INTEGER PRIMARY KEY`.
   Cursor-based pagination (`WHERE id > last_seen_id ORDER BY id
   LIMIT N`) is index-friendly and stable under concurrent writes.
   limit+offset has correctness issues under writes between pages.
   Picks: (a) limit+offset (simpler; CLI-only product has trivial
   write rate); (b) cursor-based (future-proofs for HTTP daemon);
   (c) both — limit + optional `--after-id` cursor.

4. **`since` / `until` accepted formats.** ISO-8601 UTC with ms
   per Phase 18 PB-35 audit row format. Accept multiple? Picks:
   (a) ISO-8601 only, strict; (b) ISO-8601 + relative ("24h ago",
   "yesterday"); (c) ISO-8601 + Unix timestamps. Defer (b/c) to
   future if anyone asks.

5. **`extra_json` filtering — ship at v1 or defer?**
   ADR-0013 §Decision: "queries on extra_json keys are SQLite-native
   via json_extract". Phase 20 PB-BB denormalized `sessions_killed`
   into EVT_RESET_ADMIN.extra_json. A "reset-admin summary" query
   (`extra.sessions_killed > 0`) is the immediate consumer. Picks:
   (a) defer — v1 ships only top-level column filters (actor/event/
   target/since/until); (b) ship one parametric `--extra KEY=VALUE`
   flag mapping to `json_extract(extra_json, '$.KEY') = ?`; (c) ship
   a richer JSON-path filter language.

6. **Pretty-print shape for plain CLI output.**
   Single-line per row vs multi-line "block per row" vs columnar
   table? Audit rows have variable-width `extra_json`. Columnar
   needs col-width estimation. Picks: (a) one row per line, tab-sep:
   `ts<TAB>actor<TAB>event<TAB>target<TAB>extra_json_oneline`;
   (b) rich columnar via Rich (Typer dep ships it); (c) multi-line
   block (3 lines per row).

7. **`admin_query_audit` returns what type?**
   List of `AuditRow` dataclasses vs list of dicts vs raw sqlite3
   rows? Picks: (a) `AuditRow` frozen dataclass (mirrors Phase 18
   User pattern); (b) list of dicts (JSON-serialization friendly);
   (c) iterator/generator (large-result paging — premature for v1).

8. **Stats verb — separate or filter on the same verb?**
   PHASE_MAP §21 Features list "audit stats" alongside "audit query."
   Stats = count per event / per actor / per day? Picks: (a) separate
   `admin_audit_stats(...)` function + `mindsos server admin
   audit-stats` CLI verb; (b) `--stats` flag on the same verb (mode
   toggle); (c) defer stats entirely to a future phase — v1 ships
   just the row reader.

9. **CLI verb naming.** `mindsos server admin query-audit` vs
   `mindsos server audit list` vs `mindsos server admin audit-log`?
   Phase 20 shipped `mindsos server reset-admin` (no `admin`
   subgroup). Phase 22 will add `admin promote-user` /
   `admin demote-user` / etc. Consistency vs verb-grouping. Picks:
   (a) flat: `mindsos server query-audit` (matches reset-admin
   pattern); (b) grouped: `mindsos server admin query-audit`
   (anticipates P22 admin subgroup); (c) audit-specific:
   `mindsos server audit list` + `mindsos server audit stats`
   (own subgroup).

10. **Session injection for capability check.**
    `admin_query_audit(session, ...)` — first verb to actually
    consume a Session at the function-call boundary (Phase 19
    `kill_my_own_sessions(conn, user_id, password, ...)` takes
    credentials not session). Picks: (a) session as first positional;
    (b) session as kwarg `*, session`; (c) implicit via
    Session.for_testing-style helper (anti-pattern).

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
* **confirm-phase**: host-native is canonical (per Phase 20
  experience — docker invocation can't shell out to re-run pytest
  since no docker binary inside container; produces "no-tests-dir"
  placeholder + spurious WARNING). Run from a Python ≥ 3.12 venv
  on the Linux host (`pip install -e . --user
  --break-system-packages` after pulling phase-NN branch).

Branch: `phase-21` off `origin/main` tip. Notes: `notes-phase-21.md`
at repo root. Version bump `+phase20 → +phase21` across 9 sites /
11 lines (6 pkg `__init__.py` + pyproject + docker-compose 2× +
manifest.toml 2×). Tag `phase-21-confirmed` AFTER squash-merge only;
verify `git rev-parse phase-21-confirmed` returns "unknown" BEFORE
creating.

**Path (a) workflow validated at Phase 20** — land all impl batches
in ONE commit on phase-NN, skip per-batch round-trips (squash
collapses them anyway). Saves 3 Mac round-trips per phase.

Phase 20 ADR amendments at ship: ADR-0012 §am2 only (6-change
batch). Phase 21 may amend ADR-0013 §am2 for the
admin_query_audit signature specifics + ADR-0002 §am2 if
CAN_VIEW_AUDIT_LOG enforcement shape needs documenting — phase chat
decides at design time.

══════════════════════════════════════════════════════════════════════
FIRST RESPONSE EXPECTATIONS
══════════════════════════════════════════════════════════════════════

1. Confirm cited files read; report any missing.
2. Run the pre-impl probe; report findings.
3. Surface 1-3 pre-design pushbacks (with picks) from §Likely
   pushback surfaces OR from the probe.
4. Ask the single highest-value missing-constraint question.

DO NOT write code in the first response. Phase 18's 4-round + Phase
19's 3-round + Phase 20's 4-round design pushback ledger pattern is
the shape this project favors — sign off the architecture first,
then implement. Phase 21 scope is narrow (single read-only verb +
optional stats); likely 2-3 rounds suffice.

══════════════════════════════════════════════════════════════════════
EXIT CRITERIA
══════════════════════════════════════════════════════════════════════

Phase 21 squash-merges to main; `phase-21-confirmed` tag pushed
AFTER merge; `release.yml` green; GitHub Release created. Phase
21 writes `confirmation_docs/PHASE_22_NEXT_CHAT_PROMPT.md` as
exit artifact (Phase 22 = "Server: admin ops" — admin user mgmt
verbs + admin_kill_session + cross-user read; consumes
`_assert_not_sole_admin` helper + `LastAdminError` deferred from
Phase 20 per PB-B).
══════════════════════════════════════════════════════════════════════
