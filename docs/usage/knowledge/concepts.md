---
last_confirmed_phase: 13
---

# Concepts role schema

FrameNet concepts vocabulary. **4 NodeTypes, 11 EdgeTypes,
0 HyperEdgeTypes** at `strict=False`.

## NodeTypes

`Frame`, `FrameElement`, `LexicalUnit`, `SemanticType`.

## EdgeTypes

`EVOKES` (LU → Frame), `HAS_FE` (Frame → FrameElement).

**Frame-to-frame:** `INHERITS_FROM`, `USES`, `PERSPECTIVE_ON`,
`SUBFRAME_OF`, `PRECEDES`, `IS_CAUSATIVE_OF`, `IS_INCHOATIVE_OF`.

**FE-level:** `FE_TYPED_AS` (FrameElement → SemanticType),
`FE_MAPPED_TO` (FrameElement → FrameElement).

## Strict-tighten status

`strict=False` (ADR-0149).

## Where it's used

Phase 15 (FrameNet importer) is the first content consumer.
Phase 14 (KL bootstrap) calls `ensure_role_graph(global_mg, "concepts")`.
