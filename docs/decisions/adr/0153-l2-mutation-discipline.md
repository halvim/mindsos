---
title: Per-role-graph mutation discipline + per-field content/metadata partition
status: Accepted
date: 2026-06-01
layer: L2
---

# ADR-0153: L2 mutation discipline

**Status:** Accepted

**Date:** 2026-06-01 (L2 chat closure)

**Related (Accepted):** [ADR-0150](0150-l2-knowledge-lifecycle.md) §amendment-4,
[ADR-0152](0152-l2-role-graph-schema-v2.md),
[ADR-0044](0044-memories-move-to-local-per-user.md) §amendment-3,
[ADR-0143](0143-kl-write-handle-pattern.md),
[ADR-0146](0146-l3-symmetric-write-invocation-contract.md).

**Companion docs:** `_workbench/L2_CHAT_DECISIONS.md` D-L2-3, D-L2-4,
D-L2-5; `_workbench/CHAT_A_DECISIONS.md` R6 D47.

## Context

Chat A R6 D47 surfaced the path-mutability question and routed it to
the L2 chat with the advisory preference of "immutable-with-successor-
IDs." Reanalysis during L2 chat (PB-A, PB-12) established that:

1. A single global mutability picks is too coarse. Different role-
   graphs have legitimately different mutation needs:
   - `parameter-staging` writes evidence rows continuously and prunes
     them by TTL. Mutable + retention is correct.
   - `pending-promotions` mutates until the audit decision settles,
     then must be frozen for audit chain.
   - `promoted-pipelines` content (`edge_sequence`) is immutable per
     WSD §A.2; status / lifecycle metadata is mutable in place.
   - `episodic_memories` Episodes are append-only externally; lazy
     inline-on-retire is the only permitted internal mutation per
     Chat B D-B17.
   - `ontology` / `lexicon` / `concepts` / `alignment:*` are admin-
     written via importers; not L4/L3 write targets.

2. Even within a single role-graph, "immutable" doesn't apply
   uniformly. `promoted-pipelines.status` MUST mutate to support
   lifecycle (draft → tested → active → quarantined → retired). If
   status mutation requires successor IRIs, every transition breaks
   every reference (in-flight `PipelineRun`s, MM pins, task-pattern
   `paired_pipelines` back-references). The fix is a per-field
   partition: content fields require successors on change; metadata
   fields mutate in place.

3. Chat B's "Episode immutability invariant" is not strictly
   immutability — lazy inline-on-retire replaces version-pinned
   tuples with content snapshots. The framing must be reference-
   stable, not content-immutable.

Without explicit discipline declarations, every L2 write site needs a
case-by-case judgment, and drift is guaranteed. With explicit
declarations, mutation enforcement is a one-pass field-mask check at
write time.

## Decision

### §1 Per-role-graph mutation discipline declaration

Every L2 role-graph schema declares a `mutation_discipline` at build
time. v1 enum:

| Discipline | Semantics | v1 role-graphs |
|---|---|---|
| `immutable_successor` | Content fields are write-once; updates mint a successor IRI. Metadata fields mutate in place. | `promoted-pipelines`, `task-patterns`, `world-axioms` (when WSD ships) |
| `append_only_with_lazy_inline` | External writes are append-only on content fields. Lazy inline-on-retire (when a referenced version retires) is the only permitted internal mutation; substitutes inline snapshot for version-pinned tuple. Metadata fields mutate freely. | `episodic_memories` |
| `mutable_with_retention` | Rows are mutable; admin-tunable retention TTL prunes old rows. | `parameter-staging`, `capacity-gaps`, `capacity-state`, `learned-parameters` (Local) |
| `audit_only_after_settled` | Rows mutate until terminal status (`status ∈ {applied, rejected}` etc.); once settled, frozen for audit chain. | `pending-promotions` |
| `admin_authored` | Mutation only via admin importer or admin tooling; no L4/L3 write path. | `ontology`, `lexicon`, `concepts`, `alignment:*`, `learned-parameters` (Global) |
| `append_only` | All fields append-only; no retention; no successor; no lazy inline. | `problem-trace` |

