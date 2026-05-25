# Phase 28 — L3 CapacityLayer + bootstrap + capability gate + B-26b-T5 closure

## §1 Scope (PHASE_MAP §28)

**Second L3 ship.** Adds 6 new source files to existing `mindsos_capacity/`
package (no new top-level pkg; 9-site checklist N/A). Closes the
B-26b-T5 §am3 orphan-Node Cypher gap as a carry-forward L0 fix
(compound layer label per R2 PB-26).

**Source files NEW (6):** `bootstrap.py`, `capabilities.py`,
`capacity_layer.py`, `types.py`, `schemas.py`, `views.py`.

**Source files EDITED:** `exceptions.py` (3→4 classes adds
`ConstraintViolationError`); `__init__.py` (docstring rewrite + 15 new
exports → 79 total + version bump).

**Carry-forward edits:** `mindsos_server/release.py` `_RELEASE_MERGE_CYPHER`
+ `mindsos_admin/promotion.py` `_PROPOSE_MERGE_CYPHER` (both add
`:IN_GRAPH` MERGE per ADR-0118 §am5); `tests/phase_26b/test_integration_a.py`
+ `_falkordb_assert.py` stale-comment cleanup per R5 PB-46.

**Test files NEW (14 + 1 helper + 1 `__init__.py`):**
`test_capacity_bootstrap.py`, `test_capacity_layer_init.py`,
`test_capacity_layer_register_datastate.py`,
`test_capacity_layer_register_capacity.py`,
`test_capacity_layer_local_wins.py`, `test_capability_gate.py`,
`test_capabilities_parity.py`, `test_session_protocol_satisfied.py`,
`test_views_accessors.py`, `test_constraints.py`, `test_schemas.py`,
`test_invocation_not_exported.py`, `test_import_isolation_phase_28.py`,
`test_adr_amendment_sentinels.py`, `test_release_cypher_in_graph_link.py`,
`_fixtures.py`, `__init__.py`. **Total: ~107 cases** (parametrize
expansion: 9-key reserved + 12-case import-isolation matrix).

**Cumulative target:** Phase 27 baseline 2968 + ~107 ≈ **3075 passed,
28 skipped**. Reconcile from `PHASE_27_CONFIRMED.md` at impl Step 0.

**Docs (3):** `docs/usage/capacity/overview.md` (NEW); `categories.md`
(NEW stub); `mkdocs.yml` Capacity nav `(Phase 27, 28)`. `building.md`
deferred to Phase 29 per R2 PB-21 (b).

## §2 Design rounds summary

Six rounds (R0 + R1 + R2 + R3 + R4 + R5 pre-impl probe). See
`confirmation_docs/PHASE_28_DESIGN_LOG.md` for the full pick ledger.

**Locked picks shaping ship (47 picks across R0..R5):**

* R0 PB-1 + ADR-0078 §am1 — halvim UPPERCASE wins.
* R0 PB-3 — slim CapacityLayer.
* R1 PB-14 — `session: Optional[SessionProtocol] = None` only.
* R1 PB-19 (flipped R0 PB-6) — B-26b-T5 fix ships at Phase 28.
* R3 PB-37 — `test_capabilities_parity.py` drops `importorskip`.
* R5 PB-49 — Step-0 grep confirmed zero §am5 blast radius outside Phase 26b.

## §3 ADR amendments (parent — no .git per Model C)

9 ADR touches: 0040 §am2, 0061 §Impl, 0064 §Impl, 0065 §Impl (+ Phase
15b PB-23 closure), 0066 §Impl edit (ships→shipped), 0078 §am1, 0080
§Impl, 0085 §Impl, 0118 §am5.

## §4 Sentinel-paths additions (6 entries)

`mindsos_capacity/{bootstrap,capabilities,capacity_layer,schemas,types,views}.py`.

## §5 12-site version bump `+phase27 → +phase28`

