# Phase 40 — Next Chat Prompt (Rail B slot 1: L3 X1)

> **You are the Phase 40 design + ship chat (Rail B — L3 reframe X1).** Rail C (Phase 44 L0 substrate) shipped 2026-06-04 (`tag phase-44-confirmed`). Rail A (Phases 39, 43) shipped. Rail B (40 X1 → 41 X2 → 42 X3) has not started; **Phase 40 is its first slot** and its prereqs are met. This file is your operating spec — it points you to the authoritative content rather than restating it. Read the required files; do not assume scope from this prompt alone.

═══════════════════════════════════════════════════════════════════
SCOPE — read, don't infer
═══════════════════════════════════════════════════════════════════

Phase 40 is **L3 X1: family-specific dont-know contracts (ADR-0157) + DataState realm naming convention (ADR-0158)** + the shared `identifiers.py` `REALM_*` constants. The authoritative scope lives in two places — read both, do not work from memory:

1. **`confirmation_docs/POST_PHASE_38_PHASE_MAP.md` → "### Phase 40 — L3 X1"** (the detail block: locked decisions, features, modules touched, tests, pass criteria, risks) + the §4 row + §1 "DAG execution" row.
2. **`confirmation_docs/L1_L3_REFRAME_DECISIONS.md`** — the L1/L3 reframe settlement (5 ADRs 0155-0159 + X1/X2/X3 sequencing). X1 = ADR-0157 + ADR-0158. This is the design ground truth; Phase 40 is an **impl phase** of an already-settled design (same relationship Phase 44 had to L0_SUBSTRATE_CHAT — except here the design chat already closed, so there is no design to absorb).
3. **ADRs on disk:** `docs/decisions/adr/0157-*.md`, `docs/decisions/adr/0158-*.md` (+ 0155/0156/0159 for X1/X2/X3 context). Run the **ADR transcription parity probe** (R1 step 0, per `PHASE_44_DESIGN_LOG.md` §0) — grep your design-pass draft's transcription tables against the ADR-on-disk; correct the draft, not the ADR.

═══════════════════════════════════════════════════════════════════
PREREQ CHECK (run BEFORE branching)
═══════════════════════════════════════════════════════════════════

1. `git tag --list | grep phase-44-confirmed` — must exist (Rail C shipped).
2. `git status` — clean working tree.
3. `git log --oneline -3 main` — top is the Phase 44 closure-docs commit (descendant of `phase-44-confirmed`).
4. **Branch off `main`-tip.** Rail B depends only on Phase 38 (parallel to Rails A/C per the PHASE_MAP §1 DAG row), but `main` now carries 39+43+44; branch `phase-40` off current `main` so you build on the real tree.
5. **`identifiers.py` collision discipline (PB-Z).** Phase 40 adds `REALM_*` constants to `mindsos_knowledge/identifiers.py`; Phase 39 (rename) + Phase 43/44 already edited that file. Read the current `identifiers.py` + the Phase 39 diff before touching it (PHASE_MAP §4 Phase 40 risk note names this explicitly).
6. **DAG manifest nuance (resolve early).** The manifest `[mindsos] phase` is currently `44`. `mindsos confirm-phase --phase 40` will mismatch a `phase = "44"` manifest (the check assumes serial phases). Decide how the manifest integer behaves under the parallel DAG **before** the confirm ceremony — surface it to the user; do not blind-bump.

If any check fails, surface immediately. Do not branch.

═══════════════════════════════════════════════════════════════════
REQUIRED READING (in order; do NOT skip)
═══════════════════════════════════════════════════════════════════

