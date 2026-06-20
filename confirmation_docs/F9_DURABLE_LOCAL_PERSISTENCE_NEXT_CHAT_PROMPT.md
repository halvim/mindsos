# MindsOS chat prompt — F9: durable Local persistence + capacity re-activation on reboot (Full)

This is a **MindsOS-core feature chat** (it edits `mindsos_*` — unlike the robot-demo chats, which are barred from it). It originates from the robot demo's F9 derived-feature and was scheduled "Full" at the DM-8 reanalysis (2026-06-15): the demo's Mode-B "reload" needs a learned skill to survive a process restart, which requires durable per-device **Local** persistence plus a **capacity re-activation** contract. After this chat ships, **DM-8** consumes it (the demo wires `load_or_mint_local` + a boot re-teach + `import_state`/Mode-B).

## Goal
Ship **Full F9**: (a) durable per-device **Local** KL persistence across a restart, and (b) a generic **capacity re-activation** contract so descriptor-driven learned/bundle capacities become runnable again on reboot — without serializing Python callables.

## Read first
1. `CLAUDE.md` (root) + `HANDOFF.md` (root) — current MindsOS phase state (Phase 50 shipped; WSD 51–56 reserved; DWF 57+). **Decide where F9 slots** (new phase vs maintenance) and **which branch** it forks (the MindsOS line / `main`, NOT `robot-demo-animation`; coordinate with the parked Phase-51 tree).
2. `confirmation_docs/DEMO_DERIVED_FEATURES_NEXT_CHAT_PROMPT.md` **F9 entry** (the decision + grounding summary) — start here.
3. The shipped machinery to reuse (probe-confirmed 2026-06-15):
   - `mindsos_server/persistence/local_persister.py` — **`FalkorDBLocalPersister`** (Phase 44, ADR-0160): `load(user_id)->Optional[Metagraph]`, `save(user_id, mg)`, scoped `delete(user_id)->bool`. **Dormant**: not in `mindsos_server.persistence.__all__`; no v1 consumer (Phase-44 CR-3 deferred login/logout Local writes).
   - `mindsos_core/persistence/value_codec.py` — **`encode_node_value`/`decode_node_value`** (Phase 50, ADR-0182), wired into `graph_repository.py` (persist) + `reconstruction/graph_loader.py` (load). Fixes dict-valued nodes (Episode, `learned-parameters`). The persister routes through these → dict values already round-trip.
   - `robot_demo/backend/persistence.py` `load_or_mint_global` — the **template** to mirror for a `load_or_mint_local` (find-by-name → load, else mint). Globals persist; Locals are re-seeded in-memory (PB-Z).
   - `mindsos_capacity/capacity_layer.py` `register_capacity` + `_declarations` — registration is **in-memory only**; `register_capacity` writes a graph node (metadata + PRODUCES/CONSUMES edges) but **not** the bound `implementation` callable. On reboot `get_declaration` raises.
   - Phase 50 skill activation: `mindsos_server/skills/{driver,records}.py` + `installed-skills` role-graph — the existing precedent for re-activating bundle capacities at boot (`apply_installed_skills`); F9's generic contract should subsume/align with it.
