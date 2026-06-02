# ADR-0010: KL does not import the server (I-S1); L3 accepts `SessionProtocol`

- **Status:** Accepted
- **Date:** 2026-04-22
- **Related:** ADR-0001, ADR-0002

## Context

The Server Layer (ADR-0001) sits *above* the Knowledge Layer in the dependency DAG, and above Capacity (L3). If KL or L3 were to import `mindsos_server` directly, we would:

- Create a circular dependency (server imports KL; KL imports server).
- Couple domain tests to server fixtures (or force KL to ship its own stub `Session`).
- Make KL uninstallable as a standalone library for downstream users who don't need auth.

But KL's write methods must accept a session-shaped argument so the server can enforce capabilities on the caller, and L3 needs the same seam for `CAN_WRITE_GLOBAL` checks.

## Decision

Two linked rules:

**I-S1: KL must not import `mindsos_server` at module load time.** KL's write-API methods accept a `Session` positionally (typed via a structural protocol if needed), treat it as opaque, and never instantiate one. A legacy-string overload is accepted with a `DeprecationWarning` to support the migration window.

**L3 consumes a `SessionProtocol`.** `mindsos_capacity` defines (or re-uses from `typing.Protocol`) a structural type that declares just the attributes the domain layer needs (`user_id`, `capabilities`). L3 methods that touch Global content gate on `CAN_WRITE_GLOBAL` without importing `mindsos_server` concretely.

Enforcement:

- **Test `tests_server/integration/test_layer_isolation.py`** scans the `mindsos_knowledge` package's modules and asserts no top-level `from mindsos_server` / `import mindsos_server` exists.
- **Invariant I13** (recorded in the developer guide and the `project_mindsos_l3_session_seam` memory) extends the same contract to L3.
- **Capability-string parity test** asserts that the capability constants L3 reads for its gating match the ones `mindsos_server.capabilities` exports, so a rename in one place can't silently break the other.

## Rationale

- **Dependency hygiene.** A clean DAG — Core → KL → Capacity → Intelligence → Mental Model, with Server above — is testable, debuggable, and documentable. A cycle would make all those properties fuzzy.
- **Duck-typed Session is enough.** Domain layers only need `user_id` and `capabilities`; a structural protocol captures that without pulling the concrete class.
- **Enforcement in CI, not convention.** The isolation test runs on every PR; humans forget, the test does not.
- **Legacy string overloads, not forever.** The deprecation shim buys a migration window; the target state (next major) is `Session`-only.

## Consequences

- KL and Capacity are still installable stand-alone (without `argon2-cffi`, without `mindsos_server`), which matters for downstream consumers.
- Tests that don't need auth use `Session.for_testing(user_id, is_admin=False)` — a server-shipped shim that doesn't touch SQLite (see ADR-0013).
- Any KL contributor who reaches for a server primitive is caught by the isolation test in CI.
- The capability strings are now a shared vocabulary; changes go through a coordinated PR across layers.

## Alternatives considered

1. **Move `Session` into Core.** Rejected — identity is a server-layer concern; Core should stay metagraph-only.
2. **A small shared "contracts" package holding `SessionProtocol` and capability strings.** Considered. Rejected for now — one more package to maintain, and `typing.Protocol` plus parity tests do the job. Revisit if a third consumer appears.
3. **Runtime isinstance check with a lazy import of `Session`.** Rejected — lazy imports as load-bearing correctness are brittle; a structural type is cleaner.

## Revisions

### amendment-1 (Phase 24 ship — 2026-05-22) — DAG enumeration extended for mindsos_admin (revised per Round 0 PB-Z22)

**Trigger:** Phase 24 introduces a `mindsos_server → mindsos_admin` import edge
(`mindsos_server/release.py::release_update` calls `mindsos_admin.audit_gate.run`)
AND requires `mindsos_admin → mindsos_server` imports (admin uses server's
`admin_tx`, `_require_or_audit`, `write_audit`, `Session`, capability constants).
`mindsos_admin/` is a top-level sibling package per ADR-0140 §amendment-1
admin-permanent-home — **a server-side curation toolkit**, NOT a domain layer
on the L1-L5 stack. The original §Decision §I-S1 speaks only to *domain layers*
(KL); the admin position needs explicit codification.

**Note on revision:** Phase 24 design log Round 0 PB-Z5(b) initially wrote
this amendment with `admin → server: FORBIDDEN`. PB-Z22 corrected the rule
after promotion.py impl needed server infrastructure (admin_tx + authz +
audit + Session) — the FORBIDDEN direction would have forced ~100 LOC of
helper duplication. The revised table below allows bi-directional
`admin ↔ server` (cycle-safe; no foundational server module imports admin).

**Amended decision — DAG rules:**

The original §Decision §I-S1 holds (domain layers MUST NOT import `mindsos_server`).
The following edge rules extend the layer-isolation contract:

| From → To | Status | Rationale |
|---|---|---|
| `mindsos_knowledge` → `mindsos_server` | **FORBIDDEN** | Original §I-S1; KL stays library-installable |
| `mindsos_knowledge` → `mindsos_admin` | **FORBIDDEN** | Same — KL stays self-contained from curation machinery |
| `mindsos_admin` → `mindsos_knowledge` | **ALLOWED** | Existing (Phase 15a importers + Phase 16 similarity); admin composes KL surfaces |
| `mindsos_admin` → `mindsos_server` | **ALLOWED** ⚠️ revised at Round 0 PB-Z22 | Admin is a server-side curation toolkit; uses server's `admin_tx` + `_require_or_audit` + `write_audit` + `Session` + capability constants |
| `mindsos_server` → `mindsos_admin` | **ALLOWED** | Server composes admin machinery (Phase 24: `release.py` calls `audit_gate.run` + `promotion`) |
| `mindsos_server` → `mindsos_knowledge` | **ALLOWED** | Existing; server may compose KL too |

