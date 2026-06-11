# Robot Demo — MindsOS Implementation Plan (the final demo plan)

**Status:** authored 2026-06-10 (Cowork). This is the build plan for the MindsOS side of the demo, written against the **shipped** stack (Phases 39–50 complete; tag `phase-50-confirmed`). When this plan is implemented, the demo is complete and ready to ship.

**Supersedes/companions:** supersedes `ROBOT_DEMO_PROTOTYPE_PLAN.md` Phases C–F (stub controller dropped); companions `ROBOT_DEMO_SCENARIO.md` (the beats + the two frozen contracts), `ROBOT_DEMO_STATE.md` (motion library), `DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md` (F1–F6 — demo builds minimal versions of F1/F4/F5, see §7).

---

## 0. Decisions locked 2026-06-10

| # | Decision | Rationale |
|---|---|---|
| P-1 | **Topology: one MindsOSServer process hosting 4 independent MindsOS device-instances** (Manager, Arm 1, Arm 2, Conveyor). Each instance = its **own `KnowledgeLayer` (own Global + own Local L2), own `CapacityLayer` (L3), own `IntelligenceLayer` (L4)**, co-resident in one process / one FalkorDB. The Server (auth/sessions/audit/`writeable` gate) is **shared** — it is the runtime envelope, not on the layer-composition axis (CLAUDE.md). 4 users/sessions, one per device. **(Revised Round-3 2026-06-10: was "one shared Global KnowledgeLayer + 4 Locals"; now per-device Global+Local — see P-8 + design-log §3 / PB-I…PB-N.)** | Showcases device-type-exclusive installation (P-8): each device is genuinely its own MindsOS install with its own L2/L3/L4. Still single-process ⇒ **no** cross-process Global sync needed (the original anti-rationale doesn't bite); the bus already carries the only cross-instance traffic (peer transfer, now genuinely cross-installation). Local/Global, peer transfer, and the `writeable` gate stay *real* shipped machinery. |
| P-2 | **Direct-to-MindsOS** — no stub controller. The Seam-B four-message contract survives as the internal inter-brain protocol, implemented as `interaction.*` capacities. | L4/L5 shipped; the stub's reason to exist is gone. |
| P-3 | **Deploy: old Mac Mini (Linux) + Docker Compose**, extending the existing `docker-compose.yml` stack; browsers over LAN (tunnel decision stays open). | Per existing locks; no server GL needed (browser renders). |
| P-4 | **Per-brain CapacityLayer** (4 in-memory `CapacityLayer` instances in the one process). Each is bootstrapped with the shipped builtin catalog, then the brain's own embodied capacities. | Embodied primitives are body-bound callables (Arm 1's `move_to` drives Arm 1's joints); separate CLs keep registration clean and make per-brain `capacity-state` truthful. Cognitive/builtin capacities are registered identically in all four. |
| P-5 | **No live Global writes during the demo** (per the resolved Governance model — admin = presenter, out-of-band). All Global seeding happens pre-demo via Phase-50 skill bundles installed by the admin. Beat-4 transfer is peer Local→Local (§7 F1-min), not promotion. | Removes the entire promotion-loop dependency (which was routed to WSD Phase 55 and is NOT available). |
| P-6 | **Plan execution is an L3 capability, not an L4 change.** The shipped Phase-47 `execution.py` dispatches only a notional step (Phase 49 finding). The demo registers a `process.execute_plan` capacity that walks a Plan's steps and dispatches each via the L4Dispatcher — keeping the Chat-A R1 boundary (L4 = substrate + control flow; decisions/computations = L3) and leaving `mindsos_intelligence` untouched. | Touching the shipped L4 lifecycle for the demo is risk with no thesis payoff; an L3 executor is exactly what the R1 boundary prescribes. |
| P-7 | **Live orders are constrained to the verified motion envelope.** Orderable targets = the cubby/action set covered by the 46 verified clips' machinery (`sim/motion.py` generators + the MOTION_RULES checklist). The pre-present data checklist runs on every generated trajectory before it is shown. | Grasp/IK reliability was the hardest Phase-B problem; an unconstrained live order is an unrehearsed trajectory on camera. |
| P-8 | **Each device-instance boots from a `DeviceProfile`** (`device_type` ∈ {`manager`, `arm-suction`, `arm-jaw`, `conveyor`}) that selects the device-type-exclusive bundles/capacities to install. A `core` bundle installs in all four; type-specific bundles install only on the matching device. Selection logic lives in `demo_backend`; the install mechanism is the shipped Phase-50 `install_skill`. **(Added Round-3 2026-06-10; net-new → F7.)** | Showcases "MindsOS knows where it is and provisions for its body." Real device detection is future MindsOS (F7); the demo uses a static profile per instance. DM-1 only plumbs the `device_type` field; selective install lands DM-2/DM-3. Zero `mindsos_*` edits. |

---

## 1. Task 3.1 — Deployment on the Linux server

### 1.1 What runs (one Compose stack on the Mac Mini)

```
┌──────────────────────── Mac Mini (Linux, Docker Compose) ────────────────────────┐
│  falkordb            (existing service; one instance, one /data volume)          │
│  demo-backend  (NEW)  one Python process containing:                             │
│    • MindsOS runtime envelope: server.db auth/sessions/audit (mindsos_server)    │
│    • 4 independent device-instances (mgr, a1, a2, conv), each =                  │
│        its own KnowledgeLayer (own Global + own Local) + CapacityLayer +         │
│        IntelligenceLayer + DeviceProfile  (P-1/P-8; per-device L2/L3/L4)         │
│    • BrainBus (in-process Seam-B message queues, §2.1)                           │
│    • MuJoCo sim loop (CPU, headless) + motion adapter (Seam C, §2.3)             │
│    • FastAPI + WebSocket: state broadcast + commands + control token (Seam A)    │
└──────────────────────────────────────────────────────────────────────────────────┘
            browsers (presenter + participants): frozen-v9-derived v10 UI, LAN/tunnel
```

New consumer package — consolidated under the umbrella folder **`robot_demo/`** (package import `robot_demo.backend`; with `tests/`, `docs/`, `deploy/` siblings — Round-6 restructure, design log §7). It imports downward like the CLI; domain layers never import it (ADR-0010). It is NOT a `mindsos_*` domain package and ships no ADRs of its own. *(The plan text below says `demo_backend` for the package's conceptual role; the shipped path is `robot_demo/backend/`.)*

### 1.2 Compose changes

Add to `docker-compose.yml` (new service, existing `falkordb` untouched):

```yaml
  demo-backend:
    build: { context: ., target: demo }   # NEW `demo` stage, FROM prod (PB-O)
    entrypoint: ["/usr/local/bin/entrypoint.sh"]   # gosu drop + chown, then run the command
    command: ["python", "-m", "demo_backend.main"]
    depends_on: { falkordb: { condition: service_healthy } }   # healthcheck exists (redis-cli ping)
    environment:
      FALKORDB_HOST: falkordb
      FALKORDB_PORT: "6379"
      DEMO_WS_PORT: "8765"
    ports: ["8765:8765", "8080:8080"]   # WS + static UI
    volumes:
      - ./.mindsos/logs:/var/log/mindsos
      - ./.mindsos/server-db:/var/lib/mindsos
```

**Dependency + COPY mechanism — corrected Round-4 (PB-O / PB-P).** The shipped `prod` stage installs deps via `pip install --require-hashes -r requirements.txt` then `pip install --no-deps .` — so a `pyproject.toml` **extras group is never installed** (deps come only from the hash-pinned lockfile), and the `prod` stage COPYs an explicit package list that excludes `demo_backend`/`sim`/`web`. The original "extras group `mindsos[demo]`" line was therefore mechanically inert. **Replacement:**

- New hash-pinned `requirements-demo.txt` (mujoco + fastapi + uvicorn + websockets), compiled from a new `requirements-demo.in`.
- New Dockerfile stage `FROM prod AS demo` that runs `pip install --require-hashes -r requirements-demo.txt` and `COPY demo_backend ./demo_backend` (DM-1) + `COPY sim ./sim` + `COPY web ./web` (DM-3) + `pip install --no-deps .` if `demo_backend` is packaged. Core `prod`/`test` images stay untouched (clean, as intended).
- The `demo-backend` compose service builds `target: demo`. Verify at build: `entrypoint.sh` passes an arbitrary `command` through the gosu drop (it forces `mindsos` only for the `mindsos` service via an explicit entrypoint override; the bare entrypoint should exec whatever command follows).

### 1.3 Bootstrap sequence (`demo_backend/bootstrap.py`, idempotent, run on container start)

> **Bootstrap is library calls, not CLI** — `demo_backend` is a downward consumer; it calls `mindsos_server`/`mindsos_knowledge` APIs directly (`insert_user`, `login`, `KnowledgeLayer.bootstrap`, …). No `mindsos` CLI on the box. All steps are **get-or-create idempotent** (P6: `insert_user` raises on duplicate → query-then-insert).

0. **Init server.db schema (PB-S, Round-5).** Open a conn via the shipped `mindsos_server._db` context manager (WAL + `foreign_keys=ON` + `busy_timeout=5000`) and call `mindsos_server._schema.init_or_migrate(conn)` — creates `users`/`sessions`/`audit` (+ migration `schema_version`). Idempotent (`CREATE TABLE IF NOT EXISTS`). **Required before any `insert_user`** — on a fresh volume the tables don't exist yet. Follow the shipped per-call-conn discipline (no long-lived conn shared across worker threads — PB-U).
1. Bootstrap admin (first run): get-or-create admin user with the `ADMIN_CAPS` (`insert_user(conn, "admin", …, actor_role="admin")`).
2. Get-or-create 4 users: `mgr`, `arm1`, `arm2`, `conv` (normal users — `USER_CAPS` empty in v1; their Local writes ride the ADR-0180 `writeable` gate, Phase 48 PB-10 fixed for exactly this case). Real `login()` per user → real `Session` (P9 — no `for_testing`).
3. **Per-device KnowledgeLayer (P-1, Round-3).** For each device, build its **own** `KnowledgeLayer`. **DM-1:** 4 fresh in-memory `KnowledgeLayer.bootstrap()` (one per device, distinct metagraph name); **no Falkor persist yet.** **DM-2:** a per-device named Falkor load-or-mint helper in `demo_backend` (`find_by_name(f"global::{device}")` → load, else mint+rename+persist) — the shipped `bootstrap_kl_from_falkordb` is single-Global-by-name and unusable as-is (PB-J). *Not* `bootstrap_global_pair_from_falkordb` (that's the pivot-release canonical+pending pair, not Global+Local).
4. *(DM-2 — stub at DM-1.)* **Admin installs the demo skill bundles per device, gated by `DeviceProfile`** (§3.4, P-8) — `install_skill(manifest, kl=device_kl, cl=device_cl, session=admin)`; `core`→all 4, type-specific→matching device only. Idempotent by bundle name+version+digest (Phase-50 S8).
5. *(DM-2 — stub at DM-1.)* Seed each device's Local (§3.3) via `make_writeable(device_kl, brain_session)` — Local writes by each brain's own session, no admin.
6. For each device: construct `CapacityLayer(kl=device_kl)` → run builtin bootstrap *(DM-3: + demo L3 installers, §4)* → `IntelligenceLayer(session, knowledge=device_kl, capacity=cl, max_workers=…, dream_interval_s=None)` → `.start()` → build `Orchestrator(L4Dispatcher(cl, session=session, kl=device_kl), il.mm)` (after `start()`, since `il.mm` is created there — P5). Hold `(session, kl, cl, il, orch, profile)` as the device's `Brain` struct.
7. *(DM-3+: start sim loop + BrainBus + WebSocket.)* **DM-1 smoke:** for each brain, `il.enqueue(lambda: orch.run_lifecycle({"task":"smoke"}, task_id=…))` + `future.result()`; assert 4 Episodes consolidate (in-memory at DM-1; Falkor flush is the DM-2 G-5 probe).

**Demo-day runbook:** `docker compose up -d` → bootstrap smoke passes → open URL → presenter takes control token → recorded backup cued. Reset = wipe each device's Local run-state roles + reload sim (script `demo_backend/reset.py`); per-device Global seeds survive.

---

## 2. Task 3.2 — Communication as MindsOS capacities

### 2.1 Inter-brain (Seam B) — `interaction.*` family, over an in-process BrainBus

Because all four brains share one process (P-1), the transport is an in-process bus (`demo_backend/bus.py`: one inbox `queue.Queue` per brain + a publish/subscribe map). The MindsOS-visible surface is **four interaction capacities** registered in every brain's CL — the frozen Seam-B verbs, nothing more:

| Capacity (IRI `capacity:interaction:<name>`) | Family (dont-know shape) | Consumes → Produces | Semantics |
|---|---|---|---|
| `comms.query_capabilities` | retrieval (OPTIONAL_RETURN) | `DS_CAP_QUERY` → `DS_CAP_REPORT` | **Push-cache model (PB-C, §10):** each brain *pushes* its capability report to the Manager at boot and on every `capacity-state` change (new composite, gap appears/clears); the Manager's capacity reads its local cache. No synchronous cross-brain round-trip inside a running capacity — eliminates the worker-thread block/deadlock class. The pull form exists only as a cache-miss fallback with timeout |
| `comms.dispatch` | signalling (OPTIONAL_RETURN) | `DS_DISPATCH_CMD` → `DS_DISPATCH_ACK` | Manager → brain: "run capacity X with params P as task T". Receiving brain enqueues a lifecycle run (§5). |
| `comms.report` | signalling (OPTIONAL_RETURN) | `DS_TASK_OUTCOME` → `DS_REPORT_SENT` | Brain → Manager: success / fail / dont-know (+ family dont-know payload) / capacity-gap. Feeds Manager's monitors. |
| `comms.share_to_peer` | signalling (OPTIONAL_RETURN) | `DS_SHARE_ARTIFACT` → `DS_SHARE_ACK` | Peer Local→Local transfer (beat 4). Sender ships the Pipeline artifact over the bus; **the receiver writes its own Local** via its own `writeable` — so no new authorization capability is required (§7 F1-min). |

Note `interaction` is an unkeyed FAMILY_RULES category (Phase 42 deferred set), so the four capacities register under keyed families as shown (retrieval/signalling) while keeping `interaction`-style names — confirm at build time; if `DEFERRED_DEFAULT_CATEGORIES` handling suffices, plain `interaction` category is fine.

The bus is injected into the capacity implementations as a closure at registration (same pattern as binding motion generators, §2.3). If the topology ever splits into processes, only `bus.py` changes — the capacity contracts don't.

### 2.2 Demo System (Seam A) — backend ↔ browsers, shared with participants

The Demo System (sim + UI backend) is *outside* MindsOS; brains talk to it through capacities, participants through WebSocket:

- **Inbound (user → Manager):** the WS `place_order` / `teach` / `sort` commands are converted by the backend into Manager task submissions: `mgr_intelligence.enqueue(lambda: mgr_orch.run_lifecycle({"order": lines}, task_id=…), tier=TierEnum.FOREGROUND)`. The order payload enters MindsOS as `DS_ORDER` — i.e., **the UI is a perception source**, on-thesis.
- **Outbound (brains → UI):** a `trace.demo_events` capacity (trace family, DATASTATE_MARKER) registered in all brains appends thinking events (intent, chain level, dont-know, gap, decision) to a ring buffer the broadcaster drains at 30–60 Hz into the WS `state` frame — the exact `brains:{mgr,a1,a2,conv}` schema already frozen in `ROBOT_DEMO_PROTOTYPE_PLAN.md` §4, so the v9 panel code is reused.
- **Multi-user sharing:** WS multi-client + the resolved P6.2 control-token model (one driver at a time, presenter reclaim, Reset; input limited to orders/teach/sort). Graph tab reads ride a read-only FalkorDB query endpoint in the backend (curated subgraph queries, not raw dumps).

### 2.3 Body (Seam C) — capacity → MuJoCo

`demo_backend/body_adapter.py` exposes, per embodied brain, a `BodyHandle` (submit trajectory, set gripper/suction, read poses, read joint health). The atomic L3 capacities (§4) close over their brain's `BodyHandle`. Motion generation reuses `sim/motion.py`'s combo machinery **live**: generate trajectory → run the MOTION_RULES data checklist → only then stream frames into the sim loop (P-7). Fault injection (beat 5) is a backend switch that freezes a joint; `diagnose.actuators` then *detects* it honestly.

---

## 3. Task 3.3 — L2 initial knowledge, per instance

The role-graph set is **closed at 13** (ADR-0150 §am-5/§am-6) — the demo adds **no new roles**. Placement of every demo node respects shipped storage modes (per-NodeType `storage_mode`, Phase 43).

### 3.1 Global seeds (admin, pre-demo, via skill bundles §3.4)

| Role | Demo content |
|---|---|
| `ontology` | `ItemKind:{Box,Sheet,Tube}`; `Affordance:{grasp:suction, grasp:jaw, reach:<region>}`; requires-edges: Sheet→grasp:suction, Tube→grasp:jaw, Box→(grasp:suction ∨ grasp:jaw); regions `{shelf_L, shelf_R, belt_a1, belt_mid, belt_a2}`; `ShelfCell` 3×3 grid model (r0–r2 × c0–c2); belt geometry constants (feeder/collector positions, staging band) |
| `lexicon` | order vocabulary (`box`,`sheet`,`tube`,`place`,`into`, bin/cell names); **seed position terms** (F2 seed set): `center`, `top-left`, … as cell-sets; `above`,`below`,`left-of`,`right-of` as grid offsets. Each term = lexicon entry → grounded concept (offset | cell-set) — the teachable-vocabulary substrate |
| `concepts` | `Order`, `OrderLine(target_cell, item_kind, qty)`, `Carrier`, `Cargo`, `Handoff`, `Workaround` |
| `task-patterns` | `task-pattern:demo:fulfill-order`, `:fulfill-line`, `:teach-pipeline`, `:diagnose-and-replan`. **NOT seeded: a handoff/route pattern** — pre-seeding the cross-belt route would falsify beat 1 (the scenario requires *both* the composite and the Plan to be absent at start). The route is **assembled at plan time** by `planning.route_via_reach` (§4.3) once the taught composite exists (PB-A, §10). A `task-pattern:demo:handoff-via-box` definition ships **behind a disabled fallback flag** as the rehearsed escape hatch only |
| `capacity-gaps` | **Re-homed to per-device Local `capacity-state` (PB-K, Round-3).** The shipped `capacity-gaps` role is Global-tier (`CAN_WRITE_GLOBAL` = admin) — a normal brain session cannot write it live without failing the `writeable` gate, in both the old shared-Global and new per-device model. Beats 1 & 5 record gaps in the device's **own Local** `capacity-state`; the Manager aggregates via `comms.report`. No live Global write. |
| `problem-trace` | empty — traces accumulate live |

### 3.2 What is deliberately NOT in L2

Dynamic world state (current item poses, belt occupancy) is **not** L2 knowledge — it enters per task as `DS_WORLD_FACT` perceptions and lives in the task's MM (L5), which is what makes the Manager's perceive→match→allocate beat real reasoning rather than database lookup. Static layout is Global ontology (§3.1).

### 3.3 Local seeds, per brain (each brain's own session writes via `make_writeable`)

| Brain | Local role | Seed content |
|---|---|---|
| **arm1** | `capacity-state` | **Embodiment subgraph (F4-min):** `Body(a1) —has-part→ {Arm(panda_1), EndEffector(suction_tip)}`; `suction_tip —provides→ grasp:suction`; `Body(a1) —provides→ reach:shelf_L, reach:belt_a1`; availability nodes for every §4 capacity (state: available) |
| **arm2** | `capacity-state` | same shape: `jaw_2f85 —provides→ grasp:jaw`; `reach:shelf_R, reach:belt_a2` |
| **conv** | `capacity-state` | `Body(conv) —has-part→ Belt`; `provides→ move:belt(belt_a1↔belt_mid↔belt_a2)`; staging positions (feeder, collector, mid-band marks) |
| **mgr** | `capacity-state` | no embodiment (no body) — availability nodes for cognitive capacities only |
| all 4 | `episodic_memories` | empty (runs fill it; trace recap reads it) |
| all 4 | `learned-parameters`, `parameter-staging`, `pending-promotions` | empty |

**Embodiment home decision (F4-min):** the embodiment graph lives **inside Local `capacity-state`** as new NodeTypes (`BodyPart`, `EndEffector`, `AffordanceProvision`). Rationale: the closed role set forbids a new `embodiment` role without an ADR-0150 amendment (future design, not demo work), and `capacity-state` is already the Local role the Manager queries for "what can this brain do" — affordances are the *why* behind that answer. The feasibility gate (§4, `validate.feasibility`) is a query over this subgraph + the Global requires-edges.

### 3.4 Implementation vehicle — three Phase-50 skill bundles + one Local script

Global seeds ship as **skill bundles** (`[[l2.content]]` entries target Global; installs are admin-gated through the real ADR-0180 gate — the demo eats Phase-50 dogfood):

1. `demo-world@1.0` — ontology + concepts + lexicon seeds (`tests/fixtures/skill_bundle_ref/` is the template).
2. `demo-patterns@1.0` — task-patterns.
3. `demo-capacities@1.0` — `[l3] installers = ["demo_backend.capacities:install_cognitive", …]` so the L3 catalog (§4) re-activates on every boot via `apply_installed_skills(cl, kl)`; `datastates` + `allow_new_realm = ["robot"]` for the §4 DataStates.

Local seeds (§3.3) can't ride bundles (bundle L2 content is Global-only at v1) → `demo_backend/bootstrap.py` step 5 writes them per brain session. Embodied capacity registration also can't ride bundle installers (needs the per-brain `BodyHandle` closure) → registered in step 6.

---

## 4. Task 3.4 — L3 capacities, atomic → assembled, per instance

All DataStates below register under new realm `robot` (`register_datastate(…, allow_new_realm=True)`, enabled via the bundle's `allow_new_realm` list). Naming follows the shipped `capacity:<category>:<name>` pattern. Every capacity declares `inputs`/`outputs` so registration v2 emits the `PRODUCES`/`CONSUMES` IntergraphEdges — which is what makes `find_pipeline` and the graph-viz tab honest.

### 4.0 DataStates (realm `robot`)

`DS_ORDER, DS_ORDER_LINES, DS_ALLOCATION, DS_PLAN, DS_DISPATCH_CMD, DS_DISPATCH_ACK, DS_TASK_OUTCOME, DS_CAP_QUERY, DS_CAP_REPORT, DS_SHARE_ARTIFACT, DS_SHARE_ACK, DS_WORLD_FACT, DS_POSE_TARGET, DS_MOTION_DONE, DS_GRIP_CMD, DS_GRIP_STATE, DS_PICK_GOAL, DS_HOLDING, DS_PLACE_GOAL, DS_PLACED, DS_ON_BELT, DS_IN_BOX, DS_BELT_CMD, DS_BELT_DONE, DS_STAGE_GOAL, DS_STAGED, DS_DIAG_REQUEST, DS_DIAG_REPORT, DS_TEACH_BLOCKS, DS_PIPELINE_ARTIFACT, DS_FEASIBILITY_VERDICT, DS_DEMO_EVENT`

### 4.1 Arm 1 "Lifter" (suction) — and Arm 2 "Packer" (jaw), mirrored

Ladder, bottom-up. ⬡ = atomic (wraps `BodyHandle`/`sim/motion.py`), ◆ = pre-seeded assembled, ★ = **learned live on stage** (not pre-seeded).

| Lvl | Capacity | Family (dont-know) | Consumes → Produces | Implementation |
|---|---|---|---|---|
| ⬡ | `a1.move_to` | mechanism (OPTIONAL_RETURN) | DS_POSE_TARGET → DS_MOTION_DONE | IK + waypoint generator (motion.py `Cell` machinery); checklist-gated (P-7); dont-know on unreachable pose |
| ⬡ | `a1.suction_set` (a2: `a2.jaw_set`) | mechanism | DS_GRIP_CMD → DS_GRIP_STATE | attach-on-valid-contact toggle |
| ⬡ | `a1.sense_poses` | perception (DATASTATE_MARKER) | DS_DIAG_REQUEST → DS_WORLD_FACT | reads sim body poses (the fiducial stand-in) |
| ⬡ | `a1.diagnose_actuators` | validate (VALIDATION_RESULT) | DS_DIAG_REQUEST → DS_DIAG_REPORT | compares commanded vs actual joint motion; writes gap to Local `capacity-state` + Global `capacity-gaps` on failure (beat 5) |
| ◆ | `a1.pick` | transform (DATASTATE_MARKER) | DS_PICK_GOAL → DS_HOLDING | `combo_sheet_pick`-class generator (a2: `combo_tube_pick` backward-replay) |
| ◆ | `a1.place_at_cell` | transform | DS_PLACE_GOAL → DS_PLACED | `combo_box`/`combo_sheet` generators; **primitive per scenario §0a** (demoted from learned) |
| ◆ | `a1.place_on_belt` / `a1.pick_from_belt` | transform | DS_HOLDING → DS_ON_BELT / DS_PICK_GOAL → DS_HOLDING | belt-band pick/place (combo_load_convey machinery) |
| ◆ | `validate.feasibility` | validate (VALIDATION_RESULT) | DS_PICK_GOAL∨DS_PLACE_GOAL → DS_FEASIBILITY_VERDICT | **the embodiment gate**: do my Local affordances `provide` everything the target's requires-edges demand? Refusal carries the reason ("requires grasp:suction") — beat 1's dont-know and beat 4's gate |
| ★ | `a1.load_into_box` | transform | DS_PICK_GOAL → DS_IN_BOX | **the headline taught composite** = `pick(cargo)` + present/insert + attach-on-insertion (`combo_load_convey` load half). Created at beat 2 via §7 F5-min; registered at runtime with `register_capacity(…, if_exists="raise")`; transferred to a2 at beat 4 |

Plus in both arms' CLs: shipped builtins (`text.*` not needed but harmless; `consolidate:mm`, `trace.problem`, `signalling.signal_to_tier`, `scoring.attention_score`, `decision.should_replan`, `evaluator.sufficient`, `phase6.attribute_blame`), the four `comms.*` (§2.1), and `trace.demo_events` (§2.2).

### 4.2 Conveyor

| Lvl | Capacity | Family | Consumes → Produces | Notes |
|---|---|---|---|---|
| ⬡ | `conv.run` | mechanism | DS_BELT_CMD → DS_BELT_DONE | direction + distance; moves **only on command** (the forcing invariant) |
| ⬡ | `conv.stop` | mechanism | DS_BELT_CMD → DS_BELT_DONE | |
| ◆ | `conv.stage_at` | transform | DS_STAGE_GOAL → DS_STAGED | closed-loop: run until tracked item reaches a named staging position (the conveyor's *real decision*: which item occupies the surface, which direction, staged into whose reach) |
| ◆ | `scoring.belt_schedule` | scoring (OPTIONAL_RETURN) | DS_STAGE_GOAL → DS_STAGED | orders contending stage requests (throughput) |

### 4.3 Manager (no body — all cognitive)

| Lvl | Capacity | Family | Consumes → Produces | Notes |
|---|---|---|---|---|
| ⬡ | `perception.ingest_order` | perception | DS_ORDER → DS_ORDER_LINES | UI order → typed lines (Seam A inbound) |
| ⬡ | `perception.world_snapshot` | perception | DS_DIAG_REQUEST → DS_WORLD_FACT | aggregates brains' `sense_poses` via bus |
| ◆ | `comprehension.match_items` | derivation (DATASTATE_MARKER) | DS_ORDER_LINES + DS_WORLD_FACT → DS_ALLOCATION | **the L-2 payoff**: attribute-ordered lines matched to physical items; allocation by reach + effector (consults `comms.query_capabilities` + Global requires-edges); infeasible line → dont-know (L-1 detection) |
| ◆ | `decomposition.line_to_steps` | decomposition (deferred-family) | DS_ALLOCATION → DS_PLAN | per line: same-side direct plan, or delegate cross-side routing to `planning.route_via_reach` |
| ◆ | `planning.route_via_reach` | planning (OPTIONAL_RETURN) | DS_ALLOCATION → DS_PLAN | **PB-A (§10): the cross-belt Plan is *assembled*, not canned.** Searches the tiny fixed topology graph (brain reach affordances + belt connectivity + per-brain capability cache) for a step chain that bridges source region → target region. Before beat 2 the search fails honestly (no brain provides "cargo crosses sides" — the dont-know); after the composite is taught, the same search finds `load_into_box → stage_at → pick_from_belt → place_at_cell`. Bounded: 3 embodied brains, 5 regions, ≤8 steps — depth-limited BFS, mirrors `find_pipeline` style |
| ◆ | `scoring.sequence_lines` | scoring | DS_PLAN → DS_PLAN | throughput interleave (a1 stages next while belt moves last while a2 packs previous) |
| ◆ | `planning.fulfill_order` | planning (OPTIONAL_RETURN) | DS_ORDER_LINES → DS_PLAN | the real Phase-2 planner — **replaces `planning_v0` placeholders in mgr's CL** (registered under the same names the lifecycle dispatches, see §5.2) |
| ◆ | `process.execute_plan` | process (DATASTATE_MARKER) | DS_PLAN → DS_TASK_OUTCOME | **P-6:** walks Plan steps; per step `comms.dispatch` to the owning brain, await `comms.report`, update MM; on capacity-gap/dont-know report → emits replan signal |
| ◆ | `decision.replan_on_gap` | decision (VERDICT) | DS_TASK_OUTCOME → verdict | consumed by the shipped `replan_check` (beat 5) |
| ◆ | `learning.capture_pipeline` | learning-methods (deferred-family) | DS_TEACH_BLOCKS → DS_PIPELINE_ARTIFACT | Seam-D modality 1: UI block assembly → frozen Pipeline artifact (scenario §5.1 shape) |
| ◆ | `learning.register_composite` | process | DS_PIPELINE_ARTIFACT → DS_TASK_OUTCOME | F5-min (§7): write artifact node to the target brain's Local `promoted-pipelines`* + `register_capacity` the composite in that brain's CL (over the bus — the receiving brain registers, gate-checked on receipt). **PB-D (§10): the composite's `implementation` callable is NOT the artifact** — a generic `PipelineRunner` factory in `demo_backend` binds the artifact (steps + bindings) to a callable that dispatches each sub-capacity through the brain's own dispatcher. Registration happens between lifecycle runs (the brain registers from inside its own task's terminal step), not concurrently from another thread |

\* "promoted-pipelines" is Global-tier in shipped storage; demo-time learned composites must stay Local (P-5) → the artifact node is written to the **learner's Local `capacity-state`** (as a `LearnedComposite` NodeType) and only the *name* mirrors the promoted-pipelines vocabulary. Honest annotation, not a hack: real Local→Global promotion is the WSD S10 loop, explicitly out of demo scope. **Verify at build time** whether `promoted-pipelines` per-NodeType storage_mode already admits a Local tier (Phase 43 introduced per-NodeType storage_mode) — if yes, use it and delete this asterisk.

### 4.4 The assembled ladder, end to end (what the audience sees)

```
move_to / grip  →  pick / place_at_cell / place_on_belt   (pre-seeded primitives)
                →  load_into_box                           (★ TAUGHT, beat 2)
                →  handoff-via-box                         (Orchestrator PLAN, not a capacity —
                                                            task-pattern instantiated by decomposition)
                →  fulfill-line → fulfill-order            (Manager planning + execute_plan)
```

The two-level split (within-brain composite vs Orchestrator Plan) is the frozen §5.1 contract — do not collapse it.

---

## 5. Task 3.5 — L4 intelligences, per instance

All four brains run the **same shipped substrate** — `IntelligenceLayer(session, knowledge=kl, capacity=cl_brain, max_workers, dream_interval_s=None)` — differing only in catalog + monitors. Dreaming is **off during the live demo** (no timer); a rehearsal-only dream pass is optional flavor.

| Brain | Lifecycle use | Monitors / signals | Tiers |
|---|---|---|---|
| **mgr** | Every UI command = one `run_lifecycle({"order"…}, task_id)` at FOREGROUND. Phase 1 interprets via `perception.ingest_order` + `comprehension.match_items`; plan_construction via `planning.fulfill_order`; execution dispatches `process.execute_plan` (P-6); `replan_check` consumes `decision.replan_on_gap`; phase 6 + consolidation per shipped flow | Monitor on DS_TASK_OUTCOME (reports) + a `capacity-gaps` watcher (beat 5 trigger); signal triage routes fault signals to CRITICAL | FOREGROUND orders; CRITICAL replan; BACKGROUND trace recap prep |
| **arm1 / arm2** | Each `comms.dispatch` received = `enqueue(run_lifecycle(sub_task))`. Phase 1 runs `validate.feasibility` (the gate — refusal = honest dont-know with reason, surfacing in beat 1/4); execution runs the dispatched capacity; consolidation writes the brain's own Episode | Monitor on DS_DIAG_REPORT; `diagnose_actuators` failure → signal (CRITICAL) → report to mgr | FOREGROUND dispatches |
| **conv** | Dispatches = stage/run lifecycles; `scoring.belt_schedule` arbitrates contention | none beyond reports | FOREGROUND; CRITICAL for mid-handoff stage corrections |

### 5.2 The v0-catalog problem (must not be skipped)

The shipped six-phase lifecycle dispatches the **v0 placeholder catalogs** (`planning_v0`, `phase1_v0`, `orchestration_v0`) — Phase 49 proved no real L3 step executes. **The decision criterion is not "does the lifecycle run" but "who writes the real chain artifacts" (PB-B, §10):** the UI renders HintSet/MappingResult/Plan from the MM, and `ChainArtifactWriter` is driven from inside the lifecycle phases. If the v0 phases stay placeholders, the chain fills with junk while the real reasoning happens elsewhere — the thinking panels would then be narrating fiction, which violates the never-fake rule. The approach, in order of preference, to be settled in the first build session:

1. **Same-name override:** register the demo's real implementations under the v0 capacity names (`planning.initial_plan`, `decomposition.decompose`, `process.identity`, …) in each brain's CL — if registration allows shadowing/upsert (`if_exists="upsert"`), the lifecycle dispatches demo logic with zero L4 change. **Probe first.**
2. **Configured catalog:** if the orchestrator's phase functions take/resolve capacity IRIs from the CL by name, point them at demo IRIs.
3. **Fallback:** keep v0 phases as pass-throughs and put all real work in `process.execute_plan` (P-6) — the lifecycle remains the real shipped control flow; planning/execution decisions are real L3 capacities; only the phase-internal dispatch is thinner than ideal. **If this lands, the demo capacities MUST write the chain artifacts themselves** via `CapacityContext.mm_handle` (probe: whether mm_handle exposes enough write surface, or whether a thin `ChainArtifactWriter`-wrapping capacity is needed). A chain rendered from placeholder content is disqualifying (PB-B).

Whichever lands, the L5 chain artifacts (HintSet→…→TaskRun) must be populated with the *real* demo content, because the UI renders them (§6).

### 5.3 Consolidation, crash recovery, ALS

- **Consolidation ON** for all brains (it ships on all terminal paths) — Episodes are the beat-6 trace recap *and* the per-brain memory story. `consolidate_task` → Episode + Memory + `MEMORY_CONTAINS_EPISODE` in each brain's Local `episodic_memories`.
- **Crash recovery ON** (`InMemoryCheckpointStore` per brain; startup scan writes crash-marker Episodes) — free resilience narrative if anything dies mid-rehearsal.
- **ALS:** registry stays as shipped (skeleton subsystems); no demo ALS work — real ALS firing is WSD scope.

---

## 6. Task 3.6 — L5 mental-model examples, per instance

The 6-level chain (HintSet → MappingResult → Plan → Pipeline → PipelineRun → TaskRun) is what the UI's thinking panels and beat-6 recap render. Concrete instances the demo produces:

**Example 1 — mgr, beat 0/3, order "R2c1 ← 1 tube" (cross-side, forces the box workaround):**
- HintSet: {order lines, world facts (tube at belt_a1 side), affordance hints (tube requires grasp:jaw)}
- MappingResult: line → `task-pattern:demo:handoff-via-box` (a1 can't deliver to shelf_R; a2 can't reach tube)
- Plan: [a1:`load_into_box`(tube,box1)] → [conv:`stage_at`(belt_a2)] → [a2:`pick_from_belt`(box1)] → [a2:`place_at_cell`(r2,c1)]
- Pipeline (per step, within-brain): a1's `load_into_box` = [pick(tube)… insert… attach]
- PipelineRun / TaskRun: live execution records incl. the conveyor's scheduling decision
- Terminal: Episode{task_input_ref, mm_root_ref, task_pattern_iri:"task-pattern:demo:handoff-via-box", outcome_classification:"succeeded", consolidated_at} + Memory clustered by task_pattern_iri

**Example 2 — arm1, beat 1, the honest dont-know:** TaskRun terminates `dont_know` with the family-specific payload from `validate.feasibility` ("requires grasp:jaw; I provide grasp:suction") → `TaskOutcome(status="dont_know", dont_know_reason=…)` → Episode retained (outcome `dont_know`) → Manager's MappingResult shows the unfilled Plan slot → `capacity-gaps` node — *that* is what the UI points at.

**Example 3 — mgr, beat 2, the teach:** `learning.capture_pipeline` TaskRun whose *product* is the Pipeline artifact — the chain renders a task whose output is a new capability (the thesis in one picture).

**Example 4 — beat 4, peer transfer + gate:** arm2's receive-share TaskRun: artifact received → gate query → registered-but-gated for Sheet (`place-Sheet` refused: requires grasp:suction) vs enabled for tube-in-box flows. Two MM snapshots, one artifact, different affordances.

**Example 5 — beat 5, degradation replan:** mgr TaskRun with `replans_used ≥ 1`: DIAG_REPORT signal → gap in `capacity-state`/`capacity-gaps` → `decision.replan_on_gap` verdict → re-planned Plan (cylinder route swapped; carriers keep flowing). The before/after Plan diff is the money shot.

**Beat 6 recap** = read each brain's Local `episodic_memories` + `problem-trace` and replay Episodes in order: gap → taught → executed → transferred → gated → degraded → replanned. D′1 mechanics (`read_at_version`, `retire_version`, pin-at-instantiation) back the retire/inspect beats — shipped at Phase 48, use as-is.

---

## 7. Task 4 — Gap analysis: everything else needed (honest list)

Net-new work the shipped stack does NOT provide, beyond §§1–6:

| # | Gap | Demo-scoped resolution | Effort |
|---|---|---|---|
| G-1 | **Real planning catalogs** — v0 placeholders dispatch no real L3 (§5.2) | Same-name override or execute_plan fallback; probe `if_exists="upsert"` semantics first build session | M |
| G-2 | **F1-min peer Local→Local share** — no cross-Local write exists | Receiver-writes-own-Local over the bus (§2.1) — needs zero new server capabilities; conflict rule: same-name Local exists → refuse + surface (no merge in v1) | S |
| G-3 | **F4-min embodiment gate** — no embodiment schema | NodeTypes inside Local `capacity-state` (§3.3) + `validate.feasibility` query (§4.1) | M |
| G-4 | **F5-min Pipeline artifact lifecycle** — promotion loop is WSD-55, unavailable | Frozen §5.1 artifact → Local store + runtime `register_capacity`; no Global promotion in demo (P-5) | M |
| G-5 | **Episode→Falkor flush** — descoped at Phase 49 (PB-RT, L0-26) because node `value` couldn't hold dicts | ADR-0182 `_value_json` codec **shipped at Phase 50** — wire the flush and verify round-trip; if it resists, demo falls back to in-memory episodes (recap still works; durability across restart doesn't) | S–M |
| G-6 | **demo_backend package** — sim loop, BrainBus, body adapter, WS server, control token, bootstrap/reset scripts | New code, no MindsOS changes (§1–2) | L |
| G-7 | **Live motion adapter** — `sim/motion.py` builds offline clips, not a live control loop | Runtime wrapper: generate → checklist-verify → stream frames into the stepping sim; constrain orderable targets (P-7). **PB-F (§10): precompute + cache** — during rehearsal, generate and checklist-verify trajectories for the entire constrained order menu (item × source × target × grasp branch) into a keyed cache; demo-time lookup first, live generation only on cache miss, and a checklist failure on a live miss surfaces as an honest dont-know ("can't find a safe motion"), on-thesis rather than a stall. The 46 verified clips remain the rehearsed envelope + recorded-backup source | M–L |
| G-8 | **Fault injection switch** + diagnose loop (beat 5) | Backend freezes a joint; `diagnose_actuators` detects (commanded vs actual delta) | S |
| G-9 | **UI v10** — graph tab (curated FalkorDB subgraph queries), teach/inspect/retire affordances, control token, live chain panels | Phase-D work as planned, against live data | L |
| G-10 | **Ops** — Mac Mini RAM check (FalkorDB + 4 IntelligenceLayers + MuJoCo + 4 worker pools in one process), LAN-vs-tunnel decision, rehearsal, recorded backup | Measure during DM-1; budget swap headroom. **PB-E (§10): GIL contention is the specific threat** — 4 worker pools + sim stepping + WS broadcast share one interpreter; DM-1 gate includes a sim-jitter measurement under synthetic 4-brain load. Escape hatch (prepared, not built): split the sim loop into its own process behind `BodyHandle` — the seam already isolates it, only `body_adapter.py` changes | S–M |
| G-11 | **Resettability of learned state (the empty-start thesis is a *reset* requirement)** — after every rehearsal, `load_into_box` exists (CL registration + Local artifact node + episodes); beat 1 requires it absent. CL has no deregister (Phase-50 G1: de-install is marker-only) | Reset = **process restart + Local wipe**: in-memory CLs clear on restart; `reset.py` wipes the 4 Locals' learned/run-state nodes (taught artifacts, episodes, gaps, traces) with an explicit keep-list for the §3.3 seeds; Global untouched. Tag all run-scoped nodes with a `run_id` so wipe and beat-6 recap are both run-scoped. Surgical in-place deregistration is NOT built (new mechanism, no payoff). Reset drill rehearsed; budget = seconds-to-a-minute of restart, acceptable between runs, never mid-run | M |

**Known residual risks (accepted):** single-process = single point of failure (mitigated by the mandatory recorded backup + crash-recovery markers); thread contention between 4 worker pools and the sim loop (pin sim to its own thread, keep `max_workers` small: mgr 2, others 1; PB-E escape hatch prepared); family assignments in §4 may need adjustment to the shipped FAMILY_RULES at build time (table notes which are judgment calls); **conveyor-decorative risk** — `scoring.belt_schedule` only earns its place if the rehearsed order set forces real belt contention (≥2 concurrent cross-side lines in opposite directions); if the final script can't stage that, cut the "conveyor owns a real decision" claim from the narration rather than letting it be theater.

---

## 8. Build sequence (gates, in order)

| Phase | Scope | Gate |
|---|---|---|
| **DM-1** | §1 deployment: compose service, `demo_backend` skeleton, bootstrap (admin, 4 users, Global bootstrap, smoke lifecycle ×4), RAM measurement | `docker compose up` → 4 brains start, 4 trivial Episodes consolidate, idempotent re-boot |
| **DM-2** | §4.0 DataStates + 3 skill bundles (§3.4) + Local seeds (§3.3) + G-5 episode flush probe | bundles install idempotently; `mindsos knowledge` shows seeds; episode round-trips Falkor (or fallback documented) |
| **DM-3** | Seam C: body adapter + atomic capacities + live-motion wrapper (G-7); fault switch (G-8) | each atomic capacity moves the live sim, checklist-verified |
| **DM-4** | Seam B: BrainBus + `comms.*` (push-cache, PB-C) + `trace.demo_events`; G-1/PB-B probe + resolution; **thin vertical UI slice starts here (PB-G): WS state frames + one thinking panel against live data** — the UI grows with each beat instead of landing wholesale at DM-8 | mgr dispatches a1 `place_at_cell` end-to-end through both lifecycles, visible in a browser panel |
| **DM-5** | Manager cognition (§4.3) + pre-seeded composites (§4.1–4.2): beats 0 + 3 run end-to-end (same-side and cross-side with *pre-registered* load_into_box as a temporary stand-in) | scripted order fulfills with real physics + real lifecycles |
| **DM-6** | Learn loop (G-4): Seam-D capture → artifact → runtime registration; **remove the stand-in** → beats 1–2 real | empty start → dont-know → teach → fulfil, no pre-baked skill |
| **DM-7** | F1-min share + F4-min gate (G-2, G-3) → beat 4; degradation loop → beat 5 | transfer + gate + replan run unscripted |
| **DM-8** | Seam A completion: control token, graph tab, remaining v10 affordances (G-9), beat-6 recap from episodes (run-scoped per G-11), trajectory cache fill (PB-F) | full 6-beat run driven from a browser; reset drill passes |
| **DM-9** | Deploy on Mac Mini, LAN/tunnel decision, **2 full rehearsals** (each followed by a reset drill), record the backup run | demo ready to ship |

Conventions: pair-execution pattern as established; design log `ROBOT_DEMO_MINDSOS_DESIGN_LOG.md` from DM-1; update `ROBOT_DEMO_STATUS.md` per milestone; any new net-new MindsOS feature discovered → new `Fn` in `DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md`.

---

## 9. Verification spine (every DM phase)

1. MindsOS cumulative gate stays green (demo code must not touch `mindsos_*` packages except additive registration at runtime — zero domain-layer edits is the target; any exception gets a design-log entry).
2. Per-phase scenario test in `tests_demo/` (new top-level, not in the cumulative gate) mirroring `tests/phase_49/integration_c.py` style.
3. Motion: the MOTION_RULES data checklist on every live-generated trajectory (P-7) — data, not eye, before showing.
4. Before DM-9 sign-off: kill-and-restart drill (crash recovery + bootstrap idempotency), reset drill, backup-playback drill.

---

## 10. Round-2 reanalysis — pushback log (2026-06-10)

Adversarial re-read of §§1–9. Each entry: flaw → options → **chosen**. Resolutions are already folded into the sections above (marked PB-x inline).

**PB-A — Pre-seeding `handoff-via-box` falsified beat 1.** §3.1 originally seeded the handoff task-pattern in Global, but the scenario requires *both* the composite **and** the Plan to be unknown at start ("the Orchestrator has no handoff Plan"); a Manager that boots knowing the route makes the empty-start thesis partly theater. Options: (a) keep the seed, gap only on the composite — simplest, but narration must dodge "how did it know the route"; (b) teach writes the pattern too — collides with task-patterns being Global-tier + no live Global writes (P-5); (c) assemble the route at plan time by searching the reach/capability topology. **Chosen: (c)** `planning.route_via_reach` — bounded search (3 brains, 5 regions), honest at both beats (fails before teach, succeeds after), and it's the same search the route claim is *about*; (a) retained as a disabled fallback flag for rehearsal emergencies.

**PB-B — §5.2's real criterion is chain-artifact authorship, not lifecycle execution.** The UI renders the L5 chain; `ChainArtifactWriter` runs inside the lifecycle phases. The fallback (execute_plan does the real work) risks a chain populated by v0 placeholder content — thinking panels narrating fiction, violating the never-fake rule. **Chosen:** elevate the criterion in §5.2; if the fallback lands, demo capacities must write the chain themselves via `mm_handle` (probe its write surface in DM-4); placeholder-rendered chains are disqualifying.

**PB-C — Synchronous `query-capabilities` round-trips inside running capacities.** Original §2.1 had the Manager's allocation block on bus replies mid-capacity: worker-thread blocking + a brain-to-brain query deadlock class. Options: (a) sync request/reply with timeouts; (b) push-on-change capability cache at the Manager; (c) Manager reads other Locals directly — requires `CAN_READ_OTHER_LOCALS`, an admin cap on a non-admin user (governance smell). **Chosen: (b)** — brains push at boot + on every capacity-state change; beat 5 already depends on exactly that push path (gap appears → report), so it's one mechanism, not two.

**PB-D — A taught composite is not executable data.** The Pipeline artifact is steps+bindings; `register_capacity` needs an `implementation` callable. Unstated in v1 of this plan. **Chosen:** generic `PipelineRunner` factory in `demo_backend` binds artifact → callable dispatching sub-capacities through the brain's own dispatcher; registration occurs in the receiving brain's own task context (no cross-thread CL mutation).

**PB-E — GIL contention in the one-process topology.** 4 worker pools + MuJoCo stepping + WS broadcast in one interpreter; sim jitter is the failure mode the audience sees first. Options: (a) measure, pin, keep small worker counts; (b) split sim into its own process now; (c) lower sim rate. **Chosen: (a)** with a DM-1 jitter gate under synthetic load, and (b) *prepared* as the escape hatch — the `BodyHandle` seam means only `body_adapter.py` changes. Building (b) preemptively is unjustified complexity.

**PB-F — Live trajectory generation on stage.** Checklist-gated live IK is honest but a live checklist failure = an on-camera stall. Options: (a) always generate live; (b) precompute+cache the constrained order menu during rehearsal, live-generate only on miss; (c) clips only — fakes the live claim. **Chosen: (b)**; a live miss that fails the checklist surfaces as an honest motion dont-know rather than a stall.

**PB-G — UI landed wholesale at DM-8.** The UI is the legibility backbone (resolved risk in OPEN_QUESTIONS); building beats headless until DM-8 compresses the only window where narration problems become visible. **Chosen:** thin vertical UI slice from DM-4 (WS frames + one panel), growing per beat; control token + graph tab stay at DM-8.

**PB-H — Resettability was unplanned (now G-11).** The empty-start thesis is really a *reset* requirement — every rehearsal contaminates the Locals and the CLs. **Chosen:** restart-based reset + run_id-scoped wipe/recap; no surgical deregistration mechanism.

**Missing input (not resolvable here): the demo date.** §8 has no calendar. DM-1→DM-9 is realistically 4–7 working weeks single-builder; G-6/G-7/G-9 dominate. The date determines whether the if-time beats (override, sort, box scarcity) survive scoping at all.

---

## 11. Round-3 reanalysis — per-device architecture + DM-1 grounding (2026-06-10)

DM-1 chat. Round 2.5 = adversarial re-read of §1 against shipped code (user-confirmed); Round 3 = the per-device-instance architecture change (user request). Full record + grounded API signatures in `ROBOT_DEMO_MINDSOS_DESIGN_LOG.md` §§1–3.

**Round 2.5 (confirmed):**
- **P1 / PB-B** — `CapacityContext.mm_handle` is **read-only** (4 read methods) and capacity bodies never receive the `ChainArtifactWriter` → §5.2 **option-3 is deleted** (unbuildable without editing `mindsos_intelligence`). `phase_1.run` emits chain artifacts *from the dispatched capacity's outputs*, so **same-name override (option-1) is mandatory and honest** — demo Phase-1 logic registers under the literal v0 IRIs (`capacity:process:identity`, `capacity:hint:global`, `capacity:decision:derive_goal`, `capacity:decision:map_to_task_pattern`), not the §4.3 pretty names (reconcile in DM-4).
- **P2** — promoted-pipelines has **no Local storage tier** (Global-only `storage_mode`, Phase 43) → the §4.3 asterisk **stands** (learned composites → Local `capacity-state` `LearnedComposite`).
- **P3** — `register_capacity(if_exists="upsert")` confirmed; verify edge re-emission at DM-4.
- **P5** — **Orchestrator wiring is net-new:** `IntelligenceLayer` has no `run_lifecycle`; build `Orchestrator(L4Dispatcher(cl, session, kl), il.mm)` after `il.start()`, run via `il.enqueue(...)`. Now in §1.3 step 6–7.
- **P6** — idempotent re-boot = get-or-create guards (`insert_user` raises on dup). **P7** — jitter gate = p99 ≤ 2× nominal at 50 Hz proxy + record distribution. **P8** — §1.3 steps 4–6 are DM-2/DM-3 (stubbed at DM-1). **P9** — real `login()` sessions, not `for_testing`.

**Round 3 — per-device instances (PB-I…PB-N):**
- **PB-I (scoping):** only **L2** changes; L3/L4 already per-instance. P-1 revised: 4 independent `KnowledgeLayer`s (own Global+Local) in one shared-Server process / one FalkorDB.
- **PB-J:** shipped load-or-mint is single-Global-by-name → **DM-1 = 4 fresh in-memory Globals; DM-2 = per-device named Falkor helper in `demo_backend`.** Verify `global_metagraph().name` settability.
- **PB-K:** `capacity-gaps` is Global-tier/admin-gated → **re-homed to per-device Local `capacity-state`**; Manager aggregates via `comms.report`. (Fixes a latent P-5 contradiction.)
- **PB-L:** beat-4 peer transfer is now **cross-installation** Local→Local — strengthened, no mechanism change.
- **PB-M:** **P-8** added — `DeviceProfile` drives device-type-exclusive bundle install (`demo_backend`-side; shipped Phase-50 mechanism). Manifest-level device gating filed as **F7**.
- **PB-N:** RAM gate budgets 4 Globals (minor); record the 4-KL footprint at DM-1.

**Zero `mindsos_*` edits.** Open build-time verifications: PB-J name settability; P3 upsert edge re-emission; P5 Orchestrator wiring vs Phase-47 tests; P1 v0 plan-phase (`plan_construction`/`execution`) dispatch IRIs (DM-4).
