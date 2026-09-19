---
title: Session-based write API replaces bare user_id string
status: Superseded
superseded_by: ADR-0138
date: 2026-04-22
layer: L2
aliases: [kl-ADR-001]
---

# ADR-0038: Session-based write API replaces bare user_id string

**Status:** Superseded by [ADR-0138](0138-kl-drops-write-api.md) (recorded 2026-09-19; see §Supersession below)

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

## Supersession (2026-09-19)

**Amendment status:** Accepted. Records why this ADR is Superseded; the text above is left as written.

[ADR-0138](0138-kl-drops-write-api.md) answers this ADR's question the other way. This ADR puts the capability check at the KL boundary; ADR-0138 (five days later) deletes the KL write API and says "capability checks consolidate at the L3 invocation boundary". Five of the six methods named in §Decision are deleted by ADR-0138 by name; the sixth, `step()`, survives on `MetagraphView` and takes no session.

The mechanism this ADR mandates was never built in this repo: `_coerce_session`, `session: Union[SessionProtocol, str]` and `def add_local_node` appear in this repo's history only in the text of this ADR and ADR-0039 (vendored at `40fd643`), and `session.has(` is absent from `mindsos_knowledge`.

**What survived, relocated.** A session object still crosses into KL — through `KnowledgeLayer.writeable(session, role, scope)` → `KLWriteHandle.session`, per [ADR-0143](0143-kl-write-handle-pattern.md). ADR-0143 keeps this ADR's *routing* guarantee (the principal travels with the write) and not its *capability-check* guarantee. Read this ADR as superseded by ADR-0138 and replaced by ADR-0143 — not as "KL takes a bare `user_id` again", which is false.

The Consequences line "KL must now agree with the server on what capabilities exist — see ADR-0041" is void with it: ADR-0041 is itself Superseded by ADR-0138 (recorded 2026-09-16).
