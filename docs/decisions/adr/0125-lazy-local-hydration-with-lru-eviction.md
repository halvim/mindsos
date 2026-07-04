---
title: Lazy Local hydration with LRU eviction
status: Deferred
date: 2026-04-27
layer: Server
---

# ADR-0125: Lazy Local hydration with LRU eviction (server-side)

**Status:** Deferred — acknowledged with a known path forward but not implemented in v1; revisit post-v1. Reconciled in the 2026-07 doc-vs-code audit.

**Date:** 2026-04-27

**Related:** ADR-0042 (KL install/extract hooks), ADR-0118 (per-user transactional promotion — frozen drafts add per-user state). Server-layer ADR; not a Core change.

## Context

FalkorDB is RAM-resident; persistence is Redis RDB/AOF. Server cold-start = "load every graph from RDB." Per-user Locals multiply: 1000 users × 50k-node Local = 50M nodes resident.

Today's behaviour (per ADR-0042): on login, the server hydrates the user's Local from FalkorDB and installs it into KL via `install_local_metagraph`. Idle users keep their Locals resident for the duration of their session. After logout the Local is extracted and flushed.

Three places this bites:

1. **Server cold-start.** Reload everything before accepting requests. Time grows with user count × Local size.
2. **Per-user RAM ceiling.** Active Locals stay resident; idle users with active sessions still cost RAM.
3. **Backup window.** RDB snapshot during heavy write traffic stalls writes.

Pivot v1 doesn't address this; the slice (`mindsos_server/migration.py`) walks user Locals on session-start, which compounds the cold-load cost.

## Decision

Implement `LocalRegistry` in `mindsos_server` with two policies:

### 1. Lazy hydration

Login does **not** load the Local. The session is created, audited, returned. Hydration deferred to first read or write.

```python
# Login (post-change):
sess = SessionStore.create(user_id, ...)
audit.append(LOGIN, sess)
return LoginResult(token=..., session=sess, ...)

# First read/write:
mg = LocalRegistry.get_or_hydrate(user_id, mutex=user_mutex(user_id))
KL.install_local_metagraph(user_id, mg)
# ... operation runs ...
```

Behaviour:

- **First request after login** pays hydration cost. Subsequent requests in the same session are instant.
- **Idle users** never hydrate; cost zero RAM.
- **Hydration is mutex-protected.** Two concurrent first-requests for one user serialise on `user_mutex(user_id)`.

### 2. LRU eviction

`LocalRegistry` tracks `(user_id, last_accessed_at, mg)` tuples. When total RAM (estimated by node count × constant or measured via `psutil`) exceeds a watermark, evict the LRU Local.

**Eviction discipline:**

- Acquire the target user's mutex. Skip and pick next LRU if held (busy user — hot Local). Retry on next eviction trigger.
- Extract the Local via `KL.extract_local_metagraph(user_id)`.
- Flush to FalkorDB in a transaction (per existing logout flow).
- Drop from `LocalRegistry`.
- Audit `LOCAL_EVICTED` event (new audit type).

The user's session remains valid. Their next request re-hydrates.

**Watermark:** configurable per `MindsOSServer.__init__(local_ram_watermark_mb=...)`. Default: 2048 MB (tunable; load-test informed).

**Eviction trigger:** checked after every successful flush. Cheap; doesn't add a daemon thread.

### 3. Audit and observability

- New audit event: `LOCAL_HYDRATED` (on first-read after login), `LOCAL_EVICTED` (on LRU eviction).
- New CLI: `mindsos-server local-status` shows per-user `(installed: bool, last_accessed_at, node_count)`.
- New metric (when ADR-0126's observability hooks ship): per-user hydration latency, eviction count.

## Rationale

Lazy hydration moves the cost from "every login" to "every first request after login." For a workflow where users log in but don't immediately work (CI bot, long-lived API client), this is a ~10×–100× cold-start win.

LRU eviction caps RAM at a known bound. The risk is "evict a user about to make a request" (cold cache); mitigation: skip-if-busy avoids evicting an actively-locked user, so the worst case is "evicting someone who hasn't worked in a while," which is exactly the desired semantic.

Per-user-FalkorDB-instance was an alternative (each user gets their own FalkorDB process). Rejected because process-per-user is heavy, and FalkorDB's Redis-derived process model isn't designed for hundreds of concurrent processes.

## Consequences

**Good:**

- Cold-start time drops from O(users × Local-size) to O(active-shared-Global).
- RAM usage capped by watermark; predictable under user growth.
- LRU eviction matches the actual access pattern (idle users cost nothing).
- The pivot's migration walks user Locals lazily — `migrate_user_to_latest_release` is naturally invoked from first-request hydration.

**Tradeoffs:**

- ~300 LOC server-side (`LocalRegistry`, eviction policy, mutex coordination).
- First-request latency for cold sessions becomes user-visible. Mitigation: `mindsos-server local-status` shows hydration state for ops.
- Eviction during heavy concurrent flushes can cascade — if many users are evicted at once, FalkorDB write traffic spikes. Mitigation: rate-limit evictions per minute (~1 eviction per 5 seconds in default config).
- The session-vs-Local lifetime split is more nuanced: a session can outlive its Local install/extract cycle. Adds one state to the install-record dance.

**Coordinated changes:**

- New module `mindsos_server/local_registry.py`.
- `MindsOSServer.login` no longer hydrates.
- `MindsOSServer` gains `local_ram_watermark_mb` constructor param.
- KL `install_local_metagraph` / `extract_local_metagraph` (per ADR-0042) unchanged in shape but called more frequently.
- New audit event types `LOCAL_HYDRATED`, `LOCAL_EVICTED` (added to ADR-0115's enum).
- New CLI subcommand `local-status`.

## Alternatives considered

1. **Status quo (eager hydration on login).** Rejected — cold-start cost grows linearly with user count; RAM usage unbounded.
2. **Per-user FalkorDB instance.** Rejected — heavy; process-per-user not Redis's design point.
3. **Cold-tier offload** (drop Local from FalkorDB entirely; reload from RDB on demand). Considered; rejected for v1. The reload-from-RDB path adds a new persistence tier and isn't needed if LRU eviction handles the RAM ceiling cleanly. Revisit if LRU eviction proves insufficient.
4. **TTL-based eviction** (drop Locals idle for N hours). Rejected — fixed TTL doesn't adapt to load. LRU is RAM-aware.

## Implementation references

- New: `mindsos_server/local_registry.py`.
- Modified: `mindsos_server/server.py` (login no longer hydrates).
- Modified: `mindsos_server/cli.py` (new `local-status` subcommand).
- Audit additions in `mindsos_server/audit_events.py` (per ADR-0115's enum file).
- Tests: `tests_server/unit/test_local_registry.py` + `tests_server/integration/test_lazy_hydration.py`.

ADR moves from Proposed to Accepted when `LocalRegistry` lands in `mindsos_server/`, lazy hydration is wired through `login`, and `docs/usage/server/sessions.md` reflects the new behaviour.
