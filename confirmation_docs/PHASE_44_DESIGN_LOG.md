# Phase 44 — Design Log (Rail C: L0 substrate)

**Status:** R0 design saturation — IN PROGRESS (round 1 draft).
**Branch:** `phase-44` (not yet cut; clean-tree prereq pending).
**Combined design + ship** under option C (2026-06-04): `L0_SUBSTRATE_CHAT` absorbed into R0.
**ADRs authored here:** ADR-0160 (persister impls + `MetagraphDump`), ADR-0161 (KL version surface), ADR-0011 §am-N, ADR-0004/0121 §clarification.

---

## §0 — Process discipline (inherited)

Per `HANDOFF.md §9` + `PHASE_43_DESIGN_LOG.md §10`: pair-execution (Cowork ↔ Mac ↔ Linux); 6-step confirm-phase; docker rebuild after each Mac push; R1 step-0 ADR transcription parity probe (N/A for the two NEW ADRs — authored, not transcribed); R1 step-2 buildability scan (see §2); saturation = three consecutive reversal-free rounds; follow-up budget 4-5.

**Governance rulings already locked (2026-06-04):** CR-2 ship both persisters; CR-3 `MindsOSServer` class refactor ships here; CR-4 retire-marker write here / episode-read consumer Phase 48.

---

## §1 — R0 saturation agenda

Each surface: **Q** (open question) · options · **Pick** · **Status** (`open` / `locked`).

### S1 — `MetagraphDump` serialization format (CR-1, ADR-0160)

**Q:** What backend-neutral dump shape round-trips through *both* Falkor-reconstruct and SQLite-blob?

- **A — JSON over the existing reconstruction schema.** Reuse whatever `MetagraphLoader` / Phase-11 reconstruction consumes; serialize to a versioned JSON envelope.
  Pros: one reconstruction path already tested. Cons: couples dump format to loader internals.
- **B — Dedicated `MetagraphDump` dataclass** mirroring structure (graphs/roles/nodes/edges/hyperedges/metaedges + identity + schema), serialized JSON v1 / msgpack v2, envelope `{dump_schema_version, payload}`.
  Pros: explicit boundary; forward-versionable; testable in isolation. Cons: net-new mapping to maintain alongside loader.
- **C — Falkor-native Cypher `CREATE` script** replayed for both backends.
  Pros: trivial for Falkor. Cons: couples SQLite path to Cypher; rejected.

**Pick:** **B**, JSON v1 in a versioned envelope. **Sub-Q resolved:** dump carries `(iri, version_int)` per node — *forced*, not a free choice: D'1 retention + `read_at_version` require version-pinned restore, so a HEAD-only dump would silently break side-by-side reads after a restore. **Status: locked.**

### S2 — Persister write semantics (ADR-0160, reuse ADR-0122)

**Q:** WAL graph or idempotent replace for `save()`?

