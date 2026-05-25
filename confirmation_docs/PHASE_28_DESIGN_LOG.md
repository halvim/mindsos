# Phase 28 Design Log — L3 CapacityLayer + bootstrap + capability gate + B-26b-T5 closure

**Phase:** 28
**Layer:** L3 (Intellectual Capacity) + carry-forward L0 fix per R2 PB-26
**Date:** 2026-05-24
**PHASE_MAP §28 (canonical scope):** L3 Global + Local bootstrap;
ensure-category-graph; CAN_WRITE_GLOBAL gate; CapacityLayer registry
with Local-wins lookup. **Carry-forward:** ADR-0118 §am5 Cypher
MERGE :IN_GRAPH closure (B-26b-T5 from Phase 26b).

## §1 Inheritance

* Phase 27 paperwork was open at design start (squash commit `5f1d0a4`
  on `phase-27` branch; not yet merged to main; no
  `PHASE_27_CONFIRMED.md`; no `phase-27-confirmed` tag). Phase 28
  design proceeded in parallel per R0 PB-0 (a); branch creation gates
  on Phase 27 squash-merge to main (R3 PB-34 (a)); confirm-phase
  gates on `phase-27-confirmed` tag (R5 PB-48 (a) — second gate).
* Phase 27 cumulative baseline = 2968 passed, 28 skipped (per design
  log §4 — 2967 + 1 B-27-T1 hotfix flip).
* B-26b-T5 §am3 orphan-Node Cypher carry-forward was originally
  deferred to "first FalkorDB L3 reader" (Phase 27 R0 PB-3 (a)). R5
  PB-49 probe confirmed zero blast radius outside Phase 26b's two
  helpers; R1 PB-19 (b) flipped the deferral and ships the 2-line
  Cypher patch + ADR-0118 §am5 at Phase 28.

## §2 Round-by-round picks (6 rounds: R0 + R1 + R2 + R3 + R4 + R5 pre-impl)

### R0 — 12 PBs

| PB | Topic | Pick |
|----|-------|------|
| PB-0 | Phase 27 paperwork open | (a) proceed in parallel; verify at branch |
| PB-1 | `CAN_WRITE_GLOBAL` string drift | (a) halvim UPPERCASE wins; ADR-0078 §am1 |
| PB-2 | SessionProtocol source for L3 | (a) slim `types.py`; parity test against L2 |
| PB-3 | CapacityLayer port scope | (a) slim — register + lookup + constraint + gate |
| PB-4 | views.py port scope | (b) accessors only; defer walks to Phase 29 |
| PB-5 | Test-port strategy | (a)/(c) verbatim port for bootstrap; NEW for rest |
| PB-6 | B-26b-T5 §am3 Cypher | (b) defer to Phase 32 — **FLIPPED at R1 PB-19** |
| PB-7 | Alignment-lookup as 13th category | (a) NO — retrieval capacity; close PHASE_15b PB-23 |
| PB-8 | `mindsos capacity` CLI | (a) zero CLI at Phase 28 — defer to Phase 30 |
| PB-9 | InvocationResult/call_capacity un-export discipline | (a) sentinel test |
| PB-10 | Step-0 sentinel-flip grep | (a) lock at R5 pre-impl probe |
| PB-11 | `add_constraint` Phase 28 vs Phase 29 | (a) API at 28; enforcement at 29 |
| PB-12 | ADR slate at ship | (a) lock 8-9 ADR touches; revisit R3 |

### R1 — 12 PBs (1 flip on R0)

