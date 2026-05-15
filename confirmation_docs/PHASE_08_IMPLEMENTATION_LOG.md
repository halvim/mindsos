# Phase 08 Implementation Log

> Author: implementation chat 2026-05-14 (off the design-locked
> handoff at `confirmation_docs/PHASE_08_NEXT_CHAT_PROMPT.md` +
> design log at `PHASE_08_DESIGN_LOG.md`). Branch: `phase-08` off
> `origin/main` (`b07fdc6`). Locks: 74 design-side picks (15 M + 14 PB
> + 14 RPB + 15 RR + 16 R4) + 1 user override (RPB-7 uncapped test
> budget) + Phase 08 implementation pushbacks below.

## Implementation pushbacks (continuing Phase 07's P26-P100 numbering)

### P60 — `add_metaedge` / `add_metahyperedge` cannot accept explicit ids (audit-time)

**Surfaced:** Step 0 audit (this chat) revealed the row's "slim port"
description was incomplete. The v3 baseline `MetagraphLoader` uses
private `mg._restore_metaedge(edge_id=...)` / `mg._restore_metahyperedge(edge_id=...)`
helpers that DO NOT exist on halvim's `Metagraph`. Halvim's
`add_metaedge` + `add_metahyperedge` always mint fresh UUIDs (the
`MetaEdge` / `MetaHyperEdge` dataclasses accept an explicit
`edge_id` via field-default, but the factories on Metagraph don't
expose it). `add_intergraph_edge` (Phase 05b) + `add_intergraph_hyperedge`
(Phase 05c) DO accept explicit ids — the 2 missing factories are an
asymmetry.

**Pick: A** (user-signed-off 2026-05-14). Additively extend
`add_metaedge` + `add_metahyperedge` with `edge_id: Optional[str] = None`
+ `_validate: bool = True` kwargs (mirrors Phase 05b/05c precedent on
the 2 intergraph factories; mirrors Phase 06 `add_node` / `add_edge` /
`add_hyperedge` shape from Phase 03). ~20 LoC delta on
`mindsos_core/models/metagraph.py`; no behavior change for existing
callers.

**Implementation:** `mindsos_core/models/metagraph.py:592-705` (metaedge)
+ `:712-895` (metahyperedge). Reconstruction loader uses the new
kwargs at `metagraph_loader.py::_load_metaedges` and
`_load_metahyperedges`.

**Tests:** `tests/phase_08/test_p60_metaedge_explicit_id.py` (6
assertions covering explicit-id round-trip + UUID mint default +
collision raises IdentityError + `_validate=False` tolerates
namespaced keys).

### P61 — Phase 07 IntergraphHyperEdge anchor persist gap

**Surfaced:** writing `metagraph_loader.py::_load_intergraph_hyperedges`
made the issue obvious. Phase 07's
`build_unwind_create_intergraph_hyperedges` at
`mindsos_core/cypher/builders.py:301-327` persisted ONLY `:MEMBER`
rels — anchors were NOT written. The `IntergraphHyperEdge` dataclass
invariant `n_anchors >= 1` made round-trip impossible (would fail
`SchemaError("requires at least 1 anchor")` on reconstruction).
Phase 05c row text at PHASE_MAP.md:1434 explicitly specifies
`:ANCHOR` / `:MEMBER` rel split for n-ary persistence — so Phase 07's
implementation was incomplete relative to the locked design.

**Pick: A** (announced inline at impl time per project rule on
genuine row contradictions). Additively extend Phase 07's persist
chunk:

1. `mindsos_core/cypher/builders.py::build_unwind_create_intergraph_hyperedges`
   — add `UNWIND row.anchors AS anc` + `MERGE (ih)-[:ANCHOR]->(an)`
   block alongside the existing `:MEMBER` block. Row shape gains
   `anchors: list[{node_id, graph_id}]`.
2. `mindsos_core/persistence/metagraph_repository.py:160-180` —
   persist-row construction adds the `anchors` list built from
   `ih.anchors`.
