"""Phase 49 S2 — the ``end-to-end.md`` cookbook page ships and is wired into
the nav (PB-W; text-realm precedent). Render-under-``mkdocs build --strict`` is
verified by the ship ceremony on the docs host (``mkdocs.yml`` is not copied
into the test image); here we assert presence + nav wiring, mirroring the
Phase-48 docs-ship test."""

from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PAGE = "docs/usage/cookbook/end-to-end.md"


def test_cookbook_page_present_and_nonempty():
    p = _ROOT / _PAGE
    assert p.is_file(), f"missing cookbook page: {_PAGE}"
    body = p.read_text(encoding="utf-8").strip()
    assert body, f"empty cookbook page: {_PAGE}"
    # Honest-boundary discipline (text-realm precedent): the seam + the WSD
    # gate + the no-physical-index decision must be stated.
    for token in ("space_split", "v0", "WSD", "index"):
        assert token in body, f"{token!r} not documented in the cookbook page"


def test_cookbook_page_wired_into_mkdocs_nav():
    mkdocs = _ROOT / "mkdocs.yml"
    if not mkdocs.is_file():
        pytest.skip(
            "mkdocs.yml not present in this tree (not shipped in the test image; "
            "nav validated by `mkdocs build` on the docs host)"
        )
    nav = mkdocs.read_text(encoding="utf-8")
    assert _PAGE[len("docs/"):] in nav, "end-to-end.md not referenced in mkdocs.yml nav"
