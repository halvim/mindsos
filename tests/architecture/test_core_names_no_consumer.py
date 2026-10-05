"""Guard — core does not name its external consumer.

The external demo is built as a USER of MindsOS: it lives in its own
repository and installs core by tag (RULES §1). The dependency runs one way.
Core naming that consumer — in code, tests, docs or the live queue — is the
dependency running backwards, and it had crept into eleven core modules, a
test package, the ADRs and ``STATE.json`` before this guard existed.

What is scanned: every text file under the repository root that is present
where the test runs. In the gate image that is the ``mindsos_*`` packages,
``tests/``, ``tools/``, ``docs/`` and ``confirmation_docs/``; from a checkout
it is also the root documents and ``projects/``. ``STATE.json`` is scanned
with its ``recent[]`` ship log removed — a log, like git history, keeps what
happened.

Generic English is not the consumer's name: an *Architectural Decision
Record* and a *decision recorded below* stay legal. :data:`_PROBES` pins both
directions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SELF = Path(__file__).resolve()

PATTERN = re.compile(
    r"(?<!Architectural )(?<!Architecture )\bDecision Records?\b"
    r"|decision[-_]records?"
    r"|DECISION_RECORDS"
    r"|drdemo"
)

_SUFFIXES = {".py", ".md", ".json", ".toml", ".yml", ".yaml", ".cfg", ".ini", ".sh", ".txt", ".html"}
_SKIP_DIRS = {".git", "_scratch", "__pycache__", "node_modules", ".venv", "venv", "site",
              ".pytest_cache", ".mypy_cache"}
_MAX_BYTES = 2_000_000
_REQUIRED_ROOTS = ("mindsos_capacity", "mindsos_knowledge", "tests", "tools", "docs", "confirmation_docs")

_PROBES = {
    "a Decision Record prints it": True,
    "the Decision Records demo": True,
    "tests/decision_records/x.py": True,
    "feat/decision-records": True,
    "DECISION_RECORDS_V0_PLAN.md": True,
    "drdemo-store": True,
    "Architectural Decision Records — MindsOS": False,
    "ADR (Architecture Decision Record)": False,
    "in-vs-route decision recorded below": False,
    "a printed run record": False,
}


def _text(path: Path, root: Path = _ROOT) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.name == "STATE.json" and path.parent == root:
        state = json.loads(raw)
        state.pop("recent", None)
        return json.dumps(state, ensure_ascii=False)
    return raw


def _scan(root: Path = _ROOT):
    """The one walk both callers share: (files scanned, hits), a hit being
    (file, line number, text) of a line that names the consumer. What is
    reported as adjudicated and what is reported as a problem are the same
    list, so they cannot drift apart."""
    scanned, hits = [], []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(part in _SKIP_DIRS or part.endswith(".egg-info") for part in rel.parts):
            continue
        if not path.is_file() or path.suffix not in _SUFFIXES or path.resolve() == _SELF:
            continue
        if path.stat().st_size > _MAX_BYTES:
            continue
        scanned.append(rel)
        for n, line in enumerate(_text(path, root).splitlines(), 1):
            m = PATTERN.search(line)
            if m:
                hits.append((rel.as_posix(), n, line))
    return scanned, hits


def adjudicated_sites(root: Path) -> list[tuple[str, int]]:
    """Report mode (`tools/claim_inventory.py`, the emit contract): the
    `file:line` sites this guard adjudicated -- the lines that name the
    consumer. This guard only FORBIDS, so every site it has is a problem, and
    on a clean tree its honest report is EMPTY: every other line was scanned,
    not judged. The corners below prove the emitter is alive. A hit in
    ``STATE.json`` is emitted as line 1, because that file is judged with its
    ship log removed and so has no line numbers of its own."""
    _, hits = _scan(root)
    return [(rel, 1 if rel == "STATE.json" else n) for rel, n, _ in hits]


def test_core_names_no_external_consumer():
    _, hits = _scan()
    assert not hits, "core names its external consumer:\n" + "\n".join(
        f"{rel}:{n}: {line.strip()[:120]}" for rel, n, line in hits[:50]
    )


def test_the_scan_reaches_every_required_root():
    scanned, _ = _scan()
    tops = {rel.parts[0] for rel in scanned if len(rel.parts) > 1}
    missing = [r for r in _REQUIRED_ROOTS if (_ROOT / r).is_dir() and r not in tops]
    present = [r for r in _REQUIRED_ROOTS if (_ROOT / r).is_dir()]
    assert present, f"none of {_REQUIRED_ROOTS} exists under {_ROOT}"
    assert not missing, f"roots present but not scanned: {missing}"


def test_the_pattern_catches_the_name_and_spares_generic_english():
    wrong = {text: want for text, want in _PROBES.items() if bool(PATTERN.search(text)) != want}
    assert not wrong, wrong


# -- report mode -----------------------------------------------------------

def test_it_emits_the_naming_lines_and_only_those(tmp_path):
    """Line 1 is generic English, line 3 is plain: scanned, never judged."""
    (tmp_path / "mindsos_x").mkdir()
    (tmp_path / "mindsos_x" / "a.py").write_text(
        "# Architectural Decision Records - MindsOS\n"
        "# built for the Decision Records demo\n"
        "x = 1\n",
        encoding="utf-8",
    )
    assert adjudicated_sites(tmp_path) == [("mindsos_x/a.py", 2)]


def test_a_clean_tree_emits_nothing(tmp_path):
    (tmp_path / "mindsos_x").mkdir()
    (tmp_path / "mindsos_x" / "a.py").write_text("x = 1\n", encoding="utf-8")
    assert adjudicated_sites(tmp_path) == []
