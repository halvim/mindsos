# Phase 07 — Round-6 Addendum (Design Audit, 2026-05-12)

**Status:** Pre-implementation audit addendum. Captures 53 numbered pushbacks (P26-P78) surfaced across 6 reanalysis rounds AFTER the original design log (`PHASE_07_DESIGN_LOG.md`) was locked. All 53 confirmed with user agreement; this document is the canonical amendment list to apply BEFORE Phase 07 implementation begins.

**Read order for the Phase 07 implementation chat:**

1. `PHASE_07_DESIGN_LOG.md` — original lock (M0-M15 + P1-P25; 2026-05-12 morning).
2. **THIS FILE** — round-6 addendum (P26-P78; 2026-05-12 afternoon resync probe).
3. `PHASE_MAP.md` §5 Phase 07 row (apply amendments per §"Row Amendments" below).

---

## §1 Critical pre-implementation blocker (P37 — resolved)

**Phase 06 was NEVER merged to `origin/main`.** Resync probe 2026-05-12 confirmed:
- `origin/main` HEAD = `6758bb6` = Phase 05d.
- `origin/phase-06` HEAD = `398b7318` = 3 commits ahead (impl + 2 hotfixes).
- No `phase-06-confirmed` tag.
- `PHASE_06_CONFIRMED.md` untracked in Mac working tree (never pushed).

**Phase 07 implementation BLOCKED until Phase 06 ships.** Recovery sequence (executed pre-Phase-07-chat):

1. `git stash push -u -m "phase07-design-work" -- confirmation_docs/PHASE_MAP.md confirmation_docs/PHASE_07_DESIGN_LOG.md confirmation_docs/PHASE_07_NEXT_CHAT_PROMPT.md` (NOTE: `PHASE_06_CONFIRMED.md` stays out of stash — it moves to phase-06 next).
2. `git checkout phase-06 && git pull --ff-only origin phase-06`.
3. `git add confirmation_docs/PHASE_06_CONFIRMED.md && git commit -m "Phase 06 confirmation doc — tester-confirmed at git_sha 398b7318" && git push origin phase-06`.
4. `gh pr create --base main --head phase-06` + `gh pr merge --squash --delete-branch`.
5. `git checkout main && git pull --ff-only origin main`. Verify: `mindsos_instances/` exists; Dockerfile has `COPY mindsos_instances` in both stages; pyproject `packages.find` includes `mindsos_instances*`.
6. `git tag phase-06-confirmed && git push origin phase-06-confirmed`.
7. `gh run watch` Release CI; verify green.
8. `git stash pop` to restore Phase 07 design artifacts on top of post-Phase-06 main. Resolve any `PHASE_MAP.md` conflict between Phase 06 row expansion (from merge) and Phase 07 row addition (from stash). Commit + push to main.

Once steps 1-8 land, branch `phase-07` off the fresh `origin/main` and begin implementation.

---

## §2 Pushback ledger (P26-P78, with user-confirmed picks)

