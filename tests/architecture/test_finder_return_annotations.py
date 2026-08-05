"""Guard — anything answering "is there a route?" is annotated ``FindVerdict``.

CORE-C3R1 replaced ``PipelineNotFoundError`` with a returned ``FindVerdict``
(shim **S4**). The conversion was executed by replacing the literal string
``"    ) -> Pipeline:"`` — a four-space *method* indent — so the three
``Finder.find`` methods were converted and the one module-level function,
``find_pipeline``, was not. It shipped at ``ae63aa2`` annotated ``-> Pipeline``
while returning a ``FindVerdict``: the **public** entry point, what five brains
were told to call, and the SubMind arbiter's ``plan_fn``. Nothing caught it —
the gate runs no type checker.

That is the fifth instance of one lesson in this lane: *size and verify a change
by meaning, not by string match, and verify by a different method than the one
you edited with.* This guard is that different method.

**Why it is not a list of three names.** A guard pinned to ``BFSFinder.find``,
``ConjunctionFinder.find`` and ``find_pipeline`` would be green forever the
moment those three are correct, and a fourth finder would be unguarded by
construction — the "green guard that cannot fail" ``RULES.md`` §9 forbids. The
rules below are *structural*, so a new finder is covered the day it is written:

  R1  A function that constructs and returns a ``FindVerdict`` must be
      annotated ``FindVerdict``.
  R2  A function that returns the result of ``<X>Finder(...).find(...)`` must
      be annotated ``FindVerdict`` — this is exactly ``find_pipeline``.
  R3  A method named ``find`` on ``Finder`` or any subclass of it must be
      annotated ``FindVerdict``, including the abstract base, whose body
      constructs nothing.

:func:`test_guard_flags_a_wrong_annotation` feeds the checker a fabricated
module carrying the exact defect that shipped and asserts it goes RED, per
``RULES.md`` §9: *"write a test that makes it go RED — assert the failure
behaviour, not only the passing state."*
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

#: Package roots scanned. `projects/` and the brains are consumers; they may
#: hold their own verdict types and are not held to core's annotation.
_PACKAGES = (
    "mindsos_admin",
    "mindsos_capacity",
    "mindsos_cli",
    "mindsos_core",
    "mindsos_instances",
    "mindsos_intelligence",
    "mindsos_knowledge",
    "mindsos_server",
)

_VERDICT = "FindVerdict"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "mindsos_capacity").is_dir():
            return parent
    raise AssertionError("repo root not found from %s" % here)


def _annotation_name(node: ast.AST | None) -> str | None:
    """The annotation as a bare name, unwrapping a forward reference."""
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.strip().strip('"').strip("'")
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _own_returns(fn: ast.AST) -> list[ast.Return]:
    """``return`` statements belonging to ``fn`` itself, not to a nested def."""
    found: list[ast.Return] = []
    for node in ast.iter_child_nodes(fn):
        _walk_returns(node, found)
    return found


def _walk_returns(node: ast.AST, out: list[ast.Return]) -> None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        return
    if isinstance(node, ast.Return):
        out.append(node)
    for child in ast.iter_child_nodes(node):
        _walk_returns(child, out)


def _constructs_verdict(ret: ast.Return) -> bool:
    """R1 — ``return FindVerdict(...)``."""
    val = ret.value
    return (
        isinstance(val, ast.Call)
        and isinstance(val.func, ast.Name)
        and val.func.id == _VERDICT
    )


def _delegates_to_finder(ret: ast.Return) -> bool:
    """R2 — ``return SomeFinder(...).find(...)``."""
    val = ret.value
    if not (isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute)):
        return False
    if val.func.attr != "find":
        return False
    recv = val.func.value
    if isinstance(recv, ast.Call) and isinstance(recv.func, ast.Name):
        return recv.func.id.endswith("Finder")
    if isinstance(recv, ast.Name):
        return recv.id.endswith("Finder")
    return False


def _is_finder_find(cls: ast.ClassDef, fn: ast.AST) -> bool:
    """R3 — ``find`` on ``Finder`` or a subclass."""
    if getattr(fn, "name", None) != "find":
        return False
    if cls.name == "Finder":
        return True
    for base in cls.bases:
        if isinstance(base, ast.Name) and base.id.endswith("Finder"):
            return True
        if isinstance(base, ast.Attribute) and base.attr.endswith("Finder"):
            return True
    return False


def check_source(source: str, where: str) -> tuple[list[str], int]:
    """Return ``(violations, functions_checked)`` for one module's source."""
    tree = ast.parse(source)
    violations: list[str] = []
    checked = 0
    seen: set[int] = set()

    def inspect(fn: ast.AST, qualname: str, rule: str) -> None:
        # A `find` method that also constructs a verdict matches R3 and R1.
        # Count and report it once, under the first rule that claimed it.
        nonlocal checked
        if id(fn) in seen:
            return
        seen.add(id(fn))
        checked += 1
        got = _annotation_name(getattr(fn, "returns", None))
        if got != _VERDICT:
            violations.append(
                f"{where}:{getattr(fn, 'lineno', '?')} {qualname} "
                f"[{rule}] is annotated {got!r}, expected {_VERDICT!r}"
            )

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if _is_finder_find(node, item):
                        inspect(item, f"{node.name}.{item.name}", "R3")

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        rets = _own_returns(node)
        if any(_constructs_verdict(r) for r in rets):
            inspect(node, node.name, "R1")
        elif any(_delegates_to_finder(r) for r in rets):
            inspect(node, node.name, "R2")

    return violations, checked


