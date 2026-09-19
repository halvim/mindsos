"""The claim inventory measures what it says it measures.

`tools/claim_inventory.py` is the doc-fix program's stopping rule: the program
ends when every class of checkable doc claim is guarded or owned. An inventory
that miscounts moves the finish line silently, so it is tested like a guard:

* its REGISTRY of guarded classes is checked BOTH ways -- every guard it names
  exists, and every doc-reading architecture guard is named (a new guard that
  forgets to register would otherwise leave its class counted as unguarded,
  or worse, a deleted guard would leave its class counted as guarded);
* its EXTRACTORS are run over a FABRICATED tree whose true and false claims
  are known, and must count them exactly;
* its PARTITION -- the one definition of "live" -- is pinned by its corners;
* on the real tree it must see a non-empty domain for every unguarded class,
  so it cannot pass vacuously.

It does NOT assert that `--check` passes on the real tree: that is the finish
line, and it is red until the program ends. Nor does it pin any real count --
a guard that reddens on every doc edit gets deleted.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_TOOL = _ROOT / "tools" / "claim_inventory.py"
_SELF = "tests/architecture/test_claim_inventory.py"

#: What makes an architecture test a DOC guard: it reads docs or
#: confirmation_docs, or names a markdown file. Measured 2026-09-19 on
#: 2d4c076: exactly the ten registered guards plus this file match.
_READS_DOCS = re.compile(r"[\"'/]docs[\"'/]|confirmation_docs|\.md[\"']")


def _load():
    spec = importlib.util.spec_from_file_location("claim_inventory_t", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


inv = _load()


# -- premise ---------------------------------------------------------------

def test_the_docs_tree_is_present_so_the_inventory_cannot_pass_vacuously():
    assert (_ROOT / "docs").is_dir(), "docs/ missing - the image did not copy it"
    rep = inv.build_report(_ROOT)
    assert rep["md_files_by_partition"].get(inv.LIVE, 0) > 0
    live = {r["class"] for r in rep["rows"] if r["partition"] == inv.LIVE and r["sites"]}
    missing = set(inv.UNGUARDED_CLASSES) - live
    assert not missing, f"no live sites found for {sorted(missing)} - an extractor is dead"


# -- registry, both ways ---------------------------------------------------

def test_every_registered_guard_exists():
    gone = [g for g, _ in inv.GUARDED.values() if not (_ROOT / g).is_file()]
    assert not gone, f"registry names guards that do not exist: {gone}"


def test_every_doc_reading_architecture_guard_is_registered():
    candidates = sorted((_ROOT / "tests" / "architecture").glob("test_*.py"))
    candidates.append(_ROOT / "tests" / "test_adr_status_consistency.py")
    reads_docs = {
        p.relative_to(_ROOT).as_posix()
        for p in candidates
        if p.is_file() and _READS_DOCS.search(p.read_text(encoding="utf-8"))
    }
    assert len(reads_docs) > 1, "the doc-guard census found nothing - its pattern is wrong"
    registered = {g for g, _ in inv.GUARDED.values()}
    unregistered = sorted(reads_docs - registered - {_SELF})
    assert not unregistered, (
        f"doc guards missing from claim_inventory.GUARDED: {unregistered} - "
        "register the class each one holds"
    )


# -- the one definition of "live" ------------------------------------------

@pytest.mark.parametrize("rel, part", [
    ("README.md", "live"),
    ("CLAUDE.md", "not-in-image"),
    ("RULES.md", "not-in-image"),
    ("docs/usage/x.md", "live"),
    ("docs/index.md", "live"),
    ("docs/_workbench/x.md", "scratch"),
    ("docs/changelog/x.md", "record"),
    ("docs/decisions/adr/0001-a.md", "adr-record"),
    ("docs/decisions/adr/README.md", "index"),
    ("docs/decisions/proposed.md", "index"),
    ("docs/decisions/summary/core.md", "index"),
    ("confirmation_docs/PHASE_46_CONFIRMED.md", "record"),
    ("confirmation_docs/PHASE_46_DESIGN_LOG.md", "record"),
    ("confirmation_docs/X_2026-09-12.md", "record"),
    ("confirmation_docs/CORE_RECONCILIATION_PLAN.md", "unclassified"),
    ("projects/wsd/ANALYSIS.md", "not-in-image"),
])
def test_partition_corners(rel, part):
    assert inv.partition(rel) == part


# -- extractors over a fabricated tree --------------------------------------

_PAGE = """\
---
title: page
---

