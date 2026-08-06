# Robot demo — brain structure re-plan (v5)

Proposal, not confirmed. Baseline: core `main` @ `3591add`; demo `demo/robot` @ pin `f9-confirmed`.
Converged over 6 skeptical passes; v5 folds in producer selection, peer announcement and telemetry.

---

## 0. Settled

| | |
|---|---|
| Comms | Demo builds it, behind the interface the core CR will expose. |
| Sequencing | Hybrid — build what CORE-C cannot break; stage the rest. |
| Roster | `mgr` / `arm1` / `arm2` / `conv`. **Manager keeps authority.** |
| Narrative | v2 four-way taxonomy, re-opened (§6). |
| Coordination | Direct peer *awareness*; manager-mediated *coordination* (§5). |
| Impossibility | Knowledge (a domain axiom + a predicate), not a core mechanism. Real at C4. |
| Milestones | **nilm goes first.** Robot demo designs for them, adopts after. |
| Topology | **Six processes** — gateway, world, four brains. No sharing. |
| Identity store | **Each brain owns its own `server.db`.** No shared auth/session state. |
| World | A source of truth outside MindsOS, probed and acted upon (§2). |
| Memory | World model in **L2 Local**; L5 records **how** each value was obtained (§3). |
| Producer choice | **Declare both; record the choice as unmade.** Never a naming trick (§3.2). |
| Repetition | **An L4 decision, never pipeline composition** (§4). |
| Peer discovery | **Announcement at boot. No registry component** (§5.1). |
| Telemetry | One-way out; **no brain may subscribe to another's** (§5.4). |
| `arm2` | A **UR5e** — 6 joints against the Panda's 7 (§4.3). |
| Sanitisation | Extend the vocabulary with demo-domain labels. |

---

## 1. Three seams

1. **The world seam** — the simulation is a source of truth *outside MindsOS*. Brains build world
   models; they are never handed ground truth. (§2)
2. **The peer seam** — a peer is a producer. Competence flows through the manager; occupancy flows
   peer-to-peer. (§5)
3. **The level seam** — capacities compose across joints; L4 iterates across time; a taught skill
   sits above both, which is why it can cross bodies. (§4)

---

## 2. The world

**The world is not a brain and not part of MindsOS.** No KnowledgeLayer, no CapacityLayer, no
Local, no Episodes. It is what MindsOS is pointed at. That is the sim→real story stated
architecturally: **the same brains, unchanged, against a different world.** The protocol is the
artifact that survives the swap.

### 2.1 Two protocols, never fused

| | `probe` | `act` |
|---|---|---|
| semantics | ask what is so | commit and change the world |
| repeatable | yes | no |
| cost | time | time + a resource |
| capacity family | perception | body |

The split exists latently in `BodyHandle`: `sense_poses` / `diagnose` are probes; `move_to` /
`set_grip` / `run_belt` / `stop_belt` are acts.

**The world must detect and report physical conflict**, including arm-to-arm contact. A source of
truth that cannot report a collision is not a source of truth, and the advisory queue (§5.3) depends
on it. This is a requirement of the protocol, not something to verify and then drop.

### 2.2 Probes are sensor-scoped and cost time

Otherwise the world model is free omniscience: never stale, never needing memory, and "I'm not sure"
never fires.

- A probe capacity **declares an output DataState scoped to what its sensors reach.** `arm1` cannot
  observe the far shelf because it has no capacity declaring that observation as an output. Adding a
  sensor is adding a capacity.
- Probes take time. Duration is a **learned parameter**, not a constant.

**`mgr` has no body, therefore no probe.** Its entire world picture is recalled or peer-reported —
so `mgr`'s form of probing *is* the plan-time peer query. That is a consequence of the roster, not a
special case.

### 2.3 Truth and belief diverge, visibly

The UI shows the **world's** state for `items` / `eff`; each brain card shows that brain's
**belief**. They can disagree, and that divergence is the most interesting thing available to put on
screen. It is structurally impossible today: the current demo pipes sim ground truth straight
through, so brains "know" what they never sensed, violating the grounding invariant.

---

## 3. Memory

DataStates are **declared** by the brain author (or taught). Capacities declare which DataStates
they consume and produce; at runtime a body returns a *value* for its declared output. The two must
not be conflated.

### 3.1 Where belief lives

- **L2 Local — the world model.** Durable belief about the cell, surviving across requests.
- **L5 — this run's provenance.** Which capacity produced which value, when, from what. Not memory.

L5 is per-run and `knowledge_mm` is not persisted. Belief living only there dies with the request.
Reconstructing it by scanning past episodes is archaeology, and efficient episode querying is
deferred (PRE-3).

**Three capacities, all declared and all in the graph:**

- `probe` — asks the world, produces the observation.
- `remember` — writes an observation into L2 Local. Writing is a capacity, so the judgement of what
  is worth keeping lands in the graph rather than inside a body (§8.8).
