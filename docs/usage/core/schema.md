---
last_confirmed_phase: 04-v2
---

# Schemas

Phase 04 introduces the **`Schema`** primitive — a typed vocabulary
(`NodeType` + `EdgeType` + `PropertyType`) that you can attach to a
`Graph` to enforce node/edge types and (optionally) per-property value
types. Schemas are **opt-in**: a graph without a schema behaves exactly
like Phase 03.

**Phase 04-v2** extends the vocabulary with **`HyperEdgeType`** —
n-ary edge types (`allowed_member_types`) — and makes
`HyperEdge.type_name` a required field. See the *HyperEdgeType* section
below and the *Migration from Phase 03 / Phase 04* section for the
v=2 → v=3 graph state-file migration story.

## Quick tour

```sh
# 1. Declare a strict schema.
mindsos schema create --name people-schema --strict

# 2. Add NodeTypes with property-type maps.
mindsos schema add-node-type --schema people-schema --type-name Person \
                              --prop-type age=int --prop-type name=string
mindsos schema add-node-type --schema people-schema --type-name Org

# 3. Add an EdgeType. The Cypher rel-type rule (ADR-0021) still applies —
#    rel-types must match ^[A-Z][A-Z0-9_]{0,63}$.
mindsos schema add-edge-type --schema people-schema --type-name WORKS_AT \
                              --allowed-source Person --allowed-target Org \
                              --prop-type since=int

# 4. Inspect or list.
mindsos schema inspect --name people-schema --json
mindsos schema list

# 5. Use the schema in a graph (two ways).

# (a) Attach at creation time:
mindsos graph create --name people --role ontology --schema people-schema

# (b) Attach an existing graph (eager validation; first violation rejects).
mindsos graph create --name folks
mindsos graph add-node Alice --name folks --type Person --node-id n-alice --prop age=30
mindsos graph attach-schema --name folks --schema people-schema

# 6. Schema-validated property updates (merge by default; --replace swaps).
#    Note: --node-id (NOT --node) — Phase 04 renamed for parity with add-node.
mindsos graph set-prop --name folks --node-id n-alice --prop age=31
mindsos graph set-prop --name folks --edge-id e-1     --prop weight=0.7 --replace

# 7. Detach a schema (e.g. to recover a graph with a dangling reference).
mindsos graph detach-schema --name folks
```

## CLI reference

### `mindsos schema`

| Subcommand | Purpose |
|---|---|
| `create --name X [--strict] [--json]` | Declare a new schema. |
| `add-node-type --schema X --type-name T [--prop-type k=V]... [--description TEXT] [--json]` | Register a NodeType. |
| `add-edge-type --schema X --type-name REL [--allowed-source NT]... [--allowed-target NT]... [--prop-type k=V]... [--description TEXT] [--json]` | Register an EdgeType. |
| `add-hyperedge-type --schema X --type-name REL [--allowed-member NT]... [--prop-type k=V]... [--description TEXT] [--json]` | **Phase 04-v2.** Register a HyperEdgeType (n-ary; symmetric across all members; empty `--allowed-member` permitted per AME-1, mirrors EdgeType). |
| `inspect --name X [--json]` | Report strictness + registered types (now includes `hyperedge_types`). |
| `list [--json]` | Enumerate all schemas. |
| `reset (--name X | --all) [--force] [--json]` | Delete schema(s). Refuses if any graph references the targeted schema(s); `--force` overrides. |

### `mindsos graph` (Phase 04 additions)

| Subcommand | Purpose |
|---|---|
| `create --name X [--role R] [--schema S] [--json]` | `--schema S` attaches at creation time. |
| `attach-schema --name G --schema S [--json]` | Attach + eager-validate. Re-attach permitted; `previous_schema` in JSON output. Empty-strict warning emitted on stderr. |
| `detach-schema --name G [--json]` | Clear `schema_name`. Operates on raw JSON — works even when the referenced schema is missing. |
| `set-prop --name G (--node-id ID | --edge-id ID | --hyperedge-id ID) --prop k=v ... [--replace] [--json]` | Schema-validated property update. **Phase 04-v2 adds `--hyperedge-id` to the mutex.** |
| `add-hyperedge --name G --type REL --member ID [--member ID]... [--label L] [--prop k=v]... [--hyperedge-id ID] [--json]` | **Phase 04-v2 — `--type` required** (cypher rel-type regex). Schema-validated when attached. |
| `update-hyperedge-type --name G --hyperedge-id ID --type NEW [--json]` | **Phase 04-v2 (UHT-1).** Legacy-migration recovery — update a hyperedge's `type_name` from the SENT-1 sentinel `UNSPECIFIED` to a real type. Asymmetric note: Edge.type_name and Node.type_name remain immutable. |

