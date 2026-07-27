"""nilm-scoped pytest config: register the ``integration`` marker so the
durable Falkor round-trip test doesn't warn when core's conftest (which owns
this marker) is out of scope."""


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: requires a live FalkorDB sidecar (skips if unreachable).",
    )