- `recall` — reads L2 Local, produces the same DataState the probe does.

`CATEGORY_RETRIEVAL` already exists (`identifiers.py:83`), and nilm already runs this shape:
`learn_parameter` writes, `read_learned_parameter_snapshot` reads.

### 3.2 Two producers, and an unmade choice

`probe` and `recall` declare the **same** output DataState. That is correct — having two ways to
obtain a value is real, and splitting the DataState only relocates the competition to whatever
produces the second one.

**Today the finder resolves it by accident.** `ConjunctionFinder` sorts candidate producers by
capacity IRI and takes the first (`satisfiable[0]`). The winner therefore depends on what the
capacities are named.

**Do not exploit that.** Naming for the intended winner hides an unmade decision inside a
convention.

> **Declare both producers, and record in the run trace that two were available and the selection
> was arbitrary.**

An unmade decision should be visible as unmade. This is exactly ADR-0206 §6 — the system proceeded
but is not sure — and the recorded alternatives are the input `decision.select_producers` consumes
when it ships. **The test asserts that two producers were found, not which one won.**

---

## 4. Bodies, capacities and repetition

### 4.1 Capacities compose across joints; L4 iterates across time

A capacity is *move this joint one increment*. Pipelines compose **across joints**. A trajectory —
one joint moved repeatedly — is **an L4 decision, not composition.**

**Why, and it is not convenience.** The number of increments is **data-dependent** — distance, speed,
tolerance. ADR-0205 §7 holds structure stable and structural change deliberate. As composition, every
different move distance would be a different pipeline, the catalog would explode, and nothing would
be reusable. Repetition is not a structural fact.

Consequence: **C2R4 needs no change.** The pipeline stays a single-assignment dataflow DAG.

### 4.2 What repetition still needs from core

The ruling locates the gap; it does not close it. There is no mechanism for *apply this step until a
condition holds* — `BRAIN_ARCHITECTURE_AUDIT.md` §3 gap #1, owed at **C5R2/C5R3**, hand-rolled by
nilm as `_refine_window`. Three parts:

1. **Repeat** — L4 applies one capacity to successive values.
2. **A declared stopping predicate.** Not a Python `while`; otherwise each arm brain grows its own
   convergence loop and lands back at `closed_loop.py`'s `OK_MAX_RAD=0.005`.
3. **A per-iteration record.** The blackboard holds one value per DataState IRI, so iteration
   overwrites; without a record the trace shows one value and the audit view loses the history —
   which is what the demo exists to show.

### 4.3 `arm2` is a UR5e

Six joints against the Panda's seven. Different link lengths change only numbers; a different joint
**count** changes structure, so a taught skill cannot be a trajectory even in principle. It must be a
pipeline over declared DataStates that each body grounds through its own actuators — which kills the
current four-element literal step list.

Cross-body teaching is therefore a **milestone + pipeline object**, needing C2R5 — which is why nilm
going first is on the critical path.

**The demo must be able to fail here.** If `arm2` has no capacity producing a DataState the taught
pipeline needs, transfer fails, and showing why is worth more than a transfer that always works.

**Constraints:** the new reach envelope must still leave the belt middle unreachable, since that
geometry forces cooperation; `pose_frame.py`'s fitted affine (`ax=0.5417`, `ay=-0.5818`,
`by=-0.7118`, arms at ±1.2) is invalidated; only Panda and Robotiq are vendored in `sim/menagerie/`.

### 4.4 Correction — C3R1b does *not* refuse motor capacities

An earlier draft claimed a capacity declaring "joint state in, joint state out" would be silently
refused. **Wrong.** The shipped guard (`pipeline.py:597 eligible`) is a cycle stack over DataStates,
not an overlap check, and `fire` short-circuits any input present in `starts`. Current joint state is
always a start, so an endomorphic capacity is admitted normally.

The real constraint is what §4.1 answers: `fired` memoises by capacity IRI, so a capacity appears at
most once per pipeline (the D-E fix), and the blackboard holds one value per DataState IRI. A
sequence of moves of one joint is not refused — it is **unrepresentable as composition**.

**Separate ruling: drop C3R1b's first predicate, do not narrow it.** Its own record refutes it — over
20,000 catalogs the blanket rule gives 0.46% against 2.69% for no rule, the narrow variant **3.20%,
worse than no rule**, and neither is causal because the real failures are cycles between two
*distinct* capacities. The same section concedes endomorphism is legitimate (arc1's `rotate` /
`reflect` / `move` / `recolor`). A rule that cannot distinguish refinement from endomorphism, and
that measurement says does not fix what it was for, should not ship. **Keep predicate 1b**
(`operand_arity` — 14/27 in arc3, 16/45 in arc1). C3R1b is unbuilt: this amends a design.

