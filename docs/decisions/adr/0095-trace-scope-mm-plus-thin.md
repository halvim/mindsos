---
title: Trace system scope - Mental Model as success trace, thin problem-trace for anomalies
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q13]
---

# ADR-0095: Trace system scope - MM-as-success-trace + thin problem-trace

**Status:** Accepted

**Date:** 2026-04-21

## Context

The system needs to record what happened during execution so it can learn and debug. The question is whether traces are comprehensive (every step recorded) or selective (only failures recorded).

## Decision

**Mental Models as success trace.** Successful execution is recorded by the Mental Model (which is the structured record of what was thought and done). The `capacity:trace` system records only anomalies that MMs cannot capture — crashes, exceptions, unexpected latencies, low-confidence outputs. No full-success trace store. On task completion, the MM (including any problem-trace references) is consolidated into L2's `memories` role-graph.

## Consequences

**Good:**
- Bounded trace storage; only signal-dense records.
- L4 avoids a firehose of per-invocation records.
- Success is documented naturally through the MM; failure detail is supplemented by problem-trace.

**Cost:**
- Must design the MM carefully so it captures all task-scoped reasoning; can't rely on trace as a fallback.

## Alternatives considered

1. **Full-success trace** — rejected (creates a firehose; storage explodes at scale).
2. **No trace at all** — rejected (L4 needs failure post-mortems).
