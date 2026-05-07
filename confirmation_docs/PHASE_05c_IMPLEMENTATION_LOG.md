# Phase 05c — Implementation Log

> Companion to `confirmation_docs/PHASE_MAP.md` Phase 05c row.
> Written by the implementing chat (2026-05-06; row locked across 4
> reanalysis rounds in a prior chat with 20 numbered pushbacks).
> Tester reads this along with the row before kicking off
> `confirm-phase --phase 05c`.

---

## 1. Charter

Goal: ship the n-ary `IntergraphHyperEdge` primitive (ADR-0148 amended)
+ the `IntergraphHyperEdgeType` schema vocabulary + a single
replace-only `update_intergraph_hyperedge` factory + 4 new CLI verbs on
`mindsos metagraph` + 1 new CLI verb on `mindsos metagraph-schema` +
5-way `set-prop` mutex extension + metagraph state-file v=2 → v=3
cumulative one-way migration + metagraph-schema state-file v=1 → v=2
cumulative one-way migration.

Per CASC-1 strict-sequential cascade, this unblocks Phase 05d
(`MetaEdgeType` + `MetaHyperEdgeType` vocab on `MetagraphSchema`).

**Out of scope** (carry-forward — picked up in subsequent phases):

* `MetaEdgeType` + `MetaHyperEdgeType` — Phase 05d (P1-B scope split
  re-routed past 05c).
* `MetaEdge.type_name` field audit — Phase 05d (P3 deferred).
* Eager-attach extension to walk metaedges + metahyperedges — Phase 05d
  (Push9-A from 05b expires there).
* Soft-delete substrate uniformly across all 5 edge variants — Phase 10.
* `RemovalImpact` + `force=True` — Phase 10.
* FalkorDB persistence + Cypher Pattern B emit + n-lock canonical OCC —
  Phase 07 (05c locks the contract; 07 implements).
