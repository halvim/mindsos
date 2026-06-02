# Phase 27 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

L3 DataStates + capacity primitives

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

First L3 phase ship. Slim port from parent /Layered Intelligence/mindsos_capacity/ (3081 LOC across 13 files) into halvim's NEW top-level `mindsos_capacity/` package (7th sibling: cli, core, instances, knowledge, admin, server, capacity).

## §1 Scope shipped

5 source files in `mindsos_capacity/`:

* `datastate.py` — `DataState` + `ShapeDescriptor` + `validate_datastate` + `strict_compatible` + `list_of_compat`. Verbatim from parent.
* `capacity.py` — `_CapacityBase` + `Capacity` / `Monitor` / `Adapter` dataclasses + `validate_for_registration` + `CapacityCallable`. Verbatim. **`InvocationResult` + `call_capacity` live in this file for parent-layout parity but are NOT exported from `__init__.py` until Phase 30 per R3 PB-26 staging.**
* `identifiers.py` — Full vocabulary + IRI builders + parsers + 12 categories + REF_TYPES (6 members per ADR-0067 §am1).
* `exceptions.py` — Slim to 3 classes (`CapacityLayerError` base + `DataStateError` + `CapacityRegistrationError`); 4 others (ConstraintViolationError, ResidentError, ProblemTraceError, PipelineNotFoundError) defer to Phases 28-31 raisers.
* `__init__.py` — 65 names in `__all__`. Excludes CapacityLayer, bootstrap, runtime, discovery, schemas, views, capabilities, builtins, types — all defer.

3 test files in `tests/phase_27/`:

* `test_datastate.py` — 8 tests, verbatim port from `tests_l3/unit/test_datastate.py`.
* `test_identifiers.py` — 10 tests, verbatim port from `tests_l3/unit/test_identifiers.py`.
* `test_capacity_dataclass.py` — 14 tests, NEW thin file (R2 PB-10). Covers Capacity/Monitor/Adapter dataclass def-time IRI + property bag + `validate_for_registration` + REF_TYPES parity (test 13 per ADR-0067 §am1).

1 doc page: `docs/usage/capacity/data-states.md` — port body verbatim from parent; halvim frontmatter (`last_confirmed_phase: 27`); stripped body line 53 broken cross-link to Phase 28's `building.md` (PB-32).

## §2 EXCLUDED (defer)

* `types.py` — write-API session plumbing → **Phase 33**
* `capacity_layer.py` — `CapacityLayer` registry → **Phase 28**
* `bootstrap.py` — Global+Local + ensure-category-graph → **Phase 28**
* `capabilities.py` — `CAN_WRITE_GLOBAL` → **Phase 28**
* `discovery.py` — auto-TYPE_COMPAT → **Phase 29**
* `runtime.py` — invoke + residents + ProblemTrace → **Phase 30**
* `schemas.py` — schema_for_role + Core-schema builders → **Phase 28+**
* `views.py` — `CapacityLayerView` + `SuccessorHop` → **Phase 28+**
* `builtins/` — DS_RAW_TEXT + Pipeline + install_text_capacities → **Phase 31**

## §3 ADR delta (parent only — halvim has no docs/decisions/adr/ per Model C)

* **ADR-0066 §Implementation footer (NEW)** — collision-detection staging: Phase 27 ships the IRI form + parser + exception class; Phase 28 ships the registry-side collision detection via `CapacityLayer.register`. Status stays Accepted.
* **ADR-0067 §amendment-1 (NEW)** — REF_TYPES contract: **L3.REF_TYPES ⊆ L2.REF_TYPES** with documented exclusion `L2 - L3 == {"PROMOTED"}` (PROMOTED L2-exclusive; L3 has no promotion lifecycle). Rationale: parent precedent + install-isolation discipline. Parity test at `tests/phase_27/test_capacity_dataclass.py::test_ref_types_subset_of_kl_ref_types`.

## §4 Test counts

* **Phase 27 isolated:** 32 passed in 0.16s host-native (Python 3.10 sandbox; image is 3.11+).
* **Cumulative docker:** 2968 passed, 28 skipped, 0 failed in 1872s (31:12) on `mindsos:phase27-test`. Phase 26b baseline 2931 + 32 new + 5 (manifest parity loop iterates over 7 packages vs 6; sentinel flips) = 2968.
* **Manifest-driven parity:** GREEN for all 7 packages (mindsos_cli, mindsos_core, mindsos_instances, mindsos_knowledge, mindsos_admin, mindsos_server, mindsos_capacity).
* **Slim-port isolation:** Imports clean. `__all__` = 65 names. Excluded surface absent from public API. `InvocationResult` + `call_capacity` reachable at full module path only (per PB-26 staging).

## §5 12-site version bump `+phase26b → +phase27`

pyproject.toml + manifest.toml [mindsos] phase + manifest.toml [mindsos] version + docker-compose.yml ×2 (prod + test image tags) + 7 pkg `__init__.py` (cli, core, instances, knowledge, admin, server, capacity).

## §6 9-site new-top-level-pkg checklist (Phase 27 generalization)

Grew from 7 to 9 sites:

