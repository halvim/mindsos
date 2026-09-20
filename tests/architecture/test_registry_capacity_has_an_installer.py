"""A registry capacity that nothing can install is a declaration — plan I-16.

**The defect this is born from.** I-9 shipped
``capacity:comprehension:write_prompt_edition`` — a real capacity, with a
body, a DataState and a write path — and **no installer**. Nothing in the tree
called :func:`build_write_prompt_edition`, so no registry held it, and L4 can
only route to what a registry holds. The plan recorded I-9 as ``DONE``, which
was mechanically true of the commit and said nothing about whether the
capacity could be reached. Measured 2026-09-17, two ships later.

**The predicate, and why it needs no allowlist.** Measured over
``mindsos_capacity/builtins``: every capacity factory that takes NO arguments
is a fixed registry member, and every installer-less factory in the tree is
PARAMETERISED (8–14 arguments) — a per-flow builder its consumer registers
with the values it was built from (``build_reader``, ``build_policy_limit_
lookup``, ``build_structured_ingest_reader``). That is a real distinction, not
a convenience: a parameterised family has no fixed membership to install.
⚠ So the rule is **zero-argument factory ⟹ its module defines an installer**,
and a hand-written exemption list — the thing that rots — is unnecessary.

⚠ **This does not claim the installer is CALLED.** ``install_learn_parameter_
capacities`` has no production caller either; wiring is L4's, and pinning it
here would be a claim about a different layer. What it claims is that the
capacity CAN be registered by something other than a test typing out
``register_capacity`` by hand.
"""

from __future__ import annotations

import ast
from pathlib import Path


def factories_without_an_installer(source: str) -> list[str]:
    """Zero-argument ``build_*`` functions in a module that defines no installer.

    Read from the syntax tree: an argument count is not visible to a grep, and
    the whole predicate turns on it.
    """
    tree = ast.parse(source)
    top = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if any(n.name.startswith("install_") for n in top):
        return []
    return [
        n.name
        for n in top
        if n.name.startswith("build_")
        and not (n.args.args or n.args.kwonlyargs or n.args.posonlyargs)
    ]


def _builtins_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "mindsos_capacity" / "builtins"
        if candidate.is_dir():
            return candidate
    raise RuntimeError("mindsos_capacity/builtins not found")


def _offenders() -> dict[str, list[str]]:
    out = {}
    for path in sorted(_builtins_dir().glob("*.py")):
        names = factories_without_an_installer(path.read_text(encoding="utf-8"))
        if names:
            out[path.name] = names
    return out


def test_every_registry_capacity_can_be_installed():
    assert _offenders() == {}, (
        "these modules define a fixed capacity and nothing that registers it, "
        "so it is a declaration no registry holds and L4 cannot route to it - "
        "the I-9 defect, found two ships after that item was recorded DONE. "
        f"Add the installer beside the factory: {_offenders()!r}"
    )


def test_the_checker_sees_a_fabricated_uninstallable_capacity():
    """Born red against FABRICATED input: the offence no longer exists in the
    tree, so it cannot be reproduced by mutating one."""
    offender = "def build_thing() -> Capacity:\n    return Capacity()\n"
    assert factories_without_an_installer(offender) == ["build_thing"]


def test_the_checker_clears_a_factory_whose_module_installs_it():
    fine = (
        "def build_thing() -> Capacity:\n    return Capacity()\n\n"
        "def install_thing_capacities(cl) -> None:\n"
        "    cl.register_capacity(build_thing())\n"
    )
    assert factories_without_an_installer(fine) == []


def test_the_checker_ignores_a_parameterised_per_flow_builder():
    """The other door, and the reason no allowlist is needed. A builder that
    takes the values it is built from has no fixed membership to install."""
    per_flow = "def build_reader(name, prompt_iri, question) -> Capacity:\n    return Capacity()\n"
    assert factories_without_an_installer(per_flow) == []


def test_the_census_is_load_bearing():
    """A predicate that matches nothing is green while checking zero rows."""
    total = sum(
        len([
            n for n in ast.parse(p.read_text(encoding="utf-8")).body
            if isinstance(n, ast.FunctionDef)
            and n.name.startswith("build_")
            and not (n.args.args or n.args.kwonlyargs or n.args.posonlyargs)
        ])
        for p in _builtins_dir().glob("*.py")
    )
    assert total >= 25, f"only {total} zero-argument factories seen"