* Symmetric `update_intergraph_edge_endpoints` on the binary primitive
  (P11→P13-B retreat — future-work entry filed at
  `_source_backup/root/mindsos_future_plans.md` "Discoverable
  endpoint-update verb for IntergraphEdge").
* In-place hyperedge→edge cardinality downgrade with edge_id stability
  — future-work entry filed at the same section.
* XRef cross-metagraph — Phase 09.
* Element instancing — Phase 06.

---

## 2. Pre-implementation audit findings (Step 0)

Per the locked Step 0 task in the 05c row "Automated tests" subsection,
audited every `tests/phase_05a/test_state*.py` and
`tests/phase_05b/test_state*.py` plus the broader phase-04 / phase-05a
state test files for hard-coded `_state_version` / METAGRAPH_*
constants that will break under the 05c bump (METAGRAPH 2→3 +
METAGRAPH_SCHEMA 1→2).

**Files updated to dynamic constants OR bumped literals:**

* `tests/phase_04/test_state.py` L242-243 — bumped literals from
  `== 2` → `== 3` (METAGRAPH_STATE_VERSION) and `== 1` → `== 2`
  (METAGRAPH_SCHEMA_STATE_VERSION). This file's test_constants_split
  is the canonical "constants split" canary — literals bumped per
  the 05b precedent that updated the same file.
* `tests/phase_05b/test_state_v2.py` — converted hard-coded literals
  to dynamic `state_mod.METAGRAPH_STATE_VERSION` /
  `mg_migrations.CURRENT_VERSION` references where practical (per
  P26 pick C). Renamed `test_metagraph_state_version_bumped_to_2`
  → `_at_current`; `test_metagraph_schema_state_version_is_1` →
  `_at_current`; `test_v2_idempotent` → `test_v2_advances_to_current`;
  `test_v1_idempotent_migration` → `test_v1_advances_to_current_migration`.
  Forward-version-refusal tests `test_forward_version_v3_refused` /
  `_v2_refused` renamed to `test_forward_version_refused` and use
  `CURRENT_VERSION + 1` dynamically (P26 pick C).
* `tests/phase_05a/test_metagraph_inspect_list.py` — extended P10
  shape lockers with `intergraph_hyperedges` (counts dict) +
  `intergraph_hyperedges_count` (per list entry) — symmetric with the
  05b extension for `intergraph_edges`.

**Files NOT affected** (already dynamic OR not state-version-pinned):

* `tests/phase_05a/test_metagraph_state_v1.py` — uses
  `state_mod.METAGRAPH_STATE_VERSION` dynamically.
* `tests/phase_05a/test_metagraph_create.py` — dynamic.
* `tests/phase_05a/test_migrations.py` — uses
  `metagraph_migrations.CURRENT_VERSION` dynamically; comments
  reference "= 2 in 05b" but assertions remain correct under v=3.
* `tests/phase_05a/test_graph_state_v4.py` — graph state-file
  unchanged in 05c (P17-A).
* `tests/phase_05b/test_dms_a.py` — schema state-file fixture at v=1
  exercises malformed-PropertyType injection that triggers raw-JSON
  fallback regardless of version contract; under 05c the fixture is
  now a "v=1 needs migration" file with malformed property_types —
  still hits fallback path.

---

## 3. Round-1-4 design picks (over and above the locked PHASE_MAP §5 row)

This implementation chat ran two additional rounds of reanalysis on top
of the 20-pushback locked row. **5 new pushbacks** total (P26-P30) plus
**2 follow-ups** (P31-P32) accepted by the user; folded into the
implementation:

| # | Lock | Decision |
|---|---|---|
| P26 | `phase_05b/test_state_v2.py` forward-refusal tests | **C**: rename to drop literal version; use `CURRENT_VERSION + 1` fixtures dynamically. |
| P27 | `__setattr__` scope contradiction (memory vs design doc 2026-05-06 amendment) | **A**: follow design-doc-wins-on-conflict. `IntergraphHyperEdge.__setattr__` blocks `compositional` always; blocks `anchors` / `members` / `properties` always on direct user mutation regardless of compositional flag value; factory uses `object.__setattr__` to bypass for legitimate validated updates. "Set-via-factory" contract. |
| P28 | "replace-only" naming asymmetry on update verb | **A**: keep `replace_properties: bool = False` default (merge); document the asymmetry. Anchors/members are replace-semantics; properties merge by default, opt-in to replace via `--replace-properties`. Carry-forward 05b precedent. |
| P29 | Test plan gaps | **B**: fold empty-vocab attach + edge_id-preservation coverage into existing test files (no new files). |
| P30 | Step-numbering drift in P8-A (claim "step 8.5" vs appendix step 10) | **A**: row appendix §A is canonical; treat as step 10 throughout implementation. PHASE_MAP §5 patch deferred to row maintenance. Implementation log notes the correction. |
| P31 | Tester recipe should exercise the P13-B workaround | **B**: add automated regression test in `tests/phase_05c/test_cli_intergraph_hyperedge.py::TestP13BWorkaround` covering `remove-intergraph-edge` + `add-intergraph-edge --intergraph-edge-id <orig>` — preserves edge_id stability. Permanent CI coverage > one-off tester run. |
| P32 | Row appendix §A step 5 misdescribes cypher regex enforcement timing | **A**: step 5 enforcement is INLINE in factory + ALSO at `__post_init__` (belt-and-suspenders). Implementation does both; docstrings + impl log document the actual two-phase enforcement. |

---

## 4. Module changes

### Net-new files (1)

* `mindsos_core/models/intergraph_hyperedge.py` — `IntergraphHyperEdge`
  dataclass + strict ``__setattr__`` immutability override (P27 A)
  + tuple-conversion at `__post_init__` (P2-refined) + cardinality +
  overlap defense (P14-A direct-construction safety) + cypher regex
  belt-and-suspenders (P32) (~220 LOC).

### Test files (8 + 1 conftest)

* `tests/phase_05c/__init__.py`
* `tests/phase_05c/conftest.py` — fixtures (`mg_for_hyperedge`).
* `tests/phase_05c/test_intergraph_hyperedge.py` — dataclass invariants
  (kw_only, tuple-conversion, cypher regex, cardinality, overlap,
  __setattr__ strict scope, equality/hashing, edge_id override).
* `tests/phase_05c/test_intergraph_hyperedge_type.py` — frozen
  dataclass + ordered default + property-type variants + role-based
  constraint surface.
* `tests/phase_05c/test_metagraph_schema_intergraph_hyperedge.py` —
  registration / require / validate / validate-properties surface +
  empty-vocab semantics + namespace independence between edge and
  hyperedge types.
* `tests/phase_05c/test_validation_order_hyperedge.py` — P14-A 16-step
  order; canonicalize-before-cardinality (dedup-collapse-to-1-1
  refusal); P8-A compositional+ordered=False refusal; per-step
  isolation tests (1-2 graph existence; 3-4 node existence; 5 cypher
  regex; 6 schema lookup; 7 canonicalize; 8 cardinality; 9 overlap;
  10 P8-A; 11 reserved keys; 12 validate constraints; 13 strict
  property type).
* `tests/phase_05c/test_compositional_hyperedge.py` — flag immutability
  via __setattr__; remove / update refusal; remove_graph cascade
  refusal (P17-A extended) on both anchor side AND member side; error
  message includes edge_kind.
* `tests/phase_05c/test_update_intergraph_hyperedge.py` — P10-C
  replace-only (anchors / members independently retained when None);
  P29 edge_id stability across update; merge-vs-replace properties;
  P19-A 1-1 collapse refusal; atomic rollback on validation failure;
  refusal on compositional; P20-A detached-schema structural-only.
* `tests/phase_05c/test_metagraph_attach_hyperedge_validation.py` —
  P6-A eager-attach walks intergraph_hyperedges; metaedges/metahyperedges
  still skipped (Push9-A from 05b carry-forward); P29 (b) empty-vocab
  attach behavior + Pushback 24-hybrid carry-forward.
* `tests/phase_05c/test_state_v3_round_trip.py` — metagraph v=2→v=3 +
  metagraph-schema v=1→v=2 migrations; chained migration v=1→v=3;
  byte-stable sort by edge_id; round-trip serialize+save+load+rehydrate;
  RESERVED_PROPERTY_KEYS extension.
* `tests/phase_05c/test_cli_intergraph_hyperedge.py` — CLI subprocess
  tests: 4 new metagraph subcommands (add/remove/update/list-intergraph-
  hyperedge) + 5-way set-prop mutex + add-intergraph-hyperedge-type +
  schema inspect/list shape extensions + **P31 P13-B workaround
  regression coverage** on the binary primitive.

### Touched files (extensions)

* `mindsos_core/__init__.py` — exports `IntergraphHyperEdge` +
  `IntergraphHyperEdgeType`; `__version__ = "0.0.0+phase05c"`; module
  docstring updated.
* `mindsos_core/schema/__init__.py` — re-exports
  `IntergraphHyperEdgeType`.
* `mindsos_core/schema/types.py` — adds `IntergraphHyperEdgeType`
  frozen dataclass with role-based anchor/member graph constraints +
  `ordered: bool = True` default (P18-A).
* `mindsos_core/schema/metagraph_schema.py` — adds
  `_intergraph_hyperedge_types` storage +
  `add_intergraph_hyperedge_type` / `require_intergraph_hyperedge_type`
  / `validate_intergraph_hyperedge` / `validate_intergraph_hyperedge_properties`
  methods + `intergraph_hyperedge_types` property; extended `__repr__`.
* `mindsos_core/schema/validation.py` — extends
  `RESERVED_PROPERTY_KEYS` with `intergraph_hyperedges`,
  `intergraph_hyperedge_types`, `anchors`, `members`.
* `mindsos_core/models/metagraph.py` — extends with
  `add_intergraph_hyperedge` / `remove_intergraph_hyperedge` /
  `update_intergraph_hyperedge` / `iter_intergraph_hyperedges` factory
  methods (~360 LOC); extends `remove_graph` precheck pass to walk
  BOTH `intergraph_edges` AND `intergraph_hyperedges` (P17-A extended)
  with edge_kind + side disambiguation in error messages; extends
  `attach_schema` eager pass to walk hyperedges (P6-A); adds
  `intergraph_hyperedges` instance state; extended `__repr__`.
* `mindsos_cli/state.py` — bumps comments + JSON shape doc strings to
  v=3 metagraph / v=2 metagraph-schema; constants are derived
  dynamically from `_metagraph_migrations.CURRENT_VERSION` /
  `_metagraph_schema_migrations.CURRENT_VERSION` so the bump is local
  to the migrations modules.
* `mindsos_cli/migrations/metagraph.py` — bumps `CURRENT_VERSION` 2→3;
  appends `_v2_to_v3(state)` step (sets `intergraph_hyperedges: []`
  default).
* `mindsos_cli/migrations/metagraph_schema.py` — bumps `CURRENT_VERSION`
  1→2; adds `_v1_to_v2(state)` step (sets `intergraph_hyperedge_types:
  []` default).
* `mindsos_cli/commands/metagraph.py` — extends `_metagraph_to_state`
  with `intergraph_hyperedges` array (sorted by edge_id); extends
  `_state_to_metagraph` rehydrator to load hyperedges (translating
  graph_name → graph_id at boundary); extends
  `_metagraph_schema_to_state` with `intergraph_hyperedge_types` +
  `_state_to_metagraph_schema` rehydrator; extends `inspect` /
  `list` JSON shapes additively (`counts.intergraph_hyperedges` +
  `intergraph_hyperedges_count` per list entry); extends `remove-graph`
  output with `cascaded_intergraph_edges` + `cascaded_intergraph_hyperedges`;
  extends `set-prop` to 5-way mutex; adds 4 new subcommands
  (add/remove/update/list-intergraph-hyperedge) with paired-flags
  pairing helper (`_pair_repeated_flags`).
* `mindsos_cli/commands/metagraph_schema.py` — extends `inspect` JSON
  shape with `intergraph_hyperedge_types` array + counts; extends
  `list` JSON shape with `intergraph_hyperedge_types_count`; extends
  `create` JSON output to include the new vocab array; adds
  `add-intergraph-hyperedge-type` subcommand with
  `--ordered/--unordered` flag (P18-A — defaults to `--ordered`) and
  P12-A schema-mutation-while-attached stderr warning.
* `mindsos_cli/__init__.py` — `__version__ = "0.0.0+phase05c"` +
  module docstring updated for 05c additions + 05d deferral note.
* `mindsos_cli/manifest.toml` — `[mindsos] phase = "05c"`;
  `version = "0.0.0+phase05c"`.
* `pyproject.toml` — version + description bumped.
* `docker-compose.yml` — image tags `mindsos:phase05c-{prod,test}`.
* `Dockerfile` — comment lines bumped (Phase 05b → Phase 05c
  references); existing wildcards cover the new file.
* `tests/_shared/sentinel_paths.py` — **+1 entry**:
  `mindsos_core/models/intergraph_hyperedge.py`.
* `tests/phase_04/test_state.py` — Step 0 audit: literals 2→3, 1→2.
* `tests/phase_05a/test_metagraph_inspect_list.py` — extended P10
  shape lockers (additive `intergraph_hyperedges` /
  `intergraph_hyperedges_count`).
* `tests/phase_05b/test_state_v2.py` — Step 0 audit: dynamic constants
  + dynamic forward-version-refusal fixtures (P26 C).

---

## 5. Bug ledger / decisions made during implementation

* **B-05c-T1** — initial test fixture used positional string literals
  (`g.add_node("cat", type_name="Word")`) where the literal was both
  the value AND the lookup key. ``Graph.add_node`` mints UUID4 node_ids
  by default; the literal "cat" doesn't appear as a key in
  ``g.nodes``. Test calls referencing ``(g.graph_id, "cat")`` raised
  ``IdentityError: anchor node 'cat' not in graph 'word'``.
  **Resolution**: pass explicit ``node_id="cat"`` kwarg so the
  auto-mint uses the literal as the id; applied via in-place regex
  substitution to all 6 test files in `tests/phase_05c/`. 48
  substitutions total. No code-side change needed.
* **B-05c-T2** — `test_role_mismatch_refused` originally fed a
  letter-typed node into a slot expecting Word-typed + word-role. The
  validator's check order is anchor types → member types → anchor
  graphs → member graphs; the FIRST violation triggers, which was
  anchor TYPE (Letter, not Word), not anchor GRAPH ROLE.
  **Resolution**: synthesize a Word-typed node placed in the
  letter-role graph (type matches the constraint; role mismatches),
  isolating the role-check branch.
* **D-05c-1** (design correction during implementation, not a bug) —
  The 05c row appendix §A locks step 5 as "cypher regex at
  `__post_init__`". P32 surfaced that this misdescribes timing — the
  factory enforces inline at step 5 BEFORE construction; `__post_init__`
  re-validates at step 15 for direct-construction safety. Implementation
  does both (matches 05b precedent + design intent). The PHASE_MAP §5
  row text retains the original wording; this log + the new file's
  docstring carry the corrected description.

No tester-side hotfixes recorded as of this log. Tester records any
in-container surfaces (e.g., docker image rebuild needs, recipe
deviations) in `PHASE_05c_CONFIRMED.md` `tester_notes`.

---

## 6. Compositional cascade — recovery patterns (Phase 05c extension)

Per Pushback 17-A (extended in 05c per the smaller-items fold),
`Metagraph.remove_graph` runs an atomic precheck pass that walks BOTH
`intergraph_edges` AND `intergraph_hyperedges`; if any incident edge
of either variant has `compositional=True`, raise
`CompositionalImmutableError` with structured edge_kind + side
disambiguation BEFORE mutation. State unchanged.

Tester recovery flow (unchanged from 05b):

1. Identify the offending compositional edge from the error message.
   The 05c-extended message names `edge_kind` (`intergraph_edge` /
   `intergraph_hyperedge`) and for hyperedges also names which side
   (`anchor side` / `member side`).
2. (No path: cannot be removed; cannot be demoted to non-compositional.)
3. `mindsos metagraph reset --name <MG> --force --yes` — destroys the
   entire metagraph state file + strips back-pointers from all
   referenced graphs. Tester rebuilds.

Phase 10 may add a `--force` bypass on `remove_intergraph_hyperedge`
(and on `remove_graph`'s precheck) under the full ADR-0135 surface.

---

## 7. Schema mutation while attached — Phase 04 footgun carry-forward (P12-A)

Per P12-A (carry-forward of 05b Pushback 23-A pattern), `mindsos
metagraph-schema add-intergraph-hyperedge-type` walks every
`metagraph-*.json` for `schema_name == <target>`. If any metagraphs
are attached, emits a stderr warning listing them.

The footgun: attached metagraphs do NOT re-validate against the new
vocabulary until the tester re-attaches. Existing intergraph_hyperedges
may now violate the (extended) schema silently.

Tester remediation: `mindsos metagraph attach-schema --name <MG>
--schema <X>` on each attached metagraph. Per Pushback 32-D
(carry-forward), re-attach with the same schema name runs fresh
validation; surfaces drift.

This carries forward from 05b's identical pattern (intergraph-edge
schema mutation while attached). 05c inherits cleanly; the new
hyperedge vocabulary path uses the same `_find_attached_metagraphs`
helper.

---

## 8. Forward-compat notes for 05d

Per the 05c row §D 05d dry-run appendix, the following are
pre-resolved:

* **05d adds `meta_edge_types` + `meta_hyperedge_types` arrays to
  MetagraphSchema state file** → bump v=2 → v=3. **05c's v=2 shape is
  forward-compat:** missing fields default to empty arrays. No 05c
  change needed.
* **05d's MetaEdge.type_name field audit (P3 deferred):** if 05a's
  `MetaEdge` dataclass shipped without `type_name`, 05d adds the field
  as `Optional[str] = None` with rehydration tolerance for legacy
  entries. **05c does NOT touch metaedges; no interaction.**
* **05d's eager-attach extension** to walk metaedges + metahyperedges
  (Push9-A from 05b expires in 05d). **05c's eager-attach pass**
  iterates intergraph_edges + intergraph_hyperedges only; 05d extends
  to also iterate metaedges + metahyperedges. No 05c change needed
  (additive in 05d).
* **05d's CLI verbs** (`add-meta-edge-type` + `add-meta-hyperedge-type`
  on `metagraph-schema` subapp) carry the same P12-A
  schema-mutation-footgun pattern as 05c's
  `add-intergraph-hyperedge-type`. No 05c change needed.
