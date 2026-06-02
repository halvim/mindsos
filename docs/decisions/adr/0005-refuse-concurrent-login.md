# ADR-0005: Refuse concurrent login; provide kill-session escape valves

- **Status:** Accepted
- **Date:** 2026-04-22
- **Related:** ADR-0002, ADR-0008

## Context

A user's Local Metagraph is a mutable in-memory object. Two concurrent sessions for the same `user_id` would race on it, and the race is not one we want to litigate in KL (which would have to grow either per-Local locking or copy-on-write semantics). Meanwhile, there are legitimate reasons someone might want a second session — an abandoned terminal, a different machine — and we need a way to recover without admin intervention.

## Decision

**Refuse concurrent login.** At `login()`, if an active (non-expired) session already exists for the `user_id`, raise `AlreadyLoggedInError` (HTTP 409) whose payload carries the existing session's id, `created_at`, and `source`.

Provide two escape valves:

1. **Self-evict.** `kill_my_own_sessions(credentials)` takes fresh credentials (not a token — the caller by definition doesn't have a valid one) and deletes every session row for that `user_id`. The caller then retries `login()`.
2. **Admin override.** `admin_kill_session(admin_session, target_session_id)` requires `CAN_KILL_SESSION` and deletes a single session by id.

Sessions **die on server restart** regardless — the `sessions` table is truncated at startup because in-memory Local state from FalkorDB hydration is gone (see ADR-0004).

## Rationale

- **Simpler KL.** Single-writer-per-Local is a structural invariant the domain layer can rely on. No per-Local locks, no CRDTs.
- **Explicit recovery, not silent eviction.** Silently killing an older session on login is a footgun — a user with a running import job would lose it with no warning. A 409 with a pointer to the blocker lets the caller choose.
- **Credential-backed self-evict.** Using fresh credentials (not a token) for `kill_my_own_sessions` means even if your current token is lost, you can recover without admin.
- **Admin kill for lock-out.** If a user's session is wedged and they can't reach their own credentials, `CAN_KILL_SESSION` gives admin a surgical tool without touching their account.
- **Restart wipes sessions.** Any graph that was mid-edit is gone from FalkorDB's in-memory view; pretending the session is still valid would be worse than forcing a relogin.

## Consequences

- `AlreadyLoggedInError` is part of the stable API; clients must handle 409 with the three-field payload.
- Audit event `LOGIN_REJECTED_CONCURRENT` fires so admins can spot suspicious patterns.
- Automated agents (CI, upper-layer daemons) must each get their own `user_id` rather than share.
- `session_from_token` after a restart returns 401 for every token issued before the restart; clients learn to re-login.

## Alternatives considered

1. **Silent kill of older session.** Rejected — destroys in-flight work without consent.
2. **Allow N concurrent sessions per user with per-Local locking.** Rejected — forces KL to grow mutex infrastructure we don't need elsewhere, and the user-visible coordination problem (merging two concurrent edits) isn't solved by locks.
3. **Persist sessions across restart.** Rejected — the Local they point at isn't persistent in FalkorDB at the right granularity; we would be validating tokens against state that no longer exists.

## Revisions

### amendment-1 (Phase 19 ship — 2026-05-21) — two-change batch: scope "sessions die on server restart" to future daemon; drop `source` field; lock lazy-expire-then-concurrent-check ordering

**Trigger:** Phase 19 ships login + refuse-concurrent-login per this ADR. Round-1 design review surfaced two §Decision clauses that don't fit the CLI-only product as it ships, plus an edge case in §Decision's ordering that needed an explicit lock:

1. **"Sessions die on server restart" doesn't apply to CLI-only.** §Decision says "Sessions die on server restart regardless — the `sessions` table is truncated at startup because in-memory Local state from FalkorDB hydration is gone (see ADR-0004)." There is no daemon, no startup event, no in-memory Local that survives between CLI invocations. The premise (in-flight Locals lost) doesn't fire. ADR-0004 §amendment-1 carries the parallel scope change.
2. **`source` field on `AlreadyLoggedInError` payload has no meaning in single-host CLI.** §Decision locks the payload to `{existing_session_id, created_at, source}`. "Source" is intended to distinguish "an abandoned terminal" from "a different machine" — but a CLI invocation has no remote IP, no client app, no machine differentiator. Hardcoding `source="cli"` ships a stub field with no informational value.
3. **Edge case unspecified:** existing session is 9 hours stale (sliding TTL = 8h). New `login()` arrives. If the concurrent-login check fires before lazy expiry runs, it raises `AlreadyLoggedInError` against a dead session and locks the caller out for no reason. §Decision is silent on ordering.

**Amended behavior:**

* **CLI sessions persist across invocations** (mirrors ADR-0004 §am1). The "die on restart" §Decision clause is scoped to apply only when a long-lived server process exists; the future HTTP-daemon phase amends it back into force.
* **`AlreadyLoggedInError` payload is 2-field at Phase 19:** `{existing_session_id, created_at}`. `source` field is deferred to the HTTP-daemon phase where remote-IP / client-app distinctions become meaningful. The §Decision payload-shape clause updates accordingly.
* **§Consequences ordering lock (PB-8):** `login()` MUST lazy-expire-then-concurrent-check-then-mint. Specifically: at login, first DELETE any session row for the user_id whose `min(created_at+24h, last_seen_at+8h)` is in the past; THEN check for any remaining session row; if found, raise `AlreadyLoggedInError`; else mint new. This closes the 9-hour-stale edge case.

**Rationale:** Same as ADR-0004 §am1 — match the product as it actually ships. The ordering lock costs zero (a DELETE-where + SELECT-where pair) and prevents a real foot-gun.

**Out-of-scope:** Wipe-on-restart re-activates at HTTP daemon ship. `source` field re-activates at HTTP daemon ship.

See `halvim_mindsos/confirmation_docs/PHASE_19_DESIGN_LOG.md` §1 round 1 PB-1 + PB-3 + PB-8 for the rationale chain.
