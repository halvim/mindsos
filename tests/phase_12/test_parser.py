"""Tier 2 — parse_iri + is_version_qualified_iri + builder round-trips.

Covers: edge cases (bad prefix, missing version, NFC variants, kind
detection across 7 roles); 14 builder string-round-trips (PB-10);
is_version_qualified_iri matrix; adversarial regex; alignment_role
parser rejection.
"""

from __future__ import annotations

import pytest

from mindsos_knowledge import (
    ALL_ROLES,
    ROLE_CAPACITY_STATE,
    ROLE_CONCEPTS,
    ROLE_EPISODIC_MEMORIES,
    ROLE_LEXICON,
    ROLE_ONTOLOGY,
    ROLE_PROBLEM_TRACE,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
    RefFormatError,
    alignment_role,
    capacity_snapshot_iri,
    dolce_iri,
    episode_iri,
    framenet_fe_iri,
    framenet_frame_iri,
    framenet_lu_iri,
    is_version_qualified_iri,
    memory_composite_iri,
    oewn_lemma_iri,
    oewn_sense_iri,
    oewn_synset_iri,
    parse_iri,
    pipeline_iri,
    pipeline_step_iri,
    problem_trace_iri,
    subgoal_template_iri,
    task_pattern_iri,
)


# ── Builder round-trip × 14 (PB-10) ──────────────────────────────────


_BUILDER_ROUND_TRIPS = [
    # (build_call, expected_role, expected_kind, name)
    (lambda: dolce_iri("4.0", "PhysicalObject"), ROLE_ONTOLOGY, None, "dolce"),
    (
        lambda: oewn_synset_iri("2024", "01234567", "n"),
        ROLE_LEXICON,
        "synset",
        "oewn_synset",
    ),
    (
        lambda: oewn_sense_iri("2024", "abc"),
        ROLE_LEXICON,
        "sense",
        "oewn_sense",
    ),
    (
        lambda: oewn_lemma_iri("2024", "dog", "n"),
        ROLE_LEXICON,
        "lemma",
        "oewn_lemma",
    ),
    (
        lambda: framenet_frame_iri("1.7", "139"),
        ROLE_CONCEPTS,
        "frame",
        "framenet_frame",
    ),
    (
        lambda: framenet_lu_iri("1.7", "11234"),
        ROLE_CONCEPTS,
        "lu",
        "framenet_lu",
    ),
    (
        lambda: framenet_fe_iri("1.7", "139", "Buyer"),
        ROLE_CONCEPTS,
        "fe",
        "framenet_fe",
    ),
    (
        lambda: pipeline_iri("1", "abc"),
        ROLE_PROMOTED_PIPELINES,
        "pipeline",
        "pipeline",
    ),
    (
        lambda: pipeline_step_iri("1", "abc", "s1"),
        ROLE_PROMOTED_PIPELINES,
        "step",
        "pipeline_step",
    ),
    (
        lambda: task_pattern_iri("1", "tp"),
        ROLE_TASK_PATTERNS,
        "pattern",
        "task_pattern",
    ),
    (
        lambda: subgoal_template_iri("1", "tp", "sg"),
        ROLE_TASK_PATTERNS,
        "subgoal",
        "subgoal_template",
    ),
    (
        lambda: episode_iri("1", "alice", "e1"),
        ROLE_EPISODIC_MEMORIES,
        "episode",
        "episode",
    ),
    (
        lambda: memory_composite_iri("1", "alice", "m1"),
        ROLE_EPISODIC_MEMORIES,
        "memory",
        "memory_composite",
    ),
    (
        lambda: problem_trace_iri("1", "trc"),
        ROLE_PROBLEM_TRACE,
        "entry",
        "problem_trace",
    ),
    (
        lambda: capacity_snapshot_iri("1", "u", "capacity:cat:n", "2026-05-16"),
        ROLE_CAPACITY_STATE,
        "snapshot",
        "capacity_snapshot",
    ),
]


@pytest.mark.parametrize(
    "build,expected_role,expected_kind,name",
    _BUILDER_ROUND_TRIPS,
    ids=[t[3] for t in _BUILDER_ROUND_TRIPS],
)
def test_builder_round_trip(build, expected_role, expected_kind, name) -> None:
    iri = build()
    parsed = parse_iri(iri)
    assert parsed.full == iri, f"{name}: full mismatch"
    assert parsed.role == expected_role, f"{name}: role mismatch"
    assert parsed.kind == expected_kind, f"{name}: kind mismatch"


