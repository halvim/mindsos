# Robot Demo — DM-6 next-chat prompt (degradation + replan; the resilience beat)

We are building the MindsOS Robot Demo. **DM-1…DM-5 are SHIPPED and Linux-gate green** on branch
`robot-demo-animation` (DM-5 = ◆ assembled `pick`/`place_at_cell`/`conv.stage_at` + the embodiment gate +
real allocation; gate green 2026-06-13, commits `98e7c5e`/`6ba794f`; the ◆ cartesian motion passed the gate
**first try**). This chat builds **DM-6: the degradation + replan beat (scenario §3 beat 5)** — a partial fault is injected
(a frozen joint), the self-diagnosis capability writes a `capacity-gap`, the Manager **sees the gap and
replans** (reroutes), and the chain carries a **real `ReplanRecord`/`BlameVerdict`** (the first real replan
content — v0 happy-path leaves them empty). **Do not re-litigate settled design.**

## Read first, in this order (pointer-style — this prompt does NOT repeat the files)

1. `CLAUDE.md` (root) + `HANDOFF.md` (root).
2. `confirmation_docs/ROBOT_DEMO_STATUS.md` — **start here.** The 2026-06-13 DM-5 "SHIPPED" update = current
   end-state (gate green; ◆ motion first-try pass).
3. `confirmation_docs/ROBOT_DEMO_MINDSOS_DESIGN_LOG.md` §15–§24 — the DM-3/4/5 builds + grounded findings to
   **REUSE, not re-derive.** §23–§24 are DM-5: the override seam (`predicate.sufficient`/`phase6.attribute_blame`
   per-CL, single-flight stash), the dont-know path (`sufficient=False` + `should_replan="continue"` →
   `phase_6.diagnose`), the >1-leaf-decompose probe, the ◆-composes-⬡ pattern, the Linux-gated cartesian reach.
4. `confirmation_docs/ROBOT_DEMO_SCENARIO.md` §3 beat 5 + §6 L-3 (fault-injection: hybrid visible freeze +
   self-diagnosis; **partial** degradation so a recovery path exists) and §5.2 (degradation disables an
   affordance → the gap reappears → replan).