| # | Title | Pick |
|---|---|---|
| P26 | `Node._version` missing in halvim_mindsos slim (audit checked v3 baseline by mistake) | A — patch P10 A scope to 7 core types not 6 |
| P27 | 3 of 4 ADRs (0122/0123/0127) have acceptance criteria depending on layers that don't exist yet (KL, server) | C — flip all 4 AND amend acceptance-criteria line to "Accepted when L1 mechanism ships + `core.md` documents it; consumer integration tracked separately" |
| P28 | ADR-0127's "MissingExpectedVersionError on None for Global" contradicts P7 C / M7 | B — amend ADR-0127 §"Repository API" to "L1 mechanism: bump always; OCC check opt-in via `expected_version`; L0/L2 wrap with policy that raises MissingExpectedVersionError for Globals." Keep exception class in `mindsos_core/exceptions.py` for L0/L2 to raise. |
| P29 | `docs/dev/internals/core.md` does not exist in halvim_mindsos; no `docs/dev/internals/` dir | A — create file from scratch with one "Persistence layer" section |
| P30 | ADRs live at project-root `/Layered Intelligence/docs/decisions/adr/`, not halvim_mindsos | A — edit ADRs in place at project root; add one line to `docs/dev/repo-layout.md` clarifying ADRs live at project root (Model C hybrid) |
| P31 | Row claims "15 indexes from ADR-0123" but ADR-0123 enumerates 11 | A — edit row to "all 13 from ADR-0123 amended (+IntergraphEdge +IntergraphHyperEdge per 05b/05c labels) + 2 hot-path indexes = 15 total"; amend ADR-0123 inline to list 13 indexes |
| P32 | InMemoryClient fidelity gap is structural, not just a marker problem | A — `tests/_shared/graph_equality.py:assert_graphs_equal` asserts client type at call site; raises loud `TypeError` if InMemoryClient passed |
| P33 | `MetagraphRepository.persist` observer (M9) has partial-write hole | A — document in §Risks; tester convention "re-run persist on observer failure; writes idempotent (MERGE)"; file P33 B (WAL-wrapped persist) as Phase 08 future-work |
| P34 | `falkordb` P23 A "latest" pin invites silent version drift | A — pin range `falkordb>=1.6.1,<2.0` in `requirements.in` (ALREADY in place; see P46) |
| P35 | Rollback recipe missing `pip install -e --force-reinstall` step | A — append step to row §Rollback hazards recipe on Mac side |
| P36 | P25 A sentinel-paths count says "14"; actual ≥16 | A — treat "14" as approximation; eager-add every new file at impl time |
| P37 | **Mac worktree is on Phase 05d not Phase 06** (categorical blocker) | A — resync (see §1 above) |
| P38 | `_version` is ALREADY in `RESERVED_PROPERTY_KEYS` (validation.py:54) | A — strike the validation.py edit from Modules-touched; no code change in that file |
| P39 | `MetagraphSchema` persistence not in row §Persistence layout | A — persist `MetagraphSchema` as sibling labeled node `(:MetagraphSchema {name, _props_json?, _version})` with `(:Metagraph)-[:HAS_SCHEMA]->(:MetagraphSchema {name})`; add to §Persistence layout + ADR-0123 index list |
| P40 | `sync --replace` deletion scope unspecified | A — delete only graph-scoped (Graph anchor + child elements + Tombstones); leave dangling MetaEdge/IntergraphEdge refs (surfaced by `verify` as orphan-metaedges); document in §Risks |
| P41 | `RaisesOnNthCall` granularity ambiguous | B — wrapper at Client surface; N counts whole `run_batch` events; "mid-batch crash" narrowed to "fail entire batch from statement N+1"; mid-batch fidelity test deferred to Phase 08 future-work |
| P42 | Bootstrap idempotency assumption needs specific FalkorDB-error filter | B — use `CREATE INDEX IF NOT EXISTS` Cypher form (FalkorDB v4.18.3 supports it; verify in Step 0 per P68) |
| P43 | Per-test FalkorDB graph teardown needs explicit finalizer | A — fixture uses `yield` + `finally: GRAPH.DELETE`; session-scope finalizer sweeps stale `test_*` graphs older than N seconds |
| P44 | `mindsos persistence diagnose` "WAL uncommitted count" is structurally 0 in 07 (no writer consumer) | C — use `WriteAheadLog.begin(...)` directly in test to write an uncommitted entry through the real API |
| P45 | `attach_registry(mg)` Phase 06 carry-forward doesn't exist on disk | A — subordinate to P37; resolves when Phase 06 lands |
| P46 | `falkordb` is ALREADY in requirements.in/.txt + pyproject.toml | A — strike "NEW requirements.in entry" + tester-relock from §Breaking changes and §Risks; reduce P23 A / P34 / P16 A to "verify falkordb stays pinned; no relock needed"; **anticipated hotfix B-07-T-likely-3 is no longer likely** |
| P47 | `pyproject.toml packages.find` does NOT list `mindsos_instances*` (Phase 06 backfill or P37 fallout) | A — add `mindsos_instances*` to `include` in Phase 07 regardless of P37 outcome |
| P48 | docker-compose env passes only HOST+PORT, not PASSWORD/USERNAME/GRAPH | A — add three missing env vars to both `mindsos` and `mindsos-test` services with safe defaults (`${VAR:-}`) |
| P49 | `verify --source=db` requires reconstructing metagraph from FalkorDB but metagraph_loader is Phase 08 | A — Phase 07 ships `--source=db` for `--graph G` only; `--metagraph M` requires `--source=memory`; refuse the combo at CLI with clear error |
| P50 | WAL commit sequence is itself multi-statement; partial-failure recursion | B — ship context-manager API `with wal.entry(operation_id, kind, payload) as e: ...`; raw primitives still accessible for failure-injection tests |
| P51 | CHANGELOG.md last_confirmed_phase skip 05d → 07 if Phase 06 doesn't land first | A — defer until P37 A reveals actual `origin/main` state; linear sequence assumed |
| P52 | `load --graph X` stdout summary format unspecified | A — fixed shape: `name: <X>; graph_id: <uuid>; role: <role>; schema_name: <name|none>; nodes: <count>; edges: <count>; hyperedges: <count>; metagraph_name: <name|none>` — one line per field |
| P53 | Per-test FalkorDB graph creation cost ~5-7 sec total (15 indexes × 100-130 tests) | C — keep M15 per-test isolation; accept cost; revisit at Phase 08 if 900s timeout breaches |
| P54 | Dockerfile may need `COPY mindsos_instances` (P37 fallout) | A — add `COPY mindsos_instances ./mindsos_instances` to both Dockerfile stages in Phase 07 regardless (Phase 06 backfill if needed) |
| P55 | `tests/conftest.py` does not exist; Phase 07 creates it from scratch | A — create with only `pytest_configure(config)` marker registration; minimal |
| P56 | Tombstone-WRITE primitives (P16-pre) have no caller path in 07 | A — document explicitly: "Tombstone-write is a future-consumer-only primitive in 07. No CLI verb produces tombstones." Test via direct repo calls. Soft-delete read-filter (Phase 10) is the first organic consumer. Add §Pass criterion bullet for "tombstone primitive callable; produces `:Tombstone` row" |
| P57 | `OptimisticConcurrencyExhausted` defined at L1 but no Phase 07 raiser | A — ship as definition-only; test asserts: importable, subclass of `PersistenceError`, instantiable; no raise-path test |
| P58 | Cypher rel-type validation at model `__post_init__` AND builder emit | B — builder trusts dataclass invariant; takes typed args; dataclass is single source of truth; test fixtures construct dataclasses, not raw dicts |
| P59 | Doctor `--self-test` FalkorDB-ping error model underspecified | A — pin 5-cell matrix (no section/section ok/refused/auth fail/malformed) in `docs/usage/core/persistence.md`; implement explicitly in `doctor.py` |
| P60 | `MetagraphRepository.persist` ships without CLI hook (programmatic only) | A — add row §Pass criterion bullet documenting programmatic-only status; Phase 08 adds CLI verb |
| P61 | `mindsos persistence inspect-state` output format unspecified | C — plain text default + `--json` opt-in |
| P62 | `_props_json` (ADR-0130) shape unspec; ADR-0130 not in required reads | A — spec inline in `docs/api/core/repositories.md`: `json.dumps(metagraph.properties, sort_keys=True, ensure_ascii=False, separators=(",", ":"))`; cap 1 MB; raise `PersistenceError` if exceeded; read ADR-0130 during Step 0 to verify alignment |
| P63 | `mindsos_cli/app.py` help text says "Phase 05b" (out of date) | A — bump to Phase 07 inline with `register_persistence_app` wiring (backfills Phase 06 implicitly) |
| P64 | `mindsos persistence verify` exit codes unspecified | A — mirror Phase 05d split: 0 clean, 1 CLI usage error, 2 system error (DB unreachable on `--source=db`), 3 drift (any bucket non-empty) |
| P65 | `MetagraphSchema` reusability (Phase 05b 11-A): persist as one shared row, or duplicate? | A — one `(:MetagraphSchema {name, _props_json?, _version})` row per schema name; each `(:Metagraph)-[:HAS_SCHEMA]->(:MetagraphSchema {name})`; sync-ordering refuses graph sync if metagraph-owned AND parent metagraph not yet in FalkorDB; document in §Risks |
| P66 | OCC test layering: unit (InMemoryClient) vs integration (FalkorDB raise) | A — split `test_occ.py` → `test_occ_unit.py` (InMemoryClient: OCC predicate emit + `_version` bump invariant + exception class shape) + `test_occ_integration.py` (`@pytest.mark.integration`: stale-write raises `OptimisticConcurrencyConflict`) |
| P67 | `FalkorConfig.from_env()` partial-env precedence rules | A — per-field precedence: each field independently env-then-manifest-then-default; PASSWORD env-only; doctor `--self-test` line prints resolved values with provenance |
| P68 | `CREATE INDEX IF NOT EXISTS` compatibility unverified | A — Step 0 audit task: probe live sidecar with `CREATE INDEX IF NOT EXISTS` query; if errors, fall back to P42 A (try/catch-specific-exception); if clean, proceed with P42 B |
| P69 | `:Tombstone` anchor uniqueness: per-graph or per-(graph, removed_element)? | A — Phase 07 ships per-(graph, element) tombstone: `(:Tombstone {graph_id, element_id, element_kind, removed_at, removed_by?})`; matches ADR-0133's Phase 10 read-filter model; amend row §Persistence layout |
| P70 | `MetagraphRepository.persist` concurrency: no metagraph-level lock | A — document; no code in 07; per-user mutex (Server Layer) is the lock; file metagraph-level concurrent-persist lock as Phase 18+ future-work |
| P71 | `load --to-json` overwrites silently; no `--force` flag | A — `--to-json` requires `--force` if target file exists; otherwise refuse with clear error; two-flag pattern matches Phase 05a precedent |
| P72 | `verify --source=db` reports stale FalkorDB state as drift; design choice or bug? | A — document that `--source=db` and `--source=memory` may report different findings (different snapshots); add to §Risks; drift detection is Phase 08+ future-work |
| P73 | Schema vocabulary round-trip during `sync --graph X`: writer pushes attached Schema or just element type_name strings? | B — sync writes Graph elements only; Schema stays JSON-only; FalkorDB stores `type_name` strings without vocab validation; document the asymmetry; "Graph Schema FalkorDB round-trip" filed as Phase 09+ future-work |
| P74 | `.github/workflows/phase-ci.yml` does NOT currently boot FalkorDB sidecar; integration tests will fail in CI | A — Step 0 audit `.github/workflows/phase-ci.yml`; add `services: falkordb:` GitHub Actions block OR `docker compose --profile test up -d falkordb` before pytest; add to row §Modules-touched |
| P75 | Doctor `--self-test` ordering: parity check vs FalkorDB ping | B — run all checks, collect failures, exit non-zero with combined report (tester ergonomics > fail-fast) |
| P76 | `inspect-state` / `diagnose` / `verify --source=db` failure mode if no `[falkordb]` section | A — pre-check refuses with clear error: *"`[falkordb]` manifest section missing and no `FALKORDB_HOST` env set. Configure one and retry."* Exit 1 |
| P77 | `graph_loader._props_json` defensive read is dead code in Phase 07 (P9 C skipped writer) | B — strip the defensive read; add when writer ships (Phase 10 likely) |
| P78 | `MetagraphRepository.persist` partial-state failure-mode matrix | A — re-confirm P33 A; no scope change; retry idempotent via MERGE |

