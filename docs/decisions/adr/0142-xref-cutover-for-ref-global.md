---
title: XRef cutover for ref:global_<role> user data
status: Accepted
date: 2026-04-27
layer: L2
---

# ADR-0142: XRef cutover for `ref:global_<role>` user data

**Status:** Accepted (shipped; frontmatter reconciled during the 2026-07 doc-vs-code audit)

**Date:** 2026-04-27

**Related:** ADR-0128 (hybrid XRef), ADR-0138 (KL drops write API), ADR-0143 (`KLWriteHandle`).

## Context

L1's M2 hybrid model (ADR-0128) makes `XRef` rows the canonical representation for cross-metagraph references (Local → Global). Today, KL's `add_local_node(ref_to_global=...)` and `add_local_edge(target_is_global=True)` write `ref:global_<role>=<iri>` properties on the new node/edge. Existing user Locals contain those property strings.

Under ADR-0138, KL writes are deleted; L3 capacities take over. The cutover question: do new writes (via L3 capacities) write XRef, write properties, or both? And what happens to existing user data?

## Decision

**Cutover to XRef now.** Three commitments:

1. **New writes write XRef rows only.** L3 write capacities use `KLWriteHandle.graph().add_xref(...)` for cross-metagraph refs. They do not write `ref:global_<role>` properties.
2. **Read paths consult XRef first; legacy `ref:global_<role>` properties are a read-time fallback.** `MetagraphView.follow_ref()` and `MetagraphView.step()` walk XRefs forward and look up `ref:global_<role>` properties as fallback. Fallback is read-only and emits a `LegacyRefWarning` for each fallback hit, so migration progress is observable.
3. **One-time migration job converts existing properties to XRef rows.** Runs on first server start after upgrade. Idempotent. Iterates each user's Local metagraph; for each `ref:global_<role>=<iri>` property, writes an `XRef(source_id, target_metagraph_id, target_role, target_id, ref_type)` and removes the property. Logs migrated count + verifies `iter_xrefs()` returns the new rows.

Once the migration job completes for all known Locals (audit log shows zero `LegacyRefWarning` for >7 days under steady use), the read-time fallback is removed in a follow-up release.

## Rationale

Three options were on the table:

| Option | New writes | Old data | Reverse walk |
|--------|-----------|----------|--------------|
| **A. Cutover now** | XRef | migration job | indexed |
| B. Dual-write | XRef + property | both formats | property-string scan |
| C. Read-fallback only | property | property | property-string scan |

A is the only option that ends with a single format. B and C leave property strings in user data indefinitely, which means:

- The pivot's `mindsos_server/migration.py` rewrite-walk path stays O(N) instead of indexed (defeats the M2 motivation per ADR-0128).
- Reverse walks ("which Locals point at this Global node?") never get cheap.
- Two-format detection forks every read site forever.

Migration risk is small: corpus is single-user developer scale today; the pivot release is the right moment to land the migration before user data accumulates.

## Consequences

**Good:**

- Single canonical format for cross-metagraph refs.
- Reverse walks are indexed (per ADR-0128 storage shape).
- Pivot's rewrite-walk uses indexed `iter_xrefs()` instead of property-string scan.
- L3 write capacity authors only know one ref pattern.

**Tradeoffs:**

- Migration job is new code; idempotency must be tested under partial-failure scenarios.
- Read-time fallback is transitional code that needs deletion follow-up; track in `docs/decisions/proposed.md` until removed.
- Existing tests using `ref:global_*` property assertions migrate to XRef-row assertions.

## Alternatives considered

1. **Dual-write.** Two formats forever; rejected.
2. **Read-fallback only (no migration job).** XRef advantages never realised on legacy data; rejected.
3. **Defer migration; read-fallback indefinitely.** Same as 2 with different framing; rejected.
4. **Migrate via `mindsos_server.bootstrap()` instead of first-start hook.** Considered; bootstrap runs once at install, but later upgrades need the migration. First-start hook fires per server boot until the migration completes for that DB; cleaner.

## Implementation references

- Migration job: `mindsos_server/migration.py::migrate_legacy_refs_to_xref()`.
- Read fallback: `MetagraphView.follow_ref()` updated to consult XRef then property.
- `LegacyRefWarning`: emitted per fallback hit; logs aggregate on shutdown.
- L3 write capacities (ADR-0145) write XRefs from day one; no transitional dual-write logic in L3.
- ADR moves to Accepted when (a) migration job lands and runs clean on the dev DB, (b) `LegacyRefWarning` rate is zero in CI, (c) `docs/dev/internals/knowledge.md` documents the read-fallback removal trigger.

## Phase 09 disposition (2026-05-15)

The three commitments above are partitioned across phases. Phase 09 ships **commitment 3 only** (the L1 migration callable). The remaining two commitments stay in their respective owner phases. **Status stays Proposed** until all three commitments land.

| Commitment | Owner phase | Status |
|------------|-------------|--------|
| 1. New writes write XRef rows only (L3 capacities use `KLWriteHandle.graph().add_xref(...)`) | Phase 33+ ([ADR-0145](0145-l3-per-target-write-capacity-categories.md)) | deferred |
| 2. Read paths consult XRef first; legacy `ref:global_<role>` properties as read-time fallback (`MetagraphView.follow_ref` + `LegacyRefWarning`) | Phase 14 (L2 KnowledgeLayer + MetagraphView) | deferred |
| 3. One-time migration job (`migrate_in_memory(mg, target_metagraph_id, default_ref_type)`) converting existing properties to XRef rows | **Phase 09 (this row)** | shipped |

Phase 09 ships the migration callable as **programmatic-only** — the production trigger is the Server first-start hook, which lands in Phase 18+ alongside the per-user release migration path. The Phase 09 callable signature is v3-verbatim (`migrate_in_memory(mg, *, target_metagraph_id, default_ref_type="SPECIALISES") -> int`) so the Server consumer can call it directly without adapter code. Idempotent via `mg.properties["xref:migrated_at"]` (per [ADR-0130](0130-property-bag-on-metagraph-graph.md) namespacing convention amended this phase).
