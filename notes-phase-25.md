# Phase 25 — implementation notes

Phase: 25
Phase title: Server cross-user-read substrate (`read_other_local` + `LocalPersister` Protocol + `SessionProtocol` in KL)
Branch: `phase-25` (cut from `origin/main` HEAD `a6bd4fd` Phase 24 squash)
Date: 2026-05-23
Design log: `confirmation_docs/PHASE_25_DESIGN_LOG.md`
Tag at ship: `phase-25-confirmed`

## §1 Scope shipped

* **`mindsos_knowledge/types.py`** — NEW; `SessionProtocol` per ADR-0040 §am1 first ship. Zero `mindsos_server` imports.
* **`mindsos_server/persistence/`** — NEW sub-package; `LocalPersister` Protocol + `InMemoryLocalPersister` per ADR-0011 §am2 (Metagraph at v1; MetagraphDump defers; `delete -> bool`; `fail_save_for` test hook).
* **`mindsos_server/orchestrator.py`** — NEW; `InstallRecord` dataclass + `read_other_local` ctx mgr + `_install_for` / `_release` / `_node_counts` private helpers + `reset_state_for_tests`. Module-level `_installed_locals` + `_install_lock` + `_mutex_registry` (free-function ethos per PB-38).
* **`mindsos_server/errors.py`** — extended; `FlushFailedError` + `UserHasPromotionHistoryError`.
* **`mindsos_server/admin.py`** — extended; `hard_delete_user` gains UNION pre-check + `persister: LocalPersister | None` kwarg + `local_dump_existed` audit key. NEW `read_other_local_summary` + `ReadOtherLocalSummary` + `RoleGraphSummary` dataclasses. `HardDeleteUserResult` extended with `local_dump_existed` as 6th field.
* **`mindsos_server/audit.py`** — `EVT_CROSS_USER_READ_INSTALL` payload-shape docstring locked per PB-31.
* **`mindsos_server/__init__.py`** — exports updated.
* **`mindsos_cli/commands/server.py`** — NEW verb `mindsos server admin read-local`; `_resolve_persister` + `_resolve_kl` helpers; `_admin_exit_for` extended (UserHasPromotionHistoryError → 10); hard-delete-user verb passes persister kwarg.
* **6 ADR amendments** — 0008 §am2 + 0011 §am2 + 0013 §am3 + 0040 §am1 + 0006 §am2 + 0114 §am4. ADR-0125 unchanged.
* **9-site version bump** `+phase24 → +phase25`.
* **16 test files** at `tests/phase_25/` (15 tests + conftest).
* **0 schema bumps** (`_SCHEMA_VERSION` stays at 4).

## §2 Design-log §am-impl addendum — Round 6 + Round 7 picks reconciled

The design log §5 implementation references contained 7 literals that drifted from probe-verified reality. The impl reconciled each via Round 6 (5 picks) and Round 7 (2 picks) pre-impl pushbacks; the user accepted all 7. Captured here for the design log §am-impl trail:

| # | Pick | Design log §5 said | Impl shipped | Why |
|---|---|---|---|---|
| R6-01 (a) | extend `mindsos_server/errors.py` | NEW `mindsos_server/exceptions.py` | extended `errors.py` | actual codebase has `errors.py` with 7 importing sites; the `exceptions.py` literal was a stale design-log token. |
| R6-02 (a) | iterate via `mg.graphs.values()` + role attr; build dict locally | `mg.graphs_by_role.items()` | inline dict-comp in `read_other_local_summary` + `_node_counts` | `Metagraph` has `self.graphs: Dict[str, Graph]` keyed by `graph_id`; `graphs_by_role(role)` is a method on `MetagraphView` (the KL wrapper), not an attribute on raw `Metagraph`. |
| R6-03 (a) | autouse fixture resets `_installed_locals` AND `_mutex_registry`; fresh `KL.bootstrap()` per test | "autouse: reset `_installed_locals`" | conftest resets both registries + uses fresh `KL.bootstrap()` per test | KL's `install_local_metagraph` raises `AlreadyInstalledError` if `KL._locals[user_id]` exists; orchestrator owns the install path, but tests must reset both views to avoid bleed. |
| R6-04 (a) | use `kl.local_metagraph(user_id)` for cold-start (canonical name + auto-ensured roles) | `Metagraph(name=f"local_{user_id}")` | `_install_for` uses `kl.local_metagraph(user_id)` on no-dump path; `kl.install_local_metagraph(dump)` on dump path | KL's canonical name is `local_knowledge:<user_id>` via `_local_metagraph_name`; future SQLite persister will key graphs by name and the `f"local_{user_id}"` literal would break roundtrip. |
| R6-05 (a) | `_require_or_audit` at top of `read_other_local_summary`; keep ctx-mgr inner check | summary calls users SELECT first | summary pre-checks cap BEFORE users SELECT | non-admin probing a nonexistent target gets exit 3, not exit 2; plugs the existence-leak (Phase 21 admin_query_audit precedent). |
| R7-01 (a) | append `local_dump_existed` as 6th field; preserve `ts` | 5-field shape (`ts` omitted) | 6-field `HardDeleteUserResult` with `(target_user_id, prior_role, was_disabled, sessions_killed, ts, local_dump_existed)` | Phase 22 dataclass already had `ts: str` as 5th field; design log §5 sample omitted it. |
| R7-02 (a) | `conn.commit()` after `write_audit` inside `read_other_local` ctx mgr | (no commit shown) | explicit `conn.commit()` after EVT_CROSS_USER_READ_INSTALL write | `write_audit` per ADR-0013 leaves commit to caller; a read-only summary flow would silently drop the audit row on connection close. Phase 21 `admin_query_audit` precedent. |

