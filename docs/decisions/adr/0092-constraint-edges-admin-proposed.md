---
title: Constraint edges are admin-authored; L4 may propose
status: Accepted
date: 2026-04-21
layer: L3
aliases: [L3-Q9]
---

# ADR-0092: Constraint edges - admin-authored, L4-proposed

**Status:** Accepted

**Date:** 2026-04-21

## Context

Constraints (mutual exclusion, ordering, rate limits, approval gates, version requirements) direct how capacities may be combined. The question is who can create them: admins only, or also L4 on observing failures?

## Decision

Constraint edges are authored by admins. L4 may observe failures and *propose* new constraints, but admins must approve them before they take effect. This keeps the constraint graph inspectable and auditable, matching the declarative posture of the capacity metagraph.

## Consequences

**Good:**
- Constraints are explicit, discoverable, and versioned with the system.
- Admin approval gates learning signals from cascading into the capacity graph uncontrolled.

**Cost:**
- L4 must learn to work within an initially sparse constraint graph; constraints don't auto-emerge from observation.

## Alternatives considered

1. **L4 can write constraints directly** — rejected (loses auditability; admins can't see what L4 has imposed).
2. **Constraints are hard-coded in L4** — rejected (not inspectable; couples L4 implementation to constraint semantics).