* **05d's `RESERVED_PROPERTY_KEYS` extension** with `meta_edge_types`
  + `meta_hyperedge_types` (top-level metagraph-schema state v=3
  fields). **05c's reserved-key addition** of
  `intergraph_hyperedge_types` is consistent with this pattern. No
  05c change needed.

---

## 9. Tester instructions

```sh
# [Linux] Tester host venv.
cd halvim_mindsos
git pull origin phase-05c
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e .

# Doctor self-test (static-only; no FalkorDB required).
mindsos doctor --self-test --static-only

# REBUILD test image first (B-05b-T2 lesson — stale Docker images
# break tests after pulling test-side fixes).
docker compose build mindsos-test

# In-container tests.
docker compose run --rm mindsos-test pytest tests/

# Manual exploration: see notes-phase-05c.md.

# Confirmation.
mindsos confirm-phase --phase 05c --notes-file notes-phase-05c.md
```

Expected: ≥ Phase 05b baseline (740 + 2 skipped) + 05c additions
(125+ in-process + ~40 CLI subprocess). Tester records actual count
in `PHASE_05c_CONFIRMED.md`.

### Manual exploration recipe

See `notes-phase-05c.md` (every step `[Mac]` / `[Linux]` tagged per
`feedback_terse_step_recipes.md`).

