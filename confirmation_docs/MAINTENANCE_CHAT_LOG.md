# MAINTENANCE_CHAT — log (opened 2026-06-09)

Stream-A-style maintenance commits on `main` (A0/A9 precedent, HANDOFF §3.1.10).
Not a numbered phase. No 9-surface manifest bump expected (no bump surface touched).
Prereqs verified at open: tag `phase-49-confirmed` present; `main` HEAD = `cc8a7f8`
(the Phase-49 confirm commit).

## Slate (5 items + M0 housekeeping)

| Item | Scope | Status |
|---|---|---|
| M0 | Land the uncommitted Phase-49 ship-closure doc amendments found in the working tree at open (HANDOFF §3.1.20-22 + last-updated banner; CLAUDE.md status; PHASE_MAP 47/48/49 → SHIPPED; L3_FUTURE_WORK L3-57 resolved + L3-58 added; cookbook_routing end-to-end row → Shipped). Authored in the 2026-06-09 reanalysis session, never committed. Doc-only, consistent with the confirmed tags. | pending |
| M1 | L0-24 import-cycle fix: `mindsos_admin/promotion.py:68` → lazy import inside `propose_for_promotion` (pattern `mindsos_core/persistence/client.py:140`); delete `tests/phase_44/conftest.py` band-aid; isolated subsets + cumulative gate. | pending |
| M2 | L0-25 live-Falkor round-trip coverage for `FalkorDBLocalPersister` (save→load + scoped delete). Probe first; in-vs-route decision recorded below. | pending |
| M3 | L0-26 node-value serialization contract — ADR, decide-and-document ONLY. Implementation routed to skill-acquisition slot 1 (first consumer). | pending |
| M4 | L3_FUTURE_WORK routing record: CapacityContext read-path migration (union-drop). Contract authority = SKILL_ACQUISITION R0; mechanical migration = WSD slot 1. Doc-only. | pending |
| M5 | `projects/ANALYSIS_DELTA_2026-06.md` addendum + banner pointers in `projects/wsd/ANALYSIS.md` + `projects/fol/ANALYSIS.md`. Every claim grep-verified against shipped code (NPB11-META). | pending |

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

## Commits

(per-item; never `git add -A`; untracked ROBOT_DEMO_* / *_NEXT_CHAT_PROMPT.md files
left untracked — separate workstreams)
