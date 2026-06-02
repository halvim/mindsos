# ADR-0001: Introduce a dedicated Server Layer above the domain stack

- **Status:** Accepted
- **Date:** 2026-04-22
- **Deciders:** server-design chat
- **Supersedes:** the original plan to bolt auth directly onto the Knowledge Layer (KL)

## Context

Before this decision, the Knowledge Layer's write API took a bare `user_id` string and trusted the caller. Persistence of Locals, admin cross-user access, promotion of user-authored drafts into the Global Metagraph, and session state all had to live *somewhere*, but KL is a pure in-memory domain layer and doesn't want to know about users, sessions, passwords, or storage adapters. The upper layers (Capacity, Intelligence, Mental Model) all need the same identity and lifecycle primitives, and any of them growing their own would fragment the security model.

We also had a set of eight cross-cutting concerns to resolve: argon2-backed credentials, session TTL, hydrate/flush timing against FalkorDB, admin user management, audit logging, promotion orchestration (with rollback), cross-user read, and lock-out recovery.

## Decision

Introduce a new top-level package, `mindsos_server/`, that sits **above** every domain layer (Core → Knowledge → Capacity → Intelligence → Mental Model) and owns:

- Identity (`users` table) and credential verification.
- Session lifecycle (`sessions` table, `Session` object handed to domain layers).
- Hydration/flush of per-user Local Metagraphs via a `LocalPersister` protocol.
- Admin user and session management.
- Audit logging (`audit` table).
- Promotion orchestration (similarity report + freshness re-check + atomic flush with rollback).

KL's write API is rewritten to take a `Session` parameter instead of a bare `user_id`. Capacity (L3) adopts the same seam through a `SessionProtocol` type.

## Rationale

- **Separation of concerns.** Domain layers stay domain-only. Auth, persistence, and audit belong to one place so their invariants can be enforced locally.
- **One security story.** Every upper layer sees the same `Session`, the same capability checks, the same audit entries. No second inventory of permissions.
- **Testability.** A pure domain layer is trivially testable with in-memory fixtures; a layer that bundles auth and IO is not.
- **Extensibility.** Future transports (HTTP/RPC) wrap the server layer without touching domain code.

## Consequences

- A new package to maintain, with its own invariants (I-S1..I-S10).
- KL and L3 write APIs have a breaking signature change (`user_id: str` → `session: Session`). Legacy-string overloads are kept as deprecation shims for one cycle.
- All upper-layer code paths funnel capability checks through a single module (`mindsos_server.authz`).
- The server process is now the bootstrapping agent: it holds the argon2 config, token config, SQLite schema, and FalkorDB persister wiring.

## Alternatives considered

1. **Auth as a KL submodule.** Rejected: forces every layer above KL to re-implement its own access control against the same session state, and muddies KL's pure-domain contract.
2. **Decorator-based auth at the API boundary only.** Rejected: doesn't solve hydration/flush, promotion rollback, or cross-user install bookkeeping.
3. **Reuse an external auth framework (Flask-Login, FastAPI Users).** Rejected for phase 1 — we need deterministic in-process control for promotion locking and transient installs. A transport shim can sit *above* `mindsos_server` later.
