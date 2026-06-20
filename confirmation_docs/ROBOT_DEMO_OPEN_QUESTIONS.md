# MindsOS Robot Demo — Pushbacks, Discussion Points & Open Questions

Consolidated record from the design conversation. Tags: **[resolved] / [open] / [deferred]**.
Companions: `ROBOT_DEMO_SCENARIO.md`, `ROBOT_DEMO_ARCHITECTURE.md`, `ROBOT_DEMO_PROTOTYPE_PLAN.md`, `demo_ui/` (frozen v9 UI).

---

## 1. Strategic / thesis
- **L4 + L5 unshipped (Phase 48).** The orchestrator + mental model — the "brain" — is the gated part. Full demo depends on it. **[RESOLVED 2026-06-09/10 — Phases 46–48 SHIPPED (49–50 closed the plan). Caveat: the v0 planning catalogs are placeholders; the demo supplies real planning capacities — see `ROBOT_DEMO_MINDSOS_PLAN.md`.]**
- **Open-RMF already does heterogeneous fleet orchestration.** Demo must prove what it can't: gap-driven learning, capacity-degradation replan, or cross-layer introspection. **[resolved — learning / transfer / replan is the claim]**
- **"Learns everything, not knows everything"** ⇒ start ignorant, earn capability on stage; never pre-bake the skill. **[resolved]**
- **Never present scripted motion as MindsOS thinking** (the stub controller speaks the real interface so the swap is honest). **[resolved]**
- **Recurring discipline:** what single capability is this proving, and is it shipped? **[open]**

