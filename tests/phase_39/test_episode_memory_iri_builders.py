"""Phase 39 ``episode_iri`` + ``memory_composite_iri`` builder coverage.

Per ADR-0044 §amendment-3: retired ``memory_iri`` split into two
builders, one per NodeType under ``episodic_memories`` role-graph.
Both enforce ``_USER_ID_RE`` per ADR-0044 §amendment-1.
"""

from __future__ import annotations

import pytest

from mindsos_knowledge import (
    RefFormatError,
    episode_iri,
    memory_composite_iri,
    parse_iri,
)


# ── episode_iri happy path ─────────────────────────────────────────────


def test_episode_iri_happy() -> None:
    iri = episode_iri("1", "alice", "e-001")
    assert iri == "episodic-memories-1:episode:alice:e-001"


def test_episode_iri_round_trip() -> None:
    iri = episode_iri("1", "alice", "e-001")
    parsed = parse_iri(iri)
    assert parsed.full == iri
    assert parsed.role == "episodic_memories"
    assert parsed.kind == "episode"


# ── memory_composite_iri happy path ────────────────────────────────────


def test_memory_composite_iri_happy() -> None:
    iri = memory_composite_iri("1", "alice", "m-001")
    assert iri == "episodic-memories-1:memory:alice:m-001"


def test_memory_composite_iri_round_trip() -> None:
    iri = memory_composite_iri("1", "alice", "m-001")
    parsed = parse_iri(iri)
    assert parsed.full == iri
    assert parsed.role == "episodic_memories"
    assert parsed.kind == "memory"


# ── _USER_ID_RE enforcement (ADR-0044 §amendment-1) ────────────────────


@pytest.mark.parametrize(
    "bad_uid",
    ["", "-leading-dash", "a:b", "user@example", "user with space", "a" * 65],
)
def test_episode_iri_rejects_bad_user_id(bad_uid: str) -> None:
    with pytest.raises(RefFormatError, match="user_id"):
        episode_iri("1", bad_uid, "e1")


@pytest.mark.parametrize(
    "bad_uid",
    ["", "-leading-dash", "a:b", "user@example", "user with space", "a" * 65],
)
def test_memory_composite_iri_rejects_bad_user_id(bad_uid: str) -> None:
    with pytest.raises(RefFormatError, match="user_id"):
        memory_composite_iri("1", bad_uid, "m1")


def test_episode_iri_accepts_uuid_form_user_id() -> None:
    iri = episode_iri("1", "user-abc-123", "e1")
    assert iri == "episodic-memories-1:episode:user-abc-123:e1"


def test_memory_composite_iri_accepts_uuid_form_user_id() -> None:
    iri = memory_composite_iri("1", "user-abc-123", "m1")
    assert iri == "episodic-memories-1:memory:user-abc-123:m1"


# ── version validation inherited from _ensure_version ────────────────


def test_episode_iri_rejects_bad_version() -> None:
    with pytest.raises(RefFormatError, match="version"):
        episode_iri("-bad", "alice", "e1")


def test_memory_composite_iri_rejects_bad_version() -> None:
    with pytest.raises(RefFormatError, match="version"):
        memory_composite_iri("", "alice", "m1")
