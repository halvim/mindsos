# Demo-Derived MindsOS Features — Future Design (next-chat prompt)

**Purpose.** While designing the robot demo (see the four `ROBOT_DEMO_*` docs), we invented MindsOS capabilities that don't fully exist in the shipped stack and need real design. This doc collects them so a **fresh chat** can pick up the MindsOS-design work without re-reading the demo thread.

**How to use.** Start a new chat, read `HANDOFF.md` + `CLAUDE.md` first, then this file. Each feature below has: *origin · what it is · why it's new · what needs designing · demo dependency*. Resolve them as proper MindsOS design (ADRs / phase work); the demo only needs a stub that behaves the same at the seam.

**Source docs:** `ROBOT_DEMO_SCENARIO.md`, `ROBOT_DEMO_ARCHITECTURE.md`, `ROBOT_DEMO_PROTOTYPE_PLAN.md`, `ROBOT_DEMO_OPEN_QUESTIONS.md`.

> **STATUS RECHECK 2026-06-10 (post Phases 46–50 + WSD design closure).** None of F1–F6 shipped as such, but the substrate they need did. Per-feature: **F1** still net-new (precedent grew: `CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY` shipped Phase 44; still no cross-Local *write*). **F2** still net-new; note the S10 promotion-loop mechanism was routed to **WSD Phase 55** — the demo cannot wait for it and builds a minimal Local-only learn loop instead. **F3** partially grounded: `retire_version` + `_retired_inline_pending` (D′1) shipped Phase 48; `CAN_WRITE_GLOBAL` + the ADR-0180 `writeable` gate shipped; copy-on-write shadowing + equivalence contract still undesigned. **F4** still net-new; the role-graph set is **closed at 13** (ADR-0150 §am-5/§am-6), so the demo's embodiment graph must live inside an existing Local role (decision in `ROBOT_DEMO_MINDSOS_PLAN.md`: `capacity-state`) — a new `embodiment` role needs an ADR-0150 amendment, which is future design, not demo work. **F5** partially grounded: bipartite `produces`/`consumes` + registration v2 (Phase 42) and runtime `register_capacity` give the composite half; the Pipeline-artifact→promoted-pipelines lifecycle remains demo-built. **F6** untouched. The demo-scoped minimal builds of F1/F4/F5 are specified in `ROBOT_DEMO_MINDSOS_PLAN.md` §7; this file stays the seed for the *real* designs.

---

## F1 — Peer Local→Local learning (NET-NEW)
- **Origin:** cross-robot transfer (beat 4) under the rule "Global is admin-only."
- **What:** a user's own machines share a learned entity **directly, brain-to-brain**, without promoting to Global or involving admin. "Same user, different machines."
- **Why new:** the shipped model is shared-Global + per-user-Local; **per-user peer Local↔Local sharing is not a documented mechanism.** (Precedent worth reusing: Phase-44 `CAN_READ_OTHER_LOCAL_*` roster — cross-Local reads already exist for episodic memory.)
- **Needs designing:** authorization (a `CAN_SHARE_LOCAL_TO_PEER` / cross-Local-write capability), the transfer mechanism + what travels (the Pipeline/position artifact), conflict/merge when the receiver already has a same-named Local entity, and interaction with the embodiment gate on receipt.
- **Demo dependency:** the headliner transfer beat. Stub: copy the artifact from Arm 1's store to Arm 2's, then apply the gate.

## F2 — Teachable spatial vocabulary as L2 lexicon/concepts (NEW grounding)
- **Origin:** "the relational vocabulary is a teachable feature."
- **What:** position/relation terms are **learnable L2 entries** grounded as grid **offsets** (relational) or **cell-sets** (absolute); built-ins are the seed set. Unknown term → dont-know ("teach me what X means") → taught by composition of known terms or by one example.
- **Why new:** spatial terms as first-class, user-extensible lexicon/concept entries (not a hard-coded enum) — and learned *vocabulary* (distinct from learned *capacities*).
- **Needs designing:** the grounding schema (offset / cell-set), the lexicon/concept entry shape, the "teach by example/composition" learning method, and the dont-know contract for unknown terms.
- **Demo dependency:** the "I don't know that position — teach me" beat; teachable Order/Sort relations.

## F3 — Curation governance: add / modify / replace / retire (NEW policy)
- **Origin:** "user should be able to add/remove knowledge/capacity/intelligence."
- **What:** what's user-editable is the **L2 learnable substrate** (concepts/lexicon; learned composites in `promoted-pipelines`; `task-patterns`/`learned-parameters`). Teaching → **Local**. Modifying a Global → **copy-on-write** to a shadowing Local alternative (resolve Local-first). **User cannot retire a Global** (breaks dependents) → instead **replace with an equivalent** (same contract). **Global is admin-only** (`CAN_WRITE_GLOBAL`). Remove = **retire** (versioned, reversible), never hard-delete. Local forks **pinned** (don't track Global updates).
- **Why new:** a concrete authority + copy-on-write + retire-not-delete model layered on the Local/Global split.
- **Needs designing:** the **equivalence contract** (what makes a replacement valid: name + required-affordances + produces), referential-integrity policy on retire (block/cascade/warn), retire/version mechanics (ties to D′1 `retire_version`), and the Server permission set.
- **Demo dependency:** "what you taught is in your Local DB; you have full power over Local"; replace-a-Global beat.

