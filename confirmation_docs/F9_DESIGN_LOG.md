# F9 — Durable Local persistence + capacity re-activation on reboot — DESIGN LOG

**Status:** Design complete; implementation deferred to a fresh chat.
**Branch (to open):** `feat/f9-durable-local` off `main` (NOT a numbered phase).
**Base:** `main` @ `927706c` (includes the upsert-rebind prerequisite, ADR-0156 §amendment-1).
**Scope (core chat):** `mindsos_*`, `tests/`, `docs/`. **Do NOT touch** `projects/robot_demo` (demo/robot) — the demo wires F9 later (DM-8).

---

## 0. Prerequisite already shipped

The **upsert re-bind** fix (`feat/upsert-rebind`, merged to `main` @ `20d4686`, gate green) is the enabling half of part (b): `register_capacity(..., if_exists="upsert")` now re-binds the in-memory declaration (`_declarations[iri]`), so re-registering a reloaded capacity makes it invokable. F9 builds directly on this. See ADR-0156 §amendment-1.

---

## 1. Goal

(a) **Durable per-device Local persistence** — a device's Local Metagraph (learned skills + chosen durable state) survives a process restart.
(b) **Capacity re-activation contract** — descriptor-driven learned/bundle capacities become runnable again on reboot **without serializing Python callables**.

**Gate:** a per-device Local with a learned (descriptor-driven) capability is persisted → process restart → Local reloaded → capability runnable via `invoke` **without re-registering from code**; reset wipes run-state while retaining learned skills; D'1 retention round-trips; no cumulative-gate regression.

---

## 2. The load-bearing decision (resolves PB-1 + PB-3)

**The durable artifact is the L2 `learned-parameters` descriptor; the L3 capacity node + its `implementation` are per-process and re-minted at boot.**

This is grounded in the shipped model: capacities are per-process in-memory (`mindsos_server/skills/activation.py:1-10`), and a taught skill's durable footprint is already a Local `learned-parameters` node whose value dict holds `{capability, steps, requires_affordances, cache_key, source}` (`robot_demo/backend/transfer.py:141-158`). The capacity node's `to_properties()` is deliberately lossy — it drops `inputs`/`outputs` (those are PRODUCES/CONSUMES edges per ADR-0156) and the callable. So reconstruction must NOT go through `_CapacityBase.from_properties()`; it walks the descriptor and rebuilds via a factory.

### 2.1 Registration scope — taught caps register on the **Local** (contract requirement)

For re-activation to target the Local (§5), the taught capacity (node + `learned-parameters` descriptor) must live on the **Local** metagraph, not Global. This is `register_capacity(decl, session=<local-session>)` — a session-scoped registration targets the Local and skips the Global-write gate (`capacity_layer.py:315-319`); a Local can host capacity category-graphs via `ensure_category_graph`.

**Dependency:** the demo's current `teach_local` registers with `session=None` → **Global** (`transfer.py:168`). F9's contract requires Local registration, so **DM-8 must switch the demo's teach to `session=<local>`.** This is cleaner (per-device skill = Local cap + Local descriptor) and is the model F9 is designed around. Flag prominently in the DM-8 handoff.

---

## 3. Code-grounded findings (verify still current at implementation)