**Pick:** Idempotent replace — Falkor = `delete_graph` + recreate; SQLite = `UPSERT` row. No WAL (single-Metagraph blob replace isn't a multi-graph op). `delete` best-effort, idempotent (ADR-0011). **Falkor delete-then-recreate is non-atomic** under single-process multi-threaded → guard `save`/`delete` with per-user `UserMutexRegistry` mutex (ADR-0006 precedent). **Status: locked** (pending round-2 confirm of mutex placement vs orchestrator hooks).

### S3 — SQLite-blob store shape (CR-2, ADR-0160 + ADR-0004/0121 clarification)

**Q:** Table shape + which DB file?

**Pick:** `local_dumps(user_id TEXT PRIMARY KEY, dump BLOB, dump_schema_version INT, updated_at TIMESTAMP)`. **DB file: separate `locals.db`**, not `server.db` — forced by ADR-0004's separation logic (`server.db` = auth/sessions/audit; mixing user-data blobs in breaks the concern split and the audit-backup story). ADR-0004/0121 §clarification: blob is opaque (not graph-relational) → no substrate-split violation. **Status: locked.**

### S4 — `MindsOSServer` class lifecycle (CR-3, ADR-0011 §am-N)

**Q:** Hook set + how module-level state migrates.

**Pick:** Class holds `_installed_locals` / `_install_lock` / `_mutex_registry` as instance attrs. Hooks: `on_login` (hydrate from persister), `on_logout` (flush), `on_promotion` (flush), `on_delete`. **Clean cut** (no free-function shims) — single-process, tests re-instantiate via fixture replacing `reset_state_for_tests()`. **Status: locked** — user ruling 2026-06-04: clean cut, **isolated in its own PR** (refactor + all `tests_server/` caller migration in one commit; no shims; no mid-PR broken states). Contains the §2 cascade risk to one reviewable PR.

### S5 — Retire-marker forward-contract (CR-4, ADR-0161/ADR-0153 §am-2)

**Q:** Where/how is the lazy-inline marker stored so the Phase 48 episode-read consumer can consult it?

- **A — node property on the retired version node** (`_retired_inline_pending: bool`).
- **B — separate marker graph** in the Metagraph.
- **C — row in `version_db`.**

**Pick:** **A** — co-located with versioned content, minimal, consulted at episode-read. **Lock the property name now** (Phase 48 depends on it). **Status: locked** (name `_retired_inline_pending`). **Round-2 finding:** single-underscore keys are NOT auto-reserved — only the `ov__` prefix is (`RESERVED_PROPERTY_PREFIXES`). ADR-0161 must register `_retired_inline_pending` in `RESERVED_PROPERTY_KEYS` (`mindsos_core/schema/validation.py`, currently `{_version, _state_version, _compositional}`) or schema validation rejects the marker write.

### S6 — KL version surface (ADR-0161, L2-41)

**Q:** Signatures + read target.

**Pick:** `kl.read_at_version(metagraph, role, version) -> Graph` reads Phase-11 side-by-side version graphs. `kl.retire_version(metagraph, role, version)` flips S5 marker + lazily releases HEAD-held content. Distinct from `kl.deprecate_version()` (deprecated stays readable; only retire releases). **Status: locked.**

### S7 — Kahn topological-sort scheduler (L2-37 consumer)

**Q:** Tie-break + error shape.

**Pick:** Consume `_APPLIES_AFTER_BY_ROLE`; **stable tie-break by role-name** for reproducible bootstrap order; soft edge `episodic_memories ← {task-patterns}`; cycle → `BootstrapCycleError` naming the cycle; missing decl → `frozenset()`. **Status: locked.**

### S8 — Audit constant + capability (L2-39)

**Pick:** Additive. `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` in `mindsos_server/audit.py`. **Round-2 correction:** capability roster lives in `mindsos_server/capabilities.py` (NOT `auth.py`); existing symbol is `CAN_READ_OTHER_LOCALS`, so the new constant is **`CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY`** (follow the `CAN_` convention), distinct from `CAN_READ_OTHER_LOCALS`. Add to `ADMIN_CAPS` (9 → 10 — confirmed against the frozenset; the line-27 "seven" docstring is stale) **and** the `ALL_CAPABILITIES` tuple (append at declaration-order end). Default-deny + admin opt-in. **Status: locked.**

---

## §2 — Buildability scan (R1 step 2 — pre-PR-ordering)

Exactly-N sentinels + fixture-keyed tests at risk across PR boundaries:

- **Role-count sentinel (12 roles)** — Kahn scheduler must not change role *count*, only order. Verify no test asserts iteration order pre-scheduler.
- **Capability roster 9 → 10** — the Phase 18 `test_capabilities_parity` sentinel + any `len(ADMIN_CAPS)` / `len(ALL_CAPABILITIES)` assertion must flip in the *same* PR as the `capabilities.py` add (new constant + `ADMIN_CAPS` + `ALL_CAPABILITIES` tuple — all three together).
- **`test_adr_amendment_sentinels.py`** anchors ADR-0160 + ADR-0161 — both ADR files must land *before or with* the sentinel test (Rail C chain root from Phase 38).
- **`MindsOSServer` clean cut (S4)** — every `tests_server/` caller of the free functions flips in the refactor PR; mid-PR intermediate state breaks the layer-isolation + orchestrator tests. **Highest cascade risk** → isolate in its own PR or its own commit with the test migration.

---

## §3 — Saturation status

**Round 1 + round-2 review: design saturated; corrections applied.** All surfaces S1–S8 locked. The round-2 reversal pass changed no pick but corrected three module/name facts against the code: capability roster module (`capabilities.py`, not `auth.py`) + cap name (`CAN_` convention) in S8; S5 reserved-key registration requirement; ADMIN_CAPS count confirmed 9 → 10. Reversal-free-round counter: 1/3 (no reversals this round).

**Next:** §4 PR ordering → R1 buildability re-scan → impl. No design-level item remains open.

---

## §4 — PR ordering (R1 draft)

§2-driven: isolate the highest-cascade change (S4 orchestrator cut); land each ADR with its sentinel; never split a sentinel from its code. Tester serializes; cumulative gate after each PR.

**PR1 — substrate + ADRs:**
- ADR-0160 + ADR-0161 + ADR-0011 §am-N + ADR-0004/0121 §clarification (on disk).
- `MetagraphDump` dataclass + backend-neutral serialize/reconstruct, version-pinned `(iri, version_int)` (S1).
- `FalkorDBLocalPersister` + `SQLiteLocalPersister` + `locals.db` (S2, S3); per-user mutex guard.
- `_retired_inline_pending` registered in `RESERVED_PROPERTY_KEYS` (S5).
- `tests/phase_44/test_adr_amendment_sentinels.py` (anchors both ADRs — same PR) + persister/dump round-trip tests.

**PR2 — orchestrator clean cut (ISOLATED, S4):**
- `mindsos_server/orchestrator.py` free-functions → `MindsOSServer` class + 4 hooks.
- All `tests_server/` caller migration in this PR (one commit, no shims).
- Wires PR1 persisters into `on_login` / `on_logout` / `on_promotion` / `on_delete`.

**PR3 — KL surface + bootstrap + scheduler + audit/cap:**
- `kl.read_at_version` + `kl.retire_version` (S6) + marker write.
- Falkor-backed L3 bootstrap + state-file serialization (PHASE_38 §4 #2).
- Kahn scheduler (S7).
- `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` + `CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY` + `ALL_CAPABILITIES` (S8) — Phase 18 parity sentinel flips here.
- Per-user `ProblemTraceSink` dict (PHASE_38 §4 #6) + `validate_local_to_global_ref` consumer (L2-10).

**PR-1 pre-flight checklist:** clean working tree (commit the 4 modified docs first); `phase-44` branches off the `phase-43-confirmed` descendant; docker baseline rebuild green.

**Open R1 task (not design-level):** locate the exact `test_capabilities_parity` assertion + any `len(view.roles())`/role-count sentinels the scheduler PR touches, confirm none assert *iteration order* pre-scheduler.

---

## §5 — PR1.2 investigation reversal (2026-06-04): S1 → Opt-3a

R0 locked S1 as "dedicated `MetagraphDump` dataclass, not loader reuse." PR1.2 grounding reversed it. Findings:

- The project's **authoritative** Metagraph↔JSON serializer already exists and lives in `mindsos_cli` (`_graph_to_state`/`_state_to_graph` in `commands/graph.py`; `_metagraph_to_state`/`_state_to_metagraph` in `commands/metagraph.py`; migrations in `mindsos_cli/migrations/`, graph at v=5). FalkorDB is a *projection* of these JSON state files (`mindsos_core/persistence/__init__`: "JSON state files … remain authoritative"). No core-resident element serializers exist.
- `mindsos_server` imports nothing from `mindsos_cli` (ADR-0010 layering). So reuse requires promoting the serializer down to `mindsos_core`.
- The **Falkor persister needs no JSON at all** — it round-trips natively via core `MetagraphRepository.persist` + `MetagraphLoader.load` (server-safe). Only the SQLite persister serializes.

**Ruling (user, 2026-06-04): Opt-3a.**

- **S1 reversed:** no net-new dataclass. The SQLite persister reuses the state-file serializer **promoted from `mindsos_cli` → `mindsos_core`** (CLI keeps thin re-exports). `MetagraphDump` = `{dump_schema_version, payload}` envelope over the authoritative state-file JSON; SQLite-internal only.
- **S2/S3 refined:** Falkor persister = native `persist`/`load` (no dump); SQLite persister = serialize-via-promoted-core → blob in `locals.db`.
- **Protocol unchanged:** `LocalPersister` keeps the `Metagraph` shape (ADR-0011 §am-2). **Reverts ADR-0011 §am-3 clause 1** (which had switched the Protocol to `MetagraphDump`).
- **ADR-0160 reframed:** Falkor native; `MetagraphDump` SQLite-internal, not backend-neutral; net-new-dataclass moved to §Alternatives as rejected.

**PR1.2 scope delta:** adds the serializer promotion (move 4 functions `mindsos_cli` → `mindsos_core` + CLI re-exports + CLI test-import updates). Follow-up budget unchanged (4-5) — the promote replaces, not adds to, the net-new serializer that S1 would have required.

> **Superseded same day by §6 — see below.** The Opt-3a ruling above held only until the serializer's disk-coupling surfaced; CR-2 was then reversed to Falkor-only v1.

---

## §6 — CR-2 reversal (2026-06-04): Falkor-only v1; SQLite + MetagraphDump deferred

Opt-3a (§5) assumed the serializer promotion was a clean "move 4 functions." Reading `_state_to_metagraph` / `_state_to_graph` showed it is **disk-coupled and multi-file**: a Metagraph reconstructs by loading each contained graph (`state_mod.load_graph_state(gname)`) and schema (`_load_schema_or_die`, with `typer.Exit`) from its own on-disk state file. Reusing it for a single self-contained SQLite blob requires dependency-injecting those disk resolvers + a composite inline envelope — a real refactor that also touches the CLI's working reconstruct path.

Combined with the fact that `SQLiteLocalPersister` has **no named v1 consumer**, this fails "ship only what has a live consumer."

**Ruling (user, 2026-06-04): Falkor-only v1.**

- **Ships:** `FalkorDBLocalPersister` — native round-trip via `MetagraphRepository.persist` + `MetagraphLoader.load`; per-user mutex on write; best-effort `delete -> bool`. No serialization.
- **Protocol:** keeps `Metagraph` (ADR-0011 §am-2, §am-3 cl.1).
- **Deferred bundle** (to the first local-first / portable-export consumer phase): `SQLiteLocalPersister`, `MetagraphDump`, `locals.db`, and the `mindsos_cli`→`mindsos_core` serializer promotion (with DI'd graph/schema resolvers). Tracked here.
- **Reverses CR-2** (was "ship both") and supersedes §5 Opt-3a. **S1 + S3 → deferred** (no dump format / no SQLite store ships now). **S2 → Falkor-native** (no dump on the Falkor path either).
- **ADR impact:** ADR-0160 rewritten to Falkor-only + deferral; ADR-0011 §am-3 cl.2 → Falkor ships / SQLite defers; ADR-0004 §am-2 removed (no SQLite-blob store ships, so no amendment needed). ADR-0161 unaffected.

**Revised §4 PR ordering:** PR1.2 shrinks to the Falkor-native persister + tests (no serializer promotion, no SQLite, no `locals.db`). PR2 (MindsOSServer class + hooks, CR-3) and PR3 (KL surface + scheduler + audit/cap) unchanged.

---

## §7 — PR1.2 implementation notes (FalkorDBLocalPersister)

**Substrate contract settled (was L0_SUBSTRATE_CHAT scope).** `mindsos_server/persistence/bootstrap.py` + `mindsos_core/persistence/bootstrap.py` confirm all Metagraphs — Global + pending + canonical + **every user Local** — coexist in the *one shared* FalkorDB graph (`config.graph`), scoped by `metagraph_id`/name. A user's Local is the Metagraph `local_knowledge:<user_id>` (`knowledge_layer._local_metagraph_name`). This invalidates ADR-0011's "drop the per-Local graph / `MATCH (n) DETACH DELETE n`" delete framing — there is no per-Local FalkorDB graph, and a blanket delete would destroy the co-resident Global + other Locals.

**Impl (`mindsos_server/persistence/local_persister.py`):**

- `save` → `MetagraphRepository(client).persist(metagraph)` under the per-user mutex; `PersistenceError` → `FlushFailedError`.
- `load` → `MetagraphLoader.find_by_name(local_knowledge:<user_id>)` → `load(metagraph_id)`; missing → `None`.
- `delete` → scoped multi-statement `DETACH DELETE` keyed on `metagraph_id` (elements via `IN_GRAPH`, tombstones by `graph_id`, source XRefs, anchor-attached satellites `(m)--(sat) WHERE NOT sat:Graph`, contained graphs via `IN_METAGRAPH`, then the anchor); missing → `False`; under the per-user mutex.
- Mutex injected (shared `UserMutexRegistry` passed by the orchestrator at PR2; defaults to a fresh one).

**Verification gap (known):** the Cowork sandbox has Python 3.10 and no FalkorDB; the project needs 3.12. Unit tests (`test_falkor_persister.py`, `InMemoryClient`) cover Protocol satisfaction + missing-key semantics + persist delegation + `FlushFailedError`; they do **not** exercise a real round-trip or the scoped-delete Cypher. **The save→load round-trip + delete statement set are validated only on the Linux docker gate.** Expected follow-up surface: metaedge / metahyperedge / XRef delete-coverage completeness (the anchor-satellite sweep is a best-effort first cut) — budget 1-2 gate-driven follow-ups within the 4-5 allowance.

**Gate-driven follow-up (PR1.2a — import-cycle warm-up).** First gate of `tests/phase_44/` in isolation surfaced a **pre-existing** circular import: `mindsos_server/__init__` → `admin` → `persistence` → `mindsos_admin` → `promotion` → `mindsos_server.admin.admin_tx` (`admin_tx` defined after `admin.py:80`'s persistence import). `git diff main` over all cycle modules is empty — identical to Phase 43; the cumulative suite masks it because the server-phase conftests (phase_24 does `from mindsos_admin import …`) warm `mindsos_admin` first. `tests/phase_44/` had no conftest, so cold isolated collection bit. Fix: `tests/phase_44/conftest.py` does `importlib.import_module("mindsos_admin")` before the test modules import `mindsos_server` (mirrors the server-phase warm-up; lets `admin.py` complete `admin_tx` before `promotion` needs it). Not a Phase 44 product change — a test-isolation warm-up only.

---

## §8 — PR1 ship state (2026-06-04)

**PR1 complete + validated.** `origin/phase-44` carries: R0 (`985ca72`) → PR1.1 ADRs (`c9a7960`) → PR1.1b Opt-3a reframe (`cf51cac`) → PR1.1c CR-2 Falkor-only (`db92bdd`) → PR1.2 `FalkorDBLocalPersister` (`54747ab`) → PR1.2a conftest warm-up.

**Cumulative gate (Linux docker, full `pytest tests/`):** **3619 passed, 8 skipped (integration — no live FalkorDB sidecar), 0 failed**, ~32 min. Baseline + 11 new `phase_44` tests (6 ADR sentinels + 5 persister units).

**Shipped:** ADR-0160 (Falkor-only persister + shared-graph substrate/delete contract) + ADR-0161 (KL version surface, not yet consumed — Phase 48) + ADR-0011 §am-3 + `FalkorDBLocalPersister` (native persist/load + scoped `metagraph_id` delete + per-user mutex).

**Known follow-ups carried forward (within 4-5 budget):** (1) live FalkorDB save→load round-trip + scoped-delete integration test (unit tests use `InMemoryClient` only); (2) metaedge/metahyperedge/XRef delete-coverage completeness.

**Next: PR2 — `MindsOSServer` class refactor (CR-3).** Highest-cascade-risk unit (§2). Resume by grounding `mindsos_server/orchestrator.py`'s free-function surface (`_installed_locals` / `_install_lock` / `_mutex_registry`) + the full `tests_server/` caller list before touching code; clean cut, all callers migrate in one commit, wire the Falkor persister into the 4 lifecycle hooks. Then PR3 (KL surface + Kahn scheduler + audit constant/capability).

> **Superseded by §9 — CR-3 deferred.** PR2 grounding reversed CR-3; PR2 is dropped. Next is PR3.

---

## §9 — CR-3 reversal (2026-06-04): defer the MindsOSServer class refactor

PR2 grounding over `mindsos_server/orchestrator.py` + its caller set reversed CR-3 ("do the class refactor now"). Findings:

- **The live surface is tiny.** The orchestrator's install machinery has one production consumer: `read_other_local` (ctx mgr), called only by `admin.read_other_local_summary` (→ CLI `server.py`) + 5 tests (phase_25 ×4, phase_26b ×1). Module state: `_installed_locals` / `_install_lock` / `_mutex_registry`.
- **The class's four justifications eroded.** ADR-0011 §am-2 cl.4 named the class as landing "alongside SQLite + Falkor persisters + on-login hydration + on-logout flush." Post-grounding: (1) SQLite deferred (CR-2); (2) Falkor shipped but consumed fine by the free-function `read_other_local`; (3)+(4) login/logout don't touch Locals at v1 — `sessions.py` `login`/`logout` carry `persister`/`kl` kwargs but never call them (PB-37 collapse), and nothing writes a user's Local until L4/L5, so the hooks have **no live consumer** (flush would persist empty Locals).
- Building the class + hooks now is exactly the consumer-less forward-shape the **CR-2 reversal** rejected.

**Ruling (user, 2026-06-04): defer CR-3.** The orchestrator stays free-function per PB-38. The `MindsOSServer` class + lifecycle hooks land at the L4/L5 phase that first writes user Locals (Phase 46+). **Reverses CR-3**; PR2 is dropped.

**ADR impact:** ADR-0011 §am-3 header + clauses 3/4 reverted to "class + hooks defer" (cl.1 Protocol-Metagraph + cl.2 Falkor-ships unchanged). No `orchestrator.py` change. No `tests_server/` migration.

**Revised phase shape:** PR1 (shipped, gated green) → ~~PR2~~ (dropped) → **PR3** (KL `read_at_version`/`retire_version` + `_retired_inline_pending` marker + Kahn scheduler + `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` + `CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY` + `validate_local_to_global_ref`). PR3 is now the remaining implementation work for the phase.

---

## §10 — PR3 scope + ship (2026-06-04)

**PR3 scope ruling (user):** ship **S7 + S8**; defer **S6 + L2-10**. Grounding (consumer scan): S7 resolves a shipped-but-unconsumed Phase-43 field (real); S8 is a mandated additive roster add (L2-39); S6 (`read_at_version`/`retire_version`) has zero consumers (Phase 48 / D'1) and ADR-0161 already froze the only load-bearing artifact (the marker name); L2-10's validator exists but no v1 flow writes Local→Global refs. Same consumer-discipline as CR-2/CR-3.

**S8 — audit constant + capability (additive, no v1 emit-site).** `CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY` added to `capabilities.py` (`ADMIN_CAPS` + `ALL_CAPABILITIES`, 9→10) + `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` in `audit.py`. Phase 18 `test_capabilities_parity` flipped 9→10 (`test_ten_capabilities` + set) in the same change. No KL-side capability mirror exists. `tests/phase_44/test_episodic_capability_audit.py` asserts roster shape + distinctness + default-deny.

**S7 — Kahn scheduler (consume the Phase-43 field; zero behavioral change).** `kahn_sort(roles, applies_after)` in `mindsos_knowledge/bootstrap.py` + `BootstrapCycleError` (`exceptions.py`). Wired into `KnowledgeLayer.bootstrap()`'s three walk sites (1 Global + 2 Local), replacing `sorted(...)`. **Key finding:** `_LOCAL_NAMED_ROLES = {episodic_memories, capacity-state}` and `task-patterns` is Global — so the one edge (`episodic_memories ← task-patterns`) is **cross-scope** and is filtered out by `kahn_sort`'s in-scope intersection. Every single-scope sort therefore reduces to alphabetical = the exact pre-Phase-44 `sorted()` order → **no behavioral change, no order-sensitive test risk**. The scheduler's value is consuming the dead field + cycle-detection for future within-scope edges. `tests/phase_44/test_kahn_scheduler.py` covers edge-respect, alphabetical tie-break, cross-scope filtering, missing-decl, cycle-raise, and real-declaration-reduces-to-alphabetical. Logic verified standalone (sandbox is Py3.10).

**Deferred to consumer phases:** S6 (KL retention API → Phase 48 / L3-L4; marker name already frozen in ADR-0161) + L2-10 (`validate_local_to_global_ref` wiring → first v1 Local→Global ref-write flow).

---

## §11 — Implementation complete; ship ceremony pending (checkpoint 2026-06-04)

**Phase 44 implementation done + twice-gated-green.** `origin/phase-44` carries R0 → PR1.1/1.1b/1.1c → PR1.2/1.2a (Falkor persister) → §8 ship note → CR-3-reversal → PR3 (S7+S8). Two cumulative gates: PR1 = 3619/8/0; PR3 = **3630/8/0** (3619 + 11 phase_44 tests). Zero failures both times.

**What actually shipped (vs original Phase 44 plan):**

| Item | Status |
|---|---|
| `FalkorDBLocalPersister` (native; scoped delete) | **shipped** (PR1) |
| Kahn scheduler (`kahn_sort` + `BootstrapCycleError`; consumes Phase-43 field) | **shipped** (PR3 / S7) |
| `CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY` + `EVT_READ_OTHER_LOCAL_EPISODIC_MEMORY` | **shipped** (PR3 / S8) |
| ADRs 0160 (Falkor-only) + 0161 (KL surface) + 0011 §am-3 | **shipped** (PR1) |
| SQLite persister + `MetagraphDump` + serializer promotion | **deferred** (CR-2 → first local-first consumer) |
| `MindsOSServer` class + lifecycle hooks | **deferred** (CR-3 → L4/L5 Local-write phase) |
| `read_at_version` / `retire_version` impl (S6) | **deferred** (→ Phase 48 / L3-L4; ADR-0161 froze the marker name) |
| `validate_local_to_global_ref` wiring (L2-10) | **deferred** (→ first Local→Global ref-write flow) |

**Remaining = ship ceremony only (no code):**

1. **Land `phase-44` → `main`** (FF, per Phase 43 precedent; `main` is at `eb328c2`).
2. **6-step confirm-phase** (HANDOFF §9): `mindsos confirm-phase --init-notes 44` (Mac) → tester notes body → tester edits on Linux → `mindsos confirm-phase --phase 44 --notes-file notes-phase-44.md` from post-FF `main` (Linux) → commit `PHASE_44_CONFIRMED.md` + notes + push → Mac tags `phase-44-confirmed`.
3. **Closure docs** (mirror Phase 43's docs-landing): HANDOFF §3.1 Phase 44 ship block + §1 timestamp; CLAUDE.md status flip to "Phase 44 SHIPPED"; POST_PHASE_38_PHASE_MAP §4 Phase 44 row → SHIPPED with as-shipped scope (note the CR-2/CR-3/S6/L2-10 deferrals); L2_FUTURE_WORK / L0_FUTURE_WORK status updates for the deferred items' new owner phases.

**Resume pointer:** start at ceremony step 1 (FF landing). The tester-notes body should state the as-shipped scope (PR1 persister + PR3 scheduler + cap/audit) and enumerate the four deferrals with their consumer-phase rationale (this §11 table is the source). Carry-forward follow-ups for whoever owns the deferred items: the live-FalkorDB persister round-trip + scoped-delete integration test (§7), and metaedge/XRef delete coverage.

---

## §12 — Carry-forward: pre-existing import cycle (maintenance fix)

**Not a Phase 44 bug — pre-existing and identical on `main` before Phase 44** (`git diff main` over every cycle module is empty). Surfaced twice during Phase 44 isolated test runs.

**Cycle:** `mindsos_server/__init__.py` → `from mindsos_server.admin import …` → `admin.py:80 from mindsos_server.persistence import LocalPersister` → `persistence/__init__.py:19 from .bootstrap import …` → `persistence/bootstrap.py:37 from mindsos_admin.bootstrap import …` → `mindsos_admin/__init__.py:116 from .promotion import …` → `promotion.py:68 from mindsos_server.admin import admin_tx`. At that point `mindsos_server.admin` is partially initialized (paused at line 80, before `admin_tx` is defined ~line 576) → `ImportError: cannot import name 'admin_tx'`.

**Why masked:** the full cumulative suite collects earlier server-phase conftests (e.g. phase_24 `from mindsos_admin import …`) that warm `mindsos_admin` first, so by the time any cold `mindsos_server` import runs, `admin_tx` is already cached. It bites only on isolated subsets that import `mindsos_server` cold first (`pytest tests/phase_44/`, `pytest tests/phase_18 …`).

**Band-aid in place:** `tests/phase_44/conftest.py` does `importlib.import_module("mindsos_admin")` to warm the order for isolated `phase_44` collection.

**Proper fix (maintenance, post-Phase-44):** apply the codebase's own lazy-import-to-break-cycle pattern (precedent: `mindsos_core/persistence/client.py:140` — "Late import to break the persistence.bootstrap ↔ persistence.client cycle"). Make `mindsos_admin/promotion.py:68 from mindsos_server.admin import admin_tx` a **lazy import inside the function(s) that call `admin_tx`** (first verify `admin_tx` is used only in function bodies, not at module top-level). That breaks the back-edge: when `mindsos_admin` imports `promotion`, `promotion` no longer needs `admin_tx` immediately, so `admin.py` finishes initializing and defines `admin_tx` before any call site runs. Then **remove `tests/phase_44/conftest.py`** (band-aid no longer needed) and re-run the full cumulative gate. ~1-3 line change; behavior-preserving.

**Owner:** MAINTENANCE_CHAT (or next maintenance window). Tracked as L0-24 in `docs/_workbench/L0_FUTURE_WORK.md`.
