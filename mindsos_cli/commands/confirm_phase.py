"""`mindsos confirm-phase` — generates `confirmation_docs/PHASE_NN_CONFIRMED.md`.

Two modes:

  --init-notes phase-NN [--out PATH]
      Writes a notes file (copy of `confirmation_docs/_template_notes.md` with
      NN substituted) for the tester to fill.

  --phase NN --notes-file PATH [--out PATH] [--skip-tests]
      Reads the notes file, runs the cumulative test suite via Docker Compose,
      assembles every schema field, writes the confirmation doc.

Schema fields (PHASE_MAP §1):
  phase_number, phase_title, git_sha, image_build_hash, falkordb_version,
  automated_test_summary, tester_notes, timestamp_utc, mkdocs_pages_updated.

The tester is expected to review and possibly hand-edit the produced doc
before commit. CI does not validate the doc's structure beyond
exists-and-non-empty (PHASE_MAP §1, "Confirmation doc as artifact").
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import typer

# Re-use doctor's repo-root resolver to keep the rules in one place.
from mindsos_cli.commands.doctor import _load_manifest, _repo_root


_NOTES_TEMPLATE_RELPATH = "confirmation_docs/_template_notes.md"
_TEMPLATE_NOTES_TITLE_SECTION = "## phase_title"
_TEMPLATE_NOTES_NOTES_SECTION = "## tester_notes"


# ---------------------------------------------------------------------------
# init-notes
# ---------------------------------------------------------------------------


def _init_notes(phase_token: str, out_path: Path | None) -> Path:
    """Write a notes file for `phase-NN`. Returns the written path."""
    m = re.match(r"^phase-(\d{1,3})$", phase_token)
    if not m:
        typer.echo(
            f"--init-notes expects 'phase-NN' (e.g., phase-02), got: {phase_token!r}",
            err=True,
        )
        raise typer.Exit(code=2)
    nn = m.group(1).zfill(2)

    template = _repo_root() / _NOTES_TEMPLATE_RELPATH
    if not template.exists():
        typer.echo(
            f"notes template missing: {template}\n"
            "Phase 01 ships this file; if it's gone, restore it from git.",
            err=True,
        )
        raise typer.Exit(code=1)

    body = template.read_text()
    body = body.replace("Phase NN", f"Phase {nn}")
    out = out_path or Path.cwd() / f"notes-phase-{nn}.md"
    out.write_text(body)
    return out


# ---------------------------------------------------------------------------
# phase confirmation — schema field collectors
# ---------------------------------------------------------------------------


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_repo_root(), text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _docker_image_id(tag: str) -> str:
    try:
        out = subprocess.check_output(
            ["docker", "inspect", "--format={{.Id}}", tag],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown (image not built locally — run `docker compose build`)"


def _falkordb_pin(manifest: dict[str, Any]) -> str:
    fd = manifest["runtime"]["falkordb"]
    return f"{fd['image']}:{fd['tag']}@{fd['digest']}"


def _suite_hash(phase: str) -> str:
    """sha256 of the sorted concatenation of every tests/phase_NN/**/*.py file."""
    root = _repo_root() / "tests"
    if not root.exists():
        return "no-tests-dir"
    h = hashlib.sha256()
    files: list[Path] = []
    for nn in sorted(p.name for p in root.iterdir() if p.name.startswith("phase_")):
        files.extend(sorted((root / nn).rglob("*.py")))
    if not files:
        return "no-test-files"
    for f in files:
        h.update(f.relative_to(root).as_posix().encode())
        h.update(b"\0")
        h.update(f.read_bytes())
        h.update(b"\0")
    _ = phase  # signature parity; full hash is cumulative across all phases
    return f"sha256:{h.hexdigest()}"


def _run_tests() -> dict[str, Any]:
    """Shell out to `docker compose run --rm mindsos-test pytest tests/`.

    Returns a dict with count/passed/skipped/failed parsed from output, plus
    the raw text of the pytest summary line. If pytest-json-report is
    available, prefers its JSON. Failures still return a dict; the caller
    decides whether to exit non-zero.
    """
    # `--build` ensures the test image reflects the current code on disk.
    # Without it, the tester can edit a test file, forget to rebuild, and
    # confirm-phase silently records stale results in PHASE_NN_CONFIRMED.md.
    # The rebuild is layer-cached so the cost is small (typically <5s when
    # only test files changed).
    cmd = [
        "docker",
        "compose",
        "run",
        "--build",
        "--rm",
        "-T",
        "mindsos-test",
        "pytest",
        "tests/",
        "--tb=line",
        "-q",
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=_repo_root(),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return {
            "count": 0,
            "passed": 0,
            "skipped": 0,
            "failed": 0,
            "summary": f"docker invocation failed: {type(exc).__name__}: {exc}",
            "exit_code": -1,
        }

    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    summary_line = _last_pytest_summary_line(text)
    counts = _parse_pytest_summary(summary_line)
    return {
        **counts,
        "summary": summary_line,
        "exit_code": proc.returncode,
    }


_PYTEST_SUMMARY_RE = re.compile(r"^=+\s.*(passed|failed|error|skipped)", re.IGNORECASE)


def _last_pytest_summary_line(text: str) -> str:
    """Best-effort: return the final pytest summary line (e.g. '=== 4 passed in 0.5s ===')."""
    matches = [
        ln.strip()
        for ln in text.splitlines()
        if _PYTEST_SUMMARY_RE.match(ln.strip())
    ]
    return matches[-1] if matches else "no pytest summary line found"


_SUMMARY_KW_PATTERNS = (
    # (output-key, regex). Each kw is matched at most once. `error(s)?` is a
    # single alternation so a "3 errors" line isn't double-counted by separate
    # passes for `error` and `errors` (regression: prior version did this).
    ("passed", re.compile(r"(\d+)\s+passed\b")),
    ("skipped", re.compile(r"(\d+)\s+skipped\b")),
    ("failed", re.compile(r"(\d+)\s+failed\b")),
    ("errored", re.compile(r"(\d+)\s+errors?\b")),
)


def _parse_pytest_summary(line: str) -> dict[str, int]:
    """Parse counts from a pytest summary line like '4 passed, 1 skipped in 0.5s'.

    Returns a dict with keys: count, passed, skipped, failed. Pytest "errors"
    are folded into `failed` (errors are collection/setup failures and count
    against the green-suite criterion the same way).
    """
    counts = {"count": 0, "passed": 0, "skipped": 0, "failed": 0}
    for key, pattern in _SUMMARY_KW_PATTERNS:
        m = pattern.search(line)
        if not m:
            continue
        n = int(m.group(1))
        if key == "errored":
            counts["failed"] += n
        else:
            counts[key] = n
        counts["count"] += n
    return counts


def _git_changed_docs() -> list[str]:
    """`git diff --name-only main..HEAD -- 'docs/'` — empty list if anything fails."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "main..HEAD", "--", "docs/"],
            cwd=_repo_root(),
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return sorted(set(line.strip() for line in out.splitlines() if line.strip()))
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