| Finding | Location | Consequence for F9 |
|---|---|---|
| `invoke` resolves via `_resolve_declaration`, which gates on **`_capacity_index` presence** AND reads impl from **`_declarations`** | `capacity_layer.py:649-669` | Both must be repopulated after a reload, not just `_declarations`. |
| `_capacity_index: Dict[mg_id, Dict[iri, (Node, Graph)]]`, populated **only** by `register_capacity` else-branch; lazily `{}` per Local | `capacity_layer.py:170,197,326,364-370` | After a metagraph load the index is empty → a **reindex** step is required before re-registration. |
| else-branch raises on `iri in category_graph.nodes` collision | `capacity_layer.py:359-363` | Without reindex, re-register after reload hits the collision raise, never reaching upsert. With reindex, `existing` is non-None → upsert branch (which now re-binds). |
| `FalkorDBLocalPersister.load/save/delete` exist but dormant (not in `__all__`); `delete` is a full Local teardown | `mindsos_server/persistence/local_persister.py:125-217` | Part (a) exports it + adds `load_or_mint_local`; `delete` is the hard-delete path, **not** the reset path. |
| Local roles | `mindsos_knowledge/identifiers.py:67-93` | `episodic_memories`, `capacity-state`, `parameter-staging`, `pending-promotions`, `learned-parameters`. |
| dict-valued node values round-trip via the value codec | ADR-0182, `mindsos_core/persistence/value_codec.py` | `learned-parameters` descriptors persist intact through `FalkorDBLocalPersister`. |

---

## 4. Part (a) — durable Local persistence

1. **Export `FalkorDBLocalPersister`** — add to `mindsos_server.persistence.__all__` (currently dormant). New public surface → version-surface touch.
2. **`load_or_mint_local(client, user_id)`** — mirror `robot_demo/backend/persistence.py::load_or_mint_global`: `find_by_name(local_knowledge:<user_id>)` → load + wrap, else mint a fresh Local. Lives in `mindsos_server` (NOT the demo). Returns the Local Metagraph (+ a `minted: bool`).
3. **Lazy load-on-first-access lifecycle** — a free function (per Phase 44 CR-3 / PB-38 precedent — not a `MindsOSServer` method) that, on first access to a given `user_id`'s Local, does `load_or_mint_local` + runs the part-(b) re-activation walk for that one Local. **No global boot scan** (matches the lazy `local_metagraph` model; enumerate-all-Locals is a v2 concern — see PB-D). F9 provides the durable backing store the ADR-0042 install/extract hooks will use; wiring it into actual login/logout stays deferred (Phase 44 CR-3).
4. **Key contract** — `FalkorDBLocalPersister` keys by `user_id` → `local_knowledge:<user_id>` (`_local_metagraph_name`). The demo keys by `device_id`; **pin `device_id == the user_id arg`** so names collide-match. The Phase-44 `CAN_*_OTHER_LOCAL` caps are cross-Local *reads* — orthogonal to own-Local persist.

---

## 5. Part (b) — capacity re-activation contract

**Mechanism (all in core; the demo registers a factory later):**

1. **`reactivation_key`** — a field on the `learned-parameters` descriptor (node value or a node property) naming which factory rebuilds the capacity. Absence / `"installer"` ⇒ not Local-re-activatable (re-run the installer instead; see §6).
2. **Factory registry** — new core module (e.g. `mindsos_capacity/reactivation.py`): `register_reactivation_factory(key, fn)` + `build_declaration(key, descriptor) -> _CapacityBase`. **Factory signature: `(descriptor: dict) -> _CapacityBase`** — it returns a fully-built `Capacity`/`Monitor`/`Adapter` with `implementation` bound. The factory owns ALL reconstruction (name, category, inputs, outputs, node_kind, impl), so F9 stays generic and never edge-walks or touches `to_properties`.

   **Descriptor must self-describe (PB-F).** The shipped `learned-parameters` value `{capability, steps, requires_affordances, cache_key, source}` has **no** `category`/`inputs`/`outputs`/`node_kind`, so a factory cannot rebuild the declaration generically from it today. Pick: **enrich the descriptor** to carry the full declaration spec (category, inputs, outputs, node_kind) so one generic factory suffices; the alternative is consumer-specific factories that hardcode the DataStates. Either way DM-8 writes the richer descriptor at teach time. See PB-F.
