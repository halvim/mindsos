# Robot Demo — next chat: DM-4 increment (Mode-A L5 export + `server_status`)

We are building the MindsOS Robot Demo. **DM-1…DM-4 core are SHIPPED and gate-green on Linux** (branch `robot-demo-animation`). This chat builds the remaining DM-4 increment — **Mode-A L5 export + `server_status`** — then the browser confirmation. Do not re-litigate settled design.

## Read first, in this order — this prompt does NOT repeat what's in these files

1. `CLAUDE.md` (root) — the 5-layer stack + working conventions.
2. `HANDOFF.md` (root) — current MindsOS state.
3. `confirmation_docs/ROBOT_DEMO_STATUS.md` — the **2026-06-12 DM-4 update** (what shipped, what remains). Start here for the workstream picture.
4. `confirmation_docs/ROBOT_DEMO_MINDSOS_DESIGN_LOG.md` **§19–§21** — the DM-4 build + the grounded findings you will REUSE (don't re-derive): the `if_exists="upsert"` behavioural no-op → `comms.install_override`; the reasoning chain is **readable after the lifecycle** in `il.mm.intelligence_mm` (role `chain`); per-task `brain.run_task` scope; reload re-registers DataStates; `os._exit` for the MuJoCo teardown segfault.
5. `confirmation_docs/ROBOT_DEMO_DM4_L5_EXPORT_COORDINATION.md` — **THE binding contract.** The locked snapshot schema, the `export_state`/`import_state`/`state_snapshot`/`import_result` + `server_status`/`server_event` frames, the phasing, and the UI's accepted answers. This is your spec; build to it.
6. `confirmation_docs/ROBOT_DEMO_IP_SANITIZATION.md` — policy B + the token→generic table. The wire leaves the backend already clean; the UI does not re-sanitize. Mode-A `reasoning` renders chain-artifact type names as **generic stage labels** ("Understood request → Chose approach → Planned → Executed → Outcome"); `server_status` says "Storage: connected" (not Falkor), no internal version.
7. `confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md` — the WS protocol the UI seam consumes.
8. The shipped DM-4 code you extend: `robot_demo/backend/{wiring,frames,ws_server,comms,bus,brain,dm4_check,main}.py`; serialization template = `robot_demo/backend/persistence.py::probe_episode_roundtrip` (ADR-0182 `_value_json` codec). Episode schema: `mindsos_knowledge/schemas/episodic_memories.py`. Chain dataclasses: `mindsos_intelligence/chain_artifacts.py`.
9. Memory: `robot-demo-dm4-shipped`, `pair-execution-workflow`, `no-sandbox-git-mutations`, `robot-demo-ip-sanitization`, `robot-demo-dm3-sim-runtime` (mujoco≥3.3.0 + sandbox-repro).

## Scope (this chat)

- **Mode-A L5 export.** Handle the WS command `export_state {mode:"episode-audit", scope:"<brain>"}` → emit `state_snapshot {kind:"episode-audit", …}` per the §D schema in the coordination doc. Serialize the chosen brain's Episodes (the 6-field `value`) + Memory nodes + `MEMORY_CONTAINS_EPISODE` edges + the **reasoning chain** (read `il.mm.intelligence_mm` `chain` graph after the lifecycle, faithful from the dataclasses, **per-task scoped** via the `TaskRun`/`run_task` scope) + resolved `task_input` + `problem_trace`. Reuse the `_value_json` codec template. **Sanitized** (behavior-level; IRIs → plain labels; chain type names → stage labels). Honesty: render empty `reasoning.*` as "not exercised," never hidden (v0 reasoning is thin — see the coordination doc).
- **`server_status` frame.** Real data: the four `login()` Sessions (P-1), `"Storage: connected"`, uptime; **drop the internal phase version**. Emit on connect + a ~2–5 s heartbeat. Sanitized.
- Wire both into `ws_server.py` (+ `wiring.py`/`main.py`); extend the **sanitization guard** + **`dm4_check`** to cover the new frames; headless tests + the Linux gate.
- **Browser confirmation** of the full DM-4 surface (`presentation.html?live=ws://<host>:8765`) on the UI host — the one check the headless gate can't make. Run instructions: `demo_ui/HOW_TO_USE.md` §2b.

## Do-NOT (later increments / phases)

- **No live import write** (`import_state`) and **no `server_event`** — those are the *next* increment (the coordination doc phases them after Mode-A/`server_status`).
- **No Mode-B demo-state reload** — deferred post-DM-6 (learned composites / taught terms / the PB-D PipelineRunner rebind don't exist until the teach/learn flow).
- **No DM-5 cognition** (◆ assembled `pick`/`place_at_cell`/`stage_at`, real `comprehension.match_items`/`planning.fulfill_order`). **Zero `mindsos_*` edits.**

## Conventions

Critical-design-reviewer posture (project instructions). **Before coding: reanalyze the locked schema + phasing against the shipped `robot_demo/` code + `il.mm` shape, list pushbacks with options and your choice.** Record every decision in `ROBOT_DEMO_MINDSOS_DESIGN_LOG.md` (continue the §-numbering). Any net-new MindsOS feature → a new `Fn` in `DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md`. Update `ROBOT_DEMO_STATUS.md` + the plan §8 row at the milestone, and write `ROBOT_DEMO_DM5_NEXT_CHAT_PROMPT.md` at the end. **Pair-execution (strict):** Cowork builds/validates-core (3.10 sandbox; `tomli`, and `mujoco==3.3.0` for live repro); **Mac = git only** (`add` scoped paths — the tree holds other chats' parked work, NEVER `git add -A`; watch the stale `.git/index.lock`); **Linux = `git pull` then runs + tests ALL code** (`run_linux_tests.sh`, the authoritative gate). Branch `robot-demo-animation`.

## Gate (this increment)

A client sends `export_state(episode-audit, <brain>)` and receives a `state_snapshot` whose `episodes[]` + linked `reasoning` chain are well-formed and **sanitized**; `server_status` reports 4 sessions + "Storage: connected" + uptime; the wire passes the **banned-token guard**; `dm4_check` extended to assert both; MindsOS cumulative gate + DM-1/2/3/4 gates stay green; **zero `mindsos_*` edits**.