# Sentinel section headings — ONLY these H2 labels start a new field. Any other
# `## …` heading the tester writes inside `tester_notes` (e.g. `## Background`)
# is treated as body content, not as a new field. Otherwise the tester's
# free-form notes silently truncate the moment they organise their thoughts.
_NOTES_FIELD_NAMES = ("phase_title", "tester_notes")


def _parse_notes(notes_path: Path) -> dict[str, str]:
    """Pull `phase_title` and `tester_notes` from a tester-filled notes file.

    A section ENDS only when a new line of the form `## <known-field>` is
    seen — non-sentinel H2s (e.g. `## Background` inside tester_notes) stay in
    the body. Empty/`…`-placeholder values become empty strings.
    """
    text = notes_path.read_text()
    sections: dict[str, list[str]] = {name: [] for name in _NOTES_FIELD_NAMES}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip()
            if heading in _NOTES_FIELD_NAMES:
                current = heading
                continue
            # Not a sentinel — fall through to body-append below.
        if current is not None:
            sections[current].append(line)

    def _clean(name: str) -> str:
        body = "\n".join(sections.get(name, [])).strip()
        # Strip instruction blockquotes (lines starting with '>'). Tester's
        # own content rarely starts with '>'; if it does, they can escape with
        # `\>`.
        body_lines = [ln for ln in body.splitlines() if not ln.startswith(">")]
        body = "\n".join(body_lines).strip()
        if body in ("", "…"):
            return ""
        return body

    return {name: _clean(name) for name in _NOTES_FIELD_NAMES}


def _assemble_doc(
    *,
    phase: str,
    phase_title: str,
    git_sha: str,
    image_build_hash: str,
    falkordb_pin: str,
    test_summary: dict[str, Any],
    tester_notes: str,
    timestamp_utc: str,
    mkdocs_pages_updated: list[str],
    suite_hash: str,
) -> str:
    """Render the confirmation doc body. Field order matches PHASE_MAP §1."""
    pages = (
        "\n".join(f"- {p}" for p in mkdocs_pages_updated)
        if mkdocs_pages_updated
        else "- (none — `git diff main..HEAD -- docs/` returned no changes)"
    )
    test_lines = [
        f"- count: {test_summary.get('count', 0)}",
        f"- passed: {test_summary.get('passed', 0)}",
        f"- skipped: {test_summary.get('skipped', 0)}",
        f"- failed: {test_summary.get('failed', 0)}",
        f"- suite_hash: {suite_hash}",
    ]
    if test_summary.get("summary"):
        test_lines.append(f"- pytest_summary: {test_summary['summary']}")
    test_block = "\n".join(test_lines)

    return f"""# Phase {phase} — Confirmation

> Generated by `mindsos confirm-phase --phase {phase} --notes-file …`. Tester
> may hand-edit before commit. CI's smoke check verifies "exists and
> non-empty", not field structure.

---

## phase_number

{phase}

## phase_title

{phase_title or '(missing — fill in notes file)'}

## git_sha

{git_sha}

## image_build_hash

{image_build_hash}

## falkordb_version

{falkordb_pin}

## automated_test_summary

{test_block}

## tester_notes

{tester_notes or '(missing — fill in notes file)'}

## timestamp_utc

{timestamp_utc}

## mkdocs_pages_updated

{pages}
"""


