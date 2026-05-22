"""
Phase 21 time-window filter tests.

Verifies that ``since`` / ``until`` accept lenient ISO-8601 strings
(with or without .sss / Z) per PB-22, that both bounds are inclusive
(PB-11), that ms-boundary edge cases work, and that bad ISO-8601 input
raises ``ValueError``.

Per ADR-0013 §am2 + Phase 21 PB-11 + PB-22.
"""

from __future__ import annotations

import pytest

from mindsos_server.admin import admin_query_audit


class TestInclusiveBounds:
    def test_since_inclusive_lower_bound(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # ts 02:00:00.000 — seed id 3 EVT_LOGIN_FAILED at this exact ts.
        result = admin_query_audit(
            tmp_server_db, admin_session,
            since="2026-05-21T02:00:00.000Z",
        )
        seeded_ids_in_result = {
            r.id for r in result if r.id in seeded_audit_rows
        }
        # Rows 3..8 (ts >= 02:00).
        assert seeded_ids_in_result == set(seeded_audit_rows[2:])

    def test_until_inclusive_upper_bound(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        result = admin_query_audit(
            tmp_server_db, admin_session,
            until="2026-05-21T03:00:00.000Z",
        )
        seeded_ids_in_result = {
            r.id for r in result if r.id in seeded_audit_rows
        }
        # Rows 1..4 (ts <= 03:00).
        assert seeded_ids_in_result == set(seeded_audit_rows[:4])

    def test_window_both_sides(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        result = admin_query_audit(
            tmp_server_db, admin_session,
            since="2026-05-21T02:00:00.000Z",
            until="2026-05-21T04:00:00.000Z",
        )
        seeded_ids_in_result = {
            r.id for r in result if r.id in seeded_audit_rows
        }
        # Rows 3, 4, 5 (02:00, 03:00, 04:00 — all inclusive).
        assert seeded_ids_in_result == {
            seeded_audit_rows[2],
            seeded_audit_rows[3],
            seeded_audit_rows[4],
        }


class TestLenientISO8601:
    """PB-22 — accept lenient input (with or without ms / Z), normalize."""

    def test_without_milliseconds(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # Seeded row 1 has ts 2026-05-21T00:00:00.000Z. since='...00Z'
        # should normalize and match it inclusively.
        result = admin_query_audit(
            tmp_server_db, admin_session,
            since="2026-05-21T00:00:00Z",
            until="2026-05-21T00:00:00Z",
        )
        seeded_ids_in_result = {
            r.id for r in result if r.id in seeded_audit_rows
        }
        assert seeded_ids_in_result == {seeded_audit_rows[0]}

    def test_with_explicit_offset(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # '+00:00' should normalize same as 'Z'.
        result = admin_query_audit(
            tmp_server_db, admin_session,
            since="2026-05-21T00:00:00+00:00",
            until="2026-05-21T00:00:00.000Z",
        )
        seeded_ids_in_result = {
            r.id for r in result if r.id in seeded_audit_rows
        }
        assert seeded_ids_in_result == {seeded_audit_rows[0]}


class TestRejectsInvalidInput:
    def test_date_only_form_rejected(
        self, tmp_server_db, admin_session
    ) -> None:
        # Date-only form has no time component / no timezone — rejected
        # at v1 per PB-22.
        with pytest.raises(ValueError):
            admin_query_audit(
                tmp_server_db, admin_session,
                since="2026-05-21",
            )

    def test_unix_timestamp_rejected(
        self, tmp_server_db, admin_session
    ) -> None:
        with pytest.raises(ValueError):
            admin_query_audit(
                tmp_server_db, admin_session,
                since="1747800000",
            )

    def test_garbage_rejected(
        self, tmp_server_db, admin_session
    ) -> None:
        with pytest.raises(ValueError):
            admin_query_audit(
                tmp_server_db, admin_session,
                since="not a timestamp",
            )

    def test_no_timezone_rejected(
        self, tmp_server_db, admin_session
    ) -> None:
        # No Z, no offset — naive datetime; PB-22 requires explicit tz.
        with pytest.raises(ValueError):
            admin_query_audit(
                tmp_server_db, admin_session,
                since="2026-05-21T00:00:00",
            )