3. **`reindex_capacities(mg)`** — repopulate `_capacity_index[mg.metagraph_id]` from the loaded metagraph's category-graph capacity nodes (`node_type ∈ {NODE_TYPE_CAPACITY, MONITOR, ADAPTER}`). Required so the subsequent `register_capacity(..., if_exists="upsert")` reaches the upsert branch.
4. **Re-activation walk** — `reactivate_local_capacities(cl, kl, user_id)`:
   reindex the Local → walk `learned-parameters` nodes → for each, read `reactivation_key` + descriptor → `decl = build_declaration(key, descriptor)` → `cl.register_capacity(decl, session=<local-session>, if_exists="upsert")`. Persisted PRODUCES/CONSUMES edges are skipped as duplicates; the upsert-rebind fix binds `_declarations[iri]`.

**Callable non-serializability honored:** no `implementation` is ever pickled. Descriptor-driven caps (taught = `make_taught_impl(steps)`; bundle) rehydrate via factory; arbitrary code-bodied caps re-activate by re-running their installer (§6), not by deserialization.

---

## 6. Two re-activation paths — keep separate, share one primitive

Do **not** merge control flow. Bundle caps re-activate Global-side via the shipped `apply_installed_skills` (`mindsos_server/skills/activation.py:20`, ADR-0183) — admin-gated, Global, manifest-sourced. Taught caps re-activate Local-side via §5 — user-gated, Local, descriptor-sourced. They differ in scope/gate/descriptor source. Share only the low-level `register_capacity(upsert)` + (optionally) `reindex_capacities`; F9 does **not** subsume `apply_installed_skills`.

---

## 7. Reset boundary (resolves PB-3)

`FalkorDBLocalPersister.delete()` is the **hard-delete** path (full Local teardown — drops every graph AND the Metagraph node, `local_persister.py:170-217`) — NOT reset. Add a **role-scoped reset**: `reset_run_state(user_id)` that reuses only the **per-graph element `DETACH DELETE`** subset (`local_persister.py:184-191`) scoped to run-state graph_ids. It must NOT drop the Metagraph node or the durable role-graphs; leave the (now-empty) run-state graphs in place (or let lazy mint re-create) so the Local stays well-formed.

**Proposed split (my pick — confirm at impl, see PB-A):**
- **Wiped on reset (run-state):** `episodic_memories` (per-task/run history, run_id-scoped).
- **Retained (durable learning):** `learned-parameters`, `capacity-state`.
- **Open:** `parameter-staging` + `pending-promotions` (ALS in-flight buffers) — my pick: wipe (transient evidence/proposals), but flagged (PB-A).

---

## 8. ADR seeds (promote to numbers at implementation — confirm next free; `wsd-51` holds `0184`)

**ADR-F9-A — Capacity re-activation contract.** Descriptor-of-record = L2 `learned-parameters`; capacity node + impl per-process; `reactivation_key` + factory registry (`(descriptor)->_CapacityBase`); `reindex_capacities` + `reactivate_local_capacities`; explicit "no-descriptor ⇒ re-run installer, not deserialization" distinction; supersedes ADR-0156's "Locals re-registered each session" premise (Cost §, line 61).

**ADR-F9-B — Durable Local-persistence lifecycle.** Export `FalkorDBLocalPersister`; `load_or_mint_local`; lazy load-on-first-access free function; `device_id == user_id` key contract. **Amends ADR-0160** (persister was dormant/no-consumer). **Touches ADR-0042** — F9 provides the durable backing store its install/extract hooks will use; actual login/logout wiring stays deferred (Phase 44 CR-3), so this is a forward-reference, not a behavior change to the hooks.

**ADR-F9-C — Reset boundary.** Role-scoped `reset_run_state` vs hard `delete`; the run-state/durable role split (§7).

---

## 9. Test plan (the gate)

