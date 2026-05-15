---
last_confirmed_phase: 08
---

# `mindsos persistence` — Phase 08

Five verbs that bridge JSON state files (`~/.mindsos/<kind>-<name>.json`,
authoritative per M0 B) and the FalkorDB-side projection. Phase 08
extends `sync`, `load`, and `verify` with metagraph-scoped variants and
a `--graph G | --metagraph M` mutex (R4-6 A — exit 1 on combo). The
new metagraph round-trip is documented in
[Phase 08 additions](#phase-08-additions) at the bottom of the page.

| Verb | Purpose |
|------|---------|
| `sync --graph X [--replace]` | Project a Graph JSON → FalkorDB (additive default; `--replace` does DETACH DELETE + rewrite). |
| `sync --metagraph M [--replace]` | Phase 08 — Project a Metagraph JSON → FalkorDB; `--replace` refuses on dependent instances / XRef / uncommitted WAL (RPB-4 C). |
| `load --graph X [--to-json] [--force]` | Reconstruct Graph from FalkorDB (stdout summary default; `--to-json` writes a sibling `.fromdb.json`). |
| `load --metagraph M [--to-json] [--json]` | Phase 08 — Reconstruct Metagraph from FalkorDB (9-line flat summary default; `--json` machine-readable; `--to-json` writes `~/.mindsos/metagraph-<name>.fromdb.json` sibling). |
| `diagnose` | Connectivity + 14-index presence + WAL uncommitted count. |
| `verify [--metagraph M \| --graph G] [--source=memory\|db]` | 5-bucket integrity scanner. Phase 08 unblocks `--source=db --metagraph M` — full 5-bucket scan via `load_metagraph`. |
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

## Phase 08 additions

### `sync --metagraph M [--replace]`

Projects a Metagraph state file → FalkorDB. Wraps Phase 07's
programmatic `MetagraphRepository.persist` (PB-8 A).

The additive default writes the `:Metagraph` anchor + all contained
`:Graph` anchors + `:Node` rows + 4 edge-primitive labels. `--replace`
DETACH DELETEs the metagraph-scoped substrate state first; it
**refuses** with exit 2 if any `:ElementInstance` / `:CompositeInstance`
/ `:XRef` / uncommitted `:WALEntry` row references the metagraph
(RPB-4 C). The operator-guidance message names the offending bucket(s).

```
mindsos persistence sync --metagraph my-metagraph
mindsos persistence sync --metagraph my-metagraph --replace
```

### `load --metagraph M [--to-json | --json]`

Reconstructs a Metagraph from FalkorDB via
`mindsos_core.reconstruction.load_metagraph` (PB-9 A). The locked R4-1 A
read sequence is `recover()` → anchor → contained graphs → meta-edges
→ meta-hyperedges → intergraph-edges → intergraph-hyperedges →
`after_load(mg)` observer fire (which rehydrates sibling-package
instance state if `mindsos_instances.attach_registry(mg)` ran before
the load).

Default stdout is the 9-line flat summary (R4-5 A):

```
Metagraph: <name>
Metagraph id: <mid>
Graphs: <N>
MetaEdges: <N>
MetaHyperEdges: <N>
IntergraphEdges: <N>
IntergraphHyperEdges: <N>
ElementInstances: <N>
CompositeInstances: <N>
```

`--json` opts into machine-readable JSON to stdout; `--to-json` writes
to the sibling path `~/.mindsos/metagraph-<name>.fromdb.json` (RR-7 A
— canonical state file untouched). Pass `--force` to overwrite an
existing sibling file.

```
mindsos persistence load --metagraph my-metagraph
mindsos persistence load --metagraph my-metagraph --json
mindsos persistence load --metagraph my-metagraph --to-json --force
```

### `verify --source=db --metagraph M` (PB-7 A unblock)

Phase 07 P49 A refused this combo; Phase 08 unblocks it. The CLI
calls `load_metagraph(client, mid)` then runs the existing 5-bucket
scanner in memory. No new scanner code; exit codes per P64 A
(0 clean / 1 CLI usage / 2 system error / 3 drift findings).

```
mindsos persistence verify --source=db --metagraph my-metagraph
```

### `--graph G | --metagraph M` mutex (R4-6 A)

On `load` and `verify` (and `sync`), supplying both flags exits 1
with a CLI-usage error before any DB query. Symmetric across the
three commands.

### Known constraints carried into Phase 08

* **`RefreshUnsafeError` ships but is never raised** (PB-5 B). Per-role
  mutation-flag tracking is deferred to a later phase. Callers using
  `MetagraphLoader.refresh(mg, role)` AFTER in-memory mutations on
  that role-graph LOSE those mutations silently. The class is
  importable from `mindsos_core.exceptions` and re-exported from
  `mindsos_core.reconstruction`.
* **`recover()` is per-Metagraph only** (RPB-5 A). `load_graph` does
  NOT call `recover()`; only `load_metagraph` does. Standalone Graph
  has no metagraph recovery context. Documented asymmetry.
* **`recover()` is silent no-op without registered replayers**
  (RPB-3 C narrow-catch). Uncommitted `:WALEntry` rows remain visible
  to the `verify --source=db`'s `dangling_wal_entries` bucket. Once
  L0/L2 (Phase 18+) register replayers, the call becomes meaningful.
* **`load_metagraph(..., batch_size=N)`** routes through
  `iter_load_graph` per contained graph + assembles. The whole
  metagraph is still held in memory; multi-graph streaming pagination
  is Phase 11+.
* **`load_metagraph` schema reattach is name-only** (PB-11 A). The
  persisted `:Metagraph.schema_name` plain property reloads into
  `mg.schema_name`; the vocab content is NOT auto-attached (L2
  territory). Tester recipe after load:
  `mindsos metagraph attach-schema --metagraph M --schema S`.
* **IntergraphHyperEdge anchor round-trip (P61 A)** — Phase 07's
  persist wrote only `:MEMBER` rels; Phase 08 additively writes
  `:ANCHOR` rels so the `n_anchors ≥ 1` invariant survives the load.
  Old data persisted before the Phase 08 fix has no `:ANCHOR` rels —
  affected IntergraphHyperEdges surface in the loader's WARNING log
  + are SKIPPED. Recovery: re-`sync --metagraph M --replace` under
  Phase 08 (after dropping dependent state per RPB-4 C).

## Streaming load (programmatic)

Phase 08 ships `iter_load_graph(client, graph_id, *, batch_size=10_000)`
for memory-bounded reads of large Graphs (per ADR-0124). The streaming
surface is **programmatic-only** (PB-10 A) — no `--stream` CLI flag.
Intermediate yields are nodes-only; the final yield trails any deferred
edges + hyperedges over the cumulative node set (RPB-1 A).

```python
from mindsos_core.persistence import FalkorClient
from mindsos_core.reconstruction import iter_load_graph

client = FalkorClient(config)
last_partial = None
for partial in iter_load_graph(client, "graph-id-xyz", batch_size=10_000):
    last_partial = partial
g = last_partial  # final yield = assembled Graph
```

Cross-graph primitives (`IntergraphEdge`, `IntergraphHyperEdge`) load
**only** via `MetagraphLoader.load` per the locked R4-1 A sequence
(RPB-10 A); `iter_load_graph` skips them by design.

## `MetagraphLoader.refresh(mg, role)` (programmatic)

Reloads role-graph(s) of `role` in `mg` in place. Identity preservation
guaranteed (R4-7 A+C — `id(mg)` + `id(mg.identity)` survive; external
`weakref.proxy(mg.identity)` continues to resolve).

```python
from mindsos_core.reconstruction import MetagraphLoader

loader = MetagraphLoader(client)
loader.refresh(mg, role="lexicon")
```

Edge cases (R4-2 D):

* Empty role (no graphs in `mg` with `role=$role`): WARNING log + no-op
  return.
* Role mismatch (in-memory `g.role` differs from DB `:Graph.role` for
  the same id): raises `RoleMismatchError` with both roles in the
  message. Indicates substrate corruption (external write race / manual
  DB edit); not user-recoverable at runtime.
