---
last_confirmed_phase: 14a
---

# Knowledge addition lifecycle (L2)

L2's role-set is closed at 9 entries (8 named + 1 parametric alignment
template) per
[ADR-0150](../decisions/adr/0150-l2-knowledge-lifecycle.md). Given that
closure, "how does knowledge get into L2" is a finite enumeration of
entry points. This page is the index. Sibling pages own the per-path
mechanics.

## The five stages

| Stage      | What happens                                                          | Owned by                                                                                |
|------------|-----------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| Bootstrap  | Create Global + Local metagraphs; ensure role-graphs via `ensure_role_graph` | Phase 14 — `docs/concepts/global-local.md` (forthcoming)                                |
| Authoring  | User-Local writes via L3 capacities                                    | [user-local-authoring.md](user-local-authoring.md)                                      |
| Shipping   | Admin-Global writes via importers (install / upgrade / pinned release) | [admin-global-shipping.md](admin-global-shipping.md)                                    |
| Promotion  | Local draft → pending_global → canonical Global (release-ship)        | [promotion-bridge.md](promotion-bridge.md)                                              |
| Versioning | Side-by-side role-graphs + active-version routing + PROMOTED breadcrumbs | Phase 17 — `docs/usage/knowledge/versioning.md` (forthcoming)                           |

Bootstrap and versioning are described in their owning phase's docs
(forward-cited above; Phase 14a does not write them). Phase 14a tracks
the other three.

## Per-phase mapping

The table below traces each phase that touches the lifecycle. Each
consumer phase amends its own row (flipping Status: `planned → shipped`)
in its own PR per Phase 14a round-3 PB-K3.

| Phase | Layer | Stage(s)                | Role contribution                                                                                                  | Status   |
|-------|-------|-------------------------|--------------------------------------------------------------------------------------------------------------------|----------|
| 14    | L2    | Bootstrap, Versioning   | `KnowledgeLayer` class; Global + Local metagraph bootstrap; `ensure_role_graph` idempotent; `MetagraphView` read-only; per-edge alignment-anchor IRI builder (Phase 12 PB-4 carry); MetagraphSchema scanner (Phase 11 PB-7 C carry) | planned  |
| 15    | L2    | Shipping                | 4 importers (DOLCE → `ontology`, OEWN → `lexicon`, FrameNet → `concepts`, Alignments → `alignment:<a>:<b>`); seed Global content | planned  |
| 16    | L2    | Promotion               | Pre-pivot promotion machinery: list candidates, baseline similarity, atomic per-candidate rollback                | planned  |
| 17    | L2    | Versioning              | Active-version queries; PROMOTED breadcrumb routing in views                                                       | planned  |
| 23    | L0    | Promotion               | Promotion lock + MetagraphSnapshot rollback (pre-pivot orchestration; ADR-0006/0007/0027 narrow scope)             | planned  |
| 24    | L0    | Promotion               | Full ADR-0118: per-user transactional `propose_for_promotion` + `RELEASE_SHIP_LOCK` + release manifest in `version_db/` + lazy migration | planned  |
| 25    | cross | Authoring (precursor)   | `SessionProtocol` seam in L2 + hydrate/extract hooks (the seam L3 capacities use to reach L2)                      | planned  |
| 33    | L3    | Authoring               | 5 L3 write-capacity categories per ADR-0145 (`consolidate` / `trace` / `promote` / `author` / `state`)             | planned  |
| 34    | L3    | Authoring               | Symmetric write contract per ADR-0146 (`WriteResult \| ProblemTraceRecord` return)                                  | planned  |
| 35    | L3    | Authoring               | Per-flow build pattern per ADR-0147 (`KLWriteHandle.graph()` + per-flow validators)                                | planned  |
| 36    | L2    | Authoring (precondition) | Hybrid validators home per ADR-0139 (semantic-side; structural-side already at L1)                                | planned  |
| 37    | L0+L2 | Shipping                | Server-owns-importers per ADR-0140 (importer relocation from `mindsos_knowledge/` to `mindsos_server/`)            | planned  |

Phase 14a flips no rows to `shipped` — it's design-only.

## What's NOT in the lifecycle

These do not appear above by design:

- **Per-tenant custom roles.** The role-set is closed
  ([ADR-0150](../decisions/adr/0150-l2-knowledge-lifecycle.md)).
  Per-tenant variation lives inside existing roles (namespaced under
  `concepts` or scoped per-user under `memories`), not as new top-level
  roles.
- **Memory → Global migration.** `memories` is Local-per-user per
  [ADR-0044](../decisions/adr/0044-memories-move-to-local-per-user.md).
  Cross-user pattern learning happens by L4 distilling many users'
  memories into a Pipeline / Pattern proposal — the memory itself never
  moves.
- **Direct user writes to Global.** The cognitive loop is
  L4-orchestrator → L3-capacity → L1-mutation (via `KLWriteHandle`).
  Admins reach Global via importers (Phase 15 / 37) or release-ship
  (Phase 24); users never write Global directly.

## Read this before adding a row

If you find yourself wanting to add a new role, see
[ADR-0150](../decisions/adr/0150-l2-knowledge-lifecycle.md) — runtime
addition is rejected; expansion requires ADR amendment + schema builder
+ dispatch table entry + tests + per-role IRI builder.

If you find a stage that doesn't fit any of the five above, surface it
as a Phase chat pushback before writing new docs. The five-stage
taxonomy is the synthesis Phase 14a locked.

## Source

Phase 14a design pass (rounds 1-3); cites
[ADR-0150](../decisions/adr/0150-l2-knowledge-lifecycle.md) (Accepted),
ADR-0044 (Accepted), ADR-0149 (Accepted), and ADR-0118 / 0138 / 0139 /
0140 / 0143 / 0144 / 0145 / 0146 / 0147 (all currently Proposed). The
synthesis amends as the Proposed ADRs flip Accepted in their consumer
phases.