# Heading is not prose

Plain prose that no class reaches.
See `mindsos_x/mod.py` and `mindsos_x/gone.py` and `tests/t_gone.py:12`.
Call `mindsos_x.mod.Thing.run` or `mindsos_x.mod.helper()` or `mindsos_x.Thing`.
Not `mindsos_x.mod.Thing.stop`, not `mindsos_x.nothere`.
Per ADR-0001 and ADR-0002.
Links: [ok](../decisions/adr/0001-a.md), [bad](missing.md), [web](https://x.org), [anchor](#h).

```
`mindsos_x/also_gone.py` inside a fence is still a claim
```

| a | b |
|---|---|
| cell prose | more |
"""


def _fabricate(root: Path) -> Path:
    (root / "mindsos_x").mkdir()
    (root / "mindsos_x" / "__init__.py").write_text("from .mod import Thing\n")
    (root / "mindsos_x" / "mod.py").write_text(
        "class Thing:\n    def run(self):\n        pass\n\ndef helper():\n    pass\n")
    (root / "docs" / "decisions" / "adr").mkdir(parents=True)
    (root / "docs" / "decisions" / "adr" / "0001-a.md").write_text("---\nstatus: Accepted\n---\n# ADR\n")
    (root / "docs" / "usage").mkdir()
    (root / "docs" / "usage" / "page.md").write_text(_PAGE)
    (root / "CLAUDE.md").write_text("Out of image: ADR-0002.\n")
    return root


def _rows(rep):
    return {(r["class"], r["partition"]): (r["sites"], r["false"], r["state"])
            for r in rep["rows"] if r["partition"] != "-"}


def test_fabricated_tree_is_counted_exactly(tmp_path):
    rep = inv.build_report(_fabricate(tmp_path))
    assert rep["mode"] == "walk"
    rows = _rows(rep)
    assert rows[("path-citation", "live")] == (4, 3, "UNGUARDED")
    assert rows[("python-symbol", "live")] == (5, 2, "UNGUARDED")
    assert rows[("adr-reference", "live")] == (2, 1, "UNGUARDED")
    assert rows[("relative-link", "live")] == (2, 1, "UNGUARDED")
    assert rows[("adr-reference", "not-in-image")] == (1, 1, "NOT-IN-IMAGE")
    false_symbols = sorted(s.text for s in rep["_sites"] if s.cls == "python-symbol" and s.false)
    assert false_symbols == ["mindsos_x.mod.Thing.stop", "mindsos_x.nothere"]
    # prose lines outside fences, headings, blanks, front-matter, table rules:
    # "Plain prose", See, Call, Not, Per, Links, 2 table rows = 8 lines;
    # See..Links carry a claim, so 3 are unreached.
    assert rep["residual"]["live"] == {"prose_lines": 8, "unreached": 3}


def test_check_is_open_while_anything_is_unguarded(tmp_path):
    root = _fabricate(tmp_path)
    for g, _ in inv.GUARDED.values():
        (root / g).parent.mkdir(parents=True, exist_ok=True)
        (root / g).write_text("")
    assert inv.main(["--root", str(root), "--check"]) == 1


def test_check_closes_when_every_class_is_guarded(tmp_path):
    for g, _ in inv.GUARDED.values():
        (tmp_path / g).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / g).write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.md").write_text("# Only a heading\n\nProse with no claim.\n")
    assert inv.main(["--root", str(tmp_path), "--check"]) == 0


def test_a_missing_guard_keeps_the_program_open(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.md").write_text("Prose.\n")
    rep = inv.build_report(tmp_path)
    assert {r["state"] for r in rep["rows"] if r["partition"] == "-"} == {"GUARD-MISSING"}
    assert inv.main(["--root", str(tmp_path), "--check"]) == 1