---

## 5. Coordination

### 5.1 Peers announce themselves — there is no registry

**Each brain announces itself on the comms transport at boot; peers learn of each other from
announcements.** No component holds the roster. `mgr` and the gateway learn it the same way every
brain does.

A central roster would make peer awareness die with whatever holds it, contradicting the awareness
channel being direct. Announcement also makes a brain joining or dropping out a normal event rather
than a configuration change — which is what autonomous entities require. **The transport must
support broadcast.**

### 5.2 Two channels

- **Awareness — direct, peer-to-peer, broadcast.** "I intend to hold `<resource>` until `<t>`." Any
  brain may receive. **Granularity is the resource hold, never the motor step** — motor-level
  broadcast is a firehose that changes no decision.
- **Coordination — through `mgr`.** Delegation, allocation, route determination. `mgr` holds the
  proxies.

Same axis the resource design draws: **occupancy travels peer-to-peer and stays outside the searched
graph; competence travels through the manager and lives inside it.**

**Only `mgr` holds proxies**, so the proxy graph is a star of depth 1 with no back-edge, `A→B→A` is
unrepresentable, and the distributed-cycle problem does not arise. It returns only if the topology
goes fully peer.

A proxy is **not a copy of a peer's declaration** — copying would assert "I can grip a tube", which
is false. It declares `peer.request_descriptor → <the peer's output DataState>` with
`REQUIRES_RESOURCE <the peer>`, and asserts "I can *obtain* a gripped tube", which is true.

### 5.3 The confirmed action queue

Brains **propose**; `mgr` **confirms**; `mgr` broadcasts the confirmed queue. "Any brain appends its
own decision" fails — two brains deciding simultaneously each read a broadcast set not yet containing
the other's, and both append conflicting holds. Propose/confirm makes `mgr` the single serialization
point with no new machinery.

**The queue is advisory, not a lock.** The world arbitrates what actually happened; brains acting
despite the queue are caught by a collision. Honest and demonstrable — but nobody should build
assuming exclusion is enforced.

**The queue is the missing reservation store.** Its CR must carry one line: §9.5 says *"there is no
planner/executor split over ordering — all ordering is Resolution's."* The queue orders **between
agents' committed holds**, not **within a request**. Unstated, core reads it as a contradiction.

### 5.4 Telemetry is one-way and non-load-bearing

The UI needs each brain's reasoning — intent, decision, capability badges, flags. That is a **third
flow**, distinct from comms and from probe/act.

> **Telemetry goes out only. No brain may subscribe to another brain's telemetry, and no brain
> decision may depend on anything that crossed it.**

Enforced by a test, not by convention. A decision may depend on an awareness broadcast or a manager
instruction; never on telemetry. Without this rule the telemetry channel becomes the shortcut every
future increment reaches for, and the peer seam stops holding.

---

## 6. Verdicts, and the narrative re-open

| v2 verdict | Mechanism | State |
|---|---|---|
| **can** | Self-sufficient route found — locally or through `mgr`'s proxy | Finder: **now**. Confidence bar: C4 |
| **don't know** | `find_verdict.found=False` — `bfs_exhausted` / `no_satisfiable_producer` | **Shipped** |
| **not able** | `required_input_unproducible` + `.unproducible` naming capacity → missing DataState | **Shipped**; the *explanation* needs a plan-time peer query |
| **not possible** | A domain axiom + a predicate; no pre-planning hook, so it lands in phase 1 | **Open until C4** |

- **"not able" is competence, not resources.** *No plan is impossible because of the hand — only
  slower.* `arm1`'s inability to grip a Tube is an **absent capacity**, never a runtime check inside
  a present one. With `arm2` a UR5e there is a second, distinct "not able" — *cannot reach*.
- **Teaching has a shape.** ADR-0205 §8: a Skill spans all levels. The taught carrier is a pipeline +
  a milestone crossing two differently-shaped bodies.
- **"I'm not sure" ≠ "I don't know"** (ADR-0206 §6) is now reachable twice over: a probed world model
  can be stale, and §3.2's unmade producer choice is itself a not-sure.
- **The Box is the resource axis's first hard case.** Passed arm→arm and reused → given back →
  resource. Committed as a carrier with the Tube inside → never given back → DataState.

---

## 7. Slices

### Buildable now

**S0 — repin and de-hack.** `Orchestrator(task_scope=)`→`request_scope=`;
`run_lifecycle(task_id=)`→`request_id=`; `TaskOutcome`→`RequestOutcome`; delete `install_override`
(its "upsert is a no-op" docstring is false since the F10 fix). **Budget as recurring** —
`orchestrator.py` 201→499, `phase_1.py` 75→326, repeating at C2R4/5/6/7.

