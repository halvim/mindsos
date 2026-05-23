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
    CAN_KILL_SESSION,
    CAN_MANAGE_USERS,
    CAN_PROMOTE,
    CAN_PROPOSE_MUTATION,
    CAN_READ_OTHER_LOCALS,
    CAN_VIEW_AUDIT_LOG,
    CAN_WRITE_GLOBAL,
    USER_CAPS,
)


class TestRosterPerADR0002:
    """PB-12 — ADR-0002 roster (7 at Phase 18; +2 at Phase 24 per ADR-0002 §am2)."""

    def test_nine_capabilities(self) -> None:
        # Phase 24 ADR-0002 §am2 added CAN_PROPOSE_MUTATION +
        # CAN_APPROVE_RELEASE; roster 7 → 9. Earlier "seven" assertion
        # decayed at Phase 24 ship.
        assert len(ALL_CAPABILITIES) == 9

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
    """PB-12 — USER_CAPS strictly empty; ADMIN_CAPS = all (9 at Phase 24)."""

    def test_user_caps_empty(self) -> None:
        assert USER_CAPS == frozenset()

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