## F4 — Body-model / affordance graph for embodiment gating (schema addition)
- **Origin:** the embodiment gate must be real, not faked.
- **What:** per-brain Local `embodiment` graph (parts → affordances); objects *require* affordances; capabilities *consume* them; feasibility = graph query; degradation = disable an affordance node. (Full spec: `ROBOT_DEMO_SCENARIO.md` §5.2.)
- **Needs designing:** exact L2 home (new role-graph vs fields on capacity-state), affordance vocabulary, tie to L3 `produces`/`consumes` IntergraphEdges.
- **Demo dependency:** beats 4 (gate) and 5 (degradation).

## F5 — Pipeline artifact + Plan/Pipeline level distinction (contract)
- **Origin:** "learn by demonstration → composite capacity."
- **What:** within-brain composite = parameterized linear **Pipeline** (steps + I/O bindings + required-affordances); cross-brain handoff = Orchestrator **Plan** (not a single Pipeline). (Full spec: `ROBOT_DEMO_SCENARIO.md` §5.1.)
- **Needs designing:** param/type model, author-declared vs auto-derived affordances, pipeline versioning vs L5 D′1 version-IRI freeze, whether the handoff Plan persists as a `task-pattern`.
- **Demo dependency:** the learning beat + transfer.

## F7 — Device-aware installation (per-device-type capacity provisioning) (NET-NEW)
- **Origin:** robot-demo Round-3 (2026-06-10) — MindsOS will install on different device types (computer / phone / robot); on each install it should know "where" it is and provision **device-type-exclusive** capacities + knowledge.
- **What:** an installation carries a **device identity / profile** (device type + capabilities of the host body); the install lifecycle selects which skill bundles / capacity sets apply to *this* device type and installs only those. Each device is its own MindsOS instance with its own Global+Local L2, L3, L4.
- **Why new:** Phase-50 skill bundles install unconditionally — the manifest has **no device-type gate** and there is no shipped notion of installation/device identity ("where am I"). Bundle selection by device type does not exist.
- **Needs designing:** the device-identity model (how an install detects/declares its type), a manifest-level `applies_to_device_types` gate (+ how it composes with the closed role-set and the ADR-0180 install gate), profile→bundle resolution, and the relationship to the multi-instance topology (one Server hosting N device-instances vs N Servers).
- **Demo dependency:** the opening "4 different devices, each MindsOS provisioned the right capacities for its body" beat. Demo-scoped minimal build: a `DeviceProfile` / `DeviceInstance` struct in `demo_backend` with a static profile→bundle map (`core`→all, `arm-suction`→arm1, `arm-jaw`→arm2, `conveyor`→conv, `manager`→mgr); mechanism = shipped Phase-50 `install_skill`; selection logic lives in `demo_backend`, zero `mindsos_*` edits. See `ROBOT_DEMO_MINDSOS_PLAN.md` P-1/P-8 + design-log §3.

## F6 — Box-as-resource (resource-availability in planning)
- **Origin:** "no box around → no way to grab the item the arm can't grab."
- **What:** the carrier Box is a **finite resource**; its absence is a distinct **resource dont-know** ("no box, can't"), separate from a capability gap or knowledge gap. Resolving it requires the Orchestrator to **route a box** to the loading arm before the handoff.
- **Why new:** introduces resource availability as a planning precondition + a third dont-know category.
- **Needs designing:** resource modeling (box supply per arm), the resource-gap dont-know contract, Orchestrator resource-acquisition planning.
- **Demo dependency:** optional "if time" beat.

## Note on F5 — the box-workaround is a composite + a Plan
The demo's headline learned skill ("I can't grab it → taught → I can → other arm learns") is the **box-workaround**. Under the hood it is **not** a single within-brain capability: it's a per-arm composite (`load-into-box`) **plus** an Orchestrator **Plan** (route cargo via a box across the reach gap). Demo narrative says "the arm learned it"; the design must split it per F5. Peer transfer (F1) moves the per-arm composite; the Plan lives in the Orchestrator.

---

## Convention for new features going forward
Any further net-new MindsOS capability invented while building the demo gets a new `Fn` entry here (origin · what · why-new · needs-designing · demo-dependency). This file is the single seed for the future MindsOS-design chat(s); the demo proceeds against stubs that honor the same seam behavior.
