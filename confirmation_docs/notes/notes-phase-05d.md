# Phase 05d — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

L1 MetaEdgeType + MetaHyperEdgeType vocab + eager-attach extension; 2 new `mindsos metagraph-schema` add verbs (add-meta-edge-type / add-meta-hyperedge-type) + 1 new read-only `mindsos metagraph-schema validate` verb (with `--schema MS` opt-in per round-7 P32 A); metagraph-schema state-file v=2→v=3 cumulative one-way migration (meta_edge_types + meta_hyperedge_types); ADR-0014 + ADR-0017 pointer lines (round-7 P42 C; full transcription deferred to Phase 38). Round 7 reanalysis pass dropped the locked-design fingerprint mechanism entirely (P31 A) along with the metagraph state-file bump and `--accept-vocab-change` consent flag.

## tester_notes

Tester run on 2026-05-08 from Linux box (Python 3.12 + Docker Compose +
host-side `pip install -e . --break-system-packages`). Final cumulative
result: **1013 passed, 2 skipped** in-container
(`docker compose run --rm mindsos-test pytest tests/`). The 2 skips are
the existing `test_mkdocs_buildable.py` (mkdocs not in test image) and
`test_restore_node_registers_provided_id` (Phase 08 deferral). +112 over
05c's 901 baseline (05d added the meta-vocab + eager-attach + factory +
state-migration + CLI test families).

Row was locked across 6 design-chat reanalysis rounds (M1–M7 + P1–P30)
plus a 7th round in the implementation chat that materially reshaped
the design before code landed (P31–P44). Round-7 ledger:
`confirmation_docs/PHASE_05d_IMPLEMENTATION_LOG.md` §1. Key reverses /
refines: P31 A dropped the locked-design fingerprint mechanism + its
`--accept-vocab-change` flag + the metagraph state-file bump entirely;
P32 A added `--schema MS` opt-in to the new `validate` verb; P33 A
struck P11 A's instance-graph forward-compat assertion; P39 A locked
empty-vocab + non-strict pass-silently for the new metaedge walks
(closes the 05c-migration regression vector); P41 A split exit code 2
into 2/3; P42 C swapped P35/P36's inline ADR amendments for one-line
pointers; P44 A fixed P5 A's incorrect "mirrors 05b" claim by
verifying the actual 05b validation order at `metagraph.py:735-798`.

### Hotfix ledger (issues surfaced during tester run; fixed in same chat)

#### B-05d-T1 — `tests/phase_04/test_state.py:243` had hard-coded `METAGRAPH_SCHEMA_STATE_VERSION == 2`

Surfaced on first GitHub Actions cumulative test run (run 25556420410 —
1 failed, 1012 passed, 2 skipped). Step 0 audit was scoped to
`tests/phase_05a/test_state*.py`, `tests/phase_05b/test_state_v2.py`,
`tests/phase_05c/test_state_v3_round_trip.py` per the 05d handoff
prompt; missed the Phase 04 test that asserts every per-kind constant.
Fix: migrated all four constants in that test to dynamic
`<...>_migrations.CURRENT_VERSION`. Permanent feedback memory
`feedback_state_version_audit_scope.md` filed: future state-file bumps
must grep `_state_version`-related literals across the entire `tests/`
tree, not just the most recent two phase folders.

#### B-05d-T2 — `add-metaedge` / `add-metahyperedge` CLI handlers leaked `UnknownTypeError` as Rich traceback

Surfaced during manual exploration Task 5 (`add-metaedge --type
UNDECLARED` against attached schema). The factory raised
`UnknownTypeError` correctly (validated by `tests/phase_05d/`'s
non-CLI tests in the sandbox) but the CLI handlers' `try/except` block
caught only `SchemaError` / `CypherError` / `IdentityError` /
`PropertyShapeError` — not `UnknownTypeError`. The 05b/05c sibling
add-* handlers caught it because their factories already raised it
pre-05d; 05d's `add_metaedge` / `add_metahyperedge` started raising it
for the first time and the handler block didn't keep up. Fix: added
`except UnknownTypeError` arm to both handlers in
`mindsos_cli/commands/metagraph.py`.

### Recipe deviations corrected during run (recipe text now updated)

- **Task 8 P12-A flow:** original recipe text omitted the `detach-schema`
  step before re-attaching to a different schema. P12-A refuses with
  `IdentityError` if a different schema is already attached. Added
  `mindsos metagraph detach-schema --name mg` between schema create and
  re-attach. Recipe now reads correctly.
- **Task 9 expectation flip:** original recipe text said "each step
  exits 0" but the locked P31 A behavior (no fingerprint mechanism) and
  vocab-gap refusal (P39 A non-strict-empty-pass only applies when vocab
  is EMPTY) means the second attach refuses with `UnknownTypeError`
  when the schema's mutated vocab no longer covers existing metaedges.
  Recipe now describes the correct refusal path with recovery steps.

### Manual exploration outcomes (Phase 05d surface)

