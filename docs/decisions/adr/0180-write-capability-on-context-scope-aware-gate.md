---
title: Write-half close — pre-authorized writeable capability on CapacityContext + scope-aware call-time gate
status: Accepted
date: 2026-06-09
accepted_date: 2026-06-09
layer: L4
related: [0175, 0170, 0146, 0159, 0010]
---

# ADR-0180: Write-half close — pre-authorized `writeable` capability on `CapacityContext` + scope-aware call-time gate

**Status:** Accepted

**Date:** 2026-06-09

**Related:** ADR-0175 (invoke→CapacityContext flip — §amendment-1 deferred the write-half here; **amended §am-2**), ADR-0170 (write-body gate boundary — **amended**), ADR-0146 (symmetric write contract — **amended**, contract preserved), ADR-0159 (CapacityContext v2), ADR-0010 (L3 must not reach Server; L4 may).

## Context

ADR-0175 §amendment-1 deferred PB-23's **write half** to Phase 48 with its real consumer (wired consolidation, ADR-0176). The tension: `CapacityContext` is authorization-free (10 typed fields incl. `session_id`/`user_id`/`kl`, **no Session object**), but `consolidate`/`trace` bodies call `kl.writeable(session, …)` and `trace` calls `session.has(CAN_WRITE_GLOBAL)` — they need a Session. ADR-0170 §Decision-1 froze "authorization-free context"; the open question (principal-on-context vs L4-performs-write) was left to this phase. Phase-48 grounding: exactly 2 production callers (`consolidate.py`, `trace.py`); `CapacityContext` is a frozen 10-field dataclass; `dispatch.py` already gates `effect_iri` pre-invocation but v0 demands `CAN_WRITE_GLOBAL` for *any* write-body — which would wrongly deny `consolidate:mm` (a **Local** own-user write).

## Decision

### 1. Pre-authorized `writeable` capability on the context (PB-2)

L4 `dispatch.py`, when building the `CapacityContext` for a write-body, injects an 11th field `writeable: Optional[Callable]` — a **session-bound, pre-authorized callable** closing over the dispatcher's live session + KL: `writeable(role, scope, version) -> KLWriteHandle`. Bodies call `context.writeable(role=…, scope=…, version=…)` → `handle.validate_node(...)` + `handle.write_and_validate(...)`, exactly as they called `kl.writeable(session, …)` today. The context carries a **narrowed capability**, not a principal: there is no Session attribute for an L3 body to query, so L3 structurally cannot make an authorization decision. ADR-0146's symmetric validate-then-write contract is **unchanged** (the body still validates and writes through the handle); ADR-0170's intent (no auth state in L3) is **preserved** more strongly than a Session field would.

### 2. Scope-aware gate at write-time (PB-10)

The required capability depends on **scope** (`local` → none, `kl.writeable` enforces own-user; `global` → `CAN_WRITE_GLOBAL`), and scope is a `context.writeable(...)` call argument — unknown at pre-invocation gate time. The gate therefore fires **inside the `writeable` callable, at call-time**: `scope == "global"` requires `session.has(CAN_WRITE_GLOBAL)` (raising on absence; `session is None` is the ADR-0080 bootstrap carve-out); `scope == "local"` requires no extra capability. This is the deferred "`effect_iri`-driven capability resolution," made scope-precise. It **refines** ADR-0170 ("gate before invocation" → "gate at write-time inside the pre-authorized capability") and **supersedes** the Phase-47 `dispatch.required_capability_for`/`check_write_permitted` pre-gate (which over-restricted Local writes).

**The gate travels with the capability, built by the session-holder.** Grounding (Phase 48 R1) found `capacity_layer.invoke` is itself a write-invocation path — the shipped `mindsos capacity invoke` CLI verb dispatches `consolidate`/`trace` through it. So "the gate lives in L4 dispatch" generalizes to: a single shared factory `make_writeable(kl, session)` (`mindsos_capacity/context.py`) builds the gated callable, invoked by **whoever holds the session** — `L4Dispatcher.build_context` for task lifecycles, and `CapacityLayer.invoke` (the write-body branch) for the CLI / direct L3-invoke path. The capability body is identical and principal-free either way; the gate is a property of the capability, not of the calling layer.

### 3. Migrate both `consolidate` and `trace` (PB-8); read-path union deferred (A1)

Both write bodies migrate off dict `context` to `context.writeable`; production dispatches them exclusively through `L4Dispatcher`. `trace`'s `session.has(CAN_WRITE_GLOBAL)` check is removed (subsumed by the call-time gate). The invocation tests (`tests/phase_33` consolidate + trace) migrate to `L4Dispatcher`; `tests/phase_42` field-count → 11; `tests/phase_47` dispatch-gate → call-time semantics; `tests/phase_36` precondition tests build a `CapacityContext`.

**A1 scope boundary (user-ratified, Phase 48 R1).** Grounding showed `capacity_layer.invoke` builds the **dict** context for the *entire read-capacity corpus*; making it emit `CapacityContext` (to drop the `Optional[Union[Mapping, CapacityContext]]` annotation per ADR-0175 §am-1) pulls every read test into the blast radius mid-convergence. The **write-half authorization close** — the actual goal — is achieved here (L3 holds no principal; writes are L4-gated via the capability; bodies fully on `context.writeable`). The **read-path dict + the union annotation are kept one more phase** as documented read-legacy (no auth concern, no consumer issue) and the union-drop is deferred to a cleanup pass. PB-23's authorization half **closes**; its cosmetic single-context-type half is deferred. (`tests/phase_30` + the `tests/phase_33` *context-injection* tests are therefore **not** migrated — `capacity_layer.invoke` is unchanged.)

