"""The recorded-sets role — pointers to recorded response sets (``mindsos_llm`` I-10).

Non-KL substrate: role closure and its LOCAL-ONLY scope, schema shape, the
identity-is-the-hash address, and the store's refusals, exercised through a
fabricated handle so each test proves one clause and cannot pass for another.
The capacity end to end, through a real KnowledgeLayer, is
``test_record_reading_set.py``.

Rulings: R1, R2, R8, R9, R13–R18 (``docs/plans/MINDSOS_LLM_PLAN.md`` §2);
ADR-0210 amendment 6.
"""

from __future__ import annotations

import inspect

import pytest

from mindsos_core import Metagraph

from mindsos_knowledge import ALL_ROLES, ROLE_RECORDED_SETS, parse_iri, recorded_set_iri
from mindsos_knowledge.bootstrap import (
    _GLOBAL_NAMED_ROLES,
    _LOCAL_NAMED_ROLES,
    ensure_local_role_graph,
)
from mindsos_knowledge.identifiers import _IRI_BUILDERS, RefFormatError
from mindsos_knowledge.recorded_sets import (
    RecordedSetDescriptionError,
    RecordedSetExistsError,
    RecordedSetNotFoundError,
    recorded_set_at,
    write_recorded_set,
)
from mindsos_knowledge.schemas import schema_for_role
from mindsos_knowledge.schemas._base import Discipline
from mindsos_knowledge.schemas.recorded_sets import (
    NODE_RECORDED_SET,
    PAYLOAD_STORAGE_MODE,
    RECORDED_SETS_EDGE_TYPES,
    RECORDED_SETS_NODE_TYPES,
    RECORDED_SET_PROPS,
    RULED_OUT_PROPS,
    STORAGE_MODE_FIELDS,
    build_recorded_sets_schema,
)

SHA = "a" * 64


def _description(**over):
    d = {
        "path": "/data/sets/alice.json",
        "sha256": SHA,
        "responses": 2,
        "key_schema_version": "1",
        "identities": [{"model_id": "m-1", "model_version": "v-1", "temperature": 0.0}],
        "prompts": [{"prompt_iri": "prompt:p", "prompt_version": 1}],
        "request_keys": ["sha256:1", "sha256:2"],
        "credential_level": 1,
    }
    d.update(over)
    return d


class _Written:
    def __init__(self, iri, value, properties):
        self.iri, self.value, self.properties = iri, value, properties


class _Graph:
    def __init__(self):
        self.nodes = {}


class _Handle:
    """A fabricated KLWriteHandle bound to (recorded-sets, local): the real
    minter, an in-memory node table, and nothing else."""

    def __init__(self):
        self._g = _Graph()

    def mint_iri(self, type_, **content):
        return _IRI_BUILDERS[(ROLE_RECORDED_SETS, type_)]("v1", **content)

    def graph(self):
        return self._g

    def write_and_validate(self, *, value, type_, properties, **mint):
        assert type_ == NODE_RECORDED_SET
        iri = self.mint_iri(type_, **mint)
        self._g.nodes[iri] = _Written(iri, value, dict(properties))
        return self._g.nodes[iri]


def _write(handle, **over):
    return write_recorded_set(
        handle, description=_description(**over), recorded_by="alice",
        recorded_at="2026-09-21T00:00:00.000Z",
    )


# ── role closure + scope ──────────────────────────────────────────────


def test_the_role_is_local_only():
    """Plan §4: recorded sets are never Global. The closed-set COUNT is
    asserted once, in tests/dataset_role/test_dataset_role_core.py."""
    assert ROLE_RECORDED_SETS in ALL_ROLES
    assert ROLE_RECORDED_SETS in _LOCAL_NAMED_ROLES
    assert ROLE_RECORDED_SETS not in _GLOBAL_NAMED_ROLES


def test_the_schema_is_single_type_zero_edge_append_only():
    assert build_recorded_sets_schema().mutation_discipline == Discipline.APPEND_ONLY
    assert schema_for_role(ROLE_RECORDED_SETS).mutation_discipline == Discipline.APPEND_ONLY
    assert RECORDED_SETS_NODE_TYPES == (NODE_RECORDED_SET,)
    assert RECORDED_SETS_EDGE_TYPES == ()


