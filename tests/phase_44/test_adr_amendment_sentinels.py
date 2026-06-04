"""Phase 44 PR1 sentinel — new ADR + amendment landing checks.

Verifies post-PR1.1 state of:

* ADR-0160 (NEW) — L0 persister impls + MetagraphDump serialization.
* ADR-0161 (NEW) — KL version-pinned read + retire-version lazy-inline hook.
* ADR-0011 amendment-3 — MetagraphDump + both persisters + MindsOSServer class.
* ADR-0004 amendment-2 — SQLite-blob Local backing store permitted.

Rail C chain link from Phase 38.
"""

from __future__ import annotations

from pathlib import Path

_ADR_DIR = Path(__file__).parents[2] / "docs" / "decisions" / "adr"


def _read(name: str) -> str:
    return (_ADR_DIR / name).read_text()


def test_adr_0160_present_and_accepted() -> None:
    body = _read("0160-l0-persister-impls.md")
    assert "status: Accepted" in body
    assert "**Status:** Accepted" in body


def test_adr_0160_names_dump_and_both_persisters() -> None:
    body = _read("0160-l0-persister-impls.md")
    for token in (
        "MetagraphDump",
        "FalkorDBLocalPersister",
        "SQLiteLocalPersister",
        "promoted",
        "native",
        "dump_schema_version",
        "locals.db",
    ):
        assert token in body, f"{token!r} missing from ADR-0160 body"


def test_adr_0161_present_and_accepted() -> None:
    body = _read("0161-kl-version-read-and-retire.md")
    assert "status: Accepted" in body
    assert "**Status:** Accepted" in body


def test_adr_0161_names_surface_and_retire_marker() -> None:
    body = _read("0161-kl-version-read-and-retire.md")
    for token in (
        "read_at_version",
        "retire_version",
        "_retired_inline_pending",
        "RESERVED_PROPERTY_KEYS",
        "Phase 48",
    ):
        assert token in body, f"{token!r} missing from ADR-0161 body"


def test_adr_0011_amendment_3_present() -> None:
    body = _read("0011-local-persister-protocol.md")
    assert "### amendment-3 (Phase 44 ship" in body
    after_am3 = body.split("### amendment-3", 1)[1]
    for token in (
        "MetagraphDump",
        "FalkorDBLocalPersister` + `SQLiteLocalPersister` ship",
        "clean cut",
    ):
        assert token in after_am3, f"{token!r} missing from ADR-0011 amendment-3"


def test_adr_0004_amendment_2_present() -> None:
    body = _read("0004-split-persistence.md")
    assert "### amendment-2 (Phase 44 ship" in body
    after_am2 = body.split("### amendment-2 (Phase 44 ship", 1)[1]
    for token in (
        "SQLiteLocalPersister",
        "opaque `MetagraphDump` blob",
        "locals.db",
        "local-first",
    ):
        assert token in after_am2, f"{token!r} missing from ADR-0004 amendment-2"
