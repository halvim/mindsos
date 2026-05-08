# Phase 05d — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

L1 MetaEdgeType + MetaHyperEdgeType vocab + eager-attach extension; 2 new `mindsos metagraph-schema` add verbs (add-meta-edge-type / add-meta-hyperedge-type) + 1 new read-only `mindsos metagraph-schema validate` verb (with `--schema MS` opt-in per round-7 P32 A); metagraph-schema state-file v=2→v=3 cumulative one-way migration (meta_edge_types + meta_hyperedge_types); ADR-0014 + ADR-0017 pointer lines (round-7 P42 C; full transcription deferred to Phase 38). Round 7 reanalysis pass dropped the locked-design fingerprint mechanism entirely (P31 A) along with the metagraph state-file bump and `--accept-vocab-change` consent flag.

## tester_notes

*Tester fills this field after running the recipe.*

### Manual exploration recipe

These steps subprocess `mindsos` from inside the running test image. Run
each step on the **Linux box** with the test container active (per
`feedback_docker_compose_invocation.md` — the entrypoint is the `mindsos`
CLI, so `docker compose run --rm mindsos <subcommand>` works directly).

**Working directory inside container:** `~/.mindsos/` is the default
state dir when `MINDSOS_STATE_DIR` is unset. Recipe paths use
`~/.mindsos/<file>` literally (NEVER `$MINDSOS_STATE_DIR/...` — the
shell may have it unset; see `feedback_state_dir_env_var.md`).

#### Task 1 [Linux] — Sanity: schema state-file version constants are at 3

```
docker compose run --rm mindsos --version
docker compose run --rm mindsos-test pytest tests/phase_05d/test_state_v3_schema_migration.py::TestVersionConstants -q
```

→ expect: doctor version reports `0.0.0+phase05d`; test class passes.

#### Task 2 [Linux] — Build a schema with all four vocabs registered

```
docker compose run --rm mindsos metagraph-schema create --name ms
docker compose run --rm mindsos metagraph-schema add-intergraph-edge-type --schema ms --type-name EVOKES
docker compose run --rm mindsos metagraph-schema add-intergraph-hyperedge-type --schema ms --type-name COMPOSED_OF
docker compose run --rm mindsos metagraph-schema add-meta-edge-type --schema ms --type-name LINKS_TO --json
docker compose run --rm mindsos metagraph-schema add-meta-hyperedge-type --schema ms --type-name GROUPS --json
```

→ expect: each verb exits 0. `--json` outputs include `type_name` +
`allowed_*_graphs` empty arrays + `attached_metagraphs: []`. The
meta-hyperedge JSON has NO `ordered` key (P1 C lock).

#### Task 3 [Linux] — Schema state-file shape

```
docker compose run --rm mindsos cat ~/.mindsos/metagraph-schema-ms.json
```

→ expect: JSON with `_state_version: 3`, `meta_edge_types: [...]` (1 entry),
`meta_hyperedge_types: [...]` (1 entry), and the existing
`intergraph_*_types` arrays.

#### Task 4 [Linux] — Build a metagraph + attach + add metaedge under schema constraints

```
docker compose run --rm mindsos graph create --name ont --role ontology
docker compose run --rm mindsos graph create --name lex --role lexicon
docker compose run --rm mindsos metagraph create --name mg
docker compose run --rm mindsos metagraph add-graph --name mg --graph ont
docker compose run --rm mindsos metagraph add-graph --name mg --graph lex
docker compose run --rm mindsos metagraph attach-schema --name mg --schema ms
docker compose run --rm mindsos metagraph add-metaedge --name mg --source-graph ont --target-graph lex --type LINKS_TO --json
```

→ expect: each step exits 0. Attach exits 0 (eager-attach passes — empty
metaedge collection). Add-metaedge JSON shows `type_name: LINKS_TO`.

#### Task 5 [Linux] — Vocab-gap refusal on add_metaedge

```
docker compose run --rm mindsos metagraph add-metaedge --name mg --source-graph ont --target-graph lex --type UNDECLARED
```

→ expect: exit 1; stderr contains `Unknown meta-edge type: 'UNDECLARED'`.

#### Task 6 [Linux] — Role constraint enforcement

```
docker compose run --rm mindsos metagraph-schema add-meta-edge-type --schema ms --type-name STRICT_LINK --allowed-source-graph concepts --allowed-target-graph theory
```

→ expect: exit 0; stderr contains schema-mutation footgun warning
listing `mg`.

```
docker compose run --rm mindsos metagraph attach-schema --name mg --schema ms
docker compose run --rm mindsos metagraph add-metaedge --name mg --source-graph ont --target-graph lex --type STRICT_LINK
```

→ expect: re-attach exits 0 (existing LINKS_TO metaedge still passes).
Add STRICT_LINK exits 1; stderr names "source graph role 'ontology'"
violation against `allowed_source_graphs: ['concepts']`.

#### Task 7 [Linux] — Validate verb (P9 B + P32 A)

```
docker compose run --rm mindsos metagraph-schema validate --metagraph mg --json
```

→ expect: exit 0; JSON `{passed: true, schema_name: "ms", metagraph_name:
"mg", violations: []}`. NO `vocab_fingerprint_match` field (P40 A).

```
docker compose run --rm mindsos metagraph-schema validate --metagraph nonexistent
```

→ expect: exit 2 (resource not found per P41 A).

```
docker compose run --rm mindsos metagraph create --name unattached
docker compose run --rm mindsos metagraph-schema validate --metagraph unattached
```

→ expect: exit 3 (no usable schema per P41 A).

```
docker compose run --rm mindsos metagraph-schema validate --metagraph unattached --schema ms
```

→ expect: exit 0 (P32 A — explicit `--schema` overrides "no attached"
case).

#### Task 8 [Linux] — Empty-vocab pass-silently regression (P39 A — 05c-migration safety)

```
docker compose run --rm mindsos metagraph-schema create --name empty_ms
docker compose run --rm mindsos metagraph attach-schema --name mg --schema empty_ms
```

→ expect: detach + attach exit 0. The existing `LINKS_TO` metaedge
passes silently because `empty_ms` has empty `meta_edge_types: []` and
`strict=false`.

#### Task 9 [Linux] — Round-trip + reattach without consent flag (P31 A)

```
docker compose run --rm mindsos metagraph attach-schema --name mg --schema ms
docker compose run --rm mindsos metagraph-schema add-meta-edge-type --schema ms --type-name NEW_RELATION
docker compose run --rm mindsos metagraph attach-schema --name mg --schema ms
```

→ expect: each step exits 0. Re-attach succeeds without
`--accept-vocab-change` (P31 A — no consent mechanism). Schema-mutation
footgun stderr warning emitted on add.

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
docker compose run --rm mindsos confirm-phase --phase 05d --notes-file notes-phase-05d.md
```

→ expect: exit 0; generates `confirmation_docs/PHASE_05d_CONFIRMED.md`.

### Hotfix ledger (fill if issues surface during tester run)

*(none yet)*

### Open questions surfaced during testing

*(none yet)*
