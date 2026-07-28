"""Phase 43 PR2 — consolidate.py retarget per R0 PB-43-9.

Asserts (via source-code inspection):

* ``type_="Episode"`` writes are in use (validate_node + write_and_validate).
* ``episode_id`` is the canonical record key (not ``memory_id``).
* ``NOTE(phase-48-retarget)`` comments are absent (closed at Phase 43).
* The capacity module docstring reflects the Phase 43 retarget.
"""

from __future__ import annotations

from pathlib import Path


_CONSOLIDATE_PATH = (
    Path(__file__).parents[2]
    / "mindsos_capacity"
    / "builtins"
    / "consolidate.py"
)


def _read() -> str:
    return _CONSOLIDATE_PATH.read_text()


def test_writes_type_episode() -> None:
    body = _read()
    assert 'type_="Episode"' in body
    # Both validate_node + write_and_validate now write Episode.
    assert body.count('type_="Episode"') >= 2


def test_episode_id_record_key() -> None:
    body = _read()
    assert "episode_id" in body
    # Dream PRE-0 Slice 1b: the record key is now bound to a local
    # (``episode_id = record["episode_id"]``) then threaded into the write.
    assert 'record["episode_id"]' in body
    assert "episode_id=episode_id" in body


def test_no_memory_id_in_active_code() -> None:
    body = _read()
    # ``memory_id`` may appear in retarget-history prose, but the
    # active record-key extraction must not.
    assert 'memory_id=record["memory_id"]' not in body


def test_phase_48_retarget_note_comments_gone() -> None:
    body = _read()
    assert "NOTE(phase-48-retarget)" not in body, (
        "Phase 43 PR2 commit 3 closes the two-phase tech-debt window; "
        "NOTE comments must be removed"
    )


def test_docstring_reflects_phase_43_retarget() -> None:
    body = _read()
    # Module docstring should mention the Phase 43 retarget event.
    assert "Phase 43" in body
    assert "retarget" in body.lower()
