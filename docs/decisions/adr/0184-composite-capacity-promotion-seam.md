---
title: Composite-capacity promotion — two-half target-applier seam (design-only)
status: Deferred
date: 2026-06-23
layer: Cross-layer
amends: []
aliases: [CC-3]
---

# ADR-0184: Composite-capacity promotion seam

**Status:** Deferred (design-only; no writer exists — see §Consequences)

**Date:** 2026-06-23 (core-mod chat — bongard core requests)

## Context

The bongard mint Skill (PLAN §7) provisionally registers a learned composite
capacity **Local** (machine-named, usable immediately), then — at the
Local→Global boundary, admin-gated — **promotes** it into shared knowledge
(step 5 = bongard milestone 5 / Mint step 5 / SA-6). PLAN §7 names this
"existing Server machinery." That assumption is **wrong as written**, and the
real seam is the subject of this ADR.

Grounding (verified this chat):

- **`promoted-pipelines` (Global) has no writer.** Only a docstring + an ALS
  label reference it (`mindsos_capacity/pipeline.py`, `als_subsystems.py`).
  The L2 schema (IRI minters, role-graph bootstrap) is shipped; the *verb* that
  writes a composite into it is not.
- **The propose/release pivot is ATOM-only.** `mindsos_admin.promotion`
  `propose_for_promotion` does `add_node` into a pending-Global *role-graph*;
  `PromotionItemKind.PIPELINE`/`STRUCTURE`/`SUBGRAPH` dispatch raises
  `NotImplementedError` (Phase 24 PB-3a). `mindsos_server.release.release_update`
  flips pending-Global nodes into the released Global version. Neither calls
  `register_capacity` — so a promoted composite node would be **inert**
  (present in the Global graph, not runnable via `invoke`).
- **Skill-install (ADR-0183) is the wrong path.** It installs an *authored
  bundle* (TOML manifest + data, code via normal release); it does not take a
  *runtime-minted Local node* and republish it. A minted composite has no
  bundle. Routing promotion through skill-install is a category error.

## Decision

**Composite-capacity promotion is a two-half "target-applier" seam, not a
single verb.** Build into **core** (no subsystem owns it; §0 of the
COMPOSITION_LIFECYCLE design log) when a real writer lands, behind this seam:

1. **Descriptor half (knowledge).** Read the composite's Local
   `learned-parameters` descriptor (the `COMPOSITE_DAG` value dict, ADR-0185)
   and promote it into Global **`promoted-pipelines`** via the propose/release
   pivot — i.e. implement the `PromotionItemKind.PIPELINE` branch of
   `propose_for_promotion` + the matching `release_update` dispatch. Gated by
   `CAN_PROPOSE_MUTATION` + admin release (the ADR-0118 model, unchanged).
2. **Activation half (capacity).** After release, **re-register** the composite
   in the *Global* CapacityLayer from the promoted descriptor — a Global-scoped
   analog of `reactivate_from_descriptors` (ADR-0185), dep-ordered via
   `composite_dependencies`/`COMPOSITE_DAG`. Without this the released node is
   inert.

**Placement:** descriptor half in `mindsos_admin/promotion.py` +
`mindsos_server/release.py` (the existing pivot); activation half reuses the
pure-L3 `mindsos_capacity/reactivation.py` factory registry, driven from
`mindsos_server` (which may import both layers, per ADR-0185 boundary). **No new
top-level module.** Human placement is at Local→Global only (PLAN §7), never
per-Local-mint.

## Consequences

**Build nothing now (consumer discipline, §0 "no scaffolding without a
consumer").** The writer — bongard m5 (concept-mint) / Mint step 5 / SA-6 — is
unbuilt, and the promoter mechanism is routed to WSD under the
producer-agnostic contract (skill-acquisition design log S10), undesigned. This
ADR fixes the *seam shape and placement* so the eventual writer is a fill-in,
not a redesign, and corrects the PLAN §7 "existing Server machinery" misread.

**Open contract risk:** the descriptor/operand shape interacts with the
deferred COMPOSITION_LIFECYCLE Part 5 (DataState operand-arity). If m5 mints a
composite whose inputs include same-type operands, the promotion descriptor and
the `promoted-pipelines` node shape must carry the operand axis — confirm
against the Part-5 resolution before sizing the build.

## Alternatives considered

- **Single `promote_capacity` verb in a new module** — rejected: duplicates the
  shipped propose/release pivot; ignores that activation is a distinct concern.
- **Route through skill-install (ADR-0183)** — rejected: structural mismatch
  (no bundle for a runtime-minted node).
- **Pivot-only (descriptor half, skip activation)** — rejected: leaves the
  promoted composite inert (never re-registered, not runnable via `invoke`).

## Supersession / amendment trail
- Relates to **ADR-0118** (propose/release pivot — this implements its deferred
  `PIPELINE` kind), **ADR-0185** (reactivation contract — activation half reuses
  it Global-scoped), **ADR-0156** (capacity registration). Does **not** amend
  ADR-0183 (skill install is explicitly out of scope).
