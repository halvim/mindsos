---
title: Proposed and deferred decisions
tag: shipped
teaser: Open design questions and decisions that have been acknowledged but not yet scheduled.
---

# Proposed and deferred decisions

This page holds decisions that are acknowledged, understood, and have a known path forward — but are not yet scheduled for implementation. They are grouped by layer.

Most deferred decisions carry a known tradeoff. The system works well even though the decision is deferred; fixing it would improve something non-critical or would require design work out of scope for the current layer's maturity.

!!! warning "Largely historical — most items below have shipped"
    The **L1 Core redesign (ADRs 0121–0137)** and the **Server-layer pivot (ADRs 0114/0115/0118 …)** captured on this page have since **shipped**. Their ADR files may still carry `status: Proposed` front-matter that was never flipped — treat the individual ADR + the [changelog](../changelog/CHANGELOG.md) as authoritative, not this page. The only genuinely-open proposals are the **perception ADRs 0191–0194** in the section at the bottom.

## L1 Core Layer — redesign 2026-04-27

The 2026-04-27 L1 redesign pass turned the long-deferred items below into Proposed ADRs (0121–0137) plus their downstream coordinated changes. See `docs/HANDOFF_L1_REDESIGN_2026-04-27.md` for the migration plan.

### Property bag on `Metagraph` / `Graph` — Proposed (ADR-0130)

Resolved by **ADR-0130** (formerly ADR-0033 deferred + ADR-0029 interim). `properties: Dict[str, Any]` on both `Metagraph` and `Graph`; supersedes the `:MetagraphSettings` JSON-singleton workaround.

### Reference walking and integrity — Resolved by ADR-0128 (hybrid XRef)

