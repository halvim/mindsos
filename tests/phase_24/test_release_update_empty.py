"""release_update with no unshipped pending → EmptyReleaseError.

Per PB-21(a) — strict-fail; releases table stays semantically
"things that changed canonical." No row written.
"""

from __future__ import annotations

import pytest

from mindsos_admin.exceptions import EmptyReleaseError
from mindsos_server.release import release_update


def test_release_update_empty_pending_raises(
    seeded_admin, admin_session_both,
    canonical_global_mg, pending_global_mg,
):
    """No pending rows → EmptyReleaseError. No releases row written."""
    with pytest.raises(EmptyReleaseError):
        release_update(
            seeded_admin,
            session=admin_session_both,
            canonical_global_mg=canonical_global_mg,
            pending_global_mg=pending_global_mg,
        )

    # No row should be written.
    cur = seeded_admin.execute("SELECT COUNT(*) FROM releases")
    assert cur.fetchone()[0] == 0
