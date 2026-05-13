"""FalkorConfig env + manifest precedence tests (Phase 07 — P5 → P15 A + P67 A)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mindsos_core.config import (
    DEFAULT_GRAPH,
    DEFAULT_HOST,
    DEFAULT_PORT,
    FalkorConfig,
)


def test_defaults() -> None:
    c = FalkorConfig()
    assert c.host == DEFAULT_HOST
    assert c.port == DEFAULT_PORT
    assert c.graph == DEFAULT_GRAPH
    assert c.password is None


def test_from_env_reads_host_port_password(monkeypatch) -> None:
    monkeypatch.setenv("FALKORDB_HOST", "fb-host")
    monkeypatch.setenv("FALKORDB_PORT", "7000")
    monkeypatch.setenv("FALKORDB_PASSWORD", "sekret")
    c = FalkorConfig.from_env()
    assert c.host == "fb-host"
    assert c.port == 7000
    assert c.password == "sekret"
    # graph never comes from env per P86 B.
    assert c.graph == DEFAULT_GRAPH


def test_from_env_malformed_port_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("FALKORDB_PORT", "not-a-number")
    c = FalkorConfig.from_env()
    assert c.port == DEFAULT_PORT


def test_from_manifest_absent_file_returns_defaults(tmp_path) -> None:
    c = FalkorConfig.from_manifest(tmp_path / "missing.toml")
    assert c.host == DEFAULT_HOST
    assert c.port == DEFAULT_PORT
    assert c.graph == DEFAULT_GRAPH


def test_from_manifest_reads_section(tmp_path) -> None:
    p = tmp_path / "m.toml"
    p.write_text(
        '[falkordb]\nhost = "mfh"\nport = 9999\ngraph = "g"\n'
    )
    c = FalkorConfig.from_manifest(p)
    assert c.host == "mfh"
    assert c.port == 9999
    assert c.graph == "g"


def test_from_manifest_ignores_password_field(tmp_path) -> None:
    """P15 A — password is env-only; manifest password is silently ignored."""
    p = tmp_path / "m.toml"
    p.write_text(
        '[falkordb]\nhost = "h"\npassword = "should_not_be_here"\n'
    )
    c = FalkorConfig.from_manifest(p)
    assert c.password is None


def test_from_env_and_manifest_env_wins(tmp_path, monkeypatch) -> None:
    """P67 A — env-then-manifest-then-default per field."""
    p = tmp_path / "m.toml"
    p.write_text('[falkordb]\nhost = "manifest-host"\nport = 1234\ngraph = "mg"\n')
    monkeypatch.setenv("FALKORDB_HOST", "env-host")
    # Port: env unset, so manifest wins.
    monkeypatch.delenv("FALKORDB_PORT", raising=False)
    c = FalkorConfig.from_env_and_manifest(p)
    assert c.host == "env-host"
    assert c.port == 1234
    assert c.graph == "mg"


def test_from_env_and_manifest_graph_never_from_env(tmp_path, monkeypatch) -> None:
    """P86 B — graph comes from manifest or default; env has no influence."""
    p = tmp_path / "m.toml"
    p.write_text('[falkordb]\ngraph = "manifest-g"\n')
    monkeypatch.setenv("FALKORDB_GRAPH", "env-g")  # should be ignored
    c = FalkorConfig.from_env_and_manifest(p)
    assert c.graph == "manifest-g"
