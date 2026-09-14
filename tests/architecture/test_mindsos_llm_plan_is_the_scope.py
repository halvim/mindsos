"""`docs/plans/MINDSOS_LLM_PLAN.md` owns the scope of `mindsos_llm`, alone.

**Why this file exists.** The scope of `mindsos_llm` lived in four documents that
each restated it — the CR, ADR-0210, a ``STATE.pending_designs`` entry, and the
capability contract table, which a ruling in one chat promoted to "the definition
of done". Each went stale at least once, and every chat reconstructed the plan
from fragments. **Reconstruction is where opinion enters**: a week of work was
spent re-deciding settled things and re-deriving an item list nobody owned.

The plan file fixes that by being the single owner. This guard is what stops the
fix decaying the same way, and it checks two claims:

1. **The plan is mechanically readable.** Every item's state is exactly one of
   ``TODO``, ``DONE(<sha>)`` or ``OUT(<reason>)``, ids are unique, and the
   "DONE WHEN" line and the open items agree. *"Done" must not be a judgement a
   chat can make* — §0.3 of the plan — and a state column a chat can write prose
   into is a judgement column.
2. **No other document under ``docs/`` claims the scope.** A file may point at
   the plan; it may not restate what "done" means for this module. That is the
   defect this file is named for.

**What this guard does NOT claim.** That the plan agrees with
``STATE.pending_designs``. It cannot: **``STATE.json`` is not COPYed into the test
image** (measured — zero occurrences in the ``Dockerfile``, while ``docs`` is
copied). Putting it in the image so a guard could read it would let any other
lane's STATE edit redden this one, which is a worse failure than the drift it
would catch. Recorded as a known gap in the plan's §5, with a trigger.

RULES §9: a guard is born RED. The two fabricated-input tests below are that
birth certificate — the checkers are shown flagging a bad plan and a scope-stealing
document that were built for the purpose, so neither has to be committed to prove
it.
"""

from __future__ import annotations

import re
from pathlib import Path

PLAN_PATH = "docs/plans/MINDSOS_LLM_PLAN.md"

#: A state a chat cannot argue with. ``DONE`` must carry the sha that proves it.
_STATE = re.compile(r"^(TODO|DONE\([0-9a-f]{7,40}\)|OUT\(.+\))$")
_ROW = re.compile(r"^\|\s*(I-\d+)\s*\|(.+?)\|(.+?)\|\s*(.+?)\s*\|\s*$")
_DONE_WHEN = re.compile(r"^\*\*DONE WHEN:\s*(.+?)\.\*\*", re.MULTILINE)


def _repo_root() -> Path:
    # tests/ is COPYed, never installed, so this file has exactly one copy and
    # walking up from it is unambiguous. Anchoring on a repo-root marker file
    # would fail in the image, where RULES.md is absent.
    return Path(__file__).resolve().parents[2]


def parse_items(text: str) -> list[tuple[str, str, str]]:
    """``(id, filed_as, state)`` for every item row in the plan's table."""
    out = []
    for line in text.splitlines():
        m = _ROW.match(line)
        if m:
            out.append((m.group(1), m.group(3).strip(), m.group(4).strip()))
    return out


def bad_states(items) -> list[str]:
    return [i for i, _, state in items if not _STATE.match(state)]


def duplicate_ids(items) -> list[str]:
    seen, dupes = set(), []
    for i, _, _ in items:
        if i in seen:
            dupes.append(i)
        seen.add(i)
    return dupes


def done_when(text: str) -> list[str]:
    m = _DONE_WHEN.search(text)
    return [] if not m else [p.strip() for p in m.group(1).split(",")]


#: Phrasings that assert a completion criterion. ⚠ A FLOOR, NOT A CEILING: this
#: set is hand-written and a new wording escapes it. It was widened once already,
#: the day it was written — the first version matched only "definition of done"
#: and missed the capability contract, which claims the same thing in the words
#: ``"Complete" for a capability ... cannot mean``. **When you add a phrasing,
#: add it here rather than arguing the document is fine.**
SCOPE_PHRASINGS = (
    "definition of done",
    '"complete" for',
    "'complete' for",
    "means complete",
    "complete means",
)


