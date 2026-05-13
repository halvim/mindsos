---
last_confirmed_phase: 07
---

# `mindsos persistence` — Phase 07

Five verbs that bridge JSON state files (`~/.mindsos/<kind>-<name>.json`,
authoritative per M0 B) and the FalkorDB-side projection:

| Verb | Purpose |
|------|---------|
| `sync --graph X [--replace]` | Project a Graph JSON → FalkorDB (additive default; `--replace` does DETACH DELETE + rewrite). |
| `load --graph X [--to-json] [--force]` | Reconstruct Graph from FalkorDB (stdout summary default; `--to-json` writes a sibling `.fromdb.json`). |
| `diagnose` | Connectivity + 14-index presence + WAL uncommitted count. |
| `verify [--metagraph M \| --graph G] [--source=memory\|db]` | 5-bucket integrity scanner (full on memory; 3-bucket partial on db+graph). |
| `inspect-state` | Rich-table list of FalkorDB contents (`--json` opt-in). |

## Prerequisites

A live FalkorDB sidecar reachable at the host/port carried by the
`[falkordb]` manifest section + env precedence (`FALKORDB_HOST` /
`FALKORDB_PORT` win; `FALKORDB_PASSWORD` is env-only per P15 A; no
`FALKORDB_GRAPH` env per P86 B). The Compose `mindsos-test` profile
includes FalkorDB; `docker compose up -d falkordb` brings it up.

## `sync --graph X [--replace]`

Project the JSON state for graph `X` into FalkorDB.

- **Additive default** (P18 D): MERGE-on-id. Removing a node in the
  JSON file does NOT remove it from FalkorDB; use `--replace`.
- **`--replace`** does DETACH DELETE of every `:Node` / `:HyperEdge`
  / `:Tombstone` scoped by `graph_id`, then rewrites from JSON.
- **`--replace` refusal** (P91 A): refused if any uncommitted
  `:WALEntry` rows reference the target graph. Recovery: resolve or
  truncate WAL first; exit 2.

```
$ mindsos persistence sync --graph alice-lexicon
OK graph 'alice-lexicon' synced to FalkorDB (nodes=42, edges=128, hyperedges=3, replace=False)
```

## `load --graph X [--to-json] [--force]`

Reconstruct Graph from FalkorDB. Default emits a fixed-shape stdout
summary (P52 A):

```
name: alice-lexicon
graph_id: 4d2a...
role: lexicon
schema_name: ontology_v3
nodes: 42
edges: 128
hyperedges: 3
metagraph_name: none
```

`--to-json` writes the reconstructed graph to a sibling file
`~/.mindsos/graph-<name>.fromdb.json` per P85 B (canonical state file
never overwritten). Use `--force` to replace an existing
`.fromdb.json`.

## `diagnose`

Read-only health check:

```
$ mindsos persistence diagnose
connectivity: ok
indexes_present: 14 / expected: 14
wal_uncommitted: 0
```

## `verify [--metagraph M | --graph G] [--source=memory|db]`

Integrity scanner. `--source=memory` (default) loads the JSON state
and runs the full 5-bucket scanner. `--source=db` reads from
FalkorDB:

- `--source=db --graph G` runs a 3-bucket **partial scanner** per
  P98 A (`duplicate_ids` restricted to graph labels,
  `orphan_hyperedges`, `dangling_tombstones`). The 2
  Metagraph-context buckets (`cross_graph_edges`, `orphan_metaedges`)
  report `[skipped — requires --source=memory --metagraph M]`.
- `--source=db --metagraph M` is **refused** in Phase 07 (the
  metagraph_loader lands in Phase 08); use `--source=memory` for
  metagraph-scoped verify.

Exit codes per P64 A: `0` clean / `1` CLI usage error / `2` system
error (DB unreachable on `--source=db`) / `3` drift findings.

## `inspect-state`

Rich-table listing of FalkorDB contents per P99 A:

```
$ mindsos persistence inspect-state
       Graphs
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ name          ┃ id           ┃ role   ┃
...
```

`--json` opt-in emits machine-readable JSON.

## Doctor self-test FalkorDB error matrix (P59 A)

`mindsos doctor --self-test` reports one of five cells when probing
FalkorDB:

| Cell | Condition | Behaviour |
|------|-----------|-----------|
| no-section | `[falkordb]` manifest section absent | Warning (not fail). |
| section-ok | Section present + ping returns version | Pass. |
| refused | Connection refused | Fail with `falkordb unreachable: ...`. |
| auth-fail | Driver returns auth error | Fail with driver message. |
| malformed | Section present but missing host/port/graph | Fail; lists missing keys. |

Per P75 B — doctor collects all failures across all checks and exits
non-zero with a combined report (does not fail-fast on the first).

## Rollback recipe (Mac side)

```
docker compose down -v
rm -rf .mindsos/falkordb-data/
git checkout phase-06-confirmed
pip install --user -e . --force-reinstall --no-deps --break-system-packages
docker compose build
```

Lockfile re-run is NOT needed because `falkordb` was already pinned
pre-Phase-07 in `requirements.in` (P46 A); `requirements.txt` is
unchanged across the rollback boundary.

## Recipe — pre-build before confirm-phase

Per `feedback_confirm_phase_timeout.md` (and P93): always pre-build
the test image before `mindsos confirm-phase`:

```
[Linux] docker compose --profile test build mindsos-test
[Linux] mindsos confirm-phase --phase 07 --notes-file notes-phase-07.md
```

The wrapper's 900-second timeout starts at invocation; pre-building
keeps the budget reserved for pytest, not for Docker image building.
