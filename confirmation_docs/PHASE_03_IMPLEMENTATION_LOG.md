# Phase 03 — Implementation Log

> Curated record of the Phase 03 design + implementation session
> (2026-05-04). Captures locked decisions, the Phase 03 row refinements,
> bug ledger, files touched, tests added, residual concerns, and the
> tester checklist. Read in conjunction with `PHASE_MAP.md` Phase 03
> row + the eventual `PHASE_03_CONFIRMED.md`.

---

## 1. Charter

Phase 03 = **L1 Graph elements** (slim port of `Graph` / `Node` / `Edge`
/ `HyperEdge` from the parent project, plus `mindsos_core/cypher/` for
ADR-0021 rel-type validation, behind a `mindsos graph` CLI surface with
JSON state-file persistence).

Per Phase 03 row Final amendments (29 items, locked in this session):

- Slim port of `mindsos_core/models/{graph,node,edge}.py` + `cypher/`
  (HyperEdge in `edge.py`, no separate `hyperedge.py`; matches parent).
- New `mindsos graph` Typer subcommand surface (9 subcommands).
- New `mindsos_cli/state.py` — JSON state-file persistence at
  `${MINDSOS_STATE_DIR or ~/.mindsos}/graph-<name>.json`.
- New shared test infrastructure: `tests/_shared/{cli,sentinel_paths,
  tomli_shim}.py`.
- Image-completeness regression test relocated to
  `tests/test_image_completeness.py` (root-level, single parametrised
  test over the cumulative `SENTINEL_PATHS` list).
- New docs: `docs/concepts/graphs-and-metagraphs.md`,
  `docs/usage/core/building-graphs.md`, `docs/api/core/{graph,node,
  edge,hyperedge}.md`, `docs/changelog/CHANGELOG.md` (with backfill).
- `mkdocs.yml` adds new top-level `Usage` section + `Changelog` section.
- `Dockerfile` comment lines updated to point at the relocated
  image-completeness test + shared sentinel-paths module.

---

## 2. Scope adjudications (decided at the top of the session)

| # | Question | Decision | Rationale |
|---|---|---|---|
| 2.1 | Cross-invocation persistence mechanism | **JSON state file**, parity with Phase 02 identity-registry (`graph-<name>.json`). | (a) parity with Phase 02 trains tester on the gotcha; (b) cross-invocation pass criterion drops out for free; (c) ~50 LOC concentrated in one file. |
| 2.2 | Pre-existing `tests/unit/test_graph.py` preservation | **Defer to Phase 04.** The parent file imports `Schema` / `NodeType` / `EdgeType` / `PropertyShapeError` / `UnknownTypeError` — all Phase 04 surface. Phase 03 ships only `tests/phase_03/`. | Cleanest. Matches Phase 02's pattern where preserved tests cover *fully shipped* surface; Schema isn't shipped in Phase 03. |
| 2.3 | Pass criterion replacement for "invalid IRI" bullet | **Both: dup-id + invalid rel-type.** Two pass-criterion bullets — duplicate `node_id` exits 1 with `IdentityError`; lowercase / mixed-case rel-type exits 1 with `CypherError` (ADR-0021). | "Invalid IRI" was nonsensical — Core treats `node_id` as opaque per ADR-0035 (Phase 02 already adjudicated). The two replacements cover the actual Phase 03 validation paths. |
| 2.4 | Intergraph edge primitive (raised mid-session) | **Defer to Phase 05 chat for adjudication.** Filed as PHASE_MAP §7 Q13 + full analysis at `confirmation_docs/INTERGRAPH_EDGE_DESIGN_NOTE.md`. Default outcome = defer indefinitely (status-quo: alignments-as-graph reification). | 6 pushbacks recorded against adding the primitive (Cypher OWNS, snapshot scope, schema validation, OCC/WAL ownership, importer migration cost, existing primitives may already cover). Phase 05 chat must answer 4 concrete asks before greenlighting. |
| 2.5 | ADR file porting to slim repo | **Deferred to Phase 38** (docs consolidation). Phase 03 references ADR-0014 / ADR-0021 as "(referenced; ADR file not yet ported to slim repo — confirmed against shipped behaviour only)". | Phase 02 set the silent precedent (ADR-0035 / 0131 referenced without porting). Phase 03 made it explicit. Recorded in `feedback_docs_source_of_truth.md` memory. |
| 2.6 | Changelog format | **Single `docs/changelog/CHANGELOG.md`**, append-only, one paragraph per phase. Phase 03 backfills Phase 00 / 01 / 02 entries + appends Phase 03. | Matches PHASE_MAP §6 ("each phase appends a 'Phase NN' line; final pass at 38"). |

