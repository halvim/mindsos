---
title: L1 Core decisions
tag: shipped
teaser: All architectural decisions affecting the Core Layer primitives.
next: decisions/summary/knowledge.md
---

# L1 Core decisions

Core owns the data primitives and persistence plumbing for every layer above it. These decisions lock in the data model, schema, identity contract, and write semantics that all higher layers inherit.

| ADR # | Title | Status | Summary |
|-------|-------|--------|---------|
| [0001](../adr/0001-dedicated-server-layer.md) | Introduce a dedicated Server Layer above the domain stack | Accepted | Auth, sessions, audit, promotion orchestration live in a separate top-level package |
| [0014](../adr/0014-layer-boundary-core-only.md) | Layer boundary: Core owns primitives only | Accepted | Core performs no reasoning, derivation, or integrity checking — all delegated to higher layers |
| [0015](../adr/0015-instancing-model.md) | Instancing model: reference + overrides at any granularity | Accepted | `ElementInstance` references templates with small overrides; materialisation is lazy |
| [0016](../adr/0016-cross-graph-references-via-property-prefix.md) | Cross-graph references via `ref:<role>` property prefix | Accepted | Refs are properties keyed with `ref:` prefix; Core iterates them but does not validate targets |
| [0017](../adr/0017-schema-strictness-opt-in.md) | Schema strictness is opt-in per `Schema(strict=...)` | Accepted | Stable datasets get validation; exploratory graphs stay fluid |
| [0018](../adr/0018-single-mindsos-core-package.md) | Single `mindsos_core` package with submodules | Accepted | One import path per concept; free to reshuffle internals without breaking callers |
| [0019](../adr/0019-materialisation-is-lazy.md) | Materialisation is lazy: `instance.materialise()` on demand | Accepted | Core never auto-expands instances; callers explicitly materialise then attach |
| [0020](../adr/0020-metagraph-wide-shared-identity-registry.md) | Metagraph-wide shared `IdentityRegistry` | Accepted | Every contained Graph shares the metagraph's registry; cross-graph refs are trivially safe |
| [0021](../adr/0021-cypher-rel-type-validation.md) | Cypher rel-type identifiers validated by regex | Accepted | `^[A-Z][A-Z0-9_]{0,63}$` prevents injection while allowing layer autonomy |
| [0022](../adr/0022-batched-writes-via-unwind.md) | Writes batched via `UNWIND`, one batch per relationship type | Accepted | Linear scaling; each rel-type gets its own batch since names cannot be parameterised |
| [0023](../adr/0023-two-step-writes-merge-then-set.md) | Two-step writes: `MERGE` on id first, `SET` props second | Accepted | `id` is always bound separately; property bags cannot overwrite it |
| [0024](../adr/0024-deletes-leave-tombstone-anchored-removed.md) | Deletes leave tombstone-anchored `:REMOVED_*` self-loops | Accepted | Audit is preserved; reconstruction can show deletion history |
| [0025](../adr/0025-instance-overrides-via-ov-prefix.md) | Instance overrides persisted under `ov__<key>` prefix | Accepted | Namespaced to avoid collision with Core metadata |
| [0026](../adr/0026-composite-overrides-bundle-only.md) | Composite overrides are bundle-level only; do not propagate | Accepted | Materialisation is deterministic: same instance always looks the same |
| [0027](../adr/0027-metagraph-snapshot-restore-in-place.md) | `MetagraphSnapshot.restore_into` mutates in place | Accepted | Rollback transparent to layer holders; object identity preserved |
| [0028](../adr/0028-metagraph-snapshot-not-serialisable.md) | `MetagraphSnapshot` is in-process only, not serialisable | Accepted | Core schema can evolve without snapshot-format migration |
| [0029](../adr/0029-piggyback-metadata-via-metagraph-settings.md) | Piggyback metadata persists as `:MetagraphSettings` JSON singletons | Accepted | Arbitrary-shape metadata via JSON without a full property-bag |
| [0030](../adr/0030-client-protocol-minimal-sync.md) | `Client` Protocol is minimal and synchronous | Accepted | Three methods; no async, transactions, or cancellation — wrapped at higher layers |
| [0031](../adr/0031-reconstruction-via-private-factories.md) | Reconstruction uses private `_restore_*` factories | Accepted | Load path stays separate from write path; public API cannot accidentally reuse ids |
| [0032](../adr/0032-reserved-property-keys-metagraph-wide.md) | Reserved property keys form a metagraph-wide union | Accepted | Clear, global contract; no memorising which type forbids which key |

## Deferred / Proposed decisions

Core carries several design tradeoffs that are not yet shipped but have known paths forward:

