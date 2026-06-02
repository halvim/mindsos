---
title: Server is orthogonal to the domain stack, not Layer 0
status: Accepted
date: 2026-04-27
layer: Cross-layer
amends: [0001]
---

# ADR-0136: Server is orthogonal to the domain stack, not Layer 0

**Status:** Accepted (2026-04-27 — `CLAUDE.md`, `docs/dev/internals/server.md`, `docs/decisions/summary/server.md` all reflect the orthogonal framing)

**Date:** 2026-04-27

**Amends:** ADR-0001 (introduces a dedicated Server Layer above the domain stack — terminology updated; placement clarified).

## Context

Three documents describe the Server Layer's placement, and they disagree:

- `MEMORY.md` (auto-memory) refers to "Layer 0" (above all 5 domain layers).
- `docs/decisions/summary/server.md` and `docs/dev/internals/server.md` refer to "Layer 0.5".
- `CLAUDE.md` (project root) lists Layers 1–5 only and does not mention Server.
- `HANDOFF.md` calls Server "an orthogonal **Server** layer (SHIPPED) that owns auth, sessions, capabilities, audit."

The three framings have different implications:

- **Layer 0 / Layer 0.5** suggests Server is *above* the domain stack — domain layers consume Server's contracts; Server is "in" the stack.
- **Orthogonal** suggests Server is *alongside* the stack — any consumer of the domain layers (UI, CLI, future API gateway, batch jobs) needs the same auth/session/audit machinery; Server isn't part of the stack at all.

The pivot work (`docs/HANDOFF_SERVER_PIVOT_2026-04-26.md`) lands new server-side machinery (release_update, version DB, audit gate, migration job). Without a coherent placement story, future readers will keep re-deriving where Server sits and what it owns.

## Decision

**Server is orthogonal to the domain stack, not Layer 0.**

The five domain layers (L1 Core, L2 Knowledge, L3 Capacity, L4 Intelligence, L5 Mental Model) form the "stack" — each layer consumes the one below and adds new vocabulary. Server is not on this axis. Server provides a runtime envelope (auth, sessions, capabilities, audit, persistence orchestration, lifecycle) that **any consumer** of the domain layers needs. Today there is one consumer — `MindsOSServer`. Future consumers (CLI, web UI, batch import jobs, replication agents) consume Server alongside the domain layers, not on top of them.

```
                   ┌───────────┐
                   │  Server   │  ← orthogonal: provides runtime envelope
                   │  (auth,   │     (auth/sessions/capabilities/audit/
                   │  audit,   │      persistence orchestration/lifecycle)
                   │  ...)     │
                   └─────┬─────┘
                         │ wraps
                         ▼
       ┌─────────────────────────────────────┐
       │  L5 Mental Model                    │
       │  L4 Intelligence                    │  ← the domain stack
       │  L3 Intellectual Capacity           │     (each layer adds new
       │  L2 Knowledge                       │      vocabulary, depends
       │  L1 Core                            │      only on layers below)
       └─────────────────────────────────────┘
```

**What this means concretely:**

1. **No domain layer imports `mindsos_server`.** This rule pre-existed (invariant I-S1, ADR-0010) and stays. The orthogonal framing makes it natural: a runtime envelope is consumed *around* its content, never imported *by* its content.
2. **`mindsos_server` is one consumer of the domain layers.** A future `mindsos_cli`, `mindsos_web`, or `mindsos_batch` is another consumer. All of them depend on Server for auth/session/audit; none of them are "above" any domain layer.
3. **The stack is L1–L5.** When discussing layer ordering, dependencies, layer-rely-on contracts, the answer is the five domain layers. Server is excluded from the count.
4. **The pivot's work doesn't change Server's placement.** ADR-0118, ADR-0114, etc., add capabilities to Server. They don't move Server into the stack.

**Documentation pass required:**