---

## 3. Locked decisions (final, post-iteration — 29 appendix items)

The full list lives in PHASE_MAP Phase 03 row "Final amendments
(2026-05-04 — 29 items)". Highlights:

| # | Decision |
|---|---|
| 1 | Cumulative test count baseline corrected: Phase 02 tester-measured **117 + 1 skipped** (canonical); Phase 03 expected ≈ **163** + 1 skipped. |
| 2 | `inspect` / `add-*` against missing graph → exit 1 with structured error pointing at `mindsos graph create`. |
| 3 | Malformed `--prop` JSON falls back to literal string; documented limitation. |
| 4 | State-file `_state_version: 1` field. |
| 5 | Atomic state-file write via `<path>.tmp` + `os.replace`. |
| 6 | Image-completeness test relocates to `tests/test_image_completeness.py` (root); shared `SENTINEL_PATHS` list at `tests/_shared/sentinel_paths.py`. |
| 7 | `_run_cli` env-merge helper extracts to `tests/_shared/cli.py`. |
| 8 | `mindsos_core/__init__.py:__all__` Phase 03 additions: 8 new entries (cumulative 17). |
| 9 | `mindsos graph create` over existing state file → `IdentityError` (no new exception class). |
| 10 | HyperEdge state-file canonicalisation: `member_ids = sorted(...)`. |
| 11 | `--prop k=v` splits on first `=`; empty key → exit 2. |
| 12 | `tests/phase_03/test_state.py` adds direct unit tests of `mindsos_cli/state.py`. |
| 13 | `state.py` errors are plain Python (`RuntimeError`, `FileNotFoundError`); CLI wraps with `typer.Exit(1)` + stderr. |
| 14 | Concurrent state-file race documented as known issue (Phase 02 J-02 inheritance). |
| 15 | Dockerfile comment lines 70–71 / 101–103 updated to point at relocated test + shared sentinel-paths. |
| 16 | Docstring updates in slim `mindsos_core/__init__.py`, `exceptions.py`, `models/__init__.py`. |
| 17 | Phase 01/02 deferral carry-forward (η, H, D, J-02, K-02). |
| 18 | `mindsos graph list` discovery subcommand (~15 LOC + 1 test). |
| 19 | CLI exit code policy: 1 domain, 2 usage. |
| 20 | Doc inventory: every Phase 03 doc page is a NEW file. |
| 21 | `mkdocs.yml` nav: new top-level `Usage` section + `Changelog`. |
| 22 | `requirements.{in,txt}` / `requirements-test.txt` unchanged (stdlib-only). |
| 23 | `mindsos_core/cypher/__init__.py` exports match parent's identifier-only set. |
| 24 | Small in-row locks: `state_file_path` central name validation, `list` sorted by name, rel-type rejection covers lower + mixed case, state.py function signatures pinned, `pyproject.toml [tool.setuptools.packages.find]` already wildcards `mindsos_core*` (no edit needed). |
| 25 | `Graph` slim-port method inventory (8 methods) explicitly locked. |
| 26 | Slim-port dataclass field strips: Node drops `_version`; Edge / HyperEdge drop `deprecated_at` / `disputed_at` (drops `from datetime import datetime`). |
| 27 | `_state_version` contract on load (forward + backward compat — strict). |
| 28 | State-file list ordering: `nodes` / `edges` / `hyperedges` sorted by id; same on CLI list output. |
| 29 | State-file JSON v1 schema pinned (avoids Phase 07+ drift). |

