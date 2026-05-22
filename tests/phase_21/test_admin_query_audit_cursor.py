"""
Phase 21 cursor-pagination tests.

Verifies that ``after_id`` cursor (PB-10) returns only rows with
``id > after_id``, that ``ORDER BY id ASC`` is the default (PB-12),
and that ``since + after_id`` AND-together correctly (PB-20).

Per ADR-0013 §am2 + Phase 21 PB-10 + PB-12 + PB-20.
"""

from __future__ import annotations

from mindsos_server.admin import admin_query_audit


class TestCursorPagination:
    def test_after_id_excludes_lower_ids(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # after_id=3 → rows with id > 3 only.
        result = admin_query_audit(
            tmp_server_db, admin_session,
            after_id=seeded_audit_rows[2],
        )
        seeded_ids_in_result = {
            r.id for r in result if r.id in seeded_audit_rows
        }
        assert seeded_ids_in_result == set(seeded_audit_rows[3:])

    def test_after_id_inclusive_on_upper_bound(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # after_id=seeded[2] should INCLUDE id=seeded[3] (strict >).
        result = admin_query_audit(
            tmp_server_db, admin_session,
            after_id=seeded_audit_rows[2],
        )
        ids_in_result = {r.id for r in result}
        # First retained seeded id is seeded[3].
        assert seeded_audit_rows[3] in ids_in_result
        assert seeded_audit_rows[2] not in ids_in_result

    def test_after_id_then_limit_walks_page(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # Page 1: limit=3, after_id=None → ids[0..2].
        page1 = admin_query_audit(
            tmp_server_db, admin_session, limit=3,
        )
        seeded_p1 = [r.id for r in page1 if r.id in seeded_audit_rows]
        assert seeded_p1 == seeded_audit_rows[:3]

        # Page 2: limit=3, after_id=ids[2] → ids[3..5].
        page2 = admin_query_audit(
            tmp_server_db, admin_session,
            limit=3, after_id=page1[-1].id,
        )
        seeded_p2 = [r.id for r in page2 if r.id in seeded_audit_rows]
        # Note: the EVT_AUDIT_QUERY from page1's call has id=seeded[7]+1;
        # page2 includes that row + seeded[3..5]. Re-walking via
        # after_id=last_id of page1 = seeded[2] picks up seeded[3..5].
        assert set(seeded_p2).issuperset({
            seeded_audit_rows[3],
            seeded_audit_rows[4],
            seeded_audit_rows[5],
        })


class TestAscOrdering:
    def test_default_order_is_id_asc(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        result = admin_query_audit(tmp_server_db, admin_session)
        ids = [r.id for r in result]
        assert ids == sorted(ids)

    def test_ts_order_matches_id_order(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # Seeded rows have monotonic ts in the order they were inserted.
        # Reader returns id ASC → ts also ASC (modulo the EVT_AUDIT_QUERY
        # appended at the end which has _now_utc_iso → also after all
        # seeded ts).
        result = admin_query_audit(tmp_server_db, admin_session)
        tss = [r.ts for r in result]
        assert tss == sorted(tss)


class TestSinceAndAfterIdAnd:
    """PB-20: since + after_id AND together — both bounds active."""

    def test_since_and_after_id_combine(
        self, tmp_server_db, admin_session, seeded_audit_rows
    ) -> None:
        # since=03:00 (seed id 4..8) AND after_id=seed[4] (id > 5) →
        # seed[5..8] (ts >= 03:00 AND id > seed[4]) → seed ids 6, 7, 8.
        result = admin_query_audit(
            tmp_server_db, admin_session,
            since="2026-05-21T03:00:00.000Z",
            after_id=seeded_audit_rows[4],
        )
        seeded_ids_in_result = {
            r.id for r in result if r.id in seeded_audit_rows
        }
        assert seeded_ids_in_result == {
            seeded_audit_rows[5],
            seeded_audit_rows[6],
            seeded_audit_rows[7],
        }
