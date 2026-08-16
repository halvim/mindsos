"""Phase 28 — import-isolation discipline for mindsos_capacity."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import mindsos_capacity

_PKG_DIR = Path(mindsos_capacity.__file__).resolve().parent


def _module_names_imported_by(path: Path):
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


#: The guard's DOMAIN, stated rather than implied (RULES §12.3 — a
#: quantified claim states its domain). It was a flat ``glob("*.py")``,
#: which silently exempted every subpackage; found 2026-08-16 when
#: ``llm/`` landed (coordination §87 T-F11) and would otherwise have been
#: the only architecture guard that could not see it.
#:
#: ``builtins/`` is EXCLUDED, and that is a decision, not an oversight:
#: L3 builtin bodies reach L2 through **function-local** imports by
#: design (``policy_lookup_v0`` says so at its import site — "local: L3
#: declares no L2 dep"), and this walker is an AST walk that sees nested
#: imports too, so including them would redden six shipped files. The
#: rule this guard enforces is about MODULE-level layering.
_ISOLATED_SUBPACKAGES = ("llm",)

#: Shipped subpackages deliberately OUTSIDE the walk, with the reason in
#: _ISOLATED_SUBPACKAGES' comment above. Classified, not forgotten.
_CARVED_OUT_SUBPACKAGES = frozenset({"builtins"})

_SOURCE_FILES = sorted(
    [p for p in _PKG_DIR.glob("*.py") if not p.name.startswith("_")]
    + [
        p
        for sub in _ISOLATED_SUBPACKAGES
        for p in (_PKG_DIR / sub).glob("*.py")
        if not p.name.startswith("_")
    ]
)


@pytest.mark.parametrize("source_file", _SOURCE_FILES, ids=lambda p: str(p.relative_to(_PKG_DIR)))
@pytest.mark.parametrize("forbidden", ["mindsos_server", "mindsos_knowledge"])
def test_no_upward_import(source_file, forbidden):
    imported = _module_names_imported_by(source_file)
    assert forbidden not in imported, (
        f"{source_file.name} imports forbidden module {forbidden!r}; "
        f"this violates layer isolation. Imports found: {sorted(imported)!r}."
    )


def test_every_subpackage_is_CLASSIFIED_not_merely_listed():
    """**The widening's own guard.** ``_SOURCE_FILES`` was a flat glob, so
    ``mindsos_capacity/llm/`` sat outside the one architecture guard that
    could catch it importing upward (coordination §87 T-F11). Widening the
    domain fixed that — and nothing pinned the fix: reverting to the flat
    glob turned no test red, it just quietly checked ten fewer things,
    which is the defect class this suite exists to refuse.

    The first version of this test walked ``_ISOLATED_SUBPACKAGES`` and
    asserted its modules were in the domain. **Writing the mutation plan
    killed it**: deleting ``"llm"`` from that tuple made the loop iterate
    nothing and the test pass vacuously — a guard a mutation can silence
    by emptying its own domain. So the question is asked from the
    FILESYSTEM instead: every shipped subpackage must be classified,
    either walked or carved out with a stated reason. A new one is a
    decision, not a default.
    """
    subpackages = {
        p.name for p in _PKG_DIR.iterdir()
        if p.is_dir() and (p / "__init__.py").exists()
    }
    assert subpackages, "no subpackages found - this test is checking nothing"
    unclassified = sorted(
        subpackages - set(_ISOLATED_SUBPACKAGES) - _CARVED_OUT_SUBPACKAGES
    )
    assert unclassified == [], (
        f"{unclassified} ship inside mindsos_capacity but are neither walked "
        f"by this guard nor carved out of it. Add them to "
        f"_ISOLATED_SUBPACKAGES, or to _CARVED_OUT_SUBPACKAGES with the "
        f"reason - silently outside is how llm/ nearly shipped unguarded."
    )
    for sub in _ISOLATED_SUBPACKAGES:
        shipped = {
            q for q in (_PKG_DIR / sub).glob("*.py")
            if not q.name.startswith("_")
        }
        assert shipped, f"{sub!r} is declared isolated but has no modules"
        missing = sorted(q.name for q in shipped - set(_SOURCE_FILES))
        assert missing == [], f"{sub}/ is declared isolated but {missing} are not walked"


def test_the_builtins_carve_out_is_deliberate_and_still_necessary():
    """The carve-out exists because L3 builtin bodies reach L2 through
    function-local imports BY DESIGN. If that ever stops being true the
    carve-out should go — so this fails when its reason expires, rather
    than leaving a permanent hole nobody revisits."""
    offenders = [
        q.name for q in (_PKG_DIR / "builtins").glob("*.py")
        if "mindsos_knowledge" in _module_names_imported_by(q)
    ]
    assert offenders, (
        "no builtin imports mindsos_knowledge any more - the carve-out has "
        "expired, so fold builtins/ into the guarded domain and delete this"
    )
