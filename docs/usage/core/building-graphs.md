---
last_confirmed_phase: 04
---

# Building graphs

The `mindsos graph` CLI (Phase 03 + Phase 04) creates and manipulates an
in-memory `Graph` that persists across invocations as a JSON state file
at `${MINDSOS_STATE_DIR or ~/.mindsos}/graph-<name>.json`.

Phase 04 adds:

* `mindsos graph create --schema <NAME>` — attach a Phase 04 schema at
  creation time.
* `mindsos graph attach-schema --name <GRAPH> --schema <SCHEMA>` —
  attach a schema to an existing graph; eager validation rejects
  non-conformant data with the offending element id named in the error.
* `mindsos graph detach-schema --name <GRAPH>` — clear `schema_name`
  on a graph (recovery path for dangling schema references).
* `mindsos graph set-prop` — schema-validated property updates. Use
  `--node-id <ID>` / `--edge-id <ID>` (renamed from `--node` / `--edge`
  in Phase 04 for parity with `add-node --node-id`). `--replace`
  preserves `ref:*` cross-graph reference keys; user-supplied
  `ref:*` values overwrite existing on collision.

**State file format BUMPED to v=2** in Phase 04. Phase 03 wrote v=1;
Phase 04 reads both v=1 (legacy) and v=2; writes v=2 on every save.
v=1 → v=2 migration is one-way — see [Schemas → Migration from
Phase 03](schema.md#migration-from-phase-03).

See [Schemas](schema.md) for the full schema surface.

## Quick tour

```sh
# Create a graph with an optional semantic role.
mindsos graph create --name people --role ontology

# Add nodes (the <VALUE> can be any JSON value; bare strings are fine).
mindsos graph add-node Alice --name people --type Person --node-id n-alice
mindsos graph add-node Acme  --name people --type Org    --node-id n-acme
mindsos graph add-node Bob   --name people --type Person --node-id n-bob

# Add an edge — the --type must be a valid Cypher rel-type
# (uppercase + digits + underscores per ADR-0021).
mindsos graph add-edge --name people --source n-alice --target n-acme \
                       --type WORKS_AT --label "employed since 2024"

# Add a hyperedge across N members.
mindsos graph add-hyperedge --name people \
                            --member n-alice --member n-acme --member n-bob \
                            --label project-X

# Inspect counts.
mindsos graph inspect --name people --json

# List nodes / edges / hyperedges (sorted by id, deterministic output).
mindsos graph list-nodes --name people
mindsos graph list-edges --name people
mindsos graph list-hyperedges --name people

# Discover what graphs exist in $MINDSOS_STATE_DIR.
mindsos graph list

# Clear when done.
mindsos graph reset --name people
# Or wipe everything:
mindsos graph reset --all
```

## State file location

* Default: `~/.mindsos/graph-<name>.json` (parity with Phase 02
  `identity-registry-<scope>.json`).
* Override: `export MINDSOS_STATE_DIR=/path/to/dir`.
* `<name>` must match `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$` — invalid names
  exit 2 (prevents accidental path traversal).

## State file v=2 schema (Phase 04 bump)

```json
{
  "_state_version": 2,
  "graph_id": "<uuid4>",
  "name": "<name>",
  "role": "<role-or-null>",
  "schema_name": "<schema-name-or-null>",
  "nodes":      [ {"node_id", "value", "type_name", "properties"} ],
  "edges":      [ {"edge_id", "source_id", "target_id",
                   "type_name", "label", "properties"} ],
  "hyperedges": [ {"edge_id", "member_ids" (sorted), "label", "properties"} ]
}
```

* All three top-level lists are sorted by id on save (byte-stable diffs).
* `_state_version` is strict on load — Phase 04 binary accepts v=1 and
  v=2; > 2 raises an error.
* `schema_name` is **mandatory in v=2** (may be `null`). Phase 03 v=1
  state files (no `schema_name` field) load fine; on the next mutation
  Phase 04 re-saves at v=2 with `schema_name: null`. **The v=1 → v=2
  migration is one-way** — Phase 03 binary can no longer read the file
  after Phase 04 has touched it.
* Atomic writes via `<path>.tmp` + `os.replace`; a Ctrl-C mid-write
  cannot corrupt the canonical file.

See [Schemas → Migration from Phase 03](schema.md#migration-from-phase-03)
for the full migration story including reserved-key recovery.

## `--prop k=v` and `<VALUE>` parsing

Both `--prop k=v` values and the positional `<VALUE>` for `add-node`
follow the same JSON-then-string fall-back rule:

| Input | Stored as |
|---|---|
| `--prop count=42` | int `42` |
| `--prop active=true` | bool `True` |
| `--prop tags='["a","b"]'` | list `["a", "b"]` |
| `--prop nick=Alice` | string `"Alice"` |
| `--prop tags='[bad'` | string `"[bad"` (malformed JSON falls back) |

The fall-back is deliberate (simpler than sniffing). To intentionally
store a raw string that *looks* like JSON, prefix-quote it:
`--prop tags='"[1,2]"'`.

`--prop` splits on the first `=` only, so `--prop note='hello=world'`
parses as `note` → `"hello=world"`.

## Cypher rel-type validation (ADR-0021)

Edge `--type` is enforced against `^[A-Z][A-Z0-9_]{0,63}$` (strict
uppercase, max 64 chars). Both lowercase (`works_at`) and mixed-case
(`Works_At`) are rejected with a `CypherError` exit 1.

This is FalkorDB-injection defence — relationship types splice verbatim
into Cypher queries; the conservative shape eliminates the attack
surface.

## Cross-invocation persistence — gotchas

The state file persists naturally on the host (developer's `~/.mindsos/`).
Inside a Docker container with `--rm`:

```sh
# This DOES NOT persist between invocations — --rm wipes the container fs.
docker compose run --rm mindsos graph create --name foo
docker compose run --rm mindsos graph inspect --name foo   # not found

# Work-arounds:
# (a) Run from the host venv (pip install -e .). State file lives in
#     ~/.mindsos and persists naturally.
# (b) Bind-mount the state dir:
docker compose run --rm -v ~/.mindsos:/root/.mindsos mindsos \
                       graph create --name foo
```

Same gotcha as Phase 02 identity-registry — documented to set tester
expectations.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success. |
| `1` | Domain error (`IdentityError`, `SchemaError`, `CypherError`, `UnknownTypeError`, `PropertyShapeError`, malformed / missing state file). |
| `2` | Usage error (missing required arg, malformed flag, empty `--prop` key, mutex flag violation on `set-prop`, `reset` with neither `--name` nor `--all`, invalid `<name>` regex). |
