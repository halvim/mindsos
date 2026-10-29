"""The mindsos_llm guide names only what exists.

``docs/plans/MINDSOS_LLM_PLAN.md`` item I-25, ruling R67. The guide is the
package's entry document; every test file, module path and linked document it
names must exist, or a reader following it finds nothing. Born red against a
fabricated name, so the check is known to fail when a name is missing.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "usage" / "runtime" / "mindsos-llm-guide.md"
TESTS = ROOT / "tests" / "llm_seam"

_TEST_NAME = re.compile(r"`(test_[a-z0-9_]+\.py)`")
_MODULE = re.compile(r"`((?:mindsos_[a-z_]+)(?:/[a-z0-9_]+)+\.py)`")
_LINK = re.compile(r"\]\(([^)#]+\.md)\)")


def missing_references(text: str, doc_dir: Path, root: Path, tests: Path):
    missing = []
    missing += [n for n in _TEST_NAME.findall(text) if not (tests / n).is_file()]
    missing += [m for m in _MODULE.findall(text) if not (root / m).is_file()]
    missing += [l for l in _LINK.findall(text) if not (doc_dir / l).resolve().is_file()]
    return sorted(set(missing))


def test_the_check_finds_a_fabricated_missing_name(tmp_path):
    text = ("see `test_no_such_guard.py`, `mindsos_llm/no_such_module.py` "
            "and [x](no_such_doc.md)")
    assert missing_references(text, tmp_path, ROOT, TESTS) == [
        "mindsos_llm/no_such_module.py", "no_such_doc.md", "test_no_such_guard.py"]


def test_the_guide_exists_and_names_only_what_exists():
    text = GUIDE.read_text(encoding="utf-8")
    assert _TEST_NAME.findall(text), "the guide names no test - the check would pass vacuously"
    assert missing_references(text, GUIDE.parent, ROOT, TESTS) == []
