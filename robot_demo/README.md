# Robot Demo (`robot_demo/`)

MindsOS as a layered robot brain: four independent MindsOS **device-instances**
(a Manager + two arms + a conveyor) cooperating to fulfill orders, learning the
skills they're missing, sharing them within the limits of their bodies, and
showing their reasoning the whole time.

This folder is a **consumer** of the shipped MindsOS stack (like the CLI): it
imports downward into the `mindsos_*` packages and never edits them. It ships no
ADRs.

- **Plan:** `confirmation_docs/ROBOT_DEMO_MINDSOS_PLAN.md`
- **Why (decision/pushback trail):** `confirmation_docs/ROBOT_DEMO_MINDSOS_DESIGN_LOG.md`
- **Scenario / contracts:** `confirmation_docs/ROBOT_DEMO_SCENARIO.md`

## Status — DM-1 (deployment + bootstrap) landed

DM-1 stands up the runtime and proves the substrate works. It does **not** yet
include L2 seeds, demo L3 capacities, the inter-brain bus, the sim, or any UI
(those are DM-2…DM-9).

## What landed, and why

**One process, four independent MindsOS installs.** Each device-instance has its
**own** `KnowledgeLayer` (Global + Local L2), `CapacityLayer` (L3), and
`IntelligenceLayer` (L4). The Server (auth/sessions/audit) is shared — it's the
runtime envelope, not a domain layer. This models the real future: MindsOS
installed per device type (computer / phone / robot), each provisioning the
capabilities its body needs.

```
┌───────────────── one process (Linux server) ─────────────────┐
│  shared Server: server.db (auth / sessions / audit)           │
│                                                               │
│   mgr            arm1            arm2            conv          │
│  ┌──────┐      ┌──────┐        ┌──────┐        ┌──────┐        │
│  │ KL   │      │ KL   │        │ KL   │        │ KL   │  L2    │
│  │ CL   │      │ CL   │        │ CL   │        │ CL   │  L3    │
│  │ IL   │      │ IL   │        │ IL   │        │ IL   │  L4    │
│  └──────┘      └──────┘        └──────┘        └──────┘        │
│  manager      arm-suction      arm-jaw        conveyor        │
│         (each boots from a DeviceProfile, P-8)                │
└───────────────────────────────────────────────────────────────┘
```

Each instance boots from a **`DeviceProfile`** carrying its `device_type` — the
"MindsOS knows where it is" feature (P-8; future MindsOS design tracked as F7).
At DM-1 the profile only selects naming + worker counts; device-type-exclusive
capability install lands in DM-2/DM-3.

The shipped six-phase lifecycle dispatches **v0 placeholder catalogs** today, so
DM-1 wires the real builtin catalog (`planning_v0` + `phase1_v0` +
`orchestration_v0` + `consolidate`) into each brain and runs one trivial task
per brain. Consolidation writes each brain's **own** Local `episodic_memories`
— the gate is **4 Episodes from 4 independent installs**.

For the full reasoning behind each choice (per-device L2, the read-only
`mm_handle`, the `--no-deps` lockfile, the `capacity-gaps` re-home, the
server.db schema-init, …), see the design log Rounds 2.5–5.

## Layout

```
robot_demo/
  backend/          the runtime package (import `robot_demo.backend`)
    profiles.py     DeviceProfile + the 4 device-instances (P-8)
    brain.py        per-device KL+CL+IL+Orchestrator assembly
    bootstrap.py    schema init → admin → 4 users → login → 4 brains → smoke
    main.py         entrypoint (`python -m robot_demo.backend.main`)
    reset.py        between-run reset (G-11; restart-based)
    measure.py      RAM + sim-jitter proxy (PB-E / P7)
  tests/            scenario tests (NOT in the MindsOS cumulative gate)
  docs/             DM1_DEPLOYMENT.md — architecture + bootstrap walkthrough
  deploy/           compose overlay + run_linux_tests.sh + server guide
  requirements-demo.in   demo-only deps (separate hash-pinned lockfile)
```

## Quick start

**Dev loop (any host with the repo importable):**

```bash
# core scenario tests (duck sessions — no mindsos_server, runs on 3.10+)
PYTHONPATH=. python3 -m pytest robot_demo/tests/ -q
```

**Real bootstrap + smoke (Python 3.12 host — mindsos_server needs 3.11+):**

```bash
PYTHONPATH=. python3 -m pytest robot_demo/tests/ -m integration -q
```

**On the Linux server (the deployment gate):**

```bash
bash robot_demo/deploy/run_linux_tests.sh
```

See `deploy/README.md` for the server runbook and `docs/DM1_DEPLOYMENT.md` for
how bootstrap works step by step.

## Testing note

DM-1 is **headless**. The container bootstrap smoke is the live end-to-end test;
the first **browser-linked** live test is **DM-4** (the thin WebSocket + one
reasoning-panel slice). We'll link the server to the browser UI then.
