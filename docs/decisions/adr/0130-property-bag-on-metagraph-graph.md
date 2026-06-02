---
title: Property bag on Metagraph and Graph
status: Accepted
date: 2026-04-27
layer: L1
supersedes: [0029, 0033]
---

# ADR-0130: Property bag on `Metagraph` and `Graph`

**Status:** Accepted (Phase 09 Metagraph-side 2026-05-15; Phase 10 Graph-side 2026-05-16 per §Revisions amendment-1)

**Date:** 2026-04-27

**Supersedes:** ADR-0029 (`:MetagraphSettings` JSON singletons — interim mechanism, becomes Superseded), ADR-0033 (property bag deferred — becomes Superseded by acceptance of this ADR).

**Related:** ADR-0027 (`MetagraphSnapshot.restore_into` mutates in place — must deep-copy the new `properties` dict).

## Context

Three layers above Core attach metadata to metagraphs and graphs without a typed slot:

- KL stores its active-version pointer map as `mg._kl_active_graph_ids` (a Python attr).
- Importers stamp `graph.properties = {...}` as a Python attr carrying `source`, `version`, `imported_at`.
- KL bootstrap stores `mg.user_id = user_id` as a Python attr.

ADR-0016 introduced `(:MetagraphSettings {key, value})` JSON singletons as an interim mechanism for KL's `_kl_active_graph_ids`. The pivot (ADR-0118 + PIVOT §7.5) adds at least two more piggyback keys (release pointer, pending-Global flag), and L4 design will add more (`current_plan_run_id`, `last_dream_at`).

Each new piggyback key today is an ad-hoc decision. The loader has to know about each one. There's no validation. There's no schema enforcement.

## Decision

Add a typed property bag to both `Metagraph` and `Graph`:

```python
@dataclass
class Metagraph:
    metagraph_id: str
    name: str
    properties: dict[str, Any] = field(default_factory=dict)
    # ... existing fields

@dataclass
class Graph:
    graph_id: str
    role: str
    properties: dict[str, Any] = field(default_factory=dict)
    # ... existing fields
```

**Rules:**

- Same reserved-key rules as `Node.properties`. Reserved keys (`id`, `metagraph_id`, `graph_id`, `role`, `name`, `type`, ...) raise `PropertyShapeError` on write.
- Property values follow the `PropertyType` taxonomy (scalar, list, dict). JSON-encodable.
- Schema validation runs when the Metagraph or Graph has a Schema attached and `strict=True`.
- Persisted as anchor-row properties on `:Metagraph` and `:Graph` Cypher rows. One round-trip per metagraph/graph during persist + load.

**Namespacing convention** (not enforced; follow):

- `kl:<key>` for KL-owned keys (e.g. `kl:active_graph_ids`).
- `server:<key>` for server-owned (e.g. `server:user_id`, `server:last_synced_release_id`).
- `l3:<key>`, `l4:<key>`, `l5:<key>` for upper-layer keys.
- `xref:<key>` for L1 XRef-machinery state (e.g. `xref:migrated_at` set by `mindsos_core.persistence.xref_migration.migrate_in_memory`). Added Phase 09 (2026-05-15) when Phase 09 M9 / ADR-0128 §Revisions amendment 4 surfaced the need; the migration code sets the flag but is L1-internal, so neither `kl:` nor `server:` was correct.

The colon delimits namespace from key; reserved-prefix list adds these as a guard against accidental collision with Core metadata.

**Migration:**

- ADR-0029's `:MetagraphSettings` mechanism is **Superseded**. Existing `active_graph_ids` setting reads on first load and migrates into `mg.properties["kl:active_graph_ids"]`; the `:MetagraphSettings` row is removed. Migration is one-way (new model only).
- KL's `mg._kl_active_graph_ids` and `mg.user_id` Python attrs become deprecated aliases that read from `mg.properties` for one release, then are removed.
- Importer's `graph.properties = {...}` Python attr becomes a real assignment to the typed field.

## Rationale

Three workarounds today; pivot adds two; L4 design adds more. The cost of each new ad-hoc piggyback is a small fixed implementation tax. The cumulative cost is real and growing.

The property-bag pattern matches the existing `Node.properties` precedent. Reserved-key rules carry over. Schema enforcement (when `strict=True`) extends naturally. Persistence is one extra column on each anchor row — bounded.

The alternative (`:MetagraphSettings` JSON singletons, ADR-0016) was an interim. It works but doesn't scale: each new piggyback widens the gap, the loader has to know each key, and JSON-in-string fields are opaque to FalkorDB's filtering.

A "metadata graph" alternative (a `role="_meta"` singleton graph per metagraph) was considered. It uses existing Core primitives and is queryable in Cypher. Rejected because it adds a new graph kind whose semantics are "graph that isn't really a graph" — confuses traversal, complicates the loader's role-filter logic, and doesn't fit the existing `Node.properties` precedent that this ADR follows.

