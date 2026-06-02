# Phase 29 — L3 TYPE_COMPAT auto-discovery + SuccessorHop + walks + rediscover

## phase_title

L3 Discovery + Walks

## §1 Scope (PHASE_MAP §29)

**Third L3 ship.** Adds 1 NEW source file (`discovery.py`) to existing
`mindsos_capacity/` package + edits 4 (`views.py`, `capacity_layer.py`,
`exceptions.py`, `__init__.py`). No new top-level package (9-site
checklist N/A).

**Features shipped:**

* `discover_for_capacity` + `discover_for_datastate` + `rediscover_all`
  free functions in `mindsos_capacity/discovery.py` (NEW).
* `SuccessorHop` dataclass + `successors_of` / `producers_of` /
  `consumers_of` walks on `CapacityLayerView` (atomic with discovery
  per Phase 28 R4 PB-45).
* `CapacityLayer.rediscover` method (drop auto edges + recompute;
  ADR-0078 capability gate on Global).
* Discovery hooks wired at end of `register_capacity` +
  `register_datastate`.
* Cross-graph MetaEdge variant ships at v1.
* `DiscoveryFailedError` (sub of `CapacityRegistrationError`) wrapping
  any discovery write failure during register / rediscover.

**Source files NEW (1):** `discovery.py`.
**Source files EDITED (4):** `views.py` (+SuccessorHop +3 walks),
`capacity_layer.py` (discovery hooks + rediscover method + DiscoveryFailedError),
`exceptions.py` (+DiscoveryFailedError; 4→5 classes), `__init__.py`
(+5 exports + version bump + docstring rewrite).

**No new constraint behaviour** vs Phase 28 — Phase 28 R0 PB-11 ("API
at 28; enforcement at 29") superseded by Phase 29 R0 PB-1 (runtime
constraint enforcement deferred to L4 per ADR-0092).

**Test files NEW (15):** `__init__.py`, `_fixtures.py`,
`test_discovery_for_capacity.py`,
`test_discover_for_datastate_dead_trigger.py`,
`test_discovery_cross_graph_metaedge.py`, `test_rediscover_all.py`,
`test_admin_override_preserved.py`, `test_views_successors_of.py`,
`test_views_producers_consumers.py`, `test_successor_hop_shape.py`,
`test_capacity_layer_rediscover_method.py`,
`test_discovery_failed_error.py`, `test_adr_amendment_sentinels.py`,
`test_phase_29_export_slate.py`,
`test_metagraph_schema_is_none_at_phase_29.py`. **~36 cases.**

**Cumulative target:** Phase 28 baseline 3073 + (39 collected − 3 ADR
sentinels skipping under Model C) = **3109 passed, 40 skipped** in
docker (Phase 28's 37 skips + 3 new Phase 29 ADR-amendment sentinels
that skip in-container because parent ADR tree at
`/Layered Intelligence/docs/decisions/adr/` is NOT COPYed into the
test image per Model C; behaviour matches Phase 28's 9-skip pattern
for the same reason). Reconcile from `PHASE_28_CONFIRMED.md` at impl
Step 0 (NOT yet on disk at design close; reconcile from
post-confirm-phase output if doc-commit pending).

**Local sandbox-runnable count (Python 3.10):** 36 passed, 3 skipped
under `tests/phase_29/` (test_capacity_layer_rediscover_method.py's
3 cases excluded due to `datetime.UTC` being Python 3.11+; those 3
will run green in docker on Python 3.12). Total Phase 29 cases =
**39** (close to the ~36 R5 PB-41 estimate; +3 from parametrize
expansion in test_phase_29_export_slate.py).

**Docs:** mkdocs.yml Capacity nav `(Phase 27, 28)` → `(Phase 27, 28, 29)`.
`docs/usage/capacity/building.md` substantive content **deferred to
Phase 30** per Phase 29 R0 PB-7 (alongside CLI + invoke runtime).

## §2 Design rounds summary

Six rounds (R0–R5 with R4 = pre-impl probe execution). See
`confirmation_docs/PHASE_29_DESIGN_LOG.md` for the full pick ledger
(44 picks across R0–R5; 2 R4 picks self-reversed at R5 toward parent
fidelity).

