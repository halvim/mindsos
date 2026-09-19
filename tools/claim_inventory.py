#!/usr/bin/env python3
"""Claim inventory: the doc-fix program's stopping rule.

The program ends when every class of checkable claim in the tracked docs is
GUARDED (a test in CI keeps it true) or OWNED (someone who is not a test is
responsible for it). This tool measures that; it rewrites nothing.

WHY A SCRIPT AND NOT A TABLE. The 2026-09-13 audit's list was wrong every time
it was measured (30 citations -> 40/29, 28 of which never existed; 34 broken
names -> 64 occurrences, 53 not defects; one ADR header -> a class of 18). A
markdown table rots the same way. A script is re-run instead of trusted.

WHAT IT REPORTS, per (class, partition):
  sites   how many claims of that class the partition makes
  false   how many of them are false against this tree (unguarded classes only;
          a guarded class is held at 0 by its guard in CI and is not re-derived
          here, so its checking logic lives in exactly one place)
  state   GUARDED by <test> | UNGUARDED | NOT-IN-IMAGE | NEEDS-RULING

Plus RESIDUAL: live prose lines that no class reaches. No mechanical oracle
exists for those ("the finder returns a Pipeline" was found by reading). They
are the set the stopping rule does not yet cover; this sizes it.

FLOOR, NOT CEILING -- twice over. `false` for python-symbol is a floor: a
name re-exported from another module is taken as present without following
it. And the class list below is hand-written. A class it does not
know is invisible to it -- exactly the audit's flaw. RESIDUAL is how that shows
up as a number instead of as silence.

ONE DEFINITION OF "LIVE" lives here (`partition`). Existing guards each carry a
`_SKIP_DIRS` of their own; migrating them to this one is filed, not done.
Note it differs on purpose in one place: the guards skip all of
`docs/decisions/`, this treats the index pages there (proposed.md,
superseded.md, summary/) as LIVE, because they make present-tense status
claims -- which is how proposed.md stayed false for 23 of 29 entries.

Usage:
  python3 tools/claim_inventory.py            # table
  python3 tools/claim_inventory.py --json     # machine-readable
  python3 tools/claim_inventory.py --check    # exit 1 while any row is not
                                              # GUARDED (the finish line)
  python3 tools/claim_inventory.py --list CLASS  # print the false sites
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# Partitions -- the one definition of "live".
# --------------------------------------------------------------------------

#: The test image COPIES docs/, confirmation_docs/ and README.md (Dockerfile
#: test stage, read 2026-09-19). Every other tracked .md -- CLAUDE.md,
#: HANDOFF.md, RULES.md, BRANCHES.md, projects/** -- no guard can see.

LIVE = "live"                    # present-tense docs a reader acts on
INDEX = "index"                  # docs/decisions index pages (status claims)
ADR = "adr-record"               # docs/decisions/adr/*.md -- dated records
RECORD = "record"                # changelog, confirm docs, design logs
SCRATCH = "scratch"              # docs/_workbench -- another chat's
UNCLASSIFIED = "unclassified"    # in-image, but nothing says live or record
OUT_OF_IMAGE = "not-in-image"    # tracked, but no test image copies it

_DATED = re.compile(r"(_CONFIRMED|_DESIGN_LOG|\d{4}-\d{2}-\d{2})")


def partition(rel: str) -> str:
    """Partition of a repo-relative ``.md`` path. The single source."""
    parts = rel.split("/")
    top = parts[0]
    if len(parts) == 1:
        return LIVE if rel == "README.md" else OUT_OF_IMAGE
    if top == "docs":
        if parts[1] == "_workbench":
            return SCRATCH
        if parts[1] == "changelog":
            return RECORD
        if parts[1] == "decisions":
            return ADR if len(parts) > 2 and parts[2] == "adr" and parts[-1] != "README.md" else INDEX
        return LIVE
    if top == "confirmation_docs":
        return RECORD if _DATED.search(parts[-1]) else UNCLASSIFIED
    return OUT_OF_IMAGE


# --------------------------------------------------------------------------
# Guarded classes -- registry only. Their logic lives in their guard.
# --------------------------------------------------------------------------

#: class name -> (guard file, what it holds). The test asserts BOTH ways:
#: every file here exists, and every doc-reading architecture guard is here.
GUARDED: dict[str, tuple[str, str]] = {
    "adr-status-index": ("tests/test_adr_status_consistency.py",
                         "ADR file status == README row == summary/*.md cell"),
    "role-set-count": ("tests/architecture/test_doc_role_count.py",
                       "live docs' L2 role-set count == len(ALL_ROLES)"),
    "capacity-api-retired-names": ("tests/architecture/test_doc_capacity_api.py",
                                   "live docs use no retired CORE-C3R1 finder name"),
    "adr-test-citation": ("tests/architecture/test_adr_test_citations.py",
                          "every test path an Accepted ADR cites exists or is dispositioned"),
    "pending-ship-label": ("tests/architecture/test_no_pending_ship_for_shipped_phase.py",
                           "no ADR heading calls a confirmed phase pending"),
    "adr-sentinel-no-skip": ("tests/architecture/test_no_skip_when_docs_missing.py",
                             "ADR sentinels fail, never skip, on a missing doc"),
    "retired-design-pointer": ("tests/architecture/test_retired_design_pointer.py",
                               "retired design tokens carry the current-design pointer"),
    "coordination-files-closed-set": ("tests/architecture/test_coordination_files_closed_set.py",
                                      "the tracked coordination files are a closed set"),
    "llm-plan-scope": ("tests/architecture/test_mindsos_llm_plan_is_the_scope.py",
                       "docs/plans/MINDSOS_LLM_PLAN.md owns mindsos_llm's scope"),
    "adr-0210-am4-record-shape": ("tests/architecture/test_adr_0210_am4_l2_record_shape.py",
                                  "ADR-0210 am-4's L2 record shape matches the code"),
}

# --------------------------------------------------------------------------
# Unguarded classes -- extracted and checked here.
# --------------------------------------------------------------------------

_FENCE = re.compile(r"^\s*(```|~~~)")
_CODESPAN = re.compile(r"`([^`\n]+)`")
_PATH_TOPS = r"(?:mindsos_\w+|tests_server|tests|tools|docs|confirmation_docs|projects|\.github)"
_PATH = re.compile(rf"^{_PATH_TOPS}/[\w./-]*[\w/]$")
_PATH_SUFFIX = re.compile(r"(::[\w.\[\]-]+|:\d+(?:-\d+)?|#L?\d+)$")
#: A template, not a claim: `PHASE_NN_CONFIRMED.md`, `tests/phase_NN/`,
#: `NNNN-short-slug.md`. Measured 2026-09-19: 8 of the first 26 "false" live
#: and index paths were these.
_PLACEHOLDER = re.compile(r"(?:^|[/_.-])N{2,}(?:[/_.-]|$)")
_DOTTED = re.compile(r"^(mindsos_\w+(?:\.\w+)+)(?:\(\))?$")
_ADR_REF = re.compile(r"\bADR[- ]?(\d{3,4})\b")
_MDLINK = re.compile(r"(?<!!)\[[^\]\n]*\]\(([^)\s]+)\)")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
_TABLE_SEP = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


@dataclass
class Site:
    cls: str
    file: str
    line: int
    text: str
    false: bool


@dataclass
class Tree:
    root: Path
    files: list[str]                       # repo-relative, every tracked file
    mode: str                              # "git" or "walk"
    _set: set[str] = field(default_factory=set)
    _dirs: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self._set = set(self.files)
        for f in self.files:
            parts = f.split("/")
            for i in range(1, len(parts)):
                self._dirs.add("/".join(parts[:i]))

    def exists(self, rel: str) -> bool:
        rel = rel.rstrip("/")
        return rel in self._set or rel in self._dirs


def _skip_name(name: str) -> bool:
    return name.startswith(".fuse_hidden") or name in {"__pycache__"}


def load_tree(root: Path) -> Tree:
    """Tracked files. ``git ls-files`` when a repo is there (the truth; it
    also never sees ``.fuse_hidden*`` or untracked scratch), else a walk that
    skips hidden entries -- the test image has no ``.git``."""
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                             capture_output=True, check=True, timeout=60).stdout
        files = [f for f in out.decode("utf-8").split("\0") if f]
        if files:
            return Tree(root, sorted(f for f in files if not _skip_name(f.split("/")[-1])), "git")
    except (OSError, subprocess.SubprocessError):
        pass
    files = []
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if any(part.startswith(".") and part != ".github" or _skip_name(part) for part in rel.parts):
            continue
        if p.is_file():
            files.append(rel.as_posix())
    return Tree(root, sorted(files), "walk")


def _lines_outside_fences(text: str):
    """Yield (lineno, line, in_fence). Code spans are scanned in and out of
    fences; prose residual only counts lines outside them."""
    fence = False
    for i, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line):
            fence = not fence
            yield i, line, True
            continue
        yield i, line, fence


def _module_names(py: Path) -> dict[str, set[str]]:
    """Top-level names a module defines or re-exports, and each class's
    member names. Static: depends only on the bytes."""
    try:
        tree = ast.parse(py.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return {"": set()}
    top: set[str] = set()
    members: dict[str, set[str]] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            top.add(node.name)
        elif isinstance(node, ast.ClassDef):
            top.add(node.name)
            members[node.name] = {
                n.name for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            } | {
                t.id for n in node.body if isinstance(n, (ast.Assign, ast.AnnAssign))
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target])
                if isinstance(t, ast.Name)
            }
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                if isinstance(t, ast.Name):
                    top.add(t.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                top.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, (ast.If, ast.Try)):
            for sub in ast.walk(node):
                if isinstance(sub, (ast.FunctionDef, ast.ClassDef)):
                    top.add(sub.name)
                elif isinstance(sub, (ast.Import, ast.ImportFrom)):
                    for a in sub.names:
                        top.add((a.asname or a.name).split(".")[0])
    out = {"": top}
    out.update(members)
    return out


class _Resolver:
    def __init__(self, tree: Tree) -> None:
        self.tree = tree
        self._cache: dict[str, dict[str, set[str]]] = {}

    def _names(self, rel: str) -> dict[str, set[str]]:
        if rel not in self._cache:
            self._cache[rel] = _module_names(self.tree.root / rel)
        return self._cache[rel]

    def dotted_ok(self, dotted: str) -> bool:
        parts = dotted.split(".")
        # longest module prefix that is a file in the tree
        for k in range(len(parts), 0, -1):
            base = "/".join(parts[:k])
            for rel in (base + ".py", base + "/__init__.py"):
                if rel in self.tree._set:
                    rest = parts[k:]
                    if not rest:
                        return True
                    names = self._names(rel)
                    if rest[0] not in names[""]:
                        # a subpackage/module not yet reached is a miss too
                        return False
                    if len(rest) == 1:
                        return True
                    if rest[0] in names:          # Class.member
                        return rest[1] in names[rest[0]] and len(rest) == 2
                    return True                   # re-exported object; deeper attrs unknowable statically
        return False


def scan(tree: Tree) -> list[Site]:
    sites: list[Site] = []
    adr_numbers = {
        int(m.group(1)) for f in tree.files
        if (m := re.match(r"docs/decisions/adr/(\d{4})-.*\.md$", f))
    }
    resolver = _Resolver(tree)
    for rel in tree.files:
        if not rel.endswith(".md"):
            continue
        part = partition(rel)
        if part in (SCRATCH,):
            continue
        text = (tree.root / rel).read_text(encoding="utf-8", errors="replace")
        for n, line, _fence in _lines_outside_fences(text):
            for span in _CODESPAN.findall(line):
                span = span.strip()
                cand = _PATH_SUFFIX.sub("", span)
                if _PLACEHOLDER.search(cand):
                    continue
                if _PATH.match(cand) and not re.search(r"[*{}<>]|\.\.\.", cand):
                    sites.append(Site("path-citation", rel, n, span, not tree.exists(cand)))
                    continue
                m = _DOTTED.match(span)
                if m:
                    sites.append(Site("python-symbol", rel, n, span, not resolver.dotted_ok(m.group(1))))
            for m in _ADR_REF.finditer(line):
                sites.append(Site("adr-reference", rel, n, m.group(0), int(m.group(1)) not in adr_numbers))
            for m in _MDLINK.finditer(line):
                target = m.group(1).split("#")[0]
                if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("/"):
                    continue
                resolved = (Path(rel).parent / target).as_posix()
                resolved = _normpath(resolved)
                sites.append(Site("relative-link", rel, n, m.group(1),
                                  resolved is None or not tree.exists(resolved)))
    return sites


def _normpath(p: str) -> str | None:
    out: list[str] = []
    for part in p.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not out:
                return None
            out.pop()
        else:
            out.append(part)
    return "/".join(out)


def residual(tree: Tree, sites: list[Site]) -> dict[str, tuple[int, int]]:
    """Per partition: (prose lines, prose lines no class reaches)."""
    hit = {(s.file, s.line) for s in sites}
    out: dict[str, list[int]] = {}
    for rel in tree.files:
        if not rel.endswith(".md"):
            continue
        part = partition(rel)
        text = (tree.root / rel).read_text(encoding="utf-8", errors="replace")
        body = text
        if text.startswith("---\n"):
            end = text.find("\n---", 4)
            if end != -1:
                body = "\n" * text.count("\n", 0, end + 4) + text[end + 4:]
        acc = out.setdefault(part, [0, 0])
        for n, line, fence in _lines_outside_fences(body):
            if fence or not line.strip() or _HEADING.match(line) or _TABLE_SEP.match(line):
                continue
            acc[0] += 1
            if (rel, n) not in hit:
                acc[1] += 1
    return {k: (v[0], v[1]) for k, v in out.items()}


UNGUARDED_CLASSES = ("path-citation", "python-symbol", "adr-reference", "relative-link")


def _state(part: str) -> str:
    if part == OUT_OF_IMAGE:
        return "NOT-IN-IMAGE"
    if part == UNCLASSIFIED:
        return "NEEDS-RULING"
    return "UNGUARDED"


def build_report(root: Path = ROOT) -> dict:
    tree = load_tree(root)
    sites = scan(tree)
    rows = []
    for cls, (guard, holds) in GUARDED.items():
        rows.append({"class": cls, "partition": "-", "sites": None, "false": None,
                     "state": "GUARDED" if tree.exists(guard) or (root / guard).exists()
                     else "GUARD-MISSING", "by": guard, "holds": holds})
    grouped: dict[tuple[str, str], list[Site]] = {}
    for s in sites:
        grouped.setdefault((s.cls, partition(s.file)), []).append(s)
    for (cls, part), ss in sorted(grouped.items()):
        state = _state(part)
        if part in (ADR, RECORD):
            # a false claim in a dated record is history, not a defect; the
            # count is still reported so a later ruling can use it
            state = "RECORD"
        rows.append({"class": cls, "partition": part, "sites": len(ss),
                     "false": sum(s.false for s in ss), "state": state})
    files_by_part: dict[str, int] = {}
    for f in tree.files:
        if f.endswith(".md"):
            files_by_part[partition(f)] = files_by_part.get(partition(f), 0) + 1
    res = residual(tree, sites)
    return {
        "root": str(root), "mode": tree.mode,
        "md_files_by_partition": dict(sorted(files_by_part.items())),
        "rows": rows,
        "residual": {k: {"prose_lines": a, "unreached": b} for k, (a, b) in sorted(res.items())},
        "_sites": sites,
    }


def open_rows(report: dict) -> list[dict]:
    """Rows that keep the program open: a live claim class with no guard, an
    in-image doc nobody has classified, a missing guard, or a tracked doc no
    test image copies (it needs an OWNER, which this tool cannot see)."""
    return [r for r in report["rows"]
            if r["state"] in ("UNGUARDED", "NEEDS-RULING", "NOT-IN-IMAGE", "GUARD-MISSING")
            and (r["sites"] is None or r["sites"] > 0)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--list", metavar="CLASS")
    a = ap.parse_args(argv)
    rep = build_report(a.root)
    if a.list:
        for s in rep["_sites"]:
            if s.cls == a.list and s.false:
                print(f"{s.file}:{s.line}: [{partition(s.file)}] {s.text}")
        return 0
    if a.json:
        print(json.dumps({k: v for k, v in rep.items() if k != "_sites"}, indent=2))
    else:
        print(f"claim inventory  root={rep['root']}  mode={rep['mode']}")
        print("md files: " + "  ".join(f"{k}={v}" for k, v in rep["md_files_by_partition"].items()))
        print(f"{'class':30} {'partition':14} {'sites':>6} {'false':>6}  state")
        for r in rep["rows"]:
            s = "-" if r["sites"] is None else r["sites"]
            f = "-" if r["false"] is None else r["false"]
            by = f" {r['by']}" if "by" in r else ""
            print(f"{r['class']:30} {r['partition']:14} {s!s:>6} {f!s:>6}  {r['state']}{by}")
        print("residual prose (lines no class reaches):")
        for k, v in rep["residual"].items():
            print(f"  {k:14} {v['unreached']:>6} of {v['prose_lines']}")
    if a.check:
        rows = open_rows(rep)
        print(f"OPEN rows: {len(rows)}", file=sys.stderr)
        return 1 if rows else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
