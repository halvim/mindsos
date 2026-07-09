"""`mindsos doctor` mindsos_cli import-package collision detector.

Guards the structural half of the CLI-redundancy fix: >1 installed
distribution providing the ``mindsos_cli`` import package (a vendored base
tree editable-installed alongside base — the Phase-50 ``No such command
'brain'`` bug). Unit-level: monkeypatches ``packages_distributions`` so it
needs no live FalkorDB or real second install.

See confirmation_docs/SKILL_REPO_CONTRACT.md.
"""

from __future__ import annotations

import importlib.metadata

import pytest

from mindsos_cli.commands.doctor import _cli_dist_collision


def _patch_providers(monkeypatch, mapping):
    monkeypatch.setattr(
        importlib.metadata, "packages_distributions", lambda: mapping
    )


def test_single_provider_is_not_a_collision(monkeypatch):
    _patch_providers(monkeypatch, {"mindsos_cli": ["mindsos-runtime"]})
    r = _cli_dist_collision()
    assert r["collision"] is False
    assert r["providers"] == ["mindsos-runtime"]


def test_two_providers_is_a_collision(monkeypatch):
    _patch_providers(
        monkeypatch, {"mindsos_cli": ["mindsos-runtime", "mindsos-arc"]}
    )
    r = _cli_dist_collision()
    assert r["collision"] is True
    # sorted + deduped
    assert r["providers"] == ["mindsos-arc", "mindsos-runtime"]


def test_duplicate_name_is_deduped_not_a_collision(monkeypatch):
    _patch_providers(
        monkeypatch, {"mindsos_cli": ["mindsos-runtime", "mindsos-runtime"]}
    )
    assert _cli_dist_collision()["collision"] is False


def test_zero_providers_is_not_a_collision(monkeypatch):
    # Bare source checkout on PYTHONPATH, no install.
    _patch_providers(monkeypatch, {})
    r = _cli_dist_collision()
    assert r["collision"] is False
    assert r["providers"] == []


def test_metadata_backend_error_is_reported_not_raised(monkeypatch):
    def _boom():
        raise RuntimeError("metadata backend down")

    monkeypatch.setattr(
        importlib.metadata, "packages_distributions", _boom
    )
    r = _cli_dist_collision()
    assert r["collision"] is False
    assert "RuntimeError" in (r["error"] or "")
