---
title: Transitional str shim with DeprecationWarning during migration
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-002]
---

# ADR-0039: Transitional str shim with DeprecationWarning during migration

**Status:** Accepted

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
