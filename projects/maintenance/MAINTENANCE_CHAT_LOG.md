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
- **M2-F1 (gate finding, 2026-06-09): hyperedge `type_name` not persisted —
  REAL pre-existing L0 fidelity bug, found by the M2 live round-trip on its
  first run.** `build_unwind_create_hyperedges` SET only `graph_id`/`label`/
  props (no `type_name`); the repository row omitted it; the loader already
  reads `h.type_name` and falls back to `"UNSPECIFIED"` — so every live
  round-trip retypes in-graph hyperedges, and a schema-aware load drops them
  as unknown-type. The sibling **metahyperedge** builder had the identical bug
  hotfixed at Phase 08 (B-08-T3); the graph-level builder was missed. Fix
  (2 lines, mirrors B-08-T3): `type_name` added to the builder SET + the
  repository row. Loader unchanged (already read it; `type_name` already in
  `_CORE_KEYS`). InMemoryClient records-only → no unit-test churn; phase_07
  builder tests assert substrings only. Both M2 live failures
  (`test_live_save_load_round_trip`, `test_live_scoped_delete_spares_coresidents`)
  trace to this one bug. The orphan-scan probe **xpassed** on the same run —
  the Phase-44 delete sweep left zero orphans on this shape (evidence for the
  WSD audit, not yet contract).
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
| `969d981` | Closure — L0_FUTURE_WORK markers + this log + orphaned prompt files |
| `28d149f` | M2-F1 — hyperedge `type_name` persistence fix (builders.py + graph_repository.py) — surfaced by the M2 live gate run |

## Gate — RUN 2026-06-09 on the Linux gate host (pair-execution; Cowork sandbox is py3.10/no-sidecar)

Sequence as executed (gate checkout detached at `origin/maintenance-gate`;
HEAD sha confirmed before every run per the Phase 49 forensic note):

1. **Isolated subsets @ `969d981`** — the L0-24 acceptance criterion; these
   used to die cold with `ImportError: cannot import name 'admin_tx'`:
   `tests/phase_44/` → **22 passed**; `tests/phase_18` → **101 passed, 1
   skipped**; `tests/phase_49 -m 'not integration'` → **6 passed, 1
   deselected**; `tests/maintenance -m 'not integration'` → **3 passed, 4
   deselected**. No collection errors — **M1 verified.**
2. **Live maintenance suite @ `969d981` (sidecar up)** — **2 FAILED**
   (round-trip + scoped-delete), 4 passed, **1 xpassed**. Diagnosis → **M2-F1**
   (hyperedge `type_name` never persisted; loader rehydrates `"UNSPECIFIED"`;
   identical to the Phase 08 B-08-T3 metahyperedge hotfix, sibling builder
   missed). Fixed at `28d149f`; re-run → **6 passed, 1 xpassed.** The xpass:
   the orphan-scan sweep probe found **zero orphans** — first live evidence
   for the WSD sweep audit (probe stays `xfail(strict=False)`; evidence, not
   yet contract).
3. **Full cumulative @ `28d149f`** (`docker compose run --rm mindsos-test
   pytest tests/ -q`) — **3874 passed, 11 skipped, 1 xpassed, 0 failed**
   (baseline 3868/11/0 + 6 maintenance tests + the xpass). **Incident:** the
   first cumulative ran on a **stale pre-rebuild test image** and returned the
   unchanged 3868 baseline — the docker-image variant of the Phase 49
   stale-checkout trap. Detection: in-container `ls tests/maintenance` +
   `grep` for the M2-F1 line. **Lesson for future gates: confirm the IMAGE
   content (not just the checkout sha) before trusting a cumulative count.**

Ceremony: `main` fast-forwarded `cc8a7f8..28d149f`; tag
`maintenance-2026-06-09` (A0 `a0-corpus-landed` precedent); `maintenance-gate`
branch deleted; phase-ci watched via web (no `gh` on the gate host).

## Post-gate amendments

- This gate record replaced the pre-run runbook (this commit).
- M2-F1 evidence note: the xpassed orphan scan covered nodes/edges/hyperedge/
  metaedge/metahyperedge on a 2-graph Local — the WSD audit should extend to
  XRef variants + tombstones + cross-metagraph satellites before promoting the
  probe to a strict assertion.
