---
title: Server owns bootstrap and admin operations
status: Accepted
date: 2026-04-27
layer: L0
---

# ADR-0140: Server owns bootstrap and admin operations

**Status:** Accepted (shipped; frontmatter reconciled during the 2026-07 doc-vs-code audit)

**Date:** 2026-04-27

**Related:** ADR-0136 (server is orthogonal layer), ADR-0118 (per-user transactional promotion), ADR-0138 (KL drops write API). Implies relocation of `mindsos_knowledge/promotion_v2.py` and importer modules.

## Context

ADR-0138 narrows L2 to data + accessors + validators. Several mutation paths exist today that aren't part of the L4-L3-L1 cognitive loop:

- Knowledge importers: `DolceImporter`, `OewnImporter`, `FrameNetImporter`, `AlignmentsImporter` — bulk ingest into Global at install/upgrade time.
- Pivot promotion path: `propose_for_promotion()` (currently in `mindsos_knowledge/promotion_v2.py`), `release_update()` (currently in `mindsos_server/release.py`).
- `bootstrap()` for KL — first-install admin operation creating Global metagraph + seed roles.

These are administrative operations: they run at known boundaries (install, upgrade, release-ship), with admin-grade capability gates, and are not invoked by L4's cognitive orchestrator. Putting them in L3 as capacities would (a) bloat L3 with operations L4 will never plan against, and (b) break the "L3 capacities are fixed cognitive functions" framing.

## Decision

**`mindsos_server` owns all admin/bootstrap operations.** Specifically:

- Knowledge importers (DOLCE, OEWN, FrameNet, Alignments) relocate to `mindsos_server/importers/` (or equivalent admin module). They use L1 mutation primitives directly + KL validators (per ADR-0139), with admin-only capability gates: `CAN_BOOTSTRAP_GLOBAL`, `CAN_RUN_IMPORTER`.
- `propose_for_promotion()` relocates from `mindsos_knowledge/promotion_v2.py` to `mindsos_server/promotion.py`. Capability gate: existing `CAN_PROPOSE_MUTATION`. Called by an L3 capacity (`capacity:promote:pipeline` per ADR-0145), but the implementation lives at server.
- `release_update()` stays in `mindsos_server/release.py` (already there). Capability gate: `CAN_APPROVE_RELEASE`.
- `bootstrap()` for KL stays as the install-time helper (server orchestrates).

The L4 → L3 → L2 path is reserved for cognitive operations. The `mindsos_server` admin path is a parallel surface with its own capability gates and direct L1 access.

## Rationale

- Importers run at install, not at orchestrator-decision time. They're not "fixed cognitive abilities."
- `propose_for_promotion()` is admin/system tooling — even when called *via* an L3 capacity (the capacity wraps the server function for L4 to plan against), the implementation belongs where the transactional + audit + pending_global routing lives. That's the server.
- Co-locating admin operations in `mindsos_server` keeps the capability landscape coherent (one module per capability category).

## Consequences

**Good:**

- L3 stays focused on cognitive functions; doesn't accumulate admin scaffolding.
- Server is the obvious home for capability checks specific to admin operations.
- Importers + promotion + release operations all share the same module conventions, audit hooks, and capability gating.

**Tradeoffs:**

- Code relocation: ~4 importer modules + `promotion_v2.py` move from `mindsos_knowledge/` to `mindsos_server/`. Tests follow.
- L3's `capacity:promote:pipeline` is a thin wrapper around `mindsos_server.propose_for_promotion()`; the wrapper exists so L4 has a uniform L3 interface for all writes (including admin-mediated ones).
- Importers gain a server-layer dependency; previously they were KL-internal.

## Alternatives considered

1. **Importers as admin L3 capacities.** Rejected — they're not cognitive functions and L4 will never plan against them.
2. **Importers stay in `mindsos_knowledge` as a sub-module.** Rejected — L2 is data + validators; importers mutate, breaking the rule.
3. **Importers + promotion as a separate `mindsos_admin/` package.** Considered. Reasonable on package-isolation grounds, but creates yet another sibling package (joining `mindsos_instances`, possibly `mindsos_contracts`). Held; reopen if `mindsos_server` itself becomes too large.

## Implementation references

- Relocation list:
  - `mindsos_knowledge/importers/dolce.py` → `mindsos_server/importers/dolce.py`
  - `mindsos_knowledge/importers/oewn.py` → `mindsos_server/importers/oewn.py`
  - `mindsos_knowledge/importers/framenet.py` → `mindsos_server/importers/framenet.py`
  - `mindsos_knowledge/importers/alignments.py` → `mindsos_server/importers/alignments.py`
  - `mindsos_knowledge/promotion_v2.py` → `mindsos_server/promotion.py`