---

## 10. PHASE_MAP §5 amendments (P26-P32)

The PHASE_MAP §5 Phase 05c row's "Final amendments" section already
includes the 20 numbered pushback amendments locked in the prior chat
(P1-B / P2-refined / P3 / P4-A / P5-refined / P6-A / P7-A / P8-A /
P9-A / P10-C / P11→P13-B / P12-A / P14-A / P15-A / P16-A / P17-A /
P18-A / P19-A / P20-A + smaller-items folded). This implementation
chat added 5 numbered pushbacks (P26-P30) plus 2 follow-ups
(P31-P32); their text is captured in §3 above and in
`memory/feedback_*.md` if a new pattern surfaced. No row-text
changes from this implementation chat — all 7 picks fold into
docstrings + tests + this implementation log.

Future-work entries filed at
`_source_backup/root/mindsos_future_plans.md` (locked in the row
chat; this implementation does not file additional entries):

* "Discoverable endpoint-update verb for IntergraphEdge" (P11→P13-B
  retreat).
* "In-place hyperedge→edge downgrade with edge_id stability" (P19-A).

---

## 11. 05b CHANGELOG amendment (P13-B retreat)

Per the 05c row sign-off item 2, this branch ships a single commit
amending `docs/changelog/CHANGELOG.md`'s 05b entry with the
discoverable-endpoint-update workaround note. Tester verifies the
amendment landed alongside 05c implementation in the same PR.

The workaround pattern (now permanently regression-tested via P31 in
`tests/phase_05c/test_cli_intergraph_hyperedge.py::TestP13BWorkaround`):

```sh
# To "update" an IntergraphEdge endpoint (without compositional flag):
mindsos metagraph remove-intergraph-edge --name MG --intergraph-edge-id E
mindsos metagraph add-intergraph-edge --name MG \
    --source-graph G --source-node N \
    --target-graph G2 --target-node N2 \
    --type T --intergraph-edge-id E
```

The `--intergraph-edge-id <orig>` override (Push14-A from 05b) preserves
edge_id stability across the workaround.
