"""Doctor self-test extensions for Phase 07."""

from __future__ import annotations

from mindsos_cli.commands.doctor import _COMPOSE_IMAGE_RE
from mindsos_cli.commands.confirm_phase import _CONFIRM_PHASE_TIMEOUT_SECONDS


def test_image_tag_regex_accepts_phase07() -> None:
    """Doctor _COMPOSE_IMAGE_RE matches `phase07-prod`/`phase07-test` in compose lines."""
    assert _COMPOSE_IMAGE_RE.search("    image: mindsos:phase07-prod") is not None
    assert _COMPOSE_IMAGE_RE.search("    image: mindsos:phase07-test") is not None


def test_confirm_phase_timeout_is_900s() -> None:
    """M12 — bump 600 → 900s for Phase 07 + integration tests."""
    assert _CONFIRM_PHASE_TIMEOUT_SECONDS == 900


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


def test_manifest_phase_bumped_to_07() -> None:
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
    assert manifest["mindsos"]["phase"] == "07"
    assert manifest["mindsos"]["version"] == "0.0.0+phase07"


def test_three_package_version_string_parity() -> None:
    """Phase 06 P62 A — cli + core + instances version strings match manifest."""
    import mindsos_cli, mindsos_core, mindsos_instances
    assert mindsos_cli.__version__ == "0.0.0+phase07"
    assert mindsos_core.__version__ == "0.0.0+phase07"
    assert mindsos_instances.__version__ == "0.0.0+phase07"