**Locked picks shaping ship:**

* R0 PB-1 — supersede Phase 28 R0 PB-11; no new constraint behaviour.
* R0 PB-3 — ship cross-graph MetaEdge variant at v1.
* R0 PB-5 — `DiscoveryFailedError` sub of `CapacityRegistrationError`;
  raise on discovery failure; partial-write state observable.
* R0 PB-7 — defer `building.md` to Phase 30.
* R1 PB-15 — ship `discover_for_datastate` (dead trigger at v1; sentinel test).
* R1 PB-16 — 2-case admin-override-preserved test surface.
* R4 probes 2 + 4 + 5 obsoleted R1 PB-12 (tombstone) + R1 PB-14 (private
  poke) + R2 PB-22 (bootstrap schema edit).
* R5 PB-37 + PB-38 reversed R4 PB-35 + PB-36 → parent-verbatim filter
  semantics (no `include_deprecated` discipline at Phase 29).

## §3 ADR amendments at ship (parent — no .git per Model C)

3 ADR touches in parent `/Layered Intelligence/docs/decisions/adr/`:

* **ADR-0069 §Implementation (Phase 29)** — auto-discovery shipped;
  halvim divergences (graph IDs in `add_metaedge`, public
  `remove_metaedge`); walks parent-verbatim no-filter discipline.
* **ADR-0086 §Implementation (Phase 29)** — admin-authoring is direct
  `Graph.add_edge` (no `add_type_compat` method); admin-deleted-auto-
  edge ambiguity flagged as Phase 30+ carry-forward.
* **ADR-0070 §Implementation (Phase 28 — closure footer at Phase 29)** —
  closure note: Phase 28 R0 PB-11 superseded; Phase 29 ships NO new
  constraint code.

**ADR-0068 + ADR-0092** unchanged (Phase 28 already covers both).

## §4 Sentinel-paths additions (+1)

`mindsos_capacity/discovery.py`.

## §5 12-site version bump `+phase28 → +phase29`

| # | Site | Status |
|---|------|--------|
| 1 | `pyproject.toml` `[project] version` | ✅ |
| 2 | `mindsos_cli/manifest.toml` `[mindsos] phase` | ✅ |
| 3 | `mindsos_cli/manifest.toml` `[mindsos] version` | ✅ |
| 4 | `docker-compose.yml` `mindsos:phase29-prod` | ✅ |
| 5 | `docker-compose.yml` `mindsos:phase29-test` | ✅ |
| 6 | `mindsos_cli/__init__.py` `__version__` | ✅ |
| 7 | `mindsos_core/__init__.py` `__version__` | ✅ |
| 8 | `mindsos_instances/__init__.py` `__version__` | ✅ |
| 9 | `mindsos_knowledge/__init__.py` `__version__` | ✅ |
| 10 | `mindsos_admin/__init__.py` `__version__` | ✅ |
| 11 | `mindsos_server/__init__.py` `__version__` | ✅ |
| 12 | `mindsos_capacity/__init__.py` `__version__` | ✅ |

## §6 Memory edits at ship

1. NEW `project_mindsos_phase_29.md` — phase summary + halvim
   divergences + carry-forwards.
2. UPDATE `project_mindsos_phase_28.md` — close carry-forwards items
   1 (TYPE_COMPAT discovery) + 2 (SuccessorHop + walks) + 3
   (`building.md` deferred further to Phase 30).
3. UPDATE `MEMORY.md` index with the new Phase 29 entry.

## §7 Ship checklist (13-step ordering per Phase 28 R2 PB-28 + R0 PB-9 2-gate)

* [x] **[Sandbox]** Edit 3 parent ADRs (no git; Model C).
* [ ] **[Mac]** Verify parent ADR diffs visually.
* [ ] **[Mac]** `git checkout -b phase-29 origin/main` — **GATED ON
      Phase 28 squash-merge to main** (R0 PB-9 gate 1).
* [x] **[Sandbox]** Halvim source + tests + sentinel-paths + version
      bump + mkdocs.yml + PHASE_MAP §29 + notes-phase-29.md +
      design log.