1. `pyproject.toml` `[tool.setuptools.packages.find] include` += `"mindsos_capacity*"`
2. `Dockerfile` prod stage `COPY mindsos_capacity ./mindsos_capacity`
3. `Dockerfile` test stage `COPY mindsos_capacity ./mindsos_capacity`
4. `tests/_shared/sentinel_paths.py` — 5 module paths appended
5. `mindsos_cli/commands/doctor.py` — **manifest-driven parity loop** (was 6 hand-coded blocks; now iterates `manifest["mindsos"]["packages"]`); `report["runtime"]["versions"]` flat dict replaces 6 per-pkg fields (R3 PB-25 + R5 PB-33/34)
6. `mindsos_cli/manifest.toml` — NEW `[mindsos] packages = [7 names]` (R5 PB-33)
7. `tests/phase_18/test_doctor_6pkg_parity.py` — refactor to manifest-driven; class renamed `TestAll6PkgsAtCurrentPhase` → `TestAllPackagesMatchManifest`; reads manifest via `tomllib`
8. `mkdocs.yml` — `Usage > Capacity (Phase 27) > Data states` nav entry
9. Host pip refresh (Linux side) — `pip install -e . --user --break-system-packages`

Net effect: closes the 6-pkg literal-decay class permanently. Future new-pkg phases add ONE manifest line + ONE `__init__.py` site; doctor + parity test require no further edits.

## §7 Design rounds + locked picks

5 design rounds (R0-R5; R4 saturation with zero new PBs) with picks-per-pushback discipline per `feedback_pushback_format_with_picks.md`. Full picks ledger at `confirmation_docs/PHASE_27_DESIGN_LOG.md`.

Locked picks shaping ship:

* **R0 PB-1 (a+c) + R2 PB-9 (a) + R3 PB-26 (c)** — 5-file slim port; drop `types.py`; keep `call_capacity`/`InvocationResult` in `capacity.py` un-exported.
* **R1 PB-8 → R3 (b)** — REF_TYPES duplicated (parent precedent + install-isolation); ADR-0067 §am1 carves PROMOTED out as L2-exclusive.
* **R2 PB-20 (a)** — ADR-0066 §Implementation footer documents IRI-form-at-27 vs collision-check-at-28 staging.
* **R3 PB-25 (b)** — manifest-driven N-pkg parity generalization closes the 6-pkg literal-decay class.
* **R5 PB-32 (a)** — strip data-states.md body line 53 broken cross-link.
* **R5 PB-33/34** — `[mindsos] packages = [...]` + `runtime.versions = {pkg: ver}` flat dict.

## §8 Hotfix ledger (1)

| ID | Class | Root cause + fix |
|---|---|---|
| **B-27-T1** | parity-test-sentinel-flip (NEW class — see [[feedback-parity-test-sentinel-flip-at-target-phase]]) | `tests/phase_12/test_ref_types_and_roles.py::test_adr_0067_parity_test_deferred_to_phase_27` asserted `pytest.raises(ModuleNotFoundError)` for `import mindsos_capacity`. Now that Phase 27 ships the package, the sentinel must flip. Renamed test `_deferred_to_phase_27` → `_landed_at_phase_27`; flipped assertion to verify ADR-0067 §am1 contract directly (`L3.REF_TYPES ⊆ L2.REF_TYPES` + `L2 - L3 == {"PROMOTED"}`). Surfaced as 1 docker-pytest failure on first cumulative run; rebuilt + rerun GREEN. |

## §9 Carry-forwards to Phase 28+

1. **B-26b-T5 §am3 orphan-Node Cypher** (Phase 27 R0 PB-3 (a) deferral) — Phase 26b release Cypher writes Node rows without `[:IN_GRAPH]` link; `MetagraphLoader.load` doesn't surface release content. Phase 28 is the first phase that reads released L3 canonical content via `MetagraphLoader.load`; the orphan gap surfaces immediately. Fix candidate: mechanical 2-line patch to `_RELEASE_MERGE_CYPHER` + `_PROPOSE_MERGE_CYPHER` adding `WITH n MATCH (g:Graph {id: $canonical_graph_id}) MERGE (n)-[:IN_GRAPH]->(g)`. See `[[feedback-release-cypher-orphan-node]]`.
2. **`CapacityLayer` registry + bootstrap + collision detection** — Phase 28 ships `mindsos_capacity/capacity_layer.py` + `bootstrap.py` + `capabilities.py`. ADR-0066 §Implementation footer (Phase 27 ship) documents the collision-check belongs in `CapacityLayer.register` at Phase 28.
3. **12 categories registered as Core nodes** — Phase 28 owns the `ensure_category_graph` + Global/Local bootstrap. Phase 27 ships the 12 string constants only.
4. **TYPE_COMPAT auto-discovery + CONSTRAINT edges** — Phase 29.
5. **Pipeline finder + invocation + ProblemTraceRecord** — Phase 30. **Lifts `InvocationResult` + `call_capacity` from `mindsos_capacity.capacity` into `__init__.py` exports** per PB-26 staging.
6. **Residents + text builtins** — Phase 31.
7. **Write capacities + `SessionProtocol`** — Phases 33-35.
8. **ADR-0067 §am2** if L3 acquires promotion-like lifecycle later.

## §10 Implementation references

* `notes-phase-27.md` — this file (impl checklist + per-site enumerations + hotfix ledger).
* `confirmation_docs/PHASE_27_DESIGN_LOG.md` — full round-by-round design log.
* `/Layered Intelligence/docs/decisions/adr/0066-capacity-iri-form.md` §Implementation — collision-check staging.
* `/Layered Intelligence/docs/decisions/adr/0067-ref-types-shared-with-kl.md` §amendment-1 — REF_TYPES subset contract.
* `mindsos_cli/manifest.toml` `[mindsos] packages` — canonical N-pkg parity source.
