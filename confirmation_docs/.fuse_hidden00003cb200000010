# Phase 42 — Next Chat Prompt (Rail B slot 3: L3 X3)

> **You are the Phase 42 design + ship chat (Rail B — L3 reframe X3).** Rail B slot 2 (Phase 41 X2) shipped 2026-06-05 (tag `phase-41-confirmed` at `ba7c469`; squash `9330550`; gate 3660/8/0). Rail A (39, 43) + Rail C (44) + Rail B (40, 41) all shipped. Phase 42 depends on **Phase 41 confirmed** and branches off `main`. This file is your operating spec — it points to authoritative content; it does **not** restate it. Read the routed files; do not infer scope from this prompt alone.

═══════════════════════════════════════════════════════════════════
SCOPE — read, don't infer
═══════════════════════════════════════════════════════════════════

Phase 42 is **L3 X3: bipartite topology (ADR-0156) + capacity registration contract v2 (ADR-0159) + Phase 27 dont-know audit + Model C remediation**. It is the **largest phase in Stream B** (L1 + L3 + docs + 8 amendment ADRs + a one-pass migrator + an audit deliverable). Unlike Phases 40/41 it is **not** purely settled impl — it carries one genuine design decision (the PB-8 / L3-57 `FAMILY_RULES` reconciliation, decided inside the audit deliverable). Authoritative scope, read all three:

1. **`confirmation_docs/POST_PHASE_38_PHASE_MAP.md` → "### Phase 42 — L3 X3"** (the detail block: locked decisions, in-scope features, modules touched, tests, pass criterion incl. the `TYPE_COMPAT`/`discover_*` grep-zero sentinel, breaking changes) + the §3 index row + §1 cross-cutting decisions (DAG + manifest high-water-mark).
2. **`confirmation_docs/L1_L3_REFRAME_DECISIONS.md`** → **§D38** (ADR-0156 bipartite topology) + **§Registration contract v2** (ADR-0159, incl. Fork 10 backward-compat-via-defaults) + the **§ADR map** header. The §D46/§D48 context (X1, already shipped Phase 40) is the input the Phase 27 audit reconciles against.
3. **ADRs on disk:** `docs/decisions/adr/0156-l3-bipartite-topology-reframe.md` + `0159-capacity-registration-contract-v2.md` (both **Accepted**). Run the **ADR transcription parity probe** (grep your design-pass transcription against the ADRs-on-disk; correct the draft, not the ADR — the Phase 43 NPB11-META lesson restated in `PHASE_43_DESIGN_LOG.md §10.1`).

═══════════════════════════════════════════════════════════════════
PREREQ CHECK (run BEFORE branching)
═══════════════════════════════════════════════════════════════════

1. `git tag --list | grep phase-41-confirmed` — must exist at `ba7c469` (Rail B slot 2 shipped).
2. `git log --oneline -3 main` — top is the Phase 41 confirm-artifacts commit `ba7c469`, parent the squash `9330550`. Tree clean **except** the known out-of-scope untracked items (`confirmation_docs/ROBOT_DEMO_*`, `demo_ui/`, `prototype_zero/`, the `PHASE_4x_NEXT_CHAT_PROMPT.md` files) — leave them alone, never `git add -A`.
3. **Branch `phase-42` off `main`-tip.**
4. **Manifest high-water-mark in force** (Phase 40 PB-2): slot 42 ≤ high-water 44 ships with **NO version bump**; `confirm-phase --phase 42` already accepted by `_phase_exceeds_manifest`. Do not bump version surfaces. (`POST_PHASE_38_PHASE_MAP.md §1` manifest row + `PHASE_40_DESIGN_LOG.md §11`.)

If any check fails, surface it and pause.

═══════════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════════

