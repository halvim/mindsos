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
    ROLE_INSTALLED_CAPACITIES,
    ROLE_INSTALLED_SKILLS,
    ROLE_LEARNED_PARAMETERS,
    ROLE_LEARNED_PIPELINES,
    ROLE_LEXICON,
    ROLE_ONTOLOGY,
    ROLE_PARAMETER_STAGING,
    ROLE_PENDING_PROMOTIONS,
    ROLE_POLICIES,
    ROLE_PROBLEM_TRACE,
    ROLE_PROMOTED_PIPELINES,
    ROLE_SUBMINDS,
    ROLE_REQUEST_PATTERNS,
    UnknownRoleError,
    schema_for_role,
)
from mindsos_knowledge.schemas import _ROLE_SCHEMA_BUILDERS
from mindsos_knowledge import ALL_ROLES


# DERIVED - the parametrised role list is the closed set itself.
_ALL_NAMED_ROLES = tuple(sorted(ALL_ROLES))


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


def test_dispatch_table_keys_equal_named_roles() -> None:
    """The table and the closed role-set do not drift apart.

    A separate size assertion used to sit here, written as a number. It said
    nothing this does not: two sets that are equal have the same size. The
    COUNT is asserted once, in
    ``tests/dataset_role/test_dataset_role_core.py``, and nowhere else.
    Alignment is NOT in the dispatch dict - it is prefix-keyed.
    """
    assert set(_ROLE_SCHEMA_BUILDERS) == set(ALL_ROLES)


def test_schema_for_role_strict_kwarg_plumbed() -> None:
    s = schema_for_role(ROLE_LEXICON, strict=True)
    assert s.strict is True
