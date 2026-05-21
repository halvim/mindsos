"""
Capability roster for the Server Layer.

The canonical seven capability constants per ADR-0002 + ADR-0010 +
ADR-0046, locked at Phase 18 per PB-4 (UPPER casing) + PB-12 (strict
ADR-0002 roster; Proposed-status caps from ADR-0118 / ADR-0137 wait
for their Accept-flip phase).

**Naming convention** (Phase 18 PB-4):

* Constants are UPPER_SNAKE per Python convention.
* String values match the constant name verbatim (no case difference
  between identifier and wire-string).
* The KL-side mirror at ``mindsos_knowledge/capabilities.py`` (Phase 25
  per ADR-0041) must use the same casing. Phase 18 ships
  ``tests/phase_18/test_capabilities_parity.py`` which stops auto-
  skipping at Phase 18 (server-side roster assertion ships now; the
  KL-side parity comparison activates when Phase 25 ships the KL
  mirror).

**Bundles** (PB-12):

* ``USER_CAPS`` — strictly empty in v1 per ADR-0002 §Decision
  ("reserved for future per-user grants"). Proposed-status user-default
  capabilities (e.g. ``CAN_REQUEST_PROMOTION`` from ADR-0137-Proposed)
  do NOT ship at Phase 18; they land at their Accept-flip phase.
* ``ADMIN_CAPS`` — all seven, immutable frozenset.

**Cross-references**:

* ADR-0002 §Decision — original seven-capability roster.
* ADR-0041 — KL ships the four it consults, parity test asserts subset.
* ADR-0046 — admin enforcement is capability-based, not role-string-based.
* ADR-0044 §amendment-1 — `user_id` charset (PB-7 imports the regex from KL).
* Phase 18 PB-4 / PB-5 / PB-12 — picks logged in
  ``confirmation_docs/PHASE_18_DESIGN_LOG.md``.
"""

#: Admin cross-user read via ``read_other_local()`` context manager (Phase 22).
CAN_READ_OTHER_LOCALS = "CAN_READ_OTHER_LOCALS"

#: Direct writes into Global-scope role graphs (rare; most Global writes go
#: through promote). Phase 24 first consumer.
CAN_WRITE_GLOBAL = "CAN_WRITE_GLOBAL"

#: Invoke ``similarity_report()`` and ``promote()``. Phase 24 first consumer.
CAN_PROMOTE = "CAN_PROMOTE"

#: ``hard_delete_user`` and similar destructive ops. Phase 22 first consumer.
CAN_HARD_DELETE_ARCHIVED = "CAN_HARD_DELETE_ARCHIVED"

#: ``admin_kill_session`` (evict another user's session). Phase 22 first consumer.
CAN_KILL_SESSION = "CAN_KILL_SESSION"

#: ``admin_query_audit``. Phase 21 first consumer.
CAN_VIEW_AUDIT_LOG = "CAN_VIEW_AUDIT_LOG"

#: Create / promote / demote / disable / enable / list users. Phase 18
#: enforces this on ``mindsos server user create / list / verify`` once
#: a Session caller exists (Phase 19+). Bootstrap path (Phase 18) bypasses
#: by design — see ADR-0012.
CAN_MANAGE_USERS = "CAN_MANAGE_USERS"


#: User default capability bundle — strictly empty in v1 per ADR-0002 +
#: Phase 18 PB-12. Reserved for future per-user grants; Proposed-status
#: caps from ADR-0118 / ADR-0137 add to this set at their Accept-flip
#: phase, not before.
USER_CAPS: frozenset[str] = frozenset()

#: Admin default capability bundle — all seven per ADR-0002 §Decision.
ADMIN_CAPS: frozenset[str] = frozenset(
    {
        CAN_READ_OTHER_LOCALS,
        CAN_WRITE_GLOBAL,
        CAN_PROMOTE,
        CAN_HARD_DELETE_ARCHIVED,
        CAN_KILL_SESSION,
        CAN_VIEW_AUDIT_LOG,
        CAN_MANAGE_USERS,
    }
)


#: Tuple of all capability constants in stable declaration order.
#: Convenience export for the parity test (Phase 18
#: ``test_capabilities_parity``) + future enumerations. NOT for runtime
#: gating — use the named constants directly.
ALL_CAPABILITIES: tuple[str, ...] = (
    CAN_READ_OTHER_LOCALS,
    CAN_WRITE_GLOBAL,
    CAN_PROMOTE,
    CAN_HARD_DELETE_ARCHIVED,
    CAN_KILL_SESSION,
    CAN_VIEW_AUDIT_LOG,
    CAN_MANAGE_USERS,
)