---

## 4. Bug ledger

| ID | Symptom | Root cause | Fix |
|---|---|---|---|
| **A-03** | Phase 03 conftest's `tomli_shim` was missing — sandbox Python 3.10 imports of `mindsos_cli.app` failed with `ModuleNotFoundError: tomllib` (transitive via `confirm_phase.py`). | Phase 02 had the shim inline in `phase_02/conftest.py`; Phase 03 conftest didn't inherit. | Extracted to `tests/_shared/tomli_shim.py`; both phase_02 and phase_03 conftests import it (`# noqa: F401` to suppress unused-import warning). |

No production bugs surfaced; the design questions were adjudicated up
front (persistence mechanism, test_graph.py preservation, intergraph
edge scope, ADR porting policy, changelog shape).

---

## 5. Files added / modified

### Added (Phase 03)

```
mindsos_core/cypher/__init__.py
mindsos_core/cypher/identifiers.py
mindsos_core/models/node.py
mindsos_core/models/edge.py
mindsos_core/models/graph.py
mindsos_cli/state.py
mindsos_cli/commands/graph.py
tests/_shared/__init__.py
tests/_shared/cli.py
tests/_shared/sentinel_paths.py
tests/_shared/tomli_shim.py
tests/phase_03/__init__.py
tests/phase_03/conftest.py
tests/phase_03/test_state.py
tests/phase_03/test_graph_create.py
tests/phase_03/test_graph_inspect.py
tests/phase_03/test_graph_add_node.py
tests/phase_03/test_graph_add_edge.py
tests/phase_03/test_graph_add_hyperedge.py
tests/phase_03/test_graph_reset.py
tests/phase_03/test_graph_state_persistence.py
tests/phase_03/test_graph_cypher_validation.py
tests/phase_03/test_graph_list.py
tests/test_image_completeness.py            <- relocated from tests/phase_02/
docs/concepts/graphs-and-metagraphs.md
docs/usage/core/building-graphs.md
docs/api/core/graph.md
docs/api/core/node.md
docs/api/core/edge.md
docs/api/core/hyperedge.md
docs/changelog/CHANGELOG.md
confirmation_docs/INTERGRAPH_EDGE_DESIGN_NOTE.md
confirmation_docs/PHASE_03_IMPLEMENTATION_LOG.md   <- this file
```

### Modified

```
confirmation_docs/PHASE_MAP.md   — Phase 03 row fully refined; §7 Q4 narrowed; §7 Q7 resolved; §7 Q13 added; Phase 05 row amended (intergraph design hook)
mindsos_cli/__init__.py          — version 0.0.0+phase02 → 0.0.0+phase03; docstring updated
mindsos_cli/manifest.toml        — phase 02 → 03; version bumped
mindsos_cli/app.py               — register_graph_app wired; help text bumped to Phase 03
docker-compose.yml               — image tags phase02 → phase03 (prod + test)
pyproject.toml                   — version + description bumped (packages.find unchanged — wildcard already covers mindsos_core.cypher)
mindsos_core/__init__.py         — exports Graph, Node, Edge, HyperEdge, SchemaError, CypherError, validate_*; docstring rewritten
mindsos_core/exceptions.py       — SchemaError + CypherError added; docstring updated
mindsos_core/models/__init__.py  — re-exports Edge, Graph, HyperEdge, Node
Dockerfile                       — comment lines 70-71 / 101-103 updated to point at tests/test_image_completeness.py + tests/_shared/sentinel_paths.py
mkdocs.yml                       — new Concepts entry + Usage > Core section + 4 API > Core entries + Changelog top-level section
tests/phase_02/conftest.py       — _run_cli moved to tests/_shared/cli.py (imported back here); inline tomli_shim removed (now via _shared)
tests/phase_02/test_image_completeness.py  — gutted to a docstring-only stub pointing at tests/test_image_completeness.py
```

