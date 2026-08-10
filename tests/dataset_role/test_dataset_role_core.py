"""Core write-path tests for the ``dataset:`` role prefix (ADR-0150 §am-9).

Increment 1 (core write-path) gate coverage. Pure-API tests — no FalkorDB.
The ensure-route, mint-dispatch, and boot-import assertions that need a live
Metagraph / KLWriteHandle / Stack are enumerated in the CR RUNBOOK and wired
to the repo's standard fixtures in the same PR.
"""

from __future__ import annotations

import pytest

from mindsos_knowledge import (
    ALL_ROLES,
    RefFormatError,
    UnknownRoleError,
    _ROLE_SCHEMA_BUILDERS,
    build_dataset_schema,
    dataset_node_iri,
    parse_iri,
    register_dataset_schema,
    schema_for_role,
)


def test_dataset_iri_round_trips_through_parse():
    iri = dataset_node_iri("v1", "arc1", "Task", "007bbfb7")
    assert iri == "dataset-arc1-v1:task:007bbfb7"
    p = parse_iri(iri)
    assert p.full == iri                 # the tested round-trip invariant
    assert p.role == "dataset:arc1"
    assert p.version == "v1"


@pytest.mark.parametrize(
    "version,name,ntype,eid",
    [("v1", "arc1", "Task", "007bbfb7"),
     ("v1", "arc3", "Game", "game_042"),
     ("2024", "arc1", "Task", "a-b-c"),   # hyphens are safe inside the body
     ("1.7", "arc1", "Task", "x")],       # dotted version
)
def test_dataset_iri_round_trip_variants(version, name, ntype, eid):
    iri = dataset_node_iri(version, name, ntype, eid)
    p = parse_iri(iri)
    assert p.full == iri
    assert p.role == f"dataset:{name}"
    assert p.version == version


def test_dataset_name_with_hyphen_is_rejected():
    # '-' in the name would make dataset-<name>-<version> ambiguous.
    with pytest.raises(RefFormatError):
        dataset_node_iri("v1", "arc-1", "Task", "x")


def test_schema_for_unregistered_dataset_role_raises():
    with pytest.raises(UnknownRoleError):
        schema_for_role("dataset:not_registered_zzz")


def test_register_then_schema_for_role_returns_it():
    schema = build_dataset_schema(("Task",))
    register_dataset_schema("arc1", schema)
    assert schema_for_role("dataset:arc1") is schema
    # bare-name and full-role registration are equivalent
    register_dataset_schema("dataset:arc3", build_dataset_schema(("Game",)))
    assert schema_for_role("dataset:arc3") is not None


def test_role_count_sentinel_unchanged():
    # ADR-0150 §am-9 adds a PREFIX, not a named role. The named count
    # must stay 14 (a prefix is in neither table).
    assert len(_ROLE_SCHEMA_BUILDERS) == 17
    assert len(ALL_ROLES) == 17