## 2. Scenario mechanics
- **Reach geometry is load-bearing** — cooperation forced by geometry, not script; validate first. **[resolved — prototype-zero passed]**
- **Latent bug:** purely effector-exclusive items kill the handoff engine → 3 item kinds (dual-graspable majority + exclusive minority). **[resolved]**
- **Feasibility tension (L-1):** effector × reach can yield impossible orders → detection now. **[resolved]**; taught tote/jig workaround **[deferred — v1.5]**
- **Conveyor must make a real decision** (contended shared resource) or it's decorative. **[resolved — it's a brain]**
- **Embodiment gate needs a real body-model**, not a faked refusal; gate on effector type. **[resolved]**
- **Degradation = partial fault** (recoverable, shows replan), hybrid mechanism (visible freeze + self-diagnosis), total dead-end as optional coda. **[resolved]**
- **Order by attribute, not ID**; structured entry, not NL. **[resolved]**
- **Bins → per-arm 3×3 shelves** with relational placement (bins alone showed no intelligence). **[resolved]**
- **Shelves:** within-shelf relations only; discrete slots, no gravity stacking; **no per-arm row-reach gate** (unsolvable dead-ends). **[resolved]**
- **"Learning" = capacity by composition**, not learning the meaning of spatial relations. **[resolved — don't overclaim]**
- **Relational vocabulary is TEACHABLE (open, not closed). [RESOLVED 2026-06-05]** A position term is an L2 **lexicon/concept** entry grounded as a **grid offset (relational) or cell/cell-set (absolute)** over the 3×3; built-ins are just the seed set. Unknown term → **dont-know** ("teach me what X means") → user teaches **by composition** of existing terms or **by one example** (infer offset) → new entry, Local + promotable Global (taught terms transfer between brains like skills). Keeps it genuine *new-vocabulary* learning, NOT learning spatial semantics from raw experience (scope guardrail: offsets/cell-sets over the grid only — no free-form geometry/NL).
- **Add/remove of learned content (user curation). [RESOLVED 2026-06-05 — framing + retire model]** What's user-editable is the **L2 learnable substrate**, and all three categories bottom out there: *knowledge* = concepts/lexicon; *capacity* = learned composites (`promoted-pipelines`); *intelligence* = `task-patterns` + `learned-parameters`. **Fixed/non-editable:** L3 *primitive* capacities (fixed-not-learned) + L1/L4 substrate. **Remove = retire** (version-IRI freeze + `retire_version`, reversible, preserves episode provenance) — NOT hard-delete. Demo scope: add+retire a **position term** and a **learned composite**.
  - Open sub-decisions: referential-integrity policy on retire (block / cascade / warn) when a term/composite has dependents. **[STILL OPEN — UI v10.2b (2026-06-11) ships the surface only: it shows the dependents and proceeds reversibly; the block/cascade/warn semantic is left as a single parameter for a future MindsOS chat. See `ROBOT_DEMO_UI.md` §7.]**
- **Governance — Local/Global authority. [RESOLVED 2026-06-05 — see `ROBOT_DEMO_SCENARIO.md` Governance section]** User teaching → Local; users CRUD Local freely; modifying a Global copy-on-writes a shadowing Local alternative (resolve Local-first). **User cannot retire a Global** (breaks dependents) — instead **replaces it with an equivalent** Local one. Global is **admin-only** (`CAN_WRITE_GLOBAL`); Local forks pinned. **Admin = presenter, out-of-band — no in-app admin UI; demo does no live Global writes.**
  - **Beat-4 reconciliation [RESOLVED — peer Local→Local learning]:** cross-robot transfer is machine-to-machine for the same user (no Global, no admin). New MindsOS feature → `DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md`.
  - **Peer-transfer trigger [RESOLVED — both]:** Orchestrator-mediated (autonomy) *and* explicit user "share to Arm 2" (control), staged as two distinct beats; both gated on receipt.
  - **Override / replace-a-Global [RESOLVED for demo]:** demo overrides a Global **position term** (visible), reusing the Teach tab — no bespoke UI; equivalence is trivial for terms (kind = offset/cell-set), sidestepping a general equivalence-check in v1. Sequence: override → then place using the term so the effect shows. (General equivalence contract for *capabilities* remains future work — `DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md` F3.)
- **Relational placement — live reasoning vs scripted. [RESOLVED 2026-06-05 — deterministic resolver, solver-shaped interface; infeasible/conflict → dont-know.]** v1 resolves composed clauses live by filtering the 3×3 (each clause narrows candidates; effector affordance pre-filters; fixed-order tie-break); a real CSP/backtracking solver (option C) is deferred and only needed if multi-item competing-cell boards are wanted. Infeasibility flows into the existing gap/learn/replan loop rather than being a solver flex. Optional: UI highlights candidates narrowing per clause (stronger on camera). Sub-decisions still open: single- vs multi-item boards; tie-break rule; show-live-narrowing.

## 3. Architecture
- **MindsOS can't run in a browser** (FalkorDB + Python) → client–server web app. **[resolved]**
- **No web/API layer today — CLI only** → build a new backend service. **[resolved — in plan]**
- **Each brain = full MindsOS on its own FalkorDB DB**; run as multiple graphs in one server on the old Mac Mini (RAM). **[SUPERSEDED 2026-06-10 → one MindsOSServer process; the 4 brains = 4 users/sessions, each with its own Local metagraph + own `IntelligenceLayer`, sharing one Global + one FalkorDB. Matches the shipped Server model and makes Local/Global + peer-transfer real, not emulated.]**
- **Stub controller (Phases C/F).** **[SUPERSEDED 2026-06-10 → direct-to-MindsOS; stub stage dropped, Phase F dissolved into Phase C. See `ROBOT_DEMO_PROTOTYPE_PLAN.md` §0 amendment.]**
- **Browser render (stream poses) vs server render (needs GL).** Old Mac Mini Linux GL flaky → browser render. **[resolved]**
- **Mac Mini runs Linux** (earlier macOS/Docker assumption corrected). **[resolved]**
- **Live demos crash → recorded backup mandatory.** **[resolved]**
- **2D top-down for reasoning legibility; 3D for wow** — keep both. **[resolved]**

## 4. UI / presentation
- **Brains aren't equal** — Orchestrator prominent; hierarchy visual. **[resolved]**
- **Four full reasoning panels risk overload** — recommended curation; user chose show-all-equal. **[resolved — user's call, legibility flagged]**
- **Thinking UI shows events + L5 chain, not raw graph dumps.** **[resolved]**
- **Pacing:** auto-advance vs manual click-through for live narration. **[open]**
- Offered, not built: **live target-cell highlight** during relation resolution; **"focus mode"** for the brain panels. **[open]**

## 5. Build / effort
- **Grasping is the sim pain point** → **attach-on-valid-contact** for v1 (weld on genuine closed-gripper/suction contact; containment = attach-on-insertion). **[resolved — supersedes earlier "cheat-grasp"]**
- **Asset → glTF pipeline is real new work** (cost of browser rendering). **[RESOLVED 2026-06-07 — Phase A: `sim/export_gltf.py` bakes per-body meshes → `web/assets/*.glb` + `web/manifest.json`; reconstruction verified. Note: ~16 MB high-poly Franka visuals; decimate in Phase D if first-load latency bites. See `ROBOT_DEMO_PHASE_A_REACH.md`.]**
- **UI v10 (reopens the v9 freeze, deliberately):** Teach tab gains **teach / inspect / retire** for position terms *and* learned composites; newly taught terms appear in the relation/position dropdowns. **[open — needed for the teachable-vocabulary + add/remove feature]**
- **Suction gripper not in Menagerie** → custom tip. **[resolved]**
- **Multi-week developer build, not a script** — needs a developer (or assistant across sessions). **[open reality]**

## 6. Contracts to freeze before deep build
- **Pipeline artifact** (demonstration → L5 Pipeline → L2 promoted-pipelines). **[RESOLVED 2026-06-05 — parameterized linear pipeline + I/O bindings, within-brain composite; handoff = Orchestrator Plan; see `ROBOT_DEMO_SCENARIO.md` §5.1]**
- **Body-model schema** (powers the embodiment gate). **[RESOLVED 2026-06-05 — affordance graph + thin IK reach check; see `ROBOT_DEMO_SCENARIO.md` §5.2]**

## 7. Locks recorded
- Arms: **Franka Panda ×2** (Arm 1 suction tip, Arm 2 Robotiq 2F-85). Grasp: **attach-on-valid-contact**. Network: **decide later** (LAN-first).
- UI: **v9 frozen** as official visual baseline; **v10 = Phase D** (built against live data, not mocked).
- Scenario cooperation engine: **per-arm vertical shelves + carrier-box workaround over a reach gap with command-driven conveyor**.

## 8. Round-2 resolutions (2026-06-05) — carrier-box + presentation
- **Cooperation = carrier-box workaround** (cargo a receiving arm can't grasp → loaded into a Box by the arm that can → conveyor across the reach gap → receiving arm grabs the Box; delivered boxed). Belt = continuous surface; forcing comes from the **unreachable middle + command-driven conveyor**. **[resolved — see scenario §0a]**
- **Headline learned skill = the box-workaround** ("I can't" → teach → "I can" → other arm learns peer-to-peer); `place-at-cell` demoted to primitive. Gate = the *reason* for "I can't"; box skill = taught *bypass*. **[resolved]**
- **Item taxonomy:** Box = carrier/container · Sheet = suction cargo · Tube = jaw cargo. **[resolved]**
- **Box scarcity** = optional resource-gap dont-know ("no box, can't"). **[resolved — optional/if-time; feature F6]**
- **P3 graph-viz tab** + presentation script. **[resolved — design in scenario §0a; live render = v10/Phase D build]**
- **P5 core spine** (6 beats) vs if-time extras; graph shown on 2–3 signature beats. **[resolved]**
- **P6 grasp credibility** = attach-on-valid-contact; **P6.2 interaction** = control-token on a shared sim (one driver at a time, presenter reclaim, Reset; input limited to orders/teach/sort). **[resolved]**
- **P2 reach re-validation** on real Panda + vertical shelves (top-row-at-distance risk) — first task in Phase A. **[RESOLVED 2026-06-07 — Phase A PASS. Pose-reachability IK (not 2D circle): 9/9 shelf cells both arms, own belt reachable, belt middle unreachable → cooperation forced. Going-in assumption overturned: top-row was NOT the binding constraint — the gap wasn't forced at prototype_zero spacing (real Panda reach ~0.85 m), and the shelf CENTRE column failed (belt/shelf opposite sides → joint-1 dead cone). Fixes: bases ±1.15, each arm faces its shelf, per-arm rack depth (asymmetric EEs). See `ROBOT_DEMO_PHASE_A_REACH.md`.]**
- **Still open:** pacing; live target-cell highlight / focus mode; single-vs-multi-item boards; retire integrity policy; network LAN-vs-tunnel; the asset→glTF pipeline + v10 build.
