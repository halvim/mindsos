---
title: L4 Intelligence decisions
tag: design
teaser: Proposed decisions shaping the Intelligence Layer (design-phase).
next: decisions/summary/server.md
---

# L4 Intelligence decisions

Layer 4 is the orchestrator and learner — the part of the system that improves with experience. It is currently in design phase. All decisions listed here are **Proposed** and will lock in as L4 implementation progresses.

!!! warning "Design phase"
    Layer 4 Intelligence is not yet shipped. All ADRs listed here are **Proposed** and are subject to change during implementation.

## Proposed decisions

| ADR # | Title | Summary |
|-------|-------|---------|
| [0101](../adr/0101-l4-per-session-orchestrator.md) | One IntelligenceLayer per live user session | No Global L4; learned state lives in L2; simple tenancy model |
| [0102](../adr/0102-l4-policy-as-meta-pipelines.md) | All decision-point policies composed from L3 capacities as meta-pipelines | Learnable; hard-coded Python doesn't freeze the meta-layer; inspectable |
| [0103](../adr/0103-l4-attention-priority-queue.md) | Orchestrator attention mechanism - priority queue keyed by live attention score | Four priority tiers (CRITICAL, FOREGROUND, BACKGROUND, DREAM); preemption by effective-score within tier |
| [0104](../adr/0104-l4-replan-always-on.md) | Replan trigger - always-on at every step boundary with fast-path | Fresh information always considered; fast-pass for high-confidence cases |
| [0105](../adr/0105-l4-replan-atomicity-discard.md) | Replan atomicity - discard remaining plan; regenerate from current state | Full regeneration on replan; simple logic; new information incorporated into entire remaining plan |
| [0106](../adr/0106-l4-planning-ownership.md) | Planning ownership - L4 orchestrates; planning algorithms are L3 capacities | Planning is a learnable meta-pipeline; algorithms are inspectable L3 nodes |
| [0107](../adr/0107-l4-six-planner-menu.md) | Planner menu - six loadable planning algorithms shipped as separate files | BFS, A*, Dijkstra, CSP, beam search, template-pattern-match; extensible drop-in pattern |
| [0108](../adr/0108-l4-planner-selection-learned.md) | Planner selection is learned per task shape | Chooser has its own promoted-pipelines record; improves via learning loop |
| [0109](../adr/0109-l4-cost-estimators-as-capacities.md) | Cost estimators are L3 capacities, not static node properties | Separate estimators per dimension (latency, tokens, dollars); learnable via observation |
| [0110](../adr/0110-l4-coherence-dream.md) | Coherence dream intent - GAN-like generator vs critic for training stability | Fourth dream intent alongside maintenance, exploration, retry; generator/critic for plan stability |
| [0111](../adr/0111-l4-promotion-dependency-graph.md) | Promotion dependency graph - Local capacities block Global promotion until resolved | Safe-by-default; admin sees dependency graph; two-step promotion when Local steps exist |
| [0112](../adr/0112-l4-pause-and-resume.md) | Pause-and-resume support for voluntary logout | Paused MM as normal memory; resume scans paused tasks on login; forced logout aborts |

---

**Next:** [Server decisions](server.md) — identity, sessions, and promotion orchestration.
