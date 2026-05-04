"""`mindsos doctor --self-test` verifies the [ci.required_workflows] files."""

from __future__ import annotations

import json
from pathlib import Path

from mindsos_cli.commands.doctor import (
    _COMPOSE_IMAGE_RE,
    _yaml_top_keys,
)


def test_self_test_passes_when_workflows_present(cli):
    proc = cli("doctor", "--self-test", "--json")
    payload = json.loads(proc.stdout)
    # Either it passes (workflows present + manifest sha matches), or it fails
    # only on FalkorDB unreachability when run outside compose. Neither path
    # should fail on a missing-workflow check.
    failures = payload.get("failures", [])
    workflow_failures = [f for f in failures if "CI workflow" in f]
    assert workflow_failures == [], (
        f"unexpected workflow check failures: {workflow_failures}"
    )


def test_self_test_lists_workflows_in_report(cli):
    proc = cli("doctor", "--json")  # not --self-test
    payload = json.loads(proc.stdout)
    # Plain doctor mode only adds ci_required_workflows when self-test runs;
    # plain mode does not. Just sanity-check the report shape.
    assert "manifest" in payload
    assert "runtime" in payload


def test_self_test_fails_when_a_required_workflow_is_missing(
    cli, tmp_path: Path, repo_root, monkeypatch
):
    """Set MINDSOS_REPO_ROOT to a directory that has the manifest but no
    workflows. doctor --self-test must report the missing workflows."""
    fake_root = tmp_path / "fake_repo"
    fake_root.mkdir()
    # Copy just the manifest so doctor finds the [ci] section.
    src = repo_root / "mindsos_cli" / "manifest.toml"
    dst_dir = fake_root / "mindsos_cli"
    dst_dir.mkdir()
    (dst_dir / "manifest.toml").write_text(src.read_text())
    # No workflows in this fake root.

    env = {"MINDSOS_REPO_ROOT": str(fake_root)}
    # Inherit PATH so the `mindsos` script is found.
    import os
    env["PATH"] = os.environ.get("PATH", "")

    proc = cli("doctor", "--self-test", "--json", env=env)
    payload = json.loads(proc.stdout)
    failures = payload.get("failures", [])
    workflow_failures = [f for f in failures if "CI workflow" in f]
    assert workflow_failures, (
        f"expected workflow-missing failures, got failures={failures}"
    )
    assert proc.returncode != 0


# --- Fix J — _yaml_top_keys regex tolerates quoted YAML key forms ---


def test_yaml_top_keys_unquoted():
    body = "on:\n  push: x\njobs:\n  test: {}\n"
    assert _yaml_top_keys(body) >= {"on", "jobs"}


def test_yaml_top_keys_single_quoted():
    body = "'on':\n  push: x\n'jobs':\n  test: {}\n"
    assert _yaml_top_keys(body) >= {"on", "jobs"}


def test_yaml_top_keys_double_quoted():
    body = '"on":\n  push: x\n"jobs":\n  test: {}\n'
    assert _yaml_top_keys(body) >= {"on", "jobs"}


def test_yaml_top_keys_with_trailing_whitespace_before_colon():
    body = "on  :\n  push: x\njobs   :\n  test: {}\n"
    assert _yaml_top_keys(body) >= {"on", "jobs"}


def test_yaml_top_keys_does_not_match_indented_keys():
    body = "  on:\n    push: x\n  jobs:\n    test: {}\n"
    assert "on" not in _yaml_top_keys(body)
    assert "jobs" not in _yaml_top_keys(body)


# --- Fix E — compose image-tag drift check ---
# --- Fix ε — regex anchored to `^\s*image:` so comments don't false-positive.


def test_compose_image_re_matches_canonical_tags():
    body = (
        "services:\n"
        "  mindsos:\n"
        "    image: mindsos:phase01-prod\n"
        "  mindsos-test:\n"
        "    image: mindsos:phase01-test\n"
    )
    matches = [(m.group("phase"), m.group("stage")) for m in _COMPOSE_IMAGE_RE.finditer(body)]
    assert sorted(matches) == [("01", "prod"), ("01", "test")]


def test_compose_image_re_finds_drift():
    body = (
        "    image: mindsos:phase01-prod\n"
        "    image: mindsos:phase02-test\n"
    )
    matches = [(m.group("phase"), m.group("stage")) for m in _COMPOSE_IMAGE_RE.finditer(body)]
    assert sorted(matches) == [("01", "prod"), ("02", "test")]