- `CLAUDE.md` — add a paragraph: "Plus an orthogonal Server layer (`mindsos_server`) that owns auth, sessions, capabilities, audit, persistence orchestration. Domain layers do not import Server."
- `MEMORY.md` index — update `project_mindsos_architecture.md` summary line to "5-layer metagraph system on FalkorDB; Server is orthogonal (not Layer 0)."
- Auto-memory file `project_mindsos_architecture.md` — update body to match.
- `docs/concepts/layers.md` — diagram and prose; show Server as orthogonal, not Layer 0.
- `docs/decisions/summary/server.md` — banner line ("Server Layer sits above every domain layer") becomes "Server provides a runtime envelope orthogonal to the domain stack."
- `docs/dev/internals/server.md` — same change in §"Six-layer context" (rename to "Domain stack + Server envelope").
- `HANDOFF.md` — already says "orthogonal"; no change.
- `docs/dev/handoffs/server.md` — currently says "Server Layer sits above every domain layer"; flip to orthogonal phrasing.

No code change. Pure documentation consistency.

## Rationale

The stack-vs-orthogonal framings have different implications for how new code is added:

- If Server is "Layer 0," then a new web UI either lives *above* Server (Layer -1?) or *replaces* Server. Both are confusing.
- If Server is orthogonal, then a new web UI is another consumer alongside `mindsos_server`. It depends on the domain layers and on Server (for auth/sessions/audit). The architecture has room for it without renumbering.

Layer numbering should describe *capability composition*, not deployment topology. L1 → L5 is real composition: L2 builds vocabulary on L1's primitives; L3 builds capacities that operate on L2's metagraphs; L4 orchestrates L3 capacities; L5 is task-scoped instances of L2/L3. Server doesn't compose like this — it doesn't add domain vocabulary. It adds a runtime envelope.

The disagreement across docs reflects the original framing being unclear. The pivot is a good moment to settle it because the pivot adds new server-side machinery; getting the framing right now means the new docs don't perpetuate the drift.

## Consequences

**Good:**

- Single, coherent placement story across all docs.
- Future consumers (CLI, web, batch) have a natural place to plug in.
- `CLAUDE.md` becomes accurate (currently mentions only L1–L5 with no Server; the orthogonal framing fixes the omission).
- Layer numbering stays clean — no "Layer 0" or "Layer 0.5" to explain.

**Tradeoffs:**

- One-time documentation pass across ~7 files. Mechanical.
- Memory needs an update; auto-memory consolidates trivially.
- People who learned "Layer 0" terminology have to relearn. Cheap; the term wasn't widely used outside docs.

**Coordinated changes:**

- ADR-0001 amended in place: its decision text says "introduces a dedicated Server Layer above the domain stack" — this stays as the decision rationale (the layer was introduced as separate from domain), but the placement framing shifts to orthogonal. ADR-0001 status remains Accepted.
- All seven docs listed in §"Documentation pass required" updated.

## Alternatives considered

1. **Keep "Layer 0" terminology consistently across all docs.** Rejected — doesn't fit the architecture's actual shape (Server doesn't compose with the domain layers; it wraps them). Future consumers don't have a natural place under "Layer 0."
2. **Keep "Layer 0.5" consistently.** Rejected — the half-number signals exactly the awkwardness this ADR is fixing. The framing doesn't get less awkward by being applied uniformly.
3. **Drop "layer" terminology for Server entirely; call it `mindsos_server` package only.** Considered. Rejected because the term "Server Layer" appears in many existing docs and changing all of them to "Server package" is heavier than clarifying placement. The orthogonal framing keeps the term while making the placement coherent.
4. **Status quo (drift across docs).** Rejected — the drift is a documentation correctness issue and continues to mislead readers.

## Implementation references

- Documentation update pass: 7 files listed above.
- No code change in `mindsos_server/` or any domain layer.
- ADR-0001 amendment is a Status note, not a Decision-text rewrite.

ADR moves from Proposed to Accepted when the documentation pass completes (no code dependency).
