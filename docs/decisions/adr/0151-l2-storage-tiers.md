---
title: L2 storage tiers — inline, Falkor large-property, blob_ref
status: Accepted
date: 2026-06-01
layer: L2
---

# ADR-0151: L2 storage-tier discipline

**Status:** Accepted

**Date:** 2026-06-01 (L2 chat closure)

**Related (Accepted):** [ADR-0121](0121-falkordb-persistence.md),
[ADR-0150](0150-l2-knowledge-lifecycle.md),
[ADR-0044](0044-memories-move-to-local-per-user.md) §amendment-3,
[ADR-0152](0152-l2-role-graph-schema-v2.md),
[ADR-0153](0153-l2-mutation-discipline.md).

**Companion docs:** `_workbench/L2_CHAT_DECISIONS.md` D-L2-22;
`_workbench/CHAT_B_DECISIONS.md` D-B44.

## Context

Chat B (L5 design-resolution, 2026-05-31) D-B44 introduced a three-tier
storage convention for `DataStateInstance` and `TaskInput` payloads to
absorb the wide size variance v1 will see:

- Small payloads (chat-realm tokens, short structured outputs) →
  inline JSON property; backend-agnostic; cheap reads.
- Medium payloads (multi-paragraph text, parse trees, embedding
  vectors, intermediate Code-realm ASTs) → Falkor's BLOB-style large
  property; in-graph but separated from hot scan path.
- Large payloads (full corpus snippets, neural-model
  checkpoints, image/audio frames) → external blob store + IRI
  manifest; v2 only per FOL chat scope (Chat A R5 D30).

The convention crosses L2 / L4 / L5: episode containers in L2's
`episodic_memories` role-graph hold frozen `TaskInput` references; L4
substrate routes writes to the appropriate tier; downstream chats
(FOL installation, code-skill installation) need a single architectural
anchor to cite.

ADR-0121 (FalkorDB persistence) is too backend-specific — Tier 1 is
backend-agnostic (any JSON-capable backend) and Tier 3 is non-Falkor
(blob store + manifest). A backend-cross-cutting ADR is the right
home.

## Decision

**Three storage tiers** for L2 large-payload fields, declared per-schema
via a `storage_mode` property declaration alongside the value field.

| Tier | Range | Mechanism | `storage_mode` value | Backend-specific? |
|---|---|---|---|---|
| 1 — Inline | ≤ ~4 KB | JSON-encoded property | `"inline"` | No |
| 2 — Falkor large-property | ~4 KB to ~1 MB | Falkor BLOB-style property | `"falkor_blob"` | Yes (Falkor) |
| 3 — External blob_ref | > ~1 MB | v2 only; routed to FOL chat | `"blob_ref"` (reserved) | No (blob store + manifest IRI) |

**Schema-level declaration.** Schemas that carry large-payload fields
add a `storage_mode: Literal["inline", "falkor_blob", "blob_ref"]`
property alongside the value field. The mode is set at write time by
L4 substrate (based on serialized payload size) and stored as a hint
for read-time dispatch. Read APIs MUST consult `storage_mode` before
dereferencing the payload field.

**Threshold semantics.** The ~4 KB and ~1 MB boundaries are guidance,
not strict cutoffs. The L4 substrate may apply per-deployment tuning
within a hysteresis band (e.g., do not re-tier a payload that has
crossed the boundary by < 10%). Concrete thresholds and hysteresis
are L4-implementation; this ADR locks the three-tier shape and the
`storage_mode` discipline.

**v1 ships Tiers 1 + 2.** Tier 3 (external blob_ref) is reserved in
the `storage_mode` enum but rejected at write time in v1; raising a
clear `BlobRefNotSupportedError` until FOL chat picks the blob-store
design (Chat A R5 D30) and ships the v2 plumbing.

**v1 consumers.**

- `episodic_memories.Episode.task_input_ref` — XRef into a frozen
  `TaskInput` composite whose payload field carries `storage_mode`.
  Typical sizes span Tier 1 + Tier 2; Tier 3 awaits FOL.
- `learned-parameters.LearnedParameter.value` — when neural-model
  artifacts appear (post-FOL); v1 entries are scalar/dict at Tier 1.
- Future `DataStateInstance` frozen payloads inside Episode's
  `mm_root_ref` — same discipline cascades.

