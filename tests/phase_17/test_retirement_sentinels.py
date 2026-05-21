"""Phase 17 retirement — sentinels that catch reintroduction of vacated surfaces.

Per ADR-0150 §amendment-3 (parent tree):

* `MetagraphView.step` MUST NOT grow a `version=` kwarg.
* No `(role, version)` discriminator may emerge on `KnowledgeLayer`
  or `MetagraphView`.
* `mindsos knowledge active-version` CLI verb MUST stay unregistered
  (Phase 14 PB-13 second-half dropped per PB-15 vacuum).
* ADR-0150 §amendment-3 must exist in the parent tree (with the
  Phase 14a / 15a / 15b sentinel skip-if-unreachable pattern).

If any of these tests regress, either (a) someone unwittingly
reintroduced active-version routing — re-read ADR-0150 §amendment-3
escape clause and surface concrete multi-version coexistence
evidence before flipping the lock, or (b) the lock is intentionally
being re-opened via §amendment-N — update this sentinel file
alongside the amendment.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindsos_cli.app import app
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.metagraph_view import MetagraphView


runner = CliRunner()


# ── §1 MetagraphView API-surface sentinels ─────────────────────────────


def test_step_has_no_version_kwarg() -> None:
    """ADR-0150 §amendment-3 lock — `step()` does not accept `version=`."""
    sig = inspect.signature(MetagraphView.step)
    assert "version" not in sig.parameters, (
        "ADR-0150 §amendment-3 vacates Phase 14 PB-15. "
        "`MetagraphView.step` MUST NOT grow a `version=` kwarg. "
        "If this regresses, see §amendment-3 escape clause before "
        "flipping the lock."
    )


def test_metagraph_view_has_no_active_version_method() -> None:
    """No `active_version` / `set_active_version` / `version_for_role` methods."""
    forbidden = ("active_version", "set_active_version", "version_for_role")
    for name in forbidden:
        assert not hasattr(MetagraphView, name), (
            f"ADR-0150 §amendment-3 lock — `MetagraphView.{name}` "
            f"is forbidden. There is no graph-layer active-version "
            f"state to surface."
        )


def test_knowledge_layer_has_no_active_version_state() -> None:
    """No `active_version` / `versions_by_role` / `_active_versions` on KL."""
    forbidden = (
        "active_version",
        "set_active_version",
        "versions_by_role",
        "_active_versions",
    )
    for name in forbidden:
        assert not hasattr(KnowledgeLayer, name), (
            f"ADR-0150 §amendment-3 lock — `KnowledgeLayer.{name}` "
            f"is forbidden. Version dispatch is IRI-string only."
        )


# ── §2 MetagraphView.versions_in_role shipped sentinel ─────────────────


def test_versions_in_role_method_exists() -> None:
    """Phase 17 retirement deliverable — the enumerator ships."""
    assert hasattr(MetagraphView, "versions_in_role"), (
        "Phase 17 retirement ships `MetagraphView.versions_in_role` "
        "per ADR-0150 §amendment-3. If this regresses, it was removed "
        "without ADR amendment — re-add."
    )
    sig = inspect.signature(MetagraphView.versions_in_role)
    # Method takes (self, role: str); no version=.
    assert "role" in sig.parameters
    assert "version" not in sig.parameters


# ── §3 CLI surface sentinels ───────────────────────────────────────────


def test_knowledge_versions_verb_registered() -> None:
    """The `versions` verb is registered under `mindsos knowledge`."""
    result = runner.invoke(app, ["knowledge", "versions", "--help"])
    assert result.exit_code == 0, (
        f"Phase 17 retirement ships `mindsos knowledge versions`. "
        f"Got exit_code={result.exit_code}; stdout: {result.stdout}"
    )


def test_knowledge_active_version_verb_NOT_registered() -> None:
    """PB-13 second-half — `active-version` dropped per PB-15 vacuum."""
    result = runner.invoke(app, ["knowledge", "active-version", "--help"])
    assert result.exit_code != 0, (
        "PB-13 second-half — `mindsos knowledge active-version` MUST "
        "stay unregistered. No graph-layer active-version state to "
        "surface; verb has nothing to query."
    )


# ── §4 ADR-0150 §amendment-3 presence (parent tree) ────────────────────
#
# Mirrors Phase 14a/15a/15b sentinel pattern: ADRs live in
# `/Layered Intelligence/docs/decisions/adr/` per Model C, NOT
# COPYd into the runtime container image. Skip-if-unreachable when
# running in-container.


_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR_DIR = _REPO_ROOT.parent / "docs" / "decisions" / "adr"


def _skip_if_adr_dir_missing() -> None:
    if not _ADR_DIR.exists():
        pytest.skip(
            f"ADR directory {_ADR_DIR!r} unreachable (in-container run); "
            f"ADRs live in parent project tree per Model C."
        )


def test_adr_0150_amendment_3_present() -> None:
    """ADR-0150 §amendment-3 — version-dispatch model lock."""
    _skip_if_adr_dir_missing()
    adr = _ADR_DIR / "0150-l2-knowledge-lifecycle.md"
    assert adr.exists(), f"ADR-0150 file missing: {adr}"
    content = adr.read_text(encoding="utf-8")
    assert "amendment-3 (Phase 17 retirement" in content, (
        "ADR-0150 §amendment-3 header missing — see Phase 17 "
        "retirement design log §R6 + §N5."
    )
    # Lock language anchors.
    assert "version-dispatch model lock" in content
    assert "Version is an IRI-string property only" in content
    assert "One graph per role per metagraph" in content
    # Escape clause.
    assert "Escape clause" in content
    assert "multi-version coexistence" in content