# ---------------------------------------------------------------------------
# Typer entry point
# ---------------------------------------------------------------------------


def confirm_phase(
    init_notes: str | None = typer.Option(
        None,
        "--init-notes",
        metavar="phase-NN",
        help="Write a notes-template file at notes-phase-NN.md (or --out path).",
    ),
    phase: str | None = typer.Option(
        None,
        "--phase",
        metavar="NN",
        help="Phase number (must match [mindsos] phase in manifest.toml).",
    ),
    notes_file: Path | None = typer.Option(
        None,
        "--notes-file",
        help="Tester-filled notes file (--init-notes' output, edited).",
    ),
    out: Path | None = typer.Option(
        None,
        "--out",
        help="Output path. Defaults to confirmation_docs/PHASE_NN_CONFIRMED.md "
        "(or notes-phase-NN.md for --init-notes).",
    ),
    skip_tests: bool = typer.Option(
        False,
        "--skip-tests",
        help="Emergency hand-write path: don't run docker compose; mark tests skipped.",
    ),
    json_out: bool = typer.Option(
        False,
        "--json",
        help="Emit a JSON summary on stdout instead of human text.",
    ),
) -> None:
    """Generate or initialise a phase confirmation document."""
    # Mode 1 — init notes.
    if init_notes is not None:
        if phase is not None or notes_file is not None:
            typer.echo(
                "--init-notes is mutually exclusive with --phase / --notes-file.",
                err=True,
            )
            raise typer.Exit(code=2)
        path = _init_notes(init_notes, out)
        if json_out:
            typer.echo(json.dumps({"mode": "init-notes", "path": str(path)}))
        else:
            typer.echo(f"Wrote notes template: {path}")
        return

    # Mode 2 — full confirmation.
    if phase is None or notes_file is None:
        typer.echo(
            "Either --init-notes or both --phase and --notes-file are required.",
            err=True,
        )
        raise typer.Exit(code=2)

    nn = phase.zfill(2)
    manifest = _load_manifest()
    expected = manifest["mindsos"]["phase"]
    if nn != expected:
        typer.echo(
            f"--phase {nn} mismatches manifest [mindsos] phase = {expected!r}. "
            "Bump the manifest first, or run from the correct branch.",
            err=True,
        )
        raise typer.Exit(code=2)

    if not notes_file.exists():
        typer.echo(f"notes file not found: {notes_file}", err=True)
        raise typer.Exit(code=2)

    notes = _parse_notes(notes_file)
    git_sha = _git_sha()
    falkordb_pin = _falkordb_pin(manifest)
    image_tag = f"mindsos:phase{nn}-prod"
    image_build_hash = _docker_image_id(image_tag)
    suite_hash = _suite_hash(nn)
    pages = _git_changed_docs()
    timestamp_utc = (
        _dt.datetime.now(_dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    if skip_tests:
        test_summary: dict[str, Any] = {
            "count": 0,
            "passed": 0,
            "skipped": 0,
            "failed": 0,
            "summary": "tests skipped (--skip-tests)",
            "exit_code": None,
        }
        tests_failed = False
    else:
        test_summary = _run_tests()
        tests_failed = (
            test_summary["exit_code"] not in (0, None)
            or test_summary["failed"] > 0
        )

    doc = _assemble_doc(
        phase=nn,
        phase_title=notes["phase_title"],
        git_sha=git_sha,
        image_build_hash=image_build_hash,
        falkordb_pin=falkordb_pin,
        test_summary=test_summary,
        tester_notes=notes["tester_notes"],
        timestamp_utc=timestamp_utc,
        mkdocs_pages_updated=pages,
        suite_hash=suite_hash,
    )

    target = out or _repo_root() / "confirmation_docs" / f"PHASE_{nn}_CONFIRMED.md"
    if target.exists():
        typer.echo(f"warning: overwriting existing {target}", err=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc)

    summary = {
        "mode": "confirm-phase",
        "phase": nn,
        "out": str(target),
        "tests_run": not skip_tests,
        "tests_failed": tests_failed,
        "git_sha": git_sha,
        "image_build_hash": image_build_hash,
        "test_summary": test_summary,
    }
    if json_out:
        typer.echo(json.dumps(summary, indent=2))
    else:
        typer.echo(f"Wrote {target}")
        if tests_failed:
            typer.echo(
                "WARNING: tests reported failures — review the doc and the "
                "test logs before tagging.",
                err=True,
            )

    if tests_failed:
        raise typer.Exit(code=1)
