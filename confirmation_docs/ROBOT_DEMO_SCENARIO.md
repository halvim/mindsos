# MindsOS Robot Demo — "Open Order" Scenario

**Status:** Design draft (Cowork chat, 2026-06-05). Not yet a confirmed phase. This is the candidate showcase: *MindsOS as a layered robot brain.*

**Thesis being demonstrated:** MindsOS is a system that **learns everything**, not one that knows everything. A hierarchy of MindsOS instances manages multiple physical intelligences, each speaking a different interface. Users customize what each intelligence can learn by adding capacities and demonstrating pipelines.

---

## 0. Settled decisions (this chat)

| # | Decision | Rationale | Cost accepted |
|---|----------|-----------|---------------|
| D-1 | **2 arms + 1 conveyor** (not 3 arms, not forklift+base) | Best simplicity/impressiveness balance; keeps the cooperative-handoff story while halving grasp-surface and brain count vs the 3-arm version. | Less reach-partition richness than 3 arms. |
| D-2 | **Conveyor is its own MindsOS brain** (3 intelligences + manager) | Matches the "intelligent conveyor" intent + the hierarchy-of-intelligences thesis; the conveyor is the sole bridge between the arms, so it owns a real decision. | One more inter-brain seam to integrate and keep live on stage. |
| D-3 | **Simulator: MuJoCo** | Fastest iteration, strong contact/grasp physics, lightweight. | Plainer visuals than Isaac — on-camera appeal leans on motion density + the reasoning-UI overlay, not photorealism. |
| D-4 | **Structured order entry** (UI item-into-box), not natural language | NL parsing is a rabbit hole that is not the differentiator. | None material. |

**Open locks:** L-1, L-2, L-3 all **resolved 2026-06-05** (see §6). Remaining work before build = prototype-zero + freezing the two §5 contracts.

---

## 0a. CANONICAL MODEL UPDATE (2026-06-05) — supersedes drifted item/cooperation/bin language below
Later design rounds evolved the model. Where older sections say *bins / parcels / cylinders / handoff-via-belt as the learned skill*, the current truth is:

