---
title: SessionProtocol via duck-typing, not TYPE_CHECKING import
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-003]
---

# ADR-0040: SessionProtocol via duck-typing, not TYPE_CHECKING import

**Status:** Accepted

**Date:** 2026-04-22

## Context

KL needs to annotate `session` parameters and call `session.has(...)`. The real `Session` class lives in `mindsos_server.session`. If KL imports it — even under `TYPE_CHECKING` — the layer-isolation test fails. Two options: a runtime-unreachable `TYPE_CHECKING` import, or a `SessionProtocol` duck-typed locally.

## Decision

`mindsos_knowledge/types.py` defines a `@runtime_checkable Protocol` with `session_id: str`, `user_id: str`, `actor_role: Literal["user","admin"]`, `capabilities: Iterable[str]`, and `has(capability: str) -> bool`. The real `Session` satisfies this structurally. KL makes zero imports from `mindsos_server`.

## Consequences

**Good:**
- Hard layer isolation — the layer-isolation test greps cleanly.
- `_LocalTestSession` can also satisfy the protocol.

**Bad:**
- Two definitions of "what a Session looks like" exist (the Protocol in KL, the dataclass in the server).

## Alternatives considered

Import `Session` as a concrete type — rejected because it breaks layer isolation.

## Revisions

### amendment-1 (Phase 25 ship — 2026-05-23) — First ship at Phase 25

**Trigger:** Phase 25 ships `mindsos_knowledge/types.py` with the `SessionProtocol` per §Decision verbatim. The Phase 18 PB-33 lock pre-positioned the concrete `mindsos_server.session.Session` dataclass to be structurally compatible with this Protocol; Phase 25 is the slot where KL gains its first consumer of the Protocol (via the `mindsos_server.orchestrator.read_other_local` ctx mgr whose `admin_session: Session` argument satisfies `SessionProtocol` structurally).

**Amended behavior:**

* **`mindsos_knowledge/types.py` ships at Phase 25** with the §Decision Protocol shape verbatim: `session_id: str`, `user_id: str`, `actor_role: Literal["user", "admin"]`, `capabilities: Iterable[str]`, `has(capability: str) -> bool`. `runtime_checkable` decorator enables `isinstance(session, SessionProtocol)` test assertions.

* **KL maintains zero `mindsos_server` imports.** The `tests/phase_25/test_import_isolation_phase25.py` test grep-asserts no `from mindsos_server` / `import mindsos_server` in any `mindsos_knowledge` submodule. Static scan; runs every CI run.

* **`mindsos_server.session.Session` structurally satisfies the Protocol.** `tests/phase_25/test_session_protocol_satisfied.py` asserts `isinstance(Session.for_testing(...), SessionProtocol)` for both `is_admin=True` and `is_admin=False` branches.

* **Capabilities typing:** Protocol declares `Iterable[str]`; Server's concrete `Session.capabilities` is `frozenset[str]`. Frozenset structurally satisfies Iterable; the Protocol relaxation lets future test-doubles (e.g., L3 fake sessions) use plain tuples / lists without forcing them to frozenset.

**Coordinated changes at this amendment:**

* `mindsos_knowledge/types.py` (NEW) — Protocol definition + `runtime_checkable`.
* `tests/phase_25/test_session_protocol_satisfied.py` — isinstance + attribute-shape tests.
* `tests/phase_25/test_import_isolation_phase25.py` — package-wide grep scan.

**Out-of-scope:** L3 (`mindsos_capacity`) does NOT yet consume `SessionProtocol` (L3 is in design per PHASE_MAP §1 layer status). Re-export of Protocol via `mindsos_knowledge.__init__.py` not required at v1 — KL's write API doesn't yet take session args (those land at the first user-Local-write phase).

**Phase 25 design log:** `halvim_mindsos/confirmation_docs/PHASE_25_DESIGN_LOG.md` §4 ADR delta + §5 implementation references.

### amendment-2 (Phase 28 ship — 2026-05-24) — L3 ships its own slim SessionProtocol copy

**Trigger:** Phase 28 ships `mindsos_capacity.CapacityLayer` with a Global-write capability gate (`_enforce_global_write`) that needs to type-check `session: Optional[SessionProtocol]`. ADR-0010 §I-S1 forbids `mindsos_capacity → mindsos_server`. ADR-0010 §am1/§am2 does not enumerate `mindsos_capacity → mindsos_knowledge` either, and the parent-precedent install-isolation argument (see ADR-0067 §amendment-1) keeps L3 library-installable without bootstrapping L2's import graph. Therefore L3 needs its OWN slim copy of the Protocol, not a re-export from L2.

**Amended behavior:**

* **`mindsos_capacity/types.py` ships at Phase 28** with the §Decision Protocol shape verbatim — identical to `mindsos_knowledge/types.SessionProtocol`: `session_id: str`, `user_id: str`, `actor_role: Literal["user", "admin"]`, `capabilities: Iterable[str]`, `has(capability: str) -> bool`. `runtime_checkable` decorator preserved.

* **Slim port semantics.** Halvim's L3 `types.py` ships ONLY `SessionProtocol` + `SessionArg = Optional[SessionProtocol]` type alias. The parent's `_resolve_session_arg` + `_LocalTestSession` + `_make_test_session` + bare-`str` / `Mapping` deprecation shim is NOT ported — halvim callers always pass `Session.for_testing(...)` or `None`. Phase 33 (write capacities) expands `types.py` in place if a richer resolver becomes needed.

* **Parity test at `tests/phase_28/test_session_protocol_satisfied.py`** asserts three contracts:
  1. `set(L3.SessionProtocol.__annotations__) == set(L2.SessionProtocol.__annotations__)` — strict-equality of attribute names.
  2. Both protocols expose `has(capability: str) -> bool`.
  3. `isinstance(Session.for_testing(...), L3.SessionProtocol)` — real Session structurally satisfies the L3 copy.

**Coordinated changes at this amendment:**

* `mindsos_capacity/types.py` (NEW) — Protocol + `SessionArg` alias only.
* `mindsos_capacity/__init__.py` — exports `SessionProtocol` + `SessionArg`.
* `tests/phase_28/test_session_protocol_satisfied.py` (NEW) — three-assertion parity test.
* `tests/phase_28/test_import_isolation_phase_28.py` (NEW) — asserts `mindsos_capacity` imports neither `mindsos_server` nor `mindsos_knowledge`.

**Phase 28 design log:** `halvim_mindsos/confirmation_docs/PHASE_28_DESIGN_LOG.md` §"Round 0 PB-2" + §"Round 1 PB-13" + §"Round 4 PB-40".
