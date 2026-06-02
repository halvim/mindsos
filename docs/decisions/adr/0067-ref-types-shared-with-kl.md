---
title: REF_TYPES vocabulary shared verbatim with KL
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-008]
---

# ADR-0067: REF_TYPES vocabulary shared verbatim with KL

**Status:** Accepted

**Date:** 2026-04-21

## Context

Both L2 and L3 let Local nodes reference Global nodes. If the two layers use different ref-type vocabularies, cross-layer consumers learn two similar-but-different dialects.

## Decision

`REF_TYPES = {SPECIALISES, INSTANCE_OF, RENAMES, EXTENDS, CONTRADICTS, PROXY}` is the single source. L3 imports it from L2 where feasible, or duplicates the frozenset verbatim with a parity test when layer isolation forbids the import.

## Consequences

**Good:**
- One vocabulary; one mental model.
- Admins see the same ref verbs on L2 and L3 nodes.

**Bad:**
- Extension means editing both layers and the parity test.

## Alternatives considered

Let each layer pick its own verbs — rejected because it's a silent typo firewall waiting to happen.

## §Amendment-1 (2026-05-24, Phase 27)

The original §Decision required L3's REF_TYPES to be shared **verbatim** with L2 — either by import or by duplicated frozenset + parity test.

Reality at Phase 27 ship:

- L2's REF_TYPES has 7 members: `SPECIALISES`, `INSTANCE_OF`, `RENAMES`, `EXTENDS`, `CONTRADICTS`, `PROXY`, **`PROMOTED`**.
- L3 has no promotion lifecycle (no `KnowledgeLayer.promote` analogue at L3); `PROMOTED` is semantically L2-exclusive.

Revised contract: **L3.REF_TYPES ⊆ L2.REF_TYPES**, with the documented exclusion that `PROMOTED` is L2-only. Parity test asserts:

- `L3.REF_TYPES ⊆ L2.REF_TYPES`
- `L2.REF_TYPES - L3.REF_TYPES == {"PROMOTED"}`

Rationale for keeping duplication (not import): L3 stays library-installable without bootstrapping L2's import graph, and ADR-0010 layer-isolation discipline argues for self-contained vocabulary at each layer. ADR-0010 §am1/§am2 does not explicitly forbid `mindsos_capacity → mindsos_knowledge`, but parent precedent and the install-isolation argument both favour duplication.

If L3 later acquires a promotion-like lifecycle, this amendment is superseded by either re-aligning verbatim or adding L3's own verb to the parity-set with a §amendment-2.