### §2 L4 startup invariant

`KnowledgeLayer.bootstrap()` walks installed role-graphs; each `Schema`
reports its `mutation_discipline`; L4 builds a runtime dispatch table
that enforces discipline at write time:

- Write attempt against a content field on `immutable_successor` →
  `MutationDisciplineError` raised; caller must mint successor IRI
  instead.
- Write attempt against content field on `append_only_with_lazy_inline`
  (other than the lazy-inline mechanism) →
  `MutationDisciplineError`.
- Write attempt to a settled row on `audit_only_after_settled` →
  `MutationDisciplineError`.
- Write attempt outside admin importer on `admin_authored` →
  `MutationDisciplineError` (importer flag bypasses).
- Other disciplines allow free mutation.

Enforcement is a startup invariant; the dispatch table is built once
at `KnowledgeLayer.bootstrap()` and consulted on every write through
`KLWriteHandle` (ADR-0143).

### §3 Per-field `content` vs `metadata` partition

Schemas with discipline `immutable_successor`, `append_only_with_lazy_inline`,
or `append_only` MUST declare per-node-type field partition via two
module-level frozensets:

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

Concrete per-role-graph partitions are recorded in ADR-0152 §1–§7.

The L2 validator `validate_mutation_discipline` reads the discipline +
field partition + write payload and rejects writes that touch content
fields on disciplines that forbid in-place content mutation.

Schemas without per-field partition (e.g., `mutable_with_retention`
disciplines like `parameter-staging`) skip the partition check; the
discipline itself permits free mutation.

### §4 Wording lock — reference-stability, not strict immutability

The architectural commitment is **reference-stability**, not strict
content-immutability. Storage content may change via the discipline-
permitted mechanism (lazy inline-on-retire for episodes; never for
promoted-pipelines content fields). Logical reference identity
(IRI + version tuple) does not change.

ADR text + design docs MUST use "reference-stable, content-may-
snapshot-on-retire" for `episodic_memories`. Do not use "immutable"
without qualifier — overstates the guarantee and confuses lazy-inline
semantics.

Chat B's "Episode immutability invariant" framing gets a docs cross-
reference noting this ADR supersedes the wording without changing
the picks.

### §5 New exception type

`mindsos_knowledge.exceptions.MutationDisciplineError(ValueError)` is
the raised exception. Carries:

- `iri: str` — the target node IRI.
- `role: str` — the role-graph.
- `discipline: str` — the declared discipline.
- `field: str` — the field that triggered the violation.
- `attempted_op: Literal["write_content","mutate_settled","admin_only"]`.
- `hint: str` — recommended remediation ("mint successor IRI",
  "use lazy-inline mechanism", "promote via admin importer").

### §6 Schema-level API additions

`mindsos_core.Schema` gains:

```python
@dataclass
class Schema:
    strict: bool = False
    mutation_discipline: Literal[
        "immutable_successor",
        "append_only_with_lazy_inline",
        "mutable_with_retention",
        "audit_only_after_settled",
        "admin_authored",
        "append_only",
    ] = "mutable_with_retention"  # backward-compat default
    ...
```

Phase 13 shipped schemas amend their `build_*_schema(strict)` bodies
to declare discipline. Backward compatibility: schemas built without
declaring discipline default to `mutable_with_retention` (matches the
shipped behavior).

## Rationale

**Why per-role-graph, not global.** D47's binary framing breaks at the
first counter-example (`parameter-staging` needs mutability). Per-role
discipline matches the ground truth and lets each role-graph evolve
independently.

**Why per-field partition.** Without it, `immutable_successor` is
unenforceable — status mutation can't require a successor IRI without
shattering every reference; treating status as content forces every
lifecycle transition through a successor-mint pipeline, which is
absurd. Partitioning content from metadata makes the discipline both
expressive and enforceable.