- **Task 2-3 build all four vocabs + verify state-file shape** — all
  4 add-*-type verbs exit 0; metagraph-schema-ms.json shows
  `_state_version: 3` + 4 vocab arrays with one entry each.
  `MetaHyperEdgeType` JSON entry has NO `ordered` key (P1 C confirmed).
  `MetaEdgeType` JSON entry has only `allowed_source_graphs` +
  `allowed_target_graphs` (no `allowed_*_types` — connects graphs not
  nodes).
- **Task 4 attach + add-metaedge under non-empty vocab** — attach
  exits 0; add-metaedge LINKS_TO exits 0 with JSON containing
  `type_name: "LINKS_TO"` + `source_graph: "ont"` + `target_graph:
  "lex"`.
- **Task 5 vocab-gap refusal on add_metaedge** — exit 1; clean stderr
  `UnknownTypeError: Unknown meta-edge type: 'UNDECLARED'`. (Required
  hotfix B-05d-T2 to land first.)
- **Task 6 P8 A schema-mutation footgun + role-constraint enforcement**
  — `add-meta-edge-type` exits 0 with stderr footgun warning listing
  `mg`. Re-attach exits 0 (existing LINKS_TO still validates against
  unchanged LINKS_TO MetaEdgeType). `add-metaedge --type STRICT_LINK`
  exits 1 with stderr naming the `source graph role 'ontology'`
  violation against `allowed_source_graphs: ['concepts']`.
- **Task 7 validate verb (P9 B + P32 A + P40 A + P41 A)** — 1st sub-case
  (default attached schema): exit 0; JSON `{passed: true, schema_name:
  "ms", metagraph_name: "mg", violations: []}` with NO
  `vocab_fingerprint_match` field. 2nd sub-case (metagraph not found):
  exit 2. 3rd sub-case (metagraph unattached, no `--schema` supplied):
  exit 3. 4th sub-case (`--schema MS` opt-in path): exit 0.
- **Task 8 empty-vocab pass-silently regression (P39 A)** — detach +
  attach to `empty_ms` (which has empty `meta_edge_types: []`) exits 0
  even though `mg` has an existing LINKS_TO metaedge. Closes the
  05c-migration regression vector.
- **Task 9 re-attach with vocab-mutation that breaks existing data
  (P31 A path)** — `add-meta-edge-type --type-name NEW_TYPE` exits 0
  with footgun warning; re-attach exits 1 with `UnknownTypeError:
  Unknown meta-edge type: 'LINKS_TO'`. Validates that the eager-walk +
  vocab-existence check is the sole consent surface (no fingerprint).
- **Task 10/11 pytest in-container** — 1013 passed, 2 skipped.

### Manual exploration recipe

These steps run the `mindsos` CLI **natively on the Linux host** (FalkorDB
runs in Docker; CLI runs on host via the editable `pip install -e .
--break-system-packages` install). Single-shot verification can also use
`docker compose run --rm mindsos ...` but the `--rm` flag destroys state
between invocations, so multi-step exploration must use host invocation.

**State dir:** `~/.mindsos/` is the default when `MINDSOS_STATE_DIR` is
unset. Recipe paths use `~/.mindsos/<file>` literally (NEVER
`$MINDSOS_STATE_DIR/...` — the shell may have it unset; see
`feedback_state_dir_env_var.md`).

**Reset before starting:** if the host's `~/.mindsos/` carries leftover
state from prior phases, run `mindsos metagraph reset --all --yes`,
`mindsos metagraph-schema reset --all --yes`, and `mindsos graph reset
--all --yes --force` first.

#### Task 1 [Linux] — Sanity: schema state-file version constants are at 3

```
mindsos --version
docker compose run --rm mindsos-test pytest tests/phase_05d/test_state_v3_schema_migration.py::TestVersionConstants -q
```

→ expect: doctor version reports `0.0.0+phase05d`; test class passes.

#### Task 2 [Linux] — Build a schema with all four vocabs registered

```
mindsos metagraph-schema create --name ms
mindsos metagraph-schema add-intergraph-edge-type --schema ms --type-name EVOKES
mindsos metagraph-schema add-intergraph-hyperedge-type --schema ms --type-name COMPOSED_OF
mindsos metagraph-schema add-meta-edge-type --schema ms --type-name LINKS_TO --json
mindsos metagraph-schema add-meta-hyperedge-type --schema ms --type-name GROUPS --json
```

→ expect: each verb exits 0. `--json` outputs include `type_name` +
`allowed_*_graphs` empty arrays + `attached_metagraphs: []`. The
meta-hyperedge JSON has NO `ordered` key (P1 C lock).

#### Task 3 [Linux] — Schema state-file shape

```
mindsos cat ~/.mindsos/metagraph-schema-ms.json
```

→ expect: JSON with `_state_version: 3`, `meta_edge_types: [...]` (1 entry),
`meta_hyperedge_types: [...]` (1 entry), and the existing
`intergraph_*_types` arrays.

#### Task 4 [Linux] — Build a metagraph + attach + add metaedge under schema constraints

