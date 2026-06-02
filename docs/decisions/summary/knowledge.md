---
title: L2 Knowledge decisions
tag: shipped
teaser: All architectural decisions affecting the Knowledge Layer (long-term memory).
next: decisions/summary/capacity.md
---

# L2 Knowledge decisions

Knowledge is MindsOS's long-term memory: a Global metagraph of versioned, role-tagged graphs (ontology, lexicon, concepts, memories, problem traces) plus per-user Local graphs with private knowledge. These decisions define the versioning contract, the multi-tenant split, and the handoff to the Server Layer.

| ADR # | Title | Status | Summary |
|-------|-------|--------|---------|
| [0038](../adr/0038-session-write-api.md) | Session-based write API replaces bare `user_id` string | Accepted | Write methods take `session: SessionProtocol` for defense-in-depth and capability checks |
| [0039](../adr/0039-transitional-str-shim-deprecation.md) | Backward-compat `str` shim with `DeprecationWarning` during migration | Accepted | Legacy callers emit warnings; removed once Server Phase 1 lands |
| [0040](../adr/0040-session-protocol-duck-typing.md) | `SessionProtocol` via duck-typing, not `TYPE_CHECKING` import | Accepted | Structurally-typed Protocol preserves layer isolation (I-S1) |
| [0041](../adr/0041-duplicate-capability-constants-parity-test.md) | Duplicate capability strings in KL; parity enforced by test | Accepted | Four capabilities (`can_read_other_locals`, `can_write_global`, `can_promote`, `can_hard_delete_archived`) with parity test to detect drift |
| [0042](../adr/0042-kl-install-extract-hooks.md) | Server-driven hydration via explicit `install_local_metagraph` / `extract_local_metagraph` | Accepted | Strict preconditions prevent double-hydration; server owns persistence lifecycle |
| [0043](../adr/0043-kl-in-memory-only-server-owns-io.md) | KL stays in-memory only; server owns all FalkorDB I/O | Accepted | Tests run without I/O; backend can be swapped at the server layer |
| [0044](../adr/0044-memories-move-to-local-per-user.md) | Memories move from Global to Local per user | Accepted | Privacy and correctness: raw task history is autobiographical, not systemic knowledge |
| [0045](../adr/0045-per-role-iri-builders.md) | Per-role IRI builders for all upper-layer roles | Accepted | One source of truth per role syntax (pipeline, memory, problem-trace, etc.) |
| [0046](../adr/0046-admin-enforcement-capability-based.md) | Admin enforcement is capability-based, not role-based | Accepted | Fine-grained checks via `session.has(capability)` support multi-admin models |
| [0047](../adr/0047-ref-types-open-vocabulary.md) | `REF_TYPES` is an open vocabulary with explicit extension recipe | Accepted | New types added via frozenset + docs + test + parity check |
| [0048](../adr/0048-proxy-pattern-handles-all-local-global.md) | Proxy pattern handles every Local→Global edge; no per-role carve-out | Accepted | One code path for all cross-role references via lazy proxy node creation |
| [0049](../adr/0049-similarity-report-before-promotion.md) | Admin must review a similarity report before non-forced promotion | Accepted | Deterministic report with `report_id` gates non-forced promotion; force=True available with audit stamp |
| [0050](../adr/0050-server-owns-promotion-orchestration.md) | Server owns promotion orchestration; KL owns graph writes | Accepted | Clean split: server handles locks, persistence, rollback; KL handles writes and validation |
| [0051](../adr/0051-promoted-ref-type-marks-surviving-draft.md) | `PROMOTED` ref_type marks the surviving Local draft | Accepted | Draft stays as breadcrumb with `ref:global_<role>` and `ref_type=PROMOTED` |
| [0052](../adr/0052-report-id-deterministic-content-hash.md) | `report_id` is a deterministic content-hash, not a UUID | Accepted | Freshness check via sha256 of sorted canonical JSON; same state → same id |
| [0053](../adr/0053-promote-per-candidate-atomic-rollback.md) | `promote` does per-candidate atomic rollback internally | Accepted | Undo stack runs on failure before raise; server's snapshot is outer safety net |
| [0054](../adr/0054-promotion-validation-error.md) | `PromotionValidationError` as KL-specific promotion failure | Accepted | Allows server to distinguish validation failures from argument errors for audit |
| [0055](../adr/0055-baseline-similarity-heuristic-crude.md) | Baseline similarity heuristic is deliberately crude | Accepted | Deterministic algorithm for matching on values; strength improves iteratively |
| [0056](../adr/0056-promotion-result-preserves-input-order.md) | `PromotionResult.promoted` preserves input order; candidates deduped | Accepted | Dedup without reorder for audit correlation; `similarity_report` sorts independently |
| [0057](../adr/0057-property-inventory-admin-run.md) | Property-inventory helper is admin-run, not on hot path | Accepted | Scan metagraph on demand for strict-mode migration preparation |