---

## §3 Row Amendments to apply (PHASE_MAP.md §5 Phase 07)

Implementation chat's Step 0 first action: edit the Phase 07 row to fold these 53 picks. Listed by row §section.

### §Locked decisions

- Strike `M3` "ADR file edits land in 07" — REPLACED by P27 C: ADRs 0122/0123/0126/0127 flip to Accepted AND acceptance-criteria lines amended to read "Accepted when L1 mechanism ships + `core.md` documents it; consumer integration tracked separately." ADR-0127 also amends §"Repository API" per P28 B.
- Add `M16` (new): "Resync prerequisite — Phase 06 MUST land on `origin/main` before Phase 07 implementation begins (per P37 A, §1 above)."
- Edit `P10 A` scope: 7 core element types not 6 (Node added per P26 A).
- Strike "extends `RESERVED_PROPERTY_KEYS` with `_version`" — already present at `validation.py:54` (per P38 A).
- Edit `P23 A` / `P34` / `P16 A` to "verify falkordb stays pinned at `>=1.6.1,<2.0`; no relock needed" (per P46 A).

### §Features in scope

- WAL ships context-manager API `with wal.entry(...)` as primary surface (per P50 B).
- `verify --source=db` for `--graph G` only; `--metagraph M` requires `--source=memory` (per P49 A).
- `MetagraphSchema` persists as sibling labeled node (per P39 A + P65 A).
- `MetagraphRepository.persist` documented as programmatic-only in 07; no CLI verb (per P60 A).