## State file

Schemas persist as JSON state files at
`${MINDSOS_STATE_DIR or ~/.mindsos}/schema-<name>.json` (parity with the
Phase 03 graph state file). Schemas can be referenced by multiple graphs;
deleting a schema while a graph references it is refused by default —
see [Schema reset and orphans](#schema-reset-and-orphans).

Schema state-file v=1 shape (Phase 04 introduces this format —
`SCHEMA_STATE_VERSION = 1`):

```json
{
  "_state_version": 1,
  "name": "<name>",
  "strict": false,
  "node_types": [
    {
      "name": "<name>",
      "property_types": {"<key>": "<PropertyType.value>"},
      "description": "<text-or-null>"
    }
  ],
  "edge_types": [
    {
      "name": "<NAME>",
      "allowed_sources": [ "..." ],
      "allowed_targets": [ "..." ],
      "property_types": {"<key>": "<PropertyType.value>"},
      "description": "<text-or-null>"
    }
  ]
}
```

Top-level `node_types` / `edge_types` lists are sorted by `name` on save;
`allowed_sources` / `allowed_targets` are sorted lists. Atomic writes via
`<path>.tmp` + `os.replace`.

## Graph state-file v=2 (Phase 04 bump)

Phase 03 wrote graph state files at `_state_version: 1`. **Phase 04
bumps to `_state_version: 2`**, adding the optional `schema_name` field.

Phase 04 binary accepts both v=1 (legacy, no `schema_name` field — the
loader treats missing as `null`) and v=2; writes v=2 on every save.
**The v=1 → v=2 migration is one-way**: the first Phase 04 mutation
(any `add-node`, `set-prop`, `attach-schema`, `detach-schema`, etc.)
upgrades the file. Phase 03 binary then refuses to read it via the
existing strict-version contract.

```json
{
  "_state_version": 2,
  "graph_id": "<uuid4>",
  "name": "<name>",
  "role": "<role-or-null>",
  "schema_name": "<schema-name-or-null>",
  "nodes": [ ... ],
  "edges": [ ... ],
  "hyperedges": [ ... ]
}
```

## Migration from Phase 03

If you have `~/.mindsos/graph-*.json` files written by Phase 03 binary,
they all start at `_state_version: 1`. Here's what Phase 04 does with
them:

### v=1 reads work transparently

`mindsos graph inspect`, `list-nodes`, etc. on a Phase 03 file all
succeed. The `schema_name` field is treated as `null` (no schema
attached). The file on disk stays at v=1 until you mutate it.

### First mutation upgrades to v=2

Any write (`add-node`, `set-prop`, `attach-schema`, etc.) re-serialises
the file at `_state_version: 2`. After that, a Phase 03 binary running
against the file gets the strict-version error: `this CLI supports v1`.
This is the documented strict-version contract working correctly — not
a regression.

### Reserved-key / non-primitive recovery

Phase 03 had no `validate_user_properties` enforcement, so a Phase 03
graph could contain reserved-key properties (`{"id": "evil"}`,
`{"type": "..."}`, etc.) or non-primitive values (mixed lists, dicts).
Phase 04 enforces both:

| Operation | Behaviour on legacy bad data |
|---|---|
| `inspect` / `list-*` (read-only) | **Tolerated.** Loads cleanly via `_validate=False` rehydration. |
| `add-node` / `add-edge` / `add-hyperedge` (fresh) | **Validated.** Bad data fails with `PropertyShapeError`. |
| `set-prop` (default merge) | **Validated.** The full merged candidate (existing + new) goes through `validate_user_properties`; legacy reserved keys re-trigger the error. |
| `set-prop --replace` | **Recovery path.** Existing non-ref keys are dropped; `ref:*` keys preserved; user-supplied properties applied. Use this to strip reserved keys. |
| `attach-schema` | **Validated.** Eager replay validates user-properties on every element; rejects on first violation. |

**Recovery recipe** for a graph poisoned by Phase 03 with reserved-key
properties:

```sh
# Identify the offending node ids by inspecting the state file directly.
cat ~/.mindsos/graph-<name>.json | python -m json.tool

# For each poisoned node, replace its property bag with clean data:
mindsos graph set-prop --name <name> --node-id <id> \
    --prop name=Alice --prop age=30 --replace
# (ref:* keys survive; reserved 'id'/'type'/etc. are dropped.)
```

### Severe corruption

If a Phase 03 graph has a property structure that even `--replace`
can't clean (e.g. a non-primitive value the user wants to keep), the
recovery path is hand-edit the JSON state file directly, OR
`mindsos graph reset --name <name>` and rebuild.

### Rolling back to Phase 03

If Phase 04 is superseded and you need to revert to `phase-03-confirmed`:

* Cleanest: `rm -rf ~/.mindsos/graph-*.json` and rebuild from scratch.
* Manual downgrade: for each v=2 file, edit the JSON to set
  `"_state_version": 1` and remove the `"schema_name"` field. Phase 03
  binary will then read it.

This is the Phase 04 supersession risk documented in the PHASE_MAP row.

## PropertyType vocabulary

The `--prop-type` flag accepts these eight values (drawn verbatim from
the parent project — Phase 04 ships the full vocabulary, no subset):

| Vocab value      | Python equivalent          |
|------------------|----------------------------|
| `string`         | `str`                      |
| `int`            | `int` (NOT `bool`)         |
| `float`          | `float` (or `int` — coerced by FalkorDB) |
| `bool`           | `bool`                     |
| `list[string]`   | homogeneous `list[str]`    |
| `list[int]`      | homogeneous `list[int]` (excludes `bool`) |
| `list[float]`    | `list[int|float]`           |
| `list[bool]`     | homogeneous `list[bool]`   |

**Watch out:** under strict typing, `True` / `False` do **not** satisfy
`int` even though `bool` is a Python subclass of `int`. This is
deliberate — silently accepting bools where ints are expected is a
common bug source.

A schema state file containing an unrecognised PropertyType vocab value
(e.g. `"uint32"`) fails to load with a structured error message listing
the valid vocab — the CLI exits 1 rather than printing a Python
traceback.

## Strict vs non-strict

* **`--strict`** — `Schema.validate_node_properties` /
  `validate_edge_properties` enforce the per-type `property_types`
  map. A property whose value type doesn't match its declared
  `PropertyType` exits 1 with `PropertyShapeError`. Properties not
  declared on the type are allowed only if the type's `property_types`
  map is empty (the type author opted out for that type).
* **non-strict (default)** — types are still registered (so unknown
  type names still raise `UnknownTypeError`), but per-property value
  types are NOT enforced. The user-property contract still applies
  (reserved keys, primitive values only).

## Eager attach validation

`mindsos graph attach-schema --name <GRAPH> --schema <SCHEMA>` runs
**every existing node, edge, and hyperedge** through the schema's
validation hooks before persisting the attachment. The first violation
prints a structured error including the offending element id —
e.g. `node n-alice: PropertyShapeError: ...` — and exits 1. The graph
state file is **not** modified on rejection.

This was a deliberate phase-chat decision (eager over lazy):
half-validated graphs are a footgun worse than the cost of a re-walk
on attach.

### Re-attach

`attach-schema` is **idempotent-friendly** — you can attach a different
schema to a graph that already has one. The new schema replaces the
old after eager re-validation against the new schema's rules. The JSON
output reports `previous_schema` so scripts can detect the swap.

### Empty-strict-schema footgun

If you attach a strict schema with **zero NodeTypes** to a graph,
attach itself succeeds (no violations to find), but every subsequent
`mindsos graph add-node --type <X>` will fail with
`UnknownTypeError: Unknown node type: '<X>'` because no NodeType is
registered. Phase 04 emits a stderr warning at attach time when this
condition holds; the warning names two recovery routes:

```sh
# Add NodeTypes to the schema:
mindsos schema add-node-type --schema <SCHEMA> --type-name <NAME>

# OR detach the schema:
mindsos graph detach-schema --name <GRAPH>
```

## Detach schema

`mindsos graph detach-schema --name <GRAPH>` clears the `schema_name`
field on the graph state file. It operates on the **raw JSON dict**
(not via schema rehydration), which means it works EVEN WHEN the
referenced schema state file has been deleted — the primary recovery
path for a graph with a dangling schema reference.

```sh
# Recovery from a deleted schema:
mindsos schema reset --name people-schema --force  # also breaks graphs
mindsos graph inspect --name folks                  # exits 1 — schema missing
mindsos graph detach-schema --name folks            # clears schema_name; recovers
mindsos graph inspect --name folks                  # exits 0 — no schema attached
```

`detach-schema` exits 1 if no schema is currently attached
(matches Phase 03's fail-loudly pattern on no-op operations).

## Schema reset and orphans

`mindsos schema reset --name X` and `mindsos schema reset --all` BOTH
walk every `graph-*.json` in the state dir checking for `schema_name`
references. If any graph references a schema being deleted, reset
**refuses with exit 1** and prints the list of referencing graphs.

```sh
$ mindsos schema reset --name people-schema
Refusing to reset: 2 graph(s) reference schema(s) being deleted. ...
  graph='folks' → schema='people-schema'
  graph='org-tree' → schema='people-schema'
```

`--force` overrides; the resulting graphs will need
`mindsos graph detach-schema` to recover. A stderr warning is emitted
naming the recovery command:

```sh
$ mindsos schema reset --name people-schema --force
ok: deleted schema='people-schema'
count: 1
warning: 2 graph(s) now have dangling schema_name references; run
'mindsos graph detach-schema' on each to recover.
```

## `set-prop` semantics

```sh
# Merge (default).
mindsos graph set-prop --name people --node-id n-alice --prop city=NYC

# Replace.
mindsos graph set-prop --name people --node-id n-alice --prop city=NYC --replace

# Edge variant.
mindsos graph set-prop --name people --edge-id e-1 --prop weight=0.9
```

Exactly one of `--node-id <ID>` / `--edge-id <ID>` is required (mutex;
both or neither exits 2). Routes through schema validation when a
schema is attached. Note: Phase 04 does NOT bump any `_version` field —
the optimistic-concurrency contract from ADR-0127 lands in Phase 07.

### `--replace` and `ref:*` properties

`--replace` swaps the **non-ref** portion of the bag entirely, but
**preserves cross-graph reference properties** (`ref:*` keys) from the
existing bag. User-supplied `ref:*` values overwrite existing on
collision (user values always win).

```sh
# Existing: {name: "Alice", age: 30, ref:anchor: "uuid-1"}
mindsos graph set-prop --name g --node-id n-a --prop city=NYC --replace
# Result:   {city: "NYC", ref:anchor: "uuid-1"}
#           ↑ name, age dropped; ref:anchor preserved.

# Override the ref:
mindsos graph set-prop --name g --node-id n-a --prop ref:anchor=uuid-2 --replace
# Result:   {ref:anchor: "uuid-2"}
```

**Phase 04 has NO CLI path to drop a `ref:*` key.** This is a
deliberate asymmetry — refs are linkage metadata with semantic
significance (cross-graph references); making them harder to drop
than user properties is a feature, not a bug. If you need to drop a
ref in Phase 04, hand-edit the JSON state file. Future Phase 09 ships
proper XRef migration including drop semantics.

## Exit codes

Same conventions as Phase 03 — see [Building graphs](building-graphs.md).

| Code | Meaning |
|---|---|
| `0` | Success. |
| `1` | Domain error (`UnknownTypeError`, `PropertyShapeError`, `CypherError`, `IdentityError`, `SchemaError`, malformed / missing state file, corrupt PropertyType vocab, orphan-bearing schema reset without `--force`, detach-schema on a no-schema graph). |
| `2` | Usage error (missing required arg, malformed flag, empty key, unrecognised `--prop-type` vocab, `--node-id` + `--edge-id` mutex violation, `set-prop` without any `--prop`). |

## ADR references

* **ADR-0017** — NodeType / EdgeType vocabulary (referenced; ADR file
  ports in Phase 38).
* **ADR-0021** — Cypher rel-type identifier validation (Phase 03,
  re-applied at edge-type registration time in Phase 04).
* **ADR-0014** — Layer boundary (Core has no domain logic; Schema is a
  pure type-vocabulary primitive).
* **ADR-0127** — Optimistic concurrency on `_version` (referenced;
  Phase 04 deliberately does NOT bump `_version` on `update_*` —
  Phase 07 ships the OCC machinery).
* **ADR-0130** — Graph-level `properties` bag (deferred to Phase 05/10;
  `validate_namespaced_properties` not ported in Phase 04).
* **ADR-0133** — Soft-delete via `deprecated_at` / `disputed_at`
  (deferred to Phase 10; Phase 04 reserves the keys via
  `RESERVED_PROPERTY_KEYS`).

---

## HyperEdgeType (Phase 04-v2)

Phase 04-v2 — additive scope expansion via the supersession policy
("expansion" trigger per PHASE_MAP §1) — adds `HyperEdgeType` to the
schema vocabulary and makes `HyperEdge.type_name` a required field.

**Locks:** MC-2 (ship HyperEdgeType), HET-1 (`allowed_member_types`
only; no cardinality), AME-1 (empty list permitted), SENT-1 (legacy
sentinel `UNSPECIFIED`), UHT-1 (`update-hyperedge-type` recovery CLI).

```sh
# 1. Declare a HyperEdgeType.
mindsos schema add-hyperedge-type --schema people-schema \
    --type-name ATTENDS \
    --allowed-member Person --allowed-member School \
    --description "n-ary relationship — Person + School + ..."

# 2. Use it. --type is now REQUIRED on add-hyperedge.
mindsos graph add-hyperedge --name folks --type ATTENDS \
    --member n-alice --member n-school

# 3. set-prop now accepts --hyperedge-id (mutex with --node-id / --edge-id).
mindsos graph set-prop --name folks --hyperedge-id he-1 --prop year=2024
```

**Constraint surface (HET-1):** `allowed_member_types` is a flat
`list[str]` — every member's `type_name` must be in the set; no
cardinality bounds; symmetric across all members. Empty list is
permitted (AME-1) — under non-strict accepts any member; under strict
rejects all members until populated. There's no
`update-hyperedge-type-allowed-member` CLI; if you need to change the
allowed set, declare a new HyperEdgeType.

**Re-attach validation extends:** `mindsos graph attach-schema` now
re-validates every existing hyperedge in addition to nodes and edges.
The validation order is **every Node, then every Edge, then every
HyperEdge** — first violation across the three categories surfaces
the offending element id and refuses the attach.

## Migration from Phase 03 / Phase 04 (v=2 → v=3)

Phase 04-v2 bumps the **graph state-file** format from v=2 to v=3
(adds `type_name` per hyperedge entry) AND the **schema state-file**
format from v=1 to v=2 (adds `hyperedge_types` map). Both migrations
are **one-way cumulative** — first Phase 04-v2 mutation upgrades any
pre-current file directly to the current version.

**Cumulative graph migration:** the Phase 04-v2 binary tolerates
v=1 ∪ v=2 ∪ v=3 reads. Pre-v=3 hyperedges receive
`type_name="UNSPECIFIED"` (the SENT-1 sentinel — chosen to satisfy
ADR-0021's cypher rel-type regex). The first mutation writes v=3.

**Strict-mode interaction with `UNSPECIFIED`.** A strict schema
attached to a graph with legacy hyperedges **rejects** them on eager
attach (the schema doesn't have `UNSPECIFIED` in `hyperedge_types`).
Three recovery paths:

1. **Update each legacy hyperedge to a real type** via UHT-1 *before*
   attaching the strict schema:
   ```sh
   mindsos graph update-hyperedge-type --name folks \
       --hyperedge-id he-1 --type PAIR
   ```
2. **Declare an `UNSPECIFIED` HyperEdgeType in the schema** as an
   "escape hatch" that absorbs legacy hyperedges:
   ```sh
   mindsos schema add-hyperedge-type --schema people-schema \
       --type-name UNSPECIFIED \
       --allowed-member Person --allowed-member School
   ```
3. **Recreate the hyperedge** (delete via `remove-hyperedge` if
   available, or reset the graph and rebuild — currently the only path
   for getting rid of legacy hyperedges other than UHT-1).

**Rolling back to Phase 04 (v=2).** Phase 04 binary loading a v=3 file
rejects with `this CLI supports v2`. Recovery:

* Cleanest: `rm -rf ~/.mindsos/graph-*.json && rm -rf ~/.mindsos/schema-*.json`
  and rebuild from scratch.
* Manual JSON downgrade per file:
  - `graph-*.json`: set `"_state_version": 2`; drop the `type_name`
    field from every hyperedge entry.
  - `schema-*.json`: set `"_state_version": 1`; drop the
    `hyperedge_types` field.

Rolling all the way back to Phase 03 layers v=2→v=1 on top of the above
(drop `schema_name`, set `"_state_version": 1`).

## Asymmetry: `update-hyperedge-type` vs Edge / Node

Phase 04-v2 ships **`update-hyperedge-type`** for HyperEdge. There is
no equivalent `update-edge-type` or `update-node-type` — `Edge.type_name`
and `Node.type_name` remain immutable after creation.

**Why the asymmetry:** Phase 04-v2 introduces a new top-level field
on HyperEdge mid-stream; legacy hyperedges loaded under SENT-1 carry
the `UNSPECIFIED` sentinel and need a recovery path. Edge / Node
type_name has no analogous legacy-migration concern; immutability
remains a feature there.
