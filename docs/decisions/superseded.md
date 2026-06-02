---
title: Superseded decisions
tag: shipped
teaser: ADRs that have been replaced by later decisions.
---

# Superseded decisions

When an ADR's context changes or a later decision replaces it, the old ADR is marked **Superseded** with a link to the new one. The old text stays intact for historical reference.

When an ADR becomes superseded:

1. Keep the original ADR file with its original number and text.
2. Change its `status:` front-matter line to `status: Superseded`.
3. Add a line like `superseded_by: ADR-NNNN` to link the replacement.
4. The reader can see the old reasoning, the old decision date, and the new decision that replaced it.

## Supersessions in flight

These supersessions have been **proposed** by later ADRs and become effective when the superseding ADR's code lands and a user-facing doc reflects the decision (per `about.md`).

| Original | Status | Superseded by | Notes |
|----------|--------|---------------|-------|
| [0007](adr/0007-metagraph-snapshot-rollback.md) | Accepted *(supersession proposed)* | [0118](adr/0118-per-user-transactional-promotion.md) | Cross-user atomic promotion model replaced by per-user transactional + release-boundary atomicity. The `MetagraphSnapshot` machinery itself is retained; only its use for cross-user rollback is superseded. ADR-0129 documents the narrowed scope. |
| [0029](adr/0029-piggyback-metadata-via-metagraph-settings.md) | Accepted *(supersession proposed)* | [0130](adr/0130-property-bag-on-metagraph-graph.md) | `:MetagraphSettings` JSON-singleton interim mechanism replaced by typed `properties: Dict` on `Metagraph` / `Graph`. Existing settings migrate on first load. |
| [0033](adr/0033-property-bag-on-metagraph-deferred.md) | Proposed *(supersession proposed)* | [0130](adr/0130-property-bag-on-metagraph-graph.md) | Original deferred ADR; ADR-0130 ships what 0033 deferred. |
| [0037](adr/0037-instancing-vocabulary-in-core.md) | Accepted *(supersession proposed)* | [0132](adr/0132-instancing-moved-to-mindsos-instances.md) | Instancing vocabulary moves out of Core to a sibling `mindsos_instances` package. |

## Amendments in flight

These ADRs are not superseded but are *amended* — the original decision stands, with the later ADR narrowing or extending its scope.

| Original | Status | Amended by | Notes |
|----------|--------|-----------|-------|
| [0027](adr/0027-metagraph-snapshot-restore-in-place.md) | Accepted | [0129](adr/0129-metagraph-snapshot-narrowed-to-release-ship.md) | Mutate-in-place contract retained; caller-side use narrowed to release-ship. |
| [0028](adr/0028-metagraph-snapshot-not-serialisable.md) | Accepted | [0129](adr/0129-metagraph-snapshot-narrowed-to-release-ship.md) | Not-serialisable contract retained; usage scope narrowed. |
| [0030](adr/0030-client-protocol-minimal-sync.md) | Accepted | [0126](adr/0126-async-client-via-thread-pool-wrapper.md) | Sync Client minimal surface retained; `AsyncClient` parallel Protocol added. |
| [0034](adr/0034-core-never-validates-refs.md) | Accepted | [0128](adr/0128-hybrid-xref-cross-metagraph-refs.md) | `ref:<role>` strings stay unvalidated; XRefs gain write-time validation when target is resolvable. |
| [0035](adr/0035-uuid-generation-non-deterministic.md) | Accepted | [0131](adr/0131-pluggable-id-strategy.md) | UUID4 stays default; `IdStrategy` Protocol enables opt-in alternatives. |
| [0036](adr/0036-no-multi-writer-concurrency-control.md) | Accepted | [0127](adr/0127-optimistic-concurrency-on-global-writes.md) | Per-user Locals stay single-writer; Global writes use OCC via `_version`. |
| [0001](adr/0001-dedicated-server-layer.md) | Accepted | [0136](adr/0136-server-as-orthogonal-layer.md) | Server-as-separate-package decision unchanged; placement clarified from "Layer 0" to "orthogonal." |
| [0006](adr/0006-promotion-locking.md) | Accepted | [0118](adr/0118-per-user-transactional-promotion.md) | Per-user mutex retained; `GLOBAL_PROMOTE_LOCK` renamed `RELEASE_SHIP_LOCK` and used only at release-ship. |
| [0016](adr/0016-cross-graph-references-via-property-prefix.md) | Accepted | [0128](adr/0128-hybrid-xref-cross-metagraph-refs.md) | `ref:<role>` retained for intra-metagraph; XRef takes over cross-metagraph. |
| [0083](adr/0083-pipeline-promotion-transitive.md) | Proposed | [0118](adr/0118-per-user-transactional-promotion.md) | Capacity-layer ADR-0083 (transitive promotion of pipeline dependencies, formerly capacity-ADR-024) is superseded by the unified release manifest. |

---

**Related:** [About ADRs](about.md) | [Full ADR log](adr/README.md)
