# Phase 27 Design Log — L3 DataStates + capacity primitives (slim port)

**Phase:** 27
**Layer:** L3 (Intellectual Capacity) — first ship
**Date:** 2026-05-24
**PHASE_MAP §27 (canonical scope):** DataState define with shape; Capacity / Monitor / Adapter define; IRI form `capacity:<category>:<name>` enforced; ADRs 0062 / 0063 / 0066 / 0067.

## §1 Inheritance

* Phase 26b paperwork was open at design start (commit `30c8aec`, no tag, no `PHASE_26b_CONFIRMED.md`); closed in parallel during Phase 27 execution at `fec865b` + `phase-26b-confirmed` tag.
* `mindsos_capacity/` already exists at parent `/Layered Intelligence/mindsos_capacity/` (3081 LOC across 13 files) — Phase 27 is a SLIM PORT into halvim, not net-new design. PHASE_MAP §27 row "Net-new: No" matches.
* L3 design ADRs (0062 / 0063 / 0066 / 0067) all Accepted pre-design.
* ADR-0010 §am1/§am2 doesn't enumerate `mindsos_capacity → mindsos_knowledge` explicitly; parent precedent has L3 NOT importing L2 (intentional install-isolation).
* KL `REF_TYPES` has 7 members (added `PROMOTED` after ADR-0067 was written); parent L3 has 6 — drift surface for ADR-0067 amendment.

## §2 Round-by-round picks (saturated R0..R5; R4 zero-PB)

### R0 — 8 PBs

| PB | Topic | Pick |
|----|-------|------|
| PB-0 | Phase 26b paperwork open | (b) proceed Phase 27 design; 26b paperwork in parallel; correct memory drift |
| PB-1 | `mindsos_capacity/` in parent only | (a+c) slim-port 6 files; explicit skip-list for capacity_layer/bootstrap/discovery/runtime/schemas/views/capabilities/builtins |
| PB-2 | REF_TYPES strategy | (d) if ADR-0010 permits L3→L2 else (b) — verify at R1 |
| PB-3 | B-26b-T5 orphan-Node intersection | (a) defer to Phase 28 |
| PB-4 | IRI builder home | `mindsos_capacity/identifiers.py` |
| PB-5 | Site counts | front-load at R1 |
| PB-6 | CLI verbs | (a) zero CLI; Phase 28 owns `mindsos capacity` Typer group |
| PB-7 | `tests/_shared/` capacity fixture | not a PB |

### R1 — 10 PBs (some flip R0)

| PB | Topic | Pick |
|----|-------|------|
| PB-8 | REF_TYPES (R0 PB-2 resolution) | (b) duplicate + ADR-0067 §am1 — parent precedent + install isolation |
| PB-9 | Drop `types.py` | (a) drop entirely; Phase 33 ships it; kept-files = 5 |
| PB-10 | `test_registration.py` port | (a) NEW thin `test_capacity_dataclass.py`; 3 test files total |
| PB-11 | 7-pkg parity literal-decay | (a) retrofit literal — later flipped to (b) at R3 |
| PB-12 | Site counts | lock 12-site version bump + 8-site new-pkg checklist (later 9 per R3) |
| PB-13 | 12 categories ship at 27 | string constants ship at 27; Phase 28 owns registration |
| PB-14 | ADR delta | only ADR-0067 §am1 + ADR-0066 §Implementation footer (added R2) |
| PB-15 | `__init__.py` exports | full vocabulary + 5 dataclasses + 2 helpers; no registry/bootstrap/discovery |
| PB-16 | Confirm-phase timeout | 2700s, no change |
| PB-17 | Exception slim port | ship 3 (base + DataStateError + CapacityRegistrationError); defer 4 |

### R2 — 7 PBs

| PB | Topic | Pick |
|----|-------|------|
| PB-18 | `call_capacity` + `InvocationResult` extraction | (b) extract `invocation.py` — later flipped to (c) at R3 |
| PB-19 | `validate_for_registration` | ship at Phase 27 (pure validator over IRI set) |
| PB-20 | ADR-0066 collision-check defer | (a) §Implementation footer; Status stays Accepted |
| PB-21 | ADR-0067 §am1 wording | ship draft as written |
| PB-22 | Slim `__init__.py` exports | lock (~58 names estimated; actual 65 at impl) |
| PB-23 | `test_capacity_dataclass.py` inventory | lock 14 tests |
| PB-24 | notes-phase-27.md preamble | lock |

### R3 — 7 PBs (some flip R1/R2)

| PB | Topic | Pick |
|----|-------|------|
| PB-25 | Parity-test 6→7 retrofit (flips R1 PB-11) | (b) generalize via manifest `[mindsos] packages` — closes literal-decay class permanently |
| PB-26 | `call_capacity`/`InvocationResult` extraction (flips R2 PB-18) | (c) keep in `capacity.py`, don't export from `__init__.py` — saves future-phase import rewiring |
| PB-27 | ADR amendments live in parent | lock coordination — parent file edits first; halvim PR references IDs |
| PB-28 | data-states.md frontmatter | (a) halvim convention `last_confirmed_phase: 27` |
| PB-29 | Site count revision | lock 9-site new-pkg checklist + 12-site version bump |
| PB-30 | Memory drift cleanup | lock 3 memory edits at ship |
| PB-31 | tests_l3 handoff path note | light amendment; not a real PB |

### R4 — zero PBs (saturation)

Verified KL REF_TYPES = 7; L3 = 6; parity holds. Slim-port isolation test passed (kept files import cleanly with stdlib + intra-package only). No new PBs surfaced. Design saturated.

