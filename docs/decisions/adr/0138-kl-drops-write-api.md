---
title: KL drops its write API; writes relocate to L3 capacities
status: Proposed
date: 2026-04-27
layer: L2
---

# ADR-0138: KL drops its write API; writes relocate to L3 capacities

**Status:** Proposed

**Date:** 2026-04-27

**Related:** ADR-0010 (layer isolation), ADR-0139 (hybrid invariant home), ADR-0140 (server owns admin), ADR-0141 (delete `promote()`), ADR-0143 (`KLWriteHandle`). Closes most of `docs/HANDOFF_L2_DESIGN_CONTINUATION.md` §5 Tier-1 list (5.1, 5.4, 5.5, 5.6, 5.7).

## Context

The 2026-04-27 L2 design pass clarified the cognitive-loop model:

> L1 owns mutation. L3 capacities are translations of L1 methods for specific uses. L4 is the orchestrator that decides which capacity to invoke and manages outputs. L3 never writes L2 directly — L1 does, on L3's behalf.

KL today ships a write API (`add_local_node`, `add_local_edge`, `add_local_alignment`, `promote`, `similarity_report`) gated by `session: SessionProtocol` + capability checks. That write API is *itself* a translation layer (capability check + role-graph routing + ref-shape composition + L1 calls). Under the clarified model, translations belong in L3 as named capacities, not in L2.

L2's responsibility narrows to long-term-memory data: holding the metagraphs, exposing read accessors and version-active routing, owning the schemas, and surfacing semantic-invariant validators that capacities call.

## Decision

**Drop KL's write API entirely.**

Specifically, the following shipped methods are deleted from `KnowledgeLayer`:

- `add_local_node(session, ...)`
- `add_local_edge(session, ..., target_is_global=...)`
- `add_local_alignment(session, ...)`
- `promote(session, ...)` (also covered by ADR-0141)
- `similarity_report(session, ...)` (also covered by ADR-0144)

Their behaviour relocates to L3 write capacities (per ADR-0145 / ADR-0146), which reach into KL's metagraphs through the `KLWriteHandle` accessor pattern (ADR-0143) and call L1 mutation primitives directly. KL keeps validators (ADR-0139) but no mutation methods.

KL retains:

- `MetagraphView` + `global_view()`, `local_view(user_id)`, `step()`, role-graph accessors (per ADR-0010 layer isolation; reaffirmed).
- Read-side `MetagraphView` filters using `include_deprecated=False` by default (per ADR-0133, applied at L2 read paths).
- Pure-function semantic validators on KL (per ADR-0139).
- Schemas + identifier builders + version-graph machinery.
- `bootstrap()` and importer adapters (which relocate to `mindsos_server` per ADR-0140).

## Rationale

The L1-mutates / L3-translates / L4-orchestrates partition is internally consistent only if L2 stops translating. Today's KL write methods are translation code: they map a domain concept ("add a Local node, optionally cross-ref a Global one") to a sequence of L1 operations. That mapping is exactly what an L3 capacity is.

Keeping KL writes alongside L3 capacities would either:

- duplicate the translation in two places (L4 reaches L2 through KL writes *and* through L3 capacities), or
- preserve the translation in KL while pretending L3 capacities own it.

Neither is honest. Removing KL writes is.

The cost is real: ~217 KL tests exercise the shipped write surface; they migrate to L3 capacity tests. The deletion is recoverable code (a few hundred LOC); the surface re-emerges in `mindsos_capacity` as named capacities with stable IRIs.

## Consequences

**Good:**

- L2's purpose is unambiguous: data + accessors + validators.
- L4 has one path to L2 mutation (via L3 capacities). No "which API do I call?" confusion.
- Capability checks consolidate at the L3 invocation boundary; L1 enforces structural invariants at write; KL validators enforce semantic invariants. Three honest layers, not four overlapping ones.
- The 217-test L2 surface shrinks to read + validator tests; L3 absorbs the write tests as capacity tests.

**Tradeoffs:**

- Substantial refactor: ~5–7 KL methods delete, equivalent capacities build in L3, ~200 tests migrate. Spread across the L3 chat's per-flow build pattern (ADR-0147), not landed in one PR.
- KL's `_check_global_target_exists`, `_check_role_routing` and similar helpers either become public validators (per ADR-0139) or move into `KLWriteHandle` (ADR-0143).
- The pivot's `propose_for_promotion()` (currently in `mindsos_knowledge/promotion_v2.py`) cannot stay in KL under this rule; relocates to `mindsos_server` per ADR-0140.

## Alternatives considered

1. **Keep KL writes as a private internal API; only L3 capacities allowed to call them.** Rejected — L2 is still translating, contradicting the principle. Discipline + caps enforce the rule but the code stays misplaced.
2. **Layered translation (KL writes as primitives; L3 capacities as domain-specific wrappers over them).** Rejected — two translation layers without distinct purpose. KL primitives end up looking exactly like L3 capacities one level lower.
3. **Defer the question; ship a pivot v1 with KL writes intact.** Rejected — blocks L4 design (the orchestrator can't be designed against a model the codebase contradicts).

## Implementation references

- L2 closure handoff: `docs/HANDOFF_L2_CLOSURE_2026-04-27.md`.
- L3 write design handoff: `docs/HANDOFF_L3_WRITE_DESIGN_2026-04-27.md`.
- Per-flow build pattern (ADR-0147) sequences the actual deletion + capacity build.
- ADR moves to Accepted when (a) `mindsos_knowledge` no longer ships write methods, (b) at least one L3 write capacity exists and is documented, (c) `docs/usage/knowledge/writing.md` is rewritten to describe the L4-via-L3 path.
