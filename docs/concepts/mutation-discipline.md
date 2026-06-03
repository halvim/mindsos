# Mutation discipline

Per-role-graph mutation discipline + per-field content/metadata partitioning is the L2 contract that governs how role-graph contents may change after the initial write. ADR-0153 ratifies the framework; ADR-0153 §amendment-1 (Phase 43 ship) locks the `L2Schema(Schema)` subclass placement.

## Six disciplines (ADR-0153 §1)

| Discipline | Semantics | v1 role-graphs |
|---|---|---|
| `immutable_successor` | Content fields are write-once; updates mint a successor IRI. Metadata fields mutate in place. | `promoted-pipelines`, `task-patterns` |
| `append_only_with_lazy_inline` | External writes are append-only on content fields. Lazy inline-on-retire (when a referenced version retires) is the only permitted internal mutation. Metadata fields mutate freely. | `episodic_memories` |
| `mutable_with_retention` | Rows are mutable; admin-tunable retention TTL prunes old rows. | `parameter-staging`, `capacity-state`, `capacity-gaps`, `learned-parameters` (Local) |
| `audit_only_after_settled` | Rows mutate until terminal status (`status ∈ {applied, rejected}`); once settled, frozen for audit chain integrity. | `pending-promotions` |
| `admin_authored` | Mutation only via admin importer or admin tooling; no L4/L3 write path. | `ontology`, `lexicon`, `concepts`, `alignment:*`, `learned-parameters` (Global) |
| `append_only` | All fields append-only; no retention; no successor; no lazy inline. | `problem-trace` |

Phase 43 R0a-4/S3 added `append_only` for `problem-trace`; the original L2-chat closure listed 5 disciplines.

## L2Schema subclass placement (ADR-0153 §amendment-1)

`L2Schema(Schema)` lives in `mindsos_knowledge/schemas/_base.py`. L1 `mindsos_core.Schema` stays primitive; no `mutation_discipline` field; no `Discipline` enum import. The `Discipline` enum is defined alongside `L2Schema` (L2-private vocabulary). Required-at-construction: every L2 role-graph schema MUST construct via `L2Schema(mutation_discipline=Discipline.X, strict=...)`.

Per ADR-0010 import-direction symmetry: L1 stays primitive; L2 owns its own vocabulary.

## Per-field content/metadata partition (ADR-0153 §3)

Schemas with discipline `immutable_successor`, `append_only_with_lazy_inline`, or `append_only` MUST declare per-NodeType field partition via two module-level frozensets:

```python
PIPELINE_CONTENT_FIELDS: frozenset[str] = frozenset({
    "pipeline_name", "edge_sequence", "start_ds", "end_ds",
    "expression_metadata",
})
PIPELINE_METADATA_FIELDS: frozenset[str] = frozenset({
    "status", "n_runs", "outcome_history", "provenance",
    "quarantine_threshold", "created_at", "tested_at",
    "activated_at", "quarantined_at", "quarantined_by",
    "retired_at",
})
```

The L2 validator `validate_mutation_discipline` reads the discipline + field partition + write payload and rejects writes that touch content fields on disciplines that forbid in-place content mutation. The partition-invariant validator `validate_partition_invariant` checks that CONTENT ∪ METADATA == declared field set and CONTENT ∩ METADATA == ∅.

Schemas without per-field partition (`mutable_with_retention`, `admin_authored`, `audit_only_after_settled`) skip the partition check; their discipline is gated by other mechanisms.

## Runtime dispatch (ADR-0153 §2)

`KnowledgeLayer.discipline_for(metagraph, role)` returns the role's declared discipline (or `None` if no L2Schema is installed). Lazy per-Metagraph dispatch cache populated on first lookup; cache key is `id(metagraph)`.

`KLWriteHandle.write_and_validate(...)` consults `discipline_for` at write time:

- `admin_authored` writes without `_is_admin=True` raise `MutationDisciplineError`.
- Other disciplines allow node CREATE. Their enforcement applies to subsequent **edits** of content fields / settled rows, not to creation. Edit-time enforcement composes `validate_mutation_discipline` at the per-field write boundary (deferred alongside the first L3 capacity that edits an existing node).

Schemas without an L2Schema-declared discipline (legacy raw `Schema` instances) get no discipline check.

## Exception surface

`MutationDisciplineError` (ADR-0153 §5) multi-inherits from `KnowledgeError` (L2 hierarchy) + `ValueError` (per literal ADR-0153 §5 text). Carries `iri`, `role`, `discipline`, `field`, `attempted_op`, `hint` attributes for discipline-aware remediation.

## Reference-stability (ADR-0153 §4)

The architectural commitment is **reference-stability**, not strict content-immutability. Storage content may change via the discipline-permitted mechanism (lazy inline-on-retire for episodes; never for promoted-pipelines content fields). Logical reference identity (IRI + version tuple) does not change.

ADR text + design docs use "reference-stable, content-may-snapshot-on-retire" for `episodic_memories`. Do not use "immutable" without qualifier.

## Cross-references

- Role-graphs: see [`role-graphs.md`](role-graphs.md).
- Storage tiers: see [`storage-tiers.md`](storage-tiers.md).
- ADR-0153 L2 mutation discipline.
- ADR-0152 §1/§2/§7 — per-role-graph field partitions.
- ADR-0094 §amendment-1 — `confidence` dropped from Pipeline.
