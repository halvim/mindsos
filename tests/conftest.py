"""Project-wide pytest configuration (Phase 07 — NEW per P55 A).

Registers ``@pytest.mark.integration`` so tests that hit a live
FalkorDB sidecar can be filtered (``pytest -m 'not integration'`` for
unit-only runs) and don't surface as ``PytestUnknownMarkWarning``.

This is the first project-wide ``conftest.py``; Phase 02-06 ran
without one because no marker registration was needed.
"""

from __future__ import annotations


def pytest_configure(config):
    """Register markers used by Phase 07+ tests."""
    config.addinivalue_line(
        "markers",
        "integration: requires a live FalkorDB sidecar reachable at "
        "$FALKORDB_HOST:$FALKORDB_PORT (per the docker-compose "
        "`mindsos-test` profile).",
    )
