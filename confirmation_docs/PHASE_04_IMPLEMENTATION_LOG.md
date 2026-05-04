# Phase 04 — Implementation Log

> Curated record of the Phase 04 design + implementation session
> (2026-05-04). Captures locked decisions, the Phase 04 row refinements,
> bug ledger, files touched, tests added, residual concerns, and the
> tester checklist. Read in conjunction with `PHASE_MAP.md` Phase 04
> row + the eventual `PHASE_04_CONFIRMED.md`.

This log reflects the **5-round design adversarial pushback process**:
each round surfaced gaps that the next round addressed, with
explicit options + picks for every contested decision. The phase
entered implementation only after the pushback rounds reached
diminishing returns.

---

## 1. Charter

Phase 04 = **L1 Schema** (slim port of `mindsos_core/schema/` from the
parent project: `Schema` / `NodeType` / `EdgeType` / `PropertyType` +
property-bag validation). Adds `mindsos schema` CLI subapp with own
state file. Wires schema integration into Phase 03 graph CLI: `graph
create --schema`, `graph attach-schema`, `graph detach-schema`,
`graph set-prop`. Closes 4 entries from Phase 03's slim-port deferral
appendix.

**Phase 04 also bumps the graph state-file format from v=1 to v=2** —
Phase 03 testers' existing `~/.mindsos/graph-*.json` files migrate
one-way on first Phase 04 mutation.

---

## 2. Scope adjudications (decided across 5 design rounds)