**S1 — the gateway.** One WebSocket; telemetry-in from brains, one-way, test-enforced; owns
`sanitize` and the cross-brain audit query. **First, because everything after it needs somewhere to
be observed.**

**S2 — the world.** `sim_engine` into its own process; probe and act as two protocols; sensor-scoped
probes; collision detection and reporting; pose served from the world.
*Deliverable: no brain receives ground truth it did not sense.*

**S3 — four brain processes.** Own `server.db` each. Boot announcement over the comms transport. L2
absorbs both hard-coded tables (`allocation.py`'s spatial terms = F2; `feasibility.py`'s
`ITEM_ACCEPTABLE_GRASPS` = F4/F8). Per-joint capacities. `probe` / `remember` / `recall` declared,
with the unmade producer choice recorded. `arm2` as a UR5e. `server_event` finally produced.
*Deliverable: four brains that boot independently, discover each other, and hold grounded durable
world models.*

**S4 — the comms seam, gated by the finder.** Awareness channel + `mgr`'s proxies.
*Deliverable: `ConjunctionFinder` returns a pipeline composing **more than one peer** — the
belt-bridge route across both arms and the conveyor — and it executes.* A single-proxy route proves
nothing, since `mgr` has no body and every route it composes crosses one. **This is the slice that
proves the claim.**

**S5 — the confirmed action queue.** Propose/confirm through `mgr`.
*Deliverable: exactly one decision demonstrably changed by a peer message* — e.g. `mgr` defers a
dispatch because `arm1` broadcast a gripper hold. Anything beyond that waits for a real scheduler, or
the channel is decoration.

**S6 — the chain-reader adapter.** All chain-artifact reading behind one contract; `serializer.py`
hard-codes `hintset` / `taskrun` / `stepexecutionrecord` prefixes that C2R4–C2R7 rename.

### Staged

**S7 — after C5R2/C5R3.** L4 repetition with a declared stopping predicate and per-iteration records.
**S8 — after C2R4/C2R5 and after nilm.** The taught skill becomes a pipeline + milestone and crosses
from `arm1` to the UR5e.
**S9 — after C4.** The 8 monkeypatches deleted; decomposition, confidence and the four verdicts real.

### Honesty ladder

| After | Claimable |
|---|---|
| S2 | Brains sense; they are not told. |
| S3 | Belief is durable, grounded, and visibly distinct from truth. |
| S4 | A route across **several** brains is composed, not scripted. |
| S5 | One coordination decision is changed by a real peer message. |
| S8 | A skill taught to one body runs on a differently-shaped body. |
| S9 | The system plans, decomposes, and answers with calibrated confidence. |

The current demo's sin is not that it fakes — the fakery is meticulously documented — it is that the
fakery is invisible on screen.

---

## 8. Core CRs this generates

1. **Inter-brain communication family + transport seam**, including boot announcement and broadcast.
   File with the build, not after.
2. **Proxy / advertised capability.** The cycle question is moot under the star topology; record that
   it returns if the topology goes fully peer.
3. **Resource-hold reservation store** — the confirmed action queue, with the between-agents vs
   within-request distinction stated.
4. **The world / environment seam** — MindsOS has modality-stamped ingress but no notion of an
   external world a brain may query. Probably the largest CR here.
5. **L4 repetition** (C5R2/C5R3) — repeat + declared stopping predicate + per-iteration record.
6. **Recording an unmade producer choice** — the trace must carry the alternatives, not just the
   winner. Feeds `decision.select_producers`.
7. **Drop C3R1b's first predicate**, keep `operand_arity`. Deletes planned work.
8. **Cost has a store** (§10.3) — needed the moment recall-versus-probe becomes a real choice.
9. **What is worth remembering** — the judgement deciding which observations reach L2.
10. **Resource axis, first consumer** — the Box's dual classification.
11. **Plan-time peer query** — asking *why* before committing to execute.
12. Teachable spatial vocabulary (F2); affordance as a graph, not a dict (F4/F8).
13. Chain must record `blame`, request input, replan summary.
14. Sanitisation vocabulary vs honest step labels.

---

## 9. Still open

**O1 — multi-process `server.db`.** Resolved in principle (one per brain), but the Local write path's
in-process mutex (ADR-0006) and the boot path assume a single store. Verify before S3; it can still
invalidate the topology.

**O2 — narrative reconciliation.** `ROBOT_DEMO_SCENARIO.md`, `ROBOT_DEMO_MINDSOS_DESIGN_LOG.md` and
`ROBOT_DEMO_PHASE_A_REACH.md` exist only on `robot-demo-animation`, not on `demo/robot`. Reconcile
before encoding any story.

**O3 — which L2 role holds the world model.** A new Local role, or an existing one
(`learned-parameters`, a `dataset:` graph)? The closed set is 16 and the resource axis already
proposes a 17th. Decide with the core chat, not unilaterally. **Blocks S3.**
