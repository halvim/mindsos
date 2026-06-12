# Robot Demo — DM-5 next-chat prompt (◆ assembled capacities)

We are building the MindsOS Robot Demo. **DM-1…DM-4 core are SHIPPED and gate-green on Linux**
(branch `robot-demo-animation`), and the **DM-4 increment (Mode-A L5 export + `server_status`)
is code-complete + sandbox-validated** (Linux gate + browser confirmation may still be pending —
check `ROBOT_DEMO_STATUS.md` first). This chat builds **DM-5: the ◆ assembled L3 capacities**
(`pick` / `place_at_cell` / `stage_at`) — real item-level manipulation + cell allocation, replacing
the DM-4 fixed `arm1/home` thin slice. **Do not re-litigate settled design.**

## Read first, in this order (this prompt does NOT repeat what's in these files)

1. `CLAUDE.md` (root) — the 5-layer stack + working conventions.
2. `HANDOFF.md` (root) — current MindsOS state.
3. `confirmation_docs/ROBOT_DEMO_STATUS.md` — **start here.** Confirm DM-4's Linux-gate + browser
   state (Mode-A export / `server_status`); pick up any unfinished DM-4 closure before starting DM-5.
4. `confirmation_docs/ROBOT_DEMO_MINDSOS_DESIGN_LOG.md` §15–§22 — the DM-3/DM-4 builds + the grounded
   findings to **REUSE, not re-derive**: `if_exists="upsert"` is a behavioural no-op → `comms.install_override`;
   the reasoning chain is readable post-lifecycle in `il.mm.intelligence_mm` (role `chain`), sliced
   per-task by `task_scope`; per-task `brain.run_task` scope; the v0 leaf step is notional (real steps
   are DM-5/WSD); dispatched params reach phase-2 only via `task_pattern_iri`; reload re-registers DataStates;
   `os._exit` for the MuJoCo teardown segfault.
5. `confirmation_docs/ROBOT_DEMO_SCENARIO.md` — the order→allocation→placement contract (resolver in
   `OPEN_QUESTIONS §3`; the per-arm 3×3 shelf + relation clauses `above/below/left/right/under`).
6. `confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md` — §2.2 `state` (`caps[]` badges incl. `GATED`/`FAULT`),
   §4 `place_order` `lines[].pos` clause shape, §5 the **Plan ▸ Resolve** producer (9→3→1 narrowing) the
   UI is waiting on — DM-5's allocation is the natural source for it.
7. `confirmation_docs/ROBOT_DEMO_IP_SANITIZATION.md` — policy B + the token→generic table; the
   `robot_demo/backend/sanitize.py` module (canonical banned list + `TokenMap` + `find_leaks`) is the
   one place to add any new label mapping. **The wire must leave the backend already clean.**
8. Shipped code you extend: `robot_demo/backend/{capacities,sim_engine,body_adapter,live_motion,
   motion_checklist,wiring,comms,brain,dm4_check}.py`. The DM-3 ⬡ atomics (`move_to`/`suction_set`/
   `jaw_set`/`pick`/`place_at_cell`) are registered per device in `capacities.py::register_embodied_capacities`;
   `pick`/`place_at_cell` exist as ⬡ stubs — DM-5 makes them ◆ assembled (real pick-place motion + cell-cell).
9. Memory: `robot-demo-dm4-shipped`, `pair-execution-workflow`, `no-sandbox-git-mutations`,
   `robot-demo-ip-sanitization`, `robot-demo-dm3-sim-runtime`, `mindsos-uncommitted-parked-work-2026-06-11`.

## Scope (this chat)

* **◆ assembled `pick` / `place_at_cell` / `stage_at`.** Real grasp→lift→carry→place over the live sim
  (the DM-3 `motion_checklist` gate calibrated to a real pick-place invariant, not the coarse AABB);
  per-device embodiment (suction vs jaw) gates which arm can do what — surface the **embodiment gate**
  honestly (`caps[]` badge `GATED`, a `dont_know` on the wrong gripper).
* **Real allocation** replacing DM-4's fixed `arm1/home` `decide`: resolve the order's `lines[].pos`
  clauses against the per-arm 3×3 shelf (the `OPEN_QUESTIONS §3` resolver) → (arm, cell). Feed the
  **Plan ▸ Resolve** producer (WS contract §5, 9→3→1 narrowing) so that panel goes live.
* **Mode-A export gets real depth for free:** the per-task chain now carries a real ◆ assembled step
  (not the notional v0 leaf) — the `serializer.py` `steps[]` will start reflecting actual sub-capacities.
  Keep `sanitize.plain_capacity` honest (relabel the new IRIs to plain action names).
* Wire into the gate flow; extend the sanitization guard + `dm4_check`/a new `dm5_check`; headless tests
  + Linux gate; browser confirmation.

## Do-NOT

No live `import_state` write and no `server_event` (those are the DM-4-follow-up / DM-8 increment — see
the coordination doc phasing). No Mode-B reload (post-DM-6 — there's nothing real to warm-restore until
the teach/learn flow). **Zero `mindsos_*` edits** (the tree holds parked Phase-51 + other-chat `mindsos_*`
changes — do NOT touch or stage them; see memory `mindsos-uncommitted-parked-work-2026-06-11`).

## Conventions

Critical-design-reviewer posture. **Before coding: reanalyze the DM-5 plan against the shipped DM-3/DM-4
code + the real sim — list pushbacks with options and your choice; probe, don't assume.** Record decisions
in the design log (continue §-numbering, next is §23); net-new MindsOS gaps → new `Fn`; update
`ROBOT_DEMO_STATUS.md` + plan §8 row; write `ROBOT_DEMO_DM6_NEXT_CHAT_PROMPT.md` at the end.
**Pair-execution (strict):** Cowork builds + validates core in the 3.10 sandbox (`PYTHONPATH=. python3 -m
pytest robot_demo/tests/`; install `tomli pytest websockets --break-system-packages` once); **Mac = git
only** (scoped `add` of the specific `robot_demo/` + `confirmation_docs/` paths — **never `-A`**, it would
sweep the parked `mindsos_*` work; watch the stale `.git/index.lock`); **Linux = pull + run the gate**
(`run_linux_tests.sh`). Branch `robot-demo-animation`.

## Gate

A `place_order` with a real `lines[].pos` resolves to (arm, cell), the matched arm runs a ◆ assembled
pick→place verified by the motion checklist, the wrong-gripper arm honestly refuses (embodiment gate →
`GATED`/`dont_know`), the **Plan ▸ Resolve** panel narrows 9→3→1 live, the Mode-A export shows the real
assembled step, the wire passes the banned-token guard, MindsOS + DM-1/2/3/4 gates stay green, zero
`mindsos_*` edits.
