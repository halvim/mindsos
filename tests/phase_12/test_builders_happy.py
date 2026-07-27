"""Tier 1 — Builder happy paths + user_id charset + capacity_snapshot.

Covers: 14 IRI builders (PB-2 / PB-20) + alignment_role round-trip
(PB-4) + user_id charset enforcement (PB-11) + capacity_snapshot
embedded-colon body (PB-8).
"""

from __future__ import annotations

import pytest

from mindsos_knowledge import (
    RefFormatError,
    alignment_role,
    capacity_snapshot_iri,
    dolce_iri,
    episode_iri,
    framenet_fe_iri,
    framenet_frame_iri,
    framenet_lu_iri,
    memory_composite_iri,
    oewn_lemma_iri,
    oewn_sense_iri,
    oewn_synset_iri,
    pipeline_iri,
    pipeline_step_iri,
    problem_trace_iri,
    subgoal_template_iri,
    request_pattern_iri,
)


# ── Seed-role builders (v3 verbatim port) ──────────────────────────────


def test_dolce_iri_happy() -> None:
    assert dolce_iri("4.0", "PhysicalObject") == "dolce-dul-4.0:PhysicalObject"


def test_oewn_synset_iri_happy() -> None:
    assert oewn_synset_iri("2024", "01234567", "n") == "oewn-2024:synset:01234567-n"


def test_oewn_sense_iri_happy() -> None:
    assert oewn_sense_iri("2024", "dog%1:05:00::") == "oewn-2024:sense:dog%1:05:00::"


def test_oewn_lemma_iri_happy() -> None:
    assert oewn_lemma_iri("2024", "dog", "n") == "oewn-2024:lemma:dog-n"


def test_framenet_frame_iri_happy() -> None:
    assert framenet_frame_iri("1.7", "139") == "framenet-1.7:frame:139"


def test_framenet_lu_iri_happy() -> None:
    assert framenet_lu_iri("1.7", "11234") == "framenet-1.7:lu:11234"


def test_framenet_fe_iri_happy() -> None:
    assert framenet_fe_iri("1.7", "139", "Buyer") == "framenet-1.7:fe:139:Buyer"


# ── Upper-layer builders (ADR-0045, Phase 12 net-new) ─────────────────


def test_pipeline_iri_happy() -> None:
    assert pipeline_iri("1", "abc") == "promoted-pipelines-1:pipeline:abc"


def test_pipeline_step_iri_happy() -> None:
    assert (
        pipeline_step_iri("1", "abc", "s1")
        == "promoted-pipelines-1:step:abc:s1"
    )


def test_task_pattern_iri_happy() -> None:
    assert request_pattern_iri("1", "tp-7") == "request-patterns-1:pattern:tp-7"


def test_subgoal_template_iri_happy() -> None:
    assert (
        subgoal_template_iri("1", "tp-7", "sg-2")
        == "request-patterns-1:subgoal:tp-7:sg-2"
    )


def test_episode_iri_happy() -> None:
    assert (
        episode_iri("1", "alice", "e-001")
        == "episodic-memories-1:episode:alice:e-001"
    )


def test_memory_composite_iri_happy() -> None:
    assert (
        memory_composite_iri("1", "alice", "m-001")
        == "episodic-memories-1:memory:alice:m-001"
    )


def test_problem_trace_iri_happy() -> None:
    assert problem_trace_iri("1", "trc-abc") == "problem-trace-1:entry:trc-abc"


def test_capacity_snapshot_iri_happy() -> None:
    # PB-8: capacity_iri contains colons; body becomes opaque after `snapshot:`.
    iri = capacity_snapshot_iri(
        "1", "alice", "capacity:text:tokens", "2026-05-16T00:00:00Z"
    )
    assert (
        iri == "capacity-state-1:snapshot:alice:capacity:text:tokens:"
        "2026-05-16T00:00:00Z"
    )


# ── alignment_role graph-name helper (PB-4) ───────────────────────────


def test_alignment_role_canonical_order() -> None:
    # Order-independent: same string regardless of arg order.
    assert alignment_role("lexicon", "concepts") == alignment_role(
        "concepts", "lexicon"
    )


def test_alignment_role_string_shape() -> None:
    assert alignment_role("concepts", "lexicon") == "alignment:concepts:lexicon"


# ── user_id charset enforcement (PB-11 + ADR-0044 §amendment-1) ───────


@pytest.mark.parametrize(
    "bad",
    [
        "",  # empty
        "-leading-dash",  # leading dash forbidden
        "a:b",  # colon would break parser
        "user@example",  # @ forbidden
        "user with space",  # space forbidden
        "a" * 65,  # too long
    ],
)
def test_episode_iri_rejects_bad_user_id(bad: str) -> None:
    with pytest.raises(RefFormatError, match="user_id"):
        episode_iri("1", bad, "e1")


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "-leading-dash",
        "a:b",
        "user@example",
        "user with space",
        "a" * 65,
    ],
)
def test_memory_composite_iri_rejects_bad_user_id(bad: str) -> None:
    with pytest.raises(RefFormatError, match="user_id"):
        memory_composite_iri("1", bad, "m1")


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "user:with:colon",
    ],
)
def test_capacity_snapshot_rejects_bad_user_id(bad: str) -> None:
    with pytest.raises(RefFormatError, match="user_id"):
        capacity_snapshot_iri("1", bad, "capacity:cat:foo", "2026-05-16")


def test_memory_composite_iri_accepts_typical_uuid_user_id() -> None:
    # UUID with dashes is fine.
    iri = memory_composite_iri("1", "user-abc-123", "m1")
    assert iri == "episodic-memories-1:memory:user-abc-123:m1"


def test_episode_iri_accepts_typical_uuid_user_id() -> None:
    iri = episode_iri("1", "user-abc-123", "e1")
    assert iri == "episodic-memories-1:episode:user-abc-123:e1"


# ── capacity_snapshot embedded-colon round-trip (PB-8) ────────────────


def test_capacity_snapshot_full_string_equality() -> None:
    # Build → parse → reformat-as-full should equal the original
    # build. (Field-level inverse is deferred per PB-8 / PB-10.)
    from mindsos_knowledge import parse_iri

    built = capacity_snapshot_iri(
        "1", "u1", "capacity:text:tokens", "2026-05-16T00:00:00Z"
    )
    parsed = parse_iri(built)
    assert parsed.full == built


def test_capacity_snapshot_opaque_body_carries_inner_colons() -> None:
    from mindsos_knowledge import parse_iri

    built = capacity_snapshot_iri(
        "1", "u1", "capacity:text:tokens", "2026-05-16T00:00:00Z"
    )
    parsed = parse_iri(built)
    # `snapshot` extracted; everything after it is opaque body with
    # embedded colons preserved.
    assert parsed.kind == "snapshot"
    assert parsed.body == "u1:capacity:text:tokens:2026-05-16T00:00:00Z"
