---
title: Durable Local-persistence lifecycle (FalkorDBLocalPersister + load_or_mint_local)
status: Accepted
date: 2026-06-21
layer: Server
amends: [ADR-0160, ADR-0042]
aliases: [F9-B]
---

# ADR-0186: Durable Local-persistence lifecycle

**Status:** Accepted

**Date:** 2026-06-21 (branch `feat/f9-durable-local`)

## Context

`FalkorDBLocalPersister` (`mindsos_server/persistence/local_persister.py`)
shipped at Phase 44 (ADR-0160) but **dormant** — present in the module's
`__all__` yet not re-exported at the package level, and with no consumer.
A device's Local Metagraph (learned skills + durable state) did not
survive a process restart. F9 makes per-device Locals durable so taught
capabilities can be re-activated on reboot (ADR-0185).

Two separate Local Metagraphs exist per user: the KL Local
(`local_knowledge:<user_id>`, holding the knowledge role-graphs including
`learned-parameters`) and the CL Local (`local_capacity:<user_id>`,
holding capacity category-graphs). `FalkorDBLocalPersister` keys by
`user_id` → `local_knowledge:<user_id>`.

## Decision

- **Promote `FalkorDBLocalPersister` to public surface** — re-export from
  `mindsos_server.persistence.__all__`. It is the durable backing store
  for per-device Locals.
- **Persist the KL Local only.** The CL Local is NOT persisted; it is
  re-minted from the KL `learned-parameters` descriptors at boot
  (ADR-0185 Model A). The persister's existing `local_knowledge:` key is
  therefore correct as-is.
- **`load_or_mint_local(kl, persister, user_id) -> (Metagraph, minted)`**
  (`mindsos_server/local_boot.py`) — load the dump and
  `install_local_metagraph`, else lazy-mint. **Install-before-mint**
  (PB-O): `install_local_metagraph` refuses with `AlreadyInstalledError`
  if a Local is already present, and any lazy `kl.local_metagraph` access
  mints+stores first — so the dump install must precede any lazy access;
  re-entrant (returns the existing reference if already installed).
- **`boot_local(cl, kl, persister, user_id, *, session)`** — the
  lazy load-on-first-access free function (per Phase 44 CR-3 / PB-38 — a
  free function, not a `MindsOSServer` method): `load_or_mint_local`
  then `reactivate_local_capacities` (ADR-0185) for that one user.
  **No global boot scan** (PB-D) — enumerate-all-Locals is a v2 concern,
  matching the lazy `local_metagraph` model.
- **Key contract:** a per-device caller pins `device_id == user_id` so the
  `local_knowledge:<user_id>` names collide-match. The Phase-44
  `CAN_*_OTHER_LOCAL` caps are cross-Local *reads* — orthogonal to
  own-Local persist.
- **Login/logout wiring stays deferred** (Phase 44 CR-3). F9 provides the
  durable backing store the ADR-0042 install/extract hooks will use;
  these are the free-function primitives a future lifecycle (or a demo's
  boot loop — robot DM-8) calls.

## Consequences

**Good:** per-device Locals survive restart; a single durable artifact +
single persister target (no two-metagraph persistence).

**Cost:** new public surface (persister export + `local_boot`
functions) — a version-surface touch on a non-phase `feat/` ship
(`core_git_sha` bump + public-surface note; `core_version` stays
`phase50`).

## Amendment trail
- **Amends ADR-0160** — the persister was shipped dormant/no-consumer;
  F9 promotes it to live public surface.
- **Amends ADR-0042** — forward-reference: F9 provides the durable backing
  store its install/extract hooks will use; the hooks' login/logout
  wiring is unchanged (still deferred).
- **Resilient `boot_local` re-activation (2026-07-16)** — `boot_local` /
  `reactivate_local_capacities` / `_dep_order_descriptors` take an additive-inert `strict`
  flag (default `True`); `boot_brain` passes `strict=False` so one durable Local carrying a
  learned descriptor whose factory is absent cannot brick boot (build pre-pass drops-and-warns;
  a dependency cycle degrades to unordered). See **ADR-0183 §am-2** + **ADR-0185**.
