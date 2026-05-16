"""Doctor self-test — phase + 3-package version-string parity.

Phase 10 B-10-T7 — original Phase 09 literals (``"09"`` / ``"0.0.0+phase09"`` /
``"mindsos:phase09-prod"`` etc.) decayed when Phase 10 bumped the manifest,
the three ``__version__`` strings, and the compose image tags. Per
``feedback_phase_baseline_literal_audit.md`` the fix is to read the manifest
dynamically and assert SELF-CONSISTENCY rather than a frozen literal. This
preserves the original guard (manifest ↔ package ↔ compose stay in lockstep)
while surviving future phase bumps. The original Phase 09 literals are
captured in the test docstrings so the historical baseline is still discoverable.
"""

from __future__ import annotations


def _read_manifest():
    try:
        import tomllib  # type: ignore  # Python 3.11+
    except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
        import tomli as tomllib  # type: ignore[no-redef]
    from pathlib import Path
    return tomllib.loads(
        Path(__file__).resolve().parents[2]
        .joinpath("mindsos_cli", "manifest.toml")
        .read_text()
    )


def test_manifest_phase_and_version_self_consistent():
    """Manifest's phase and version stay in lockstep — phase ``NN`` ↔ version ``0.0.0+phaseNN``.

    Phase 09 historical baseline (now dynamic per B-10-T7): phase=="09",
    version=="0.0.0+phase09". See ``feedback_phase_baseline_literal_audit.md``.
    """
    from mindsos_cli.commands.doctor import _load_manifest

    manifest = _load_manifest()
    phase = manifest["mindsos"]["phase"]
    version = manifest["mindsos"]["version"]
    assert version == f"0.0.0+phase{phase}", (
        f"manifest phase={phase!r} but version={version!r} — "
        f"self-consistency requires version=='0.0.0+phase{phase}'"
    )


def test_three_package_version_parity():
    """Phase 06 P62 A — mindsos_core + mindsos_cli + mindsos_instances all bump together.

    Phase 09 historical baseline (now dynamic per B-10-T7): "0.0.0+phase09".
    """
    import mindsos_cli
    import mindsos_core
    import mindsos_instances

    expected = _read_manifest()["mindsos"]["version"]
    assert mindsos_core.__version__ == expected
    assert mindsos_cli.__version__ == expected
    assert mindsos_instances.__version__ == expected


def test_compose_image_tags_in_lockstep_with_manifest():
    """docker-compose.yml image tags reference the manifest's phase string.

    Phase 09 historical baseline (now dynamic per B-10-T7):
    ``mindsos:phase09-prod`` + ``mindsos:phase09-test`` lines.
    """
    from mindsos_cli.commands.doctor import _repo_root

    phase = _read_manifest()["mindsos"]["phase"]
    compose = (_repo_root() / "docker-compose.yml").read_text()
    assert f"mindsos:phase{phase}-prod" in compose
    assert f"mindsos:phase{phase}-test" in compose