3. `mindsos_core/reconstruction/metagraph_loader.py::_load_intergraph_hyperedges`
   — reads both `:ANCHOR` and `:MEMBER` rels via two `OPTIONAL MATCH`
   sub-queries collecting into separate lists.

**Backwards-compatibility:** Phase 07 readers don't query `:ANCHOR`
rels; they keep working. **Old data** persisted before the Phase 08
fix has no `:ANCHOR` rels; affected rows surface in the loader's
WARNING log + are SKIPPED. Recovery: re-`sync --metagraph M --replace`
under Phase 08 (after dropping dependent state per RPB-4 C).

**Tests:** `tests/phase_08/test_p61_intergraph_hyperedge_anchor_persist.py`
(3 assertions: builder query shape; persist-row construction;
integration round-trip).

## Commit sequence (single feature branch — squash-merge target)

The implementation lands on `phase-08` as a single feature branch.
Squash-merge to main will produce one Phase 08 commit per the
per-phase workflow (steps j → l in `user_two_machine_setup.md`).
Branch ahead-of-main delta: +18 source modules + +20 test modules
+ +4 doc edits + 1 ADR file edit at project root (outside
halvim_mindsos git tracking per Model C hybrid; mirrors Phase 07
chunk-7 precedent).

## Files modified

### `mindsos_core/`

* `exceptions.py` — 3 new classes (`RefreshUnsafeError`,
  `WALReplayerMissingError`, `RoleMismatchError`).
* `_observers.py` — new `AfterLoadCallback` type alias +
  `_dispatch_after_load` helper with per-observer exception isolation
  (RR-9 A diverges from `_dispatch_after_persist`).
* `models/metagraph.py` — `register_after_load_observer` method +
  `_after_load_observers` list init + P60 explicit-id kwargs on
  `add_metaedge` + `add_metahyperedge`.
* `reconstruction/__init__.py` — 6 + 3 exports (R4-12 A).
* `reconstruction/graph_loader.py` — NEW `iter_load_graph` function
  (PB-3 A) + refactored `load_graph` via single-batch sentinel
  (RR-12 A).
* `reconstruction/metagraph_loader.py` — NEW. Class `MetagraphLoader`
  + module function `load_metagraph` (RR-5 B / RR-8 A / R4-1 A
  locked sequence / R4-7 A+C identity preservation).
* `cypher/builders.py` — P61 A: `build_unwind_create_intergraph_hyperedges`
  emits `:ANCHOR` rels alongside `:MEMBER`.
* `persistence/metagraph_repository.py` — P61 A: persist-row builds
  `anchors` list from `ih.anchors`.

### `mindsos_instances/`

* `reconstruction/__init__.py` — NEW. Exports `InstanceLoader`.
* `reconstruction/instance_loader.py` — NEW. Slim port from v3
  (substrate-rewrite to use `ElementRegistry.add` not v3's
  `mg._attach_instance`; RR-3 A allow-list validation; RR-4 B orphan
  template log+skip).
* `registry.py::attach_registry` — extends with after-load observer
  subscription path (PB-4 A); idempotent per Phase 06 P49 B helper.

### `mindsos_cli/`

* `commands/persistence.py` — `sync --metagraph M [--replace]`
  (PB-8 A + RPB-4 C); `load --metagraph M [--to-json] [--json]`
  (PB-9 A + R4-5 A + RR-7 A); `verify --source=db --metagraph M`
  UNBLOCK (PB-7 A); `--graph G | --metagraph M` mutex on load + verify
  + sync (R4-6 A); 9-line flat summary builder; sibling fromdb.json
  payload builder.
* `app.py` — help-text bump Phase 07 → Phase 08 (RR-14 A).
* `manifest.toml` — `phase = "08"` + `version = "0.0.0+phase08"`
  (R4-15 A).
* `__init__.py` — `__version__ = "0.0.0+phase08"`.

### Cross-package version-string parity (R4-15 A)

* `mindsos_core/__init__.py` — `__version__` bump.
* `mindsos_instances/__init__.py` — `__version__` bump.
* `pyproject.toml` — `version` + `description` bump.
* `docker-compose.yml` — image tags `mindsos:phase08-{prod,test}`
  (R4-16 A).
