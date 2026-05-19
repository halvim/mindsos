---
last_confirmed_phase: 14a
---

# Local↔Global promotion bridge (L2)

> **Maturity banner.** This page synthesises a path whose mechanics are
> defined by ADRs that are mostly still **Proposed**:
> [ADR-0118](../decisions/adr/0118-per-user-transactional-promotion.md)
> (per-user transactional promotion),
> [ADR-0138](../decisions/adr/0138-kl-drops-write-api.md) (KL drops
> write API),
> [ADR-0140](../decisions/adr/0140-server-owns-admin-operations.md)
> (server owns admin),
> [ADR-0141](../decisions/adr/0141-delete-shipped-promote.md) (delete
> shipped `promote()`),
> [ADR-0144](../decisions/adr/0144-similarity-at-release-ship-audit-gate.md)
> (similarity at audit gate). This page amends (`last_confirmed_phase`
> flip) as each ADR flips Accepted in its consumer phase. **This page
> is not a binding spec; the ADRs are.**

This page describes how user-Local content reaches the canonical
Global. It's the bridge between
[user-local-authoring.md](user-local-authoring.md) (which writes Local)
and [admin-global-shipping.md](admin-global-shipping.md) (which describes
admin-curated Global content). The two write-paths are otherwise
parallel; promotion is the only crossing.

## What crosses

Local-originated content that becomes shared system-wide:

