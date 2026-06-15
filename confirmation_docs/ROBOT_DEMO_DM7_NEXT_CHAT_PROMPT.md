# Robot Demo — DM-7 next-chat prompt (teach → peer-transfer → carrier-box cooperation)

We are building the MindsOS Robot Demo. **DM-1…DM-6 are SHIPPED and Linux-gate green** on branch
`robot-demo-animation`. DM-6 closed the degradation + closed-loop verify→replan + manager-reroute beat
(`DM-6 GATE PASS`). This chat builds **DM-7: the teach → peer-transfer → carrier-box cooperation beat**
(scenario §3 beat 4 + the two-arm/conveyor cooperation Plan). **Do not re-litigate settled design.**

## Read first, in this order (pointer-style — this prompt does NOT repeat what's in the files)

1. `CLAUDE.md` (root) + `HANDOFF.md` (root).
2. `confirmation_docs/ROBOT_DEMO_STATUS.md` — **start here.** The **2026-06-14/15 DM-6 SHIPPED** update is the
   current end-state (what's live, the new `robot_demo/backend` surface, what's deferred).
3. `confirmation_docs/ROBOT_DEMO_MINDSOS_DESIGN_LOG.md` **§26** (DM-6 ship) + **§25/§25.A** (DM-6 decisions to
   **REUSE, not re-derive** — the per-CL override seam, the fault stash, thin-marker replans, the
   freeze-insensitive motion path, the disjoint-reach/conveyor facts, manager `max_workers=1`). Earlier
   §15–§24 = DM-3/4/5 grounded findings (the ◆-composes-⬡ pattern, the cartesian reach, the `install_override`
   seam, the IP-sanitization producer).
4. `confirmation_docs/ROBOT_DEMO_SCENARIO.md` — **beat 4** (teach a skill on one arm → it learns →
   peer-transfers to the other arm → the receiver uses it) **+ the carrier-box cooperation** sections
   (two arms + the conveyor cooperating to move a carrier the geometry forbids a single arm from handling).
5. `confirmation_docs/DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md` — the net-new MindsOS features the demo
   needs design for: **F1 peer Local↔Local learning**, **F2 teachable vocabulary**, **F6 box-as-resource**
   (carrier box), the Pipeline/Plan split. DM-7 is where these get realized or scoped.
6. `confirmation_docs/ROBOT_DEMO_UI_BACKEND_COORDINATION.md` (the **active** UI↔backend channel; supersedes
   `ROBOT_DEMO_DM4_L5_EXPORT_COORDINATION.md`). Open backend-owed item carried into DM-7: the **per-step
   `reasoning.verification[]` export surface** (UI-agreed follow-on; entry shape already **frozen** there) —
   decide whether DM-7 ships it. `state.cbeat` + both manager fixtures already delivered.
7. `confirmation_docs/ROBOT_DEMO_OPEN_QUESTIONS.md` (locks/open) + `confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md`
   (frames/commands) + `confirmation_docs/ROBOT_DEMO_IP_SANITIZATION.md` (policy B vocabulary).
8. Memory: `robot-demo-dm6-shipped`, `robot-demo-dm5-built`, `pair-execution-workflow`,
   `no-sandbox-git-mutations`, `robot-demo-ip-sanitization`, `robot-demo-dm3-sim-runtime`,
   `mindsos-uncommitted-parked-work-2026-06-11`.

## Scope (this chat)

* **Teach a skill/movement on one arm** (the operator-teach flow — see scenario beat 4 + F2). The taught
  artifact becomes a **learned, L2-stored, L4-selectable** capability — but **resolve the OPEN DESIGN
  QUESTION first** (carried from the DM-6 prompt, still undecided): *how* a movement lives in L2. The grounded
  reframe: L2 is **not** a trajectory store — put the **capability** (a Pipeline in `promoted-pipelines`) + a
  **cache key/reference** (in `learned-parameters`) in L2, keep the trajectory blob in a motion store (the
  DM-3 `TrajectoryCache` / clips). Two framings to pick between: **(a)** a pre-baked library shipped with the
  fleet ("knows-some"), or **(b)** the authored clips as **cache pre-fill for capabilities learned on stage**
  (preserves the "starts ignorant, learns everything" thesis — the recommended framing). **Surface this to the
  user early; record the pick** in `DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md` + one line in the Pipeline
  artifact contract (`ROBOT_DEMO_SCENARIO.md §5.1`).