# ── parse_iri edge cases ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "PhysicalObject",  # no prefix
        "unknown-prefix-1.0:body",
        "dolce-dul-:bare-version",  # empty version segment
        "alignment:concepts:lexicon",  # graph name (PB-4 — not an IRI)
        "no-colon-here",
        None,
        42,
    ],
)
def test_parse_iri_rejects_malformed(bad) -> None:
    with pytest.raises(RefFormatError):
        parse_iri(bad)


def test_parse_iri_dolce_no_kind() -> None:
    # DOLCE has no kind sub-prefix; body is the whole post-version-colon rest.
    parsed = parse_iri("dolce-dul-4.0:PhysicalObject")
    assert parsed.kind is None
    assert parsed.body == "PhysicalObject"


def test_parse_iri_lexicon_kind_extracted() -> None:
    parsed = parse_iri("oewn-2024:synset:01234567-n")
    assert parsed.kind == "synset"
    assert parsed.body == "01234567-n"


def test_parse_iri_lexicon_unknown_kind_stays_in_body() -> None:
    # `frobnicate` is not in _KINDS_PER_ROLE[ROLE_LEXICON]; treated as
    # opaque body (not kind-extracted).
    parsed = parse_iri("oewn-2024:frobnicate:foo")
    assert parsed.kind is None
    assert parsed.body == "frobnicate:foo"


def test_parse_iri_capacity_state_opaque_after_snapshot() -> None:
    # PB-8: capacity-state body holds embedded colons after `snapshot:`.
    parsed = parse_iri(
        "capacity-state-1:snapshot:u1:capacity:text:tokens:2026-05-16T00:00:00Z"
    )
    assert parsed.role == ROLE_CAPACITY_STATE
    assert parsed.kind == "snapshot"
    assert parsed.body == "u1:capacity:text:tokens:2026-05-16T00:00:00Z"


def test_parse_iri_problem_trace_kind_extracted() -> None:
    parsed = parse_iri("problem-trace-1:entry:trc-1")
    assert parsed.kind == "entry"


def test_parse_iri_ontology_no_kind_table_entry() -> None:
    # ROLE_ONTOLOGY absent from _KINDS_PER_ROLE — kind always None.
    parsed = parse_iri("dolce-dul-4.0:Anything:With:Colons")
    assert parsed.kind is None
    assert parsed.body == "Anything:With:Colons"


def test_parse_iri_nfc_normalisation_round_trip() -> None:
    # NFD-decomposed café → NFC-composed café via builder normalisation.
    nfd_cafe = "café"  # 'cafe' + combining acute
    iri = dolce_iri("1.0", nfd_cafe)
    parsed = parse_iri(iri)
    assert parsed.body == "café"  # NFC form


def test_parse_iri_full_field_preserved() -> None:
    src = "framenet-1.7:fe:139:Buyer"
    parsed = parse_iri(src)
    assert parsed.full == src


# ── is_version_qualified_iri matrix ───────────────────────────────────


@pytest.mark.parametrize(
    "value,expected",
    [
        ("dolce-dul-4.0:PhysicalObject", True),
        ("oewn-2024:synset:01-n", True),
        ("episodic-memories-1:memory:alice:m1", True),
        ("episodic-memories-1:episode:alice:e1", True),
        ("not-an-iri", False),
        ("alignment:concepts:lexicon", False),  # PB-4
        ("", False),
        (None, False),
        (42, False),
        ("PhysicalObject", False),
    ],
)
def test_is_version_qualified_iri_matrix(value, expected) -> None:
    assert is_version_qualified_iri(value) is expected


# ── Adversarial regex ────────────────────────────────────────────────


def test_version_rejects_leading_dash() -> None:
    with pytest.raises(RefFormatError, match="version"):
        dolce_iri("-1.0", "Foo")


def test_version_rejects_empty() -> None:
    with pytest.raises(RefFormatError, match="version"):
        dolce_iri("", "Foo")


def test_fragment_rejects_whitespace() -> None:
    with pytest.raises(RefFormatError, match="fragment"):
        dolce_iri("1.0", "has space")


def test_alignment_role_is_not_parseable_as_iri() -> None:
    # PB-4 lock: alignment_role output is NOT an IRI.
    name = alignment_role("lexicon", "concepts")
    with pytest.raises(RefFormatError):
        parse_iri(name)