def _scan() -> tuple[list[str], int, int]:
    root = _repo_root()
    violations: list[str] = []
    checked = files = 0
    for pkg in _PACKAGES:
        pkg_dir = root / pkg
        if not pkg_dir.is_dir():
            continue
        for path in sorted(pkg_dir.rglob("*.py")):
            files += 1
            v, c = check_source(
                path.read_text(encoding="utf-8"), str(path.relative_to(root))
            )
            violations.extend(v)
            checked += c
    return violations, checked, files


def test_finder_returns_are_annotated_find_verdict():
    violations, checked, _ = _scan()
    assert not violations, (
        "Return annotation does not match what the function returns:\n  "
        + "\n  ".join(violations)
        + "\n\nA no-route answer is a FindVerdict, not a Pipeline (shim S4)."
    )
    assert checked >= 4, (
        f"only {checked} verdict-returning functions found; expected at least "
        "the four on `mindsos_capacity/pipeline.py` (Finder.find, "
        "BFSFinder.find, ConjunctionFinder.find, find_pipeline). A scan that "
        "finds nothing passes vacuously."
    )


def test_packages_are_scanned():
    _, _, files = _scan()
    assert files > 50, f"only {files} files scanned — the walk is not reaching the packages"


_DEFECT = '''
class Finder:
    def find(self) -> "FindVerdict": ...

class BFSFinder(Finder):
    def find(self) -> FindVerdict:
        return FindVerdict(reason="x")

def find_pipeline() -> Pipeline:
    return BFSFinder().find()
'''

_CLEAN = _DEFECT.replace("def find_pipeline() -> Pipeline:", "def find_pipeline() -> FindVerdict:")


def test_guard_flags_a_wrong_annotation():
    """The exact defect that shipped at `ae63aa2` must make this guard RED."""
    violations, checked = check_source(_DEFECT, "<probe>")
    assert checked == 3, checked
    assert len(violations) == 1, violations
    assert "find_pipeline" in violations[0] and "R2" in violations[0]
    assert "'Pipeline'" in violations[0]


def test_guard_is_green_on_the_corrected_form():
    violations, checked = check_source(_CLEAN, "<probe>")
    assert checked == 3, checked
    assert violations == [], violations


@pytest.mark.parametrize(
    "src",
    [
        "def f() -> Pipeline:\n    return FindVerdict()\n",
        "class ZFinder(Finder):\n    def find(self) -> Pipeline: ...\n",
        "def g() -> None:\n    return ZFinder().find()\n",
    ],
    ids=["R1", "R3", "R2"],
)
def test_each_rule_can_fire(src):
    """No rule may be inert — each must produce a violation on its own shape."""
    violations, _ = check_source(src, "<probe>")
    assert len(violations) == 1, violations