## Rationale

- **Capability, not principal.** Handing L3 a narrowed, pre-authorized callable is least-privilege and structurally bars L3 auth decisions — strictly better than a Session field for the WSD write-capacities built against this contract.
- **No `_CapacityBase` change.** Scope/role stay where they belong (the body knows what it writes); the call-time gate needs no declared scope field.
- **ADR-0146 + ADR-0170 both preserved** rather than traded against each other.

## Consequences

- `CapacityContext` gains an 11th field (`writeable`, default `None`; frozen dataclass admits it).
- `consolidate`/`trace` bodies + 2 tests migrate; transitional union annotation removed.
- `dispatch.check_write_permitted` pre-gate replaced by the call-time gate inside the injected callable.
- Amends ADR-0175 (§am-2), ADR-0170 (gate timing + principal-free clarification), ADR-0146 (handle now from `context.writeable`).

## Alternatives considered

1. **Session object on `CapacityContext` (PB-2 Opt B).** Rejected — re-opens L3-side authorization (any body can call `.has()`); the exact thing the strict line + ADR-0170 forbid, and the contract WSD builds against.
2. **L4 performs the KL write; body assembles only.** Rejected — breaks ADR-0146 (L3 is the write surface) + double-validation seam.
3. **Declare write-scope on `_CapacityBase` + keep pre-invocation gate (PB-10 Opt B).** Rejected — registration-contract touch (post-Phase-42 v2) for 2 consumers; heavier than the call-time gate.

## §Implementation (Phase 48; pending ship)

`mindsos_capacity/context.py` (11th `writeable` field + shared `make_writeable(kl, session)` factory); `mindsos_intelligence/dispatch.py` (`build_context` injects `make_writeable(...)`; **remove** `required_capability_for`/`check_write_permitted` — the blanket pre-gate — and the `mindsos_intelligence.__init__` re-export); `mindsos_capacity/capacity_layer.py` (write-body branch builds a `CapacityContext` with `make_writeable(...)`; read path keeps the dict — A1′); `consolidate.py`/`trace.py` body migration to `context.writeable`; test migration (`tests/phase_33` consolidate+trace → `L4Dispatcher`; `tests/phase_42` 10→11; `tests/phase_47` call-time gate; `tests/phase_36` precondition `CapacityContext`; `tests/phase_34` no-KL error-message). **Not** touched (A1): `runtime.py` union annotation (kept for the read-path dict); `tests/phase_30` + `tests/phase_33` context-injection tests + the `tests/phase_34` CLI/bypass tests (the write-branch keeps them green). Commit-group 2a. Write-gate coverage in `tests/phase_47/test_dispatch_gate.py` (Local write succeeds without `CAN_WRITE_GLOBAL`; Global write denied without it).

## §amendment-3 — the external-model capability, and why the pattern generalises (2026-08-16)

**Amendment status:** Accepted

`CapacityContext` gains a **12th** field, `llm` (default `None`): the narrowed
capability through which a `comprehension.*` body consults an external
language model, typed by the new `LLMHandle` Protocol in
`mindsos_capacity/context.py`. The concrete clients ship in
`mindsos_llm/` (relocated there by ADR-0210 slice 1a, 2026-09-02; it was
`mindsos_capacity/llm/` when this ADR was accepted) and are named in the
Protocol's docstring only.

**This is §Decision-1's pattern re-used, not a new one.** The body receives a
narrowed capability rather than a client it constructed; it holds no
credentials, no session and no principal; the capability is injected by L4
`dispatch.build_context`, which is the only place holding the live client.
ADR-0170 is untouched — L3 still makes no authorization decision — and the
field is `None` for every body that did not ask for it, exactly as
`writeable` is `None` for read-bodies.

**Injection is DECLARED, not ambient.** `Capacity` gains
`consults_llm: bool = False`, and `build_context` injects the client only
when the resolved declaration sets it — the discipline ADR-0200 (C3)
established for `reads_mm`. A **category-membership** rule was the archived
seam's mechanism and is REJECTED: a category says what a capacity *is*, a
dependency says what it *does*, and only the second can be read off the
registry per capacity. (Coordination §87 T-F7 / §89; the endorsement that
briefly went the other way rested on a mis-stated premise about `reads_mm`.)

**A declared-but-unbound client is FATAL.** `L4Dispatcher.dispatch` raises
`LLMUnavailableError` before `runtime.invoke`'s envelope, so it escapes
`execute_pipeline` rather than becoming a stopped member. That is deliberate
and pinned: a dispatcher with no client bound fails identically for every
member, so a partial Record would be a Record of nothing. It is also why that
one message may name an IRI while every error in `mindsos_llm` is
fixed prose — those reach a customer through `stopped_detail`, and this one
reaches no page at all.

**Consequences.** `tests/phase_42/test_typed_capacity_context.py`'s field pin
is restated 11 → 12 and RENAMED (`...has_eleven_fields` asserting twelve is
the stale-name class). `mindsos_capacity.__all__` is unchanged at 146:
`LLMHandle` is exported from `context.py` and deliberately not re-exported at
package level, since no consumer imports it — the two export-slate pins stand.
