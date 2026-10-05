"""No test may SKIP because a file under ``docs/`` could not be found.

The ADR sentinels written between Phase 11 and Phase 36 skip when the ADR
directory is missing — a branch written for "Model C", when ADRs lived in a
parent project outside this repo and the test image did not copy them. That
layout is gone: ``docs/`` is in the repo and the ``Dockerfile`` test stage
COPYs it. Every such skip branch can now only fire for one reason — the test
is looking in the wrong place — and a skip hides exactly that.

Measured 2026-09-16 at ``953993e``: 13 test modules carried the branch.
Eleven resolved the path correctly and never skipped. Two did not, and had
skipped on every run in every checkout and in the image:

- ``tests/phase_11/test_adr_0134_amendments.py`` (4 tests) looked one level
  ABOVE the repo root; its ``test_adr_0134_stays_proposed`` would also have
  failed, because ADR-0134 was accepted at Phase 15b.
- ``tests/phase_12/test_ref_types_and_roles.py`` (1 test), same path error.

So a missing doc is a FAILURE, never a skip. This guard walks the AST of every
module under ``tests/`` and refuses a ``pytest.skip(...)`` call or a
``pytest.mark.skipif(...)`` whose string arguments carry a phrasing of that
branch.

⚠ **FLOOR, NOT CEILING.** ``_PHRASES`` is hand-written from the phrasings
found in the wild; a skip worded some other way is missed. Phase 12's
"not reachable from" escaped the first grep for this class, which is how the
list was widened. Add a phrase when a new one is found.

⚠ **NARROW ON PURPOSE.** A first version also matched the bare words
"unreachable" and "in-container". It reddened on two LEGITIMATE skips —
``tests/_shared/falkordb_fixture.py`` ("FalkorDB unreachable at ...") and
``tests/phase_06/test_cli_instances.py`` (a Python-version skipif). Both are
pinned below as negative corners, so widening the list back fails here first.
"""

from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_TESTS = _ROOT / "tests"
_THIS = Path(__file__).resolve()

_PHRASES = (
    "model c",
    "not reachable from",
    "not copyed into test image",
    "not present in this environment",
)


def _strings(node: ast.AST) -> list[str]:
    out: list[str] = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            out.append(sub.value)
    return out


def _is_skip_call(call: ast.Call) -> bool:
    f = call.func
    if isinstance(f, ast.Attribute) and f.attr in ("skip", "skipif"):
        base = f.value
        if isinstance(base, ast.Name) and base.id == "pytest":
            return True
        if (
            isinstance(base, ast.Attribute)
            and base.attr == "mark"
            and isinstance(base.value, ast.Name)
            and base.value.id == "pytest"
        ):
            return True
    return False


def _judged(source: str):
    """Every call the guard JUDGES in one module: (line number, the phrases it
    carries) for each ``pytest.skip`` / ``pytest.mark.skipif`` call. The one
    walk both callers share, so what is reported as adjudicated and what can
    be reported as an offence cannot drift apart. Every other line of the
    module is scanned, never judged."""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and _is_skip_call(node):
            text = " ".join(
                s for part in [*node.args, *(k.value for k in node.keywords)]
                for s in _strings(part)
            ).lower()
            yield node.lineno, [p for p in _PHRASES if p in text]


def find_offences(source: str, name: str) -> list[str]:
    """Pure predicate over one module's source."""
    return [
        f"{name}:{lineno} skips on a missing doc ({hit[0]!r})"
        for lineno, hit in _judged(source)
        if hit
    ]


def _modules(root: Path):
    """(repo-relative name, source) of every module under ``tests/`` but this one."""
    for p in sorted((root / "tests").rglob("*.py")):
        if p.resolve() != _THIS:
            yield p.relative_to(root).as_posix(), p.read_text(encoding="utf-8")


def adjudicated_sites(root: Path) -> list[tuple[str, int]]:
    """Report mode (`tools/claim_inventory.py`, the emit contract): the
    `file:line` sites this guard adjudicated -- the line of each skip call in
    a test module, whichever way the judgement went (it skips on a missing doc,
    or it skips for some other reason). These are test files, so the sites add
    nothing to any live page's coverage."""
    return sorted({(name, lineno) for name, source in _modules(root) for lineno, _ in _judged(source)})


def test_the_premise_holds_docs_are_in_the_tree():
    assert (_ROOT / "docs" / "decisions" / "adr").is_dir(), (
        "docs/decisions/adr is missing — if the image stopped copying docs/, "
        "this guard's premise is false; fix the image, do not reintroduce skips"
    )
    modules = [p for p in _TESTS.rglob("*.py") if p.resolve() != _THIS]
    assert modules, "tests/ tree not found — the guard would pass vacuously"


def test_no_test_skips_because_a_doc_is_missing():
    offences: list[str] = []
    for name, source in _modules(_ROOT):
        offences += find_offences(source, name)
    assert not offences, (
        f"{len(offences)} skip(s) on a missing doc — make them failures:\n" + "\n".join(offences)
    )


def test_fabricated_modules_exercise_every_corner():
    skip = 'import pytest\ndef t():\n    pytest.skip(f"ADR dir {d} unreachable (in-container run); per Model C")\n'
    mark = 'import pytest\npytestmark = pytest.mark.skipif(True, reason="not reachable per Model C")\n'
    fail = 'import pytest\ndef t():\n    pytest.fail("ADR dir missing")\n'
    other = 'import pytest\ndef t():\n    pytest.skip("mkdocs not installed")\n'
    attr = 'import x\ndef t():\n    x.skip("not reachable from here")\n'
    falkor = 'import pytest\ndef t():\n    pytest.skip(f"FalkorDB unreachable at {h}:{p}: {e}")\n'
    sandbox = 'import pytest\npytestmark = pytest.mark.skipif(S, reason="CLI subprocess tests require Python 3.11+ (tomllib); in-container sandbox")\n'
    phase30 = 'import pytest\ndef t():\n    pytest.skip(f"ADR file {p} not COPYed into test image")\n'
    assert len(find_offences(skip, "a")) == 1
    assert len(find_offences(mark, "b")) == 1
    assert find_offences(fail, "c") == []
    assert find_offences(other, "d") == []
    assert find_offences(attr, "e") == []
    assert find_offences(falkor, "f") == []
    assert find_offences(sandbox, "g") == []
    assert len(find_offences(phase30, "h")) == 1


# -- report mode -----------------------------------------------------------

_MODULE = (
    "import pytest\n"
    "def a():\n"
    '    pytest.skip("ADR dir not reachable from here")\n'
    "def b():\n"
    '    pytest.skip("mkdocs not installed")\n'
    "def c():\n"
    '    pytest.fail("ADR dir missing")\n'
)


def test_it_emits_the_skip_calls_and_only_those(tmp_path):
    """Lines 3 and 5 are skip calls, judged one way each. Line 7 fails rather
    than skips, and the other lines are not calls: scanned, never judged."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_m.py").write_text(_MODULE, encoding="utf-8")
    assert adjudicated_sites(tmp_path) == [("tests/test_m.py", 3), ("tests/test_m.py", 5)]


def test_every_reported_offence_is_an_emitted_site(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_m.py").write_text(_MODULE, encoding="utf-8")
    emitted = {f"{f}:{n}" for f, n in adjudicated_sites(tmp_path)}
    offences = {o.split(" ", 1)[0] for o in find_offences(_MODULE, "tests/test_m.py")}
    assert offences == {"tests/test_m.py:3"} and offences <= emitted