- **Cell targets:** per-arm **vertical 3×3 shelves** (not bins). Arm 1 = left/suction, Arm 2 = right/jaw.
- **Item taxonomy:** **Box = carrier/container** (dual-graspable; holds cargo) · **Sheet = suction-only cargo** · **Tube = jaw-only cargo**.
- **Cooperation = the carrier-box workaround.** Cargo a receiving arm can't grasp is **loaded into a Box by the arm that can**; the Box (graspable by both) is moved across the **unreachable middle** by the **command-driven Conveyor**; the receiving arm grabs the Box. Cargo is delivered **boxed** (the receiving arm never touches what it can't grasp). Item-in-box uses **attach-on-insertion**.
- **Belt:** continuous *surface* (one conveyor, no hole); cooperation is forced by the **reach gap** (arms can't reach the middle) + **conveyor moves only on command** (no free-riding). Red band marks the unreachable middle.
- **The headline learned skill = the box-workaround** (NOT `place-at-cell`, which is now a primitive). Arc: **"I can't grab it"** (embodiment gate → real dont-know) → **user teaches the box-workaround** → **"now I can"** → **the other arm learns it peer-to-peer**. The gate is the *reason* for the initial "I can't"; the box skill is the taught *bypass* (gate not removed, routed around via cooperation).
- **Under the hood (future-design, not demo):** "an arm learns to grab it" = a per-arm composite (`load-into-box`) + an Orchestrator **Plan** (route via box). Demo narrative keeps it as "the arm learned it." See `DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md`.
- **Box scarcity (optional / "if time" beat):** no box in reach → a distinct **resource** dont-know ("no box, can't"); resolving it means the Orchestrator routes a box to the loading arm first.
- **Grasp method:** **attach-on-valid-contact** (weld activates only on a genuine closed-gripper / suction-cup contact) — credible, reliable; not weld-on-proximity.
- **Governance / peer transfer / teachable vocabulary / add-remove:** see the Governance section and §5; net-new MindsOS features tracked in `DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md`.

### Graph-visualization tab (P3) — proving the metagraph
Each intelligence card gets a **Graph** toggle showing *that brain's relevant subgraph* (curated, animated — not the whole DB). Presentation script for when to surface it: (1) dont-know → needed node absent; (2) learning → new composite node appears + wires; (3) embodiment gate → capability node present but required-affordance edge unsatisfied; (4) peer transfer → node copies Arm 1→Arm 2; (5) degradation → affordance node greys, dependents ripple; (6) override → Local node shadows Global; (7) Orchestrator → one query across world-model + all robots' capability graphs. Show on beats 1/3/4 minimum. *(Live graph-from-FalkorDB rendering is a v10 build item.)*

### Core spine vs optional (P5)
**Core (rehearse bulletproof):** 1 dont-know → 2 learn box-workaround → 3 cooperative execution → 4 peer transfer + embodiment gate → 5 degradation/replan → 6 trace/graph recap.
**If-time extras:** teach a new position term · override a Global term · Sort · composed relational placement · box-scarcity beat · second peer-transfer trigger.
Graph view shown on **2–3 signature beats only** (gate, learning, transfer), not every beat.

---

## 1. The intelligences

Four MindsOS instances, each a separate brain with its own Local knowledge graph + a shared Global graph (per the L2 Global/Local split). The manager is "another user/agent" in the Server sense.

- **Manager** — no body. Bird's-eye fiducial view → symbolic world graph. Owns the user UI. Receives the order, decomposes it, dispatches across the three embodied brains, replans on failure, proposes promotions. (Heavy on **L4** orchestrator/replan/promotion + **L5** mental-model chain.)
- **Arm-1 "Lifter"** — fixed base, **suction** end-effector. Reaches the upstream conveyor segment + Bin Group L. Cannot reach downstream conveyor or Bin Group R.
- **Arm-2 "Packer"** — fixed base, **parallel-jaw** end-effector. Reaches the downstream conveyor segment + Bin Group R. Cannot reach upstream conveyor or Bin Group L.
- **Conveyor** — a reversible belt. Capacities: advance, reverse, hold, vary-speed, stage-at-position. It is the **sole physical bridge** between the two arms (their reach envelopes do **not** overlap), so it owns a genuine scheduling decision: which item occupies the shared surface, in which direction, staged into whose reach.

---

## 2. Layout & reach geometry (the load-bearing design)

> **This geometry is the engine. If any single arm can complete an order end-to-end, the cooperation is theater.** Prototype the reach envelopes *first* (see §6, prototype-zero).

```
   feeder chute
        |
        v
   [==== upstream belt ====]----GAP----[==== downstream belt ====]
        ^                                        ^
      Arm-1 (suction)                          Arm-2 (jaw)
        |                                        |
   Bin Group L (L1, L2)                     Bin Group R (R1, R2)
```

Invariants that force cooperation:

1. **No reach overlap between the arms.** A physical GAP in the belt span is reachable by neither arm — only the conveyor bridges it. Direct arm-to-arm handoff is impossible by construction.
2. **Each arm reaches only its own bin group.** An item destined for a bin on the *other* side must transit the belt.
3. **Items enter upstream only** (feeder chute onto the belt). So every item starts in Arm-1's half of the world.

Consequence: an order line whose target bin is in Group R requires Arm-1 → belt → Arm-2 → bin. An order line targeting Group L for an item arriving downstream-staged requires belt reversal. The manager must sequence all of this for throughput (Arm-1 stages the next item while the belt moves the last while Arm-2 packs the previous).

**Item ontology (three kinds — see §6 L-1 for why three, not two):**

1. **Dual-graspable carriers (majority)** — boxes both effectors can grip (jaw on the sides, suction on top). **These carry the cooperation:** a carrier entering upstream but destined for Bin R must go Arm-1 → belt → Arm-2, which is what makes the cross-belt **handoff** (an Orchestrator Plan, §5.1) a real, forced cooperation rather than two arms working in isolation.
2. **Effector-exclusive minority** — **parcels** (suction-only → Arm-1) and **cylinders** (jaw-only → Arm-2). These exist to power the embodiment gate: Arm-2's jaw is *refused* `pick-parcel` by its own embodiment; Arm-1's suction is refused `pick-cylinder` (§3 beat 4).
3. **The body-model** (Seam C, §5) is what makes the refusal real — capability is predicated on effector type, not just knowledge.

---

## 3. Single-run choreography — five features, one continuous demo

Each beat is an on-screen **chapter** (the UI must label it, or the complexity reads as random motion).

**Beat 0 — Order placed.** User composes an order in the UI as **(bin, attribute, quantity) lines, ordered by attribute — not item ID** (e.g. *L1: 1 parcel; R2: 2 carriers + 1 cylinder*). Items arrive mixed on the feeder, so the manager must **perceive and match** physical items to requested attributes, then allocate and sequence. Manager renders its decomposition and the world state.

**Beat 1 — Ignorant start → dont-know (thesis + explainable UI).** No brain yet knows the within-brain composite `place-at-cell`, and the Orchestrator has no `handoff` **Plan** to bridge the belt. The plan needs both; it hits a **dont-know** (family-specific dont-know contract) and surfaces the gap in the UI. *Nothing is pre-baked — the empty start is the thesis.* (Two levels — see §5.1: the learned/transferable *skill* is a within-brain composite; the cross-belt *handoff* is an Orchestrator Plan over per-brain capabilities.)

**Beat 2 — Acquisition by composition (learning).** User demonstrates a **within-brain composite** once — `place-at-cell` on Arm-1 = `move-to` + `align` + `release`. MindsOS captures it as a **Pipeline** → **promoted-pipelines** → registers a new composite capacity (capacity registration contract v2 + Pipeline-artifact contract §5.1). The cross-belt **handoff is the Orchestrator's *Plan*** assembled from per-brain capabilities (Arm-1 `place-on-belt`, conveyor `stage`, Arm-2 `pick-from-belt`) — *not* one brain's skill. UI shows the new composite node + its sub-capacity tree.

**Beat 3 — Cooperative execution.** The three brains run the new capacity to fulfill a cross-side line; manager parallelizes the next line for throughput.

**Beat 4 — Cross-robot transfer + embodiment gate (headliner + the subtle bit).** The `place-at-cell` composite learned on Arm-1 is promoted **Local → Global** (pending-promotions → Global). Arm-2 inherits it **but the affordance gate still applies** (§5.2): Arm-2 (jaw) is refused `place-Sheet` (suction-only); Arm-1 (suction) is refused `place-Tube` (jaw-only). UI shows knowledge transferring while capability is body-gated.

**Beat 5 — Degradation replan (resilience).** Inject a **partial** fault: a joint in Arm-2 is frozen in MuJoCo (*visibly* — the arm stops moving normally), degrading *one* sub-capability (e.g. fine-grasp for cylinders) while it can still grip carriers. A thin **self-diagnosis** capability detects the unresponsive actuator and writes the gap into `capacity-state`. Manager sees the **capacity-gap** appear, replans — reroutes cylinder-handling, keeps fulfilling carriers, conveyor re-stages as needed — showing visible recovery rather than a dead-stop. *Optional coda:* trigger a total dead-end (Arm-2 is the only reach to Bin R) so the system honestly surfaces a dont-know — "and when it truly can't, it says so."

**Beat 6 — Trace recap.** UI replays the mental-model history: gaps detected → capacity acquired → promotion → embodiment gate → degradation replan. The explainability payoff incumbents (Open-RMF, behavior trees) structurally can't show.

---

## 4. MindsOS layer / role mapping

What each piece of the demo exercises (names per `CLAUDE.md`):

- **L2 roles:** `capacity-state` (what each brain can do — queried by the manager), `capacity-gaps` (Global; detected missing capabilities, beats 1 & 5), `promoted-pipelines` + `pending-promotions` + `learned-parameters` (beats 2 & 4), `task-patterns` + `problem-trace` (decomposition + trace), `episodic_memories` (run retention). Plus `ontology` / `lexicon` / `concepts` for the order vocabulary.
- **L3 capacities:** `combination` (composition of primitives → composite), `decomposition` (order → lines → steps), `path-finding` / `scoring` (throughput-optimal sequencing), `perception` (fiducial → symbolic fact), `signalling` + `interaction` (inter-brain comms = the "communication capacity"), `learning-methods` (demonstration capture). Dont-know via the family-specific dont-know contracts; `produces`/`consumes` bipartite IntergraphEdges wire capability I/O.
- **L4 (manager):** per-session orchestrator, replan, attention queue, promotion-proposing. *Decisions live here as control flow over L3 capabilities (Chat A R1 boundary).*
- **L5:** the 6-level chain — HintSet → MappingResult → Plan → Pipeline → PipelineRun → TaskRun — is exactly what the UI renders. The demonstration in beat 2 produces the **Pipeline** level.
- **Server:** each brain is a session; inter-brain reads ride capability-based authorization (cf. the Phase-44 `CAN_READ_OTHER_LOCAL_*` roster pattern). Global promotion is a cross-session write.
- **Scope reality (updated 2026-06-10):** L4 + L5 **SHIPPED** (Phases 46–48; 49–50 closed the numbered plan). The gate is gone. Concrete shipped surface this demo rides: `IntelligenceLayer` + `orchestrator.run_lifecycle` six-phase lifecycle (Phase 47), MM consolidation → Episode/Memory + the ADR-0180 `writeable` gate + D′1 `retire_version` (Phase 48), capacity registration v2 with `produces`/`consumes` edges (Phase 42), family dont-know contracts (Phase 40), the four Phase-43 role-graphs (`capacity-gaps`, `pending-promotions`, `learned-parameters`, `parameter-staging`), and Phase-50 skill bundles. **Caveat:** the shipped `planning_v0`/`phase1_v0`/`orchestration_v0` catalogs are placeholders — Phase 49 proved the lifecycle dispatches no real L3 step. The demo must supply real planning/decomposition capacities. Implementation plan: `ROBOT_DEMO_MINDSOS_PLAN.md`.

---

## 5. Runtime interface seams (the four contracts to design)

The hierarchy's value is that each seam is a *different* interface — that heterogeneity is itself part of the showcase.

**Seam A — User ↔ Manager (the UI / L5 artifact made visible).**
- Structured order entry — (bin, attribute, quantity) lines, ordered by **attribute, not item ID** (L-2). Optional single constraint (priority / co-locate) as a stretch.
- Live mental-model view: the 6-level chain lighting up.
- Gap notification + demonstration prompt.
- Bird's-eye world view (fiducial-derived).

**Seam B — Manager ↔ sub-brain (inter-brain / "communication capacity").** Keep to four messages — every extra is on-stage breakage risk:
- `query-capabilities` (read the brain's `capacity-state`)
- `dispatch` (execute capacity X with params)
- `report` (success / fail / dont-know / capacity-gap)
- `promote` (Local → Global sync)

**Seam C — sub-brain ↔ body (capacity → actuation).**
- Primitive capacity → MuJoCo actuator command (joint target, gripper open/close, belt velocity).
- Sensor → symbolic-fact ingestion (fiducial pose → knowledge node).
- Fault / dont-know signal up from the actuation layer, incl. a thin **self-diagnosis** capability that detects an unresponsive actuator and writes the gap to `capacity-state` (L-3, beat 5).
- **Hosts the body-model** (reach envelope, effector type, DOF, payload) — powers the beat-4 gate.

**Seam D — Demonstration (the learning seam: stable contract, swappable input).**
- **Modality 1 — UI block-assembly (build first):** user sequences existing capacity blocks + params. Cheapest; unmistakably learning-not-coding; reuses the Seam-A UI.
- **Modality 2 — teleop-trace capture (later):** drive the arm through the sequence; MindsOS abstracts a Pipeline. Don't gate the demo on it.
- **Modality 3 — example I/O pairs (future):** feeds `learned-parameters`.
- **All three emit the same Pipeline artifact** → promoted-pipelines → composite capacity. *Design this artifact contract first; ship with Modality 1.*

### Governance — Local/Global authority (RESOLVED 2026-06-05)
- **User teaching → Local.** Any entity a user adds/teaches is **Local**. Users may add / modify / **retire** their Local entities freely.
- **Modify a Global → copy-on-write to Local.** Editing a Global entity creates a **Local alternative** that **shadows** the Global for that user; the Global original is untouched. Resolution order in a brain: **Local-first, fall back to Global.**
- **User cannot retire a Global locally** (would break dependents). Instead the user **replaces a Global with an *equivalent* Local alternative** — same contract/signature (name + required-affordances + produces) — which shadows the Global. Pure removal of Global is not user-available.
- **Global is admin-only.** Only an **admin** role may add/modify/retire Global. Maps to Server-layer capability auth: `CAN_WRITE_LOCAL` (user) vs `CAN_WRITE_GLOBAL` (admin).
- **Local forks/replacements are pinned** — an admin update to a shadowed Global does *not* propagate to the Local alternative (D′1 pin-at-instantiation); v1 UX = silently pinned.
- **Cross-robot transfer = peer Local→Local learning (RESOLVED).** Same user owns both brains, so Arm 1 teaches Arm 2 **directly — no Global, no admin**. New MindsOS feature (see `DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md`). The embodiment gate (§5.2) still filters what the receiving arm can execute. **Both share triggers, staged as distinct beats:** (i) **Orchestrator-mediated** — mid-plan it detects Arm 2 needs the skill and propagates it (autonomy); (ii) **explicit user** — "share to Arm 2" (control). Both gated on receipt.
- **Override scenario (Local-only, reuses Teach tab — no bespoke UI).** To demonstrate overriding a Global: the user **redefines a Global *position term*** (e.g. "center") via the Teach/modify affordance → copy-on-write creates a shadowing **Local alternative**; equivalence is trivial (a term's contract = its kind: offset/cell-set). Sequence must be **override → then place an order/sort using that term** so the change is *visible* (the item lands in the new cell). Inspect shows "Global · your Local override"; Global untouched; no admin. (Overriding a *term* over a *capability* because the effect is visible on camera.)
- **Admin = the presenter, out-of-band.** The live demo performs **no Global writes**, so no in-app admin role-switch and no admin UI. "Replace a Global" is a *Local* action (creates a Local alternative). v10 UI stays Local-scoped.
- **Demo emphasis:** what the user taught lands in *their* Local DB; the user has full power over Local; sharing to another of their machines is peer-to-peer.

### Position-definition artifact (teachable vocabulary)
Spatial terms are **learnable L2 knowledge**, not a fixed list. A term = a lexicon/concept entry grounded as a **grid offset** (relational, e.g. `above` = −1 row) or **cell/cell-set** (absolute, e.g. `top-left` = (0,0)); built-ins are the seed set. Unknown term in an order/sort → **dont-know** ("teach me what X means") → taught **by composition** of known terms or **by one example** (infer offset) → new entry, Local + promotable Global (transfers like a skill). Same learn→promote→inherit machinery as the Pipeline composite — one story: *knowledge, learned capacities, and learned intelligence are the same kind of editable L2 artifact.* Scope guardrail: offsets/cell-sets over the 3×3 only — no free-form geometry or NL definitions.

**Add/remove (user curation).** User-editable = the L2 learnable substrate (concepts/lexicon; learned composites in `promoted-pipelines`; `task-patterns`/`learned-parameters`). Primitive capacities + substrate are fixed. **Remove = retire** (version-IRI freeze + `retire_version`, reversible, preserves episode provenance), with a dependents check (block/cascade/warn) and explicit Local-vs-Global scope. UI for this is **v10** (reopens the v9 freeze deliberately).

### Two hard contracts everything else hangs on
1. **Pipeline artifact** (Seam D output → L5 Pipeline level → L2 promoted-pipelines) — **RESOLVED 2026-06-05: parameterized linear pipeline + explicit I/O bindings, scoped to within-brain composites.**
   - **Two levels (load-bearing):** the artifact is a **within-brain composite capacity** (e.g. `place-at-cell`); the cross-brain **handoff is an Orchestrator Plan** over per-brain capabilities (Plan level of the chain), *not* a single Pipeline. Don't conflate them.
   - **Shape:** `Pipeline{ name, version, inputs:[typed params], requires_affordances:[…], steps:[{capacity,args}], bindings (input/prior-output via produces-consumes), produces:DataState }`. Linear, no branching in v1; concurrency lives in the Orchestrator Plan.
   - **Example:** `place-at-cell(item, cell) = [move-to(approach(cell)), align(cell), release()]`, `requires_affordances:[grasp:<item>, reach:<cell>]`.
   - **Lifecycle:** register → composite capacity in capacity-state → promote Local→Global writes `promoted-pipelines` → other brain inherits, **gate (§5.2) still applies**. `requires_affordances` auto-derived where possible.
   - **Modality-agnostic capture (all → same artifact):** block-assembly builds steps+bindings directly (v1); teleop-trace segments + lifts concrete poses to params (v2); example-pairs infer params → `learned-parameters` (later).
   - **Open sub-decisions:** input type set (Object/ShelfCell/Pose — keep tiny); author-declared vs auto-derived affordances; whether the handoff Plan is persisted as a reusable `task-pattern`; pipeline versioning vs L5 D′1 version-IRI freeze.

2. **Body-model schema** (Seam C) — **RESOLVED 2026-06-05: affordance graph (symbolic gate) + thin IK reach check at execution.**
   - **Lives in:** each brain's **Local graph** as an `embodiment` structure (L2 knowledge about the body), consulted by L3 capacity feasibility. Keeps capacities fixed-not-learned while the body description stays editable knowledge.
   - **Shape:** `Body —has-part→ {Arm, EndEffector}`; `EndEffector —provides→ Affordance(grasp:suction|jaw)`; `Body —provides→ Affordance(reach:<region>)`. Objects declare requirements (Sheet `requires grasp:suction`; Tube `requires grasp:jaw`; Box `requires grasp:{suction∨jaw}`). Capabilities declare consumed-affordance preconditions (ties to L3 `consumes` IntergraphEdges).
   - **The gate = a feasibility query:** does my embodiment `provide` every affordance the capability + target `require`? If not → refuse with a *reason* ("requires effector=suction") → that is the on-camera embodiment gate and the DONT_KNOW.
   - **Degradation:** a fault disables a part/affordance node (wrist → disable `fine-grasp`); re-running the query fails → `capacity-gap` reappears → replan (beat 5). Falls out for free.
   - **Reach:** structural (each arm owns its shelf as a `reach:<region>` affordance for symbolic planning) + a thin IK check at execution for the specific cell. Geometry stays honest; the gate stays symbolic.
   - **Drop-in:** stub controller runs the affordance match in plain Python; MindsOS later runs it as a FalkorDB query over the `embodiment` graph — same contract.
   - **Affordance vocabulary v1:** `grasp:{suction,jaw}` + `reach:<region>`. `payload`/`dof` deferred.
   - **Open sub-decisions:** exact L2 home (new `embodiment` role-graph vs fields on capacity-state); whether `reach` stays an affordance or is purely structural + IK.

---

## 6. Risks, open locks, build sequencing

**Prototype-zero (do before anything else):** build the bare MuJoCo cell — 2 arms (one URDF, two end-effectors), reversible belt, bins, fiducials — and *empirically tune the reach envelopes* so the no-overlap + bin-partition invariants (§2) actually hold. If cooperation isn't forced by geometry, the whole demo is fake. Everything downstream depends on this.

**Open locks to close:**
- **L-1 Feasibility tension — RESOLVED (2026-06-05).** *Latent bug found:* purely effector-exclusive items (2-kind model) collapse feasibility to "each bin only accepts the type its arm grips," which means each arm grips *and* bins alone — **no handoff ever happens**, killing the `handoff-via-belt` centerpiece. **Resolution:** (1) three item kinds (§2) — dual-graspable carriers as the cooperation-carrying majority, effector-exclusive parcels/cylinders as the gate minority; (2) infeasibility handled as **(b), staged**: **v1 = detection** — manager detects an infeasible line (e.g. parcel → Bin R) and surfaces it as a gap, reusing the dont-know machinery already needed for beats 1 & 5 (zero extra cost, on-thesis); **v1.5 = resolution (stretch)** — the taught tote-loading workaround (Arm-1 loads parcel into a dual-graspable tote → belt → Arm-2 bins it), which adds the tote/jig mechanism and is therefore deferred until the base learning loop is proven.
- **L-2 Order-entry expressiveness — RESOLVED (2026-06-05).** Order = **(bin, attribute, quantity) lines, ordered by attribute not item ID.** This is the load-bearing choice: ordering by attribute forces the manager to perceive + match physical items, then allocate (reach + effector) and sequence (throughput) — rich, non-obvious planning with no NL parser and no constraint DSL. Rejected: explicit item→bin assignment (pre-decides allocation → no visible intelligence) and a full goal/constraint language (scope creep). One optional constraint (priority / co-locate) is a stretch only.
- **L-3 Fault-injection mechanism — RESOLVED (2026-06-05).** **Hybrid mechanism + partial degradation.** Freeze a joint in MuJoCo (visible on camera) *and* a thin self-diagnosis capability detects the unresponsive actuator → writes the gap to `capacity-state` (real introspective loop, on-thesis). Degrade *one* sub-capability, not the whole arm, so the manager has a recovery path to show (reroute) rather than a dead-stop. Total dead-end kept as an optional coda for the honest dont-know. Fallback if self-diagnosis is too much for v1: L2-level capability withdrawal + UI annotation (cleaner, weaker on camera). Grounding: withdrawal/restore = mutation of `capacity-state`; gap surfaces in `capacity-gaps`.

**Standing risks:**
- **Grasp reliability on camera.** Even in MuJoCo, contact/slip can whiff. Mitigation: tune grasp sites; consider attach-on-contact for non-grasp-critical items; rehearse.
- **Legibility vs complexity.** Dense multi-agent motion is illegible without the UI narrating *why* each move. Seam-A reasoning view does double duty (feature #4 + legibility). Budget for it.
- **Brain-count integration surface.** 4 instances × Seam-B = the main live-demo fragility. Keep Seam B to its four messages.
- ~~**Scope dependency.** L4/L5 unshipped (Phases 46–48).~~ **RESOLVED 2026-06-10** — shipped. The remaining scope risk is demo-side: the net-new F1–F6 features (`DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md`) still don't exist in the stack and the demo builds minimal versions of F1/F4/F5 itself.

**Suggested sequencing (updated 2026-06-10):** steps 1–2 are done (Phase A/B; contracts frozen 2026-06-05). Remaining build follows `ROBOT_DEMO_MINDSOS_PLAN.md`: deploy/bootstrap the 4 brains → L2 seeds + L3 capacity catalog → beats 1–3 (learning loop) → beats 4–6 (transfer, gate, degradation, recap) → UI narration + rehearsal + recorded backup.

---

## 7. The one-line pitch the demo must earn
> A user hands a hierarchy of MindsOS minds a job they don't yet know how to do; the minds discover the gap, learn the missing skill from one demonstration, share it among themselves within the limits of their bodies, recover when one of them breaks — and show their reasoning the whole time. No current robot stack does all of that.