1. **`HANDOFF.md`** §1 (orientation), §9 (process discipline — two-machine Mac/Linux sync + pair-execution + 6-step confirm-phase + docker rebuild), §3.1 (the "L3 surface L4 consumes" list — Phase 42 rewrites discovery/pipeline topology beneath it), **§3.1.16 (Phase 41 ship closure — your most recent precedent, incl. the grounding corrections + ceremony record)**, §3.1.15 (Phase 40).
2. **`confirmation_docs/POST_PHASE_38_PHASE_MAP.md`** §0 (how a phase chat reads this file), §1, the Phase 42 detail block, and the Phase 41 row for process precedent.
3. **`confirmation_docs/L1_L3_REFRAME_DECISIONS.md`** §D38 + §Registration (+ §ADR map) in full; skim §D46/§D48 (the X1 vocabulary the audit reconciles).
4. **`confirmation_docs/PHASE_41_DESIGN_LOG.md`** (immediate-predecessor process precedent: §0 discipline, §1 S-surface format to mirror, §5 impl-time grounding findings, §3/§4 sentinel ledger) **and `PHASE_44_DESIGN_LOG.md §0 + §5–§12`** (load-bearing consumer-discipline + the L0-24 import cycle) **and `PHASE_40_DESIGN_LOG.md §10`** (the S2 lesson — a sweep must include **test-fixture AND docs consumers**; Phase 40's 38-failure gate-1 cascade. This is *critical* for Phase 42: the `TYPE_COMPAT`/`discover_*` retirement + the ~50-file Model C remediation are exactly that sweep at scale) **+ §11** (manifest high-water-mark).
5. **Modules Phase 42 touches** (read for diff baselines, named in the PHASE_MAP "Modules touched"): `mindsos_capacity/discovery.py` (DELETE whole ~330 LOC — but verify its consumers first), `capacity_layer.py` (`register_capacity` edge emission + TYPE_COMPAT retire), `pipeline.py` (`find_pipeline` bipartite rewrite), `views.py` (`successors_of` rewrite), `capacity.py` (`_CapacityBase` +5 fields), the Phase 33-35 write bodies (`context["kl"]`→`context.kl`), `mindsos_instances/` catalog (Phase 06 amendment), and the Phase 29 + Phase 33 tests that retire/rewrite.

═══════════════════════════════════════════════════════════════════
INHERITED LESSONS — apply, do not re-derive (sources above)
═══════════════════════════════════════════════════════════════════

- **Ground-first consumer discipline (Phase 44 §5–§12; Phase 41 §5).** Before deleting/rewriting any surface, grep **every** consumer across `mindsos_*`, `tests/`, and `docs/`. `discovery.py` "deletes whole" — but `views.successors_of` / `pipeline.find_pipeline` / `register_capacity` consume its TYPE_COMPAT edges; ground each before rewrite. The PHASE_MAP grep-zero sentinel (`TYPE_COMPAT`/`discover_for_capacity`/`discover_for_datastate`/`rediscover_all`) is **repo-wide-unsatisfiable** for the same reason Phase 41's was (ADRs 0069/0086/0156 + summaries document the retirement) — **scope the sentinel to the shipped package** (`mindsos_capacity/**/*.py`), per the Phase 41 PB-2 precedent, and scrub live docstrings as part of the sweep.
- **Verify every "Modules touched" path EXISTS before trusting it (Phase 41 IPB-4).** Phase 41's PHASE_MAP row listed `docs/concepts/monitors.md`, a phantom. Phase 42 touches ~50 docs files + new `tools/migrate_phase_42_bipartite.py` + `mindsos_capacity/verdicts.py` + `context.py` — confirm each target's existence/non-existence at R0 and reconcile the row.
- **"Deletes whole" ≠ production whole-delete (Phase 41 IPB-1/IPB-2).** Confirm `discovery.py` truly has no other occupants, and that retiring Phase 29 tests doesn't orphan a shared `_fixtures.py` (the Phase 41 `_fixtures` trap).
- **Export-slate sentinels now at 112** (Phase 41 set them). Any `__all__` change (the +5 `_CapacityBase` fields are dataclass fields, not exports; but `context.py`/`verdicts.py` may add exports) re-flips the count in **four** files (`tests/phase_29/31/33/34_*export_slate*`). Re-grep before locking; Phase 29's slate file survives even though the Phase 29 *suite* retires.
- **ADR transcription parity probe** as R1 step 0 (ADR-0156 + ADR-0159; verify status Accepted, no flip).
- **Sentinel chain:** `tests/phase_42/test_adr_amendment_sentinels.py` chains from Phase 41's; anchors ADR-0156 + ADR-0159 + the 8 amendment ADRs.
- **The PB-8 / L3-57 reconciliation is a real decision** (tracked `docs/_workbench/L3_FUTURE_WORK.md` L3-57): the Phase 27 audit deliverable must decide *amend ADR-0157's `FAMILY_RULES` dict* (rename `derive`/`signal`→`derivation`/`signalling` + add the 7 unkeyed categories) *vs keep the permissive `DATASTATE_MARKER` default*. Treat as a pushback with options, not a settled pick.
- **Ceremony hygiene (Phase 41 §3.1.16):** run `confirm-phase` on **post-squash `main`**, not the branch tip; tag `phase-42-confirmed` at the confirm-artifacts commit (Phase 41 precedent: tag at `ba7c469`, not the squash); fix the Linux box `git config` author before committing confirm artifacts; CHANGELOG stays untouched (stopped at Phase 38).
- **Largest-phase tester load (PHASE_MAP risk row):** budget more gate-driven follow-up cycles (Phase 43 needed 6); cascade failures at first gate often trace to a single root cause — diagnose before fixing.

═══════════════════════════════════════════════════════════════════
OUT OF SCOPE
═══════════════════════════════════════════════════════════════════

- The one-pass migrator targets **Global only** (Locals are in-memory pending the Phase 44 persisters; do not migrate Locals).
- L4-side consumers — the bipartite walk's L4 consumers + the `cl.iter_monitors()` consumer (`MonitorSubscriptionRegistry`) ship **Phase 46**.
- Re-litigation of ADR-0156 / ADR-0159 / the reframe (settled in §D38 + §Registration; you implement them).
- `DontKnowReason.UNHANDLED_INPUT` (L3-56) — owned by **L4 (Phase 46/47)**, not this phase.

═══════════════════════════════════════════════════════════════════
FIRST ACTION
═══════════════════════════════════════════════════════════════════

Run the prereq check. Ack required-reading completion. Then **R0**: read the scope sources, run the ADR-0156 + ADR-0159 transcription parity probe, **grep the full TYPE_COMPAT/`discover_*` blast radius** across `mindsos_*` / `tests/` / `docs/` (this is large — `discovery.py` delete + `pipeline`/`views`/`register_capacity` rewrite + ~50-file Model C remediation), **verify every "Modules touched" path's existence** (phantom check), ground the one-pass migrator against shipped Global state, and produce the R0 saturation agenda in a new `confirmation_docs/PHASE_42_DESIGN_LOG.md` (mirror the Phase 41 / Phase 44 S-surface format). Surface the L3-57 reconciliation as an explicit pushback with options. Then run the pre-impl pushback rounds (budget 2–3 + a buildability scan over the export-slate + grep-zero + migrator-idempotence sentinels) before branching.

The user runs this project with: **"Before proceeding with any implementation, reanalyze the plan and list your pushbacks with options, then show me your choice. Any decision can change as we go."** Honor it — skeptical review each round, terse, options + your pick, pause for authorisation before impl.