* `Dockerfile` — comment bump (Phase 06 wildcard COPY of
  `mindsos_instances` already covers the new `reconstruction/`
  subdir; no explicit COPY needed).

### `tests/`

* `_shared/sentinel_paths.py` — +5 entries (R4-14 A: metagraph_loader,
  instances/reconstruction/__init__, instance_loader, metagraph_equality,
  large_graph_factory).
* `_shared/metagraph_equality.py` — NEW. `assert_metagraphs_equal`
  walker (RR-13 A).
* `_shared/large_graph_factory.py` — NEW. `make_large_graph_fixture`
  builder (RR-13 A).
* `conftest.py` — `pytest.mark.slow` marker registration (RPB-12 B+C).
* `phase_08/` — NEW directory; 22 test modules covering R4-3 A
  exceptions, RR-9 A dispatcher, PB-4 A + RPB-9 A observer, P60
  factories, P61 A anchor persist, PB-3 A + RPB-1 A + RPB-8 A
  iter_load_graph, RR-12 A load_graph refactor, R4-11 A loader class,
  R4-8 A recover-first, RPB-3 C narrow-catch, PB-11 A schema_name,
  R4-7 A+C identity preservation, R4-2 D refresh edge cases, RR-3 A
  override allow-list + RR-4 B orphan template, R4-6 A mutex, R4-15 A
  parity, RPB-6 A legacy-strip, RR-1 A unregister, PB-7 A
  verify-unblock, PB-9 A + R4-5 A load CLI, PB-8 A + RPB-4 C sync
  CLI, RR-13 A walker + factory, plus opt-in 10K slow test.

### `docs/`

* `usage/core/persistence.md` — frontmatter bump + Phase 08
  additions section + streaming + refresh sub-sections (RR-15 A).
* `dev/internals/core.md` — frontmatter bump + NEW "Reconstruction
  layer (Phase 08)" section with 5 subsections (RR-15 A).
* `api/core/loaders.md` — NEW. Full API reference (RR-15 A).
* `changelog/CHANGELOG.md` — Phase 08 entry appended.
* `mkdocs.yml` — nav entry for `api/core/loaders.md`.

### Project-root ADR (outside halvim_mindsos git tracking; Model C hybrid)

* `/Layered Intelligence/docs/decisions/adr/0124-streaming-loader-iter-load-and-refresh.md`
  — status `Proposed → Accepted`; PB-3 A signature amendment
  (`iter_load_graph` graph-scoped, no `metagraph_id` slot); PB-5 B
  Constraint amendment (`RefreshUnsafeError` class shipped;
  enforcement deferred); RR-6 A `§Implementation references`
  rewritten with actual halvim paths; P27 C acceptance-criterion
  wording.

## Test plan summary

Per RPB-7 user-override 2026-05-13 (uncapped budget):

* **Unit (sandbox-runnable; no FalkorDB)** — every Cypher-shape +
  exception-class + observer-plumbing assertion via InMemoryClient
  call-recording. Files: `test_exceptions_phase08.py`,
  `test_after_load_observer.py`, `test_after_load_observer_dispatcher.py`,
  `test_p60_metaedge_explicit_id.py`, `test_iter_load_graph_unit.py`,
  `test_load_graph_refactor.py`, `test_metagraph_loader_class.py`,
  `test_load_metagraph_unit.py`, `test_load_metagraph_recovery.py`,
  `test_legacy_metagraph_settings_stripped.py`,
  `test_identity_registry_unregister.py`, `test_refresh_unsafe_error_class.py`,
  `test_doctor_phase08.py`, `test_p61_intergraph_hyperedge_anchor_persist.py`
  (partial), `test_metagraph_equality_helper.py`,
  `test_large_graph_factory.py`, `test_instance_loader_unit.py`,
  `test_refresh_edge_cases.py` (empty-role unit + role-mismatch
  integration).
