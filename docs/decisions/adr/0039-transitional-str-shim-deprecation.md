---
title: Transitional str shim with DeprecationWarning during migration
status: Superseded
superseded_by: ADR-0138
date: 2026-04-22
layer: L2
aliases: [kl-ADR-002]
---

# ADR-0039: Transitional str shim with DeprecationWarning during migration

**Status:** Superseded by [ADR-0138](0138-kl-drops-write-api.md) (recorded 2026-09-19; see §Supersession below)

**Date:** 2026-04-22

## Context

Landing ADR-0038 meant rewriting every KL write-API call in the repo in lockstep. Doing that in one atomic PR would have coupled the KL refactor to the server's Phase-1 delivery. A migration window — KL lands first, callers migrate, server Phase 1 lands, shim disappears — was the path of least risk.

## Decision

Each write-API method accepts `session: Union[SessionProtocol, str]`. The `str` path emits `DeprecationWarning`, then tries to import `mindsos_server.session.Session.for_testing`; if that fails, it falls back to a KL-internal `_LocalTestSession` dataclass that satisfies `SessionProtocol` structurally. The `_coerce_session(session)` helper centralises this logic.

## Consequences

**Good:**
- Existing tests keep passing during the migration window.
- Environments without the server package stay green.

**Bad:**
- The test suite now emits ~22 `DeprecationWarning`s until the codemod runs.
- Two session code paths coexist until the shim is removed.

## Alternatives considered

None recorded; this was the consensus choice during the 2026-04-22 design session.

## Supersession (2026-09-19)

**Amendment status:** Accepted. Records why this ADR is Superseded; the text above is left as written.

This ADR's whole subject is the `str` path of [ADR-0038](0038-session-write-api.md)'s signature. ADR-0038 is Superseded by [ADR-0138](0138-kl-drops-write-api.md), which deleted the write API that signature belonged to, so the migration window this ADR governs has nothing left to migrate.

The shim was never built in this repo: `_coerce_session` appears in this repo's history only in the text of this ADR and ADR-0038 (vendored at `40fd643`), and `mindsos_capacity/types.py` records the parent's shim as unported dead code. The name `_LocalTestSession` survives only as an unrelated L3 test fixture (`tests/phase_30/_fixtures.py`) — a SessionProtocol stub, not this ADR's `str` fallback.
