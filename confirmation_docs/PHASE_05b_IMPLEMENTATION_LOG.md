# Phase 05b — Implementation Log

> Companion to `confirmation_docs/PHASE_MAP.md` Phase 05b row.
> Written by the implementing chat (2026-05-05; row locked across 6
> reanalysis rounds in the same chat). Tester reads this along with the
> row before kicking off `confirm-phase --phase 05b`.

---

## 1. Charter

Goal: ship the binary `IntergraphEdge` primitive (ADR-0148 first draft),
the `IntergraphEdgeType` schema vocabulary, and the `MetagraphSchema`
container — plus a new top-level `mindsos metagraph-schema` CLI subapp
parallel to `mindsos schema`, plus 5 new subcommands on
`mindsos metagraph` (add-intergraph-edge, remove-intergraph-edge,
list-intergraph-edges, attach-schema, detach-schema), plus the 4-way
mutex on `set-prop` (Pushback 27-A extends 05a's 3-way), plus the
metagraph state-file v=1 → v=2 cumulative one-way migration, plus the
new `metagraph-schema-<n>.json` v=1 state-file kind.

Per CASC-1 strict-sequential cascade, this unblocks Phase 05c
(`IntergraphHyperEdge` + `IntergraphHyperEdgeType` + `MetaEdgeType` +
`MetaHyperEdgeType` per Pushback 1-C narrowing).

**Out of scope** (carry-forward — picked up in subsequent phases):

* `IntergraphHyperEdge` (n-ary) — Phase 05c.
* `IntergraphHyperEdgeType` — Phase 05c.
* `MetaEdgeType` + `MetaHyperEdgeType` — Phase 05c (Pushback 1-C
  narrowing — moved out of 05b's original stub scope).
* Soft-delete substrate uniformly across all 4 edge variants (Edge /
  HyperEdge / MetaEdge / MetaHyperEdge / IntergraphEdge) — Phase 10.
* `RemovalImpact` + `force=True` on `remove_graph` — Phase 10.
* `Graph.properties` graph-level property bag (ADR-0130) — Phase 10.
* Persistence to FalkorDB (Cypher Pattern B) — Phase 07.
* OCC two-lock canonical ordering for binary intergraph edges — Phase 07
  (05b locks the contract via design doc §3.4; 07 implements).
* XRef cross-metagraph — Phase 09.
* Element instancing (ADR-0024 / ADR-0025) — Phase 06.
* `Graph.role` immutability via `__setattr__` — filed Pushback 25-B as
  future work (cost too high for 05b; would supersede shipped Phase 03).
* `update-intergraph-edge-label` CLI verb — filed Pushback 31-B as
  future work.
* `mindsos metagraph` CLI subapp two-level reorganization — filed
  Pushback 33-B as future work.
* `remove-intergraph-edge-type` (and symmetric retroactive backfix
  across all schema kinds) — filed Pushback 34-B as future work.

---

## 2. Round-1-6 design picks (over and above the 30-item PHASE_MAP §5 row)

The implementing chat ran six rounds of reanalysis on top of the
30-item original PHASE_MAP §5 row. **34 numbered pushbacks** total were
locked, with **4 future-work entries** filed. All 34 picks accepted by
the user; folded into the implementation:

| # | Lock | Decision |
|---|---|---|
| 1-C | Scope narrowing | 05b ships IntergraphEdge primitive + IntergraphEdgeType + MetagraphSchema container ONLY. MetaEdgeType + MetaHyperEdgeType deferred to 05c (alongside IntergraphHyperEdge / IntergraphHyperEdgeType for symmetric typed-edge surface across the metagraph in one phase). |
| 2-A | `compositional` storage | Top-level dataclass field on `IntergraphEdge` AND top-level field in JSON state file. The reserved key `_compositional` is added to `RESERVED_PROPERTY_KEYS` to prevent user-property collision with the future Phase 07 Cypher emit's stamped property name. |
| 3-A | New `mindsos metagraph-schema` subapp | Top-level subapp parallel to `mindsos schema`. Bindings via `mindsos metagraph attach-schema --name MG --schema MS` and `detach-schema --name MG`. |
| 4-A | Role-based graph constraints | `IntergraphEdgeType.allowed_source_graphs` / `allowed_target_graphs` are role-based (`frozenset[str]` of `Graph.role` values). Empty = any role. `Graph.role=None` is unmatchable when constraint non-empty (Python set semantics). |
| 5-A | `MetagraphSchema.strict` semantics | Mirrors Phase 04 `Schema.strict`: gates property-type validation only. Type-existence (`require_intergraph_edge_type`) is mandatory whenever a schema is attached, regardless of `strict`. |
| 6-A | No escape hatch for compositional cascade | Compositional intergraph edges are truly immutable. Tester recovery for a wedged metagraph is `mindsos metagraph reset --name <MG> --force --yes`. No `demote-intergraph-edge` verb. |
| 7-A | Eager attach validation | `Metagraph.attach_schema(MS)` walks every existing `intergraph_edge`, schema-validates each. First violation raises with offending edge_id; no mutation. Atomic precheck. |
| 8-A | Accept 05c heavyweight | Pushback 1-C moved 2 vocabularies to 05c, making 05c the new heavyweight (3 vocabularies + IntergraphHyperEdge primitive). Accept rather than re-supersede 05a (cost too high — 05a is already shipped). |
| 9-A | Eager validation scope | Eager attach validates only against vocabularies the schema carries. In 05b (only `IntergraphEdgeType`), existing metaedges/metahyperedges are NOT validated. Tester re-attaches in 05c when `MetaEdgeType` / `MetaHyperEdgeType` arrive. |
| 10-A | `strict` ships day one | `MetagraphSchema(*, strict=False)` constructor ships from 05b. State-file v=1 carries `strict: <bool>` field. Avoids API churn in 05c. |
| 11-A | Schema reuse across N metagraphs | `MetagraphSchema` is basename-keyed (`metagraph-schema-<name>.json`); metagraph state-file v=2 carries `schema_name: str | null` reference. Multiple metagraphs can attach the same schema. |
| 12-A | One attached at most | `Metagraph.attach_schema(...)` while a *different* schema is attached refuses with `IdentityError("detach first")`. Re-attaching the same schema by name runs fresh validation (Pushback 32-D below). |
| 13-A | Single node-existence check | `add_intergraph_edge` checks `source_node_id in source_graph.nodes` only. Belt-and-suspenders `mg.identity` check is redundant per ADR-0020 unified registry. |
| 14-A | Always mint via `mg.mint_id` | `IntergraphEdge.edge_id` minted via `mg.mint_id("intergraph_edge")` which delegates to `mg.id_strategy`. ADR-0131 pluggability story uniform across 05b. |
| 15-B | Module file layout | NEW files `mindsos_core/models/intergraph_edge.py` (model + helpers) and `mindsos_core/schema/metagraph_schema.py` (schema container). `IntergraphEdgeType` lives in existing `mindsos_core/schema/types.py`. `Metagraph` factory methods stay in `mindsos_core/models/metagraph.py` (extended ~250 lines). |
| 16-A | 14-step validation order | `add_intergraph_edge` runs a locked 14-step validation order; documented in factory docstring. Predictable error UX; future cascade rows inherit. |
| 17-A | Atomic precheck for compositional cascade | `Metagraph.remove_graph` walks all incident `intergraph_edges`; if ANY has `compositional=True` → raise `CompositionalImmutableError` with offending edge_id BEFORE any mutation. State unchanged on raise. |
| 18-A | RESERVED_PROPERTY_KEYS extension | Added `intergraph_edges`, `schema_name`, `_compositional` (only the underscore-prefixed Cypher-property form; the dataclass field name `compositional` is NOT reserved). |
| 19-B | Attach-time role-mismatch warning | CLI `attach-schema` emits stderr warning when schema references roles not satisfied by any contained graph. Non-blocking (model-layer attach succeeds). |
| 20-A | `mindsos metagraph-schema reset` orphan check | Walks every `metagraph-*.json`; refuses with exit 1 if any has `schema_name == X`; `--force --yes` strips back-pointers from referenced metagraphs. Mirror 05a Q6-A + Phase 04 schema reset. |
| 22-A | `__setattr__` immutability override | `IntergraphEdge.__setattr__` enforces `compositional` immutability post-init via an `_initialized` flag. Other field mutations (`label`, `properties`) work normally. ~15 LOC. |
| 23-A | Schema mutation while attached: stderr warning | CLI `add-intergraph-edge-type` walks every metagraph state file; if any has `schema_name == <target>`, emits stderr warning listing them. Tester must re-attach to surface drift. (Phase 04 carry-forward footgun.) |
| 24-hybrid | Empty MetagraphSchema attach semantics | Non-strict empty schema: attach succeeds with stderr warning (no edges to validate against); validates 0 edges. Strict empty schema: any pre-existing intergraph_edges fail at attach (strict + no vocab = empty allow-list). |
| 25-A | `Graph.role` doc-convention immutable | No `__setattr__` enforcement in 05b (would trigger Phase 03 retroactive supersession; cost too high). Filed Pushback 25-B as future work. |
| 26-A | Detach-then-attach incompatible schema | Refuse cleanly per Pushback 7-A eager-validation contract; tester recovery is manual remove-and-re-add (or full reset for compositional-blocked). `--check-only` dry-run deferred to Phase 11. |
| 27-A | 4-way `set-prop` mutex | `mindsos metagraph set-prop` extends 05a's 3-way (`--on-metagraph | --metaedge-id | --metahyperedge-id`) with `--intergraph-edge-id`. When `compositional=True`, refuses with `CompositionalImmutableError`. |
| 28-A + DMS-A | Stale `schema_name` recovery | `mindsos metagraph detach-schema` is a unified command with internal raw-JSON fallback. Schema state file missing → `_state_to_metagraph` sets dangling ref (no raise); normal-path detach clears it. Schema state file malformed → raw-JSON fallback mutates state file directly, bypasses rehydration. |
| 29-A | Eager attach atomicity | Precheck pass over all intergraph_edges; first violation raises with offending edge_id; no mutation to metagraph state file or in-memory metagraph on failure. |
| 30-A | `attach-schema --json` shape | `{metagraph, previous_schema, new_schema, validated_intergraph_edges: <count>}`. Mirror Phase 04 graph attach-schema with the 05b-specific count field added. |
| 31-A | `IntergraphEdge.label` set-at-create | No `update-intergraph-edge-label` verb in 05b; tester recovery is remove-and-re-add with `--intergraph-edge-id <orig>` override. Filed Pushback 31-B as future work. |
| 32-A + 32-D | `attach_schema` API + re-attach semantics | `Metagraph.attach_schema(schema, *, schema_name)` — explicit keyword name. Re-attach with same `schema_name` runs FRESH eager validation (NOT silent no-op); raises if drift surfaces; idempotent at state-file level on all-pass. |
| 33-A | Subapp size accepted | 05b accepts the flat `mindsos metagraph` surface (~18 subcommands; will hit ~22 in 05c, ~30+ in Phase 10). Filed Pushback 33-B (CLI two-level reorganization) as future work. |
| 34-A | No `remove-*-type` verb | Inherits Phase 04 schema-vocabulary gap. Tester recovery for typo'd type is `metagraph-schema reset --name MS --force --yes`. Filed Pushback 34-B (symmetric backfix across all schema kinds) as future work. |
| Test budget | Unlimited per `feedback_test_budget_unlimited.md` | Final Phase 05b in-process count: **145 tests**. Cumulative across phase_03/04/04-v2/05a/05b in-process: **524 tests** (with the 6 phase_05a tests carry-forward updated). Plus root-level `test_image_completeness.py`: 37 tests. CLI subprocess tests in `test_cli_intergraph_edge.py` + `test_cli_metagraph_schema.py` + `test_dms_a.py` are deferred to in-container (require Python 3.12 + installed `mindsos` binary). |

---

## 3. Module changes

### Net-new files (4)

* `mindsos_core/models/intergraph_edge.py` — `IntergraphEdge` dataclass
  + `__setattr__` immutability override (~140 LOC).
* `mindsos_core/schema/metagraph_schema.py` — `MetagraphSchema`
  container + validators (~210 LOC).
* `mindsos_cli/commands/metagraph_schema.py` — new Typer subapp
  with 5 subcommands (~530 LOC).
* `mindsos_cli/migrations/metagraph_schema.py` — migration chain
  (empty in 05b; v=1 current) (~50 LOC).

### Test files (10 + 1 conftest)

* `tests/phase_05b/__init__.py`
* `tests/phase_05b/conftest.py` — fixtures (`mg_with_two_graphs`).
* `tests/phase_05b/test_intergraph_edge.py` — 37 tests.
* `tests/phase_05b/test_intergraph_edge_type.py` — 7 tests.
* `tests/phase_05b/test_metagraph_schema.py` — 24 tests.
* `tests/phase_05b/test_metagraph_schema_attach.py` — 19 tests.
* `tests/phase_05b/test_compositional_cascade.py` — 10 tests.
* `tests/phase_05b/test_state_v2.py` — 16 tests.
* `tests/phase_05b/test_mint_id.py` — 12 tests.
* `tests/phase_05b/test_reserved_keys.py` — 10 tests.
* `tests/phase_05b/test_validation_order.py` — 10 tests.
* `tests/phase_05b/test_cli_intergraph_edge.py` — CLI subprocess tests
  (in-container).
* `tests/phase_05b/test_cli_metagraph_schema.py` — CLI subprocess tests
  (in-container).
* `tests/phase_05b/test_dms_a.py` — DMS-A CLI subprocess tests
  (in-container).

### Touched files

* `mindsos_core/__init__.py` — exports `IntergraphEdge`,
  `IntergraphEdgeType`, `MetagraphSchema`, `CompositionalImmutableError`;
  `__version__` bump.
* `mindsos_core/exceptions.py` — re-adds `CompositionalImmutableError`
  (R3-B 05a stripped it).
* `mindsos_core/schema/__init__.py` — re-exports `IntergraphEdgeType`,
  `MetagraphSchema`.
* `mindsos_core/schema/types.py` — adds `IntergraphEdgeType` frozen
  dataclass next to `NodeType` / `EdgeType` / `HyperEdgeType`.
* `mindsos_core/schema/validation.py` — extends `RESERVED_PROPERTY_KEYS`
  with `intergraph_edges`, `schema_name`, `_compositional` (Pushbacks
  18-A + 6 carry-forward).
* `mindsos_core/models/metagraph.py` — adds `add_intergraph_edge` +
  `remove_intergraph_edge` + `update_intergraph_edge_properties` +
  `iter_intergraph_edges` + `attach_schema` + `detach_schema` +
  `mint_id`; extends `remove_graph` with the Pushback 17-A precheck
  pass for compositional intergraph_edges; adds `intergraph_edges` /
  `schema` / `schema_name` instance state.
* `mindsos_cli/state.py` — adds `METAGRAPH_SCHEMA_STATE_VERSION = 1` +
  `metagraph_schema_file_path` / `iter_metagraph_schema_files` /
  `load_metagraph_schema_state` / `save_metagraph_schema_state` /
  `delete_metagraph_schema_state_file` helpers.
* `mindsos_cli/migrations/metagraph.py` — adds `_v1_to_v2(state)` step
  setting `intergraph_edges: []` + `schema_name: None` defaults;
  `CURRENT_VERSION = 2`.
* `mindsos_cli/commands/metagraph.py` — adds `_metagraph_schema_to_state`
  + `_state_to_metagraph_schema` helpers (used by both the metagraph
  CLI and the new metagraph-schema CLI); extends `_metagraph_to_state`
  + `_state_to_metagraph` to v=2 (intergraph_edges + schema_name); 5
  new subcommands (add-intergraph-edge / remove-intergraph-edge /
  list-intergraph-edges / attach-schema / detach-schema with DMS-A
  fallback); extends `set-prop` to 4-way mutex; extends `inspect` /
  `list` JSON shapes (P10 amendment).
* `mindsos_cli/app.py` — `register_metagraph_schema_app(app)` wired.
* `mindsos_cli/__init__.py` — `__version__ = "0.0.0+phase05b"` +
  module docstring updated.
* `mindsos_cli/manifest.toml` — `[mindsos] phase = "05b"`;
  `version = "0.0.0+phase05b"`.
* `pyproject.toml` — version + description bumped.
* `docker-compose.yml` — image tags `mindsos:phase05b-{prod,test}`.
* `Dockerfile` — comment lines bumped (Phase 05a → Phase 05b
  references); COPY block has the existing wildcards covering the new
  files.
* `tests/_shared/sentinel_paths.py` — **+4 entries**:
  `mindsos_core/models/intergraph_edge.py`,
  `mindsos_core/schema/metagraph_schema.py`,
  `mindsos_cli/commands/metagraph_schema.py`,
  `mindsos_cli/migrations/metagraph_schema.py`.
* `tests/phase_04/test_state.py` — `test_graph_state_version_constants_split`
  updated for `METAGRAPH_STATE_VERSION == 2` (was `1`) + adds
  `METAGRAPH_SCHEMA_STATE_VERSION == 1`.
* `tests/phase_05a/test_migrations.py` — `test_metagraph_chain_at_current_v1`
  → renamed `test_metagraph_chain_v1_migrates_to_current` (now expects
  v=1 input forward-migrated to v=2 with `intergraph_edges=[]` and
  `schema_name=None` defaults populated). `test_metagraph_chain_rejects_forward_version`
  uses `CURRENT_VERSION + 1` dynamically.
* `tests/phase_05a/test_metagraph_inspect_list.py` — both shape-locking
  tests updated for the v=2 P10 extensions (`schema_name` top-level +
  `counts.intergraph_edges` + `intergraph_edges_count` per list entry).

---

## 4. Bug ledger / decisions made during implementation

* **B-05b-1** — `Metagraph.__init__` already had `intergraph_edges`
  field placement to consider. **Resolution**: declared right after
  `metahyperedges` for symmetric ordering with the pre-existing
  metaedges/metahyperedges dicts; `schema` and `schema_name` declared
  after `properties` (the in-memory cached instance lives next to the
  persisted reference).
* **B-05b-2** — `IntergraphEdge.__setattr__` override needed to allow
  `__post_init__` to set `_initialized = True` without recursing into
  the override. **Resolution**: use `object.__setattr__(self, "_initialized", True)`
  inside `__post_init__`. Within `__setattr__`, also use
  `object.__setattr__(self, name, value)` for non-`compositional`
  writes to avoid re-entering custom logic.
* **B-05b-3** — `Metagraph.attach_schema` needed access to source/target
  node `type_name` and graph `role` for the eager validation walk. The
  pre-existing code stored only edge fields; node/graph lookup happens
  via `self.graphs[edge.source_graph_id].nodes[edge.source_node_id]`.
  **Resolution**: nested dict access in the validation loop;
  performance acceptable for in-memory iteration in 05b (Phase 07
  indexes optimize).
* **B-05b-4** — `_state_to_metagraph` rehydration for v=2 metagraph
  state files needed to handle three schema-reference cases:
  (a) `schema_name` is null → no attach; (b) `schema_name` is set and
  schema state file exists → load + attach with eager validation;
  (c) `schema_name` is set but schema state file is missing → set
  dangling reference (DMS-A path; subsequent operations refuse with
  recovery pointer). **Resolution**: try/except on `load_metagraph_schema_state`
  with FileNotFoundError catching the dangling case; RuntimeError
  re-raised with structured DMS-A recovery message.
* **B-05b-5** — DMS-A unified `detach-schema` CLI command needed to
  handle both "schema state file missing" and "schema state file
  malformed" cases. The first case is silently handled by
  `_state_to_metagraph` (sets dangling ref); normal-path detach clears
  it. The second case raises RuntimeError; raw-JSON fallback bypasses
  rehydration. **Resolution**: pre-flight by reading the metagraph
  state file as raw JSON; check `schema_name`; try
  `_state_to_metagraph`; on RuntimeError, mutate raw JSON and write
  atomically.
* **B-05b-6** — Re-attach with same `schema_name` (Pushback 32-D fresh
  validation): the original Pushback 12-A locked "idempotent silent
  no-op" but on round 6 (Pushback 32-D) the lock changed — re-attach
  always re-validates. **Resolution**: `attach_schema` checks
  `self.schema_name is not None and self.schema_name != schema_name`
  for the "different attached" case (refuses with `IdentityError`);
  same-name case falls through to the eager validation walk.
* **B-05b-7** — `Metagraph.add_graph` interaction with attached schema:
  when a graph is added to a schema-attached metagraph, the graph's
  role might not match any `IntergraphEdgeType.allowed_*_graphs`
  constraint. Per Pushback 19-B, this is a non-blocking warning at
  CLI attach time, not at `add_graph` time. **Resolution**: model-layer
  `add_graph` has no schema-validation hook; CLI `attach-schema` walks
  contained graph roles vs schema constraints and emits the warning.
  Per Pushback 25-A, role drift after attach is a documented
  carry-forward footgun (filed 25-B as future work).
* **B-05b-8** — `pytest tests/phase_03 tests/phase_04 tests/phase_04_v2 tests/phase_05a`
  initially had 1 hard-coded `METAGRAPH_STATE_VERSION == 1` (in
  `tests/phase_04/test_state.py:test_graph_state_version_constants_split`)
  + 2 inspect/list shape lockers (in
  `tests/phase_05a/test_metagraph_inspect_list.py`). **Resolution**:
  surgical updates per the row's pre-implementation audit lock
  (PHASE_MAP §5 Phase 05a amendment 21 carry-forward extended to 05b).
  All 524 in-process cumulative tests pass after fixes.

---

## 5. Compositional cascade — recovery patterns

Per Pushback 17-A, `Metagraph.remove_graph` runs an atomic precheck:
walk all incident intergraph_edges; if ANY has `compositional=True`,
raise `CompositionalImmutableError` BEFORE mutation. State unchanged.

Tester recovery flow:

1. Identify the offending compositional edge from the error message.
2. (No path: cannot be removed; cannot be demoted to non-compositional.)
3. `mindsos metagraph reset --name <MG> --force --yes` — destroys the
   entire metagraph state file + strips back-pointers from all
   referenced graphs. Tester rebuilds.

Phase 10 may add a `--force` bypass on `remove_intergraph_edge` (and
on `remove_graph`'s precheck) under the full ADR-0135 surface. Until
then, compositional really means immutable.

---

## 6. Schema mutation while attached — Phase 04 footgun carry-forward

Per Pushback 23-A, `mindsos metagraph-schema add-intergraph-edge-type`
walks every `metagraph-*.json` for `schema_name == <target>`. If any
metagraphs are attached, emits a stderr warning listing them.

The footgun: attached metagraphs do NOT re-validate against the new
vocabulary until tester re-attaches. Existing intergraph_edges may now
violate the (extended) schema silently.

Tester remediation: `mindsos metagraph attach-schema --name <MG> --schema <X>`
on each attached metagraph. Per Pushback 32-D, re-attach with the same
schema name runs fresh validation; surfaces drift.

This carries forward Phase 04's identical pattern (graph-schema
mutation while attached). 05b inherits cleanly. Documentation in
`docs/usage/core/metagraph-schema.md` will track.

---

## 7. DMS-A unified `detach-schema` recovery

Per Pushback 28-A, `mindsos metagraph detach-schema` operates in two
modes via internal fallback:

1. **Normal path**: rehydrate metagraph through `_state_to_metagraph`
   (which loads + attaches the referenced schema if present + well-formed).
   Call `mg.detach_schema()`; persist; refuse if no schema attached.

2. **Raw-JSON fallback (DMS-A)**: if the schema state file is missing,
   `_state_to_metagraph` already handles it gracefully (sets dangling
   ref; no raise). Normal-path detach clears the ref cleanly. Only when
   the schema state file is *malformed* (raises `RuntimeError`) does
   the raw-JSON fallback fire: mutate the metagraph state file
   directly, set `schema_name: None`, write atomically, bypass
   rehydration. Stderr emits `warning: rehydration failed (...);
   falling back to raw-JSON detach (DMS-A — Pushback 28-A).` and JSON
   output carries `used_raw_fallback: true`.

The single tester-facing verb (`mindsos metagraph detach-schema`)
handles both failure modes uniformly. Symmetric with 05a's `mindsos
graph detach-metagraph` (DM-A) for dangling `metagraph_name`
back-pointers.

---

## 8. Forward-compat notes for 05c

Per the §D 05c dry-run appendix in PHASE_MAP §5 Phase 05b row, the
following are pre-resolved:

* **05c will add `intergraph_hyperedges` array to metagraph state file**
  → bump v=2 → v=3. **05b's v=2 shape is forward-compat:** missing
  field defaults to empty array. No 05b change needed.
* **05c's `IntergraphHyperEdgeType` schema vocabulary** + 05c's
  `MetaEdgeType` + `MetaHyperEdgeType` vocabularies all add to
  `MetagraphSchema`. State file v=1 → v=2 in 05c. **05b's MetagraphSchema
  v=1 shape is forward-compat:** missing fields default to empty
  arrays. No 05b change needed.
* **05c's compositional cascade through `Metagraph.remove_graph`**
  extends 05b's precheck pass to also iterate `mg.intergraph_hyperedges`.
  No 05b change needed (additive in 05c).
* **05c's n-lock canonical ordering** for n-ary intergraph hyperedges
  generalizes 05b's two-lock-for-binary contract. Both lock the
  contract; Phase 07 implements both.
* **05c's `IntergraphHyperEdge.compositional`** flag is the same
  `_compositional` reserved key as 05b. **05b's reserved-key addition**
  covers both. No 05b change needed.

---

## 9. Tester instructions

```sh
# [Linux] Tester host venv.
cd halvim_mindsos
git pull origin phase-05b
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e .

# Doctor self-test (static-only; no FalkorDB required).
mindsos doctor --self-test --static-only

# In-container tests.
docker compose run --rm mindsos-test pytest tests/

# Manual exploration: see docs/usage/core/metagraph-schema.md and
# docs/concepts/intergraph-edges.md.

# Confirmation.
mindsos confirm-phase --phase 05b --notes-file notes-phase-05b.md
```

Expected: 145 added Phase 05b in-process tests + cumulative
(528 + 2 skipped from 05a baseline) + 3 CLI subprocess test files
(test_cli_intergraph_edge.py + test_cli_metagraph_schema.py +
test_dms_a.py — these run in-container with the installed `mindsos`
binary). Sandbox-projected cumulative: ~660-700 + 2 skipped in-container.
Tester records actual count in `PHASE_05b_CONFIRMED.md`.

### Manual exploration recipe

```sh
# 1. Two graphs with roles + nodes.
mindsos graph create --name lex --role lexicon
mindsos graph add-node --name lex --node-id n_cat --value cat --type Word
mindsos graph create --name cpt --role concepts
mindsos graph add-node --name cpt --node-id n_concept --value Cat#1 --type Concept

# 2. Metagraph with both graphs.
mindsos metagraph create --name mg
mindsos metagraph add-graph --name mg --graph lex
mindsos metagraph add-graph --name mg --graph cpt

# 3. MetagraphSchema with role-based IntergraphEdgeType.
mindsos metagraph-schema create --name ms1 --strict
mindsos metagraph-schema add-intergraph-edge-type \
    --schema ms1 --type-name EVOKES \
    --allowed-source-type Word --allowed-target-type Concept \
    --allowed-source-graph lexicon --allowed-target-graph concepts \
    --prop-type weight=float

# 4. Attach the schema (eager validation runs).
mindsos metagraph attach-schema --name mg --schema ms1 --json

# 5. Add an intergraph edge satisfying all constraints.
mindsos metagraph add-intergraph-edge \
    --name mg \
    --source-graph lex --source-node n_cat \
    --target-graph cpt --target-node n_concept \
    --type EVOKES --prop weight=0.5

# 6. Inspect the metagraph; observe intergraph_edges count + schema_name.
mindsos metagraph inspect --name mg --json

# 7. Add a compositional edge and observe the immutability.
mindsos metagraph-schema add-intergraph-edge-type \
    --schema ms1 --type-name COMPOSED_OF
mindsos metagraph attach-schema --name mg --schema ms1   # re-attach to surface drift
mindsos metagraph add-intergraph-edge \
    --name mg \
    --source-graph lex --source-node n_cat \
    --target-graph cpt --target-node n_concept \
    --type COMPOSED_OF --compositional
mindsos metagraph remove-intergraph-edge --name mg \
    --intergraph-edge-id <id>   # CompositionalImmutableError (exit 1)

# 8. DMS-A recovery: simulate a missing schema, recover via detach-schema.
rm $MINDSOS_STATE_DIR/metagraph-schema-ms1.json
mindsos metagraph detach-schema --name mg --json   # exits 0
```

---

## 10. PHASE_MAP §5 amendment (round 1-6 picks)

The PHASE_MAP §5 Phase 05b row's "Final amendments" section already
includes the 34 numbered pushback amendments (1-C / 2-A / 3-A / 4-A /
5-A / 6-A / 7-A / 8-A / 9-A / 10-A / 11-A / 12-A / 13-A / 14-A / 15-B /
16-A / 17-A / 18-A / 19-B / 20-A / 22-A / 23-A / 24-hybrid / 25-A /
26-A / 27-A / 28-A+DMS-A / 29-A / 30-A / 31-A / 32-A+D / 33-A / 34-A +
test budget unlimited) per the row text written in the same chat as
this implementation log. Future-work entries filed at
`_source_backup/root/mindsos_future_plans.md`:

* **Pushback 25-B** — `Graph.role` immutability via `__setattr__`
  (Phase 03 retroactive supersession trigger).
* **Pushback 31-B** — `update-intergraph-edge-label` CLI verb
  (asymmetry against 05a metaedge / metahyperedge label pattern).
* **Pushback 33-B** — `mindsos metagraph` subapp two-level
  reorganization (CLI breaking change vs already-shipped 05a).
* **Pushback 34-B** — symmetric `remove-*-type` backfix across all
  schema kinds (asymmetry against Phase 04 graph schema vocabularies).
