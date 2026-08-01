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

#: Invoke ``mindsos_admin.propose_for_promotion()`` per ADR-0118 +
#: ADR-0141 §am1. Phase 24 first consumer (declared + first consumer
#: same phase per ADR-0002 §am2). Required to write a row to
#: ``pending_mutations`` + the parallel FalkorDB ``mindsos_pending_
#: global_<role>`` graph.
CAN_PROPOSE_MUTATION = "CAN_PROPOSE_MUTATION"

#: Invoke ``mindsos_server.release_update()`` per ADR-0118 + ADR-0115.
#: Phase 24 first consumer (declared + first consumer same phase per
#: ADR-0002 §am2). At v1 semantic = "can ship a release" (no separate
#: approve step; ADR-0118 §Tradeoffs override-path-is-v2). v2 quorum-
#: approve extends semantic to actual approve-vs-ship distinction; cap
#: name forward-compatible without rename.
CAN_APPROVE_RELEASE = "CAN_APPROVE_RELEASE"

#: Admin read of ANOTHER user's Local ``episodic_memories`` role-graph,
#: distinct from the generic ``CAN_READ_OTHER_LOCALS`` (L2-39 / D-L2-23,
#: Phase 44). No v1 emit-site — registered ahead of the first capacity
#: that reads cross-user episodic memory (default-deny; admin opt-in).
CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY = "CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY"

#: Run the skill-bundle install driver (ADR-0183, Phase 50). Gates the
#: install *lifecycle* (preflight + installer entry points + record
#: write), not a write path — all graph writes travel through the
#: ADR-0180 ``make_writeable`` gate regardless.
#:
#: **CORE-C2R1 (ADR-0150 §am-11 / ADR-0002 §am-3):** held by ordinary
#: users, not only admins. ``scope`` decides the realm and the ADR-0180
#: gate still requires ``CAN_WRITE_GLOBAL`` for a Global install, so an
#: admin-only *Global* install is preserved while a user may install
#: into their own Local realm. This capability answers "may this
#: principal install a Skill at all" — worth being able to withhold,
#: since an installed Skill registers capacities that then execute.
CAN_INSTALL_SKILL = "CAN_INSTALL_SKILL"

#: Run the skill-bundle de-install driver (ADR-0183 §De-install, Phase
#: 50): reverse-dependency refuse + deprecate bundle-tagged content +
#: record flip. Same scope rules as ``CAN_INSTALL_SKILL`` — a Global
#: de-install still needs ``CAN_WRITE_GLOBAL``. Held by ordinary users
#: from CORE-C2R1: a principal who may install their own Skill may
#: remove it.
CAN_UNINSTALL_SKILL = "CAN_UNINSTALL_SKILL"


#: User default capability bundle. Empty from v1 through Phase 50 per
#: ADR-0002 + Phase 18 PB-12; **CORE-C2R1 (ADR-0002 §am-3) adds the two
#: skill-lifecycle capabilities** so a user can install a Skill into
#: their own Local realm. This is the first non-empty ``USER_CAPS``.
#:
#: It grants no new *write* reach: every graph write still passes the
#: ADR-0180 gate, which requires ``CAN_WRITE_GLOBAL`` for ``scope=
#: "global"``. A user therefore installs Local and an admin promotes.
#: Proposed-status caps from ADR-0137 add here at their Accept-flip
#: phase, not before.
USER_CAPS: frozenset[str] = frozenset(
    {
        CAN_INSTALL_SKILL,
        CAN_UNINSTALL_SKILL,
    }
)

#: Admin default capability bundle — all twelve per ADR-0002 §Decision +
#: §am2 (Phase 24 ship; +CAN_PROPOSE_MUTATION + CAN_APPROVE_RELEASE per
#: PB-23(a)) + Phase 44 (+CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY per
#: L2-39) + Phase 50 (+CAN_INSTALL_SKILL + CAN_UNINSTALL_SKILL per
#: ADR-0183). ``CAN_READ_PENDING_GLOBAL`` deferred to first direct-read
#: consumer phase per PB-23(a).
ADMIN_CAPS: frozenset[str] = frozenset(
    {
        CAN_READ_OTHER_LOCALS,
        CAN_WRITE_GLOBAL,
        CAN_PROMOTE,
        CAN_HARD_DELETE_ARCHIVED,
        CAN_KILL_SESSION,
        CAN_VIEW_AUDIT_LOG,
        CAN_MANAGE_USERS,
        CAN_PROPOSE_MUTATION,
        CAN_APPROVE_RELEASE,
        CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY,
        CAN_INSTALL_SKILL,
        CAN_UNINSTALL_SKILL,
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
    CAN_PROPOSE_MUTATION,
    CAN_APPROVE_RELEASE,
    CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY,
    CAN_INSTALL_SKILL,
    CAN_UNINSTALL_SKILL,
)