* [ ] **[Sandbox]** Local `python3 -m pytest tests/phase_29/` →
      sandbox-runnable pass; 1 server-importing test
      (`test_capacity_layer_rediscover_method.py` via `datetime.UTC`)
      may skip-to-collect on Python 3.10; will run green in docker.
* [ ] **[Linux]** Host pip refresh NOT needed (no new top-level pkg).
* [ ] **[Linux]** `docker compose --profile test build mindsos-test`.
* [ ] **[Linux]** `docker compose run --rm mindsos-test pytest
      tests/phase_29/ tests/`. **Expected: ~3109 passed, 40 skipped**
      (37 inherited from Phase 28 + 3 new Phase 29 ADR-amendment
      sentinels skipping per Model C).
* [ ] **[Mac]** Commit + push + open PR + CI green (release.yml).
* [ ] **[Mac]** Squash-merge.
* [ ] **[Linux]** `mindsos confirm-phase --phase 29 --notes-file
      notes-phase-29.md` — **GATED ON `phase-28-confirmed` tag pushed
      + tag-CI green** (R0 PB-9 gate 2).
* [ ] **[Mac]** Commit + push `PHASE_29_CONFIRMED.md`.
* [ ] **[Mac]** `git tag phase-29-confirmed <follow-up-sha>` + push.
* [ ] **[Mac]** CI re-runs against tag green.

## §8 Hotfix ledger preamble (R3 PB-30 → R4 PB-32 reduced to 1 slot)

R4 probes closed every concrete schema/API gap (PB-21 EdgeType
properties already whitelisted; PB-22 schema validation bypassed
under `schema is None`; PB-14 `remove_metaedge` public; PB-12
hard-delete confirmed). 1 contingency hotfix slot retained for
unforeseen impl-phase surprises:

* **B-29-T1** (reserved) — generic contingency.

## §9 Carry-forwards to Phase 30+ (9 items per R5 picks summary)

1. `docs/usage/capacity/building.md` substantive content — Phase 30
   (alongside CLI + invoke).
2. `mindsos capacity` CLI Typer group — Phase 30 (invoke anchor).
3. ADR-0086 admin-deleted-auto-edge resolution — first reported foot-gun.
4. Pipeline finder + invocation + `InvocationResult` / `call_capacity`
   + `ProblemTraceRecord` — Phase 30 (flips Phase 28 sentinels
   `test_invocation_not_exported.py` +
   `test_problem_trace_attribute_not_present_at_phase_28`).
5. Residents + text builtins + pathfinding — Phase 31.
6. Write capacities + symmetric contract + per-flow validators —
   Phases 33-35.
7. Additional-graph membership API per ADR-0085 — first concrete
   consumer.
8. Bulk rediscover verb (across all metagraphs) — first admin caller.
9. `include_deprecated` parameter discipline across L3 walks
   (`successors_of` / `producers_of` / `consumers_of` /
   `iter_capacities` / `iter_constraints` / `_drop_auto_edges`) —
   Phase 30+ when soft-delete becomes a real L4 concern (R5 PB-37
   carry-forward; reversal of R4 PB-35 toward parent fidelity).

## tester_notes

Phase 29 ships `mindsos_capacity/discovery.py` + `SuccessorHop` +
walks on `CapacityLayerView` + `CapacityLayer.rediscover` method +
`DiscoveryFailedError`. No new top-level package, no new CLI verb, no
new admin/server surface. The cross-graph MetaEdge variant ships at
v1; admin-override invariant verified per ADR-0086. Constraint surface
unchanged from Phase 28 (per ADR-0092 — runtime enforcement is L4's
concern). Probe-driven scope reductions at R4 dropped 2 carry-forward
items vs R3 estimate (tombstone-compact verb + public-method
follow-up both unnecessary).

Verify in-container with
`docker compose run --rm mindsos-test pytest tests/phase_29/ tests/`;
expect ~3109 passed / 37 skipped (no new skip class; Phase 28's 9
ADR-amendment sentinels continue to skip Model C-style in-container
when parent ADR tree isn't COPYed; Phase 29 adds 3 more such
sentinels under `test_adr_amendment_sentinels.py`).

Phase 30 sentinels (`test_invocation_not_exported.py` +
`test_problem_trace_attribute_not_present_at_phase_28`) remain
untouched and continue to pass at Phase 29.
