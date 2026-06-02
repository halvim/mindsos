---
title: Indexes + persist-time check + per-layer verify_integrity
status: Accepted
date: 2026-04-27
accepted_date: 2026-05-13
layer: L1
---

# ADR-0123: Indexes + persist-time check + per-layer `verify_integrity`

**Status:** Accepted (Phase 07 — M3 A inline flip 2026-05-13)

**Date:** 2026-04-27 · **Accepted:** 2026-05-13

**Related:** ADR-0121 (substrate commitment), ADR-0034 (Core never validates refs — diagnostic helper path).

## Context

FalkorDB has no `UNIQUE` constraint, no foreign-key enforcement, no schema validation at the database level. Every Core invariant lives in Python. A direct Cypher write (operator running `CREATE`, buggy migration script, future driver bug) bypasses every safety check.

Two cases observed:

1. **Duplicate ids.** Concurrent admin imports could MERGE the same logical entity twice with different UUIDs. Detection lives only in Python's `IdentityRegistry`, which doesn't see what FalkorDB committed.
2. **Cross-graph leaks.** Already documented (Core handoff §8). Cypher edges that point outside their graph; loader logs a WARNING and continues.

## Decision

Three layers of detection (no DB-level enforcement; detection is the achievable bar):

### 1. FalkorDB indexes

Bootstrap creates 14 indexes total per Phase 07 P95 B (10 node-label `id` indexes + 3 relationship-type `id` indexes per ADR-0021 + 1 hot-path index on `:Node {graph_id}` for the persist-time check):

```cypher
-- 10 node-label `id` indexes.
CREATE INDEX FOR (n:Metagraph)             ON (n.id)
CREATE INDEX FOR (n:Graph)                 ON (n.id)
CREATE INDEX FOR (n:Node)                  ON (n.id)
CREATE INDEX FOR (n:HyperEdge)             ON (n.id)
CREATE INDEX FOR (n:MetaHyperEdge)         ON (n.id)
CREATE INDEX FOR (n:IntergraphHyperEdge)   ON (n.id)
CREATE INDEX FOR (n:ElementInstance)       ON (n.id)
CREATE INDEX FOR (n:CompositeInstance)     ON (n.id)
CREATE INDEX FOR (n:Tombstone)             ON (n.graph_id)
CREATE INDEX FOR (n:WALEntry)              ON (n.operation_id)

-- 3 relationship-type `id` indexes per ADR-0021 (Edge/MetaEdge/IntergraphEdge
-- are REL types, not node labels — use relationship-index syntax per P89 A).
CREATE INDEX FOR ()-[r:Edge]-()            ON (r.id)
CREATE INDEX FOR ()-[r:MetaEdge]-()        ON (r.id)
CREATE INDEX FOR ()-[r:IntergraphEdge]-()  ON (r.id)

-- 1 hot-path index — persist-time check uses this for per-graph node scan.
CREATE INDEX FOR (n:Node)                  ON (n.graph_id)
```

**Note** (Phase 07 P88 A + P89 A): the original v1 DDL block treated `:Edge` / `:MetaEdge` / `:IntergraphEdge` as node labels — that was wrong per ADR-0021 (those are relationship types). The rewrite above uses the correct `()-[r:RelType]-()` syntax for FalkorDB relationship indexes; Phase 07 Step 0 probe (P68 A) confirmed FalkorDB v4.18.3 supports both bare `CREATE INDEX FOR` forms.

**Hotfix B-07-T1 (2026-05-13):** the original P89 A DDL used `CREATE INDEX IF NOT EXISTS FOR ...`, but FalkorDB v4.18.3's Cypher parser does NOT recognise the `IF NOT EXISTS` clause (returns a hard syntax error, not a runtime "already exists" error). The hotfix drops the clause; idempotency comes from the defensive try/except in `mindsos_core/persistence/bootstrap.py:bootstrap()` that swallows the `Attribute 'id' is already indexed` error returned on re-create.

**Tombstone index key**: per-(graph, element) tombstone shape (Phase 07 P69 A) uses a compound `{graph_id, element_id}` MERGE; the index above on `graph_id` is the secondary that the persist-time check uses for per-graph scans.

Indexes don't enforce uniqueness, but they make duplicate detection a single-query scan: `MATCH (n:Node {id: $id}) RETURN count(n)` runs in O(log N) instead of O(N).