**Why a startup invariant, not write-time validation.** Write-time
validation requires every writer to consult the discipline table;
startup invariant builds the dispatch table once and embeds it in
`KLWriteHandle`. Matches Chat A R3 D51 "L3 reachability invariant"
pattern.

**Why a new exception type.** Discipline violations are programmer
errors per ADR-0146 §Decision (propagate vs catch). A distinct
exception type signals "you need a successor IRI" cleanly rather than
swallowed into generic `ValueError`. Carries enough metadata for the
caller to take the right remediation.

**Why "reference-stability" wording.** Chat B's "immutability invariant"
overstated the guarantee — lazy inline-on-retire mutates storage
content. The correct invariant is reference identity, not content
identity. Honest framing prevents downstream chats from designing
against a guarantee that doesn't hold.

## Consequences

**Good:**

- D47 closure is enforceable, not aspirational.
- `promoted-pipelines` lifecycle (5-state status enum, system-
  triggered quarantine) composes cleanly with content-immutability
  via the per-field partition.
- `episodic_memories` Episode invariant has a precise wording
  (reference-stable, lazy-inline-permitted) that survives Chat B's
  PB-QQ retention-policy fine-tuning.
- New role-graphs declare discipline up-front; no drift.
- Validator `validate_mutation_discipline` is one of the 4 unconsumed
  L2 validators (Phase 38 carry-forward item #9) — this ADR gives it
  a concrete consumer.

**Tradeoffs:**

- 5 enum values is a vocabulary tax. Each value is meaningful (no
  collapse possible without losing real semantic distinctions).
- Phase 13 shipped schemas need amendment (one-liner discipline
  declaration + content/metadata frozensets where applicable). Chat C
  plan-authoring sequences the deploy phase.
- L4 startup invariant adds a small fixed cost to
  `KnowledgeLayer.bootstrap()` (build dispatch table over installed
  role-graphs). Linear in role-graph count; negligible at v1 scale.
- New exception type adds catch-site surface for downstream callers;
  most callers can let it propagate per ADR-0146.

**Lock-ins:**

- Discipline enum values are part of the L2 schema contract. Adding
  a new discipline is an ADR amendment + enforcement-table change.
- Per-field partition frozenset names (`*_CONTENT_FIELDS`,
  `*_METADATA_FIELDS`) are the convention; renaming breaks importer
  code.

## Alternatives considered

1. **Single global D47 pick (`immutable_successor` everywhere).**
   Rejected — incompatible with `parameter-staging`, `capacity-state`,
   `capacity-gaps`. Forces special-casing per role-graph anyway.

2. **Docstring discipline only; no formal field.** Rejected —
   D47's whole point was preventing drift. Discipline-by-convention
   drifts.

3. **Two disciplines (immutable / mutable).** Rejected — collapses
   `append_only_with_lazy_inline`, `audit_only_after_settled`, and
   `append_only` into one of two buckets, losing the semantic
   distinctions that make them useful.

4. **Discipline enforced only at validator layer (no startup
   invariant).** Rejected — validators are post-hoc; startup invariant
   catches misregistration at deploy time. Cheaper to catch early.

5. **Per-field partition lifted to discipline-level metadata.**
   Rejected — different node types in the same role-graph have
   different field partitions (e.g., Episode vs Memory in
   `episodic_memories`). Per-node-type partition is the right
   granularity.

6. **Use Chat B "immutability invariant" wording verbatim.** Rejected
   — lazy inline-on-retire is content mutation; reference-stability
   is the correct frame.

## Source

`_workbench/L2_CHAT_DECISIONS.md` D-L2-3, D-L2-4, D-L2-5;
`_workbench/CHAT_A_DECISIONS.md` R6 D47 (advisory direction);
`_workbench/CHAT_B_DECISIONS.md` D-B17 (Episode immutability
invariant — reframed as reference-stability here); WSD `pending_adrs/
L2_knowledge.md` §A.2 (paths value-typed); Chat A R3 D51 (L3
reachability invariant pattern).
