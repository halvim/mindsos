"""Doctor self-test — phase=09 + 3-package version-string parity."""

from __future__ import annotations


def test_manifest_phase_is_09():
    from mindsos_cli.commands.doctor import _load_manifest, _repo_root

    manifest = _load_manifest(_repo_root() / "mindsos_cli" / "manifest.toml")
    assert manifest["mindsos"]["phase"] == "09"
    assert manifest["mindsos"]["version"] == "0.0.0+phase09"


def test_three_package_version_parity():
    """Phase 06 P62 A — mindsos_core + mindsos_cli + mindsos_instances all bump together."""
    import mindsos_cli
    import mindsos_core
    import mindsos_instances

    expected = "0.0.0+phase09"
    assert mindsos_core.__version__ == expected
    assert mindsos_cli.__version__ == expected
    assert mindsos_instances.__version__ == expected


def test_compose_image_tags_at_phase09():
    from pathlib import Path

    from mindsos_cli.commands.doctor import _repo_root

    compose = (_repo_root() / "docker-compose.yml").read_text()
    assert "mindsos:phase09-prod" in compose
    assert "mindsos:phase09-test" in compose
