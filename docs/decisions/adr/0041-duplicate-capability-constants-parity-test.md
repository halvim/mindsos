---
title: Duplicate capability string constants in KL with parity test
status: Superseded
superseded_by: ADR-0138
date: 2026-04-22
layer: L2
aliases: [kl-ADR-004]
---

# ADR-0041: Duplicate capability string constants in KL with parity test

**Status:** Superseded by [ADR-0138](0138-kl-drops-write-api.md) (recorded 2026-09-16; see §Supersession below)

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

## Amendment — test citations not in this repo (2026-09-15, doc-fix #4)

**Amendment status:** Accepted. Records a fact; the decision above is unchanged, and the text above is left as written.

The test files below are cited above but no file by that name exists. They are names written when this ADR was drafted; the behaviour they stood for is accounted for here, one disposition each. Guarded by `tests/architecture/test_adr_test_citations.py`; gaps are tracked in `docs/plans/ADR_TEST_GAPS.md`.

- `tests/unit/knowledge/test_session_seam.py` — retired: the decision was superseded by ADR-0138 (see §Supersession below), so there is no KL constant set to compare. Filed as ATG-1, now `OUT`.

## Supersession (2026-09-16)

**Amendment status:** Accepted. Records why this ADR is Superseded; the text above is left as written.

The KL-side deliverable of this decision — `mindsos_knowledge/capabilities.py` with four duplicated capability constants and a `KL_CAPABILITIES` tuple — was never built in this repo (`git log --all -- mindsos_knowledge/capabilities.py` is empty; nothing in `mindsos_knowledge` ever imported it). Amendment-1 deferred it to Phase 25; Phase 25 shipped `SessionProtocol` (ADR-0040) without it.

The reason is [ADR-0138](0138-kl-drops-write-api.md): KL's write API was deleted, and with it every capability check KL made — "capability checks consolidate at the L3 invocation boundary". KL now consults no capability, so there is nothing for a duplicated constant set to serve. The pattern this ADR chose (a local copy of a server capability string, pinned by a parity test, no upward import) lives on one layer up in [ADR-0078](0078-l3-capability-local-copy.md): `mindsos_capacity/capabilities.py` and `tests/phase_28/test_capabilities_parity.py`.

Removed with this supersession: the `TestKLSideParity` subtest in `tests/phase_18/test_capabilities_parity.py`, which could only ever skip. Gap ATG-1 in `docs/plans/ADR_TEST_GAPS.md` is `OUT`.
