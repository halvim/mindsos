"""Tier 3 — REF_TYPES + ref-key helpers + role constants + ADR sentinels.

Covers: REF_TYPES self-consistency (PB-3 defers L3 parity to Phase 27);
global/local ref-key helpers + REF_TYPE_KEY; role constants +
frozensets (SEED_ROLES / UPPER_LAYER_ROLES / ALL_ROLES); ADR-0045
closure sentinel (14 builders + __all__); ADR-0044 §amendment-1
sentinel (charset documented); ADR-0067 parity-deferred sentinel.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import mindsos_knowledge
from mindsos_knowledge import (
    ALL_ROLES,
    REF_TYPE_KEY,
    REF_TYPES,
    ROLE_CAPACITY_STATE,
    ROLE_CONCEPTS,
    ROLE_EPISODIC_MEMORIES,
    ROLE_LEXICON,
    ROLE_ONTOLOGY,
    ROLE_PROBLEM_TRACE,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
    SEED_ROLES,
    UPPER_LAYER_ROLES,
    global_ref_key,
    local_ref_key,
)


# ── REF_TYPES self-consistency (PB-3 L3 parity test deferred to Phase 27) ─


def test_ref_types_is_frozenset() -> None:
    assert isinstance(REF_TYPES, frozenset)


def test_ref_types_starter_vocabulary() -> None:
    # ADR-0047 starter set + PROMOTED amendment (2026-04-22).
    expected = frozenset({
        "SPECIALISES",
        "INSTANCE_OF",
        "RENAMES",
        "EXTENDS",
        "CONTRADICTS",
        "PROXY",
        "PROMOTED",
    })
    assert REF_TYPES == expected


def test_ref_type_key_constant() -> None:
    assert REF_TYPE_KEY == "ref_type"


# ── Ref-key helpers (PB-12) ───────────────────────────────────────────


def test_global_ref_key_format() -> None:
    assert global_ref_key("lexicon") == "ref:global_lexicon"


def test_local_ref_key_format() -> None:
    assert local_ref_key("ontology") == "ref:ontology"


def test_global_ref_key_handles_upper_layer_roles() -> None:
    # Hyphenated upper-layer roles round-trip into the key.
    assert global_ref_key("promoted-pipelines") == "ref:global_promoted-pipelines"


def test_local_ref_key_handles_upper_layer_roles() -> None:
    assert local_ref_key("task-patterns") == "ref:task-patterns"


# ── Role constants + frozensets (PB-9) ────────────────────────────────


def test_seed_roles_matches_v3() -> None:
    assert SEED_ROLES == frozenset({ROLE_ONTOLOGY, ROLE_LEXICON, ROLE_CONCEPTS})


def test_upper_layer_roles_matches_adr_0045() -> None:
    """Phase 43 (ADR-0150 §am-5) added 4 upper-layer role-graphs;
    Phase 50 (ADR-0150 §am-6) added installed-skills."""
    from mindsos_knowledge import (
        ROLE_CAPACITY_GAPS,
        ROLE_INSTALLED_SKILLS,
        ROLE_LEARNED_PARAMETERS,
        ROLE_PARAMETER_STAGING,
        ROLE_PENDING_PROMOTIONS,
        ROLE_SUBMINDS,
        ROLE_LEARNED_PIPELINES,
    )

    assert UPPER_LAYER_ROLES == frozenset({
        ROLE_PROMOTED_PIPELINES,
        ROLE_TASK_PATTERNS,
        ROLE_EPISODIC_MEMORIES,
        ROLE_PROBLEM_TRACE,
        ROLE_CAPACITY_STATE,
        # Phase 43 (ADR-0150 §am-5) upper-layer additions.
        ROLE_PARAMETER_STAGING,
        ROLE_PENDING_PROMOTIONS,
        ROLE_CAPACITY_GAPS,
        ROLE_LEARNED_PARAMETERS,
        # Phase 50 (ADR-0150 §am-6) addition.
        ROLE_INSTALLED_SKILLS,
        # feat/subminds (ADR-0150 §am-7) addition.
        ROLE_SUBMINDS,
        # feat/learned-pipeline-persistence (ADR-0203) addition.
        ROLE_LEARNED_PIPELINES,
    })


def test_all_roles_is_union() -> None:
    assert ALL_ROLES == SEED_ROLES | UPPER_LAYER_ROLES
    assert SEED_ROLES.isdisjoint(UPPER_LAYER_ROLES)


# ── ADR-0045 closure sentinel ─────────────────────────────────────────


_ADR_0045_BUILDERS = (
    # Seed (v3)
    "dolce_iri",
    "oewn_synset_iri",
    "oewn_sense_iri",
    "oewn_lemma_iri",
    "framenet_frame_iri",
    "framenet_lu_iri",
    "framenet_fe_iri",
    # Upper-layer (ADR-0045 + ADR-0044 §amendment-3 split memory builder
    # into episode_iri + memory_composite_iri per Phase 39 ship; ADR-0045
    # itself is currently stale on this surface — Phase 43 may amend it
    # alongside the schema-v2 ship per design log §3 phasing).
    "pipeline_iri",
    "pipeline_step_iri",
    "task_pattern_iri",
    "subgoal_template_iri",
    "episode_iri",
    "memory_composite_iri",
    "problem_trace_iri",
    "capacity_snapshot_iri",
)


def test_adr_0045_all_builders_present_and_exported() -> None:
    """ADR-0045 closure: all builders ship + are in __all__ (PB-2 + PB-20).

    Post-Phase-39 ship: 8 upper-layer builders (memory_iri split per
    ADR-0044 §amendment-3 + ADR-0146 §amendment-3); 7 seed-role; total 15.
    """
    assert len(_ADR_0045_BUILDERS) == 15
    for name in _ADR_0045_BUILDERS:
        assert hasattr(mindsos_knowledge, name), f"{name} not exported"
        assert name in mindsos_knowledge.__all__, f"{name} missing from __all__"


# ── ADR-0044 §amendment-1 sentinel (user_id charset documented) ───────


_ADR_PATH_CANDIDATES = [
    Path(__file__).resolve().parents[2].parent
        / "docs" / "decisions" / "adr"
        / "0044-memories-move-to-local-per-user.md",
    Path("../docs/decisions/adr/0044-memories-move-to-local-per-user.md"),
]


def _read_adr_0044() -> str:
    for candidate in _ADR_PATH_CANDIDATES:
        try:
            return candidate.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
    pytest.skip(
        f"ADR-0044 not reachable from {[str(p) for p in _ADR_PATH_CANDIDATES]}"
    )


def test_adr_0044_amendment_1_user_id_charset() -> None:
    """Amendment-1 documents user_id charset per PB-17."""
    text = _read_adr_0044()
    assert "amendment-1" in text
    assert "user_id" in text
    # Charset regex characters present in the documented section.
    assert "[A-Za-z0-9]" in text or "0,63" in text


# ── ADR-0067 L3 parity test deferred sentinel (PB-3) ──────────────────


def test_adr_0067_parity_test_landed_at_phase_27() -> None:
    """PB-3 origin: REF_TYPES parity test against L3 was deferred from
    Phase 12 to Phase 27 (the first L3 ship). At Phase 27 the parity
    test landed at ``tests/phase_27/test_capacity_dataclass.py::
    test_ref_types_subset_of_kl_ref_types``.

    Sentinel flipped at Phase 27 ship: ``mindsos_capacity`` now
    exists, and the ADR-0067 §amendment-1 contract holds:
    ``L3.REF_TYPES ⊆ L2.REF_TYPES`` with
    ``L2 - L3 == {"PROMOTED"}``.
    """
    import importlib

    capacity = importlib.import_module("mindsos_capacity")
    kl_ids = importlib.import_module("mindsos_knowledge.identifiers")
    assert capacity.REF_TYPES <= kl_ids.REF_TYPES, (
        "L3.REF_TYPES must be a subset of L2.REF_TYPES"
    )
    assert kl_ids.REF_TYPES - capacity.REF_TYPES == {"PROMOTED"}, (
        "L2 - L3 expected to be exactly {'PROMOTED'} per ADR-0067 §am1"
    )
