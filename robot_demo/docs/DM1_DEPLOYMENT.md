# DM-1 — architecture & deployment walkthrough

How the DM-1 backend is built, why it's shaped this way, and how to run and
extend it. Companion to the top-level `robot_demo/README.md`; the decision
trail is in `confirmation_docs/ROBOT_DEMO_MINDSOS_DESIGN_LOG.md`.

## 1. The per-device-instance model

The demo's four brains are **four independent MindsOS installs** co-resident in
one process:

| Brain | `device_type` | Body | L2 / L3 / L4 |
|---|---|---|---|
| `mgr` | `manager` | none (cognitive) | own KL / CL / IL |
| `arm1` | `arm-suction` | suction arm | own KL / CL / IL |
| `arm2` | `arm-jaw` | parallel-jaw arm | own KL / CL / IL |
| `conv` | `conveyor` | reversible belt | own KL / CL / IL |

Only **L2** changed from the earlier "one shared Global" plan — L3 and L4 were
already per-instance. The Server (auth/sessions/audit, `server.db`) is shared:
it's the runtime envelope, not on the layer-composition axis. Because everything
is one process, there is **no cross-process Global sync** — the eventual
inter-brain traffic (peer skill transfer, DM-7) rides an in-process bus, not a
shared graph.

Why per-device: it models how MindsOS will really ship — installed per device
type, each provisioning the capabilities its body needs ("MindsOS knows where it
is", P-8 / F7) — and it makes the DM-7 peer transfer a genuine
**cross-installation** Local→Local share.

## 2. Bootstrap sequence (`backend/bootstrap.py`)

Run on container start; **idempotent** (re-boot safe).

0. **Init `server.db` schema** — `mindsos_server._schema.init_or_migrate(conn)`
   over a connection from the shipped `mindsos_server._db.open_db()` context
   manager (WAL + `foreign_keys=ON` + `busy_timeout`). Required before any
   `insert_user` on a fresh volume — the omission of this step was the one real
   bootstrap-blocker found in review (design log PB-S).
1. **Admin** — get-or-create via `_insert_first_admin` (existence-checked, not
   catch-and-swallow; P6).
2. **4 brain users** — `insert_user(..., actor_role="user")`; `USER_CAPS` is
   empty in v1, so a brain's Local writes ride the ADR-0180 `writeable` gate
   (the gate only fires on **Global** writes; a normal-user Local consolidate
   needs no `CAN_WRITE_GLOBAL`).
3. **Real `login()`** per user → a real `Session` (not `Session.for_testing`;
   P9 — the whole point of the shared Server is that auth is real machinery).
4. **Per-device stack** (`backend/brain.py::build_brain_stack`): for each
   profile, build the brain's own `KnowledgeLayer` (fresh in-memory at DM-1,
   renamed per device — PB-J), install the builtin catalog into its
   `CapacityLayer`, construct and `.start()` its `IntelligenceLayer`
   (`dream_interval_s=None` — dreaming off), then bind an `Orchestrator` to the
   IL's MM. (`il.mm` exists only after `start()`, so order matters — P5.)
5. **Smoke** — for each brain: assert `consolidation_enabled(dispatcher)` is
   `True` (guards against a silent graceful-skip — PB-Q), `il.enqueue(...)` a
   trivial `run_lifecycle` onto the worker pool, and assert one Episode lands in
   the brain's own Local `episodic_memories`. Gate: **4 Episodes**.

DM-1 deliberately **stubs** steps that belong to later phases: skill bundles
(DM-2), Local seeds (DM-2), demo L3 capacities (DM-3), bus/sim/UI (DM-4+). These
are marked with `# DM-2`/`# DM-3` comments in `bootstrap.py`.

## 3. Why these wiring choices (grounded in shipped code)

