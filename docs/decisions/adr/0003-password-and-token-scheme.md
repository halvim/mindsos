# ADR-0003: argon2id password hashing + 256-bit opaque session tokens with sliding + absolute TTL

- **Status:** Accepted
- **Date:** 2026-04-22
- **Related:** ADR-0004

## Context

The server holds human credentials and issues tokens that grant access to the user's Local Metagraph (potentially the full record of their domain-authoring work). Both the at-rest password representation and the in-flight token format need to be conservative enough to survive an attacker who gets read-only access to `server.db` or who intercepts a token.

## Decision

**Password storage:**

- Hash with **argon2id** (memory-hard, side-channel-resistant), default parameters from `argon2-cffi` (time_cost=3, memory_cost=65536 KiB, parallelism=4).
- Stored as the standard `$argon2id$...` encoded hash in `users.password_hash`.
- Password changes rehash with a fresh salt and revoke all existing sessions for that user.

**Session tokens:**

- 256 bits from `secrets.token_urlsafe(32)` — opaque, unpredictable, URL-safe.
- Stored as **SHA-256 digest** in `sessions.token_hash`; the plaintext token is never persisted server-side after issue.
- Lookup does a constant-time comparison against the stored hash.

**Token lifetime:**

- **Sliding TTL = 8 hours.** Every successful `session_from_token` bumps `last_seen_at`; a session is considered valid as long as `now - last_seen_at < 8h`.
- **Absolute TTL = 24 hours.** Measured from `created_at`. A session cannot be extended past this ceiling regardless of activity.
- Expiry is checked lazily on lookup (raises `SessionExpiredError` → HTTP 401) and reaped lazily by a background `sweeper` thread.

## Rationale

- **argon2id over bcrypt/scrypt/PBKDF2.** OWASP 2021+ recommends argon2id as the default; memory-hardness shuts down GPU/ASIC cracking.
- **Opaque tokens over JWTs.** JWTs would push revocation into denylists and force key rotation. Opaque tokens with server-side state are simpler, shorter, and revocable by `DELETE FROM sessions WHERE ...`.
- **Storing only the hash.** If `server.db` leaks, the attacker gets neither passwords (argon2id) nor replayable tokens (SHA-256 of 256 random bits is infeasible to pre-image).
- **Sliding + absolute.** Sliding prevents surprise timeouts during active work; absolute caps the blast radius of a stolen token. Both together match the threat model of an interactive local tool that may sit idle or may run long jobs.

## Consequences

- Logout and `admin_kill_session` are cheap (single DELETE).
- Password change forces re-login for every active session; this is the intended UX.
- `argon2-cffi` is a runtime dependency; the developer guide calls it out.
- The 24h cap means long-running promotion or import jobs that straddle the boundary must be re-authenticated; operationally, this is preferable to an unbounded token.
- Clock skew between sweeper and request handlers is tolerated — expiry is monotonic-ish; we check at the handler.

## Alternatives considered

1. **bcrypt with a high cost factor.** Still memory-light, still GPU-attackable. Rejected.
2. **JWTs with short expiry + refresh tokens.** Doubles the moving parts, forces a denylist anyway for early revoke. Rejected.
3. **Sliding-only (no absolute cap) or absolute-only (no sliding).** Sliding-only lets a forgotten session live forever; absolute-only forces a relogin mid-task. Rejected both.
4. **Longer tokens (e.g., 512 bits).** No material benefit at 256 bits of entropy. Rejected.

## Revisions

### amendment-1 (Phase 19 ship — 2026-05-21) — three-change batch: drop "constant-time", scope sweeper to daemon, unify `SessionExpiredError` into `InvalidSessionError`

**Trigger:** Phase 19 ships the sessions half of this ADR. Round-1 + round-3 design review surfaced three points where the 2026-04-22 text describes a mechanism that does not match the CLI-only product as it ships, OR that misaligns with project conventions established at Phase 18:

1. **Constant-time comparison clause is misleading.** §Decision says "Lookup does a constant-time comparison against the stored hash." The actual lookup is `SELECT … WHERE token_hash = ?` against an indexed column — not constant-time and doesn't need to be. The 256-bit SHA-256 preimage-resistance dominates any plausible attacker model; constant-time string-compare against an indexed lookup is security theater.
2. **Sweeper thread has no host in CLI-only product.** §Decision names a "background `sweeper` thread." A CLI command's process lives for one verb-call; spawning a sweeper inside each invocation reaps nothing meaningful. The CLI-only product (Phase 18-39 scope per `confirmation_docs/PHASE_MAP.md` §1) has no daemon to host a long-lived thread.
3. **`SessionExpiredError` should unify with not-found into a single opaque-cause class.** Phase 18 PB-23 established the project pattern (`AuthFailedError` with private cause enum). The three `session_from_token` failure modes (expired-sliding, expired-absolute, never-existed) have the same threat-model property — the differential leaks no useful information to a 256-bit-random guesser. Different exception classes complicate callers without security gain.

**Amended behavior:**

* **Indexed-equality lookup, not constant-time compare.** Phase 19 `session_from_token` does `SELECT … FROM sessions WHERE token_hash = ?` where `?` is `hashlib.sha256(token.encode("ascii")).hexdigest()`. SQLite returns 0 or 1 row; no byte-position-of-diff timing leak in practice. The "constant-time comparison" §Decision clause is dropped as misleading; §Rationale's "Storing only the hash" still holds — the leak resistance argument is correct, the mechanism wording was off.
* **Lazy-only expiry at Phase 19; sweeper thread deferred to future HTTP daemon phase.** Phase 19 `session_from_token` checks expiry on every lookup and DELETEs the expired row inline before raising the error. Expired rows accumulate harmlessly between lookups (size bounded by user count × 24h ÷ avg-session-life — trivial for local-first). The §Decision sweeper-thread line is scoped to apply only when a long-lived server process exists; the future HTTP-daemon phase (post-38) amends this back into force.
* **`InvalidSessionError(cause: InvalidSessionCause)` single class.** Cause enum values: `EXPIRED_SLIDING`, `EXPIRED_ABSOLUTE`, `NOT_FOUND`. Public message uniform ("invalid session"); `.cause` is the private inspection point. HTTP layer (future) maps all three to 401. Replaces the §Decision reference to `SessionExpiredError → HTTP 401` — same HTTP code, broader scope.

**Rationale:** All three changes preserve the security properties §Rationale claims (argon2id, opaque tokens, sliding+absolute TTL); only the *mechanisms* shift to match (a) the indexed-SQLite reality, (b) the CLI-only product shape, and (c) the established Phase 18 PB-23 exception-shape pattern.

**Out-of-scope:** Sweeper thread (re-activates at HTTP daemon phase). Constant-time clause stays dropped — even when HTTP ships, the threat model doesn't justify resurrecting it.

See `halvim_mindsos/confirmation_docs/PHASE_19_DESIGN_LOG.md` §1 round 1 PB-4 + PB-7 + round 3 PB-14 for the rationale chain.
