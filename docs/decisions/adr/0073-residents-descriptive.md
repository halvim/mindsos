---
title: Residents are descriptive; L3 contains no event loop
status: Accepted
date: 2026-04-21
layer: L3
aliases: [capacity-ADR-014]
---

# ADR-0073: Residents are descriptive; L3 contains no event loop

**Status:** Accepted

**Date:** 2026-04-21

## Context

Monitors subscribe to DataStates and emit others. A naive implementation would spawn threads or coroutines inside L3 to drive them. That places scheduling policy in the wrong layer and makes testing painful.

## Decision

`start_resident` builds a `ResidentSubscription` and registers it in a module-level dict. It does not spawn threads, timers, or queues. L4's event loop iterates `active_subscriptions()` and dispatches.

## Consequences

**Good:**
- L3 stays synchronous, purely functional, and trivially testable.
- L4 owns concurrency, back-pressure, and lifecycle.

**Cost:**
- Module-level dict's sharing across layer instances flagged in open-concerns B4 as a test-hygiene hazard.

## Alternatives considered

1. **Build a tiny built-in scheduler in L3** — rejected (L4 needs its own anyway; two schedulers would fight).

## Enforced as

Invariant I10 in the L3 handoff.

## §amendment-1 (2026-05-25, Phase 31) — Halvim divergences

Four clauses, batched per Phase 22 ADR-0012 §am3 precedent. The §Decision text above describes parent reference behavior; halvim ships the descriptive contract with the following divergences. All four flow from halvim's session-driven posture (no leaky module globals; no `user_id=` legacy kw) and from closing the §Cost row above ("module-level dict's sharing across layer instances flagged ... as a test-hygiene hazard").

**Clause 1 — Per-layer subscription registry.** `start_resident` registers the new `ResidentSubscription` in `self._subscriptions` (a `Dict[str, ResidentSubscription]` field on the `CapacityLayer` instance) rather than a module-level dict in `mindsos_capacity.runtime`. Free-function `start_resident(declaration, ...)` and `stop_resident(subscription)` (parent shape) are NOT shipped at halvim Phase 31 — the only public surface is the `CapacityLayer.start_resident` / `stop_resident` / `active_subscriptions` methods. This closes the §Cost row: each test (and each multi-tenant deployment) gets its own registry; nothing leaks across layer instances.

**Clause 2 — `subscribes_to` kwarg dropped.** Parent's `start_resident(declaration, *, subscribes_to=None, ...)` allowed callers to override the declaration's intrinsic `Monitor.subscribes_to: Tuple[str, ...]`. Halvim drops the kwarg: the declaration is the source of truth. If L4 wants narrower subscription than a Monitor declares, the policy is to register a narrower Monitor — not to override per-start_resident-call. Eliminates a footgun ("why does my resident not fire" when caller-side override silently narrows the declaration's intended set).

**Clause 3 — `ResidentSubscription` is `@dataclass(eq=False)`.** Default `@dataclass` would generate field-by-field equality. With mutable `state: Dict` + `handlers: List` fields, that equality is fragile and useless. `ResidentSubscription` is a HANDLE (callers hold an opaque token for stop / observation); Python default id-based eq matches the intent. Hashability inherits from Python default (id-based via `object.__hash__`).

**Clause 4 — Wrong-type raises `ResidentError`, not `CapacityRegistrationError`.** Parent's `start_resident` raises `CapacityRegistrationError` when the IRI resolves to a non-Monitor declaration. Halvim raises `ResidentError(CapacityLayerError)` — residents are a *lifecycle* concern distinct from registration (Phase 28's `DiscoveryFailedError` subclasses `CapacityRegistrationError` because discovery IS registration; residents are not). Unknown-IRI failures still propagate `CapacityRegistrationError` from `_resolve_declaration` unchanged — only the type-mismatch case is rehomed.

## §Implementation (2026-05-25, Phase 31)

Shipped 2026-05-25 in three halvim source files:

- `mindsos_capacity/exceptions.py` — adds `ResidentError(CapacityLayerError)` (8th class). Subclass choice locked at Phase 31 R1 PB-16.
- `mindsos_capacity/runtime.py` — adds `@dataclass(eq=False) ResidentSubscription` with `subscription_id` / `declaration` / `subscribes_to` / `handlers` / `state` (ADR-0099 Q6 slot; L4-managed; L3 never writes) / `_active` fields plus `on_signal` / `emit` / `is_active` methods. The free-function `start_resident` / `stop_resident` / `active_subscriptions` from parent are NOT ported (§amendment-1 clause 1).
- `mindsos_capacity/capacity_layer.py` — `CapacityLayer.__init__` initializes `self._subscriptions: Dict[str, ResidentSubscription] = {}`. Methods `start_resident(capacity_iri, *, session: SessionArg = None, context: Optional[Mapping[str, Any]] = None) -> ResidentSubscription`, `stop_resident(subscription) -> None`, `active_subscriptions() -> List[ResidentSubscription]`. Provenance-stamping (session_user_id + session_id into context dict) mirrors Phase 30's `invoke` precedent.

Status remains Accepted.