1. **`HANDOFF.md`** §1 (orientation), §9 (process discipline — pair-execution + 6-step confirm-phase + docker rebuild + manifest-bump discipline), §3.1.14 (Phase 44 ship closure — the most recent precedent).
2. **`confirmation_docs/POST_PHASE_38_PHASE_MAP.md`** §0 (how a phase chat reads this file), §1 (DAG execution + settled cross-cutting decisions), Phase 40 detail block, and the **two prior Rail-B rows** (there are none before 40 — 40 is Rail B root; instead read the Phase 39 + 44 rows for `identifiers.py`/process precedent).
3. **`confirmation_docs/L1_L3_REFRAME_DECISIONS.md`** in full (your design ground truth).
4. **`confirmation_docs/PHASE_44_DESIGN_LOG.md` §0 + §5-§12** — the most important process precedent. In particular the **consumer discipline**: Phase 44 reversed three "do-it-now" rulings (CR-2, CR-3, S6/L2-10) because grounding showed no v1 consumer. Apply the same test to every X1 surface — *ground against the real codebase before building; do not ship speculative forward-shape that has no v1 consumer.* §12 documents a pre-existing import cycle (L0-24) that bites isolated test runs (see below).
5. **Modules Phase 40 touches** (read for diff baselines — named in the PHASE_MAP Phase 40 "Modules touched"): `mindsos_knowledge/identifiers.py` + the L3 capacity/contract surfaces ADR-0157/0158 name.

═══════════════════════════════════════════════════════════════════
PROCESS DISCIPLINE (inherited — do not re-derive)
═══════════════════════════════════════════════════════════════════

All process discipline lives in **`HANDOFF.md` §9** + **`PHASE_44_DESIGN_LOG.md` §0/§5-§12**. Internalize before branching. The load-bearing ones:

- **Ground-first consumer discipline (the Phase 44 lesson).** Before building any surface, grep for its v1 consumer. If none, defer it to its consumer phase and record the deferral — don't build it. This is what made Phase 44 ship narrow-and-correct.
- **Pair-execution** (Cowork prepares file content; user runs git on Mac; Linux runs gates via docker). Cowork sandbox `.git/` is read-only and the sandbox is Python 3.10 (project needs 3.12 — sandbox can only syntax-compile + run pure-logic checks; real gates run on the Linux docker image).
- **6-step confirm-phase** + **manifest-bump-N-surface** (bumping `[mindsos] phase` cascades to pyproject + 7 package `__version__` + docker-compose image tags + any export-slate test assertions; `doctor --self-test` enforces parity — run it).
- **Buildability scan over locked commit boundaries** (exactly-N sentinels + fixture-keyed tests) before ratifying PR ordering.
- **L0-24 import cycle (pre-existing).** `admin↔persistence↔mindsos_admin` bites isolated `pytest tests/phase_NN/` runs that import `mindsos_server` cold (full suite masks it). Phase 40 is L3 and may not import `mindsos_server`, so it may not be affected — but if your tests do, either add an `importlib.import_module("mindsos_admin")` conftest warm-up (band-aid) **or** clear L0-24 first (the surgical lazy-import fix in `mindsos_admin/promotion.py` is the right fix — full diagnosis in `PHASE_44_DESIGN_LOG.md §12` + `L0_FUTURE_WORK.md` L0-24). Clearing L0-24 as a maintenance preface is encouraged.

═══════════════════════════════════════════════════════════════════
OUT OF SCOPE
═══════════════════════════════════════════════════════════════════

- Phase 41 (X2) + Phase 42 (X3) — later Rail B slots.
- Rail D (Phase 45 — gated on DREAM_FAMILY_CHAT, not yet opened).
- Phase 46 (L4 substrate — opens after all four rails complete).
- Re-litigation of the L1/L3 reframe design (settled in L1_L3_REFRAME_DECISIONS; you implement it).

═══════════════════════════════════════════════════════════════════
FIRST ACTION
═══════════════════════════════════════════════════════════════════

Run the prereq check. Ack required-reading completion. Then **R0**: read the scope sources, run the ADR transcription parity probe, ground each X1 surface against its v1 consumer (defer the consumer-less), and produce the R0 saturation agenda in a new `confirmation_docs/PHASE_40_DESIGN_LOG.md` (mirror the Phase 44 design log's S-surface format). Surface the DAG-manifest nuance (prereq #6) to the user before the ship ceremony.