* **Integration (`@pytest.mark.integration`; requires FalkorDB
  sidecar)** — round-trip fidelity tests via the live driver. Files:
  `test_load_metagraph_integration.py` (4 fixture variants per Phase
  08 row), `test_iter_load_graph_integration.py` (3 RPB-8 A scenarios),
  `test_iter_load_graph_intergraph_excluded.py` (RPB-10 A),
  `test_load_metagraph_streaming.py` (RR-2 D),
  `test_load_metagraph_schema_name.py` (PB-11 A), additional sections
  of recovery / refresh / instance / CLI tests.
* **Slow tier (`@pytest.mark.slow`)** — `test_iter_load_graph_10k.py`
  (RPB-12 C). Opt-in; default test run excludes.

## Step 0 audit findings (carried forward)

See `confirmation_docs/PHASE_08_DESIGN_LOG.md` Step 0 section for the
design-side audit. Implementation-side Step 0 (this chat) confirmed
the design's findings + surfaced 4 additional anomalies:

* **A1** — ADRs live at project-root `/Layered Intelligence/docs/decisions/adr/`,
  NOT under halvim_mindsos. Per Model C hybrid + Phase 07 chunk-7
  precedent. Phase 08's ADR-0124 edit lands at project-root, outside
  halvim_mindsos git tracking.
* **A2** — `add_metaedge` + `add_metahyperedge` need explicit-id
  kwargs (→ P60 fix).
* **A3** — `mg._attach_instance` / `_attach_composite` /
  `element_instances` from v3 InstanceLoader do NOT exist on halvim
  Metagraph; substituted by `ElementRegistry.add` API. InstanceLoader
  port rewrites the substrate calls.
* **A4** — `_dispatch_after_load` exception-isolation diverges from
  `_dispatch_after_persist` (intentional per RR-9 A); slim-port copy
  would have missed this.

Plus the implementation-time P61 surfaced during MetagraphLoader
authoring (IntergraphHyperEdge anchor persist gap).

## CASC-1 unblocks

* Phase 09 (XRef) — observer pattern locked in Phase 08; XRefLoader
  subscribes via `register_after_load_observer` per RR-10 A.
* Phase 10 (Snapshot) — `verify --source=db --metagraph M` now full
  bandwidth (PB-7 A).
* Phase 14 (L2 KL bootstrap) — `load_metagraph` is the foundation.

## Pending tester actions

Per `user_two_machine_setup.md` workflow (steps c→l):

1. `[Linux] git pull` the `phase-08` branch.
2. `[Linux] pip install -e .` (refresh editable install — picks up
   new `mindsos_instances/reconstruction/` subpackage).
3. `[Linux] mindsos doctor --self-test --static-only` (host venv
   preflight; FALKORDB_HOST=localhost; verifies version-string parity
   + manifest phase + image-tag drift).
4. `[Linux] docker compose --profile test build mindsos-test`
   (pre-build per `feedback_confirm_phase_timeout.md`).
5. `[Linux] docker compose run --rm mindsos-test pytest tests/`
   (full cumulative suite; expect ≥ Phase 07's 1269 + Phase 08
   additions).
6. `[Linux]` manual CLI exploration of new surface:
   * `mindsos persistence sync --metagraph my-mg`
   * `mindsos persistence sync --metagraph my-mg --replace`
     (expect refusal on dependent state)
   * `mindsos persistence load --metagraph my-mg`
   * `mindsos persistence load --metagraph my-mg --json`
   * `mindsos persistence load --metagraph my-mg --to-json --force`
   * `mindsos persistence load --graph g1 --metagraph m1`
     (expect exit 1 — mutex)
   * `mindsos persistence verify --source=db --metagraph my-mg`
7. `[Linux] mindsos confirm-phase --phase 08 --notes-file notes-phase-08.md`.
8. `[Linux]` review + edit `confirmation_docs/PHASE_08_CONFIRMED.md`.
9. `[Mac OR Linux]` git add + commit + push + PR + squash-merge.
10. `[Mac, on main]` tag `phase-08-confirmed` from squash-merged
    commit; push tag; Release CI green per
    `feedback_release_workflow_ordering.md`.