| # | Question | Decision | Rationale |
|---|---|---|---|
| 2.1 | Schema CLI shape: standalone `mindsos schema ...` vs flag on `graph create` only | **Standalone subapp PLUS `--schema` flag on `graph create` PLUS `attach-schema` PLUS `detach-schema`.** | Schemas are reusable across graphs; needs its own CRUD surface. Parity with Phase 02 (`identity`) and Phase 03 (`graph`). |
| 2.2 | Schema persistence: own state file vs embedded | **Own state file `schema-<name>.json` + optional `schema_name` field on graph state file.** | Schema reuse across graphs is the primary use case. Embedded would force duplication. |
| 2.3 | Property type vocab: subset (4 primitives) vs full (8 incl. lists) | **Full 8-variant enum from parent.** | Splitting forward-debts to Phase 05+. The variants are paired in one Enum; cherry-picking creates drift. |
| 2.4 | Schema attach validation: eager / lazy / eager+`--force` | **Eager. NO `--force` escape hatch.** First violation exits 1 with offending element id; graph state file unchanged. | Lazy hides corruption. Force is an extra code path future phases must respect. Eager is the only honest answer. |
| 2.5 | `set-prop` shape: single command (mutex flag) vs two commands | **Single command with `--node-id` / `--edge-id` mutex flag**, repeatable `--prop`, `--replace` flag. Renamed from `--node` / `--edge` for parity with `add-node --node-id`. | Fewer subcommands. Easier to extend. Flag-name parity with sibling commands. |
| 2.6 | Cumulative test count target | **No artificial cap — write tests for full coverage; row drops the upfront point estimate (Pick H).** Tester records the actual count in PHASE_04_CONFIRMED. | Estimates were wrong twice (163 vs 189 actual; 235-245 vs 341 actual). Drop the broken mechanism. |
| 2.7 | `_state_version` bump strategy | **Bump GRAPH_STATE_VERSION to 2; split per-kind constants.** Phase 04 binary reads v=1 (legacy) and v=2; writes v=2 always. | One-way migration is the canonical strict-version contract. Phase 03 binary refuses v=2 cleanly per the existing contract. |
| 2.8 | `Schema` ctor signature | **Parent-shape: `__init__(*, strict: bool = False)`. NO `name` field.** | State-file basename is the persistence-layer identity. Don't fork the upstream class. |
| 2.9 | `validate_namespaced_properties` port | **Defer to Phase 05/10.** | ADR-0130 graph-level properties bag still deferred; no Phase 04 caller. |
| 2.10 | `update_*_properties` `_version` bump (ADR-0127) | **Skip — Phase 07 OCC owns it.** | Slim Node has no `_version` field; methods merge/replace only. |
| 2.11 | Eager-attach error: include element id? | **Yes — wrap each `add_*` replay in try/except; prefix message with `<kind> <id>: <ExceptionType>: <message>`.** | Tester needs to know WHICH element violated. Cheap UX win. |
| 2.12 | `set-prop --replace` and `ref:*` keys | **Always preserve existing `ref:*` keys across replace.** User-supplied `ref:*` values overwrite existing on collision. NO CLI path to drop `ref:*` in Phase 04. | Refs are linkage metadata, not user property data. Making them harder to drop is a feature. Phase 09 ships proper ref management. |
| 2.13 | `attach-schema` re-attach | **Permitted; new schema replaces old after eager re-validation.** JSON output reports `previous_schema`. | Tester convenience matches "graph mutations are idempotent-ish". |
| 2.14 | `detach-schema` on a graph with no schema | **Exit 1** — Phase 03 fail-loudly pattern on no-op. | Consistent with `reset --name X` failing on missing X. |
| 2.15 | Empty strict schema attached to a graph | **Eager-attach succeeds (no violations to find), but emit a stderr warning** naming the recovery routes. | Tester would otherwise hit `UnknownTypeError` on every subsequent `add-node` with no clue why. |
| 2.16 | Phase 03 v=1 graphs with reserved-key / non-primitive properties (Phase 03 didn't validate) | **Add `_validate: bool = True` kwarg to `Graph.add_*`; rehydration uses `_validate=False` to tolerate legacy data; mutations validate as normal; recovery via `set-prop --replace`.** | Phase 03 didn't have `validate_user_properties`; Phase 04 enforcing it on rehydration would silently brick Phase 03 graphs. The kwarg makes the legacy-tolerance explicit and bounded. |
| 2.17 | Corrupt `PropertyType` vocab in schema state file | **Wrap `PropertyType(v)` in try/except in `_state_to_schema`; raise RuntimeError → exit 1 with valid vocab listed.** | Bare ValueError = Python traceback for the tester. Match the strict-version-error pattern. |
| 2.18 | `schema reset` orphan check | **Both `--name X` and `--all` walk every graph state file checking `schema_name`; refuse with exit 1 if any orphan would result; `--force` overrides.** | Default-safe matches every other destructive command. Force is the explicit escape hatch. |
| 2.19 | `mindsos graph list` / `schema list` version-check | **Bypass deliberate** — read JSON directly so future-version files appear in listings rather than hidden. Mutating commands DO use the strict loader. | Inclusive listing is correct; strictness here would harm UX. |

---

## 3. Locked decisions (final, post-iteration — 18 row-appendix items)

The full list lives in PHASE_MAP Phase 04 row "Final amendments
(2026-05-04)". Highlights:

| # | Decision |
|---|---|
| 1 | Slim port `mindsos_core/schema/{__init__,types,schema,validation}.py` from parent. `validate_namespaced_properties` deferred to Phase 05/10. |
| 2 | `Schema` ctor stays parent-shape. State-file basename is identity. |
| 3 | Full 8-variant `PropertyType` enum ported. |
| 4 | New exceptions: `PropertyShapeError`, `UnknownTypeError`. Both inherit `CoreError`. |
| 5 | Eager attach validation; offending element id in error message; re-attach permitted; empty-strict warning. |
| 6 | `set-prop` single command, `--node-id` / `--edge-id` mutex, `--prop` repeatable, `--replace` preserves `ref:*` (user values win on collision). |
| 7 | **Graph state-file BUMPED to v=2** (`GRAPH_STATE_VERSION = 2`). One-way migration. Per-kind constants split (`SCHEMA_STATE_VERSION = 1`). |
| 8 | Schema state-file v=1 schema pinned. NEW2: corrupt `PropertyType` → RuntimeError → exit 1. |
| 9 | **`Graph.add_*` gain `_validate: bool = True` kwarg.** Rehydration `_validate=False`; mutations keep `_validate=True`; recovery via `set-prop --replace`. |
| 10 | **`graph detach-schema`** ships in Phase 04. Raw-JSON path; works on dangling references. Exits 1 if no schema attached. |
| 11 | **`schema reset` orphan check + `--force`.** Both `--name` and `--all` gated. |
| 12 | Carry-over deferrals from Phase 03 row that Phase 04 closes: Schema typing on `Graph.__init__`, `validate_user_properties`, `update_*_properties` (no `_version`), `tests/unit/test_graph.py` (14 of 15; 1 skip for `_restore_node`). |
| 13 | Carry-forward deferrals: Graph properties bag → 05/10, Node `_version` OCC → 07, soft-delete → 10, `_restore_*` → 08, Q13 intergraph → Phase 05, ref:* drop UX → Phase 09. |
| 14 | `pyproject.toml [tool.setuptools.packages.find].include` already wildcards `mindsos_core*`. |
| 15 | `Dockerfile` COPY both new modules in prod + test stages. Sentinel-paths: +5 entries. |
| 16 | `requirements.{in,txt}` / `requirements-test.txt` unchanged (stdlib-only). |
| 17 | `mindsos graph list` and `mindsos schema list` deliberately bypass strict version check. |
| 18 | Phase 03 tests updated to reference `state_mod.GRAPH_STATE_VERSION` rather than hard-coded `1`. |

---

## 4. Bug ledger

| ID | Symptom | Root cause | Fix |
|---|---|---|---|
| **B-04** | `schema reset --force` did NOT emit the dangling-references warning when orphans existed. | Initial implementation gated `_find_orphan_referencers` behind `not force` — under `--force`, the orphans list stayed empty. | Always compute `orphan_referencers`; refusal AND warning paths share the data. Surfaced by `test_reset_force_emits_warning_about_dangling`. |
| **B-04-prev** | Phase 03 `test_state_file_has_state_version` and `test_load_future_state_version_rejected` failed under Phase 04. | These tests pinned `_state_version: 1` and the regex `"this CLI supports v1"` — both became stale when Phase 04 bumped to v=2. | Updated both tests to reference `state_mod.GRAPH_STATE_VERSION` dynamically. Per PHASE_MAP §1 "Breaking changes between phases allowed". |

No production bugs surfaced beyond these two test-author oversights.
The 5 design pushback rounds prevented several would-have-been bugs
(e.g. NEW1's `_validate=False` rehydration prevented silent backward-
compat breakage for Phase 03 v=1 graphs with reserved keys).

---

## 5. Files added / modified

### Added (Phase 04)

```
mindsos_core/schema/__init__.py
mindsos_core/schema/types.py
mindsos_core/schema/schema.py
mindsos_core/schema/validation.py
mindsos_cli/commands/schema.py
tests/phase_04/__init__.py
tests/phase_04/conftest.py
tests/phase_04/test_state.py
tests/phase_04/test_schema_create.py
tests/phase_04/test_schema_add_node_type.py
tests/phase_04/test_schema_add_edge_type.py
tests/phase_04/test_schema_inspect.py
tests/phase_04/test_schema_list.py
tests/phase_04/test_schema_reset_orphan.py
tests/phase_04/test_schema_state_round_trip.py
tests/phase_04/test_graph_create_with_schema.py
tests/phase_04/test_graph_attach_schema.py
tests/phase_04/test_graph_detach_schema.py
tests/phase_04/test_graph_set_prop.py
tests/phase_04/test_property_validation.py
tests/phase_04/test_validate_user_properties.py
tests/phase_04/test_legacy_compat.py
tests/unit/test_graph.py                  <- ported from parent (14 of 15; 1 skip)
docs/usage/core/schema.md
docs/api/core/schema.md
docs/api/core/types.md
confirmation_docs/PHASE_04_IMPLEMENTATION_LOG.md   <- this file
```

### Modified

```
confirmation_docs/PHASE_MAP.md   — Phase 04 row fully refined; 18-item final amendments appendix
mindsos_cli/__init__.py          — version 0.0.0+phase03 → 0.0.0+phase04; docstring updated
mindsos_cli/manifest.toml        — phase 03 → 04; version bumped
mindsos_cli/app.py               — register_schema_app wired; help text bumped to Phase 04
mindsos_cli/state.py             — schema_file_path / save_schema_state / load_schema_state /
                                   delete_schema_state_file / iter_schema_files. Per-kind version
                                   constants split: GRAPH_STATE_VERSION=2, SCHEMA_STATE_VERSION=1.
                                   _load_state_file accepts max_version kwarg. STATE_VERSION
                                   alias kept for backward-compat = GRAPH_STATE_VERSION.
mindsos_cli/commands/graph.py    — attach-schema (per-element try/except + element id in error +
                                   re-attach + previous_schema + empty-strict warning),
                                   detach-schema (raw-JSON path), set-prop (--node-id/--edge-id;
                                   --replace preserves ref:*; user values win on collision),
                                   --schema flag on create. _state_to_graph passes _validate=False
                                   to add_*. _graph_to_state writes v=2 always.
mindsos_cli/commands/schema.py   — _state_to_schema wraps PropertyType(v) → RuntimeError.
                                   reset_cmd adds orphan check + --force. _schema_to_state uses
                                   SCHEMA_STATE_VERSION.
mindsos_core/__init__.py         — exports Schema, NodeType, EdgeType, PropertyType,
                                   PropertyShapeError, UnknownTypeError, validate_user_properties,
                                   RESERVED_PROPERTY_KEYS, REF_PROPERTY_PREFIX (~9 new); cumulative ~26
mindsos_core/exceptions.py       — PropertyShapeError + UnknownTypeError added; docstring updated
mindsos_core/models/graph.py     — `schema: Optional[Schema] = None` ctor param restored;
                                   schema validation hooks wired into add_*; update_node_properties /
                                   update_edge_properties added (no _version bump);
                                   `_validate: bool = True` kwarg added to add_node / add_edge /
                                   add_hyperedge. _validated_*_properties helpers gain
                                   validate_user_props kwarg.
docker-compose.yml               — image tags phase03 → phase04 (prod + test)
pyproject.toml                   — version + description bumped (packages.find unchanged)
Dockerfile                       — comment lines updated (Phase 03 / Phase 04 references)
mkdocs.yml                       — Schemas page + 2 new API pages added to nav
docs/usage/core/building-graphs.md  — schema integration callout, v=2 schema, set-prop flag rename
docs/changelog/CHANGELOG.md      — Phase 04 entry rewritten with full feature list
tests/_shared/sentinel_paths.py  — 5 new entries (mindsos_core/schema/* + commands/schema.py)
tests/phase_03/test_graph_state_persistence.py  — test_state_file_has_state_version uses
                                   state_mod.GRAPH_STATE_VERSION (was hard-coded 1)
tests/phase_03/test_state.py     — test_load_future_state_version_rejected uses
                                   state_mod.GRAPH_STATE_VERSION in regex (was hard-coded "v1")
tests/phase_04/test_graph_attach_schema.py  — added re-attach, error-id, empty-strict tests
tests/phase_04/test_graph_set_prop.py       — flag rename + ref:* preservation tests +
                                              legacy-recovery tests
tests/phase_04/test_state.py     — added v=2 round-trip + version-constants split tests
```

`requirements.in` / `requirements.txt` / `requirements-test.txt` —
**unchanged** (Phase 04 schema (de)serialization uses only stdlib
`json`, `os`, `pathlib`, `re`, `enum`, `dataclasses`).

---

## 6. Tests added / count delta

**Phase 04 added:** ~16 test files in `tests/phase_04/` + 1 ported file
in `tests/unit/test_graph.py` + 5 new sentinel-path entries.

**Sandbox cumulative result (Mac, Python 3.10):**

* **339 passed + 40 failed (subprocess CLI on 3.10) + 1 skipped + 1 collection error (redis).**
* The 40 failures are documented Phase 02/03 sandbox quirks (Python
  3.10 vs 3.12 + `pip install -e .`). All pass in-container.
* Cumulative collected: **380 (sandbox) + 1 redis-only-in-3.12 = 381**.

**In-container expected (Python 3.12):** **≈ 379 passed + 2 skipped.**
The 2 skips: existing `test_mkdocs_buildable.py` (mkdocs not in test
image) + new `test_restore_node_registers_provided_id` (deferred to
Phase 08).

**Tester records the post-collection actual count** in
`PHASE_04_CONFIRMED.md` `tester_notes`. The PHASE_MAP row no longer
carries an upfront point estimate (Pick H).

---

## 7. Residual concerns (deferred to Phase 05+)

Inherited from Phase 01/02/03 deferrals (carry-forward):

| ID | Issue | Plan |
|---|---|---|
| **η** | `--build` is unconditional in `confirm-phase`. | Defer further. |
| **H** | `_run_tests` 600s timeout hard-coded. | Defer further. |
| **D** | Cumulative `pytest tests/` is unbounded. | Targeted at ~Phase 14 (rolling 3-phase window). |
| **J-02** | Graph state file not advisory-locked. **Phase 04 inherits the same gotcha for schema state file.** | Acceptable — debug-only, single-tester surface. Phase 07's persistence layer ships proper concurrency control. |
| **K-02** | State-file location not gitignored by default. | Acceptable — `MINDSOS_STATE_DIR` override is explicit; default outside repo. |
| **L-03 (Phase 03)** | Q13 intergraph edge primitive. | **Phase 05 chat MUST adjudicate.** Phase 04 did NOT touch. |

New deferrals introduced in Phase 04:

| ID | Issue | Plan |
|---|---|---|
| **M-04** | `_validate=False` rehydration kwarg on `Graph.add_*` is a Phase 04 bridge for Phase 03 backward-compat. | Phase 08's `_restore_*` reconstruction helpers will subsume this kwarg; Phase 04 tolerance becomes the canonical "restore" mode there. |
| **N-04** | `attach-schema` eager replay is O(N); no `--dry-run` to surface ALL violations in one pass. | Acceptable for Phase 04 testers; flag for Phase 14+ if DOLCE-scale (~150k nodes) becomes a friction point. |
| **O-04** | `update_node_properties` does not bump any `_version`. Phase 07 OCC will need to retro-fit. | Acknowledged — ADR-0127 owns the migration. |
| **P-04** | No CLI path to drop a `ref:*` key (Pick D + NEW6 deferred). Recovery via hand-edit. | Phase 09 XRef migration (ADR-0142) ships proper ref management. |
| **Q-04** | v=1 → v=2 graph state file migration is one-way. Phase 04 supersession requires `rm -rf ~/.mindsos/graph-*.json` OR manual JSON downgrade. | Documented in `docs/usage/core/schema.md` "Migration from Phase 03" + PHASE_MAP Phase 04 "Risks". Tester accepts the contract. |
| **R-04** | Schema state-file persistence is genuinely net-new design (parent has no analogue). | Phase 07 real persistence will likely supersede or migrate this format. Acknowledged in PHASE_MAP Net-new line. |

---

## 8. Tester checklist

1. **[Mac]** Pull main, branch off `origin/main`:
   ```sh
   git fetch origin
   git checkout main
   git pull
   git checkout -b phase-04 origin/main
   ```
2. **[Mac]** Verify version strings are aligned:
   ```sh
   grep -n "version\|phase" mindsos_cli/manifest.toml pyproject.toml mindsos_cli/__init__.py
   ```
   All three should show `0.0.0+phase04`; manifest's `[mindsos] phase = "04"`.
3. **[Mac]** Verify compose image tags:
   ```sh
   grep "image: mindsos:" docker-compose.yml
   ```
   Both lines should show `mindsos:phase04-prod` / `mindsos:phase04-test`.
4. **[Mac]** Commit + push.
5. **[Linux]** Pull, checkout, build:
   ```sh
   git fetch origin
   git checkout phase-04
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
   Expect **≈ 379 passed + 2 skipped** (1 mkdocs, 1 `_restore_node`).
   Confirm exact count from the pytest summary; record in
   `PHASE_04_CONFIRMED.md` `tester_notes`.
8. **[Linux]** Manual exploration (single-invocation form because compose `--rm` wipes state):
   ```sh
   docker compose run --rm mindsos doctor
   docker compose run --rm mindsos doctor --self-test
   docker compose run --rm mindsos schema --help
   docker compose run --rm mindsos graph --help

   # Full Phase 04 happy path:
   docker compose run --rm --entrypoint /bin/sh mindsos -c '
       mindsos schema create --name people --strict &&
       mindsos schema add-node-type --schema people --type-name Person --prop-type age=int &&
       mindsos schema add-node-type --schema people --type-name Org &&
       mindsos schema add-edge-type --schema people --type-name WORKS_AT \
           --allowed-source Person --allowed-target Org &&
       mindsos schema inspect --name people --json &&
       mindsos graph create --name folks --schema people &&
       mindsos graph add-node Alice --name folks --type Person --node-id n-a --prop age=30 &&
       mindsos graph add-node Acme  --name folks --type Org    --node-id n-b &&
       mindsos graph add-edge --name folks --source n-a --target n-b --type WORKS_AT &&
       mindsos graph set-prop --name folks --node-id n-a --prop city=NYC &&
       mindsos graph inspect --name folks --json &&
       mindsos graph add-node Bob --name folks --type Person --prop age=thirty;
       echo "exit (strict prop-type mismatch): $?"
   '
   # Last command should print PropertyShapeError with the offending id + exit 1.

   # Phase 04-specific recovery flows:
   docker compose run --rm --entrypoint /bin/sh mindsos -c '
       # detach-schema recovery from dangling reference:
       mindsos schema create --name s &&
       mindsos schema add-node-type --schema s --type-name T &&
       mindsos graph create --name g --schema s &&
       mindsos schema reset --name s --force &&
       mindsos graph inspect --name g; echo "exit (dangling): $?" &&
       mindsos graph detach-schema --name g &&
       mindsos graph inspect --name g
   '

   # Re-attach swap:
   docker compose run --rm --entrypoint /bin/sh mindsos -c '
       mindsos schema create --name s1 &&
       mindsos schema add-node-type --schema s1 --type-name T &&
       mindsos schema create --name s2 --strict &&
       mindsos schema add-node-type --schema s2 --type-name T &&
       mindsos graph create --name g --schema s1 &&
       mindsos graph add-node x --name g --type T &&
       mindsos graph attach-schema --name g --schema s2 --json
   '
   # JSON output should report previous_schema=s1, schema_name=s2.

   # Empty-strict-schema warning:
   docker compose run --rm --entrypoint /bin/sh mindsos -c '
       mindsos schema create --name empty --strict &&
       mindsos graph create --name g &&
       mindsos graph attach-schema --name g --schema empty
   '
   # Should emit "warning: schema 'empty' is strict but declares zero NodeTypes..."
   ```
9. **[Linux]** Host-venv migration test (state persists naturally):
   ```sh
   source .venv/bin/activate
   # Simulate a Phase 03 v=1 file by hand:
   cat > ~/.mindsos/graph-legacy.json <<EOF
   {"_state_version": 1, "graph_id": "abc", "name": "legacy", "role": null,
    "nodes": [{"node_id": "n-a", "value": "Alice", "type_name": "Person",
               "properties": {"id": "evil-legacy", "name": "Alice"}}],
    "edges": [], "hyperedges": []}
   EOF
   mindsos graph inspect --name legacy --json    # exit 0 (loads v=1)
   mindsos graph set-prop --name legacy --node-id n-a --prop city=NYC
   # Should fail because 'id' is reserved in the merged candidate.
   mindsos graph set-prop --name legacy --node-id n-a --prop name=Alice --replace
   # Should succeed; reserved 'id' stripped.
   cat ~/.mindsos/graph-legacy.json | grep _state_version
   # Should now show "_state_version": 2 (one-way migration).
   ```
10. **[Linux]** Generate the confirmation doc:
    ```sh
    mindsos confirm-phase --init-notes 04
    ${EDITOR:-nano} notes-phase-04.md   # fill phase_title + tester_notes
    mindsos confirm-phase --phase 04 --notes-file notes-phase-04.md
    ```
11. **[Linux]** Review `confirmation_docs/PHASE_04_CONFIRMED.md`; hand-edit if needed.
12. **[Mac]** Verify the working tree is clean and the doc + notes are tracked:
    ```sh
    git status
    git ls-files confirmation_docs/PHASE_04_CONFIRMED.md notes-phase-04.md
    ```
13. **[Mac]** Add + commit + push:
    ```sh
    git add confirmation_docs/PHASE_04_CONFIRMED.md notes-phase-04.md
    git add -A
    git commit -m "Phase 04 — L1 Schema (NodeType/EdgeType + opt-in strict + attach/detach + set-prop + v=2 state-file bump)"
    git push -u origin phase-04
    ```
14. **[Mac]** Open PR against `main`; CI runs `phase-ci.yml`; wait green.
15. **[Mac]** Squash-merge the PR.
16. **[Mac]** Tag the squash-merge commit on **main** (not on the
    phase-04 branch — Phase 01 lesson):
    ```sh
    git checkout main
    git pull
    git tag phase-04-confirmed
    git push origin phase-04-confirmed
    ```
17. CI runs `release.yml`. Verify the GitHub Release exists with all
    expected assets and SHA256-verified.

---

## 9. Decision references

- `confirmation_docs/PHASE_MAP.md` Phase 04 row + Final amendments
  appendix (18 items) — canonical contract.
- `feedback_docs_source_of_truth.md` (memory) — ADR porting deferred to
  Phase 38 (locked precedent set in Phase 02 / 03).
- ADR-0017 (NodeType / EdgeType vocabulary) — referenced; ADR file
  ports in Phase 38. Phase 04 confirms against shipped behaviour:
  `NodeType` / `EdgeType` are frozen dataclasses with optional
  `property_types` / `allowed_sources` / `allowed_targets`.
- ADR-0021 (Cypher rel-type validation) — referenced; re-applied at
  edge-type registration time in Phase 04 by `Schema.add_edge_type`.
- ADR-0014 (layer boundary core-only) — referenced; Phase 04 keeps
  `mindsos_core.schema` purely typological — no domain logic, no I/O.
- ADR-0127 (OCC `_version`) — referenced; Phase 04 deliberately does
  NOT bump `_version` on `update_*`. Phase 07 owns the migration.
- ADR-0130 (graph-level properties bag) — deferred to Phase 05/10.
- ADR-0133 (soft-delete via `deprecated_at` / `disputed_at`) —
  deferred to Phase 10; Phase 04 reserves the keys via
  `RESERVED_PROPERTY_KEYS`.
- ADR-0142 (XRef cutover) — referenced; Phase 09 owns proper ref
  management including drop semantics (Pick NEW6 deferred there).

---

## 10. State at end of session

- Phase 04 implementation complete on Mac. Awaiting tester run on
  Linux box.
- Sandbox dry-run (Python 3.10): **339 passed + 40 failed (subprocess
  on 3.10) + 1 skipped + 1 collection error (redis)**. Cumulative
  collected: 380 sandbox / 381 in-container.
- All 5 design pushback rounds (12 + 3 + 7 + 5 + 1 = 28 distinct
  pushbacks) addressed; remaining concerns filed as residual
  M-04 through R-04.
- All version strings aligned (manifest, pyproject, `__init__.py`,
  compose tags). `doctor --self-test` not host-runnable in the Mac
  sandbox (Python 3.10 vs 3.12 manifest); will pass in the test image.
- `pyproject.toml [tool.setuptools.packages.find].include` already
  wildcards `mindsos_core*` — auto-covers the new
  `mindsos_core.schema`. No edit needed.
- `[Mac]` work is complete. Tester executes §8 from step 5 onwards.