### §Modules touched

- Strike `mindsos_core/schema/validation.py` (no edit — `_version` already reserved) per P38 A.
- Add `pyproject.toml` `packages.find` includes `mindsos_instances*` (P47 A — Phase 06 backfill).
- Add `Dockerfile` `COPY mindsos_instances ./mindsos_instances` in both stages (P54 A — Phase 06 backfill safety).
- Add `docker-compose.yml` env vars `FALKORDB_PASSWORD` / `FALKORDB_USERNAME` / `FALKORDB_GRAPH` to both services (P48 A).
- Add `.github/workflows/phase-ci.yml` — FalkorDB sidecar boot or services block (P74 A).
- `tests/conftest.py` — NEW (project-wide first conftest; marker registration only per P55 A).
- `mindsos_cli/app.py` — help text bump to Phase 07 (P63 A; also Phase 06 backfill).

### §Persistence layout

- Index count phrasing: "13 from ADR-0123 amended (+IntergraphEdge +IntergraphHyperEdge per 05b/05c labels) + 2 hot-path indexes = 15 total" (P31 A).
- Add `:MetagraphSchema {name, _props_json?, _version}` row + `:HAS_SCHEMA` edge from `:Metagraph` (P39 A + P65 A).
- Amend `:Tombstone` row to per-(graph, element): `(:Tombstone {graph_id, element_id, element_kind, removed_at, removed_by?})` (P69 A).

