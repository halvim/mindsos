"""Every live page declares what its prose was last read against.

Doc-fix mechanism: page verification. The claim inventory measured it at
c088a4d: 5808 of 6618 live prose lines (88%) carry no reference any extractor
can check. Those lines get neither a guard nor an owner -- "the finder returns
a Pipeline" was found by READING, and no oracle exists for it. Owner ruling
2026-09-19: a live page either is held true by guards or states the commit its
prose was last read against.

THE KEY: front-matter `verified_at: <sha>` or `verified_at: unverified`.
`unverified` is the honest value for a page nobody has re-read; it is NOT a
loophole, because `tools/claim_inventory.py --check` counts every unverified
page as an OPEN row, so the program's finish line stays red until the pages
are actually read. This guard holds the weaker, mechanical half: the key is
present and well-formed on every live page.

WHY NOT `last_confirmed_phase` (79 live pages carry it): phases stopped
advancing at 50, and three phase sentinels
(tests/phase_35, tests/phase_36, tests/phase_38) pin exact strings in it. It
is left untouched.

WHAT THIS CANNOT DO: the test image has no `.git`, so a sha's existence is not
checked here -- only its shape. The inventory, run in a checkout, is where a
stale or unknown sha is reported.

FLOOR, NOT CEILING: presence is not verification. The count is the point.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_TOOL = _ROOT / "tools" / "claim_inventory.py"


def _load():
    spec = importlib.util.spec_from_file_location("claim_inventory_va", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


inv = _load()


def test_the_premise_holds_so_the_guard_cannot_pass_vacuously():
    assert (_ROOT / "docs").is_dir(), "docs/ missing - the image did not copy it"
    ver = inv.verification(inv.load_tree(_ROOT))
    assert ver["live_pages"] > 50, f"only {ver['live_pages']} live pages - partition() is wrong"


def test_every_live_page_declares_verified_at():
    ver = inv.verification(inv.load_tree(_ROOT))
    assert not ver["bad"], (
        f"{len(ver['bad'])} live page(s) without a well-formed `verified_at` "
        f"(a sha or `unverified`):\n" + "\n".join(sorted(ver["bad"]))
    )


def test_the_phase_marker_is_left_alone():
    """`last_confirmed_phase` is pinned by the phase sentinels; this mechanism
    adds a key, it does not migrate that one."""
    pages = [p for p in (_ROOT / "docs").rglob("*.md")
             if "last_confirmed_phase" in inv.front_matter(p.read_text(encoding="utf-8", errors="replace"))]
    assert len(pages) > 50, "the phase marker vanished - a sweep overwrote front matter"


# -- fabricated corners ----------------------------------------------------

def _tree(root: Path, page: str) -> Path:
    (root / "docs" / "usage").mkdir(parents=True)
    (root / "docs" / "usage" / "p.md").write_text(page)
    (root / "docs" / "changelog").mkdir()
    (root / "docs" / "changelog" / "old.md").write_text("no key here, it is a record\n")
    return root


def _bad(root: Path):
    return inv.verification(inv.load_tree(root))["bad"]


def test_a_sha_is_accepted(tmp_path):
    assert _bad(_tree(tmp_path, "---\nverified_at: 8cb83d8\n---\n\nprose\n")) == []


def test_unverified_is_accepted_and_counted(tmp_path):
    ver = inv.verification(inv.load_tree(_tree(tmp_path, "---\nverified_at: unverified\n---\n\nprose\n")))
    assert ver["bad"] == [] and ver["unverified"] == 1 and ver["verified"] == 0


def test_a_missing_key_is_reported(tmp_path):
    assert _bad(_tree(tmp_path, "# page\n\nprose\n")) == ["docs/usage/p.md"]


def test_a_date_is_not_a_sha(tmp_path):
    assert _bad(_tree(tmp_path, "---\nverified_at: 2026-09-20\n---\n\nprose\n")) == ["docs/usage/p.md"]


def test_a_record_page_needs_no_key(tmp_path):
    root = _tree(tmp_path, "---\nverified_at: unverified\n---\n\nprose\n")
    assert _bad(root) == [] and inv.verification(inv.load_tree(root))["live_pages"] == 1


def test_the_key_must_be_in_the_front_matter_not_the_body(tmp_path):
    assert _bad(_tree(tmp_path, "# page\n\nverified_at: 8cb83d8\n")) == ["docs/usage/p.md"]