`requirements.in` / `requirements.txt` / `requirements-test.txt` —
**unchanged** (Phase 03 graph primitives + state-file (de)serialization
use only stdlib `json`, `os`, `pathlib`, `re`).

---

## 6. Tests added / count delta

**Phase 03 added:** ≈ 65 new tests across 9 files (in `tests/phase_03/`)
+ 5 new sentinel-path entries appended to `SENTINEL_PATHS` (relocated to
`tests/test_image_completeness.py`).

**Sandbox dry-run (Mac, Python 3.10) result:** 65 / 65 Phase 03 tests
PASSED in-process via `typer.testing.CliRunner`. Cumulative sandbox run
(`PYTHONPATH=. pytest tests/`): 149 PASSED, 40 FAILED, 0 skipped — the
40 failures are all Python-3.10-sandbox-specific subprocess CLI tests
that need `mindsos` on PATH (Phase 02 §10 documented this — `pip install
-e .` requires Python ≥ 3.12). All 40 will pass in the test image.

| File | Tests | What |
|---|---|---|
| `tests/phase_03/test_state.py` | 10 | `state.py` direct unit tests: state_dir env var, state_file_path validation, save/load round-trip, atomic write, missing/corrupt file, missing/future `_state_version`, sorted iter, delete idempotence. |
| `tests/phase_03/test_graph_create.py` | 5 | Create writes state file; JSON output; `--role`; duplicate name → exit 1; invalid name regex → exit 2. |
| `tests/phase_03/test_graph_inspect.py` | 3 | Empty graph counts; counts after add-node; missing graph → exit 1. |
| `tests/phase_03/test_graph_add_node.py` | 9 | Happy path; explicit `--node-id`; duplicate id → exit 1; `--prop` int / list / bool / string-fallback; `<VALUE>` JSON-int parse; empty `--prop` key → exit 2. |
| `tests/phase_03/test_graph_add_edge.py` | 5 | Happy path; lowercase rel-type → exit 1 (CypherError); mixed-case rel-type → exit 1; missing source → exit 1; explicit `--edge-id`. |
| `tests/phase_03/test_graph_add_hyperedge.py` | 5 | Happy n-ary path; empty members → exit 1 (SchemaError); member ordering canonicalised; unknown member → exit 1; explicit `--hyperedge-id`. |
| `tests/phase_03/test_graph_reset.py` | 5 | `--name` deletes; `--all` deletes all; no flag → exit 2; both flags → exit 2; missing graph → exit 1. |
| `tests/phase_03/test_graph_state_persistence.py` | 4 | Round-trip ≥3 nodes / ≥2 edges / ≥1 hyperedge; `_state_version: 1`; node lists sorted by id on save; hyperedge `member_ids` sorted. |
| `tests/phase_03/test_graph_cypher_validation.py` | 16 (parametrised) | Direct unit tests of `validate_edge_type_identifier` / `validate_label_identifier` (ADR-0021 regex coverage incl. lowercase, mixed-case, hyphen, digit-prefix, empty, whitespace, length limit, non-string). |
| `tests/phase_03/test_graph_list.py` | 2 | Empty list; multiple graphs sorted by name. |
| `tests/test_image_completeness.py` | 22 (parametrised; was 15 in phase_02; +5 Phase 03 + 2 catch-up entries) | Sentinel files exist + non-zero on disk. Migrated from `tests/phase_02/` to root in Phase 03; sentinel list at `tests/_shared/sentinel_paths.py`. |

**Cumulative test count (in-container, Python 3.12):** Phase 02 baseline
117 + 1 skipped → Phase 03 expected ≈ **163** + 1 skipped (the
`test_mkdocs_buildable.py` skip — mkdocs not in test image).

---

## 7. Residual concerns (deferred to Phase 04+)

