# Phase 04 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

L1 Schema (NodeType / EdgeType / opt-in strict + attach/detach + set-prop + v=2 state-file bump)

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

Tester run on 2026-05-04 from Linux box. Final cumulative result:
**379 passed, 2 skipped** in-container
(`docker compose run --rm mindsos-test pytest tests/`). The 2 skips
are existing `test_mkdocs_buildable.py` (mkdocs not in test image) and
new `test_restore_node_registers_provided_id` (Phase 08 deferral —
`Graph._restore_node` ships there).

### Manual exploration outcomes (Phase 04 surface)

- `mindsos schema {create,add-node-type,add-edge-type,inspect,list,reset}`
  — full CRUD round-trip; `inspect --json` shows sorted node_types /
  edge_types; `reset --name` orphan check refused with exit 1 when a
  graph referenced the schema; `--force` overrides with a stderr
  warning naming `mindsos graph detach-schema`.
- `mindsos schema reset --all` ALSO runs the orphan check (NEW3
  confirmed manually).
- `mindsos graph create --schema people` — schema attached at create
  time; `inspect --json` reports `schema_name` + `schema_strict`.
- `mindsos graph attach-schema` — eager validation; first violation
  prints `node <id>: PropertyShapeError: ...` with offending element
  id (Pick B confirmed). Re-attach permitted; `previous_schema`
  surfaces in JSON output (Pick N4).
- Empty-strict-schema warning fires at attach time when the schema is
  strict AND has zero NodeTypes (Pick G).
- `mindsos graph detach-schema` recovers a graph from a dangling
  schema reference (raw-JSON path; works EVEN WHEN the referenced
  schema state file is gone — Pick E + N1 confirmed).
- `mindsos graph set-prop --node-id N --prop k=v` — default merge with
  schema validation. `--replace` swaps the bag entirely BUT preserves
  `ref:*` cross-graph reference keys (Pick D + N5 confirmed via
  Supp-2; user-supplied `ref:*` values overwrite existing on
  collision).
- All 8 PropertyType variants exercised through pytest
  (`test_property_validation.py` — strict-mode rules including the
  `bool`-vs-`int` subtype trap and FalkorDB `int → float` coercion).

### Phase 03 → Phase 04 migration confirmed

Hand-wrote a v=1 graph state file containing a reserved-key
poisoned property (`{"id": "evil-legacy"}`):
- `mindsos graph inspect` loaded it cleanly (rehydration `_validate=False`
  tolerance — NEW1 confirmed).
- Default `set-prop` merge failed with `PropertyShapeError: ... key 'id'
  is reserved by the Core Layer` because the merged candidate still
  contained the reserved key.
- `set-prop --replace` recovered: reserved `id` stripped, user-supplied
  properties applied, file re-saved at `_state_version: 2` (one-way
  migration confirmed).

### Process snags worth recording

1. **Step 19 of the tester checklist had a strict-mode bug.** The
   original recipe declared `Person` with only `age=int`, then tried
   `set-prop --prop city=NYC` — which correctly fails under strict
   mode because `city` is undeclared on `Person`. The right test
   recipe declares both `age=int` AND `city=string` on `Person` (Option A
   from the implementing chat). Worth noting for Phase 05+ test
   recipes: under strict mode, every property key the tester intends
   to set MUST be declared on the type (or the type's
   `property_types` map MUST be empty for opt-out).

2. **`graph list` and `schema list` deliberately bypass the strict
   version check** (PHASE_MAP Phase 04 row appendix #17). A
   future-version state file appears in the listing rather than being
   hidden — verified `v=N` field shows in the human output (Supp-1).

### Phase 05 chat — load-bearing reminder (filed earlier)

**Q13 — intergraph edge primitive** is filed in PHASE_MAP §7 Q13
with full analysis at `confirmation_docs/INTERGRAPH_EDGE_DESIGN_NOTE.md`.
Phase 05 row already amended to require adjudication before
implementing Metagraph elements. Default = defer indefinitely.

### Host venv

Python 3.12.x on Linux box. `pip install -e .` re-run after `git pull`
to phase-04 (Phase 04 added the `mindsos_core.schema` subpackage; the
wildcard `[tool.setuptools.packages.find].include = ["mindsos_core*"]`
already covers it, but a fresh editable install ensures discovery on
all Python versions). `which mindsos` resolves to the venv's bin
directory. `confirm-phase` preflight (`doctor --self-test
--static-only`) ran cleanly before this doc was written.