- **Round-trip across simulated restart:** persist a Local with a descriptor-driven learned capability → construct a **fresh CL/KL** (empty `_declarations`/`_capacity_index`, simulating a process restart) → `load_or_mint_local` + `reactivate_local_capacities` → `invoke` returns the live result **without re-registering from code**.
- **Reset semantics:** `reset_run_state` wipes `episodic_memories`, retains `learned-parameters` (capability still invokable after reset).
- **D'1 retention round-trip:** persist+reload a Local carrying retired versions; `kl.read_at_version` / `retire_version` resolve correctly; `_retired_inline_pending` survives (PB-B).
- **Negative:** a no-descriptor / code-bodied capacity is NOT silently "re-activated" from the Local walk (routes to installer path).
- **No cumulative-gate regression** (Linux: `docker compose -p mindsos-core --profile test run --rm mindsos-test pytest tests/`).

---

## 10. Open pushbacks (my picks; changeable in the impl chat)

- **PB-A (reset granularity):** wipe `parameter-staging`/`pending-promotions` on reset? **Pick: yes** (in-flight ALS state, not durable skill). Confirm against ALS owners.
- **PB-B (D'1 round-trip):** `read_at_version`/`retire_version` resolve after persist+reload? **Pick: low risk — markers are plain props (ADR-0177/0161); make it a test item, not a design blocker.**
- **PB-C (capacity-state durability):** is `capacity-state` durable or run-state? **Pick: durable** (per-user learned capacity snapshots).
- **PB-D (boot Local discovery):** how does boot enumerate which Locals to load? **Pick: load-on-demand at first access (lazy), not a global scan** — matches the lazy `local_metagraph` model; a scan is a v2 concern.
- **PB-E (ADR numbers / branch collision):** `wsd-51` is parked and holds `0184`. **Pick: confirm next free ADR number against `main` + parked branches at branch-open; do not hard-assign now.**
- **PB-F (descriptor richness):** the shipped `learned-parameters` descriptor lacks `category`/`inputs`/`outputs`/`node_kind`, so generic reconstruction is impossible without consumer-specific factories. **Pick: enrich the descriptor to self-describe** (carry the full declaration spec) so one generic factory rehydrates any taught cap; DM-8 writes the richer descriptor at teach time. Alternative: per-key consumer-specific factories (demo hardcodes its DataStates) — rejected as less generic. See §5.2.
- **PB-G (taught-cap registration scope):** F9 requires taught caps on the **Local** (§2.1); the demo currently registers Global (`session=None`). **Pick: F9 contract = Local registration; DM-8 switches the demo to `session=<local>`.** Hard dependency for the gate.

---

## 11. Scope boundaries (anti-collision)

- Core only: `mindsos_capacity`, `mindsos_server`, `mindsos_core` (if needed), `tests/`, `docs/`. Never `projects/robot_demo`.
- New public surface (persister export, `load_or_mint_local`, reactivation registry) ⇒ a **version-surface touch** — decide bump discipline for a non-phase `feat/` ship (likely `core_git_sha` + a public-surface note; `core_version` stays `phase50`).
- Honor the commit rules: explicit-path staging, never `-A`, never commit `*NEXT_CHAT_PROMPT*`.
- Coordinate with `wsd-51` (parked) — if it merges first, rebase F9 on the new `main` and re-gate.

---

## 12. Sequencing for the implementation chat

1. R0 probe: re-confirm §3 findings against `main` tip; confirm ADR numbers (PB-E).
2. Part (a): export + `load_or_mint_local` + boot lifecycle + key contract.
3. Part (b): `reactivation_key` + factory registry + `reindex_capacities` + `reactivate_local_capacities`.
4. Reset: `reset_run_state` + role split.
5. ADRs F9-A/B/C + amendments to 0160/0042.
6. Tests (§9) → Linux gate → squash-merge → STATE.json `core_git_sha` bump → write the DM-8 next-chat handoff (gitignored).

After F9 ships, **DM-8** (robot demo, `demo/robot`) consumes it: `persistence.py` calls `load_or_mint_local`; a boot loop re-teaches from persisted `learned-parameters` via a registered `"taught"` factory; `import_state`/Mode-B restores demo-state onto durable Locals.