### R5 — pre-impl probe (7 PBs)

| PB | Topic | Pick |
|----|-------|------|
| PB-32 | data-states.md body line 53 broken cross-link | (a) strip at port |
| PB-33 | Manifest package-list shape | (a) `[mindsos] packages = [...]` (extends `[mindsos]` section) |
| PB-34 | doctor.py report field shape | (b) flat `runtime.versions = {pkg: ver}` (drop 6 individual `<pkg>_version` keys; grandfather `init_version`) |
| PB-35 | _read_package_init_version reuse | lock; ~25 LOC refactor |
| PB-36 | Branch + commit + ADR ordering | lock 11-step ordering + commit template |
| PB-37 | Confirm-phase timeout | lock 2700s; pre-build mandatory |
| PB-38 | Test reads manifest.toml | lock pattern — tomllib + direct read (no `_load_manifest` dep) |

## §3 Locked ship state

* **Branch:** `phase-27` off `origin/main` (Phase 26b confirmation sha `fec865b`).
* **5 source files** in `mindsos_capacity/`: `datastate.py` + `capacity.py` + `identifiers.py` + `exceptions.py` (3 classes) + `__init__.py` (65 exports).
* **3 test files** in `tests/phase_27/`: `test_datastate.py` (8 tests port) + `test_identifiers.py` (10 tests port) + `test_capacity_dataclass.py` (14 tests NEW).
* **Refactored:** `tests/phase_18/test_doctor_6pkg_parity.py` (manifest-driven; class renamed `TestAll6PkgsAtCurrentPhase` → `TestAllPackagesMatchManifest`).
* **9-site new-pkg checklist** (PB-29 lock).
* **12-site version bump** `+phase26b → +phase27` (PB-29 lock).
* **doctor.py refactor** — manifest-driven parity loop; `runtime.versions = {pkg: ver}` flat dict (PB-25/33/34/35).
* **Docs:** `docs/usage/capacity/data-states.md` (port + PB-28 frontmatter + PB-32 line-53 strip); `mkdocs.yml` nav add.
* **Parent ADR edits:** ADR-0066 §Implementation footer; ADR-0067 §amendment-1.

## §4 Impl-phase reconciliations (post-design)

* **R2 PB-22 estimate `~58 names` → 65 names actual.** Counted at `__init__.py` write time; the estimate undercounted (vocabulary + dataclass-internal exports). Functional outcome identical.
* **B-27-T1 hotfix.** `tests/phase_12/test_ref_types_and_roles.py::test_adr_0067_parity_test_deferred_to_phase_27` shipped at Phase 12 with `pytest.raises(ModuleNotFoundError)` sentinel asserting `mindsos_capacity` doesn't exist. Surfaced 1 docker-pytest failure at Phase 27 cumulative sweep (2967 passed + 1 failed in 30:47). Fix: flipped test name + assertion to verify ADR-0067 §am1 contract directly. New memory class: `[[feedback-parity-test-sentinel-flip-at-target-phase]]`.

## §5 Carry-forwards (to Phase 28+)

1. **B-26b-T5 §am3 orphan-Node Cypher** — Phase 28 first consumer of `MetagraphLoader.load(canonical_id)` on L3-released content; fix candidate is mechanical 2-line patch to `_RELEASE_MERGE_CYPHER` + `_PROPOSE_MERGE_CYPHER` adding `WITH n MATCH (g:Graph {id: $canonical_graph_id}) MERGE (n)-[:IN_GRAPH]->(g)`. See `[[feedback-release-cypher-orphan-node]]`.
2. **`CapacityLayer` + bootstrap + collision detection** — Phase 28 ships `mindsos_capacity/capacity_layer.py` + `bootstrap.py` + `capabilities.py`; ADR-0066 §Implementation footer (Phase 27) documents the collision-check belongs in `CapacityLayer.register` at Phase 28.
3. **12 categories registered as Core nodes** — Phase 28 owns `ensure_category_graph` + Global/Local bootstrap.
4. **TYPE_COMPAT auto-discovery + CONSTRAINT edges** — Phase 29.
5. **Pipeline finder + invocation + ProblemTraceRecord** — Phase 30. **Lifts `InvocationResult` + `call_capacity` exports** per PB-26 staging.
6. **Residents + text builtins** — Phase 31.
7. **Write capacities + `SessionProtocol`** — Phases 33–35.
8. **ADR-0067 §am2** if L3 acquires promotion-like lifecycle later.

## §6 Hotfix ledger

| ID | Class | Root cause | Fix |
|---|---|---|---|
| B-27-T1 | parity-test-sentinel-flip (`[[feedback-parity-test-sentinel-flip-at-target-phase]]`) | Phase 12 PB-3 shipped sentinel `pytest.raises(ModuleNotFoundError)` for `import mindsos_capacity`; Phase 27 introduced the package, breaking the sentinel | Renamed test `_deferred_to_phase_27` → `_landed_at_phase_27`; flipped assertion to verify ADR-0067 §amendment-1 contract directly |

## §7 Memory edits at ship

* `[[project-mindsos-phase-26b]]` — predictive-author drift resolved by user paperwork closure (no edit needed; matches git reality).
* `[[feedback-new-top-level-package]]` — 5/7 → 9 sites at Phase 27 (manifest packages list + mkdocs nav additions).
* `[[feedback-docker-compose-version-bump-site]]` — 10 → 12 sites at Phase 27.
* NEW `[[project-mindsos-phase-27]]`.
* NEW `[[feedback-parity-test-sentinel-flip-at-target-phase]]`.

Implementation log + ship checklist: `notes-phase-27.md`.