| PB | Topic | Pick |
|----|-------|------|
| PB-13 | Slim types.py shape | (a) Protocol + SessionArg alias + runtime_checkable parity |
| PB-14 | Public method signature | (a) `session: Optional[SessionProtocol] = None` only |
| PB-15 | Test inventory lock | (b) 14 files / ~55 estimate (later ~107 post-parametrize) |
| PB-16 | schemas.py port scope | (a) full port (179 LOC; reserved edges shipped) |
| PB-17 | Sentinel-path granularity | (a) 6 new per-file entries |
| PB-18 | `__init__.py` re-export slate | (a) 14 names; SuccessorHop defers (later 15 per R2 PB-25) |
| PB-19 | **FLIPS R0 PB-6** — B-26b-T5 fix at Phase 28 | (b) 2-line Cypher patch + ADR-0118 §am5 |
| PB-20 | PHASE_MAP + carry-forward updates | (a) edit PHASE_MAP §28 + notes + ADR-0118 §am5 |
| PB-21 | Phase 28 docs slate | (b) amend overview; stub categories; defer building |
| PB-22 | ADR amendment sentinels | (a) ship test_adr_amendment_sentinels.py |
| PB-23 | `_capacity_index` per-Local invariant | (a) +2 assertions in test_capacity_layer_init.py |
| PB-24 | RESERVED_PROPERTY_KEYS rejection | (a) parametrized over all keys |

### R2 — 8 PBs

| PB | Topic | Pick |
|----|-------|------|
| PB-25 | ConstraintViolationError lift | (a) exceptions.py 3→4; __init__.py slate 14→15 |
| PB-26 | B-26b-T5 fix package boundary | (a) compound layer label "L3 + carry-forward L0 fix" |
| PB-27 | ADR-0118 §am5 wording lock | (a) explicit + scoped; preserves §am3/§am4 invariants |
| PB-28 | 13-step ship checklist ordering | (a) extend Phase 27's 11 to 13 |
| PB-29 | 12-site version bump verification | (a)+(b) lock list + Step-0 grep |
| PB-30 | __init__.py docstring update | (a) full rewrite |
| PB-31 | Import-isolation forbidden-target list | (c) 2 forbidden: server + knowledge |
| PB-32 | PHASE_MAP ADR cross-cite verification | (a) Step-0 verify at impl |

### R3 — 9 PBs

| PB | Topic | Pick |
|----|-------|------|
| PB-33 | `problem_trace` attribute drop | (a) drop entirely from __init__; sentinel test |
| PB-34 | Phase 27 closure gate | (a) gate phase-28 branch on squash-merge only |
| PB-35 | `_resolve_declaration` ship-or-drop | (a) ship per parent; test directly |
| PB-36 | `_declarations` global dict | (a) ship parent's single-dict; +1 sentinel test |
| PB-37 | test_capabilities_parity skip vs require | (a) drop importorskip; require server |
| PB-38 | test_invocation_not_exported assertion form | (a) two tests — __all__ + ImportError |
| PB-39 | SessionProtocol parity assertion form | (c) 3 assertions in 1 test |
| PB-40 | types.py separate vs inline | (a) separate file per parent layout |
| PB-41 | Cumulative target | (a) range lock; refine at impl Step 0 |

### R4 — 4 small PBs (near-saturation)

| PB | Topic | Pick |
|----|-------|------|
| PB-42 | RESERVED_PROPERTY_KEYS parametrize count | (a) auto-parametrize from frozenset (9 keys) |
| PB-43 | ConstraintViolationError hierarchy test | (a) +1 assertion `issubclass(...)` |
| PB-44 | ADR-0085 §Implementation wording | (a) add footer; ADR slate 8→9; sentinels parametrize over 9 |
| PB-45 | SuccessorHop dataclass drop with methods | (a) drop dataclass too; Phase 29 atomic re-introduction |

### R5 — pre-impl probe (4 PBs)

Probe confirmed: ✅ Zero `pytest.raises(ImportError|ModuleNotFoundError)`
referencing Phase 28 surface. ✅ Metagraph supports `.user_id` attribute
assignment. ✅ 9 ADR titles verified. ✅ §am5 zero blast radius outside
Phase 26b.

