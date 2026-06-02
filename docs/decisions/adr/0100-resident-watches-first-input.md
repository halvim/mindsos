---
title: Resident granularity restated - watches input DataState of first pipeline node
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q18]
---

# ADR-0100: Resident granularity - watches first pipeline input

**Status:** Accepted

**Date:** 2026-04-21

## Context

(Restatement and confirmation of Q5 with Q18 context.) Each resident watches for the input DataState of the first node of some potential pipeline. If matched, it signals a pipeline candidate. The question is whether this signal-when-first-input-matches rule is the right level of granularity.

## Decision

Yes. Each resident watches for the input DataState of the first node of a potential pipeline and signals a pipeline candidate; L4 decides whether to invest compute. This is the settled rule; restated as Q18 confirmation.

## Consequences

**Good:**
- Residents compose naturally with reactive pipelines at the same scale.
- Signals are synchronous events that L4 can handle predictably.
- No resident state explosion (one resident per first-node-input type).

**Cost:**
- (Same as Q5; no new costs.)

## Alternatives considered

(Same as Q5; none recorded beyond rejection of coarse monitors and predicate-based watchers.)

## Relationship

This confirms and restates ADR-0088 (Q5) without substantive change; included as Q18 because the design plan restated it separately in the final questions section.
