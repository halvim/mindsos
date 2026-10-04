"""A signature or keyword call written in a live page matches the tree.

Doc-fix mechanism: API drift. Verification batches 4a, 4b, 5 and 6 (PRs #240,
#241, #243, #244) were carried by a static probe that compared what the pages
SAY a call takes against what the tree actually defines -- it found the five
loader signatures missing ``include_deprecated``, a cited
``validate_namespaced_properties`` that exists nowhere, and field tables that
had drifted. The probe lived outside the repo, so nothing ran it after the
batch. This guard is that comparison, made permanent and narrowed to the part
that is decidable without judgement.

THE RULE, in three halves:

* a ``def NAME(...)`` written inside a ```python fence on a live or index page
  must list the same parameters as the one definition of ``NAME`` in the tree,
  both ways;
* a keyword argument in a call on such a page must be a real parameter of the
  one definition of the callee (for a class: its ``__init__`` parameters plus
  its fields, or its fields alone when the constructor is generated);
* the call's ARITY must work: it may not pass more positional arguments than
  the callee has positional slots, and it must supply every parameter that has
  no default. An example that raises ``TypeError`` the moment a reader runs it
  is the same defect as a wrong parameter name.

DOMAIN -- deliberately narrow, so a RED line is always a real defect:

* ``tools/claim_inventory.partition`` decides what is live or index; a dated
  record may describe the API of its date.
* A name is checked only when it resolves to EXACTLY ONE definition across
  module functions, classes and methods. ``cl.invoke(..., session=...)`` is
  correct on ``CapacityLayer.invoke`` and wrong on ``runtime.invoke``; the
  page does not say which, so an ambiguous name is SKIPPED, not reported.
* A name absent from the tree is SKIPPED. A page documenting a function that
  does not exist is a different class (a reference that does not resolve) and
  belongs to its own guard, not to this one.
* Fields are resolved through base classes, so a dataclass that inherits its
  fields is not reported for having them.
* A call carrying ``...`` is a deliberate elision (``handle.write_and_validate(
  ...)`` in the review checklist) and is skipped whole. So is a call with
  ``*args`` / ``**kwargs`` spread at the call site, and a callee taking
  ``*args`` is not held to a positional maximum.
* Arity is checked only against an EXPLICIT signature. A generated dataclass
  constructor is not, because which fields carry defaults is not read here.
* Parameters starting with ``_`` are not required to appear in a doc, and a
  callable taking ``**kwargs`` is only checked one way.

FLOOR, NOT CEILING: a signature written as prose, in a heading, or in a fence
that is not Python is MISSED here rather than reported wrong.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_TOOL = _ROOT / "tools" / "claim_inventory.py"
_DOMAIN = frozenset({"live", "index"})
_FENCE = re.compile(r"```(\w*)\n(.*?)```", re.S)


def _load():
    spec = importlib.util.spec_from_file_location("claim_inventory_sig", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


inv = _load()


# -- the tree ---------------------------------------------------------------


def _sig(node: ast.AST) -> dict:
    """What a ``def`` accepts: names, positional slots, what has no default."""
    a = node.args
    positional = [p.arg for p in a.posonlyargs + a.args if p.arg not in ("self", "cls")]
    keyword_only = [p.arg for p in a.kwonlyargs]
    defaulted = len(a.defaults)
    required = positional[: len(positional) - defaulted] if defaulted else list(positional)
    required += [p.arg for p, d in zip(a.kwonlyargs, a.kw_defaults) if d is None]
    return {
        "names": positional + keyword_only,
        "positional": positional,
        "required": required,
        "star": a.vararg is not None,
        "starstar": a.kwarg is not None,
    }


class Tree:
    """Every ``mindsos_*`` definition under ``root``, indexed by bare name."""

    def __init__(self, root: Path) -> None:
        self.funcs: dict[str, list[tuple[str, dict]]] = {}
        self.methods: dict[str, list[tuple[str, dict]]] = {}
        self.classes: dict[str, list[tuple[str, dict, dict, list[str]]]] = {}
        for pkg in sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith("mindsos_")):
            for path in sorted(pkg.rglob("*.py")):
                if ".fuse_hidden" in path.name:
                    continue
                try:
                    mod = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
                except SyntaxError:
                    continue
                where = str(path.relative_to(root).with_suffix("")).replace("/", ".")
                self._module(mod, where)

    def _module(self, mod: ast.Module, where: str) -> None:
        for node in mod.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.funcs.setdefault(node.name, []).append((where, _sig(node)))
            elif isinstance(node, ast.ClassDef):
                fields: dict[str, None] = {}
                methods: dict[str, dict] = {}
                bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                bases += [b.attr for b in node.bases if isinstance(b, ast.Attribute)]
                for stmt in node.body:
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        fields[stmt.target.id] = None
                    elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods[stmt.name] = _sig(stmt)
                        self.methods.setdefault(stmt.name, []).append(
                            (f"{where}.{node.name}", methods[stmt.name])
                        )
                    elif isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if not isinstance(target, ast.Name):
                                continue
                            if target.id == "__slots__":
                                for sub in ast.walk(stmt.value):
                                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                                        fields.setdefault(sub.value, None)
                            else:
                                fields.setdefault(target.id, None)
                self.classes.setdefault(node.name, []).append((where, fields, methods, bases))

    # -- resolution through base classes ------------------------------------

    def _chain(self, name: str, seen: frozenset[str] = frozenset()) -> list[tuple]:
        if name in seen or name not in self.classes:
            return []
        entry = self.classes[name][0]
        out = [entry]
        for base in entry[3]:
            out += self._chain(base, seen | {name})
        return out

    def fields(self, name: str) -> set[str]:
        return {f for entry in self._chain(name) for f in entry[1]}

    def method(self, cls: str, meth: str):
        for entry in self._chain(cls):
            if meth in entry[2]:
                return entry[2][meth]
        return None

    def unique(self, name: str):
        """``{accepted, sig, where}`` when ``name`` has exactly one definition
        across functions, classes and methods; otherwise ``None``. ``sig`` is
        ``None`` when the callable has no explicit signature to check arity
        against (a generated dataclass constructor)."""
        hits = (
            [("call", where, sig) for where, sig in self.funcs.get(name, [])]
            + [("call", where, sig) for where, sig in self.methods.get(name, [])]
            + [("class", c[0], None) for c in self.classes.get(name, [])]
        )
        if len(hits) != 1:
            return None
        kind, where, sig = hits[0]
        if kind == "class":
            ctor = self.method(name, "__init__")
            if ctor is not None:
                return {"accepted": set(ctor["names"]) | self.fields(name),
                        "sig": ctor, "where": where}
            return {"accepted": self.fields(name), "sig": None, "where": where}
        return {"accepted": set(sig["names"]), "sig": sig, "where": where}


# -- the pages --------------------------------------------------------------


def _report(rel: str, line: int, msg: str) -> str:
    return f"{rel}:{line}: {msg}"


def _elided(node: ast.Call) -> bool:
    """A call written with ``...`` stands for arguments the page left out."""
    for arg in list(node.args) + [kw.value for kw in node.keywords]:
        if isinstance(arg, ast.Constant) and arg.value is Ellipsis:
            return True
    return False


def _check_def(tree: Tree, rel: str, line: int, node: ast.AST, out: list[str]) -> None:
    hit = tree.unique(node.name)
    if hit is None:
        return
    accepted, where = hit["accepted"], hit["where"]
    documented = _sig(node)["names"]
    for arg in documented:
        if arg not in accepted:
            out.append(_report(rel, line, f"`{node.name}(...)` documents `{arg}`, not a parameter of {where}"))
    if hit["sig"] is not None and hit["sig"]["starstar"]:
        return
    for arg in sorted(accepted):
        if arg not in documented and not arg.startswith("_"):
            out.append(_report(rel, line, f"`{node.name}(...)` omits `{arg}`, a real parameter of {where}"))


def _check_call(tree: Tree, rel: str, line: int, node: ast.Call, out: list[str]) -> None:
    func = node.func
    name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)
    if name is None or _elided(node):
        return
    hit = tree.unique(name)
    if hit is None:
        return
    accepted, sig, where = hit["accepted"], hit["sig"], hit["where"]
    named = [kw.arg for kw in node.keywords if kw.arg]
    spread = any(kw.arg is None for kw in node.keywords)
    starred = any(isinstance(a, ast.Starred) for a in node.args)

    if named and not (sig is not None and sig["starstar"]):
        for kw in named:
            if kw not in accepted:
                out.append(_report(rel, line, f"`{name}({kw}=...)` is not a parameter of {where}"))
    if sig is None or starred:
        return
    positional = sig["positional"]
    if not sig["star"] and len(node.args) > len(positional):
        out.append(_report(
            rel, line,
            f"`{name}(...)` is given {len(node.args)} positional argument(s) but {where} "
            f"takes at most {len(positional)}",
        ))
        return
    if spread:
        return
    supplied = set(positional[: len(node.args)]) | set(named)
    missing = [p for p in sig["required"] if p not in supplied]
    if missing:
        out.append(_report(
            rel, line,
            f"`{name}(...)` never supplies {missing}, required by {where}",
        ))


def _nodes(root: Path):
    """Every ``def`` and call in a python fence of a live or index page:
    (file, line number, node). The one walk both callers share."""
    inventory = inv.load_tree(root)
    for rel in inventory.files:
        if not rel.endswith(".md") or inv.partition(rel) not in _DOMAIN:
            continue
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        for match in _FENCE.finditer(text):
            lang, code = match.group(1), match.group(2)
            if lang not in ("python", "py"):
                continue
            try:
                parsed = ast.parse(code)
            except SyntaxError:
                continue
            start = text[: match.start()].count("\n") + 2
            for node in ast.walk(parsed):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Call)):
                    yield rel, start + node.lineno - 1, node


def find_problems(root: Path) -> list[str]:
    tree = Tree(root)
    out: list[str] = []
    for rel, line, node in _nodes(root):
        if isinstance(node, ast.Call):
            _check_call(tree, rel, line, node, out)
        else:
            _check_def(tree, rel, line, node, out)
    return sorted(set(out))


def _is_judged(tree: Tree, node: ast.AST) -> bool:
    """Whether ``_check_def`` / ``_check_call`` reach a verdict on ``node``
    instead of returning early: the name resolves to exactly one definition
    and, for a call, its arguments are not elided with ``...``."""
    if isinstance(node, ast.Call):
        func = node.func
        name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)
        return name is not None and not _elided(node) and tree.unique(name) is not None
    return tree.unique(node.name) is not None


def adjudicated_sites(root: Path) -> list[tuple[str, int]]:
    """Report mode (`tools/claim_inventory.py`, the emit contract): the
    `file:line` of every documented signature or call this guard compared with
    the tree. An unknown or ambiguous name, an elided call and a fence that
    does not parse were read, not judged, and are NOT emitted."""
    root = Path(root)
    tree = Tree(root)
    return sorted({(rel, line) for rel, line, node in _nodes(root) if _is_judged(tree, node)})


# -- the guard --------------------------------------------------------------


def test_the_premise_holds_so_the_guard_cannot_pass_vacuously():
    assert (_ROOT / "docs").is_dir(), "docs/ missing - the image did not copy it"
    tree = Tree(_ROOT)
    assert len(tree.funcs) > 100, f"only {len(tree.funcs)} module functions indexed"
    assert len(tree.classes) > 100, f"only {len(tree.classes)} classes indexed"
    hit = tree.unique("iter_load_graph")
    assert hit and hit["sig"], "a known-unique function did not resolve to a signature"
    assert hit["sig"]["required"] == ["client", "graph_id"], hit["sig"]["required"]


def test_the_pages_are_actually_scanned():
    """A fence the guard cannot parse is a fence it cannot check -- count them."""
    inventory = inv.load_tree(_ROOT)
    parsed = 0
    for rel in inventory.files:
        if not rel.endswith(".md") or inv.partition(rel) not in _DOMAIN:
            continue
        text = (_ROOT / rel).read_text(encoding="utf-8", errors="replace")
        for lang, code in _FENCE.findall(text):
            if lang in ("python", "py"):
                try:
                    ast.parse(code)
                except SyntaxError:
                    continue
                parsed += 1
    assert parsed > 50, f"only {parsed} python fences parsed on live pages"


def test_documented_signatures_agree_with_the_tree():
    bad = find_problems(_ROOT)
    assert not bad, (
        f"{len(bad)} documented signature(s) or call(s) disagree with the "
        "tree:\n" + "\n".join(bad)
    )


# -- fabricated corners -----------------------------------------------------

_SOURCE = '''
from dataclasses import dataclass


@dataclass
class _Base:
    iri: str


@dataclass
class Widget(_Base):
    name: str
    size: int = 1


class Panel:
    def __init__(self, *, strict: bool = False) -> None:
        self.strict = strict

    def render(self, mode, *, verbose=False):
        return mode


class Dial:
    def render(self, mode):
        return mode


def build(client, graph_id, *, batch_size=10, include_deprecated=False, _internal=None):
    return client


def flexible(name, **kwargs):
    return name


def variadic(first, *rest):
    return first
'''


def _tree(root: Path, live: str, record: str = "") -> Path:
    (root / "mindsos_demo").mkdir(parents=True)
    (root / "mindsos_demo" / "mod.py").write_text(_SOURCE)
    (root / "docs" / "usage").mkdir(parents=True)
    (root / "docs" / "usage" / "p.md").write_text(live)
    (root / "docs" / "changelog").mkdir()
    (root / "docs" / "changelog" / "old.md").write_text(record)
    return root


def _page(body: str) -> str:
    return "# page\n\n```python\n" + body + "\n```\n"


#: one row per message the guard can emit, so each is proven to fire
_FABRICATED = (
    _page("def build(client, graph_id, *, batch_size=10, include_deprecated=False, verbose=True):\n    ..."),
    _page("def build(client, graph_id, *, batch_size=10):\n    ..."),
    _page("build(client, 'g', unknown_flag=True)"),
    _page("Widget(colour='red')"),
    _page("Panel(mode='fast')"),
    _page("build(client)"),
    _page("build(client, 'g', 'surplus')"),
)


def test_every_message_fires_on_a_fabricated_page(tmp_path):
    for i, page in enumerate(_FABRICATED):
        root = tmp_path / f"c{i}"
        root.mkdir()
        found = find_problems(_tree(root, page))
        assert len(found) == 1, f"corner {i}: {found}"


def test_a_true_page_is_silent(tmp_path):
    page = _page(
        "def build(client, graph_id, *, batch_size=10, include_deprecated=False):\n"
        "    ...\n"
        "w = Widget(iri='x', name='n', size=2)\n"
        "p = Panel(strict=True)\n"
        "flexible('n', anything=1)\n"
        "variadic(1, 2, 3, 4)\n"
        "build(client, 'g', batch_size=5)\n"
        "build(graph_id='g', client=client)"
    )
    assert find_problems(_tree(tmp_path, page)) == []


def test_an_elided_call_is_skipped(tmp_path):
    """`handle.write_and_validate(...)` means "arguments omitted", not "none"."""
    assert find_problems(_tree(tmp_path, _page("build(...)"))) == []


def test_a_spread_call_is_not_judged_on_missing_arguments(tmp_path):
    assert find_problems(_tree(tmp_path, _page("build(client, **opts)"))) == []


def test_a_generated_constructor_is_not_held_to_arity(tmp_path):
    """Which dataclass fields carry defaults is not read, so arity is not checked."""
    assert find_problems(_tree(tmp_path, _page("Widget('x')"))) == []


def test_an_ambiguous_name_is_skipped(tmp_path):
    """`render` is a method on two classes, so the page does not say which."""
    assert find_problems(_tree(tmp_path, _page("panel.render('fast', nonsense=1)"))) == []


def test_an_unknown_name_is_skipped(tmp_path):
    assert find_problems(_tree(tmp_path, _page("absent_helper(whatever=1)"))) == []


def test_a_dated_record_is_outside_the_domain(tmp_path):
    record = _page("Widget(colour='red')")
    assert find_problems(_tree(tmp_path, "nothing here\n", record)) == []


def test_a_non_python_fence_is_not_read_as_python(tmp_path):
    page = "# page\n\n```cypher\nWidget(colour='red')\n```\n"
    assert find_problems(_tree(tmp_path, page)) == []


# -- report mode -----------------------------------------------------------

def test_it_emits_the_judged_lines_and_only_those(tmp_path):
    page = _page(
        "build(client, 'g')\n"
        "absent_helper(whatever=1)\n"
        "build(...)\n"
        "panel.render('fast')\n"
        "Widget(colour='red')"
    )
    assert adjudicated_sites(_tree(tmp_path, page)) == [("docs/usage/p.md", 4), ("docs/usage/p.md", 8)]


def test_every_reported_problem_is_an_emitted_site(tmp_path):
    for i, page in enumerate(_FABRICATED):
        root = tmp_path / f"e{i}"
        root.mkdir()
        _tree(root, page)
        emitted = {f"{f}:{n}" for f, n in adjudicated_sites(root)}
        problems = {":".join(p.split(":", 2)[:2]) for p in find_problems(root)}
        assert problems and problems <= emitted, f"corner {i}: {problems - emitted}"
