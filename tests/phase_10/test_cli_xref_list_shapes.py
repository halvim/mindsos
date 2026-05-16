"""M24 + RR-6 — xref-list 10-field JSON + Rich table conditional columns."""

from __future__ import annotations

import json

from typer.testing import CliRunner

import mindsos_cli.commands.persistence as pers_mod
from mindsos_cli.commands.persistence import persistence_app


class _StubClient:
    def __init__(self, rows):
        self.rows_to_return = rows
        self.queries: list = []

    def run_query(self, q, p):
        self.queries.append((q, p))

        class R:
            def __init__(self, rs):
                self.rows = rs

        if "Metagraph {name" in q:
            return R([{"mid": "mg-1"}])
        if "XRef" in q:
            return R(self.rows_to_return)
        return R([])

    def close(self) -> None:
        pass


def _install(rows):
    pers_mod._build_client = lambda: _StubClient(rows)


def _cols(output: str) -> int:
    border = next((l for l in output.splitlines() if l.startswith("┏")), "")
    return border.count("┳") + 1 if border else 0


_BASE_ROW = {
    "xref_id": "x1", "source_id": "s1",
    "target_metagraph_id": "tmg", "target_role": "ont",
    "target_id": "t1", "ref_type": "SPECIALISES",
}


def test_json_emits_10_fields_unconditional() -> None:
    _install([dict(_BASE_ROW, target_stale=False, deprecated_at=None)])
    runner = CliRunner()
    r = runner.invoke(persistence_app, ["xref-list", "--metagraph", "m", "--json"])
    parsed = json.loads(r.output)
    assert set(parsed[0].keys()) == {
        "xref_id", "source_id", "target_metagraph_id", "target_role",
        "target_id", "ref_type", "target_stale", "deprecated_at",
    }


def test_default_state_renders_6_columns() -> None:
    _install([dict(_BASE_ROW, target_stale=False, deprecated_at=None)])
    runner = CliRunner()
    r = runner.invoke(persistence_app, ["xref-list", "--metagraph", "m"])
    assert _cols(r.output) == 6


def test_stale_true_grows_to_7() -> None:
    _install([dict(_BASE_ROW, target_stale=True, deprecated_at=None)])
    runner = CliRunner()
    r = runner.invoke(persistence_app, ["xref-list", "--metagraph", "m"])
    assert _cols(r.output) == 7


def test_deprecated_at_non_none_grows_to_7() -> None:
    _install([dict(_BASE_ROW, target_stale=False, deprecated_at="2026-05-15T12:00:00+00:00")])
    runner = CliRunner()
    r = runner.invoke(persistence_app, ["xref-list", "--metagraph", "m"])
    assert _cols(r.output) == 7


def test_both_non_default_grow_to_8() -> None:
    _install([dict(_BASE_ROW, target_stale=True, deprecated_at="2026-05-15T12:00:00+00:00")])
    runner = CliRunner()
    r = runner.invoke(persistence_app, ["xref-list", "--metagraph", "m"])
    assert _cols(r.output) == 8


def test_legacy_v3_row_defaults_in_json() -> None:
    """B-09-T7 carry — legacy 8-field rows produce 10-field JSON via defaults."""
    _install([dict(_BASE_ROW)])  # no target_stale, no deprecated_at
    runner = CliRunner()
    r = runner.invoke(persistence_app, ["xref-list", "--metagraph", "m", "--json"])
    parsed = json.loads(r.output)
    assert parsed[0]["target_stale"] is False
    assert parsed[0]["deprecated_at"] is None
    assert len(parsed[0]) == 8  # 6 base + 2 defaulted


def test_cypher_return_projects_10_fields() -> None:
    stub = _StubClient([])
    pers_mod._build_client = lambda: stub
    runner = CliRunner()
    runner.invoke(persistence_app, ["xref-list", "--metagraph", "m"])
    xref_q = next(q for q, _ in stub.queries if "XRef" in q)
    assert "x.target_stale AS target_stale" in xref_q
    assert "x.deprecated_at AS deprecated_at" in xref_q
