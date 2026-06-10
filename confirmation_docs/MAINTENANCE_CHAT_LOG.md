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

(recorded per item as they close)

## Commits

(per-item; never `git add -A`; untracked ROBOT_DEMO_* / *_NEXT_CHAT_PROMPT.md files
left untracked — separate workstreams)
