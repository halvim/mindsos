"""Phase 08 test-directory conftest.

Re-exports the ``falkor_client`` fixture from
``tests/_shared/falkordb_fixture.py`` so Phase 08 integration tests
(``@pytest.mark.integration``) can request the fixture by name without
each test file repeating the explicit ``from tests._shared.falkordb_fixture
import falkor_client`` line that Phase 07 used.

B-08-T2 hotfix — Phase 07 integration tests use the explicit-import
pattern (e.g. ``tests/phase_07/test_client_falkor_integration.py:11``);
Phase 08 tests were authored without the import and surfaced as 27
"fixture 'falkor_client' not found" errors on first in-container
run. Cleaner long-term solution: re-export once in this conftest so
new Phase 08+ test files inherit the fixture automatically.
"""

from __future__ import annotations

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401 — fixture re-export
