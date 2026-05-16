"""Doctor self-test extensions for Phase 07."""

from __future__ import annotations

from mindsos_cli.commands.doctor import _COMPOSE_IMAGE_RE
from mindsos_cli.commands.confirm_phase import _CONFIRM_PHASE_TIMEOUT_SECONDS


def test_image_tag_regex_accepts_phase07() -> None:
    """Doctor _COMPOSE_IMAGE_RE matches `phase07-prod`/`phase07-test` in compose lines."""
    assert _COMPOSE_IMAGE_RE.search("    image: mindsos:phase07-prod") is not None
    assert _COMPOSE_IMAGE_RE.search("    image: mindsos:phase07-test") is not None


def test_confirm_phase_timeout_is_at_least_900s() -> None:
    """M12 — bump 600 → 900s for Phase 07 + integration tests.

    Phase 10 B-10-T7 — original literal ``== 900`` was broken by B-10-T4's
    bump to 1800s once the cumulative suite outgrew 900s. Per
    ``feedback_phase_baseline_literal_audit.md`` the fix is ``>= 900`` so
    the test enforces "no regression below the Phase 07 floor" while
    surviving future bumps. See ``feedback_confirm_phase_timeout.md`` for
    the bump history (600 → 900 → 1800).
    """
    assert _CONFIRM_PHASE_TIMEOUT_SECONDS >= 900


def test_manifest_falkordb_section_present() -> None:
    """The new [falkordb] section ships with host/port/graph keys."""
    try:
        import tomllib  # type: ignore  # Python 3.11+
    except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
        import tomli as tomllib  # type: ignore[no-redef]
    from pathlib import Path

    manifest = tomllib.loads(
        Path(__file__).resolve().parents[2]
        .joinpath("mindsos_cli", "manifest.toml")
        .read_text()
    )
    assert "falkordb" in manifest
    assert "host" in manifest["falkordb"]
    assert "port" in manifest["falkordb"]
    assert "graph" in manifest["falkordb"]
    # P15 A + P86 B — password/username explicitly excluded.
    assert "password" not in manifest["falkordb"]
    assert "username" not in manifest["falkordb"]


def test_manifest_phase_and_version_self_consistent() -> None:
    """B-08-T1 hotfix — dynamic check; survives future phase bumps.

    Original Phase 07 test hard-coded ``"07"`` / ``"0.0.0+phase07"``
    and broke at Phase 08 ship. Per ``feedback_state_version_audit_scope.md``
    precedent (B-05d-T1 fix on ``phase_04/test_state.py:243``), the
    fix is to read the manifest dynamically and assert
    self-consistency: phase ``NN`` ↔ version ``0.0.0+phaseNN``.
    """
    try:
        import tomllib  # type: ignore  # Python 3.11+
    except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
        import tomli as tomllib  # type: ignore[no-redef]
    from pathlib import Path
    manifest = tomllib.loads(
        Path(__file__).resolve().parents[2]
        .joinpath("mindsos_cli", "manifest.toml")
        .read_text()
    )
    phase = manifest["mindsos"]["phase"]
    version = manifest["mindsos"]["version"]
    assert version == f"0.0.0+phase{phase}", (
        f"manifest phase={phase!r} but version={version!r} — "
        f"self-consistency requires version=='0.0.0+phase{phase}'"
    )


def test_three_package_version_string_parity() -> None:
    """Phase 06 P62 A — cli + core + instances version strings match manifest.

    B-08-T1 hotfix — read the manifest dynamically instead of hard-
    coding the literal so future phase bumps don't break this test.
    """
    try:
        import tomllib  # type: ignore  # Python 3.11+
    except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
        import tomli as tomllib  # type: ignore[no-redef]
    from pathlib import Path
    import mindsos_cli, mindsos_core, mindsos_instances
    manifest = tomllib.loads(
        Path(__file__).resolve().parents[2]
        .joinpath("mindsos_cli", "manifest.toml")
        .read_text()
    )
    expected = manifest["mindsos"]["version"]
    assert mindsos_cli.__version__ == expected
    assert mindsos_core.__version__ == expected
    assert mindsos_instances.__version__ == expected