## Consequences

**Good:**

- Three existing workarounds collapse to clean field assignments. KL's `_kl_active_graph_ids` is a typed property; `mg.user_id` is a typed property; importer metadata is a typed property.
- Pivot's piggyback keys have a home. ADR-0114's `last_synced_release_id` per-user is a server-namespaced property on the user's Local Metagraph.
- L4 design can stamp `current_plan_run_id` cleanly without a third workaround round.
- One persistence pattern, one validation pass. No more ad-hoc loader logic per key.

**Tradeoffs:**

- One additional column on `:Metagraph` and `:Graph` Cypher rows. JSON-encoded; FalkorDB stores the string.
- Reserved-key list grows by a few prefix-style guards (`kl:`, `server:`, `l3:`, `l4:`, `l5:`).
- Migration of `:MetagraphSettings` rows happens on first load; one-time cost; idempotent.
- `MetagraphSnapshot.of(mg)` (ADR-0027) must deep-copy `mg.properties` and `g.properties` for every contained graph. ~5 LOC change in snapshot module.

**Coordinated changes:**

- ADR-0029 status flips to **Superseded** when this ADR's code lands. ADR-0033 likewise flips to **Superseded** (it was Proposed; this is its acceptance).
- KL's bootstrap updates: `create_local(user_id)` writes `mg.properties["server:user_id"] = user_id` instead of `mg.user_id = user_id`.
- KL's `versions.py` updates: `_kl_active_graph_ids` becomes a property at `mg.properties["kl:active_graph_ids"]`.
- Importers update: `result.graph.properties = {...}` continues to work but now writes to the real typed field.
- Pivot ADR-0114 references `mg.properties["server:last_synced_release_id"]` for per-user release tracking.

## Alternatives considered

1. **Status quo + `:MetagraphSettings` JSON singletons (ADR-0016).** Rejected — every new piggyback is an ad-hoc decision; loader has to know each key; JSON-in-string is opaque to FalkorDB's filtering; the cumulative loader complexity grows linearly with piggyback count.
2. **Sanctioned `_meta` graph per metagraph.** Rejected — uses existing primitives but introduces a "graph that isn't really a graph" mental model that confuses traversal and doesn't match the `Node.properties` precedent.
3. **External meta-DB** (extends pivot's SQLite version DB to hold metagraph/graph metadata). Rejected — adds a fourth store boundary; cross-store consistency surface widens; pulls metadata away from the graph it belongs to.
4. **Status quo + louder warnings.** Rejected — papers over a real abstraction gap; doesn't help future layers that haven't picked their workaround yet.

## Implementation references

- New fields on `Metagraph` and `Graph` dataclasses in `mindsos_core/models/`.
- Reserved-key list in `mindsos_core/schema/validation.py`.
- Persistence in `mindsos_core/persistence/metagraph_repository.py` and `graph_repository.py`.
- Loader updates in `mindsos_core/reconstruction/`.
- Migration helper for ADR-0016 → ADR-0130: read `:MetagraphSettings` rows on first load, write into `mg.properties`, delete the `:MetagraphSettings` row.
- KL coordinated updates: `mindsos_knowledge/bootstrap.py`, `mindsos_knowledge/versions.py`, `mindsos_knowledge/importers/base.py`.

ADR moves from Proposed to Accepted when the corresponding code lands and at least one user-facing document (`docs/concepts/graphs-and-metagraphs.md` or `docs/dev/internals/core.md`) reflects the decision.

**Acceptance (Phase 09 — 2026-05-15):** `Metagraph.properties` shipped Phase 06; `Graph.properties` deferred per `_props_json` Phase 07 P9 C still pending — Phase 09 narrows acceptance to the Metagraph side which has full coverage (consumed by Phase 09 `xref:migrated_at` migration flag + Phase 06 element-instance attach metadata). Graph-side property bag re-evaluated when the next consumer surfaces.

## Revisions

1. **2026-05-16 (Phase 10 T-rev.A + P69 caveat).** Graph-side `Graph.properties` accepted. Consumer = `MetagraphSnapshot._GraphSnap.properties` which deep-copies the bag on `of()` and restores on `restore_into()` (3 sites in `metagraph_snapshot.py`). Per the P69 design-chat caveat the acceptance is **on snapshot-preservation basis**; if a future typed-key consumer (e.g., KL-namespaced graph metadata, importer source tagging) surfaces with semantics that conflict with the bag's current value-passthrough shape, this ADR is re-opened. Phase 10 ships `Graph.__init__(properties=...)` parameter + reserved-key validation via `validate_user_properties(scope="graph")`.
