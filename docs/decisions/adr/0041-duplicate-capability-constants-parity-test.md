---
title: Duplicate capability string constants in KL with parity test
status: Accepted
date: 2026-04-22
layer: L2
aliases: [kl-ADR-004]
---

# ADR-0041: Duplicate capability string constants in KL with parity test

**Status:** Accepted

**Date:** 2026-04-22

## Context

KL consults four capability strings (`can_read_other_locals`, `can_write_global`, `can_promote`, `can_hard_delete_archived`) inside `session.has(...)` checks. The server defines those same four. The question was: share the constants via a tiny shared package, or duplicate them?

## Decision

Duplicate. `mindsos_knowledge/capabilities.py` ships the four KL-relevant constants plus a `KL_CAPABILITIES` tuple. A parity test in `tests/unit/knowledge/test_session_seam.py::test_capability_parity` asserts the KL set equals the intersection with the server's canonical set; it auto-skips when `mindsos_server` isn't installed.

## Consequences

**Good:**
- KL stays import-isolated from the server.
- No extra Python distribution to publish / version.

**Bad:**
- Two string literals for each capability in the codebase; drift risk capped by the parity test.

## Alternatives considered

1. **Pull from an environment variable or shared config module** — rejected because it's still import-time coupling.
2. **Pass the constant in on KL construction** — rejected because it complicates the constructor.

## Revisions

### amendment-1 (Phase 18 ship — 2026-05-21) — documentary: UPPER casing canonical; parity test stops auto-skipping at Phase 18

**Trigger:** This ADR's §Decision spells the four KL-relevant
capability constants in lower-case (`can_read_other_locals`,
`can_write_global`, `can_promote`, `can_hard_delete_archived`).
ADR-0002 §Decision spells them UPPER (`CAN_READ_OTHER_LOCALS`, etc.).
Phase 18 ships the canonical server-side roster; the parity test
asserts the KL set is a subset of the server roster — but only if
both use the same casing.

**Amended behavior:**

* **UPPER casing is canonical.** When `mindsos_knowledge/capabilities.py`
  ships at Phase 25 (this ADR's KL-side deliverable), the four KL
  constants MUST use UPPER casing to match the server-side roster
  shipped at Phase 18.
* **Parity test stops auto-skipping at Phase 18.** The test at
  `tests/phase_18/test_capabilities_parity.py` ships the server-side
  roster assertions unconditionally (no auto-skip). The KL-side
  subset comparison (`test_kl_caps_subset_of_server_caps`) auto-skips
  on `ImportError` until Phase 25 lands `mindsos_knowledge.capabilities`.

**Rationale:** ADR-0002 is the canonical roster source-of-truth (it
enumerates all seven caps; ADR-0041 enumerates only the four KL
consults). Aligning ADR-0041 to ADR-0002's casing keeps a single
casing convention across the codebase.

**Out-of-scope:** the KL-side constants themselves land at Phase 25
per ADR-0040 + this ADR's original §Decision.

See `halvim_mindsos/confirmation_docs/PHASE_18_DESIGN_LOG.md` §1
rounds 1-2 PB-4 for the casing decision.