| PB | Topic | Pick |
|----|-------|------|
| PB-46 | §am5 stale-comment cleanup in Phase 26b test files | (a) +3 collateral edits |
| PB-47 | Phase 27 baseline reconcile | (a) range 3070-3080; reconcile from CONFIRMED.md |
| PB-48 | Phase 27 tag prerequisite for Phase 28 confirm-phase | (a) 2-gate ordering |
| PB-49 | Defensive Step-0 grep for §am5 side effects | (a) grep + inspect at impl Step 0 |

## §3 Locked ship state

* **Branch:** `phase-28` off `origin/main` (gated on Phase 27 squash-merge).
* **6 NEW source files** in `mindsos_capacity/`: `bootstrap.py`,
  `capabilities.py`, `capacity_layer.py`, `schemas.py`, `types.py`,
  `views.py`.
* **3 EDITED files** in `mindsos_capacity/`: `exceptions.py` (3→4
  classes), `__init__.py` (rewrite + 15 exports + version bump).
* **2 EDITED carry-forward files** per R2 PB-26: `mindsos_server/release.py`
  `_RELEASE_MERGE_CYPHER` + `mindsos_admin/promotion.py`
  `_PROPOSE_MERGE_CYPHER` (both add `:IN_GRAPH` MERGE).
* **2 EDITED test files** collateral per R5 PB-46:
  `tests/phase_26b/test_integration_a.py` + `_falkordb_assert.py`.
* **15 NEW test files** in `tests/phase_28/` totaling ~107 cases.
* **6 sentinel-paths additions**.
* **12-site version bump** `+phase27 → +phase28`.
* **9 ADR amendments** in parent tree (Model C; no parent .git).
* **Docs:** `overview.md` + `categories.md` (NEW) + `mkdocs.yml` nav.
* **PHASE_MAP §28** edited with compound layer label + Phase 15b PB-23 RESOLVED.

## §4 Impl-phase reconciliations (post-design)

* **R1 PB-15 (b) test count estimate ≈55 → ~107 actual** — parametrize
  expansion (9-key RESERVED_PROPERTY_KEYS + 12-case import-isolation
  matrix) inflated raw test count.
* **`__init__.py` export count: R1 PB-18 estimate 79 → 79 actual.**
* **Sandbox-runnable Phase 28 tests: 69/69 pass** locally (Python 3.10);
  7 server-importing tests collect-fail in sandbox due to `datetime.UTC`
  (Python 3.11+); will run green in docker.

## §5 Carry-forwards (to Phase 29+)

1. TYPE_COMPAT auto-discovery + 5-kind CONSTRAINT enforcement — Phase 29.
2. `SuccessorHop` dataclass + walks — Phase 29 atomic per R4 PB-45.
3. Pipeline finder + invocation + InvocationResult/call_capacity
   exports + problem_trace — Phase 30. Flips sentinel tests.
4. `mindsos capacity` CLI Typer group — Phase 30.
5. Residents + text builtins + pathfinding — Phase 31.
6. `docs/usage/capacity/building.md` content — Phase 29.
7. Write capacities + symmetric contract + per-flow validators — Phases 33-35.
8. `types.py` deprecation shim expansion — Phase 33 (if needed).
9. Additional-graph membership API per ADR-0085 — first consumer.
10. **B-26b-T5 — RESOLVED at Phase 28** via ADR-0118 §am5.

## §6 Hotfix ledger

None anticipated post-sandbox-green; any B-28-T* will be appended at
confirm-phase ship time per [[feedback-batch-fix-dont-iterate]].

## §7 Memory edits at ship

* NEW `[[project-mindsos-phase-28]]`.
* UPDATE `[[feedback-release-cypher-orphan-node]]` → RESOLVED Phase 28 §am5.
* UPDATE `[[project-mindsos-phase-27]]` carry-forwards (close #1+#2+#3).

Implementation log + ship checklist: `notes-phase-28.md`.
