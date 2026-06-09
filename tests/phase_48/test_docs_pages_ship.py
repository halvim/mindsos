"""Phase 48 S12 — the 3 new concept/reference docs ship and are in the nav
(PB-V Stream C absorb). Render-under-`mkdocs build --strict` is verified by the
ship ceremony; here we assert presence + nav wiring."""

from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]

_NEW_PAGES = [
    "docs/concepts/layers.md",
    "docs/concepts/society-of-mind.md",
    "docs/getting-started/facts-and-figures.md",
]


def test_new_docs_pages_present_and_nonempty():
    for rel in _NEW_PAGES:
        p = _ROOT / rel
        assert p.is_file(), f"missing doc page: {rel}"
        assert p.read_text(encoding="utf-8").strip(), f"empty doc page: {rel}"


def test_new_pages_wired_into_mkdocs_nav():
    mkdocs = _ROOT / "mkdocs.yml"
    if not mkdocs.is_file():
        pytest.skip("mkdocs.yml not present in this tree (not shipped in the test image; nav validated by `mkdocs build` on the docs host)")
    nav = mkdocs.read_text(encoding="utf-8")
    for rel in _NEW_PAGES:
        leaf = rel[len("docs/"):]
        assert leaf in nav, f"{leaf} not referenced in mkdocs.yml nav"
