"""Every reference a live doc makes resolves in this tree.

Doc-fix mechanism: live references. A live page (docs/ outside the dated
records, the docs/decisions index pages, README.md, and the plans named in
`tools/claim_inventory.py:LIVE_CONFIRMATION_DOCS`) names repo paths, ADR
numbers, relative links and `mindsos_*` dotted symbols. A reader follows them.
Measured at bca051d by `tools/claim_inventory.py`: 30 did not resolve, 3 of
them TRUE statements about a retired ADR number ("ADR-0117 Withdrawn").

THE LOGIC IS THE INVENTORY'S, not a copy: this guard calls
`claim_inventory.scan` and `partition`, so the inventory's counts and this
guard cannot disagree. "Live" is defined there, once.

WHAT IS TRUE WITHOUT RESOLVING -- derived, never typed:
* a missing ADR number that the ADR index's own "numbers not in use" note
  lists, on a line that itself says Withdrawn / not in use;
* a template path (`PHASE_NN_CONFIRMED.md`, `NNNN-slug.md`);
* a path whose whole top directory is absent from the tree (the test image
  does not copy `projects/`) -- unjudgeable, so skipped.

HOW TO FIX A RED: read the line first. A moved target gets the new path. A
target that never existed in this repo (`git log --all -- <path>` empty) gets
named without its directory and said so ("never committed to this repo"). An
untracked file is named by bare filename. Do NOT rewrite a dated record to
satisfy this -- dated records are outside the domain on purpose.

FLOOR, NOT CEILING: four extractor classes only; a symbol re-exported from
another module is taken as present. See the inventory's docstring.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_TOOL = _ROOT / "tools" / "claim_inventory.py"
_DOMAIN = frozenset({"live", "index"})


def _load():
    spec = importlib.util.spec_from_file_location("claim_inventory_lr", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


inv = _load()


def _false_live(root: Path) -> list[str]:
    tree = inv.load_tree(root)
    return [
        f"{s.file}:{s.line}: [{s.cls}] {s.text}"
        for s in inv.scan(tree)
        if s.false and inv.partition(s.file) in _DOMAIN
    ]


def test_the_premise_holds_so_the_guard_cannot_pass_vacuously():
    assert (_ROOT / "docs").is_dir(), "docs/ missing - the image did not copy it"
    assert inv.GUARDED_EXTRACTED["live-doc-references-resolve"] == _DOMAIN
    tree = inv.load_tree(_ROOT)
    live = [s for s in inv.scan(tree) if inv.partition(s.file) in _DOMAIN]
    per_class = {c: sum(s.cls == c for s in live) for c in inv.UNGUARDED_CLASSES}
    assert all(per_class.values()), f"an extractor found nothing live: {per_class}"
    assert inv.retired_adr_numbers(tree), "the ADR index's 'numbers not in use' note was not found"


def test_every_live_reference_resolves():
    bad = _false_live(_ROOT)
    assert not bad, f"{len(bad)} live doc reference(s) do not resolve:\n" + "\n".join(bad)


# -- fabricated corners ----------------------------------------------------

_INDEX = '!!! note "ADRs 0003, 0004 — numbers not in use"\n'


def _tree(root: Path, page: str) -> Path:
    (root / "docs" / "decisions" / "adr").mkdir(parents=True)
    (root / "docs" / "decisions" / "adr" / "README.md").write_text(_INDEX)
    (root / "docs" / "decisions" / "adr" / "0001-a.md").write_text("# ADR\n")
    (root / "docs" / "usage").mkdir()
    (root / "docs" / "usage" / "p.md").write_text(page)
    (root / "confirmation_docs").mkdir()
    (root / "confirmation_docs" / "OLD_NOTES.md").write_text("See ADR-0999.\n")
    return root


def test_a_retired_number_named_as_retired_is_true(tmp_path):
    assert _false_live(_tree(tmp_path, "ADR-0003 was Withdrawn.\nADR-0004 is not in use.\n")) == []


def test_a_retired_number_used_as_a_pointer_is_false(tmp_path):
    bad = _false_live(_tree(tmp_path, "See ADR-0003 for the design.\n"))
    assert len(bad) == 1 and "ADR-0003" in bad[0]


def test_withdrawn_does_not_excuse_a_number_the_index_never_retired(tmp_path):
    bad = _false_live(_tree(tmp_path, "ADR-0005 was Withdrawn.\n"))
    assert len(bad) == 1 and "ADR-0005" in bad[0]


def test_a_dated_record_is_outside_the_domain(tmp_path):
    assert _false_live(_tree(tmp_path, "Per ADR-0001.\n")) == []


def test_a_live_plan_is_inside_the_domain(tmp_path):
    root = _tree(tmp_path, "Per ADR-0001.\n")
    (root / "confirmation_docs" / "CORE_RECONCILIATION_PLAN.md").write_text("See `docs/gone.md`.\n")
    bad = _false_live(root)
    assert len(bad) == 1 and "docs/gone.md" in bad[0]