- `concepts` drafts — user-drafted concept additions.
- `lexicon` drafts — user-drafted entries.
- `alignment:<role-a>:<role-b>` drafts — user-drafted alignments.
- `promoted-pipelines` proposals — L4-distilled pipelines (originating
  in user Mental Models, distilled across many users' memories).
- `task-patterns` proposals — L4-distilled task templates.

**Does NOT cross:**

- `memories` per
  [ADR-0044](../decisions/adr/0044-memories-move-to-local-per-user.md)
  (Accepted). Autobiographical records stay in the originating user's
  Local until account deletion. Cross-user pattern learning happens by
  L4 distilling many users' memories into a Pipeline / Pattern proposal
  — the memory itself never moves.
- `capacity-state`. Per-user resident state; no shared semantics.

## The three atomicity boundaries (per ADR-0118)

The original cross-user atomic promotion model (ADR-0006 / ADR-0007)
was superseded by
[ADR-0118](../decisions/adr/0118-per-user-transactional-promotion.md).
The pivot replaces one shared scope with three independent ones:

### 1. Per-user `propose_for_promotion` (admin-initiated)

- One user's Local + one set of pending-Global writes.
- One SQLite transaction (over `pending_mutations` + audit rows) +
  bounded FalkorDB writes to one user's Local and one pending graph.
- **No global lock.**
- Source user's draft is `DRAFT_FROZEN`; on rejection, `DRAFT_UNFROZEN`.

### 2. Release-boundary `release_update` (admin-rare)

- `RELEASE_SHIP_LOCK` acquired (renamed from `GLOBAL_PROMOTE_LOCK`).
- Release-level audit gate runs — **similarity findings surface here**
  per
  [ADR-0144](../decisions/adr/0144-similarity-at-release-ship-audit-gate.md).
- For each role with pending content: atomic copy
  `mindsos_pending_global_<role>` → `mindsos_global_<role>`, then clear
  pending. Backed by FalkorDB per-graph atomicity.
- `releases` row inserted with `manifest_json` snapshot.
- `MetagraphSnapshot` of the affected canonical Global graph taken
  before the copy; restores canonical on partial failure (ADR-0027
  retained narrowly for this purpose).

### 3. Per-user lazy migration (per-user pace)

- Each user's session-start path checks `last_synced_release_id <
  current_release_id` and applies the rewrite map of every release in
  between.
- For a user whose draft was promoted: frozen draft deletes from their
  Local; refs rewrite to canonical id.
- Idempotent + atomic per user.
- Failures contain to one user (no multi-Local rollback).

## Phase contributions

| Phase | What lands                                                                                                       |
|-------|------------------------------------------------------------------------------------------------------------------|
| 16    | Pre-pivot promotion machinery: list candidates, baseline similarity heuristic, atomic per-candidate rollback. Pure L2; no auth gate (server adds it in Phase 23). |
| 23    | Promotion lock + MetagraphSnapshot rollback (`GLOBAL_PROMOTE_LOCK`, retained narrowly post-ADR-0118 as `RELEASE_SHIP_LOCK`). |
| 24    | Full ADR-0118 impl: per-user transactional `propose_for_promotion`, `release_update`, release manifest in `version_db/`, lazy migration. **NEW CODE** per PHASE_MAP. |

The relationship between Phase 16 and Phase 24 is incremental — Phase
16 ships the pre-pivot baseline; Phase 24 lands the pivot. The
pre-pivot `promote()` deletes per
[ADR-0141](../decisions/adr/0141-delete-shipped-promote.md) (Proposed)
before Phase 24 ships the replacement.

## Similarity at the audit gate (per ADR-0144)

Similarity is **not** a pre-flight advisory at `propose_for_promotion`
time. It runs **once**, at `release_update`, against the full pending
batch.

Three weighted scorers per
[ADR-0144](../decisions/adr/0144-similarity-at-release-ship-audit-gate.md):

- **Levenshtein** on canonical names (target IRI tail) — 0.0 to 1.0.
- **Structural overlap** — Jaccard on the candidate's frame-element +
  synonym + parent-class sets against an existing Global node.
- **Reference Jaccard** — Jaccard on outbound `ref:<role>` + `XRef`
  targets.

Default weights: 0.4 / 0.4 / 0.2. Threshold 0.85 for blocking finding;
0.5–0.85 surfaced as "review." Admin decides per-candidate (accept /
drop / merge / defer).

The shipped prefix-match heuristic deletes per ADR-0144 §Module layout.

## Capabilities required

- `CAN_PROPOSE_MUTATION` (per-user; entry to the bridge).
- `CAN_APPROVE_RELEASE` (admin; gate at `release_update`).
- `CAN_PROMOTE_PROPOSAL` (admin; per-candidate accept/drop at audit
  gate — naming TBD in Phase 24).

Per ADR-0118 §Decision + ADR-0144 §Decision (both Proposed).

## Boundary vs sibling docs

Per Phase 14a round-3 PB-M1:

- **This page** owns bridge mechanics (propose → pending → audit-gate →
  ship → migrate).
- **`docs/concepts/release-model.md`** (Phase 24's deliverable;
  forthcoming) owns per-user release semantics
  (`last_synced_release_id`, lazy migration logic, version-graph
  routing post-ship).
- **[admin-global-shipping.md](admin-global-shipping.md)** owns
  importer-side Global content origin (Phase 15 / 37) — disjoint from
  this bridge.

## References

Accepted:

- [ADR-0044](../decisions/adr/0044-memories-move-to-local-per-user.md)
  — memories Local-per-user (locks "memories don't cross").
- [ADR-0150](../decisions/adr/0150-l2-knowledge-lifecycle.md) — closed
  role-set (defines the bridge's finite source-and-target table).

Proposed (this page amends as they ship):

- [ADR-0118](../decisions/adr/0118-per-user-transactional-promotion.md)
  — per-user transactional promotion (the bridge's atomicity model).
- [ADR-0138](../decisions/adr/0138-kl-drops-write-api.md) — KL drops
  write API.
- [ADR-0140](../decisions/adr/0140-server-owns-admin-operations.md) —
  server owns admin (promotion implementation lives in
  `mindsos_server`).
- [ADR-0141](../decisions/adr/0141-delete-shipped-promote.md) — delete
  shipped `promote()`.
- [ADR-0144](../decisions/adr/0144-similarity-at-release-ship-audit-gate.md)
  — similarity at audit gate.