ADR-0128 introduces first-class `XRef` for cross-metagraph references with write-time validation, while retaining `ref:<role>` strings for intra-metagraph (which don't auto-upgrade). ADR-0034 amended.

### UUID determinism — Resolved by ADR-0131 (pluggable IdStrategy)

ADR-0131 introduces `IdStrategy` Protocol with `UUID4Strategy` (default), `UUID5FromContentStrategy`, and `IRIPassthroughStrategy`. Tests can opt into determinism; KL importers formalise their IRI-passthrough pattern. ADR-0035 amended.

### Multi-writer concurrency — Resolved by ADR-0127 (OCC on Global)

ADR-0127 adds optimistic concurrency on Global writes via `_version` property. Per-user Locals stay single-writer (per-user mutex enforces). ADR-0036 amended.

### Instancing vocabulary placement — Resolved by ADR-0132 (move to `mindsos_instances`)

ADR-0132 moves `ElementInstance` and friends to a sibling `mindsos_instances` package. Core shrinks; L5 owns its vocabulary natively. ADR-0037 superseded.

## L1 Core Layer — additional redesign decisions

### Substrate commitment — ADR-0121

FalkorDB stays as graph substrate; SQLite is reserved for non-graph state (auth, audit, version DB). Six paired weakness mitigations (0122–0127) ship as siblings.

### Multi-statement write safety — ADR-0122

WAL graph (`:WAL` sibling Graph per Metagraph) protects multi-statement writes. KL `propose_for_promotion` uses it; `MetagraphSnapshot` narrows to release-ship.

### Integrity detection — ADR-0123

FalkorDB indexes + persist-time check + per-layer `verify_integrity` scanners. `mindsos-server fsck` CLI.

### Streaming loader — ADR-0124

`iter_load(batch_size)` for memory-bounded loads; `MetagraphLoader.refresh(role)` for delta reloads. `LazyGraph` deferred to future implementation.

### Lazy Local hydration — ADR-0125

Login no longer hydrates; first read/write triggers. LRU eviction under RAM watermark.

### `AsyncClient` Protocol — ADR-0126

Thread-pool wrapper around sync Client. Ships now (no real consumer yet) to avoid downstream layers wrapping ad-hoc.

### MetagraphSnapshot scope narrowed — ADR-0129

KL drops snapshot for ordinary writes; uses WAL. Snapshot retained for release-ship canonical-Global rollback only.

### Soft-delete representation — ADR-0133

`deprecated_at` / `disputed_at` properties on edges; default `include_deprecated=False` on Core read APIs. `disputed_at` does not filter by default (different semantic).

### Schema migration scanner — ADR-0134

`Schema.migrate_from(old, on_violation=...)` returns violations. `unknown_edge_type_policy` config flag flips loader's silent-drop to warn-or-error.

### `RemovalImpact` on `remove_graph` — ADR-0135

`remove_graph` returns structured impact report (incoming XRefs + ref-string scan); `force=False` default blocks removal when impact non-empty.

### Server orthogonal placement — ADR-0136

Server is orthogonal to the domain stack, not Layer 0. Documentation pass across `CLAUDE.md`, layers concept, summary docs.

### User-facing `request_promotion` — ADR-0137

User-initiated promotion request; admin reviews and approves/rejects. Coexists with admin-direct `propose_for_promotion`.

## L2 Knowledge Layer

### Authoring and deletion methods — Proposed

Future methods: `list_authored`, `inspect_authored`, `hard_delete`. Will accept `session: SessionProtocol` from day one (no migration shim). See **ADR-0058**.

### Pruning promoted drafts — Proposed

Current topology keeps Local drafts as breadcrumbs after promotion. Bulk cleanup is future admin surface. See **ADR-0059**.

## L3 Capacity Layer

### Pipeline generation as a capacity — Proposed

Procedures that assemble pipelines (map task → pipeline, order steps, pick alternates) should be L3 capacities, not L4 code. See **ADR-0082**. Current `find_pipeline` is close; register it once L4 design settles.

### Transitive promotion of dependencies — Proposed

Pipelines mixing Global and Local capacities cannot safely promote without promoting all Local step dependencies first. See **ADR-0083**. Admin tool should display dependency graph and gate promotion.

## L4 Intelligence Layer — SHIPPED

The Phase 46–48 convergence **shipped** Layers 4 and 5. The original design-phase menu (ADRs 0101–0112) was settled at the Chat A/B foundation chats and superseded by the shipped decisions **ADRs 0163–0181**. See [L4/L5 decisions](summary/intelligence.md). The 0101–0112 files remain as historical design exploration and should not be read as open questions.

## Server Layer pivot — 2026-04-26

A multi-session design conversation in April 2026 produced a model pivot for how Globals are curated and released. The pivot moves the system from real-time-shared Globals with cross-user atomic promotion → admin-curated Globals shipped via discrete releases, with per-user transactional promotion into a `pending_global` buffer.

The pivot's full scope is captured in `docs/PIVOT_V1_SCOPE_2026-04-26.md`. The model itself is described in the release-model design notes. The handoff for the next implementation session is `docs/HANDOFF_SERVER_PIVOT_2026-04-26.md`. **This pivot has since shipped** (Phase 24 and later); the entry is retained for historical context.

Eight ADRs cover the model. All are **Proposed** until both code and a user-facing doc reflect them. Drafting begins with ADR-0118 (highest priority — supersedes ADR-0007).

| ADR # | Title | Status | Supersedes |
|-------|-------|--------|------------|
| 0113 | Mutation model — Resolution A (auto-bump on mutation) | Proposed | — |
| 0114 | Release manifest + version DB schema (SQLite) | Proposed | parts of 0007 |
| 0115 | Audit gate + impact report format | Proposed | 0009; parts of 0007 |
| 0116 | Edge soft-delete model (deprecated/disputed) | Proposed | — |
| 0117 | Compositional metaedge immutability (`CompositionalMetaEdge`) | Proposed | — |
| [0118](adr/0118-per-user-transactional-promotion.md) | Per-user transactional promotion + release-boundary atomicity | Proposed *(drafted 2026-04-26; vertical slice landed 2026-04-27 — 13 tests green)* | 0007 in full |
| 0119 | Composition-signature dedup at promote | Proposed | — |
| 0120 | Cross-layer rewrite handler contract (KL + Capacity in v1) | Proposed | — |

### Cross-layer impact carried by the pivot

Seven cross-layer decisions resolved in PIVOT §6.B, all Proposed status (effect lands when ADRs ship):

- **Capacity rewrite handler in v1** (was v2). Capacity is shipped and uses cross-layer refs; pulling the handler forward avoids known-broken state.
- **`CompositionalMetaEdge` subclass in Core** to enforce composition-as-identity.
- **Ref auto-upgrade contract** stated in `docs/concepts/references.md` — refs by node id; auto-upgrade on Global version bump; note-fork (v2) is the only pinning mechanism.
- **L4 promotion contract note** — pipeline promotion follows the release model when L4 rewrite handler ships in v2. See `mindsos_l4_session_handoff_2026-04-25.md` §11.
- **L3 unified release manifest** — one release ships L2 and L3 promotions atomically. ADR-024 superseded.
- **Default query semantics: `include_deprecated=False`** across L2 / L3 / L4 / L5 reads.
- **L5 memory pinning via note-fork (v2)** — Option A. L5 v1 is sequenced after server-pivot v2. See `layer5_mental_model_design_notes.md` §3.4.

### Reconciliation with shipped server (decided)

Per PIVOT §6, ten reconciliation decisions inform the ADR drafting:

- New `kl.propose_for_promotion()` method; old `kl.promote()` deprecated; remove in v2.
- `GLOBAL_PROMOTE_LOCK` renamed `RELEASE_SHIP_LOCK` and used only at release-ship.
- `MetagraphSnapshot` retained for release-ship rollback only.
- `similarity_report` becomes part of the audit gate; freshness-id mechanism dropped.
- Per-user mutex stays; write-lease deferred to v2 with concurrent-login relaxation.
- Per-ADR supersede; new ADRs cite their supersession.
- Existing promotion tests retained as `@pytest.mark.deprecated_pivot` until new tests cover the same correctness properties.
- L2 critique items §5.6, §5.7, §5.8 bundle with the pivot; §5.1 ships independently.
- `mindsos_server/` → `mindsos_runtime/` rename deferred to a dedicated post-pivot PR.
- No fixed v1 deadline; iterate via PIVOT amendments.

## Perception (open) — ADRs 0191–0194

The current genuinely-open proposals. All carry `status: Proposed`; validated on synthetic substrates, not yet shipped as release code. See [`perception-principles.md`](../concepts/perception-principles.md) for the doctrine (P1–P17).

| ADR # | Title | Status |
|-------|-------|--------|
| [0191](adr/0191-two-axis-perception-confidence.md) | Two-axis perception confidence (grounding + decision) + per-capacity calibration | Proposed |
| [0192](adr/0192-perception-atom-layer.md) | Perception atom layer — geometry/signal realms + the introduce-atom primitive | Proposed |
| [0193](adr/0193-grounding-control-loop.md) | Grounding control loop — irreducibility/request-atom signal + top-down descent trigger | Proposed |
| [0194](adr/0194-recursive-recognizers-and-reuse-promotion.md) | Recursive scale-relative recognizers + reuse-driven promotion | Proposed |

---

**Related:** [About ADRs](about.md) | [Full ADR log](adr/README.md)
