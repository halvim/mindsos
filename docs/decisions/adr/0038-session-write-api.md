---
title: Session-based write API replaces bare user_id string
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-001]
---

# ADR-0038: Session-based write API replaces bare user_id string

**Status:** Accepted

**Date:** 2026-04-22

## Context

Pre-seam KL took `user_id: str` as the first positional argument on every write method. A bare string carries no capability information, so any caller — including buggy server code — could write into any user's Local without being stopped at the KL boundary. When the server layer design solidified, the asymmetry became untenable: the server already knows who the principal is and what they can do; passing only `user_id` would throw that away at the layer boundary.

## Decision

The KL write API accepts `session: Union[SessionProtocol, str]` as its first positional argument. Inside each method the first line is `session = _coerce_session(session)`; subsequent code uses `session.user_id` for Local lookups and `session.has(...)` for capability assertions. This applies to `add_local_node`, `add_local_edge`, `add_local_alignment`, `step`, `similarity_report`, and `promote`. Methods that do not take a principal (`install_local_metagraph`, `extract_local_metagraph`, etc.) keep their existing signatures — the server enforces capability at its own boundary before calling them.

## Consequences

**Good:**
- Defence-in-depth: a server bug that hands KL the wrong session is caught at the KL boundary.
- The same signature works in tests, integration, and production — the Session is just constructed differently.

**Bad:**
- Every write-API caller in tests and in L3 had to migrate.
- KL must now agree with the server on what capabilities exist — see ADR-0041.

## Alternatives considered

None recorded; this was the consensus choice during the 2026-04-22 design session.
