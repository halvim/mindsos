---
title: About Architectural Decision Records
tag: shipped
teaser: What an ADR is, the format MindsOS uses, and how to propose one.
next: decisions/summary/core.md
---

# About Architectural Decision Records

An Architectural Decision Record (ADR) is a lightweight document that captures a significant decision made while designing or shipping a system. It answers the question that every engineer eventually asks: "Why is it like this?" ADRs exist to make those answers findable, debatable, and traceable over time.

MindsOS uses ADRs to document every major design tradeoff across its five layers. An ADR does not attempt to capture every implementation detail — it focuses on the *choice* that was made, the *context* that forced the choice, and the *consequences* that follow. If an ADR is written well, a future engineer can read it and decide whether the original reasoning still holds, or whether circumstances have changed enough to warrant a new decision.

!!! info "Quick facts"
    - Format: Nygard/MADR-style: Context, Decision, Consequences, Alternatives considered
    - Status values: Accepted (locked in, shipped, load-bearing), Proposed (agreed but not yet implemented), Deferred (acknowledged but explicitly not scheduled), Superseded (replaced by another ADR)
    - Location: `docs/decisions/adr/NNNN-short-slug.md` (numbered globally; one layer-agnostic log)
    - Layer metadata: front-matter `layer:` field filters by L1 Core, L2 Knowledge, L3 Capacity, L4 Intelligence, L5 Mental Model, Server, or Cross-layer

## Format

Every ADR follows the same skeleton:

```yaml
---
title: Short title in title case
status: Accepted | Proposed | Deferred | Superseded
date: YYYY-MM-DD
layer: L1 | L2 | L3 | L4 | L5 | Server | Cross-layer
aliases: [optional-old-id, like-core-ADR-003]
supersedes: [optional-adr-number-if-replacing-an-old-one]
---
```

Followed by prose sections:

**Status.** The lifecycle of the decision: Accepted (shipped and load-bearing), Proposed (consensus reached but not yet coded), Deferred (acknowledged, known tradeoff, not scheduled), or Superseded (replaced by a later ADR).

**Context.** The situation or problem that made this decision necessary. What was the pressure? What constraint was discovered? Why couldn't we ignore this?

**Decision.** What was chosen. Stated as a declaration, not a negotiation: "We will [do X]" or "Layer Y owns [concern Z]." Brief and actionable.

**Consequences.** What follows from the decision, sorted into good and bad. Use (+) and (−) prefixes to distinguish. Does it unblock other layers? Does it carry ongoing cost? Are there future revisits implied?

**Alternatives considered.** What else was on the table and why it lost. Helps future readers understand what was evaluated. Also the place to note if a rejected alternative is "permanently closed" vs. "deferred — revisit if [circumstance X]."

See `/docs/decisions/adr/0001-dedicated-server-layer.md` for a worked example.

## How to propose an ADR

When you're designing a feature and you reach a point where you say "okay, we could do this three ways, each with tradeoffs," that's an ADR waiting to happen.

1. **Open a chat or a discussion.** Describe the decision, the context, and the options. Get alignment on the choice.
2. **Write a draft ADR.** Follow the template above. Aim for one page. One page forces you to be precise.
3. **Link it into the project plan.** If the ADR unlocks work for other layers, flag that in the Consequences. If it supersedes a Proposed ADR or defers a concern, note that too.
4. **Land the ADR and the code together.** An ADR without code, or code without an ADR, is half-baked. They move in the same PR.

## ADR numbering and lifecycle

- ADRs are numbered globally in `/docs/decisions/adr/` starting from 0001. Numbers are never reused.
- Status starts at **Proposed** when the decision is made, but before the code lands.
- Status moves to **Accepted** when the decision lands in *code* *and* *at least one user-facing document* (the handoff, the architecture doc, or a usage guide).
- Status becomes **Superseded** if a later ADR replaces it. The old ADR keeps its number but gains a "Superseded-by: ADR-NNNN" line. Do not rewrite it.
- **Deferred** is for decisions that are acknowledged but explicitly not scheduled. Use it when you decide "we could do X, we won't, but here's why" — it marks the issue as resolved, not open.

## Per-layer summary pages

Each layer has a summary page that indexes all the ADRs affecting it:

- [L1 Core decisions](summary/core.md) — the primitives every other layer depends on
- [L2 Knowledge decisions](summary/knowledge.md) — the long-term memory and versioning contract
- [L3 Capacity decisions](summary/capacity.md) — fixed abilities and discovery
- [L4 / L5 Intelligence decisions](summary/intelligence.md) — learning, orchestration, and the Mental Model (shipped, Phases 46–48)
- [Server decisions](summary/server.md) — identity, session, audit, promotion
- [Cross-layer decisions](summary/cross-layer.md) — boundaries, isolation, handoffs

These pages are filtered views of the full numbered log. Start with the summary page for your layer to get oriented; link through to the full ADR for details.

## When to write an ADR vs. inline documentation

Write an ADR when:

- The decision is **load-bearing** — it shapes the contract between layers or the behaviour of the system.
- The decision involves **tradeoffs** — you could have chosen differently, each way has good and bad.
- The decision is **non-obvious** — someone reading the code six months from now will ask "why?"
- The decision might **change** — future engineers should know it was deliberate, not an accident.

Don't write an ADR for:

- Implementation details that don't affect the contract (e.g., "we use a dict instead of a list for O(1) lookup").
- Bugs that were fixed (those go in the changelog or a commit message).
- Features that are obviously the right choice in context (e.g., "we use Python" in a Python project).

## Related resources

- **Full ADR log:** [Decisions / Full ADR log](adr/README.md)
- **Proposed / deferred questions:** [Decisions / Proposed](proposed.md)
- **Superseded ADRs:** [Decisions / Superseded](superseded.md)
- **Layer handoffs:** `docs/dev/handoffs/<layer>.md` — the public API contract each layer promises

---

**Next:** [L1 Core decisions](summary/core.md) — decisions about the data primitives.
