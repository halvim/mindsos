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