### §Automated tests

- Split `test_occ.py` → `test_occ_unit.py` + `test_occ_integration.py` (P66 A).
- `test_cypher_builders.py` — builder takes typed dataclasses; no raw-dict path (P58 B).
- `test_bootstrap.py` — uses `CREATE INDEX IF NOT EXISTS` Cypher form (P42 B).
- Step 0 sub-task: verify FalkorDB v4.18.3 + driver 1.6.1 supports `CREATE INDEX IF NOT EXISTS` (P68 A).

### §Risks

- Add: `MetagraphRepository.persist` observer partial-write hole; retry idempotent via MERGE (P33 A).
- Add: `sync --replace` leaves dangling MetaEdge/IntergraphEdge refs after graph-scoped delete; surfaced by `verify` (P40 A).
- Add: `--source=memory` and `--source=db` are different snapshots; clean DB may still drift from memory (P72 A).
- Add: graph sync ordering — refuses if metagraph-owned AND parent metagraph not yet in FalkorDB (P65 A consequence).

### §Rollback hazards

- Append step to recovery recipe: `pip install --user -e . --force-reinstall --no-deps --break-system-packages` on Mac after `git checkout phase-06-confirmed` (P35 A).

### §Doc sections

- `docs/dev/internals/core.md` — NEW file + NEW directory (P29 A).
- `docs/api/core/repositories.md` — spec `_props_json` encoding inline (P62 A).
- `docs/usage/core/persistence.md` — 5-cell doctor self-test matrix (P59 A).
- `docs/dev/repo-layout.md` — one line clarifying ADRs live at project root (P30 A).