**Backward compat.** Phase 13 shipped schemas without `storage_mode`
declarations continue to work — implicit Tier 1. Schemas amended in
ADR-0152 (L2 role-graph schema v2) gain explicit declarations where
they carry large-payload fields. No retroactive write-time tier
re-routing for shipped data.

## Rationale

**Why three tiers, not two.** Two tiers (inline vs external) would
force Falkor's native BLOB capability into "external" framing, paying
network/serialization cost for medium payloads that fit in Falkor.
Three tiers match the actual storage-cost surface: ≤ ~4 KB is
property-scan-cheap; ~4 KB to ~1 MB is in-graph but separable; > ~1 MB
needs out-of-graph storage and an IRI manifest pattern.

**Why `storage_mode` field, not implicit.** Explicit declaration lets
read APIs dispatch without size-probing every payload. The field is
small (single string), always present, and survives lazy
inline-on-retire (the snapshot inherits the original mode).

**Why v2-defer Tier 3.** FOL chat (Chat A R5 D30) owns the blob-store
shape — IRI manifest, content-addressing, retention, GC. Designing
Tier 3 prematurely either presumes FOL's pick or commits to a shape
FOL would reject. Reserving the enum value preserves forward
compatibility without committing to internals.

**Why an ADR (not just docs).** Chat B introduces this as a v1
commitment crossing L2/L4/L5. Downstream chats (FOL installation,
code-skill installation, WSD installation) must cite an architectural
anchor when sizing their storage choices; a docs cookbook page has no
authority weight.

## Consequences

**Good:**

- Single architectural anchor for v1 storage-tier discipline; one
  cite-able decision across L2/L4/L5.
- Episode storage costs (Chat B PB-QQ) are explicitly bounded by the
  three tiers; retention policy fine-tuning (deferred to v1.5) builds
  on this foundation.
- Forward-compatible with FOL chat's Tier 3 design — `blob_ref` enum
  reserved; schema layout unchanged when FOL ships v2.
- Backend-cross-cutting: schemas declare storage discipline once;
  swapping FalkorDB for another backend re-implements Tier 2 without
  touching schemas.

**Tradeoffs:**

- L4 substrate carries tier-routing logic at write time
  (~100-200 LOC per Chat C estimate). Cost is bounded; not on L4's
  critical-path budget.
- `storage_mode` adds one property per large-payload field; minor
  schema bloat. Acceptable for explicit dispatch.
- Tier 2 ties one tier to FalkorDB. Backends without BLOB-style
  large-property support would need to merge Tier 2 into either Tier
  1 (with re-tuned threshold) or Tier 3 (with the FOL plumbing). v1
  is FalkorDB-only per ADR-0121; revisit if backend abstraction
  surfaces.
- Tier boundaries are not strict cutoffs — implementations must
  document the hysteresis band they apply.

**Lock-ins:**

- The `storage_mode` field name is part of the L2 schema contract.
  Renaming requires schema migration across all consumers.
- The three-value enum is the v1 commitment; expansion (e.g.,
  Tier 4 — streaming/chunked) is a future-ADR amendment.

## Alternatives considered

1. **Section in ADR-0121 (FalkorDB persistence).** Rejected — Tier 1
   is backend-agnostic; Tier 3 is non-Falkor. ADR-0121's scope is
   FalkorDB-as-graph-backend, not cross-backend storage discipline.

2. **New `docs/concepts/storage-discipline.md` cookbook page only.**
   Rejected — no architectural authority; downstream chats need an
   ADR to cite when their storage choices reference the tiers.

3. **Two tiers (inline + external blob_ref).** Rejected — collapses
   Tier 2 into Tier 3, paying out-of-graph cost for medium payloads
   that fit in Falkor's BLOB property. Wastes Falkor's native
   capability.

4. **Implicit tier dispatch by size at write time, no `storage_mode`
   field.** Rejected — read APIs would need to size-probe every
   payload to know how to dispatch; lazy inline-on-retire would lose
   tier metadata on the snapshot. Explicit field is cheaper.

5. **Ship Tier 3 in v1 with a stub blob-store implementation.**
   Rejected — presumes FOL chat's eventual pick. Stubs accumulate
   technical debt; clean deferral matches Chat A R5 D30.

## Source

Chat B D-B44 (PB-ZZ); L2 chat closure D-L2-22 + D-L2-12;
`_workbench/L2_CHAT_DECISIONS.md` R7 D-L2-22 for the alternatives
considered + rationale chain; Chat A R5 D30 for the FOL chat routing
of Tier 3 blob_ref.