def scope_claims(docs: dict[str, str]) -> list[str]:
    """Paths that claim this module's scope instead of pointing at the plan."""
    return sorted(
        path
        for path, body in docs.items()
        if path != PLAN_PATH
        and "mindsos_llm" in body
        and any(p in body.lower() for p in SCOPE_PHRASINGS)
        and PLAN_PATH not in body
    )


def _plan_text() -> str:
    return (_repo_root() / PLAN_PATH).read_text(encoding="utf-8")


def _docs() -> dict[str, str]:
    root = _repo_root()
    return {
        str(p.relative_to(root)): p.read_text(encoding="utf-8", errors="ignore")
        for p in (root / "docs").rglob("*.md")
    }


def test_the_plan_is_where_it_says_it_is():
    assert (_repo_root() / PLAN_PATH).is_file(), (
        f"{PLAN_PATH} is missing. It owns the scope of mindsos_llm; without it "
        "every chat reconstructs the item list from prose, which is the defect "
        "this file exists to prevent."
    )


def test_every_item_state_is_from_the_closed_set():
    items = parse_items(_plan_text())
    assert items, "no item rows parsed - the table's shape changed"
    assert not bad_states(items), (
        "an item's state must be TODO, DONE(<sha>) or OUT(<reason>) and nothing "
        f"else, so 'done' is not a judgement a chat makes: {bad_states(items)}"
    )


def test_item_ids_are_unique():
    assert not duplicate_ids(parse_items(_plan_text()))


def test_the_open_items_and_the_done_when_line_agree():
    text = _plan_text()
    items = parse_items(text)
    required = done_when(text)
    assert required, "the DONE WHEN line is missing or unparseable"
    ids = {i for i, _, _ in items}
    assert set(required) <= ids, f"DONE WHEN names unknown ids: {set(required) - ids}"
    out = {i for i, _, s in items if s.startswith("OUT(")}
    assert not (set(required) & out), (
        f"DONE WHEN requires an item marked OUT: {set(required) & out}"
    )
    todo = {i for i, _, s in items if s == "TODO"}
    assert todo <= set(required), (
        "an open item that nothing requires is scope nobody agreed to: "
        f"{todo - set(required)}"
    )


def test_no_other_document_claims_this_module_s_scope():
    claimed = scope_claims(_docs())
    assert not claimed, (
        "these documents state a definition of done for mindsos_llm instead of "
        f"pointing at {PLAN_PATH}. Four such documents, each stale, are why the "
        f"plan exists: {claimed}"
    )


def test_the_checkers_flag_a_fabricated_bad_plan():
    fabricated = (
        "| I-1 | a thing | filed-as | DONE(abc1234) |\n"
        "| I-1 | a repeat | filed-as | mostly done, I think |\n"
        "| I-9 | unrequired | filed-as | TODO |\n"
        "\n**DONE WHEN: I-1.**\n"
    )
    items = parse_items(fabricated)
    assert bad_states(items) == ["I-1"], "a prose state must be refused"
    assert duplicate_ids(items) == ["I-1"], "a repeated id must be refused"
    assert done_when(fabricated) == ["I-1"]
    todo = {i for i, _, s in items if s == "TODO"}
    assert todo - set(done_when(fabricated)) == {"I-9"}, (
        "an open item absent from DONE WHEN must be visible"
    )


def test_the_checker_flags_a_fabricated_scope_claim():
    assert scope_claims({
        "docs/somewhere/other.md": "the definition of done for mindsos_llm is here",
    }) == ["docs/somewhere/other.md"]
    assert scope_claims({
        "docs/somewhere/other.md": (
            "the definition of done for mindsos_llm lives in " + PLAN_PATH
        ),
    }) == [], "a document that POINTS at the plan is correct and must pass"
