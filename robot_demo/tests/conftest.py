"""Pytest config for tests_demo. Registers the ``integration`` marker so
the real-server (Falkor/argon2) tests are opt-in and don't warn."""

from __future__ import annotations


def pytest_configure(config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: real-server scenario (mindsos_server + argon2; "
        "Python 3.12 host). Deselect with -m 'not integration'.",
    )
