# Robot Demo — DM-5 next-chat prompt (◆ assembled capacities)

We are building the MindsOS Robot Demo. **DM-1…DM-4 are SHIPPED and gate-green on Linux**, and the
**DM-4 L5 increment (Mode-A `episode-audit` export + `server_status`) is SHIPPED, Linux-gate green, and
browser-confirmed** (branch `robot-demo-animation`, commit `70d3cd9`+). This chat builds **DM-5: the ◆
assembled L3 capacities** (`pick` / `place_at_cell` / `stage_at`) — real item-level manipulation + real
order→cell allocation, replacing DM-4's fixed `arm1/home` thin slice. **Do not re-litigate settled design.**

## Read first, in this order (this prompt does NOT repeat what's in these files)

1. `CLAUDE.md` (root) — the 5-layer stack + working conventions.
2. `HANDOFF.md` (root) — current MindsOS state.
3. `confirmation_docs/ROBOT_DEMO_STATUS.md` — **start here.** The DM-4 + L5-increment end-state (what
   shipped, what's confirmed, what the UI now owns). Read the two 2026-06-12 DM-4 updates.
4. `confirmation_docs/ROBOT_DEMO_MINDSOS_DESIGN_LOG.md` §15–§22 — the DM-3/DM-4 builds + the grounded
   findings to **REUSE, not re-derive** (§22 lists them: `if_exists="upsert"` is a no-op → `comms.install_override`;
   chain readable post-lifecycle in `il.mm.intelligence_mm` role `chain`, sliced per-task by `task_scope`;
   the v0 leaf step is **notional** (DM-5 makes it real); params reach phase-2 only via `task_pattern_iri`;
   `os._exit` for the MuJoCo teardown segfault; the opaque-token sanitization model).
5. `confirmation_docs/ROBOT_DEMO_DM4_L5_EXPORT_COORDINATION.md` — the live DM-4↔UI channel. **Tail sections
   are load-bearing for DM-5:** the UI owns the live `datasource.js` wiring (B1–B3); and **DM-5 owes the UI
   two things** — (a) a real refusal fixture (`outcome_classification:"dont_know"` + populated `dont_know`/
   `blame`) once the embodiment gate is real, and (b) real milestone names (the v0 `"root"` was deliberately
   left un-prettified — see §22).
6. `confirmation_docs/ROBOT_DEMO_SCENARIO.md` — the order→allocation→placement contract (resolver in
   `ROBOT_DEMO_OPEN_QUESTIONS.md §3`; per-arm 3×3 shelf + relation clauses `above/below/left/right/under`).
7. `confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md` — §2.2 `state` (`caps[]` badges incl. `GATED`/`FAULT`),
   §4 `place_order` `lines[].pos` clause shape, §5 the **Plan ▸ Resolve** producer (9→3→1) the UI awaits —
   DM-5's allocation is its natural source.
8. `confirmation_docs/ROBOT_DEMO_IP_SANITIZATION.md` — policy B + the token→generic table; `robot_demo/
   backend/sanitize.py` (canonical banned list + `TokenMap` + `plain_capacity`/`plain_task_pattern` +
   `find_leaks`) is the one place to add any new label mapping. **The wire must leave the backend clean.**
9. Shipped code you extend: `robot_demo/backend/{capacities,sim_engine,body_adapter,live_motion,
   motion_checklist,wiring,comms,brain,serializer,dm4_check}.py`. The DM-3 ⬡ atomics are registered per
   device in `capacities.py::register_embodied_capacities`; `pick`/`place_at_cell` exist as ⬡ stubs —
   DM-5 makes them ◆ assembled (real pick→place motion + cell-to-cell).
10. Memory: `robot-demo-dm4-shipped`, `pair-execution-workflow`, `no-sandbox-git-mutations`,
    `robot-demo-ip-sanitization`, `robot-demo-dm3-sim-runtime`, `mindsos-uncommitted-parked-work-2026-06-11`.

## Run the live demo (already wired — use it to eyeball DM-5)

On the Linux/Mac-Mini server: `./demo.sh up` (root helper) builds + starts the `demo-backend` and prints the
dashboard URL with the LAN IP; `./demo.sh help` lists all commands. Open `presentation.html?live=ws://<ip>:8765`.
(The browser may live on a different machine — use the server's LAN IP, not `localhost`.)

## Scope (this chat)

* **◆ assembled `pick` / `place_at_cell` / `stage_at`** — real grasp→lift→carry→place over the live sim
  (calibrate the DM-3 `motion_checklist` to a real pick-place invariant, not the coarse AABB); per-device
  embodiment (suction vs jaw) gates which arm can do what → surface the **embodiment gate** honestly
  (`caps[]` badge `GATED`, a real `dont_know` on the wrong gripper). **This produces the first real
  `outcome_classification:"dont_know"`** — drop the refusal fixture the UI is waiting on (item 5b).
* **Real allocation** replacing DM-4's fixed `arm1/home` `decide`: resolve `lines[].pos` clauses against the
  per-arm 3×3 shelf → (arm, cell); feed the **Plan ▸ Resolve** producer (WS contract §5) so that panel lives.
* **Real reasoning depth, for free:** the per-task chain now carries a real assembled step + real milestone
  names (not the v0 notional leaf / `"root"`) → `serializer.py`'s `steps[]`/`milestones[]` reflect them;
  keep `sanitize.plain_capacity` honest for any new IRIs. Re-export `fixtures/episode_audit_mgr.json` (and add
  a refusal fixture) for the UI.
* Wire into the gate flow; extend `sanitize` + `dm4_check`/a new `dm5_check`; headless tests + Linux gate.

## Do-NOT

No live `import_state` write and no `server_event` (DM-4-follow-up / DM-8 — see coordination phasing). No
Mode-B reload (post-DM-6). The UI's live `datasource.js` (B1–B3) is the **UI chat's** job, not this one.
**Zero `mindsos_*` edits** — the tree holds parked Phase-51 + other-chat `mindsos_*`/doc changes; never touch
or stage them (memory `mindsos-uncommitted-parked-work-2026-06-11`).

## Conventions

Critical-design-reviewer posture. **Before coding: reanalyze the DM-5 plan against the shipped DM-3/DM-4 code
+ the real sim — list pushbacks with options and your choice; probe, don't assume.** Record decisions in the
design log (continue §-numbering, next is §23); net-new MindsOS gaps → new `Fn`; update `ROBOT_DEMO_STATUS.md`
+ plan §8 row + the coordination doc (fixtures); write `ROBOT_DEMO_DM6_NEXT_CHAT_PROMPT.md` at the end.
**Pair-execution (strict):** Cowork builds + validates core in the 3.10 sandbox (`PYTHONPATH=. python3 -m
pytest robot_demo/tests/`; once: `pip install tomli pytest websockets --break-system-packages`); **Mac = git
only** (scoped `add` of specific `robot_demo/` + `confirmation_docs/` paths — **never `-A`**; watch the stale
`.git/index.lock` → `rm -f .git/index.lock`); **Linux = pull + run the gate** (`bash robot_demo/deploy/
run_linux_tests.sh`). Branch `robot-demo-animation`.

## Gate

A `place_order` with a real `lines[].pos` resolves to (arm, cell); the matched arm runs a ◆ assembled pick→place
verified by the motion checklist; the wrong-gripper arm honestly refuses (embodiment gate → `GATED` + real
`dont_know`); the **Plan ▸ Resolve** panel narrows 9→3→1 live; the Mode-A export shows the real assembled step +
real milestone names; the wire passes the banned-token guard; MindsOS + DM-1/2/3/4 gates stay green; zero
`mindsos_*` edits.
