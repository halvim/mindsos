"""Import isolation for ``mindsos_llm`` — the guard that moved with it.

**Why this file exists.** Until ADR-0210 slice 1a the model client shipped
as ``mindsos_capacity/llm/`` and was walked by
``tests/phase_28/test_import_isolation_phase_28.py`` through its
``_ISOLATED_SUBPACKAGES`` tuple. Promoting it to a top-level package emptied
that tuple, and **an emptied domain is exactly the silent-hole defect that
suite exists to refuse** — reverting to a flat glob "turned no test red, it
just quietly checked ten fewer things". So the guard is re-established here,
on the package's new home, in the same ship as the move.

**The forbidden set is WIDER than the one it inherited, deliberately.**
Inside ``mindsos_capacity`` the rule was "do not import upward"
(``mindsos_server``, ``mindsos_knowledge``). ``mindsos_llm`` is substrate for
the whole stack, so it must not reach the capacity or intelligence layers
either:

* ``mindsos_server`` — ADR-0010 §I-S1. ⚠ **This is load-bearing for
  ADR-0210's credential design.** L0 owns the user's vendor id, credential
  level, mode and credential custody; this package may never reach into that
  store. **L0 PUSHES a resolver callable in at client construction.** The
  package that makes the network call is therefore structurally unable to
  read the store the credential came from — see the CR §7c.
* ``mindsos_knowledge`` — the rule inherited from phase 28.
* ``mindsos_capacity`` / ``mindsos_intelligence`` — substrate does not
  depend on the layers that consume it. Verified true at the moment of the
  move: nothing under ``llm/`` imported outside the standard library and its
  own siblings, which is what made the relocation safe to do at all.
  ``replay.RecordedLLM`` satisfies ``mindsos_capacity.context.LLMHandle``
  **structurally** (the Protocol is ``runtime_checkable``) precisely so no
  import has to cross.

The walk is an AST walk, so a function-local import is caught too. There is
no carve-out here and there should not be one: a body in this package that
needs a layer above it is a design event, not an import to exempt.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import mindsos_llm

_PKG_DIR = Path(mindsos_llm.__file__).resolve().parent

#: Every layer this package may not reach. See the module docstring for why
#: each one is here; adding a module to this package never removes it from
#: the walk, because the walk is computed from the filesystem.
FORBIDDEN_ROOTS = (
    "mindsos_server",
    "mindsos_knowledge",
    "mindsos_capacity",
    "mindsos_intelligence",
)


def _module_names_imported_by(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


#: ⚠ **``rglob``, not ``glob``, and that is the whole point of this line.**
#: The first version of this file walked only the top level, which left
#: ``adapters/anthropic.py`` — **the one module in the package that actually
#: opens a socket** — outside the guard that exists to watch this package. It
#: was caught by counting the collect delta, not by reading. This is the same
#: defect ``tests/phase_28`` was built to refuse, reproduced by the ship that
#: cites it: a walk whose domain silently excludes the interesting part.
_SOURCE_FILES = sorted(
    p for p in _PKG_DIR.rglob("*.py") if not p.name.startswith("_")
)


@pytest.mark.parametrize(
    "source_file", _SOURCE_FILES, ids=lambda p: p.name
)
@pytest.mark.parametrize("forbidden", FORBIDDEN_ROOTS)
def test_no_upward_import(source_file: Path, forbidden: str) -> None:
    imported = _module_names_imported_by(source_file)
    assert forbidden not in imported, (
        f"{source_file.name} imports {forbidden!r}. mindsos_llm is substrate: "
        f"it is pushed to, never reaching. Imports found: {sorted(imported)!r}."
    )


def test_every_subpackage_is_WALKED_not_merely_shipped():
    """The domain's own guard, asked from the FILESYSTEM.

    ``tests/phase_28`` learned that a guard walking a hand-listed tuple can be
    silenced by emptying the tuple — the test then iterates nothing and passes
    vacuously. So the question here is asked the other way round: **every
    subpackage that ships must appear in the walk.** There is no carve-out
    list, and there should not be one: a module in this package that needs a
    layer above it is a design event, not an import to exempt.
    """
    subpackages = {
        d for d in _PKG_DIR.iterdir()
        if d.is_dir() and (d / "__init__.py").exists()
    }
    for sub in subpackages:
        shipped = {q for q in sub.glob("*.py") if not q.name.startswith("_")}
        missing = sorted(q.name for q in shipped - set(_SOURCE_FILES))
        assert missing == [], (
            f"{sub.name}/ ships {missing} which this guard does not walk - "
            "silently outside is how the adapter that opens the socket nearly "
            "escaped the one guard watching this package"
        )


def test_the_adapter_that_opens_the_socket_is_IN_the_walk():
    """Named on its own, because it is the module the guard most needs to
    cover and the one the first version of this file missed."""
    walked = {str(p.relative_to(_PKG_DIR)) for p in _SOURCE_FILES}
    assert "adapters/anthropic.py" in walked, walked


def test_the_walk_is_not_empty():
    """The domain-emptied failure mode, pinned.

    ``tests/phase_28`` learned this the expensive way: a guard whose domain
    can silently become empty is a guard a rename can switch off. If this
    package's modules stop being found, that is a red, not a quiet pass.
    """
    assert len(_SOURCE_FILES) >= 8, (
        f"only {len(_SOURCE_FILES)} module(s) walked in {_PKG_DIR} - the "
        "package moved or the glob stopped matching, and this guard is now "
        "checking almost nothing"
    )


def test_the_credential_owner_is_unreachable_from_here():
    """ADR-0210 §7c, stated as its own test rather than as one row in a
    parametrized sweep, because it is the one that carries a security
    argument: L0 holds the credential, this package holds the call, and the
    only thing that crosses is a callable L0 hands in."""
    offenders = sorted(
        p.name for p in _SOURCE_FILES
        if "mindsos_server" in _module_names_imported_by(p)
    )
    assert offenders == [], (
        f"{offenders} reach mindsos_server. The credential seam is INJECTED: "
        "L0 resolves vendor, level and mode and passes a resolver callable to "
        "the client it constructs. This package must never read that store."
    )
