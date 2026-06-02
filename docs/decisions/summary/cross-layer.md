---
title: Cross-layer decisions
tag: shipped
teaser: Decisions about layer boundaries, data flow, and handoffs.
---

# Cross-layer decisions

These decisions define how layers interact, what data flows where, and how the layer boundaries are enforced. They cut across the stack and must be satisfied by all layers.

| ADR # | Title | Status | Summary |
|-------|-------|--------|---------|
| [0010](../adr/0010-layer-isolation.md) | KL does not import the server (I-S1); L3 accepts `SessionProtocol` | Accepted | Hard layer boundaries; domain layers never depend upward |
| [0014](../adr/0014-layer-boundary-core-only.md) | Layer boundary — Core owns primitives only | Accepted | Core performs no reasoning, validation, or concurrency control |
| [0087](../adr/0087-richness-annotation-implicit.md) | Upper-layer roles in L2: ontology, lexicon, concepts, memories | Accepted | KL metagraph partitioned by role; each role versioned independently |
| [0136](../adr/0136-server-as-orthogonal-layer.md) | Server is orthogonal to the domain stack, not Layer 0 | Accepted | Documentation-consistency pass; Server provides runtime envelope, not layer composition |

---

**Related:** [About ADRs](../about.md) | [Full ADR log](../adr/README.md)
