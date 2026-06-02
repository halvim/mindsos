---
title: report_id is a deterministic content-hash, not a UUID
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-015]
---

# ADR-0052: report_id is a deterministic content-hash, not a UUID

**Status:** Accepted

**Date:** 2026-04-22

## Context

The server's freshness check compares the `reviewed_similarity_report_id` the admin confirmed to the id of a freshly-generated report. A UUID would force a side-channel for the check. A content hash makes the check trivial.

## Decision

`report_id = sha256(candidate_set || per_local_content_hash || global_content_hash)`, where `metagraph_content_hash(mg)` is sha256 of a canonical JSON serialisation (sorted graphs → sorted nodes/edges → sorted properties). Same inputs + same Local states → same id. Mutation → different id.

## Consequences

**Good:**
- Freshness check is a one-line equality.
- `metagraph_content_hash` is reusable — the server's audit / coherence tooling can use the same primitive.

**Bad:**
- Core's `Metagraph` has no native content hash, so KL computes its own.

## Alternatives considered

None recorded; this was the consensus choice during the 2026-04-22 design session.

## Revisions

### amendment-1 (Phase 16 ship — 2026-05-20) — role-scoped hash + 6-decimal canonicalization + cross-mg input extension

Per Phase 16 PB-F2 + PB-T2 + PB-K2, three clarifications to the §Decision hash construction:

**1. Hash scope is per-role-graph, not whole-metagraph.** `metagraph_content_hash(mg, *, role)` hashes ONLY the role-graph named by `role`, not every contained graph in the metagraph. Cross-role mutation (e.g., a parallel importer populating `lexicon` while a similarity report is being computed against `ontology`) does NOT invalidate the report. The original §Decision phrasing "the Global's metagraph_content_hash" is reinterpreted as "the role-graph being scored within Global".

WAL + tombstones + soft-deleted nodes (per ADR-0133's `deprecated_at`) are excluded by construction (different graphs in the metagraph; not visited under role-scoped hashing).

**2. 6-decimal canonicalization for numeric inputs.** Cross-machine + cross-Python-version determinism requires explicit FP precision. Numeric inputs to the hash string (thresholds; any FP value joined into the canonical-JSON input) are canonicalized via `f"{x:.6f}"` before joining. `Finding.score` outputs are `round(x, 6)`. This defends `report_id` against refactor-induced summation-order changes.

**3. Hash input set extends to `(mg_role_hash, target_mg_role_hash)` when `compute_similarity`'s `target_mg` kwarg is given** (per PB-K2 Phase 24 reuse signature). Intra-mg calls (`target_mg=None`) hash one role-graph. Cross-mg calls (Phase 24's release-ship audit gate: pending Global vs canonical Global) hash both.

**Reusability call-out preserved:** `metagraph_content_hash` ships at `mindsos_admin/_content_hash.py` (public surface; Phase 24's audit gate at `mindsos_admin/promotion.py` consumes the same primitive). The original §Consequences "reusable" claim is honoured.

**Phase 16 design log:** `halvim_mindsos/confirmation_docs/PHASE_16_DESIGN_LOG.md` §1 Round 3 PB-F + Round 4 PB-K + Round 5 PB-T.
