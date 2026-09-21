"""No live page describes the retired "Model C" layout as the current one.

Doc-fix mechanism: the retired-layout frame. Until Phase 38 the ADRs lived
OUTSIDE this repo, in a separate project-root tree, and the docs said so
("Model C hybrid", "parent tree", `Layered Intelligence/`, `halvim_mindsos/`).
The ADRs have lived in `docs/decisions/adr/` ever since, but verification
batches 1 and 2 (PRs #230, #231) found two live pages still teaching the old
layout as present fact -- `repo-layout.md` said ADRs live outside the repo, and
`internals/capacity.md` deferred to a copy of itself that does not exist. Two
pages with the same lie is a class, so it gets a guard.

THE RULE: in a live or index doc (`tools/claim_inventory.partition` -- the one
definition of "live"), a line naming the retired layout must itself say
`retired`. A true sentence ABOUT the retired layout is fine; one that presents
it as the current arrangement is not. The same shape as a retired ADR number
being true only on a line that says Withdrawn.

Tokens are case-sensitive on purpose: a case-insensitive `Model C` matched
"model call" in the LLM docs, which is how the class was first over-counted.

FLOOR, NOT CEILING: a sentence can describe the old layout without these tokens.
Dated records (ADRs, confirmation docs, the changelog) are outside the domain.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_TOOL = _ROOT / "tools" / "claim_inventory.py"
_DOMAIN = frozenset({"live", "index"})

TOKENS = re.compile(r"\bModel C\b|\b[Pp]arent[- ]tree\b|Layered Intelligence|halvim_mindsos")
SAYS_RETIRED = re.compile(r"\bretired\b", re.IGNORECASE)


def _load():
    spec = importlib.util.spec_from_file_location("claim_inventory_mc", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


inv = _load()


def find_problems(root: Path) -> list[str]:
    tree = inv.load_tree(root)
    out = []
    for rel in tree.files:
        if not rel.endswith(".md") or inv.partition(rel) not in _DOMAIN:
            continue
        text = (root / rel).read_text(encoding="utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            if TOKENS.search(line) and not SAYS_RETIRED.search(line):
                out.append(f"{rel}:{n}: {line.strip()[:120]}")
    return out


def test_the_premise_holds_so_the_guard_cannot_pass_vacuously():
    assert (_ROOT / "docs").is_dir(), "docs/ missing - the image did not copy it"
    tree = inv.load_tree(_ROOT)
    assert any(inv.partition(f) == "live" for f in tree.files), "no live pages found"


def test_no_live_page_presents_the_retired_layout_as_current():
    bad = find_problems(_ROOT)
    assert not bad, (
        f"{len(bad)} live line(s) name the retired Model C layout without saying it is retired:\n"
        + "\n".join(bad)
    )


# -- fabricated corners ----------------------------------------------------

def _tree(root: Path, live: str, record: str = "Model C is how it works.\n") -> Path:
    (root / "docs" / "usage").mkdir(parents=True)
    (root / "docs" / "usage" / "p.md").write_text(live)
    (root / "docs" / "changelog").mkdir()
    (root / "docs" / "changelog" / "old.md").write_text(record)
    return root


def test_a_line_saying_retired_is_true(tmp_path):
    assert find_problems(_tree(tmp_path, "The retired Model C layout kept ADRs elsewhere.\n")) == []


def test_the_layout_as_present_fact_is_reported(tmp_path):
    bad = find_problems(_tree(tmp_path, "ADRs live in the parent tree per Model C.\n"))
    assert len(bad) == 1 and "p.md:1" in bad[0]


def test_every_token_is_caught(tmp_path):
    page = "per Model C\nthe parent-tree copy\nunder Layered Intelligence/\nnot halvim_mindsos/\n"
    assert len(find_problems(_tree(tmp_path, page))) == 4


def test_model_call_is_not_model_c(tmp_path):
    assert find_problems(_tree(tmp_path, "The model call can fail.\nA model config.\n")) == []


def test_a_dated_record_is_outside_the_domain(tmp_path):
    assert find_problems(_tree(tmp_path, "nothing here\n")) == []