4. ADRs to read: 0160/0161 (Local persister + version markers), 0151/0152 (storage_mode + L2 schema v2), 0182 (value codec), 0150 §am-5/6 (role-set), 0177 (D'1 retention), 0042 (install/extract hooks).

## What's shipped vs net-new (probe verdict)
- **Part (a) durable Local persistence — ~80% shipped.** Net-new = export `FalkorDBLocalPersister`; a `load_or_mint_local(client, user_id)` factory; a **load-Locals-on-boot lifecycle**; the **persist/retain vs reset boundary**; tests. Small-to-moderate core delta.
- **Part (b) capacity re-activation — net-new and the hard half.** A capability `implementation` is a live closure → **cannot be pickled**. Re-activation must be **descriptor/factory-driven**: persist the capability node's metadata + a re-activation key; on Local load, walk capability nodes and **rebuild the declaration from properties** (`_CapacityBase.from_properties()` or a re-activation-factory registry), then `register_capacity(..., if_exists="upsert")` to repopulate `_declarations` + re-emit edges. Descriptor-driven caps (learned skills = `make_taught_impl(steps)`; bundle skills) rehydrate cleanly; **arbitrary code-bodied caps re-activate by re-running their installer**, not by deserialization — the contract must make that distinction explicit.

## Pushbacks to resolve early (probe, don't assume)
- **Reset/boot-determinism (load-bearing).** The demo keeps Locals in-memory by choice (PB-Z) for a deterministic boot smoke + trivial reset. Persisting Locals breaks that unless F9 defines **what survives vs what resets** (proposal: learned skills/installed-skills survive; episodes/run-state/placed-orders are run_id-scoped and wiped). Use the shipped `FalkorDBLocalPersister.delete` for the reset path. Pin this contract before coding.
- **Callable non-serializability.** Do NOT attempt to serialize `implementation`. Confirm the re-activation registry approach against every capability *kind* (`Capacity`/`Monitor`/`Adapter`/`DreamCapacity`) — some have no descriptor and must re-activate via installer re-run.
- **Alignment with Phase-50 skill activation.** F9's re-activation must not double-register or conflict with `apply_installed_skills` / the install-record no-op-on-digest-match. Decide whether F9 *is* the general boot re-activation path that bundle activation plugs into.
- **D'1 retention round-trip.** `_retired_inline_pending` is a plain property → survives; confirm `read_at_version`/`retire_version` still resolve correctly after a persist+reload of a Local with retired versions.
- **Multi-Local / scope.** `FalkorDBLocalPersister` keys by `user_id` (Local metagraph `local_knowledge:<user_id>`); the demo keys Locals by `device_id`. Confirm the key contract + the `CAN_*_OTHER_LOCAL` capability interactions (Phase 44 added read-only cross-Local caps; F9 is about own-Local persistence).

## Deliverables
- Export + `load_or_mint_local` + load-on-boot lifecycle (part a).
- `_CapacityBase.from_properties()` (or a re-activation factory registry) + the Local-load re-hydration walk + re-registration loop (part b).
- The persist/retain vs reset boundary contract.
- ADRs (re-activation contract; Local-persistence lifecycle; reset boundary) + amendments to 0160/0042 as needed.
- Tests: Local round-trip survives a simulated restart; a descriptor-driven learned capability is runnable (`invoke`) after reload without re-registering from code; reset wipes run-state but retains learned skills; retention round-trip.
- Slot into the post-Phase-50 map; update `HANDOFF.md` + write the next-chat prompt.

## Conventions
Critical-design-reviewer posture; probe the shipped persister/codec/CapacityLayer before designing; list pushbacks with options + your pick. Pair-execution (Cowork builds + sandbox-validates; Mac commits; Linux runs the gate — authoritative). Honor `no-sandbox-git-mutations` + the parked-tree note (scope-add only F9 paths, never `-A`). Full ceremony: ADRs, cumulative gate, confirmation doc.

## After F9 ships → DM-8 (robot demo) consumes it
`confirmation_docs/ROBOT_DEMO_DM8_NEXT_CHAT_PROMPT.md` Mode-B reload becomes: demo `persistence.py` calls `load_or_mint_local`; a boot loop re-teaches learned skills from persisted `learned-parameters` descriptors; `import_state`/Mode-B restores a saved demo-state onto the durable Locals. (DM-8's other items: clip-replay = live-recorded cache pre-fill or deferred; `verification[]` deferred; UI wiring = UI chat.)

## Gate
A per-device Local with a learned (descriptor-driven) capability is persisted, the process is restarted, the Local is reloaded, and the capability is **runnable via `invoke` without re-registering from code**; the reset path wipes run-state while retaining learned skills; D'1 retention round-trips; no regression to the cumulative MindsOS gate.
