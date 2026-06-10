# MAINTENANCE_CHAT — log (opened 2026-06-09)

Stream-A-style maintenance commits on `main` (A0/A9 precedent, HANDOFF §3.1.10).
Not a numbered phase. No 9-surface manifest bump expected (no bump surface touched).
Prereqs verified at open: tag `phase-49-confirmed` present; `main` HEAD = `cc8a7f8`
(the Phase-49 confirm commit).

## Slate (5 items + M0 housekeeping)

| Item | Scope | Status |
|---|---|---|
| M0 | Land the uncommitted Phase-49 ship-closure doc amendments found in the working tree at open (HANDOFF §3.1.20-22 + last-updated banner; CLAUDE.md status; PHASE_MAP 47/48/49 → SHIPPED; L3_FUTURE_WORK L3-57 resolved + L3-58 added; cookbook_routing end-to-end row → Shipped). Authored in the 2026-06-09 reanalysis session, never committed. Doc-only, consistent with the confirmed tags. | **DONE** `5238006` |
| M1 | L0-24 import-cycle fix: `mindsos_admin/promotion.py:68` → lazy import inside `propose_for_promotion` (pattern `mindsos_core/persistence/client.py:140`); delete `tests/phase_44/conftest.py` band-aid; isolated subsets + cumulative gate. | **DONE** `b5a6ef1` (gate pending on host) |
| M2 | L0-25 live-Falkor round-trip coverage for `FalkorDBLocalPersister` (save→load + scoped delete). Probe first; in-vs-route decision recorded below. | **DONE** `a21d5cd` (live run pending on host) |
| M3 | L0-26 node-value serialization contract — ADR, decide-and-document ONLY. Implementation routed to skill-acquisition slot 1 (first consumer). | **DONE** `a3f6e18` (ADR-0182) |
| M4 | L3_FUTURE_WORK routing record: CapacityContext read-path migration (union-drop). Contract authority = SKILL_ACQUISITION R0; mechanical migration = WSD slot 1. Doc-only. | **DONE** `29164f8` (L3-59) |
| M5 | `projects/ANALYSIS_DELTA_2026-06.md` addendum + banner pointers in `projects/wsd/ANALYSIS.md` + `projects/fol/ANALYSIS.md`. Every claim grep-verified against shipped code (NPB11-META). | **DONE** `d2ca23b` |

## Decisions

- **M1 scope note:** the L0-24 item text predates Phase 49; `tests/phase_49/conftest.py`
  carried a *mirror* of the phase_44 warm-up band-aid. Both removed (same fix,
  same rationale). The lazy import lands inside `propose_for_promotion` (the
  only `admin_tx` call site — AST-verified zero remaining top-level
  `mindsos_server.admin` imports in `mindsos_admin/`).
- **M2 in-vs-out (R0):** SHIP HERE. Probe result: authoring needs only the
  existing `tests/_shared` substrate (`falkor_client` per-test fresh-graph
  fixture + `assert_metagraphs_equal`); no new harness. Tests live in NEW
  `tests/maintenance/` (phase dirs are frozen gate snapshots; maintenance
  items get their own home). **Sweep-audit split per the chat prompt:** the
  round-trip + scoped-delete + idempotency tests are gate-blocking; the
  orphan-scan sweep-completeness probe ships `xfail(strict=False)` — a pass is
  evidence, a failure is the known best-effort-sweep gap, and the full
  metaedge/metahyperedge/XRef sweep audit is **routed to WSD installation**
  (L0-25 closure marker reflects the split).
- **Environment note:** the Cowork sandbox is py3.10 (repo requires ≥3.12) with
  no FalkorDB sidecar — all M1/M2 verification here is static (AST + grep);
  the isolated subsets + cumulative gate + live integration run on the gate
  host at closure (pair-execution pattern, Phase 43 precedent).

- **M3:** Option 1 (node-level `_value_json`, extending the ADR-0130 JSON-encoding
  pattern) picked over decomposed-nodes + blob-store; rationale + reversal trigger
  in ADR-0182. Zero L0 code shipped (decide-and-document; ADR-0181 precedent).
  Sentinel test pins the contract surface AND asserts no implementation shipped.
- **M4:** routing recorded as L3-59 (contract authority SKILL_ACQUISITION R0;
  mechanical migration WSD slot 1).
- **M5:** all six flagged findings grep-verified and absorbed; re-grep results:
  WSD ANALYSIS 3 stale-vocab hits (lines 88/146/172 — resident ×2,
  `add_type_compat`), FOL ANALYSIS clean (zero hits for TYPE_COMPAT / discovery /
  PlanRun / bare-`memories` / resident). `InterGraphEdge` casing NOTED + routed to
  SKILL_ACQUISITION R0, not resolved. Beyond the flagged list, the delta also
  absorbs: 3 WSD L2 role-graph B-rows → shipped Phase 43; FOL B20 typed
  CapacityContext → shipped Phase 42; FOL C5 concurrency → re-grounded against
  the Phase 46/47 worker model; FOL B19 blob-store split (rejected for node
  values per ADR-0182; survives for large model artefacts).
- **Closure scope note:** the orphaned untracked `*_NEXT_CHAT_PROMPT.md` files
  (MAINTENANCE, SKILL_ACQUISITION, PHASE_41/46/49) are landed in the closure
  commit — repo convention tracks prompt files, and HANDOFF/CLAUDE.md reference
  them; the handoff target (SKILL_ACQUISITION prompt §AMENDMENT) depends on the
  M3 + M5 artifacts shipped above. ROBOT_DEMO_* / DEMO_* files left untracked
  (separate workstream).

## Commits

| Commit | Item |
|---|---|
| `5238006` | M0 — land Phase-49 ship-closure doc amendments + open this log |
| `b5a6ef1` | M1 — L0-24 lazy `admin_tx` import + band-aid removals |
| `a21d5cd` | M2 — L0-25 live round-trip + scoped-delete tests (`tests/maintenance/`) |
| `a3f6e18` | M3 — ADR-0182 + sentinel test |
| `29164f8` | M4 — L3-59 routing record |
| `d2ca23b` | M5 — ANALYSIS delta addendum + banners |
| (closure) | L0_FUTURE_WORK markers + this log + orphaned prompt files |

## Gate (to run on the gate host — sandbox is py3.10, no sidecar; repo requires ≥3.12)

Per HANDOFF §9 ship-env invariants (confirm the gate checkout's HEAD sha FIRST —
Phase 49 forensic note; `python3`; no `gh`/`mindsos` CLI):

1. `git rev-parse HEAD` on the gate checkout == the closure commit.
2. Isolated subsets (the L0-24 acceptance criterion — these bit cold):
   `python3 -m pytest tests/phase_44/ -q` and `tests/phase_18` and
   `tests/phase_49 -m 'not integration'` and `tests/maintenance -m 'not integration'`.
3. With the FalkorDB sidecar up: `python3 -m pytest tests/maintenance/ -q`
   (M2 live tests; orphan-scan may xfail — that is the documented L0-25 residual).
4. Full cumulative gate: expected ~3868+5 passed (4 new maintenance tests pass
   or skip-without-sidecar + 1 xfail/xpass tolerated) / 0 failed.
5. `mkdocs build` (ADR-0182 is nav-absent like 0181 — INFO-level only; PB-16
   re-scoped `--strict` to docs-maintenance).
