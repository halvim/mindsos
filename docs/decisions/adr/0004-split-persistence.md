# ADR-0004: Split persistence — SQLite for server state, FalkorDB for graphs

- **Status:** Accepted
- **Date:** 2026-04-22
- **Related:** ADR-0001, ADR-0011

## Context

The server needs to persist two very different kinds of state:

1. **Small, relational, strongly-consistent server state** — users, sessions, audit log. Read-heavy on lookup, transactional on write, queryable by admin tools.
2. **Large, schemaless, graph-shaped domain state** — Global Metagraph + per-user Local Metagraphs. Already modelled on FalkorDB in the existing adapter.

FalkorDB is the right store for the second; it is not the right store for the first. Using FalkorDB for the audit log would force graph gymnastics for "give me the last 100 failed logins for user X", and using SQLite for the Locals would throw away all the metagraph machinery.

## Decision

Persistence is **split by data kind**:

- **`server.db` (SQLite file)** holds:
  - `users(user_id, password_hash, role, disabled, created_at, ...)`
  - `sessions(session_id, user_id, token_hash, created_at, last_seen_at, expires_at, source, ...)`
  - `audit(id, ts, actor_user, event, target_user, extra_json, ...)`
  - Schema DDL lives in `mindsos_server/_schema.py`.
  - Migrations are forward-only, versioned by a `schema_version` table row.

- **FalkorDB** holds **only graphs**:
  - One graph per role per scope: `global_<role>` for the Global Metagraph's role graphs; `local_<slug(user_id)>_<role>` for each user's Locals.
  - Access mediated through the `LocalPersister` protocol (see ADR-0011).

Server code reads/writes `server.db` directly; KL never sees SQLite. KL reads/writes its in-memory metagraphs; the server hydrates them from FalkorDB on login and flushes them on logout.

## Rationale

- **Right tool, right job.** SQLite is the world's most battle-tested small-relational store; it handles the server's needs with a single file and no daemon. FalkorDB carries the graph workload it was designed for.
- **Independent recovery.** Corrupted Local in FalkorDB? Re-import from source; users table is untouched. Corrupted `server.db`? `reset-admin` rebuilds identity without touching graphs.
- **Admin query shape.** Audit queries are relational (`WHERE actor=? AND event=? ORDER BY ts DESC LIMIT ?`). Forcing them into Cypher would be hostile.
- **Transactional server state.** User create/promote/demote/disable all need ACID; SQLite gives it free.

## Consequences

- Two backup stories: operators back up `server.db` on one cadence and FalkorDB on another. The developer guide calls this out.
- Cross-store consistency is limited: we document that a session's `user_id` column referring to a user must match the Local at hydration time; mismatches surface as `SessionHalfBuiltError` (503).
- Session state dies on server restart — `sessions` rows are wiped because in-flight Locals are gone from FalkorDB's KL view. This is a feature, not a bug (see ADR-0005).
- `server.db` is small; no replication story is required for v1.

## Alternatives considered

1. **All-FalkorDB (audit as a graph).** Rejected — relational queries on the audit log are unidiomatic and slow.
2. **All-SQLite (serialize graphs).** Rejected — gives up the FalkorDB adapter and its Cypher surface for no benefit.
3. **Postgres for server state.** Overkill for a local-first tool; we can migrate the schema later without changing the split.

## Revisions

### amendment-1 (Phase 19 ship — 2026-05-21) — two-change batch: scope "session state dies on server restart" to future daemon; simplify `sessions` schema (`expires_at` computed, not stored)

**Trigger:** Phase 19 ships the `sessions` table half of this ADR. Round-1 + round-2 design review surfaced two points:

1. **§Consequences says "Session state dies on server restart — `sessions` rows are wiped because in-flight Locals are gone from FalkorDB's KL view."** This justification doesn't apply to the CLI-only product. There is no daemon, no in-memory Local that survives between invocations, and no "restart event." Per `confirmation_docs/PHASE_MAP.md` §1, the product as it ships through Phase 38 is CLI-only; FalkorDB persists across CLI runs; the premise that triggers the wipe doesn't fire. Literal compliance with the §Consequences text (wipe `sessions` on every CLI invocation) would make `login()` immediately useless because the next CLI verb would see no session.
2. **`expires_at` column is redundant.** §Decision lists `sessions(..., created_at, last_seen_at, expires_at, ...)`. But expires_at = `min(created_at + 24h_absolute, last_seen_at + 8h_sliding)` is a pure function of two other columns. Storing it invites drift if last_seen_at gets updated and expires_at doesn't.

**Amended behavior:**

* **CLI-only sessions persist across invocations.** Phase 19 `sessions` rows die on (a) lazy TTL expiry on `session_from_token` lookup, (b) explicit `logout(token)` / `kill_my_own_sessions(credentials)` / `admin_kill_session(target_session_id)` (P22), or (c) tester manually deleting `server.db`. The §Consequences wipe-on-restart rule is scoped to apply only when a long-lived server process exists; the future HTTP-daemon phase (post-38) amends it back into force together with ADR-0005 §am1.
* **`sessions` schema simplified to 5 columns:** `(session_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users ON DELETE CASCADE, token_hash TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL, last_seen_at TEXT NOT NULL)`. Phase 19 `session_from_token` computes `expires_at = min(created_at + ttl.absolute_seconds, last_seen_at + ttl.sliding_seconds)` at every lookup. The §Decision column list updates from 7-ish to 5; `expires_at` and `source` are both dropped (`source` per ADR-0005 §am1). Index `idx_sessions_user_id ON sessions(user_id)` added for the concurrent-login lookup hot path. `token_hash UNIQUE` constraint auto-indexes the lookup hot path.

**Rationale:** Honest product description matters more than literal ADR compliance when the product shape has shifted underneath the text. The wipe-on-restart §Consequences clause was written for an HTTP-daemon era that hasn't materialized; the schema simplification follows the established hygiene rule "don't store what you can compute."

**Out-of-scope:** Wipe-on-restart re-activates when HTTP daemon ships (re-amend at that point). `expires_at` storage stays dropped permanently — even under daemon there's no reason to denormalize.

See `halvim_mindsos/confirmation_docs/PHASE_19_DESIGN_LOG.md` §1 round 1 PB-1 + round 2 PB-10 for the rationale chain.