```
mindsos graph create --name ont --role ontology
mindsos graph create --name lex --role lexicon
mindsos metagraph create --name mg
mindsos metagraph add-graph --name mg --graph ont
mindsos metagraph add-graph --name mg --graph lex
mindsos metagraph attach-schema --name mg --schema ms
mindsos metagraph add-metaedge --name mg --source-graph ont --target-graph lex --type LINKS_TO --json
```

→ expect: each step exits 0. Attach exits 0 (eager-attach passes — empty
metaedge collection). Add-metaedge JSON shows `type_name: LINKS_TO`.

#### Task 5 [Linux] — Vocab-gap refusal on add_metaedge

```
mindsos metagraph add-metaedge --name mg --source-graph ont --target-graph lex --type UNDECLARED
```

→ expect: exit 1; stderr contains `Unknown meta-edge type: 'UNDECLARED'`.

#### Task 6 [Linux] — Role constraint enforcement

```
mindsos metagraph-schema add-meta-edge-type --schema ms --type-name STRICT_LINK --allowed-source-graph concepts --allowed-target-graph theory
```

→ expect: exit 0; stderr contains schema-mutation footgun warning
listing `mg`.

```
mindsos metagraph attach-schema --name mg --schema ms
mindsos metagraph add-metaedge --name mg --source-graph ont --target-graph lex --type STRICT_LINK
```

→ expect: re-attach exits 0 (existing LINKS_TO metaedge still passes).
Add STRICT_LINK exits 1; stderr names "source graph role 'ontology'"
violation against `allowed_source_graphs: ['concepts']`.

#### Task 7 [Linux] — Validate verb (P9 B + P32 A)

```
mindsos metagraph-schema validate --metagraph mg --json
```

→ expect: exit 0; JSON `{passed: true, schema_name: "ms", metagraph_name:
"mg", violations: []}`. NO `vocab_fingerprint_match` field (P40 A).

```
mindsos metagraph-schema validate --metagraph nonexistent
```

→ expect: exit 2 (resource not found per P41 A).

```
mindsos metagraph create --name unattached
mindsos metagraph-schema validate --metagraph unattached
```

→ expect: exit 3 (no usable schema per P41 A).

```
mindsos metagraph-schema validate --metagraph unattached --schema ms
```

→ expect: exit 0 (P32 A — explicit `--schema` overrides "no attached"
case).

#### Task 8 [Linux] — Empty-vocab pass-silently regression (P39 A — 05c-migration safety)

```
mindsos metagraph-schema create --name empty_ms
mindsos metagraph detach-schema --name mg
mindsos metagraph attach-schema --name mg --schema empty_ms
```

→ expect: detach + attach exit 0. The existing `LINKS_TO` metaedge
passes silently because `empty_ms` has empty `meta_edge_types: []` and
`strict=false`.

#### Task 9 [Linux] — Reattach without consent flag (P31 A)

The carryover from Task 8 has `mg` attached to `empty_ms`. To exercise
the "schema mutation makes existing data invalid → eager-attach refuses
without ceremony" path:

```
mindsos metagraph-schema add-meta-edge-type --schema empty_ms --type-name NEW_TYPE
mindsos metagraph attach-schema --name mg --schema empty_ms
echo "exit=$?"
```

→ expect:
- `add-meta-edge-type` exits 0 with schema-mutation footgun stderr
  warning (P8 A) — adds `NEW_TYPE` only.
- `attach-schema` exits 1; stderr `UnknownTypeError: Unknown meta-edge
  type: 'LINKS_TO'`. The vocab now has `NEW_TYPE` only (non-empty), so
  P39 A's empty-vocab pass-silently rule does NOT apply; eager-attach
  walks the existing `LINKS_TO` metaedge and refuses on vocab gap. **No
  `--accept-vocab-change` flag exists** (P31 A — fingerprint mechanism
  dropped). Recovery: register `LINKS_TO` on `empty_ms`, OR detach +
  attach `ms` (which has both).

This validates the load-bearing P31 A behavior: re-attach has zero new
state-tracking surface; the eager-walk + vocab-existence check is the
sole consent mechanism.

#### Task 10 [Linux] — Run full Phase 05d test suite

```
docker compose run --rm mindsos-test pytest tests/phase_05d/ -v
```

→ expect: all tests pass. Cumulative ≥ 901 (05c baseline) + 05d
additions; record actual count below.

#### Task 11 [Linux] — Run full cumulative suite

```
docker compose run --rm mindsos-test pytest tests/
```

→ expect: cumulative passes; 2 existing skips
(`test_mkdocs_buildable.py`, `test_restore_node_registers_provided_id`).
Record actual `<N> passed, 2 skipped` count.

#### Task 12 [Linux] — confirm-phase

```
mindsos confirm-phase --phase 05d --notes-file notes-phase-05d.md
```

→ expect: exit 0; generates `confirmation_docs/PHASE_05d_CONFIRMED.md`.

### Hotfix ledger (fill if issues surface during tester run)

*(none yet)*

### Open questions surfaced during testing

*(none yet)*