* **Peer-transfer (Local↔Local, F1).** Realize the `comms.share_to_peer` path (it's a **stub** today —
  `robot_demo/backend/comms.py`, returns `{"status":"deferred","note":"DM-7"}`): the taught capability/params
  transfer from one arm's Local to the peer's Local; the receiver can then perform the skill. Graph-honest +
  IP-sanitized.
* **Carrier-box cooperation Plan (F6).** The two arms + conveyor cooperate on a carrier the geometry forbids a
  single arm from completing — a real multi-step Plan (decompose → per-arm/conveyor steps → synchronize). This
  is the first **multi-leaf decompose** with real cross-device coordination (DM-6 plans were flat).
* **UI:** surface the teach/transfer/cooperation beats on the wire (behavior-level, policy B). Decide the
  per-step `verification[]` export surface (frozen shape in the coordination doc) — ship it here or defer.

## Carry-forward from DM-6 (read §26 — don't re-derive)

* The closed-loop substrate is live: `ReplanVerdict.divergence`/`should_replan`/`sufficient` (MindsOS) +
  the demo verification capability. **Message discipline:** MindsOS substrate + installed capability; never
  "MindsOS ships X". Policy B holds on every wire/panel string.
* The orchestrator replan loop re-executes the **same** plan (hollow v0 execution) → real behavior lives in
  the demo motion/manager bodies; the orchestrator emits **thin-marker** chain artifacts. A real multi-leaf
  Plan (carrier-box) will exercise `plan_construction`/`execution` more than anything so far — **probe how the
  shipped v0 lifecycle handles a >1-leaf decompose with cross-device steps before assuming** (DM-5 §23 probed
  a >1-leaf decompose; extend that).
* Deferred and still open: the cinematic `combo_*` clip-replay (needs a `SimEngine` event-bearing trajectory
  channel + cache pre-fill — ties directly into the "learned movements in L2" pick above); Mode-B demo-state
  reload (`export_state{mode:"demo-state"}` — needs the learn flow, so it may unblock here).

## Do-NOT

**Zero `mindsos_*` edits.** **Zero vendored `sim/` edits** (`robot_demo/backend/sim_engine.py` is demo code and
editable; the vendored `sim/` package is not). The tree may hold parked Phase-51 + other-chat `mindsos_*`/`sim/`
changes — never touch or stage them (memory `mindsos-uncommitted-parked-work-2026-06-11`). No teach/learn
shortcuts that fabricate the chain (no-fabrication rule — real exports only).

## Conventions

Critical-design-reviewer posture. **Before coding: reanalyze the DM-7 plan against the shipped code + the real
sim — list pushbacks with options + your choice; probe, don't assume** (every DM-3…DM-6 chat caught a brief ask
that was wrong this way — expect the same, especially around peer-transfer auth/scope and the multi-leaf Plan).
Record decisions in the design log (continue §-numbering, next is **§27**); net-new MindsOS gaps → a new `Fn`
in `DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md`; update `ROBOT_DEMO_STATUS.md` + the active coordination doc;
write `ROBOT_DEMO_DM8_NEXT_CHAT_PROMPT.md` at the end. **Pair-execution (strict):** Cowork builds + validates
core in the 3.10 sandbox (`PYTHONPATH=. python3 -m pytest robot_demo/tests/`; once:
`pip install tomli pytest websockets --break-system-packages`); **Mac = git only** (scoped `add` of specific
`robot_demo/`+`confirmation_docs/` paths — **never `-A`**; clear a stale `.git/index.lock`); **Linux = pull +
run the gate** (`run_linux_tests.sh` + the in-container `dm*_check` modules; rebuild `demo-backend` after any
baked-source change). Branch `robot-demo-animation`.

## Gate

A skill is **taught** on one arm (real learned capability/params in L2 per the chosen framing), **peer-transfers**
to the other arm's Local (real `share_to_peer`, not the stub), and the **receiver performs it**; the **carrier-box
cooperation Plan** runs as a real multi-leaf decompose with the two arms + conveyor coordinating to completion;
the wire passes the banned-token guard; the Mode-A export renders the new beats honestly (no fabrication);
MindsOS + DM-1..DM-6 gates stay green; zero `mindsos_*` / vendored `sim/` edits.
