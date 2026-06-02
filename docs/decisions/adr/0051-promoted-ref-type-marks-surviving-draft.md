---
title: PROMOTED ref_type marks the surviving Local draft
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-014]
---

# ADR-0051: PROMOTED ref_type marks the surviving Local draft

**Status:** Accepted

**Date:** 2026-04-22

## Context

After a draft is promoted to Global, what happens to the Local node? Two options: (a) delete it; (b) keep it, rewritten to reference the new Global node.

## Decision

Option (b). The Local draft stays in place, with `ref:global_<role>` set to the new Global IRI and `ref_type = "PROMOTED"`. Edges from the draft to other Locals stay; edges to other Globals stay.

## Consequences

**Good:**
- The draft becomes a breadcrumb: "this is the idea I authored, and here's what it graduated into."
- The rewrite is reversible — promotion's atomic undo-stack restores values.

**Bad:**
- Local metagraphs grow over time; pruning promoted drafts is a future operation.

## Alternatives considered

Delete the Local draft after promotion — rejected because it loses audit and authoring history.
