"""Gate guard: ADR status must agree across file, README, and summaries.

Wraps ``tools/check_adr_status_consistency.py`` so the existing
``pytest tests/`` gate fails loud if any ADR's status drifts between its
front-matter, its prose ``**Status:**`` line, the ADR index README, and
the per-layer summary tables. Added in the 2026-07 doc-vs-code audit to
stop the decision index from silently rotting again.

2026-08-01: it rotted anyway. The checker's table-header detection never
matched the README's actual header, so ``check_index`` was a no-op on the
one file it exists to police, and the index had stopped at ADR-0137 with
76 files missing and 18 rows disagreeing with their file. A green guard
that cannot fail is worse than no guard, so the tests below now pin the
*failure* behaviour as well as the passing state: each of the three
detectable defects (missing row, disagreeing row, phantom row) has a test
that asserts the checker reports it.
"""

import importlib.util
from pathlib import Path

_CHECKER = (
    Path(__file__).resolve().parent.parent
    / "tools"
    / "check_adr_status_consistency.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("adr_status_checker", _CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def adjudicated_sites(root):
    """Report mode (`tools/claim_inventory.py`, the emit contract): the
    `file:line` sites this guard adjudicated. The judging lives in the
    checker, so the report does too -- built on the same walks as its
    problem lists (`_judge_rows`, `_judge_page`). See the checker's
    `adjudicated_sites` for exactly which lines are judged."""
    return _load().adjudicated_sites(Path(root))


def test_adr_status_consistent_across_docs():
    mod = _load()
    adr_status, file_problems = mod.load_adr_statuses()
    assert adr_status, "no ADRs found — checker path or glob is wrong"
    assert not file_problems, (
        "ADR file status inconsistencies (front-matter vs prose):\n  "
        + "\n  ".join(file_problems)
    )
    index_problems = mod.check_index(mod.README, adr_status, require_complete=True)
    for path in sorted(mod.SUMMARY_DIR.glob("*.md")):
        index_problems += mod.check_index(path, adr_status)
    assert not index_problems, (
        "ADR index/summary status disagrees with the ADR files:\n  "
        + "\n  ".join(index_problems)
    )


def test_every_adr_file_has_an_index_row():
    """The README claims to be the full index. Hold it to that.

    This is the check whose absence let the index stop at ADR-0137 while
    the guard stayed green: only *disagreeing* rows were ever reported,
    never *missing* ones.
    """
    mod = _load()
    adr_status, _ = mod.load_adr_statuses()
    listed = {fname for _, fname in mod._iter_table_rows(mod.README.read_text("utf-8"))}
    missing = sorted(set(adr_status) - listed)
    assert not missing, (
        f"{len(missing)} ADR file(s) absent from docs/decisions/adr/README.md:\n  "
        + "\n  ".join(missing)
    )


def test_index_rows_are_actually_parsed():
    """Guard against the guard silently disarming itself.

    The 2026-07 version yielded zero rows because its header detection
    required a cell containing "adr", which the README header has no such
    cell for. Nothing failed — it just stopped checking. Assert that the
    README's table is genuinely being read.
    """
    mod = _load()
    rows = list(mod._iter_table_rows(mod.README.read_text("utf-8")))
    assert len(rows) > 100, (
        f"only {len(rows)} index rows parsed from README.md — the table-header "
        "detection has stopped matching, so the index is no longer checked"
    )


def test_duplicate_adr_numbers_are_not_collapsed():
    """ADR-0172 and ADR-0201 each have amendment files sharing their number.

    Keying statuses by ``filename[:4]`` silently discarded all but one per
    number. Keyed by filename now — assert every file is present.
    """
    mod = _load()
    adr_status, _ = mod.load_adr_statuses()
    on_disk = {p.name for p in mod.ADR_DIR.glob("[0-9][0-9][0-9][0-9]-*.md")}
    assert set(adr_status) == on_disk, (
        "statuses were not loaded one-per-file: "
        f"{sorted(on_disk - set(adr_status))} dropped"
    )


def _readme_variant(tmp_path, mod, transform):
    """Copy the real ADR tree, mutate README, and re-point the checker at it."""
    import shutil

    dst = tmp_path / "adr"
    shutil.copytree(mod.ADR_DIR, dst)
    readme = dst / "README.md"
    readme.write_text(transform(readme.read_text("utf-8")), "utf-8")
    return readme


def test_missing_row_is_reported(tmp_path):
    mod = _load()
    adr_status, _ = mod.load_adr_statuses()
    victim = "0205-abstraction-levels.md"
    readme = _readme_variant(
        tmp_path,
        mod,
        lambda s: "\n".join(l for l in s.split("\n") if victim not in l),
    )
    problems = mod.check_index(readme, adr_status, require_complete=True)
    assert any(victim in p and "no row" in p for p in problems), problems


def test_disagreeing_row_is_reported(tmp_path):
    mod = _load()
    adr_status, _ = mod.load_adr_statuses()
    readme = _readme_variant(
        tmp_path,
        mod,
        lambda s: s.replace(
            "| [0205](0205-abstraction-levels.md) | Abstraction levels — one graph at several resolutions | Accepted |",
            "| [0205](0205-abstraction-levels.md) | Abstraction levels — one graph at several resolutions | Deferred |",
            1,
        ),
    )
    problems = mod.check_index(readme, adr_status, require_complete=True)
    assert any("0205" in p and "!=" in p for p in problems), problems


def test_phantom_row_is_reported(tmp_path):
    mod = _load()
    adr_status, _ = mod.load_adr_statuses()
    readme = _readme_variant(
        tmp_path,
        mod,
        lambda s: s.replace(
            "| [0001](0001-dedicated-server-layer.md)",
            "| [9999](9999-not-an-adr.md) | Phantom | Accepted | L1 | — |\n"
            "| [0001](0001-dedicated-server-layer.md)",
            1,
        ),
    )
    problems = mod.check_index(readme, adr_status, require_complete=True)
    assert any("9999-not-an-adr.md" in p for p in problems), problems


# --------------------------------------------------------------------------
# The two decision index pages (2026-09-21, STATE.pending_designs
# proposed-md-lists-shipped-adrs-as-unscheduled). proposed.md said its
# entries were "not yet scheduled" while most had shipped; superseded.md
# called two long-superseded ADRs Accepted. Nothing read either page.
# --------------------------------------------------------------------------


def test_index_pages_state_true_statuses():
    mod = _load()
    adr_status, _ = mod.load_adr_statuses()
    for page in mod.INDEX_PAGES:
        assert page.is_file(), f"{page} missing - the guard would pass vacuously"
        rows = list(mod._iter_table_rows(page.read_text("utf-8")))
        assert rows, f"{page.name}: no linked status rows parsed - the guard is disarmed"
    problems = mod.check_index_pages(adr_status)
    assert not problems, (
        "a decision index page states a status the ADR file does not have:\n  "
        + "\n  ".join(problems)
    )


def _page(tmp_path, text):
    p = tmp_path / "page.md"
    p.write_text(text, "utf-8")
    return p


#: fabricated statuses, so every corner below is independent of the real tree
_FAKE = {
    "0001-a.md": "accepted",
    "0002-b.md": "proposed",
    "0003-c.md": "superseded",
    "0004-d.md": "deferred",
}


def test_linked_status_cell_in_adr_relative_form_is_checked(tmp_path):
    mod = _load()
    page = _page(tmp_path, "| ADR # | Status |\n|---|---|\n| [0001](adr/0001-a.md) | Proposed |\n")
    assert any("0001-a.md" in p for p in mod.check_index_page(page, _FAKE))


def test_bare_number_row_with_a_status_is_reported_and_not_in_use_is_not(tmp_path):
    mod = _load()
    page = _page(
        tmp_path,
        "| ADR # | Status |\n|---|---|\n| 0001 | Proposed |\n| 0009 | never written (number not in use) |\n",
    )
    problems = mod.check_index_page(page, _FAKE)
    assert len(problems) == 1 and "'0001'" in problems[0], problems


def test_open_heading_rule(tmp_path):
    mod = _load()
    page = _page(
        tmp_path,
        "## Open\n### Thing — ADR-0001\n### Other — ADR-0002\n### Later — ADR-0004\n"
        "### Done — Resolved by ADR-0001\n## Resolved — record\n### Old — ADR-0003\n",
    )
    problems = mod.check_index_page(page, _FAKE, headings_claim_open=True)
    assert len(problems) == 1 and "ADR-0001" in problems[0], problems


def test_effective_supersession_rows_must_be_superseded(tmp_path):
    mod = _load()
    page = _page(
        tmp_path,
        "## Effective supersessions\n| Original | Superseded by |\n|---|---|\n"
        "| [0003](adr/0003-c.md) | [0001](adr/0001-a.md) |\n| [0001](adr/0001-a.md) | [0002](adr/0002-b.md) |\n"
        "## Supersessions in flight\n| Original | Superseded by |\n|---|---|\n| [0001](adr/0001-a.md) | x |\n",
    )
    problems = mod.check_index_page(page, _FAKE, superseded_section="Effective supersessions")
    assert len(problems) == 1 and "0001-a.md" in problems[0], problems


# --------------------------------------------------------------------------
# Report mode: the sites the checker adjudicated (the claim-coverage gate).
# --------------------------------------------------------------------------

_D = "docs/decisions"


def _tree(root):
    files = {
        f"{_D}/adr/0001-a.md": "---\nstatus: accepted\n---\n# A\n\n**Status:** Accepted\n",
        f"{_D}/adr/0002-b.md": "---\nstatus: proposed\n---\n# B\n",
        f"{_D}/adr/README.md": (
            "# Index\n\n| ADR | Title | Status |\n|---|---|---|\n"
            "| [0001](0001-a.md) | A | Accepted |\n| [0002](0002-b.md) | B | Deferred |\n"
            "\nProse naming 0001-a.md outside any table.\n"
        ),
        f"{_D}/summary/core.md": (
            "| ADR | Status |\n|---|---|\n| [0001](../adr/0001-a.md) | Accepted |\n"
            "| plain cell | Accepted |\n"
        ),
        f"{_D}/proposed.md": (
            "## Open\n### Thing — ADR-0002\n### Done — ADR-0001\n### No number — ADR\n"
            "| ADR # | Status |\n|---|---|\n| 0001 | Proposed |\n| [0002](adr/0002-b.md) | Proposed |\n"
        ),
        f"{_D}/superseded.md": (
            "## Effective supersessions\n| Original | Superseded by |\n|---|---|\n"
            "| [0001](adr/0001-a.md) | [0002](adr/0002-b.md) |\n## Other\n| [0002](adr/0002-b.md) | x |\n"
        ),
    }
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, "utf-8")
    return root


