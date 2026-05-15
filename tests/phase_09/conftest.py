"""Phase 09 conftest — re-exports falkor_client (RR-11; B-08-T2 carry).

Per Phase 09 RR-11 + the Phase 08 B-08-T2 hotfix precedent: integration
tests in tests/phase_09/ get the live :class:`FalkorClient` fixture
without per-file imports.
"""

from __future__ import annotations

from tests._shared.falkordb_fixture import falkor_client  # noqa: F401
