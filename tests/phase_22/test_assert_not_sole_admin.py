"""
Phase 22 R1 PB-7 — _assert_not_sole_admin helper.

ADR-0012 §Decision invariant: "Never zero admins, always at least one."
Helper counts ``actor_role='admin' AND disabled=0`` rows; raises
LastAdminError iff target IS the only active admin.
"""

from __future__ import annotations

import pytest

from mindsos_server.admin import _assert_not_sole_admin
from mindsos_server.errors import LastAdminError


class TestSoleAdminInvariant:
    def test_raises_when_target_is_sole_active_admin(self, seeded_admin):
        with pytest.raises(LastAdminError):
            _assert_not_sole_admin(seeded_admin, "admin")

    def test_does_not_raise_when_two_admins(self, seeded_two_admins):
        # Either admin can be demoted/disabled because the other remains.
        _assert_not_sole_admin(seeded_two_admins, "admin")
        _assert_not_sole_admin(seeded_two_admins, "admin2")

    def test_does_not_raise_for_non_admin_target(self, seeded_user):
        # Demoting a non-admin doesn't shrink active-admin count.
        _assert_not_sole_admin(seeded_user, "alice")

    def test_disabled_admin_does_not_count(
        self, seeded_disabled_admin_extra
    ):
        # admin2 is disabled; admin is the sole ACTIVE admin.
        # Disabling/deleting admin2 doesn't change the active count.
        _assert_not_sole_admin(seeded_disabled_admin_extra, "admin2")

    def test_raises_when_active_admin_target_with_disabled_peer(
        self, seeded_disabled_admin_extra
    ):
        # admin is the sole ACTIVE admin even though admin2 exists
        # (admin2 is disabled — doesn't count).
        with pytest.raises(LastAdminError):
            _assert_not_sole_admin(seeded_disabled_admin_extra, "admin")

    def test_target_user_id_on_error(self, seeded_admin):
        with pytest.raises(LastAdminError) as exc_info:
            _assert_not_sole_admin(seeded_admin, "admin")
        assert exc_info.value.target_user_id == "admin"