| # | Site | Status |
|---|------|--------|
| 1 | `pyproject.toml` `[project] version` + `description` rewrite | ✅ |
| 2 | `mindsos_cli/manifest.toml` `[mindsos] phase` | ✅ |
| 3 | `mindsos_cli/manifest.toml` `[mindsos] version` | ✅ |
| 4 | `docker-compose.yml` `mindsos:phase28-prod` | ✅ |
| 5 | `docker-compose.yml` `mindsos:phase28-test` | ✅ |
| 6 | `mindsos_cli/__init__.py` `__version__` | ✅ |
| 7 | `mindsos_core/__init__.py` `__version__` | ✅ |
| 8 | `mindsos_instances/__init__.py` `__version__` | ✅ |
| 9 | `mindsos_knowledge/__init__.py` `__version__` | ✅ |
| 10 | `mindsos_admin/__init__.py` `__version__` | ✅ |
| 11 | `mindsos_server/__init__.py` `__version__` | ✅ |
| 12 | `mindsos_capacity/__init__.py` `__version__` | ✅ |

## §6 Memory edits at ship

1. NEW `project_mindsos_phase_28.md`.
2. UPDATE `feedback_release_cypher_orphan_node.md` → RESOLVED Phase 28 §am5.
3. UPDATE `project_mindsos_phase_27.md` carry-forwards (close #1+#2+#3).

## §7 Ship checklist (13-step ordering per R2 PB-28)

* [x] **[Sandbox]** Edit 9 parent ADRs (no git; Model C).
* [ ] **[Mac]** Verify parent ADR diffs visually.
* [ ] **[Mac]** `git checkout -b phase-28 origin/main` — **GATED ON
      Phase 27 squash-merge to main** (R5 PB-48 (a) gate 1).
* [x] **[Sandbox]** Halvim source + tests + sentinel-paths + version
      bump + docs + PHASE_MAP + notes-phase-28.md.
* [x] **[Sandbox]** Local `pytest tests/phase_28/` → **69/69
      sandbox-runnable pass**; 7 server-importing test files (~38 cases)
      skip-to-collect on Python 3.10 due to `datetime.UTC` (needs 3.11+);
      will run green in docker.
* [ ] **[Linux]** Host pip refresh NOT needed (no new top-level pkg).
* [ ] **[Linux]** `docker compose --profile test build mindsos-test`.
* [ ] **[Linux]** `docker compose run --rm mindsos-test pytest
      tests/phase_28/ tests/`. **Expected: ~3075 passed, 28 skipped.**
* [ ] **[Mac]** Commit + push + open PR + CI green (release.yml).
* [ ] **[Mac]** Squash-merge.
* [ ] **[Linux]** `mindsos confirm-phase --phase 28 --notes-file
      notes-phase-28.md` — **GATED ON `phase-27-confirmed` tag pushed
      + tag-CI green** (R5 PB-48 (a) gate 2).
* [ ] **[Mac]** Commit + push `PHASE_28_CONFIRMED.md`.
* [ ] **[Mac]** `git tag phase-28-confirmed <follow-up-sha>` + push.
* [ ] **[Mac]** CI re-runs against tag green.

## §8 Carry-forwards to Phase 29+

* TYPE_COMPAT auto-discovery + 5-kind CONSTRAINT enforcement — Phase 29.
* `SuccessorHop` dataclass + walks — Phase 29 atomic per R4 PB-45.
* Pipeline finder + invocation + InvocationResult/call_capacity
  exports + problem_trace — Phase 30 (flips sentinel tests).
* Residents + text builtins + pathfinding — Phase 31.
* `docs/usage/capacity/building.md` substantive content — Phase 29.
* Write capacities + symmetric contract + per-flow validators — Phases 33-35.
* `mindsos capacity` CLI Typer group — Phase 30 (invoke anchor).
* Additional-graph membership API per ADR-0085 — first consumer.
* B-26b-T5 — RESOLVED at Phase 28 via §am5. No further carry-forward.