5. `confirmation_docs/ROBOT_DEMO_DM4_L5_EXPORT_COORDINATION.md` (tail) — the DM-5↔UI handoff, all closed:
   the **a1 fixture now carries TWO real episodes** (succeeded + refusal) in
   `confirmation_docs/fixtures/episode_audit_arm1_refusal.json`; "real milestone names" is **re-stated as
   depth+labels** (don't re-promise names — `plan_construction` mints them, not overridable); the `resolve`
   frame is a live producer; the arm `task_input` is a dispatch, not a user order. DM-6 owes the UI the **real
   `ReplanRecord`/`BlameVerdict`** content in the Mode-A export (the audit view's replan/blame fields go
   non-null on a real replan).
6. Shipped code you extend: `robot_demo/backend/{sim_engine,capacities,gate,wiring,serializer,brain}.py`.
   The fault machinery already exists from DM-3: `SimEngine.freeze_joint`/`clear_freezes`/`probe_actuators`
   + `capacities.make_diagnose_impl` (writes a `capacity_gap` `CapacitySnapshot` to the brain's Local via the
   `make_writeable` closure). DM-6 wires **diagnose → gap → the Manager's replan** over the real lifecycle.
7. Memory: `robot-demo-dm4-shipped`, `pair-execution-workflow`, `no-sandbox-git-mutations`,
   `robot-demo-ip-sanitization`, `robot-demo-dm3-sim-runtime`, `mindsos-uncommitted-parked-work-2026-06-11`.

## Scope (this chat)

* **Real replan over the shipped v0 path.** The orchestrator already branches on `replan_check.check` →
   `"replan"` (probed in §23: `should_replan` is the overridable `decision.should_replan` capacity; the v0
   default is `"continue"`). Drive a replan by overriding `should_replan` from the gap state: a detected
   `capacity_gap` → `"replan"` (bounded by the per-task budget) → the chain emits a **real `ReplanRecord`**;
   on a true dead-end → the dont-know path emits a **real `BlameVerdict`** (DM-5 already wired the serializer
   to render `reasoning.blame`/`replans` — they go non-null here).
* **Fault → self-diagnosis → gap → Manager replan.** Inject `freeze_joint` (visible), run `diagnose_actuators`
   (already writes the Local `capacity_gap`), surface it to the Manager (a `capacity-state`/`capacity-gaps`
   read or a `report` `capacity-gap` status), and have the Manager reroute (re-allocate to the healthy arm /
   re-stage). Surface the `FAULT` cap badge + a `fault` flag (WS §2.2).
* **Mode-A export shows the real replan/blame.** Re-export a fixture with a populated `reasoning.replans`
   (and `blame` on the dead-end coda) for the UI. Extend `sanitize`/`dm5_check`→`dm6_check`; headless tests +
   Linux gate.

## Carry-forward from DM-5 (read §24 — don't re-derive)

* **DM-5 motion is gate-green but the stand-offs are coarse.** `sim_engine.item_grasp_target`/`cell_target`
   are first-cut offsets that held first try (the proximity-gated attach + warm-started IK absorbed them) —
   no calibration debt blocks you, but they're approximate. If DM-6's reroute exercises new cells/items and a
   `motion_checklist` edge shows, that's the place to tune (DM-3 §18 pattern); don't assume they're tight.
* **OPEN DESIGN QUESTION raised this chat (NOT decided) — "learned movements in L2, chosen by L4."** The
   user wants the authored clips (`web/anim_*.json`) to become *learned, L2-stored, L4-selectable movements*.
   Grounded reframe (discussed, not written down yet): **L2 is not a trajectory store** — put the *capability*
   (Pipeline in `promoted-pipelines`) + a *cache key/reference* (in `learned-parameters`) in L2, keep the
   trajectory blob in a motion store (the DM-3 `TrajectoryCache` / clips). And it tensions the "learns
   everything, starts ignorant" thesis. **Two framings to pick:** (a) a pre-baked library shipped with the
   fleet (knows-some), or (b) the clips as **cache pre-fill for capabilities learned on stage** (the DM-8
   cache-fill PB-OO already anticipates; preserves the thesis — recommended). **Where to record once picked:**
   a new `Fn` in `confirmation_docs/DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md` + one line in the Pipeline
   artifact contract (`ROBOT_DEMO_SCENARIO.md §5.1`). Surface this to the user early — it may reshape DM-6/DM-8.
* **Deferred (NOT DM-6 unless you choose):** the cinematic `combo_*` clip-replay (DM-5 PB-1a — needs a
   `SimEngine` event-bearing trajectory channel + cache pre-fill); the teach/peer-transfer flow + the
   carrier-box cooperation Plan (DM-7); Mode-B reload (post-DM-6).

## Do-NOT

No teach/learn flow or peer-transfer (DM-7). No Mode-B reload. No cinematic clip-replay unless explicitly
chosen (cost in §23 PB-1a). **Zero `mindsos_*` edits** — the tree holds parked Phase-51 + other-chat
`mindsos_*`/`sim/` changes; never touch or stage them (memory `mindsos-uncommitted-parked-work-2026-06-11`).

## Conventions

Critical-design-reviewer posture. **Before coding: reanalyze the DM-6 plan against the shipped code + the
real sim — list pushbacks with options + your choice; probe, don't assume** (the DM-5 reanalysis refuted two
brief asks — expect the same). Record decisions in the design log (continue §-numbering, next is §25);
net-new MindsOS gaps → new `Fn`; update `ROBOT_DEMO_STATUS.md` + the coordination doc (fixtures); write
`ROBOT_DEMO_DM7_NEXT_CHAT_PROMPT.md` at the end. **Pair-execution (strict):** Cowork builds + validates core
in the 3.10 sandbox (`PYTHONPATH=. python3 -m pytest robot_demo/tests/`; once:
`pip install tomli pytest websockets --break-system-packages`); **Mac = git only** (scoped `add` of specific
`robot_demo/`+`confirmation_docs/` paths — **never `-A`**; watch the stale `.git/index.lock`); **Linux =
pull + run the gate**. Branch `robot-demo-animation`.

## Gate

A fault is injected (visible frozen joint), self-diagnosis writes a real `capacity_gap`, the Manager sees it
and **replans** (reroutes) — the chain carries a real `ReplanRecord`; a dead-end coda surfaces a real
`BlameVerdict` + a `dont_know`; the `FAULT` badge shows; the Mode-A export renders non-null `replans`/`blame`;
the wire passes the banned-token guard; MindsOS + DM-1..DM-5 gates stay green; zero `mindsos_*` edits.