def test_the_role_graph_is_creatable_in_a_local_realm():
    g = ensure_local_role_graph(Metagraph("kl:local:alice"), ROLE_RECORDED_SETS)
    assert g.role == ROLE_RECORDED_SETS


def test_the_payload_is_the_large_field_and_storage_mode_is_declared_for_it():
    assert STORAGE_MODE_FIELDS[NODE_RECORDED_SET] == frozenset({"value"})
    assert PAYLOAD_STORAGE_MODE == "falkor_blob"
    assert "value" not in RECORDED_SET_PROPS


def test_nothing_ruled_out_is_a_property():
    """R8/R14 (set_id), R9 (vendor_id), R16 (captured_at)."""
    assert RULED_OUT_PROPS == {"set_id", "vendor_id", "captured_at"}
    assert not (RULED_OUT_PROPS & RECORDED_SET_PROPS)


# ── the address is the identity ───────────────────────────────────────


def test_the_address_is_the_hash_and_round_trips():
    iri = recorded_set_iri("v1", SHA)
    assert iri == f"recorded-sets-v1:set:{SHA}"
    parsed = parse_iri(iri)
    assert (parsed.role, parsed.version, parsed.kind, parsed.body, parsed.full) == (
        ROLE_RECORDED_SETS, "v1", "set", SHA, iri,
    )


def test_an_address_that_is_not_a_hash_is_refused():
    for bad in ("A" * 64, "a" * 63, "sha256:" + "a" * 64, "set-1"):
        with pytest.raises(RefFormatError, match="64 lowercase hex"):
            recorded_set_iri("v1", bad)


def test_mint_iri_dispatches_and_a_missing_key_is_a_key_error():
    minter = _IRI_BUILDERS[(ROLE_RECORDED_SETS, NODE_RECORDED_SET)]
    assert minter("v1", sha256=SHA) == recorded_set_iri("v1", SHA)
    with pytest.raises(KeyError, match="sha256"):
        minter("v1")


# ── the store ─────────────────────────────────────────────────────────


def test_the_pointer_carries_the_derived_facts_and_the_facts_of_the_write():
    node = _write(_Handle())
    assert node.properties == {
        "sha256": SHA,
        "file_uri": "/data/sets/alice.json",
        "responses": 2,
        "key_schema_version": "1",
        "recorded_at": "2026-09-21T00:00:00.000Z",
        "recorded_by": "alice",
        "storage_mode": "falkor_blob",
        "credential_level": 1,
    }
    assert set(node.properties) <= RECORDED_SET_PROPS
    assert node.value["request_keys"] == ["sha256:1", "sha256:2"]
    assert set(node.value) == {"responses", "key_schema_version", "identities", "prompts", "request_keys"}


def test_file_uri_can_only_come_from_the_file_that_was_hashed():
    """R18: no argument lets a caller name a different file."""
    assert "file_uri" not in inspect.signature(write_recorded_set).parameters


def test_a_level_the_payloads_do_not_state_is_not_stored():
    assert "credential_level" not in _write(_Handle(), credential_level=None).properties


def test_a_recapture_of_the_same_bytes_is_refused():
    handle = _Handle()
    _write(handle)
    with pytest.raises(RecordedSetExistsError, match="already exists"):
        _write(handle)


@pytest.mark.parametrize(
    "over,fragment",
    [
        ({"request_keys": ["sha256:2", "sha256:1"]}, "not sorted"),
        ({"request_keys": [], "responses": 0}, "no request_keys"),
        ({"responses": 3}, "does not describe one file"),
    ],
    ids=["unsorted", "empty", "count_mismatch"],
)
def test_a_description_that_is_not_one_is_refused(over, fragment):
    with pytest.raises(RecordedSetDescriptionError, match=fragment):
        _write(_Handle(), **over)


def test_a_description_missing_a_derived_field_is_refused():
    d = _description()
    del d["sha256"]
    with pytest.raises(RecordedSetDescriptionError, match="missing"):
        write_recorded_set(_Handle(), description=d, recorded_by="a", recorded_at="t")


def test_a_missing_pointer_refuses_rather_than_returning_a_neighbour():
    class _EmptyView:
        def iter_nodes(self, role, type_=None):
            return iter(())

    with pytest.raises(RecordedSetNotFoundError):
        recorded_set_at(_EmptyView(), SHA)