Bootstrap (the existing `mindsos_core.bootstrap` function) creates indexes idempotently. Index creation is the third step of `bootstrap`, after schema setup and tombstone anchor creation.

### 2. Persist-time double-check

After every batched MERGE in `MetagraphRepository.persist` and `GraphRepository.persist`, run:

```cypher
MATCH (n:Label) WHERE n.id IN $ids RETURN n.id, count(n) AS c
```

Any row with `c > 1` raises `IntegrityCheckError` immediately. The check uses the indexes (W2 piece 1) so cost is O(K log N) where K = batch size.

Configurable via `FalkorConfig(persist_time_check_policy="strict" | "warn" | "off")`. Default `strict`. Tests can set `off` for performance-sensitive bench cases.

### 3. Per-layer `verify_integrity` functions

Each layer ships a scanner that admins run via CLI and the audit gate (per ADR-0115 [Reserved]) calls before release-ship.

**L1 Core (this ADR):**

```python
class IntegrityReport(NamedTuple):
    duplicate_ids: list[tuple[str, list[str]]]   # (label, [ids])
    cross_graph_edges: list[tuple[str, str]]      # (edge_id, source_graph_id)
    orphan_hyperedges: list[str]                  # hyperedges with zero members
    orphan_metaedges: list[str]                   # metaedges referring to deleted graphs
    dangling_tombstones: list[str]                # tombstone anchors with no parent

def Metagraph.verify_invariants(self) -> IntegrityReport: ...
```