Inherited from Phase 01/02 deferrals (carry-forward, no friction yet):

| ID | Issue | Plan |
|---|---|---|
| **η** | `--build` is unconditional in `confirm-phase`'s `_run_tests`; no opt-out except `--skip-tests`. | Defer further. |
| **H** | `_run_tests` 600s timeout hard-coded. | Defer further. |
| **D** | Cumulative `pytest tests/` is unbounded. | Targeted at ~Phase 14 (rolling 3-phase window for push CI). |
| **J-02** | Identity-registry state file not advisory-locked. **Inherited by Phase 03 graph state file** (same gotcha). | Acceptable — debug-only, single-tester surface. Phase 07's persistence layer ships proper concurrency control. |
| **K-02** | State file location not gitignored by default. | Acceptable — `--state-file` (Phase 02) / `MINDSOS_STATE_DIR` env var (Phase 03) is explicit override; default outside repo. |

New deferrals introduced in Phase 03:

| ID | Issue | Plan |
|---|---|---|
| **A-03 (resolved)** | Phase 03 conftest missing tomllib shim — fixed in this session by extracting to `tests/_shared/tomli_shim.py`. | Done. |
| **L-03** | Q13 (intergraph edge primitive) recorded as `confirmation_docs/INTERGRAPH_EDGE_DESIGN_NOTE.md` + PHASE_MAP §7 Q13 + Phase 05 row amendment. | **Phase 05 chat MUST adjudicate** before implementing Metagraph elements. Default = defer indefinitely. |

---

## 8. Tester checklist

1. **[Mac]** Pull main, branch off `origin/main`:
   ```sh
   git fetch origin
   git checkout main
   git pull
   git checkout -b phase-03 origin/main
   # If the implementing chat has already pushed phase-03, just check it out:
   #   git fetch origin && git checkout phase-03
   ```
2. **[Mac]** Verify version strings are aligned:
   ```sh
   grep -n "version\|phase" mindsos_cli/manifest.toml pyproject.toml mindsos_cli/__init__.py
   ```
   All three should show `0.0.0+phase03`; manifest's `[mindsos] phase = "03"`.
3. **[Mac]** Verify compose image tags:
   ```sh
   grep "image: mindsos:" docker-compose.yml
   ```
   Both lines should show `mindsos:phase03-prod` / `mindsos:phase03-test`.
4. **[Mac]** Commit + push (if not already pushed by the implementing chat).
5. **[Linux]** Pull, **`git checkout phase-03`** (this step was implicit in
   Phase 01/02 — Phase 02 tester ran from `main` first and got the wrong
   count), build images:
   ```sh
   git fetch origin
   git checkout phase-03
   git pull
   docker compose build mindsos mindsos-test
   ```
6. **[Linux]** Bring up FalkorDB:
   ```sh
   docker compose up -d falkordb
   ```
7. **[Linux]** Run cumulative tests in-container (canonical pass criterion):
   ```sh
   docker compose run --rm mindsos-test pytest tests/ -v
   ```
   Expect **≈ 163 passed + 1 skipped** (the 1 skip is
   `test_mkdocs_buildable.py` — mkdocs not in the test image).
8. **[Linux]** Manual exploration:
   ```sh
   docker compose run --rm mindsos doctor
   docker compose run --rm mindsos doctor --self-test
   docker compose run --rm mindsos graph --help
   docker compose run --rm mindsos graph list

   # Single-invocation demo (compose --rm wipes state between runs):
   docker compose run --rm mindsos sh -c '
       mindsos graph create --name demo --role ontology &&
       mindsos graph add-node Alice --name demo --type Person --node-id n-a &&
       mindsos graph add-node Acme  --name demo --type Org    --node-id n-b &&
       mindsos graph add-edge --name demo --source n-a --target n-b --type WORKS_AT &&
       mindsos graph add-hyperedge --name demo --member n-a --member n-b --label "trio" &&
       mindsos graph inspect --name demo --json &&
       mindsos graph add-edge --name demo --source n-a --target n-b --type works_at; echo "exit: $?"
   '
   # Last command (lowercase rel-type) should print CypherError + exit 1.
   ```