| ADR # | Title | Status | Summary |
|-------|-------|--------|---------|
| [0033](../adr/0033-property-bag-on-metagraph-deferred.md) | Property bag on `Metagraph` / `Graph` | Superseded by [0130](../adr/0130-property-bag-on-metagraph-graph.md) | Original deferred ADR; superseded by L1 redesign acceptance |
| [0034](../adr/0034-core-never-validates-refs.md) | Core never walks `ref:*` targets — integrity is a higher-layer concern | Amended by [0128](../adr/0128-hybrid-xref-cross-metagraph-refs.md) | Property-string refs stay unvalidated; XRefs gain write-time validation |
| [0035](../adr/0035-uuid-generation-non-deterministic.md) | UUID generation is non-deterministic | Amended by [0131](../adr/0131-pluggable-id-strategy.md) | UUID4 stays default; alternative strategies become opt-in |
| [0036](../adr/0036-no-multi-writer-concurrency-control.md) | No multi-writer concurrency control | Amended by [0127](../adr/0127-optimistic-concurrency-on-global-writes.md) | Per-user Locals stay single-writer; Global writes use OCC |
| [0037](../adr/0037-instancing-vocabulary-in-core.md) | Instancing vocabulary lives in Core | Superseded by [0132](../adr/0132-instancing-moved-to-mindsos-instances.md) | Vocabulary moves to `mindsos_instances` sibling package |

## L1 redesign decisions (2026-04-27)

The L1 redesign pass (see `docs/HANDOFF_L1_REDESIGN_2026-04-27.md`) drafted seventeen Proposed ADRs covering substrate commitment, FalkorDB-weakness mitigations, the hybrid XRef model, soft-delete representation, and the package move for instancing. All are **Proposed** until code lands.

| ADR # | Title | Status | Summary |
|-------|-------|--------|---------|
| [0121](../adr/0121-substrate-falkordb-for-graphs-sqlite-for-non-graph.md) | Substrate — FalkorDB for graphs, SQLite for non-graph state | Proposed | Commits to FalkorDB; six paired weakness mitigations land as ADRs 0122–0127 |
| [0122](../adr/0122-wal-graph-for-multi-statement-write-safety.md) | WAL graph for multi-statement write safety | Proposed | Sibling `:WAL` graph per Metagraph; replays uncommitted entries on crash |
| [0123](../adr/0123-indexes-and-verify-integrity.md) | Indexes + persist-time check + per-layer `verify_integrity` | Proposed | FalkorDB indexes for cheap dup detection; `mindsos-server fsck` CLI |
| [0124](../adr/0124-streaming-loader-iter-load-and-refresh.md) | Streaming loader: `iter_load` and `MetagraphLoader.refresh` | Proposed | Pagination via SKIP/LIMIT; per-role refresh for L4 delta reloads |
| [0126](../adr/0126-async-client-via-thread-pool-wrapper.md) | `AsyncClient` Protocol via `asyncio.to_thread` | Proposed | Thread-pool wrapper around sync Client; ~50 LOC |
| [0127](../adr/0127-optimistic-concurrency-on-global-writes.md) | Optimistic concurrency on Global writes (`_version` property) | Proposed | Conditional MERGE; retry-on-conflict; `_version` reserved property |
| [0128](../adr/0128-hybrid-xref-cross-metagraph-refs.md) | Hybrid cross-graph refs — XRef primitive + ref-string convention | Proposed | First-class XRef for cross-metagraph; ref-strings for intra-metagraph |
| [0129](../adr/0129-metagraph-snapshot-narrowed-to-release-ship.md) | MetagraphSnapshot scope narrowed to release-ship | Accepted | KL drops snapshot for ordinary writes; uses WAL graph |
| [0130](../adr/0130-property-bag-on-metagraph-graph.md) | Property bag on `Metagraph` and `Graph` | Proposed | Typed `properties` field; supersedes ADRs 0029 and 0033 |
| [0131](../adr/0131-pluggable-id-strategy.md) | Pluggable `IdStrategy` on `Metagraph` | Proposed | Default UUID4; opt-in `UUID5FromContent` and `IRIPassthrough` |
| [0132](../adr/0132-instancing-moved-to-mindsos-instances.md) | Instancing vocabulary moved to `mindsos_instances` package | Proposed | Sibling package; supersedes ADR-0037 |
| [0133](../adr/0133-soft-delete-via-deprecated-disputed-properties.md) | Soft-delete via `deprecated_at` / `disputed_at` properties | Proposed | Property-on-edge representation; default `include_deprecated=False` |
| [0134](../adr/0134-schema-migration-scanner.md) | Schema migration scanner + loader warning on unknown edge types | Proposed | `Schema.migrate_from`; configurable `unknown_edge_type_policy` |
| [0135](../adr/0135-removal-impact-on-remove-graph.md) | `RemovalImpact` report on `remove_graph` | Proposed | Detects incoming XRefs and ref-strings; `force` flag required for removal |

---

**Next:** [L2 Knowledge decisions](knowledge.md) — long-term memory, versioning, and Global/Local patterns.