Runs server-side; admin-runnable via CLI; cheap enough to call before every release-ship (ADR-0115's audit gate).

**KL** ships `KnowledgeLayer.verify_refs() -> RefIntegrityReport` (separate ADR; aligns with ADR-0034's `verify_refs()` proposal). Walks XRefs and checks targets exist.

**L3** ships `CapacityLayer.verify_constraints() -> ConstraintReport` (separate, future). Walks CONSTRAINT edges.

Each layer's verify function uses Core's `verify_invariants` as a base scan, then layers in domain-specific checks.

### CLI integration

```
mindsos-server fsck                  # runs all layers' verify_integrity, reports findings
mindsos-server fsck --layer=core     # only Core's verify_invariants
mindsos-server fsck --layer=core --metagraph-id=...  # scoped to one Metagraph
mindsos-server fsck --json           # machine-readable output
```

The CLI is read-only by default; `--repair` flag is v2 (after the soft-delete model and undelete semantics are clearer).

## Rationale

Three layers because no single one is sufficient:

- **Indexes alone** detect nothing; they just make detection cheap.
- **Persist-time check alone** protects writes through Core's repositories but not direct Cypher.
- **`verify_integrity` alone** is run-when-you-think-of-it; misses fast-feedback on writes.

Together: indexes give cheap detection; persist-time check catches Core-write-path duplicates immediately; `verify_integrity` catches operator damage and integrates with the audit gate.

The DB-level enforcement gap (no UNIQUE) is unfixable on FalkorDB. Detection is the achievable bar. The `verify_integrity` family is the audit-gate hook that makes the gap manageable.

## Consequences

**Good:**

- Duplicate ids surfaced within one round-trip of writing them (persist-time check).
- Cross-graph leaks become a queryable property of the data, not a log-only warning.
- Audit gate (ADR-0115) has a structured input (`IntegrityReport`) instead of ad-hoc scans.
- `mindsos-server fsck` becomes a real diagnostic tool for ops.

**Tradeoffs:**

- Persist-time check adds one round-trip per batch. For an N-graph metagraph persist with K batches per graph, that's NK extra queries. Acceptable on indexed lookups; tunable via `FalkorConfig`.
- Each layer ships its own scanner; risk of drift between Core's `verify_invariants` and KL/L3 scanners. Mitigation: integration test runs all scanners against a known-bad fixture and asserts each catches its own bucket.
- Index creation is idempotent but adds boot time on first start of a fresh database. Bounded.

**Coordinated changes:**

- `mindsos_core/bootstrap.py` — index creation step.
- `mindsos_core/persistence/integrity.py` (new) — `IntegrityReport`, persist-time check.
- `mindsos_core/persistence/metagraph_repository.py`, `graph_repository.py` — invoke persist-time check at end of batch.
- `mindsos_core/models/metagraph.py` — `verify_invariants()` method.
- `mindsos_server/cli.py` — `fsck` subcommand.
- KL: `KnowledgeLayer.verify_refs()` — separate ADR, follows the same shape.
- ADR-0115 [Reserved] audit gate: calls `verify_invariants` and `verify_refs` pre-release-ship.

## Alternatives considered

1. **Wrapper Client that intercepts CREATE.** `EnforcingClient` wraps `FalkorClient` and refuses any statement not matching a whitelist. Rejected — limits power-user diagnostics; CLI tools have to bypass; "wrap-the-driver" smell.
2. **Indexes only, no persist-time check, no `verify_integrity`.** Rejected — detection becomes pull-only; no fast feedback at write time.
3. **`verify_integrity` only, no persist-time check.** Rejected — admins must remember to run scanner; no immediate signal on bugs.
4. **DB-level UNIQUE via FalkorDB-future-feature.** Rejected — feature not present; design can't depend on speculation.
5. **Defer entirely; rely on Python-side `IdentityRegistry`.** Rejected — registry only sees writes that go through Core; direct Cypher bypasses; the gap is real.

## Implementation references

- `mindsos_core/bootstrap.py` — index DDL block.
- `mindsos_core/persistence/integrity.py` (new).
- `mindsos_core/models/metagraph.py` — `verify_invariants()`.
- `mindsos_server/cli.py` — `fsck` subcommand.
- Tests: `tests/unit/core/test_integrity.py` + `tests/integration/test_fsck.py`.
- Documentation: `docs/dev/internals/core.md` (integrity section), `docs/api/server/cli.md` (fsck reference).

**Acceptance criteria (Phase 07 P27 C amendment):** *Accepted when L1 mechanism ships + `docs/dev/internals/core.md` documents the pattern; consumer integration (`mindsos-server fsck`, KL `verify_refs()`, L3 `verify_constraints()`) tracked separately.* Met by Phase 07: 14-index `DEFAULT_INDEXES` + `bootstrap()` ship in `mindsos_core/persistence/bootstrap.py`; `verify_invariants(mg)` returns a 5-bucket `IntegrityReport` in `mindsos_core/persistence/integrity.py`; sibling `verify_invariants_graph(graph)` returns a 3-bucket `PartialIntegrityReport` per Phase 07 P98 A for the `mindsos persistence verify --source=db --graph G` partial path; `docs/dev/internals/core.md` "Persistence layer" §Indexes documents the model.

## Revisions

### amendment-1 (Phase 26a ship — 2026-05-23) — Hot-path index `Metagraph.name` added

**Trigger:** Phase 26a wires server-driven FalkorDB persistence per
ADR-0118 §amendment-3. The `bootstrap_kl_from_falkordb` wrapper (per
Phase 26a R5-PB-4 (a)) calls `MetagraphLoader.find_by_name(name)` on
every CLI invocation that needs KL — hot-path lookup. Without an
index on `Metagraph.name`, the lookup scans all Metagraph anchors
(Global + pending + canonical + every user Local). At v1 N is small
but grows; the index is cheaper now than after N grows.

**Amended decision:**

`DEFAULT_INDEXES` in `mindsos_core/persistence/bootstrap.py` gains a
19th entry:

```python
("node", "Metagraph", "name"),
```

This is the second `Metagraph` node-label index (the first is
`("node", "Metagraph", "id")` from §Decision §1 original). Symmetric
with the §1 "hot-path index" precedent for `("node", "Node", "graph_id")`
which was added under the same rationale.

**Consequences:**

- Phase 09 baseline-literal-decay class (per memory
  `feedback_phase_baseline_literal_audit.md`): tests that count
  `len(DEFAULT_INDEXES)` or assert the per-(kind, label) distinct
  count bump from 18 → 19. Phase 09 B-09-T2 precedent for
  "compare to distinct-pair count, not len(DEFAULT_INDEXES)"
  applies — the new entry adds one more (kind, label) pair.
- `FalkorClient.__init__` lazy-bootstrap creates the index on
  first connection after deploy; FalkorDB v4.18.3 quirks per
  memory `feedback_falkordb_index_ddl_quirks.md` apply (no
  `IF NOT EXISTS`; substring match on label coverage).
- Existing Metagraphs (Global from prior Phase 25 deploys) get
  the index applied on next bootstrap; no data migration needed
  since the index is built lazily over existing rows.

**Phase 26a design log:** `halvim_mindsos/confirmation_docs/PHASE_26a_
DESIGN_LOG.md` §1 R6-PB-1 (a) pick.