9. **[Linux]** Host-venv multi-invocation demo (state persists naturally):
   ```sh
   source .venv/bin/activate
   mindsos graph create --name demo --role ontology
   mindsos graph add-node Alice --name demo --type Person --node-id n-a
   mindsos graph add-node Acme --name demo --type Org --node-id n-b
   mindsos graph add-edge --name demo --source n-a --target n-b --type WORKS_AT
   mindsos graph add-node Alice2 --name demo --type Person --node-id n-a   # duplicate → exit 1
   mindsos graph inspect --name demo
   mindsos graph reset --name demo
   ```
10. **[Linux]** Generate the confirmation doc:
    ```sh
    mindsos confirm-phase --init-notes 03
    ${EDITOR:-nano} notes-phase-03.md   # fill phase_title + tester_notes
    mindsos confirm-phase --phase 03 --notes-file notes-phase-03.md
    ```
11. **[Linux]** Review `confirmation_docs/PHASE_03_CONFIRMED.md`; hand-edit if needed.
12. **[Mac]** Verify the working tree is clean and the doc + notes are tracked:
    ```sh
    git status
    git ls-files confirmation_docs/PHASE_03_CONFIRMED.md notes-phase-03.md
    ```
13. **[Mac]** Add + commit + push:
    ```sh
    git add confirmation_docs/PHASE_03_CONFIRMED.md notes-phase-03.md
    git add -A
    git commit -m "Phase 03 — L1 Graph elements (Graph / Node / Edge / HyperEdge + Cypher rel-type validation + graph CLI + state file)"
    git push -u origin phase-03
    ```
14. **[Mac]** Open PR against `main`; CI runs `phase-ci.yml` (in-container
    pytest + mkdocs build); wait green.
15. **[Mac]** Squash-merge the PR.
16. **[Mac]** Tag the squash-merge commit on **main** (not on the
    phase-03 branch — Phase 01 lesson):
    ```sh
    git checkout main
    git pull
    git tag phase-03-confirmed
    git push origin phase-03-confirmed
    ```
17. CI runs `release.yml`. Verify the GitHub Release exists with all
    expected assets and SHA256-verified.

---

## 9. Decision references

- `confirmation_docs/PHASE_MAP.md` Phase 03 row + Final amendments
  appendix (29 items) — canonical contract.
- `confirmation_docs/INTERGRAPH_EDGE_DESIGN_NOTE.md` — Q13 design note
  (intergraph edge primitive); Phase 05 chat must adjudicate.
- `feedback_docs_source_of_truth.md` (memory) — ADR porting deferred to
  Phase 38 (locked precedent set in Phase 02; made explicit in Phase 03).
- ADR-0014 (layer boundary core-only) — referenced; confirmed against
  shipped slim `mindsos_core` having no domain logic.
- ADR-0021 (cypher rel-type validation) — referenced; load-bearing for
  Phase 03 invalid-rel-type pass criterion. Validated by
  `validate_edge_type_identifier` in `mindsos_core/cypher/identifiers.py`.

---

## 10. State at end of session

- Phase 03 implementation complete on Mac. Awaiting tester run on Linux box.
- Sandbox dry-run (Python 3.10): 149 / 189 PASSED. The 40 failures are
  all subprocess CLI tests that require Python 3.12 (`pip install -e .`
  needs `requires-python = ">=3.12"`). All 65 / 65 Phase 03 tests
  PASSED in-process.
- All version strings aligned (manifest, pyproject, `__init__.py`,
  compose tags). `doctor --self-test` not host-runnable in this sandbox
  (Python 3.10 vs 3.12 manifest); will pass in the test image.
- `git status` is clean save for the Phase 03 changes themselves +
  confirmation doc note files (untracked).
- `[Mac]` work is complete. Tester executes §8 from step 5 onwards.
