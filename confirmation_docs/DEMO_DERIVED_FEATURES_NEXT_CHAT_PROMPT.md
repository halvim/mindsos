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
- **DM-2 grounding (2026-06-11):** the "fields on capacity-state" branch is **forced** — `capacity-state` ships a single `CapacitySnapshot` NodeType and **zero EdgeTypes**, and type registration is enforced even at `strict=False`, so a typed BodyPart/EndEffector subgraph with provides/has-part edges is unbuildable without a schema edit (forbidden). DM-2 property-encodes the whole embodiment in one `CapacitySnapshot` value (read by `validate.feasibility`). A *real* affordance subgraph therefore requires a new role-graph (see **F8**), not capacity-state fields.

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

## F8 — Real `embodiment` Local role-graph (schema addition; grounds F4)
- **Origin:** robot-demo DM-2 (2026-06-11). The embodiment "subgraph" had to be property-encoded inside a `capacity-state` `CapacitySnapshot` value because that role's schema is single-NodeType / zero-EdgeType and a schema edit is forbidden (PB-W).
- **What:** a per-user Local `embodiment` role-graph in the closed role-set with typed `BodyPart`/`EndEffector`/`AffordanceProvision` NodeTypes + `has-part`/`provides` EdgeTypes, so feasibility is a real graph walk (not a property read) and degradation disables an affordance *node/edge*.
- **Why new:** the closed role-set (ADR-0150) forbids a new role without an amendment; `capacity-state`'s schema can't host the types; Local metagraphs only auto-create `episodic_memories` + `capacity-state`.
- **Needs designing:** ADR-0150 role-set amendment (+1 Local role), the schema (NodeTypes/EdgeTypes), Local storage_mode, and migration of the DM-2 property-bag encoding into the typed graph.
- **Demo dependency:** none at DM-2 (the property-bag encoding suffices through DM-3+); this is the productized successor.

## F9 — Durable Local persistence + bundle-installer re-activation on reboot
- **Origin:** robot-demo DM-2 (2026-06-11). DM-2 persists per-device **Globals** only (PB-Z); Locals are in-memory and re-seeded each boot, and `install_skill` no-ops on reboot (digest match) so a bundle's L3 installer does **not** re-run via the install path.
- **What:** (a) durable per-device **Local** persistence (episodes/learned composites survive a restart) with a clean reset story that still wipes run-state; (b) a reboot re-activation contract so a bundle's L3 **capacities** (not just KL-resident DataStates) are re-registered into the fresh in-memory CapacityLayer — i.e. wiring `apply_installed_skills` into the boot path.
- **Why new:** Phase-42/50 keep the CapacityLayer in-memory; the install record's no-op short-circuit means installers don't re-run on reboot. DataStates survive only because they live in the persisted Global; capacities would be lost.
- **Needs designing:** the persisted-Local vs reset boundary (run_id-scoped durable store), and whether boot calls `apply_installed_skills` per device before/after `install_skill`.
- **Demo dependency:** latent at DM-2 (no bundle registers capacities; §4 embodied caps are registered directly each boot in DM-3). Becomes load-bearing if any demo capacity ever ships *inside* a bundle.

## F10 — `register_capacity(if_exists="upsert")` should re-bind the implementation
- **Origin:** robot-demo DM-4 (2026-06-12, design-log §19 PB-WW). The demo needs to run real logic under the shipped v0 capacity IRIs so the live chain is honest.
- **What:** `upsert` currently back-fills the PRODUCES/CONSUMES edges but does **not** re-assign `self._declarations[iri]` (that assignment is on the first-registration branch only, `capacity_layer.py:350-371`); the dispatcher resolves the impl via `get_declaration → _declarations`, so `upsert` is a **behavioural no-op** — it cannot swap a capacity's implementation. A consumer-facing `re_bind`/`upsert`-that-replaces-impl would make same-name override a supported operation.
- **Why new:** today the only working override is a consumer reaching into the private `_declarations` dict (the demo's `comms.install_override`) — fine for the demo, but a private-API dependency MindsOS should make first-class if override is a real use case (it is, for WSD/skill swaps).
- **Demo dependency:** worked-around in DM-4 (`install_override`); no blocker.

## F11 — `Orchestrator.run_lifecycle` twice on one instance collides chain IRIs
- **Origin:** robot-demo DM-4 (2026-06-12, design-log §21 PB-HHH). The 2nd `place_order` on a brain crashed (`IdentityError: Duplicate id 'hintset:<scope>:1'`).
- **What:** `ChainArtifactWriter` mints IRIs as `{prefix}:{task_scope}:{seq}` with `seq` reset per lifecycle, so a single `Orchestrator` (fixed `task_scope`) reused across tasks re-mints identical chain-node IRIs → the MM's chain graph collides. Either `run_lifecycle` should derive a per-run uniquifier (e.g. fold `task_id` into the writer scope) or guard/namespace per run, so one Orchestrator can serve many tasks.
- **Why new:** the shipped contract implicitly assumes one Orchestrator (or one `task_scope`) per task; nothing enforces or documents it, and the failure is a hard crash on the 2nd run.
- **Demo dependency:** worked-around in DM-4 (`brain.run_task` = fresh Orchestrator + unique `task_scope` per lifecycle); no blocker.

## F12 — v0 planning passes no milestone identity to `is_leaf`/`decompose`
- **Origin:** robot-demo DM-7 (2026-06-15, design-log §27, probe A). Building the carrier-box multi-leaf Plan via the per-CL decompose override.
- **What:** `plan_construction._decompose_recursive` dispatches `planning.is_leaf` and `planning.decompose` with a **hardcoded empty milestone** (`{DS_MILESTONE: {}}`) — neither the milestone identity nor its depth reaches the capacity body. So a per-CL override that needs to branch on *which* milestone (e.g. root-not-leaf, children-leaf; or per-device child specs) must be **stateful** (a call-counter) rather than a pure function, and child device identity (arm1/conv/arm2) cannot ride on the orchestrator's milestone — it must travel out-of-band (the DM-4/5 `task_pattern_iri`/`encode_target` side-channel).
- **Why new:** the shipped v0 contract decomposes blind; a real `planning.decompose` (WSD) would need the milestone passed in to emit identity-bearing children. Nothing currently threads it.
- **Demo dependency:** worked-around in DM-7 (stateful override + side-channel, probe-validated); no blocker. Fixing first-class needs a `mindsos_*` change → out of demo scope.

## Note on F5 — the box-workaround is a composite + a Plan
The demo's headline learned skill ("I can't grab it → taught → I can → other arm learns") is the **box-workaround**. Under the hood it is **not** a single within-brain capability: it's a per-arm composite (`load-into-box`) **plus** an Orchestrator **Plan** (route cargo via a box across the reach gap). Demo narrative says "the arm learned it"; the design must split it per F5. Peer transfer (F1) moves the per-arm composite; the Plan lives in the Orchestrator.

---

## Convention for new features going forward
Any further net-new MindsOS capability invented while building the demo gets a new `Fn` entry here (origin · what · why-new · needs-designing · demo-dependency). This file is the single seed for the future MindsOS-design chat(s); the demo proceeds against stubs that honor the same seam behavior.