**Cycle safety:** Bi-directional `admin ↔ server` is cycle-safe because
foundational server modules (`audit`, `authz`, `session`, `capabilities`,
`admin.py`, `users.py`) do NOT import `mindsos_admin`. Only
`mindsos_server.release` (NEW Phase 24) imports admin. Import graph at
module-load time:

```
server.release ─► admin.audit_gate ─► admin.similarity (no further)
              └─► admin.promotion ─► server.admin (admin_tx, foundational)
                                  └─► server.audit (foundational)
                                  └─► server.authz (foundational)
                                  └─► server.session (foundational)
                                  └─► server.capabilities (foundational)
```

No cycle: `admin.*` consumes server-foundational modules; only
`server.release` consumes admin. Server-foundational modules do not
consume admin.

**Enforcement:**

`tests/phase_24/test_import_isolation_phase24.py` scans top-level
`from X` / `import X` statements across the four packages and asserts
the table above. The test ships in the same commit as this amendment per
Phase 24 design log PB-Z10 same-commit-discipline lock.

**Rationale:**

The original Z5(b) rule "admin → server FORBIDDEN" was based on a
misreading of admin's position: admin was treated as a domain layer
(parallel to KL/Capacity), but it's a *server-side curation toolkit* per
ADR-0140 §am1 "admin operations live in `mindsos_admin/`, not
`mindsos_server/`" — operations that NEED server's transactional +
capability + audit infrastructure. Treating admin as forbidden-from-server
would have forced helper duplication (admin_tx, write_audit, etc.) with
ongoing drift risk. The revised rule recognizes admin's actual
architectural position.

KL stays library-installable without admin or server — both blocked. The
domain-layer isolation guarantee of ADR-0010 §I-S1 is preserved.

**Phase 24 design log:** `halvim_mindsos/confirmation_docs/PHASE_24_
DESIGN_LOG.md` §1 Round 0 PB-Z5(b) initial lock + PB-Z22 revision
+ §4 ADR delta (13 touches post-Round-0).

### amendment-2 (Phase 26a ship — 2026-05-23) — DAG enumeration extended for admin → core

**Trigger:** Phase 26a wires server-driven FalkorDB persistence per
ADR-0118 §amendment-3. The wiring introduces the first direct
`mindsos_admin → mindsos_core` import edge (admin needs `Client` from
`mindsos_core.persistence.client` to write pending/canonical Globals
to FalkorDB). The original §amendment-1 table did not enumerate the
admin → core direction explicitly; this amendment closes the gap
following the explicit-over-implicit discipline §amendment-1 PB-Z22
established.

**Amended decision — DAG rules (extended table):**

| From → To | Status | Rationale |
|---|---|---|
| `mindsos_knowledge` → `mindsos_server` | **FORBIDDEN** | Original §I-S1 |
| `mindsos_knowledge` → `mindsos_admin` | **FORBIDDEN** | KL stays self-contained from curation machinery |
| `mindsos_knowledge` → `mindsos_core` | **ALLOWED** | Foundational; KL composes Core types |
| `mindsos_admin` → `mindsos_knowledge` | **ALLOWED** | Existing (Phase 15a / 16) |
| `mindsos_admin` → `mindsos_server` | **ALLOWED** | Existing (Phase 24 §am1 PB-Z22) |
| `mindsos_admin` → `mindsos_core` | **ALLOWED** ⚠️ added at Phase 26a | Admin wires propose / release / importer to FalkorDB via `Client` from `mindsos_core.persistence.client`; transitively allowed already (admin → knowledge → core) but enumerated explicitly per PB-Z22 discipline |
| `mindsos_server` → `mindsos_admin` | **ALLOWED** | Existing (Phase 24) |
| `mindsos_server` → `mindsos_knowledge` | **ALLOWED** | Existing |
| `mindsos_server` → `mindsos_core` | **ALLOWED** | Foundational |

**Enforcement:**

`tests/phase_26a/test_import_isolation_phase26a.py` extends the
Phase 24/25 import-isolation parity scans to assert the new
`mindsos_admin → mindsos_core` edge is the only NEW edge introduced
at Phase 26a (i.e., KL → server stays forbidden; KL → admin stays
forbidden). AST-walk pattern from Phase 25 B-25-T1 hotfix used.

**Rationale:**

Phase 24 §am1 PB-Z22 corrected an initial `admin → server: FORBIDDEN`
pick after impl probe revealed the helper-duplication cost. Phase 26a
applies the same explicit-discipline preemptively: admin → core
is implicit-allowed via transitivity (admin → knowledge → core), but
the table is the canonical contract future maintainers consult, and
"implicit by transitivity" risks the same Phase 24 PB-Z5(b) misread
class. Enumerating explicitly costs ~3 lines of doc and ~10 lines of
test.

**Phase 26a design log:** `halvim_mindsos/confirmation_docs/PHASE_26a_
DESIGN_LOG.md` §1 R3-PB-4 (a) pick.
