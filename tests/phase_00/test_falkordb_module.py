"""Confirms the FalkorDB graph module is loaded in the running falkordb sidecar.

By virtue of this test running at all (mindsos-test depends_on falkordb:
service_healthy), the compose stack is healthy. This test additionally verifies
the FalkorDB graph module is loaded — i.e. the sidecar is the FalkorDB image,
not vanilla Redis.
"""

from __future__ import annotations

import os

import redis


def _module_names(modules: list) -> list[str]:
    names: list[str] = []
    for m in modules:
        if not isinstance(m, list):
            continue
        for i in range(0, len(m) - 1, 2):
            key = m[i]
            if isinstance(key, bytes):
                key = key.decode()
            if key == "name":
                v = m[i + 1]
                if isinstance(v, bytes):
                    v = v.decode()
                names.append(str(v))
    return names


def test_falkordb_graph_module_loaded():
    host = os.environ.get("FALKORDB_HOST", "falkordb")
    port = int(os.environ.get("FALKORDB_PORT", "6379"))
    client = redis.Redis(host=host, port=port, socket_timeout=5)
    assert client.ping()
    modules = client.execute_command("MODULE", "LIST")
    assert isinstance(modules, list) and modules, "MODULE LIST returned no modules"
    names = _module_names(modules)
    assert "graph" in names, f"FalkorDB graph module not loaded; modules={names}"
