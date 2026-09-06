"""
Tests for ``mindsos_server.capabilities`` — Phase 18 PB-4 + PB-12.

ADR-0041 parity test: this test STOPS auto-skipping at Phase 18 (the
server-side roster ships now). The KL-side parity comparison activates
at Phase 25 when ``mindsos_knowledge/capabilities.py`` lands; until
then, those subtests skip gracefully.
"""

from __future__ import annotations

import pytest

from mindsos_server.capabilities import (
    ADMIN_CAPS,
    ALL_CAPABILITIES,
    CAN_APPROVE_RELEASE,
    CAN_HARD_DELETE_ARCHIVED,
    CAN_INSTALL_SKILL,
    CAN_KILL_SESSION,
    CAN_MANAGE_USERS,
    CAN_PROMOTE,
    CAN_PROPOSE_MUTATION,
    CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY,
    CAN_READ_OTHER_LOCALS,
    CAN_UNINSTALL_SKILL,
    CAN_USE_LLM_CREDENTIAL,
    CAN_VIEW_AUDIT_LOG,
    CAN_WRITE_GLOBAL,
    USER_CAPS,
)


class TestRosterPerADR0002:
    """PB-12 — ADR-0002 roster (7 at Phase 18; +2 at Phase 24 per ADR-0002 §am2)."""

    def test_ten_capabilities(self) -> None:
        # Phase 24 ADR-0002 §am2 added CAN_PROPOSE_MUTATION +
        # CAN_APPROVE_RELEASE; roster 7 → 9. Phase 44 L2-39 added
        # CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY; roster 9 → 10.
        # Phase 50 ADR-0183 added CAN_INSTALL_SKILL +
        # CAN_UNINSTALL_SKILL; roster 10 → 12. ADR-0210 slice 2 added
        # CAN_USE_LLM_CREDENTIAL; roster 12 → 13.
        #
        # ⚠ This literal and the set below are the ONLY mechanical
        # inverse the roster has: measured 2026-09-06, NOTHING in this
        # repo parametrizes over ALL_CAPABILITIES, ADMIN_CAPS or
        # USER_CAPS, so a capability added without editing this file
        # adds no test and silences nothing — it simply is not checked.
        # Keep both, and keep them literal.
        assert len(ALL_CAPABILITIES) == 13

    def test_all_capabilities_listed(self) -> None:
        assert set(ALL_CAPABILITIES) == {
            CAN_READ_OTHER_LOCALS,
            CAN_WRITE_GLOBAL,
            CAN_PROMOTE,
            CAN_HARD_DELETE_ARCHIVED,
            CAN_KILL_SESSION,
            CAN_VIEW_AUDIT_LOG,
            CAN_MANAGE_USERS,
            CAN_PROPOSE_MUTATION,    # Phase 24 +ADR-0002 §am2
            CAN_APPROVE_RELEASE,     # Phase 24 +ADR-0002 §am2
            CAN_READ_OTHER_LOCAL_EPISODIC_MEMORY,  # Phase 44 +L2-39
            CAN_INSTALL_SKILL,       # Phase 50 +ADR-0183
            CAN_UNINSTALL_SKILL,     # Phase 50 +ADR-0183
            CAN_USE_LLM_CREDENTIAL,  # ADR-0210 slice 2
        }


class TestUpperCasingPerPB4:
    """PB-4 — all capability constants are UPPER_SNAKE; string value matches name."""

    def test_all_constants_upper_case(self) -> None:
        for cap in ALL_CAPABILITIES:
            assert cap == cap.upper(), f"capability not UPPER: {cap!r}"

    def test_string_value_matches_identifier(self) -> None:
        assert CAN_READ_OTHER_LOCALS == "CAN_READ_OTHER_LOCALS"
        assert CAN_WRITE_GLOBAL == "CAN_WRITE_GLOBAL"
        assert CAN_PROMOTE == "CAN_PROMOTE"
        assert CAN_HARD_DELETE_ARCHIVED == "CAN_HARD_DELETE_ARCHIVED"
        assert CAN_KILL_SESSION == "CAN_KILL_SESSION"
        assert CAN_VIEW_AUDIT_LOG == "CAN_VIEW_AUDIT_LOG"
        assert CAN_MANAGE_USERS == "CAN_MANAGE_USERS"


class TestBundlesPerPB12:
    """PB-12 — ADMIN_CAPS = all (12 at Phase 50).

    ``USER_CAPS`` was strictly empty from Phase 18 through Phase 50.
    **CORE-C2R1 (ADR-0002 §amendment-3)** adds the two skill-lifecycle
    capabilities so a user can install a Skill into their own realm
    (ADR-0150 §am-11). It grants no new write reach — a Global install
    still needs ``CAN_WRITE_GLOBAL`` at the ADR-0180 gate.
    """

    def test_user_caps_are_the_skill_lifecycle_pair(self) -> None:
        """⚠ No longer only the pair — ADR-0210 slice 2 added a third.

        The name is kept so the test id does not churn; the claim it
        actually carries is *``USER_CAPS`` is exactly this enumerated
        set*, which is what stops a capability drifting into every
        user's bundle unannounced.
        """
        assert USER_CAPS == frozenset(
            {CAN_INSTALL_SKILL, CAN_UNINSTALL_SKILL, CAN_USE_LLM_CREDENTIAL}
        )

    def test_user_caps_hold_no_write_or_admin_capability(self) -> None:
        """Every user-default capability acts on the holder's OWN realm.

        §am-3 used to phrase this as "install, and nothing else"; a
        third member makes that wording false without making the claim
        false. The claim is the one in this test's name: nothing here
        reaches another user or the Global scope.
        """
        assert CAN_WRITE_GLOBAL not in USER_CAPS
        assert not (
            USER_CAPS
            - {CAN_INSTALL_SKILL, CAN_UNINSTALL_SKILL, CAN_USE_LLM_CREDENTIAL}
        )

    def test_admin_caps_all(self) -> None:
        assert ADMIN_CAPS == frozenset(ALL_CAPABILITIES)

    def test_bundles_are_frozensets(self) -> None:
        assert isinstance(USER_CAPS, frozenset)
        assert isinstance(ADMIN_CAPS, frozenset)


class TestKLSideParity:
    """
    ADR-0041 parity comparison.

    KL ships ``mindsos_knowledge/capabilities.py`` at Phase 25 per
    ADR-0040 + ADR-0041; until then this subtest auto-skips on
    ``ImportError``. Once KL ships its constants, the test enforces
    that ``KL_CAPABILITIES ⊆ ALL_CAPABILITIES`` (KL ships only the four
    it consults; subset of the seven).
    """

    def test_kl_caps_subset_of_server_caps(self) -> None:
        try:
            from mindsos_knowledge.capabilities import KL_CAPABILITIES
        except ImportError:
            pytest.skip("mindsos_knowledge.capabilities not shipped yet (Phase 25)")

        kl_set = set(KL_CAPABILITIES)
        server_set = set(ALL_CAPABILITIES)
        assert kl_set.issubset(server_set), (
            f"KL capabilities not a subset of server roster: "
            f"missing in server = {kl_set - server_set}"
        )
