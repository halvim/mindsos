# Phase 27 — L3 DataStates + capacity primitives (slim port)

## §1 Scope (PHASE_MAP §27)

**First L3 ship.** Slim port of read-side definitions from parent
`mindsos_capacity/` (3081 LOC across 13 files) into halvim's new
`mindsos_capacity/` top-level package.

**Source files (5):**

* `mindsos_capacity/__init__.py` — slim exports (~58 names, 7
  dataclasses + 3 exceptions + 12 categories + 4 node types + 4
  kinds + 4 edges + 5 constraints + 5 refs + RESERVED + helpers)
* `mindsos_capacity/datastate.py` — `DataState` + `ShapeDescriptor`
  + `validate_datastate` + `strict_compatible` + `list_of_compat`
* `mindsos_capacity/capacity.py` — `_CapacityBase` + `Capacity` +
  `Monitor` + `Adapter` + `CapacityCallable` + dataclass-only IRI
  property + `validate_for_registration`. `InvocationResult` +
  `call_capacity` LIVE in this file for parent-layout parity but
  are NOT exported from `__init__.py` until Phase 30.
* `mindsos_capacity/identifiers.py` — full vocabulary + IRI
  builders + parsers + 12 categories + REF_TYPES (6 members per
  ADR-0067 §amendment-1)
* `mindsos_capacity/exceptions.py` — slim to 3 classes
  (`CapacityLayerError` base + `DataStateError` + `CapacityRegistrationError`)

**EXCLUDED (defer to later phases):**

* `types.py` — write-API session plumbing → **Phase 33**
* `capacity_layer.py` — `CapacityLayer` registry → **Phase 28**
* `bootstrap.py` — Global+Local + ensure-category-graph → **Phase 28**
* `capabilities.py` — `CAN_WRITE_GLOBAL` → **Phase 28**
* `discovery.py` — auto-TYPE_COMPAT → **Phase 29**
* `runtime.py` — invoke + residents + ProblemTrace → **Phase 30**
* `schemas.py` — schema_for_role + Core-schema builders → **Phase 28+**
* `views.py` — `CapacityLayerView` + `SuccessorHop` → **Phase 28+**
* `builtins/` — DS_RAW_TEXT + Pipeline + install_text_capacities → **Phase 31**

**Test files (3):**

* `tests/phase_27/test_datastate.py` — 8 tests (port verbatim from
  parent `tests_l3/unit/test_datastate.py`)
* `tests/phase_27/test_identifiers.py` — 10 tests (port verbatim from
  parent `tests_l3/unit/test_identifiers.py`)
* `tests/phase_27/test_capacity_dataclass.py` — 14 tests (NEW thin
  file authored at Phase 27 per R2 PB-10 + PB-23 inventory; covers
  Capacity/Monitor/Adapter dataclass def-time IRI + property bag +
  `validate_for_registration` slice that ships without the registry,
  plus ADR-0067 §amendment-1 parity test)

**Total: 32 new tests.** Cumulative target: Phase 26b baseline 2931 +
32 ≈ **2963 passed, 28 skipped (no new skips at Phase 27)**.

**Docs (1):**

* `docs/usage/capacity/data-states.md` — port content body verbatim
  from parent; rewrite frontmatter to halvim convention
  (`last_confirmed_phase: 27`); strip line 53 broken cross-link to
  `building.md` (Phase 28 ships that page).
* `mkdocs.yml` — add `Usage > Capacity (Phase 27) > Data states` nav.

## §2 Design rounds summary

Five rounds (R0 + R1 + R2 + R3 + R5; R4 saturated with zero PBs).
Picks-per-pushback discipline per memory
`feedback_pushback_format_with_picks.md`. See `confirmation_docs/PHASE_27_DESIGN_LOG.md`
for the full pick ledger.

**Locked picks shaping ship:**

* **R0 PB-1 (a+c) + R2 PB-9 (a) + R2 PB-18 (c)** — 5-file slim port; drop
  `types.py`; keep `call_capacity` + `InvocationResult` in `capacity.py`
  but don't export from `__init__.py`.
* **R1 PB-8 → R3 (b)** — REF_TYPES duplicated (parent precedent +
  install-isolation argument); ADR-0067 §amendment-1 carves PROMOTED
  out as L2-exclusive.
* **R2 PB-20 (a)** — ADR-0066 §Implementation footer documents
  IRI-form-at-27 vs collision-check-at-28 staging.
* **R3 PB-25 (b)** — manifest-driven N-pkg parity generalization
  closes the 6-pkg literal-decay class; `[mindsos] packages = [...]`
  is the single source.

## §3 ADR amendments (parent only — no .git per Model C)

1. `/Layered Intelligence/docs/decisions/adr/0066-capacity-iri-form.md`
   — added §Implementation footer (collision-check phasing across 27
   and 28); Status stays Accepted.
2. `/Layered Intelligence/docs/decisions/adr/0067-ref-types-shared-with-kl.md`
   — added §amendment-1 (REF_TYPES L3 ⊂ L2; `L2 - L3 == {"PROMOTED"}`).

## §4 9-site new-top-level-package checklist (Phase 27 generalization)

