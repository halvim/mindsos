"""EmptyComparisonError from the audit gate → FAILED row, then BlockingFindingError.

ADR-0114 amendment-1 (Round 6) cites this file by name: "asserts
EmptyComparisonError → FAILED row with ``error_class="empty_comparison"``".
It was never written; filed as ATG-2 in ``docs/plans/ADR_TEST_GAPS.md``
by doc-fix #4 and written here under the cited name.

What ships (``mindsos_server/release.py``): the gate's
``EmptyComparisonError`` rolls back the release transaction, a second
transaction writes the FAILED row with ``error_class="empty_comparison"``,
and the caller receives ``BlockingFindingError(blocking_findings=[])``
chained ``from`` the original error (ADR-0144 §am2, PB-Z16(a)).

The error is produced by the REAL gate, not a patched one: node ids ending
in ``:`` have an empty IRI tail (Levenshtein undefined), and bare ontology
Class nodes have no parents/synonyms/frame-elements (structural undefined)
and no references (reference undefined) — all three components undefined.
The ``__cause__`` assertion is what proves this path ran rather than an
ordinary blocking similarity finding, which raises the same exception type.
"""

from __future__ import annotations

import json

import pytest

from mindsos_admin.exceptions import BlockingFindingError, EmptyComparisonError
from mindsos_server.audit import EVT_RELEASE_FAILED
from mindsos_server.release import release_update


def test_empty_comparison_writes_failed_row_then_raises_blocking(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg, inject_pending_node,
):
    inject_pending_node(pending_global_mg=pending_global_mg, node_id="empty-tail-a:")
    inject_pending_node(pending_global_mg=pending_global_mg, node_id="empty-tail-b:")

    with pytest.raises(BlockingFindingError) as excinfo:
        release_update(
            seeded_admin,
            session=admin_session_both,
            canonical_global_mg=canonical_global_mg,
            pending_global_mg=pending_global_mg,
        )

    assert isinstance(excinfo.value.__cause__, EmptyComparisonError), (
        "BlockingFindingError did not come from the empty-comparison path"
    )
    assert excinfo.value.blocking_findings == []

    rows = seeded_admin.execute(
        "SELECT release_id, manifest_json, audit_event_id "
        "FROM releases WHERE status = 'FAILED'"
    ).fetchall()
    assert len(rows) == 1
    release_id, manifest_str, event_id = rows[0]
    manifest = json.loads(manifest_str)
    assert manifest["error_class"] == "empty_comparison"
    assert manifest["included_mutation_ids"] == []
    assert manifest["mutations_attempted_count"] == 2

    assert seeded_admin.execute(
        "SELECT COUNT(*) FROM releases WHERE status = 'SHIPPED'"
    ).fetchone()[0] == 0

    event, extra_json = seeded_admin.execute(
        "SELECT event, extra_json FROM audit WHERE id = ?", (event_id,)
    ).fetchone()
    assert event == EVT_RELEASE_FAILED
    extra = json.loads(extra_json)
    assert extra["release_id"] == release_id
    assert extra["error_class"] == "empty_comparison"

    assert seeded_admin.execute(
        "SELECT COUNT(*) FROM pending_mutations WHERE shipped_in_release IS NULL"
    ).fetchone()[0] == 2