Plus one no-op clarification:

* **ADR-0008 Status** — design log §4 said "Proposed → Accepted" at Phase 25 ship; the file was already `Accepted` from §am1 (which had pre-flipped). §am2 is the load-bearing change at Phase 25; no Status mutation needed.

## §3 Smoke results

Host-native syntax check (`python3 -m py_compile`): GREEN for all 9 prod files + 16 test files.

Host-native test run: **TODO [Linux]** — sandbox has Python 3.10 (no `datetime.UTC`); run on Linux host with `python3 -m pytest tests/phase_25/ -v` then `python3 -m pytest tests/ -v` (cumulative).

Docker test run: **TODO [Linux]** — rebuild `mindsos-test` image then `docker compose run --rm mindsos-test pytest tests/phase_25/ tests/`.

Manual smoke: **TODO [Mac or Linux]** — host-native per `feedback_smoke_harness_host_native.md`. Recipe:
```
mindsos server bootstrap admin-caller   # input: adminpw
mindsos server login admin-caller       # input: adminpw
# Create target user
echo "alicepw" | mindsos server admin promote-user alice  # only if alice exists; otherwise insert via direct DB or future create-user verb
mindsos server admin read-local alice                     # expect exit 0; per-role counts
mindsos server admin read-local nonexistent               # expect exit 2 UserNotFoundError
mindsos server admin hard-delete-user some-clean-user     # expect exit 0; local_dump_existed=False
mindsos server admin hard-delete-user some-admin-with-promotion-history  # expect exit 10 UserHasPromotionHistoryError
```

## §4 Hotfix ledger

(Populated during ship as needed.)

| ID | Symptom | Fix | Files | Notes |
|---|---|---|---|---|
| (none yet) | | | | |

## §5 Ship checklist progress

* [x] Phase 25 source written.
* [x] Phase 25 tests written.
* [x] Version bump 9 sites.
* [x] 6 ADR amendments appended.
* [x] notes-phase-25.md at repo root (this file).
* [ ] Host-native tests GREEN (`tests/phase_25/` then cumulative `tests/`). **[Linux]**
* [ ] Docker tests GREEN. **[Linux]**
* [ ] Manual smoke. **[Mac or Linux]**
* [ ] `git status` review on Mac; `git add` everything (including ADR amendments + notes-phase-25.md + Phase 25 design log).
* [ ] Open PR against `main` from `phase-25`.
* [ ] CI green (`release.yml`).
* [ ] Squash-merge PR.
* [ ] `git tag phase-25-confirmed <squash-sha>` + push.
* [ ] CI re-runs against tag green.
* [ ] `confirm-phase --phase 25 --notes-file notes-phase-25.md` generates `confirmation_docs/PHASE_25_CONFIRMED.md`.
* [ ] Commit + push the confirmation doc.

## §6 Implementation references

See `confirmation_docs/PHASE_25_DESIGN_LOG.md` §5 for the canonical scope; the §am-impl addendum above documents where this ship's literals diverge from §5 and why.
