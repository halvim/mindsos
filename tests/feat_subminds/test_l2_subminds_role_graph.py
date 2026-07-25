"""feat/subminds Slice 1 — L2 ``subminds`` role-graph (ADR-0190 + ADR-0150 §am-7).

Closed role-set 13 → 14; schema build + dispatch membership + IRI
round-trip + Global bootstrap (Slice 1 ships the Global form only).
"""

from __future__ import annotations

import pytest

from mindsos_core.models.metagraph import Metagraph

from mindsos_knowledge import (
    ALL_ROLES,
    ROLE_SUBMINDS,
    UPPER_LAYER_ROLES,
    build_subminds_schema,
    schema_for_role,
    submind_definition_iri,
)
from mindsos_knowledge.bootstrap import (
    _GLOBAL_NAMED_ROLES,
    _LOCAL_NAMED_ROLES,
    ensure_global_role_graph,
    ensure_local_role_graph,
)
from mindsos_knowledge.exceptions import KnowledgeError
from mindsos_knowledge.identifiers import parse_iri
from mindsos_knowledge.schemas import _ROLE_SCHEMA_BUILDERS
from mindsos_knowledge.schemas._base import Discipline, L2Schema


def test_role_constant_value():
    assert ROLE_SUBMINDS == "subminds"


def test_closed_role_set_is_14():
    assert ROLE_SUBMINDS in UPPER_LAYER_ROLES
    assert ROLE_SUBMINDS in ALL_ROLES
    assert len(ALL_ROLES) == 15


def test_dispatch_table_includes_subminds():
    assert len(_ROLE_SCHEMA_BUILDERS) == 15
    assert _ROLE_SCHEMA_BUILDERS[ROLE_SUBMINDS] is build_subminds_schema


def test_schema_is_l2_admin_authored():
    s = build_subminds_schema()
    assert isinstance(s, L2Schema)
    assert s.mutation_discipline is Discipline.ADMIN_AUTHORED
    assert "SubMindDefinition" in s.node_types


def test_schema_for_role_dispatches():
    assert isinstance(schema_for_role(ROLE_SUBMINDS), L2Schema)


def test_iri_round_trip():
    iri = submind_definition_iri("v1", "thirst", "r0")
    assert iri == "subminds-v1:definition:thirst:r0"
    parsed = parse_iri(iri)
    assert parsed.role == ROLE_SUBMINDS


def test_global_bootstrap_creates_role_graph():
    mg = Metagraph(name="global")
    g = ensure_global_role_graph(mg, ROLE_SUBMINDS)
    assert g.role == ROLE_SUBMINDS
    # Idempotent.
    assert ensure_global_role_graph(mg, ROLE_SUBMINDS) is g


def test_global_scoped_in_slice_1():
    # Slice 1 bootstraps Global only; Local form is deferred to the
    # taught-endowment slice (not yet a member of _LOCAL_NAMED_ROLES).
    assert ROLE_SUBMINDS in _GLOBAL_NAMED_ROLES
    assert ROLE_SUBMINDS not in _LOCAL_NAMED_ROLES
    with pytest.raises(KnowledgeError):
        ensure_local_role_graph(Metagraph(name="local-u1"), ROLE_SUBMINDS)