def test_compose_image_re_ignores_other_tags():
    body = "    image: redis:7\n    image: falkordb/falkordb:v4.18.3\n"
    assert list(_COMPOSE_IMAGE_RE.finditer(body)) == []


def test_compose_image_re_ignores_full_line_comments():
    """Fix ε — a comment line referencing an old phase tag must not match."""
    body = (
        "# was: mindsos:phase00-prod (bumped on 2026-05-03)\n"
        "    image: mindsos:phase01-prod\n"
        "# old: mindsos:phase00-test\n"
        "    image: mindsos:phase01-test\n"
    )
    matches = [(m.group("phase"), m.group("stage")) for m in _COMPOSE_IMAGE_RE.finditer(body)]
    # Only the two real image: lines match; the comments don't.
    assert sorted(matches) == [("01", "prod"), ("01", "test")]


def test_compose_image_re_ignores_indented_comments():
    body = (
        "services:\n"
        "  # mindsos:phase00-prod  (legacy reference, do not use)\n"
        "  mindsos:\n"
        "    image: mindsos:phase01-prod\n"
    )
    matches = [(m.group("phase"), m.group("stage")) for m in _COMPOSE_IMAGE_RE.finditer(body)]
    assert matches == [("01", "prod")]


def test_compose_image_re_ignores_non_image_yaml_keys():
    """A `description:` or any other key with the literal must not match."""
    body = (
        "    description: was mindsos:phase00-prod before bump\n"
        "    image: mindsos:phase01-prod\n"
    )
    matches = [(m.group("phase"), m.group("stage")) for m in _COMPOSE_IMAGE_RE.finditer(body)]
    assert matches == [("01", "prod")]


def test_compose_image_re_requires_image_prefix_at_line_start():
    """`mindsos:phase01-prod` floating in body text (no `image:` prefix) doesn't match."""
    body = "Run mindsos:phase01-prod and you're done.\n"
    assert list(_COMPOSE_IMAGE_RE.finditer(body)) == []


def test_self_test_fails_on_compose_phase_drift(cli, tmp_path: Path, repo_root):
    """Build a fake repo where compose references a different phase number
    than the manifest, and assert self-test catches it."""
    fake_root = tmp_path / "fake_repo"
    fake_root.mkdir()
    # Manifest at phase 01.
    (fake_root / "mindsos_cli").mkdir()
    (fake_root / "mindsos_cli" / "manifest.toml").write_text(
        (repo_root / "mindsos_cli" / "manifest.toml").read_text()
    )
    # Compose claims phase 99 — drift.
    (fake_root / "docker-compose.yml").write_text(
        "services:\n"
        "  mindsos:\n"
        "    image: mindsos:phase99-prod\n"
        "  mindsos-test:\n"
        "    image: mindsos:phase99-test\n"
    )
    # Provide the workflow files so self-test doesn't also fail on those.
    wf = fake_root / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "phase-ci.yml").write_text("on:\n  push: {}\njobs:\n  test: {}\n")
    (wf / "release.yml").write_text("on:\n  push: {}\njobs:\n  release: {}\n")

    import os
    env = {
        "MINDSOS_REPO_ROOT": str(fake_root),
        "PATH": os.environ.get("PATH", ""),
        # Force falkordb ping to a non-resolvable host so we don't get hung up
        # on the unrelated falkordb-unreachable failure (it'll still appear in
        # `failures` but we filter for the compose-drift one specifically).
        "FALKORDB_HOST": "nowhere.invalid",
    }
    proc = cli("doctor", "--self-test", "--json", env=env)
    payload = json.loads(proc.stdout)
    failures = payload.get("failures", [])
    drift_failures = [f for f in failures if "compose image-tag drift" in f]
    assert len(drift_failures) == 2, (
        f"expected 2 drift failures (one per compose stage), got "
        f"{drift_failures} (all failures: {failures})"
    )
    # Both 99/prod and 99/test should be flagged.
    assert any("phase99-prod" in f for f in drift_failures)
    assert any("phase99-test" in f for f in drift_failures)


def test_self_test_passes_compose_check_on_current_repo(cli):
    """The shipped repo's compose tags align with the manifest's phase."""
    proc = cli("doctor", "--self-test", "--json")
    payload = json.loads(proc.stdout)
    failures = payload.get("failures", [])
    drift_failures = [f for f in failures if "compose image-tag drift" in f]
    assert drift_failures == [], (
        f"compose drift detected on current repo: {drift_failures}"
    )