### §Breaking changes

- Strike "NEW `requirements.in` entry: `falkordb`" — already pinned (P46 A).
- Strike "Lockfile sha256 changes; tester re-runs `tools/lock.sh`" — no relock needed (P46 A).

### §Final amendments (append items)

- 47. P26-P78 round-6 addendum applied (53 pushbacks; see this file's §2 ledger).
- 48. Phase 06 must ship before Phase 07 starts (P37 A).
- 49. ADRs 0122/0123/0126/0127 flip to Accepted with acceptance-criteria line amendments (P27 C).
- 50. ADR-0127 §"Repository API" amends per P28 B.
- 51. Anticipated hotfix B-07-T-likely-3 (lockfile sha256 mismatch) is REMOVED — no relock needed.

---

## §4 Step 0 audit additions (beyond original prompt)

Implementation chat's Step 0 pre-implementation audit pass now must:

1. **Resync verification (P37).** Confirm `origin/main` HEAD includes Phase 06 squash-merge. Verify `mindsos_instances/` directory exists locally; `Dockerfile` has `COPY mindsos_instances` in both stages; `pyproject.toml packages.find` includes `mindsos_instances*`. If any missing → halt; resync per §1 not complete.
2. **`_version` presence audit (P26).** Confirm `Node._version` field absence in `mindsos_core/models/node.py` (will be added in 07).
3. **`falkordb` dep audit (P46).** Confirm `requirements.in` has `falkordb>=1.6.1,<2.0`; `requirements.txt` has `falkordb==1.6.1`; `pyproject.toml dependencies` lists `falkordb`; `manifest.toml requirements_txt_sha256` matches current `requirements.txt`. If matches → no relock action.
4. **`CREATE INDEX IF NOT EXISTS` probe (P68).** Run probe query against live sidecar; record outcome.
5. **CI workflow audit (P74).** Inspect `.github/workflows/phase-ci.yml`; identify FalkorDB sidecar wiring (or absence).
6. **`tests/conftest.py` audit (P55).** Confirm absence (Phase 07 creates).
7. **`docs/dev/internals/` audit (P29).** Confirm absence of directory.
8. **ADR-0130 read (P62).** Read ADR-0130 in full to verify `_props_json` encoding spec alignment.
9. **`_version` reserved-key already present (P38).** Confirm `RESERVED_PROPERTY_KEYS` at `schema/validation.py:54` includes `_version`.
10. **`pyproject.toml packages.find` audit (P47).** Confirm `mindsos_instances*` included (Phase 06 fallout). If missing on post-resync main → fix as Phase 06 backfill in 07.

Report findings as a brief audit summary (file + line citations + any anomalies). Do NOT write any new code until user signs off on Step 0 report.

---

*End of PHASE_07_ROUND_6_ADDENDUM.md. Implementation chat consumes this + PHASE_07_DESIGN_LOG.md + PHASE_MAP.md §5 Phase 07 row (post-amendments) + PHASE_07_NEXT_CHAT_PROMPT.md.*
