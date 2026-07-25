"""Phase 13 PB-11 + PB-5 — ``schema_for_role`` dispatch.

Covers: 8-role happy path × parametric, alignment-prefix branch,
unknown-role raises ``UnknownRoleError``.
"""

from __future__ import annotations

import pytest

from mindsos_core import Schema

from mindsos_knowledge import (
    ROLE_CAPACITY_GAPS,
    ROLE_CAPACITY_STATE,
    ROLE_CONCEPTS,
    ROLE_EPISODIC_MEMORIES,
    ROLE_INSTALLED_SKILLS,
    ROLE_LEARNED_PARAMETERS,
    ROLE_LEARNED_PIPELINES,
    ROLE_LEXICON,
    ROLE_ONTOLOGY,
    ROLE_PARAMETER_STAGING,
    ROLE_PENDING_PROMOTIONS,
    ROLE_PROBLEM_TRACE,
    ROLE_PROMOTED_PIPELINES,
    ROLE_SUBMINDS,
    ROLE_TASK_PATTERNS,
    UnknownRoleError,
    schema_for_role,
)
from mindsos_knowledge.schemas import _ROLE_SCHEMA_BUILDERS


_ALL_NAMED_ROLES = (
    ROLE_ONTOLOGY,
    ROLE_LEXICON,
    ROLE_CONCEPTS,
    ROLE_PROMOTED_PIPELINES,
    ROLE_TASK_PATTERNS,
    ROLE_EPISODIC_MEMORIES,
    ROLE_PROBLEM_TRACE,
    ROLE_CAPACITY_STATE,
    # Phase 43 additions per ADR-0150 §am-5.
    ROLE_PARAMETER_STAGING,
    ROLE_PENDING_PROMOTIONS,
    ROLE_CAPACITY_GAPS,
    ROLE_LEARNED_PARAMETERS,
    # Phase 50 addition per ADR-0150 §am-6.
    ROLE_INSTALLED_SKILLS,
    # feat/subminds addition per ADR-0150 §am-7.
    ROLE_SUBMINDS,
    # feat/learned-pipeline-persistence addition per ADR-0203.
    ROLE_LEARNED_PIPELINES,
)


@pytest.mark.parametrize("role", _ALL_NAMED_ROLES)
def test_schema_for_role_returns_schema_for_each_named_role(role: str) -> None:
    s = schema_for_role(role)
    assert isinstance(s, Schema)
    assert s.strict is False


def test_alignment_prefix_returns_alignment_schema() -> None:
    from mindsos_knowledge.schemas.alignment import NODE_ALIGNMENT_ANCHOR

    s = schema_for_role("alignment:concepts:lexicon")
    assert NODE_ALIGNMENT_ANCHOR in s.node_types


def test_alignment_prefix_arbitrary_pair_returns_alignment_schema() -> None:
    from mindsos_knowledge.schemas.alignment import NODE_ALIGNMENT_ANCHOR

    # PB-5 — parametric; any role-pair under the alignment prefix works.
    s = schema_for_role("alignment:bar:foo")
    assert NODE_ALIGNMENT_ANCHOR in s.node_types


def test_unknown_role_raises_unknown_role_error() -> None:
    with pytest.raises(UnknownRoleError) as excinfo:
        schema_for_role("not-a-real-role")
    msg = str(excinfo.value)
    # Error message names the valid roles + the alignment prefix hint.
    assert "not-a-real-role" in msg
    assert "alignment:" in msg


def test_dispatch_table_size_equals_named_role_count() -> None:
    # Closure sentinel — Phase 14+ adding a role must extend the table.
    # Alignment is NOT in the dispatch dict (prefix-keyed, not name-keyed).
    # Phase 43 PR2 commit 1 expanded the closed role-set from 8 to 12 per
    # ADR-0150 §amendment-5 (parameter-staging, pending-promotions,
    # capacity-gaps, learned-parameters). Phase 50 expanded 12 to 13 per
    # ADR-0150 §amendment-6 (installed-skills). feat/subminds expanded 13
    # to 14 per ADR-0150 §amendment-7 (subminds).
    assert len(_ROLE_SCHEMA_BUILDERS) == 15


def test_dispatch_table_keys_equal_named_roles() -> None:
    assert set(_ROLE_SCHEMA_BUILDERS) == set(_ALL_NAMED_ROLES)


def test_schema_for_role_strict_kwarg_plumbed() -> None:
    s = schema_for_role(ROLE_LEXICON, strict=True)
    assert s.strict is True
