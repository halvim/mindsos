---
title: Local copy of CAN_WRITE_GLOBAL + parity test (no upward import)
status: Accepted
date: 2026-04-22
layer: L3
aliases: [capacity-ADR-019]
---

# ADR-0078: Local copy of CAN_WRITE_GLOBAL + parity test

**Status:** Accepted

**Date:** 2026-04-22

## Context

L3 needs the capability string `"can_write_global"` to gate Global writes. The string's canonical definition lives in `mindsos_server.capabilities`. A direct import would make L3 depend on a layer *above* it, violating the Server Layer's invariant **I-S1** (no domain-layer import of the server package).

## Decision

`mindsos_capacity/capabilities.py` defines `CAN_WRITE_GLOBAL = "can_write_global"` as a local constant. A parity test (`tests_l3/unit/test_session_api.py::TestCapabilityParity`) `importorskip`s `mindsos_server.capabilities` and asserts the strings match; skipped cleanly when the server package isn't installed.

## Consequences

**Good:**
- Layer isolation is preserved.
- Drift is caught at test time, not runtime.

**Cost:**
- One extra file and an explicit test (both cheap).

## Alternatives considered

1. **Pull `CAN_WRITE_GLOBAL` from an environment variable** — rejected (still an import-time coupling, dressed up).
2. **Pass the constant in on `CapacityLayer` construction** — rejected (complicates the constructor for every consumer to work around a test-only concern).

## Enforced as

Invariant I13 ("no upward imports from `mindsos_server`"). Mirrors KL's analogous copy of the same constant.

## §amendment-1 (Phase 28 ship — 2026-05-24) — halvim UPPERCASE string-value convention + no skip-clean

**Trigger:** Phase 28 ports `mindsos_capacity.capabilities.CAN_WRITE_GLOBAL` into halvim. Direct verbatim port of the §Decision text would ship `CAN_WRITE_GLOBAL = "can_write_global"` (lowercase). Halvim's `mindsos_server/capabilities.py:44` defines `CAN_WRITE_GLOBAL = "CAN_WRITE_GLOBAL"` (UPPERCASE — established Phase 18 ship). Verbatim port would FAIL the parity test (`mindsos_capacity.CAN_WRITE_GLOBAL == mindsos_server.capabilities.CAN_WRITE_GLOBAL`), which is the whole point of this ADR.

**Amended behavior:**

* **Halvim's UPPERCASE value wins.** `mindsos_capacity.capabilities.CAN_WRITE_GLOBAL = "CAN_WRITE_GLOBAL"` ships at Phase 28. Server-side is unchanged. The constant *name* is the same; the *string value* is UPPERCASE in halvim vs lowercase in the original §Decision draft. This is a halvim-specific reconciliation, not a contract change.

* **`importorskip` dropped.** The §Decision text references `pytest.importorskip("mindsos_server.capabilities")` so the test skips when the server package isn't installed. Halvim is a monorepo — `mindsos_server` is ALWAYS installed in both prod + test images. The skip is dead-code in halvim. Phase 28's `tests/phase_28/test_capabilities_parity.py` drops `importorskip` and requires the server import; fails loud if missing. Mirrors halvim's existing `tests/phase_18/test_capabilities_parity.py` precedent.

**Coordinated changes at this amendment:**

* `mindsos_capacity/capabilities.py` (NEW at halvim) — `CAN_WRITE_GLOBAL = "CAN_WRITE_GLOBAL"` UPPERCASE.
* `tests/phase_28/test_capabilities_parity.py` (NEW) — strict equality assertion, no skip-clean.

**Out-of-scope:** the canonical (non-halvim) reference implementation in the parent tree may keep the lowercase convention; this amendment only locks halvim's port direction. Future re-convergence (if both repos merge) requires whichever side's string is older to migrate.

**Phase 28 design log:** `halvim_mindsos/confirmation_docs/PHASE_28_DESIGN_LOG.md` §"Round 0 PB-1" + §"Round 3 PB-37".
