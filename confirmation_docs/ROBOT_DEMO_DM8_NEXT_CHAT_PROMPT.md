# Robot Demo — DM-8 next-chat prompt (close DM-7 gate → cinematic clip-replay + Mode-B reload + verification[])

We are building the MindsOS Robot Demo. DM-1…DM-6 are SHIPPED + Linux-gate green on branch
`robot-demo-animation`. **DM-7 is BUILT + sandbox-green (88 passed / 6 skipped, zero regressions)** —
teach → peer-transfer (Local↔Local) → carrier-box cooperation (real multi-leaf decompose) — but its
**Linux live gate has not been run yet**. DM-8 closes the DM-7 gate first, then takes the deferred
polish surfaces. Do not re-litigate settled design.

## Read first, in this order (pointer-style — this prompt does NOT repeat the files)
1. `CLAUDE.md` (root) + `HANDOFF.md` (root).
2. `confirmation_docs/ROBOT_DEMO_STATUS.md` — the **2026-06-15 DM-7 BUILT** update is the current end-state.
3. `confirmation_docs/ROBOT_DEMO_MINDSOS_DESIGN_LOG.md` **§27 (DM-7 reanalysis + probes) + §28 (DM-7 build)**
   — the picks + what shipped + the gate-pending list. Earlier §25/§25.A/§26 = DM-6 reuse.
4. `confirmation_docs/ROBOT_DEMO_SCENARIO.md` — beat 4 (now Local↔Local) + §5.1/§5.2 + the carrier-box sections.
5. `confirmation_docs/DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md` — F1/F2/F5/F6 + **F12** (v0 planning passes
   no milestone identity → the stateful-override workaround DM-7 used).
6. `confirmation_docs/ROBOT_DEMO_UI_BACKEND_COORDINATION.md` — the **DM-7 → UI** section (the three new WS
   commands `teach`/`transfer`/`cooperate` + their frame titles/messages) + the still-owed frozen
   `verification[]` shape.
7. `confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md` + `ROBOT_DEMO_IP_SANITIZATION.md` (policy B) +
   `ROBOT_DEMO_OPEN_QUESTIONS.md`.
8. Memory: `robot-demo-dm6-shipped`, `pair-execution-workflow`, `no-sandbox-git-mutations`,
   `robot-demo-ip-sanitization`, `robot-demo-dm3-sim-runtime`, `mindsos-uncommitted-parked-work-2026-06-11`.

## Scope (this chat)
1. **Close the DM-7 Linux gate (do this first).** The runner is already wired — `run_linux_tests.sh` now
   has **step 7d (DM-6)** and **step 7e (DM-7** = `dm7_check.py`); the DM-6 step was missing and was added
   this chat (`bash -n` clean). So this is a **run**, not a wiring task: Mac commits the scoped DM-7 paths
   (incl. `run_linux_tests.sh`), Linux runs the gate. Expect a likely iteration on **live motion fidelity**
   for the carrier-box's new `load_carrier`/`unload_carrier` arm targets (the structural + wire asserts hold;
   the physical move may need a calibration pass like DM-3 §18 / DM-5). `dm7_check.py` is body-optional, so
   the wire/graph asserts pass even headless.
2. **Cinematic clip-replay + `TrajectoryCache` pre-fill** (deferred since DM-5/§25 PB-1c). The taught
   composite (`transfer.make_taught_impl`) already accepts an injected `run_step`; the `learned-parameters`
   descriptor carries a `cache_key`. Wire the authored `combo_*` clips as the motion store the taught skill
   replays — preserving "starts ignorant, learns everything" (the §27 PB-1 framing-(b) pick). Needs a
   `SimEngine` event-bearing trajectory channel.
3. **Mode-B demo-state reload** (`export_state{mode:"demo-state"}`) — now unblockable since the learn/teach
   flow exists (a learned skill is real state to warm-restore). Currently the live path is not wired
   (`wiring.py on_command`), only the UI mock.
4. **`verification[]` export (optional, PB-5)** — the frozen per-step shape in the coordination doc. Ship it
   only if the carrier-box loop yields the per-step data cheaply; else leave deferred.
5. **UI wiring** of the three DM-7 commands (Teach / Transfer / Cooperate buttons) — coordinate via
   `ROBOT_DEMO_UI_BACKEND_COORDINATION.md` (the DM-7 → UI section has the exact frame contract).

## Carry-forward / do-NOT
* Zero `mindsos_*` edits, zero vendored `sim/` edits (`robot_demo/backend/sim_engine.py` is demo code and
  editable; the vendored `sim/` package is not). The tree holds **parked `mindsos_*`/Phase-51 + other-chat**
  changes — never touch or stage them (memory `mindsos-uncommitted-parked-work-2026-06-11`). When the Mac
  commits, scope-add only the specific `robot_demo/` + `confirmation_docs/` paths, never `-A`; clear any
  stale `.git/index.lock`.
* No-fabrication rule: real exports only (the taught/transferred/cooperation chain must be honest).
* Policy B on every wire/panel string; the internal capability name `load_into_box` stays off the wire
  (label = "box-workaround"); `find_leaks==[]` is enforced by the DM-7 tests + `dm7_check`.

## Conventions
Critical-design-reviewer posture. Before coding: reanalyze the DM-8 plan against the shipped code + the real
sim — list pushbacks with options + your choice; probe, don't assume (every DM-3…DM-7 chat caught a brief ask
that was wrong this way — especially around the SimEngine trajectory channel + Mode-B state extent). Record
decisions in the design log (continue §-numbering, next is §29); net-new MindsOS gaps → a new `Fn` in
DEMO_DERIVED_FEATURES; update `ROBOT_DEMO_STATUS.md` + the coordination doc; write
`ROBOT_DEMO_DM9_NEXT_CHAT_PROMPT.md` at the end. Pair-execution (strict): Cowork builds + validates core in
the 3.10 sandbox (`PYTHONPATH=. python3 -m pytest robot_demo/tests/`; once:
`pip install tomli pytest websockets --break-system-packages`); Mac = git only (scoped `add` of specific
`robot_demo/`+`confirmation_docs/` paths — never `-A`; clear a stale `.git/index.lock`); Linux = pull + run
the gate (`robot_demo/deploy/run_linux_tests.sh` + the in-container `dm*_check` modules; rebuild
`demo-backend` after any baked-source change). Branch `robot-demo-animation`.

## Gate
The DM-7 live gate (`dm7_check.py`) is wired into `run_linux_tests.sh` and prints `DM-7 GATE PASS` on Linux
(teach + Local↔Local transfer + the carrier-box 3-leaf cooperation, clean wire); the cinematic clip-replay
plays the taught skill from the motion store; Mode-B reload warm-restores a learned skill; MindsOS +
DM-1..DM-7 gates stay green; zero `mindsos_*` / vendored `sim/` edits.
