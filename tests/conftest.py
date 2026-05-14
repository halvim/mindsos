"""Project-wide pytest configuration (Phase 07 — NEW per P55 A).

Registers ``@pytest.mark.integration`` so tests that hit a live
FalkorDB sidecar can be filtered (``pytest -m 'not integration'`` for
unit-only runs) and don't surface as ``PytestUnknownMarkWarning``.
Phase 08 adds ``@pytest.mark.slow`` per RPB-12 B+C for opt-in 10K-node
streaming smoke tests.

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
    # Phase 08 RPB-12 B+C — opt-in 10K-node streaming smoke fixtures.
    # Default test run skips ``-m slow``; CI may opt in via env var.
    config.addinivalue_line(
        "markers",
        "slow: opt-in slow test (Phase 08 RPB-12 C — 10K-node "
        "streaming fixtures). Default test run excludes; opt in with "
        "`pytest -m slow`.",
    )