## Deferred decisions

| ADR # | Title | Status | Summary |
|-------|-------|--------|---------|
| [0058](../adr/0058-authoring-methods.md) | `list_authored`, `inspect_authored`, `hard_delete` authoring methods | Proposed | Not yet shipped; will accept `session: SessionProtocol` from day one |
| [0059](../adr/0059-prune-promoted-drafts.md) | Pruning promoted Local drafts | Proposed | Current topology keeps drafts indefinitely; bulk-cleanup is future admin surface |

## L2 redesign (2026-04-27)

The 2026-04-27 design pass relocates KL's write API into L3 as named capacities and reframes L2 as data + accessors + validators. ADRs 0049 (similarity-review gate), 0050 (promotion orchestration), 0051 (PROMOTED ref_type), 0052 (report_id content-hash), 0053 (atomic rollback), 0055 (crude similarity heuristic) are superseded or amended by the new ADRs below. Status: Proposed (decisions locked; code and user-facing docs follow).

| ADR # | Title | Status | Summary |
|-------|-------|--------|---------|
| [0138](../adr/0138-kl-drops-write-api.md) | KL drops its write API; writes relocate to L3 capacities | Proposed | `add_local_node`/`_edge`/`_alignment`/`promote`/`similarity_report` delete from `KnowledgeLayer`; behaviour relocates as L3 write capacities |
| [0139](../adr/0139-hybrid-invariant-home.md) | Hybrid invariant home (L1 structural + KL semantic) | Proposed | L1 enforces structural invariants at write; KL exposes pure-function semantic validators that L3 capacities call as preconditions |
| [0140](../adr/0140-server-owns-admin-operations.md) | Server owns bootstrap and admin operations | Proposed | Importers + `propose_for_promotion` + `release_update` move to `mindsos_server`; outside the cognitive loop |
| [0141](../adr/0141-delete-shipped-promote.md) | Delete shipped `KL.promote()` (ADR-0118 path is canonical) | Proposed | Pivot supersedes; no coexistence; supersedes ADR-0007 + ADR-0050 + ADR-0053 |
| [0142](../adr/0142-xref-cutover-for-ref-global.md) | XRef cutover for `ref:global_<role>` user data | Proposed | New writes go to XRef rows (per ADR-0128); read-time fallback on legacy properties; one-time migration job |
| [0143](../adr/0143-kl-write-handle-pattern.md) | `KLWriteHandle` pattern for L3 write capacities | Proposed | `kl.writeable(session, role, scope)` returns a non-mutating accessor; capacities call L1 through `handle.graph()` |
| [0144](../adr/0144-similarity-at-release-ship-audit-gate.md) | Similarity at release-ship audit gate; restore spec | Proposed | Similarity moves to ADR-0115 audit step; restored Levenshtein + structural overlap + reference Jaccard; supersedes ADR-0049 + ADR-0052 + ADR-0055 |

See `docs/HANDOFF_L2_CLOSURE_2026-04-27.md` for the full closure handoff.

---

**Next:** [L3 Capacity decisions](capacity.md) — fixed abilities, discovery, and reactive/resident capacities.