def test_it_emits_the_judged_lines_and_only_those(tmp_path):
    """ADR files: their status lines. README and summary: the linked status
    rows, not the header, the separator, an unlinked row or prose. proposed.md:
    the two headings naming an ADR number (not the one naming none), the
    bare-number row and the linked row. superseded.md: the linked row of the
    effective section only."""
    assert adjudicated_sites(_tree(tmp_path)) == [
        (f"{_D}/adr/0001-a.md", 2),
        (f"{_D}/adr/0001-a.md", 6),
        (f"{_D}/adr/0002-b.md", 2),
        (f"{_D}/adr/README.md", 5),
        (f"{_D}/adr/README.md", 6),
        (f"{_D}/proposed.md", 2),
        (f"{_D}/proposed.md", 3),
        (f"{_D}/proposed.md", 7),
        (f"{_D}/proposed.md", 8),
        (f"{_D}/summary/core.md", 3),
        (f"{_D}/superseded.md", 4),
    ]


def test_a_reported_problem_sits_on_an_emitted_line(tmp_path):
    """The walk that emits a line is the walk that reports it: the README's
    disagreeing row is line 6, and the index page's three problems are on
    lines 3, 7 (proposed.md) and 4 (superseded.md)."""
    mod = _load()
    root = _tree(tmp_path)
    readme = (root / _D / "adr" / "README.md").read_text("utf-8")
    assert [(n, bool(p)) for n, p in mod._judge_rows(readme, "README.md", _FAKE_TREE, set())] == [
        (5, False), (6, True),
    ]
    proposed = (root / _D / "proposed.md").read_text("utf-8")
    assert sorted((n, bool(p)) for n, p in mod._judge_page(proposed, "proposed.md", _FAKE_TREE, headings_claim_open=True)) == [
        (2, False), (3, True), (7, True),
    ]
    superseded = (root / _D / "superseded.md").read_text("utf-8")
    assert [(n, bool(p)) for n, p in mod._judge_page(
        superseded, "superseded.md", _FAKE_TREE, superseded_section="Effective supersessions")] == [(4, True)]
    emitted = set(adjudicated_sites(root))
    for rel, n in ((f"{_D}/adr/README.md", 6), (f"{_D}/proposed.md", 3), (f"{_D}/proposed.md", 7), (f"{_D}/superseded.md", 4)):
        assert (rel, n) in emitted


#: the statuses of the fabricated tree above
_FAKE_TREE = {"0001-a.md": "accepted", "0002-b.md": "proposed"}