- **Builtin catalog = the `install_*` functions**, not `create_global`:
  `install_planning_v0 + install_phase1_v0 + install_orchestration_v0 +
  install_consolidate_capacities + reset_v0_verdicts` — exactly what a trivial
  `run_lifecycle` dispatches and what `consolidation_enabled` requires. Matches
  `tests/phase_47/_fixtures.py` + `tests/phase_49/integration_c.py`.
- **The chain artifacts are honest for free.** `phase_1.run` emits HintSet /
  MappingResult **from the dispatched capacity's outputs**, so when the demo
  later overrides the v0 capacity IRIs (DM-4), the reasoning panels render real
  content with zero edits to `mindsos_intelligence`. The fallback "capacities
  write the chain via `mm_handle`" is impossible — `mm_handle` is read-only and
  a capacity body never receives the writer (design log PB-B/P1).
- **`capacity-gaps` is recorded in each device's Local**, not Global: the
  shipped role is Global-tier/admin-gated, so a brain can't write it live in
  either model (PB-K). The Manager learns gaps via reports (DM-4).
- **`promoted-pipelines` has no Local storage tier**, so DM-2+ learned
  composites live in Local `capacity-state` as a `LearnedComposite` node, name-
  mirrored only (PB-2 / §4.3).

## 4. Build & packaging

The core image installs deps from a hash-pinned `requirements.txt` then
`pip install --no-deps .` — so a `pyproject` extras group is **never installed**
(design log PB-O). The demo's heavy deps therefore ride a **separate**
hash-pinned `robot_demo/requirements-demo.txt`.

The demo image **owns its Dockerfile** (`robot_demo/deploy/Dockerfile`) and is
`FROM mindsos:<phase>-prod` (the already-built core image) + the demo deps +
the `robot_demo` package — so the **core `Dockerfile` stays demo-free** (design
log §8). Build order: build the core `prod` image first, then the demo image
(`run_linux_tests.sh` does both; base tag overridable via `MINDSOS_BASE`). The
compose service is an overlay (`deploy/docker-compose.demo.yml`) merged with the
root compose so it reuses the existing `falkordb`.

This in-repo "own Dockerfile FROM prod" shape is the deliberate alternative to a
**separate repo**: the demo still tracks HEAD (it imports `mindsos_server`
*private* internals today — `_db.open_db`, `_schema.init_or_migrate`,
`_insert_first_admin`), which a versioned repo boundary would make brittle. A
split is revisited at demo-v1-stable, once the demo depends only on a *public*
mindsos bootstrap API.

## 5. Measurements (`backend/measure.py`)

- **RAM** under the full 4-brain stack (now 4 Globals, not 1 — PB-N), feeding
  Mac-Mini sizing.
- **Sim-jitter proxy**: a 50 Hz busy stepping thread (the sim stand-in; real
  MuJoCo loop is DM-3) while the 4 ILs loop enqueued trivial lifecycles. Reports
  the step-interval distribution; **provisional** gate p99 ≤ 2× nominal. The
  real bar lands in DM-3 — synthetic numbers won't transfer.

## 6. Running

| Goal | Command |
|---|---|
| Core scenario (any host) | `PYTHONPATH=. python3 -m pytest robot_demo/tests/ -q` |
| Real-server scenario (3.12) | `PYTHONPATH=. python3 -m pytest robot_demo/tests/ -m integration -q` |
| Linux deployment gate | `bash robot_demo/deploy/run_linux_tests.sh` |
| Run for real (stays up) | see `deploy/README.md` |

## 7. What's NOT here yet (next phases)

DM-2 L2 seeds + 3 device-type skill bundles + per-device Falkor persistence ·
DM-3 body adapter + atomic capacities + live motion · DM-4 BrainBus + `comms.*`
+ first UI slice (**first browser-linked live test**) · DM-5…DM-9 cognition,
learning loop, transfer/gate/degradation, full UI, rehearsal.

## 8. Hard rules honored

Zero edits to `mindsos_*` (additive registration only); commits are Mac-only
(no git from the sandbox); per-phase tests live in `robot_demo/tests/` outside
the MindsOS cumulative gate.