- Capability additions: `CAN_BOOTSTRAP_GLOBAL`, `CAN_RUN_IMPORTER` (joining the existing pivot-era set).
- `mindsos_knowledge/__init__.py` keeps re-exports for one release with `DeprecationWarning`.
- ADR moves to Accepted when relocations land + capability constants ship + `docs/usage/server/*.md` documents the admin surface.

## Revisions

### amendment-1 (Phase 15a ship — 2026-05-19) — admin permanent home is `mindsos_admin/`, not `mindsos_server/`; §Decision §1+§2 superseded

**Trigger:** Phase 15a's design pass (PB-1 → PB-1-i → PB-2-i across rounds 1, 2, 4) re-promoted §Alternatives #3 ("Importers + promotion as a separate `mindsos_admin/` package") from "Held" to the chosen end-state. The trigger was **ADR-0043 (Accepted) invariant precedence**: ADR-0043 forbids file-I/O in `mindsos_knowledge/`, but the original §Decision routed file-I/O importers to `mindsos_server/`, which solved ADR-0043 only by routing file-I/O code to a layer hosting session/auth/HTTP envelope — a category mismatch with the project role-description ("Server is not on the layer-composition axis — it provides a runtime envelope").

**Amended behavior:**

* **§Decision §1 superseded.** Importer permanent home is `mindsos_admin/importers/`, not `mindsos_server/importers/`. All 4 importers (DOLCE / OEWN / FrameNet / Alignments) ship at admin. Phase 15a ships the first 3; Phase 15b ships Alignments. No relocation phase needed; Phase 37 row in PHASE_MAP retired.
* **§Decision §2 superseded.** Promotion machinery permanent home is `mindsos_admin/promotion.py`, not `mindsos_server/promotion.py`. Phase 16's `propose_for_promotion()` lands at admin from day one (forward-cited from Phase 15a's PHASE_MAP edit per Phase 15a PB-3-i Round 4).
* **§Decision §3 unchanged.** `release_update()` stays in `mindsos_server/release.py`. Release-ship orchestration requires session + audit + HTTP envelope; that's server territory.
* **§Decision §4 unchanged.** `bootstrap()` for KL stays as the install-time helper. Admin's `bootstrap_global` (Phase 15a) is a parallel orchestration helper for the importer flow per ADR-0042 §amendment-2.

**Rationale partition (role-description-driven):**

| Concern | Home | Reason |
|---|---|---|
| Cognitive write capacities | `mindsos_capacity` (L3) | Cognitive loop owns these |
| Knowledge data + accessors + validators | `mindsos_knowledge` (L2) | ADR-0043 keeps it I/O-free |
| Admin operations (importers, scanner, promotion) | `mindsos_admin` (parallel L2-adjacent) | File-I/O permitted; no session/HTTP machinery required; admin-CLI boundary |
| Runtime envelope (sessions, auth, HTTP, capability gates) | `mindsos_server` (L0) | Per ADR-0136 |
| Release-ship orchestration | `mindsos_server/release.py` | Session + audit + HTTP envelope required |

**Capability gates deferred:** `CAN_BOOTSTRAP_GLOBAL`, `CAN_RUN_IMPORTER`, `CAN_PROPOSE_MUTATION` defer to Phase 18+ when the server's capability framework lands. Phase 15a / 15b admin operations are admin-CLI-boundary-gated only.

**Server may import admin:** When Phase 18+ ships server, an HTTP endpoint handler at `mindsos_server/endpoints/admin_import.py` may import `mindsos_admin.bootstrap_global` and `mindsos_admin.DolceImporter` to expose importers over HTTP. The import direction is server → admin (downward); admin code is not relocated.

**ADR Status remains Proposed.** Phase 15a does NOT flip Accepted. The flip waits for whichever later phase first wires capability gates around admin operations (Phase 18 or beyond).

**Out-of-scope for amendment-1:**

* Server-side HTTP exposure of admin operations (Phase 18+ owns).
* Capability gates themselves (Phase 18+).
* `mindsos_admin/` subpackage layout for promotion / scanner — Phase 15b / Phase 16 land the modules per the conservative day-one layout decision (Phase 15a PB-4-i Round 4): grow into the layout; empty packages are noise.

See `halvim_mindsos/confirmation_docs/PHASE_15a_DESIGN_LOG.md` §PB-1 / §PB-8 / §PB-17 / §PB-18 for the multi-round rationale chain.