| # | Site | Status |
|---|------|--------|
| 1 | `pyproject.toml` `[tool.setuptools.packages.find] include` += `"mindsos_capacity*"` | ✅ |
| 2 | `Dockerfile` prod stage `COPY mindsos_capacity ./mindsos_capacity` | ✅ |
| 3 | `Dockerfile` test stage `COPY mindsos_capacity ./mindsos_capacity` | ✅ |
| 4 | `tests/_shared/sentinel_paths.py` — 5 module paths appended | ✅ |
| 5 | `mindsos_cli/commands/doctor.py` — manifest-driven parity loop (was: 6 hand-coded blocks; now iterates `manifest["mindsos"]["packages"]`); `report["runtime"]["versions"]` flat dict replaces 6 per-pkg fields | ✅ |
| 6 | `mindsos_cli/manifest.toml` — NEW `[mindsos] packages = [...7 names...]` | ✅ |
| 7 | `tests/phase_18/test_doctor_6pkg_parity.py` — refactor to manifest-driven; rename class `TestAll6Pkgs...` → `TestAllPackagesMatchManifest`; uses `tomllib` | ✅ |
| 8 | `mkdocs.yml` — `Usage > Capacity (Phase 27) > Data states` nav entry | ✅ |
| 9 | Host pip refresh — **[Linux]** `pip install -e . --user --break-system-packages` after pulling phase-27 branch | **TODO [Linux]** |

## §5 12-site version bump `+phase26b → +phase27`

| # | Site | Status |
|---|------|--------|
| 1 | `pyproject.toml` `[project] version` + `description` rewrite | ✅ |
| 2 | `mindsos_cli/manifest.toml` `[mindsos] phase` | ✅ |
| 3 | `mindsos_cli/manifest.toml` `[mindsos] version` | ✅ |
| 4 | `docker-compose.yml` `mindsos:phase27-prod` | ✅ |
| 5 | `docker-compose.yml` `mindsos:phase27-test` | ✅ |
| 6 | `mindsos_cli/__init__.py` `__version__` | ✅ |
| 7 | `mindsos_core/__init__.py` `__version__` | ✅ |
| 8 | `mindsos_instances/__init__.py` `__version__` | ✅ |
| 9 | `mindsos_knowledge/__init__.py` `__version__` | ✅ |
| 10 | `mindsos_admin/__init__.py` `__version__` | ✅ |
| 11 | `mindsos_server/__init__.py` `__version__` | ✅ |
| 12 | `mindsos_capacity/__init__.py` `__version__` (NEW pkg) | ✅ |

## §6 Memory edits at ship (3)

1. `project_mindsos_phase_26b.md` — strike "tag pushed; release.yml
   green" drift; replace with whatever is true at Phase 27 ship time
   (R0 PB-0).
2. `feedback_new_top_level_package.md` — 7 → 9 sites at Phase 27
   (manifest `[mindsos] packages` + mkdocs nav additions).
3. `feedback_docker_compose_version_bump_site.md` — 10 → 12 sites at
   Phase 27.

## §7 Ship checklist (11-step ordering per PB-36)

* [x] **[Sandbox]** Edit parent ADRs (no git): ADR-0066 §Implementation
      footer + ADR-0067 §amendment-1.
* [x] **[Sandbox]** Halvim source edits + tests (32 new tests in
      tests/phase_27/).
* [x] **[Sandbox]** Local `pytest tests/phase_27/` → **32 passed in
      0.16s** on Python 3.10.
* [ ] **[Mac]** `git checkout -b phase-27 origin/main`.
* [ ] **[Linux]** `pip install -e . --user --break-system-packages`
      (host pip refresh; site #9 of new-pkg checklist).
* [ ] **[Linux]** `docker compose --profile test build mindsos-test`.
* [ ] **[Linux]** `docker compose run --rm mindsos-test pytest
      tests/phase_27/ tests/`. **Expected: ~2963 passed, 28 skipped.**
* [ ] **[Mac]** Commit + push + PR + CI green (release.yml).
* [ ] **[Mac]** Squash-merge.
* [ ] **[Linux]** `mindsos confirm-phase --phase 27 --notes-file
      notes-phase-27.md` → generates `confirmation_docs/PHASE_27_CONFIRMED.md`.
* [ ] **[Mac]** Commit + push `PHASE_27_CONFIRMED.md`.
* [ ] **[Mac]** `git tag phase-27-confirmed <follow-up-sha>` + push.
* [ ] **[Mac]** CI re-runs against tag green.

## §8 Carry-forwards to Phase 28+

* **B-26b-T5 §am3 orphan-Node Cypher** — defer to Phase 28 (first
  consumer of `MetagraphLoader.load` on released L3 canonical
  content). R0 PB-3 (a) lock.
* **CapacityLayer registry + bootstrap + collision detection** — Phase 28.
* **TYPE_COMPAT auto-discovery + CONSTRAINT edges** — Phase 29.
* **Pipeline finder + invocation + ProblemTraceRecord** — Phase 30
  (also lifts `InvocationResult` + `call_capacity` exports).
* **Residents + text builtins** — Phase 31.
* **Write capacities + `SessionProtocol`** — Phases 33–35.
