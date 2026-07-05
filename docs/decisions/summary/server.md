---
title: Server decisions
tag: shipped
teaser: Architectural decisions shaping multi-user access, identity, and promotion.
next: decisions/summary/cross-layer.md
---

# Server decisions

The Server Layer is **orthogonal** to the domain stack (per ADR-0136) — it provides a runtime envelope (auth, sessions, capability-based authorization, audit, persistence orchestration, lifecycle) that any consumer of the domain layers needs. It is not "Layer 0"; the stack is L1–L5. The ADRs below cover all cross-cutting concerns — they are already numbered 0001 through 0013 and were the earliest decisions made in the MindsOS architecture.

!!! warning "Pivot in progress (2026-04-26)"
    A multi-session design conversation in April 2026 produced a model pivot for how Globals are curated and released. Eight new ADRs (0113–0120) are **Proposed** and will supersede or amend several of the ADRs in the table below when they land. Most consequentially:

    - **ADR-0007** (`MetagraphSnapshot` rollback) — to be superseded in full by **ADR-0118** (per-user transactional promotion + release-boundary atomicity).
    - **ADR-0009** (similarity-report freshness) — to be superseded by **ADR-0115** (audit gate). The freshness-id mechanism is removed; similarity becomes part of the audit gate.
    - **ADR-0001, 0002, 0004** — to receive amendments documenting release-management responsibilities and the new `releases` table in the SQLite schema.
    - **ADR-0005** (refuse concurrent login) and **ADR-0006** (promotion locking) — to be revisited in a v2 follow-up. Per-user mutex stays in v1; concurrent-login relaxation is v2.

    Until ADRs 0113–0120 land, the table below describes the **shipped** model. New work should reference [the pivot scope contract](../../PIVOT_V1_SCOPE_2026-04-26.md) and [the release-model concept page](../../concepts/release-model.md). The handoff for the next implementation session is at [docs/HANDOFF_SERVER_PIVOT_2026-04-26.md](../../HANDOFF_SERVER_PIVOT_2026-04-26.md).

| ADR # | Title | Status | Summary |
|-------|-------|--------|---------|
| [0001](../adr/0001-dedicated-server-layer.md) | Introduce a dedicated Server Layer above the domain stack | Accepted | Auth, sessions, audit, promotion orchestration live in a separate top-level package |
| [0002](../adr/0002-session-and-capability-model.md) | Session-plus-capability authorization model | Accepted | `Session` carries `user_id`, `session_id`, `actor_role`, `capabilities` set, and `has(capability)` method |
| [0003](../adr/0003-password-and-token-scheme.md) | argon2id password hashing + 256-bit opaque session tokens | Accepted | Sliding + absolute TTL; secure credential storage |
| [0004](../adr/0004-split-persistence.md) | SQLite for server state, FalkorDB for graphs | Accepted | Clean separation: SQLite for identity/audit, FalkorDB for domain data |
| [0005](../adr/0005-refuse-concurrent-login.md) | Refuse concurrent login; provide kill-session escape valves | Accepted | One session per user at a time; admin can kill sessions to recover |
| [0006](../adr/0006-promotion-locking.md) | Per-user RLocks + GLOBAL_PROMOTE_LOCK in lexicographic order | Accepted | Deadlock-free multi-user coordination for safe promotion |
| [0007](../adr/0007-metagraph-snapshot-rollback.md) | In-memory `MetagraphSnapshot` for promotion rollback | Superseded by [0118](../adr/0118-per-user-transactional-promotion.md) | Deep copy on enter; mutate in place on rollback |
| [0008](../adr/0008-cross-user-reads-no-flush.md) | Admin cross-user reads never flush (I-S3) with refcount install | Accepted | Transient installs for read-only admin queries |
| [0009](../adr/0009-similarity-report-freshness.md) | Similarity-report freshness via content hash | Accepted | Stale reports detected by re-computing hash |
| [0010](../adr/0010-layer-isolation.md) | KL does not import server (I-S1); L3 accepts `SessionProtocol` | Accepted | Hard layer boundaries; domain layers never depend upward |
| [0011](../adr/0011-local-persister-protocol.md) | `LocalPersister` protocol with session-scoped hydrate/flush | Accepted | Flexible adapter for per-user Local metagraphs |
| [0012](../adr/0012-bootstrap-and-last-admin.md) | Bootstrap and reset-admin CLIs + last-admin protection | Accepted | Admin creation and emergency recovery; at least one admin required |
| [0013](../adr/0013-audit-and-test-shim.md) | Universal audit logging and `Session.for_testing()` shim | Accepted | Every mutation logged; tests construct sessions without server |

### Pivot ADRs (drafted 2026-04-26 onward)

| ADR # | Title | Status | Summary |
|-------|-------|--------|---------|
| [0118](../adr/0118-per-user-transactional-promotion.md) | Per-user transactional promotion + release-boundary atomicity | Accepted | Supersedes ADR-0007 in full. Two independent atomicity boundaries: per-user `propose_for_promotion` and admin-triggered `release_update`. Lazy per-user migration runs separately. Slice ships ATOM-only; STRUCTURE/SUBGRAPH/PIPELINE land with ADR-0117/0119/0120. |
| 0113 | Mutation model — Resolution A | Reserved | Mutation auto-bumps version under the hood; admin UX is "edit," storage is append-only. |
| 0114 | Release manifest + version DB schema (SQLite) | Reserved | Schema for `pending_mutations`, `releases`, `node_versions`, `peer_deps`. |
| 0115 | Audit gate + impact report format | Reserved | Supersedes ADR-0009. Pre-ship audit; structured `ImpactReport`; no override in v1. |
| 0116 | Edge soft-delete model (deprecated/disputed) | Reserved | Soft delete default; hard delete is v2 with whitelist + quorum. |
| 0117 | Compositional metaedge immutability (`CompositionalMetaEdge`) | Reserved | Composition is identity; new Core subclass enforces write-once. |
| 0119 | Composition-signature dedup at promote | Reserved | Hash of sorted component ids + edge labels; promote-time dedup. |
| 0120 | Cross-layer rewrite handler contract (KL + Capacity in v1) | Reserved | Each layer exposes `rewrite_refs(old_id, new_id)` per a shared contract. |

### L1 redesign — server-touching ADRs (drafted 2026-04-27)

The L1 redesign pass produced two server-layer ADRs in addition to its L1 Core surface. See `docs/HANDOFF_L1_REDESIGN_2026-04-27.md` for the full context.

| ADR # | Title | Status | Summary |
|-------|-------|--------|---------|
| [0125](../adr/0125-lazy-local-hydration-with-lru-eviction.md) | Lazy Local hydration with LRU eviction | Deferred | Login no longer hydrates; first read/write triggers; idle Locals evicted under RAM watermark |
| [0136](../adr/0136-server-as-orthogonal-layer.md) | Server is orthogonal to the domain stack, not Layer 0 | Accepted | Documentation pass: Server provides runtime envelope, not layer composition |
| [0137](../adr/0137-user-facing-request-promotion.md) | User-facing `request_promotion` API | Deferred | New ordinary-user API to surface promotion candidates; admin reviews and triggers `propose_for_promotion` |

---

**Next:** [Cross-layer decisions](cross-layer.md) — layer boundaries, isolation, and handoffs.
