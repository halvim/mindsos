# Phase 41 — Next Chat Prompt (Rail B slot 2: L3 X2)

> **You are the Phase 41 design + ship chat (Rail B — L3 reframe X2).** Rail B slot 1 (Phase 40 X1) shipped 2026-06-05 (`tag phase-40-confirmed`). Rail A (39, 43) + Rail C (44) shipped. Phase 41 depends on **Phase 40 confirmed** and branches off `main`. This file is your operating spec — it points to authoritative content; it does **not** restate it. Read the required files; do not infer scope from this prompt alone.

═══════════════════════════════════════════════════════════════════
SCOPE — read, don't infer
═══════════════════════════════════════════════════════════════════

Phase 41 is **L3 X2: ADR-0155 Monitor-lifecycle retirement from L3** — a **hard-break** retirement (Phase 31 resident infrastructure deletes whole). Authoritative scope, read all three:

1. **`confirmation_docs/POST_PHASE_38_PHASE_MAP.md` → "### Phase 41 — L3 X2"** (the detail block: locked decisions, retire/keep lists, the rename, `iter_monitors`, modules touched, tests, pass criterion incl. the grep-zero sentinel, breaking-changes) + the §3 index row + §1 cross-cutting decisions.
2. **`confirmation_docs/L1_L3_REFRAME_DECISIONS.md` → §D36** — the design ground truth for ADR-0155 (Monitor lifecycle relocates L3→L4). Phase 41 is an **impl phase** of an already-settled design.
3. **ADR on disk:** `docs/decisions/adr/0155-*.md`. Run the **ADR transcription parity probe** (grep your design-pass transcription against the ADR-on-disk; correct the draft, not the ADR — the Phase 43 NPB11-META lesson, restated in `PHASE_43_DESIGN_LOG.md §10.1`).

═══════════════════════════════════════════════════════════════════
PREREQ CHECK (run BEFORE branching)
═══════════════════════════════════════════════════════════════════

1. `git tag --list | grep phase-40-confirmed` — must exist (Rail B slot 1 shipped).
2. `git status` — clean tree; `git log --oneline -3 main` — top is the Phase 40 closure-docs commit (`ce6edc3`, descendant of `phase-40-confirmed` at `cf3faeb`).
3. **Branch `phase-41` off `main`-tip.**
4. **Manifest behaves per the high-water-mark convention now in force** (shipped Phase 40, PB-2). Phase 41 (41 ≤ high-water 44) ships with **NO version bump**; `confirm-phase --phase 41` is already accepted by `confirm_phase._phase_exceeds_manifest`. Do **not** bump the manifest or version surfaces. Read `POST_PHASE_38_PHASE_MAP.md §1` manifest row + `PHASE_40_DESIGN_LOG.md §11`.

If any check fails, surface it and pause.

═══════════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════════

1. **`HANDOFF.md`** §1 (orientation), §9 (process discipline — pair-execution + 6-step confirm-phase + docker rebuild), §3.1 (the settled "L3 surface L4 consumes" list — Phase 41 amends it), **§3.1.15 (Phase 40 ship closure — your most recent precedent, incl. the ceremony anomalies to avoid)**.
2. **`confirmation_docs/POST_PHASE_38_PHASE_MAP.md`** §0 (how a phase chat reads this file), §1, the Phase 41 detail block, and the prior Rail-B row (Phase 40) for `mindsos_capacity` / process precedent.
3. **`confirmation_docs/L1_L3_REFRAME_DECISIONS.md` §D36** in full (design ground truth) + the §ADR-map header.
4. **`confirmation_docs/PHASE_40_DESIGN_LOG.md`** (immediate-predecessor process precedent: §0 discipline, §1 S-surface format to mirror, §9 buildability scan, §10 gate-driven follow-up + the S2 lesson, §11 ship closure + manifest high-water-mark) **and `PHASE_44_DESIGN_LOG.md §0 + §5–§12`** (the load-bearing consumer-discipline precedent + the L0-24 import cycle).
5. **Modules Phase 41 touches** (read for diff baselines — named in the PHASE_MAP Phase 41 "Modules touched"): the Phase 31 resident module-set + `mindsos_capacity/capacity_layer.py` + `mindsos_capacity/__init__.py` + the Phase 27/28 register/dataclass tests.

═══════════════════════════════════════════════════════════════════
INHERITED LESSONS — apply, do not re-derive (sources above)
═══════════════════════════════════════════════════════════════════

- **Ground-first consumer discipline (Phase 44).** Before deleting/renaming any surface, grep for **every** consumer across `mindsos_*`, `tests/`, and `docs/`. Phase 40's gate-1 cascade (38 failures) came from test-fixture consumers missed at R0 (`PHASE_40_DESIGN_LOG.md §10` S2 lesson). Phase 41 is a **hard-break**: the retired surface set (`start_resident` / `stop_resident` / `active_subscriptions` / `_subscriptions` / `ResidentSubscription` / `ResidentError` / `KIND_RESIDENT`) and the `KIND_RESIDENT`→`KIND_MONITOR` rename **must** be swept exhaustively first. The PHASE_MAP pass criterion already specifies the grep-zero sentinel — make it a `tests/phase_41/` test.
- **Export-slate sentinels.** Retiring exports changes `mindsos_capacity.__all__`; the exactly-N count is asserted in **four** files (`tests/phase_29/31/33/34_*export_slate*`) — Phase 40 set them to **114**. Re-grep before locking (Phase 40 PB-9 first under-counted to one file). `ResidentSubscription` (+ any retired export) leaving `__all__` drops the count; flip all four.
- **ADR transcription parity probe** as R1 step 0.
- **Sentinel chain:** `tests/phase_41/test_adr_amendment_sentinels.py` chains from Phase 40's; anchor ADR-0155 canonical strings (status Accepted — verify, no flip).
- **Ceremony hygiene (Phase 40 §11 anomalies — avoid):** run `confirm-phase` on **post-squash `main`**, not the branch tip; fix the Linux box's `git config` author identity before committing confirm artifacts.

═══════════════════════════════════════════════════════════════════
OUT OF SCOPE
═══════════════════════════════════════════════════════════════════

- Phase 42 (X3 — bipartite topology + registration contract v2 + Phase 27 audit incl. the PB-8 `FAMILY_RULES` reconciliation routed from Phase 40).
- The **L4-side** `MonitorSubscriptionRegistry` + the `cl.iter_monitors()` consumer — those ship Phase 46 (L4 substrate). Phase 41 ships the L3-side retirement + the `iter_monitors` producer only; no L4 consumer exists at v1 (acceptable per DAG, same pattern as Phase 40's family_rules ahead of its L4 consumer).
- Re-litigation of ADR-0155 / the L1/L3 reframe (settled in §D36; you implement it).

═══════════════════════════════════════════════════════════════════
FIRST ACTION
═══════════════════════════════════════════════════════════════════

Run the prereq check. Ack required-reading completion. Then **R0**: read the scope sources, run the ADR-0155 transcription parity probe, **grep the full hard-break blast radius** (every retired symbol + the `KIND_RESIDENT` rename across `mindsos_*` / `tests/` / `docs/`), ground the `iter_monitors` producer against its (absent-at-v1, Phase 46) consumer, and produce the R0 saturation agenda in a new `confirmation_docs/PHASE_41_DESIGN_LOG.md` (mirror the Phase 40 / Phase 44 design-log S-surface format). Then run the pre-impl pushback rounds (budget 2–3 + a buildability scan over the export-slate + retirement sentinels) before branching.
