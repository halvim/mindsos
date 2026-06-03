# L2 storage tiers

L2 large-payload field handling per ADR-0151. Three tiers absorb the size variance v1 will see — small structured outputs through neural-model artifacts — without forcing every field into the same storage path.

## Three tiers (ADR-0151 §Decision)

| Tier | Size range | Mechanism | `storage_mode` value | Backend-specific? |
|---|---|---|---|---|
| 1 — Inline | ≤ ~4 KB | JSON-encoded property | `"inline"` | No |
| 2 — Falkor large-property | ~4 KB to ~1 MB | Falkor BLOB-style property | `"falkor_blob"` | Yes (FalkorDB) |
| 3 — External blob_ref | > ~1 MB | v2 only; routed to FOL chat | `"blob_ref"` (reserved) | No (blob store + manifest IRI) |

The thresholds are guidance, not strict cutoffs. L4 substrate may apply per-deployment tuning within a hysteresis band. This concept doc locks the three-tier shape and the `storage_mode` discipline; concrete thresholds are L4-implementation.

## Per-NodeType `storage_mode` field

Per ADR-0151 + ADR-0152 §6 + Phase 43 NPB8-1: `storage_mode` is a per-NodeType property declaration (not a per-role-graph class field). Schemas declare which NodeTypes carry large-payload fields via a module-level `STORAGE_MODE_FIELDS` dict mapping `NodeType_name -> frozenset[field_name]`.

**Phase 43 v1 consumer (sole large-payload NodeType in scope):**

```python
# mindsos_knowledge/schemas/learned_parameters.py
STORAGE_MODE_FIELDS: dict[str, frozenset[str]] = {
    "LearnedParameter": frozenset({"value"}),
}
```

`LearnedParameter.value` is the only Phase 43 large-payload field. The `storage_mode` property carries the tier value at write time per ADR-0151. NPB11-4 regression guard: no other Phase 43 schema MUST export `STORAGE_MODE_FIELDS`.

Other large-payload candidates routed forward:

- `episodic_memories.Episode.task_input_ref` — XRef into a frozen `TaskInput` composite whose payload field carries `storage_mode`. The Episode itself does NOT declare `storage_mode` (the XRef target does).
- `DataStateInstance` frozen payloads inside Episode's `mm_root_ref` — same discipline cascades (future phases).

## v1 ships Tiers 1 + 2

`BLOB_REF` is reserved in the `StorageMode` enum but rejected at write time in v1. FOL installation chat (per Chat A R5 D30) ships the blob-store design + v2 plumbing. Until then: large payloads exceeding ~1 MB raise `BlobRefNotSupportedError` (deferred class; will land alongside FOL).

## Read-side dispatch

Read APIs MUST consult `storage_mode` before dereferencing the payload field. The `StorageMode` enum has `INLINE` / `FALKOR_BLOB` / `BLOB_REF` (3 values).

## Cross-references

- Role-graphs: see [`role-graphs.md`](role-graphs.md).
- Mutation discipline: see [`mutation-discipline.md`](mutation-discipline.md).
- ADR-0151 L2 storage tiers.
- ADR-0152 §6 LearnedParameter schema.
- Chat A R5 D30 — FOL blob-store ownership.
