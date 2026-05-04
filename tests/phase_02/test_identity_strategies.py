"""Phase 02 — `mindsos identity strategies` enumerates ADR-0131 implementations."""

from __future__ import annotations

import json


def test_strategies_lists_all_three_in_json(cli):
    proc = cli("identity", "strategies", "--json")
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    names = [s["name"] for s in payload["strategies"]]
    assert names == ["uuid4", "uuid5", "iri"]


def test_strategies_json_shape(cli):
    proc = cli("identity", "strategies", "--json")
    payload = json.loads(proc.stdout)
    for spec in payload["strategies"]:
        assert isinstance(spec["name"], str)
        assert isinstance(spec["class"], str)
        assert spec["class"].startswith("mindsos_core.")
        assert isinstance(spec["deterministic"], bool)
        assert isinstance(spec["ignores_content"], bool)
        assert isinstance(spec["description"], str) and spec["description"]


def test_strategies_human_text_mentions_uuid4_uuid5_iri(cli):
    proc = cli("identity", "strategies")
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "uuid4" in out
    assert "uuid5" in out
    assert "iri" in out
