"""`mindsos doctor` — runtime pin reporter and drift detector.

Without `--self-test`: prints pinned versions + actual runtime state (text or JSON).
With `--self-test`: compares runtime to canonical manifest.toml; exits non-zero on drift.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

import typer


# Tolerates quoted YAML keys (`'on':`, `"on":`) and trailing whitespace before
# the colon. Anchored to start-of-line via re.MULTILINE.
_YAML_TOPLEVEL_KEY_RE = re.compile(r"^(['\"]?)(?P<key>[a-z_]+)\1\s*:", re.MULTILINE)


def _yaml_top_keys(body: str) -> set[str]:
    """Return the set of top-level YAML key names, ignoring quoting style."""
    return {m.group("key") for m in _YAML_TOPLEVEL_KEY_RE.finditer(body)}


# Matches `mindsos:phase<N>-<stage>` ONLY when it appears as the value of an
# `image:` field — anchored to start-of-line + optional whitespace + `image:`.
# This deliberately excludes:
#   - YAML comments (whether full-line `# ...` or inline `key: val # ...`),
#   - documentation strings inside other fields (`description: was phase00`),
#   - any non-image YAML key that happens to contain the literal.
# Used by --self-test to detect phase-tag drift between manifest and compose.
_COMPOSE_IMAGE_RE = re.compile(
    r"^\s*image:\s*mindsos:phase(?P<phase>\d+)-(?P<stage>[a-z]+)\b",
    re.MULTILINE,
)

_REPO_ENV = "MINDSOS_REPO_ROOT"


def _repo_root() -> Path:
    """Return the repo root.

    Inside the container, MINDSOS_REPO_ROOT is set by the Dockerfile (= /app).
    Outside, walk up from this file until pyproject.toml is found.
    """
    if val := os.environ.get(_REPO_ENV):
        return Path(val)
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def _load_manifest() -> dict[str, Any]:
    """Read mindsos_cli/manifest.toml — canonical truth file."""
    manifest_path = _repo_root() / "mindsos_cli" / "manifest.toml"
    if not manifest_path.exists():
        # Fall back to package-relative path (when installed via pip).
        manifest_path = Path(__file__).parent.parent / "manifest.toml"
    with manifest_path.open("rb") as f:
        return tomllib.load(f)


def _ping_falkordb() -> dict[str, Any]:
    """Ping FalkorDB and return reachability + reported version.

    Uses the `redis` client (transitive dep of `falkordb`) for the ping itself
    so the check works even if falkordb-py changes its public API.
    """
    host = os.environ.get("FALKORDB_HOST", "falkordb")
    port = int(os.environ.get("FALKORDB_PORT", "6379"))
    try:
        import redis

        client = redis.Redis(host=host, port=port, socket_timeout=5)
        client.ping()
        version = "unknown"
        try:
            modules = client.execute_command("MODULE", "LIST")
        except Exception:
            modules = []
        if isinstance(modules, list):
            for module in modules:
                if not isinstance(module, list):
                    continue
                pairs: dict[str, Any] = {}
                for i in range(0, len(module) - 1, 2):
                    key = module[i]
                    val = module[i + 1]
                    if isinstance(key, bytes):
                        key = key.decode()
                    pairs[key] = val
                name = pairs.get("name")
                if isinstance(name, bytes):
                    name = name.decode()
                if name == "graph":
                    raw_ver = pairs.get("ver")
                    if isinstance(raw_ver, int):
                        # Redis-module version int format: MAJOR*10000 + MINOR*100 + PATCH.
                        major = raw_ver // 10000
                        minor = (raw_ver // 100) % 100
                        patch = raw_ver % 100
                        version = f"{major}.{minor}.{patch}"
                    elif raw_ver is not None:
                        version = str(raw_ver)
                    break
        return {"reachable": True, "host": host, "port": port, "version": version}
    except Exception as exc:
        return {
            "reachable": False,
            "host": host,
            "port": port,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _requirements_sha256() -> str | None:
    path = _repo_root() / "requirements.txt"
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def doctor(
    self_test: bool = typer.Option(
        False,
        "--self-test",
        help="Compare runtime state vs manifest; non-zero exit on drift.",
    ),
    json_out: bool = typer.Option(
        False, "--json", help="Emit JSON instead of human text."
    ),
) -> None:
    """Smoke-check the runtime; with --self-test, also verify pin parity."""
    manifest = _load_manifest()
    falkordb_pin = manifest["runtime"]["falkordb"]
    python_pin = manifest["runtime"]["python"]
    lockfile_pin = manifest["lockfile"]["requirements_txt_sha256"]

    runtime_python = ".".join(str(x) for x in sys.version_info[:3])
    runtime_req_sha = _requirements_sha256()
    falkordb_state = _ping_falkordb()

    report = {
        "manifest": {
            "falkordb": dict(falkordb_pin),
            "python": dict(python_pin),
            "requirements_txt_sha256": lockfile_pin,
        },
        "runtime": {
            "python_version": runtime_python,
            "requirements_txt_sha256": runtime_req_sha,
            "falkordb": falkordb_state,
        },
    }

    if not self_test:
        if json_out:
            typer.echo(json.dumps(report, indent=2))
        else:
            typer.echo(
                f"FalkorDB pin:   "
                f"{falkordb_pin['image']}:{falkordb_pin['tag']}@{falkordb_pin['digest']}"
            )
            typer.echo(
                f"Python pin:     "
                f"{python_pin['image']}:{python_pin['tag']}@{python_pin['digest']}"
            )
            typer.echo(f"Lockfile sha:   {lockfile_pin}")
            typer.echo(f"Runtime python: {runtime_python}")
            typer.echo(
                f"Runtime requirements.txt sha: {runtime_req_sha or 'not present'}"
            )
            if falkordb_state["reachable"]:
                typer.echo(
                    f"FalkorDB ping:  OK "
                    f"(host={falkordb_state['host']}:{falkordb_state['port']}, "
                    f"server-version={falkordb_state['version']})"
                )
            else:
                typer.echo(
                    f"FalkorDB ping:  UNREACHABLE "
                    f"(host={falkordb_state['host']}:{falkordb_state['port']}, "
                    f"error={falkordb_state['error']})",
                    err=True,
                )
        return

    # Self-test mode — compare runtime to manifest.
    failures: list[str] = []

    if runtime_python != python_pin["version"]:
        failures.append(
            f"python version drift: runtime={runtime_python} "
            f"manifest={python_pin['version']}"
        )

    if lockfile_pin == "PENDING_LOCK":
        failures.append(
            "lockfile not yet generated: run tools/lock.sh on the Linux box and "
            "paste the resulting sha256 into mindsos_cli/manifest.toml."
        )
    elif runtime_req_sha is None:
        failures.append("requirements.txt missing on disk")
    elif runtime_req_sha != lockfile_pin:
        failures.append(
            f"requirements.txt sha drift: runtime={runtime_req_sha} "
            f"manifest={lockfile_pin}"
        )

    if not falkordb_state["reachable"]:
        failures.append(f"falkordb unreachable: {falkordb_state['error']}")
    elif falkordb_state["version"] not in ("unknown", falkordb_pin["version"]):
        failures.append(
            f"falkordb version drift: runtime={falkordb_state['version']} "
            f"manifest={falkordb_pin['version']}"
        )

    # Phase 01+: required CI workflows must exist + non-empty + parse-shaped.
    # Only checked when manifest declares them (Phase 00 manifest has no [ci]).
    ci_section = manifest.get("ci") or {}
    required_workflows = ci_section.get("required_workflows", [])
    for relpath in required_workflows:
        path = _repo_root() / relpath
        if not path.exists():
            failures.append(f"required CI workflow missing: {relpath}")
            continue
        body = path.read_text()
        if not body.strip():
            failures.append(f"required CI workflow empty: {relpath}")
            continue
        # Shape-check: top-level `on:` AND `jobs:` keys must appear (regex
        # tolerates `on:`, `'on':`, `"on":`, and trailing whitespace).
        keys = _yaml_top_keys(body)
        missing = [k for k in ("on", "jobs") if k not in keys]
        if missing:
            failures.append(
                f"required CI workflow shape-broken: {relpath} "
                f"(missing top-level keys: {', '.join(missing)})"
            )
    if required_workflows:
        report["manifest"]["ci_required_workflows"] = list(required_workflows)

    # Phase 01+: compose image-tag parity. Every `mindsos:phaseNN-<stage>`
    # reference in docker-compose.yml must match the manifest's [mindsos] phase.
    # Catches the most common per-phase mistake (bumping manifest but leaving
    # compose tags pointing at the prior phase).
    expected_phase = manifest["mindsos"]["phase"]
    compose_path = _repo_root() / "docker-compose.yml"
    if compose_path.exists():
        compose_body = compose_path.read_text()
        bad: list[tuple[str, str]] = []  # (matched-phase, stage)
        for m in _COMPOSE_IMAGE_RE.finditer(compose_body):
            if m.group("phase") != expected_phase:
                bad.append((m.group("phase"), m.group("stage")))
        if bad:
            for phase, stage in bad:
                failures.append(
                    f"compose image-tag drift: docker-compose.yml references "
                    f"mindsos:phase{phase}-{stage}, but manifest [mindsos] phase "
                    f"= {expected_phase}. Bump every mindsos:phase*-* literal "
                    f"in compose to match."
                )
        report["manifest"]["expected_compose_image_phase"] = expected_phase

    result = {"ok": not failures, "failures": failures, **report}

    if json_out:
        typer.echo(json.dumps(result, indent=2))
    else:
        if failures:
            typer.echo("doctor --self-test: FAIL", err=True)
            for f in failures:
                typer.echo(f"  - {f}", err=True)
        else:
            typer.echo("doctor --self-test: OK")

    raise typer.Exit(code=1 if failures else 0)
