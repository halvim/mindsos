---
last_confirmed_phase: 05b
---

# `mindsos metagraph-schema`

Phase 05b's metagraph-level schema container. Parallel to
`mindsos schema` (which carries graph-level `NodeType` /
`EdgeType` / `HyperEdgeType` vocabularies); `mindsos metagraph-schema`
carries the metagraph-level `IntergraphEdgeType` vocabulary (and in
Phase 05c, `MetaEdgeType` / `MetaHyperEdgeType` /
`IntergraphHyperEdgeType` will join it).

## Subcommands

```
mindsos metagraph-schema create --name <NAME> [--strict] [--json]
mindsos metagraph-schema inspect --name <NAME> [--json]
mindsos metagraph-schema list [--json]
mindsos metagraph-schema reset (--name NAME | --all) [--force] [--yes] [--json]
mindsos metagraph-schema add-intergraph-edge-type
                                   --schema <NAME> --type-name <TYPE>
                                   [--allowed-source-type <NT>]...
                                   [--allowed-target-type <NT>]...
                                   [--allowed-source-graph <ROLE>]...
                                   [--allowed-target-graph <ROLE>]...
                                   [--prop-type k=<PROPTYPE>]...
                                   [--description STR]
                                   [--json]
```

State files live at `${MINDSOS_STATE_DIR or ~/.mindsos}/metagraph-schema-<name>.json`
(v=1 in Phase 05b).

## Strict mode

Per Pushback 5-A, `MetagraphSchema(strict=False)` mirrors Phase 04
`Schema(strict=False)`: gates per-type **property-type** validation
only. Type-existence (`require_intergraph_edge_type`) is mandatory
whenever a schema is attached, regardless of `strict`. A non-strict
schema accepts any property values for a registered type; a strict
schema enforces the `--prop-type k=v` map.

## IntergraphEdgeType

Required: `--type-name` (cypher rel-type per ADR-0021;
`^[A-Z][A-Z0-9_]{0,63}$`).

Optional constraint surfaces:

* `--allowed-source-type <NT>` (repeatable) — every source `Node.type_name`
  must be in this set. Empty = any.
* `--allowed-target-type <NT>` (repeatable) — same for target.
* `--allowed-source-graph <ROLE>` (repeatable) — Pushback 4-A:
  *role-based* graph constraint. The source graph's `Graph.role`
  must be in this set. `Graph.role=None` is unmatchable when the
  constraint is non-empty (Python set semantics: `None not in
  frozenset({"lexicon"})`).
* `--allowed-target-graph <ROLE>` (repeatable) — same for target.
* `--prop-type k=<vocab>` (repeatable) — Phase 04 8-variant
  `PropertyType` vocabulary.
* `--description <STR>` — optional human-readable description.

## Attach + detach

```
mindsos metagraph attach-schema --name <MG> --schema <MS>
mindsos metagraph detach-schema --name <MG>
```

(Live on the `mindsos metagraph` subapp, not on `mindsos
metagraph-schema` — bindings are metagraph-side per Pushback 3-A.)

`attach-schema` runs **eager** validation over every existing
`intergraph_edge` (Pushback 7-A + 9-A + 17-A + 29-A). First
violation raises with the offending `edge_id`; state unchanged.
Pushback 9-A scope: 05b's eager walk validates only
`intergraph_edges`; existing `metaedges` / `metahyperedges` are NOT
validated (no `MetaEdgeType` / `MetaHyperEdgeType` vocabularies in
05b — they land in 05c). Pushback 19-B: stderr warning if the schema
references roles not satisfied by any contained graph.

Per Pushback 12-A, only one schema may be attached per metagraph at
a time. `attach-schema` while a different schema is attached refuses
with `IdentityError("detach first")`. Per Pushback 32-D, re-attaching
the same schema by name runs **fresh** eager validation (NOT a
silent no-op) — surfaces drift from schema mutation since the
previous attach.

`detach-schema` is a **unified command** (Pushback 28-A + DMS-A) with
internal raw-JSON fallback:

* **Normal path**: rehydrate metagraph → `mg.detach_schema()`;
  refuses with exit 1 if no schema attached.
* **Raw-JSON fallback**: if the schema state file is *malformed*
  (rehydration raises), mutate the metagraph state file directly,
  set `schema_name: None`, write atomically. JSON output carries
  `used_raw_fallback: true`.

Schema state file *missing* (FileNotFoundError) is handled silently
on the normal path: `_state_to_metagraph` sets `schema_name` to the
dangling reference without raising; `detach-schema` clears it.

## Schema mutation while attached (Phase 04 carry-forward footgun)

Per Pushback 23-A, `mindsos metagraph-schema add-intergraph-edge-type`
walks every metagraph state file for `schema_name == <target>`. If
any are attached, emits stderr warning listing them. The footgun:
attached metagraphs do NOT re-validate against the new vocabulary.
Tester runs `mindsos metagraph attach-schema --name <MG> --schema <X>`
on each attached metagraph to surface drift (Pushback 32-D — re-attach
is fresh validation).

Documented as carry-forward; future-work Pushback 34-B addresses the
broader symmetric backfix across all schema kinds.

## Reset orphan check (Pushback 20-A)

`mindsos metagraph-schema reset --name <X>` walks every
`metagraph-*.json` state file checking for `schema_name == X`.

* If any metagraphs reference X: refuse with exit 1 listing them.
  Tester recovery options: `mindsos metagraph detach-schema --name <MG>`
  on each, OR re-run with `--force --yes` to strip back-pointers.
* `--force --yes` strips `schema_name` references from referenced
  metagraphs (warning emitted to stderr) before deleting the schema
  state file. The metagraphs become un-validated; existing
  intergraph_edges retain their `type_name` strings but are no
  longer schema-checked.

`--all --yes` walks every `metagraph-schema-*.json` and applies the
same strip-then-delete pattern.

## Examples

### Build a strict schema with role-based constraints

```sh
mindsos metagraph-schema create --name ms1 --strict
mindsos metagraph-schema add-intergraph-edge-type \
    --schema ms1 --type-name EVOKES \
    --allowed-source-type Word --allowed-target-type Concept \
    --allowed-source-graph lexicon --allowed-target-graph concepts \
    --prop-type weight=float \
    --description "Lex→Concept evocation"
```

### Attach + add an edge that satisfies all constraints

```sh
mindsos metagraph attach-schema --name mg --schema ms1 --json
mindsos metagraph add-intergraph-edge \
    --name mg \
    --source-graph lex --source-node n_cat \
    --target-graph cpt --target-node n_concept \
    --type EVOKES --prop weight=0.5
```

### DMS-A recovery: stale `schema_name` after manual schema deletion

```sh
rm $MINDSOS_STATE_DIR/metagraph-schema-ms1.json
mindsos metagraph detach-schema --name mg --json
# JSON output: {"metagraph": "mg", "previous_schema": "ms1",
#               "detached": true, "used_raw_fallback": false}
```
