"""`mindsos version` — exit 0, structured fields present, JSON parses."""

from __future__ import annotations

import json


def test_version_exits_zero(cli):
    proc = cli("version")
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "mindsos" in out.lower()
    assert "git_sha" in out
    assert "image_hash" in out


def test_version_json_schema(cli):
    proc = cli("version", "--json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert {"version", "git_sha", "image_hash"} <= set(payload.keys())
    assert payload["version"], "version field empty"
