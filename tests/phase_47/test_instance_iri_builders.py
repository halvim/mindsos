"""ADR-0201 Slice 0 — capacity_mm instance-IRI builder vocabulary.

Pure-function coverage for the instance-IRI builders + the structural
type-vs-instance guard. No writer, no registry, no metagraph — Slice 0 is
additive vocabulary only (nothing constructs a NodeInstance yet).
"""

from __future__ import annotations

import pytest

from mindsos_capacity.identifiers import (
    NODE_TYPE_CAPACITY_INSTANCE,
    NODE_TYPE_DATASTATE_INSTANCE,
    NODE_TYPES,
    PROP_CAPACITY_INSTANCE_TYPE,
    PROP_DATASTATE_INSTANCE_TYPE,
    capacity_instance_iri,
    datastate_instance_iri,
    datastate_instance_root_iri,
    datastate_iri,
    capacity_iri,
    _CAPACITY_NAME_RE,
    _DATASTATE_NAME_RE,
)


# ── form ────────────────────────────────────────────────────────────────

def test_datastate_instance_iri_form():
    iri = datastate_instance_iri("datastate:arc.raw_task", "task7", "pipelinerun:p1", 3)
    assert iri == "datastate:arc.raw_task#task7.p1.3"


def test_datastate_instance_iri_accepts_bare_name():
    # A bare type name and its full IRI must produce the same instance IRI.
    a = datastate_instance_iri("arc.raw_task", "task7", "p1", 0)
    b = datastate_instance_iri("datastate:arc.raw_task", "task7", "p1", 0)
    assert a == b == "datastate:arc.raw_task#task7.p1.0"


def test_capacity_instance_iri_keeps_category_and_name():
    iri = capacity_instance_iri("capacity:planning:derive_initial_plan", "task7", "p1", 2)
    assert iri == "capacity:planning:derive_initial_plan#task7.p1.2"


def test_root_iri_form_has_no_run_or_seq():
    iri = datastate_instance_root_iri("datastate:arc.raw_task", "task7")
    assert iri == "datastate:arc.raw_task#task7.root"


def test_seq_varies_the_iri():
    a = datastate_instance_iri("datastate:x", "t", "p", 0)
    b = datastate_instance_iri("datastate:x", "t", "p", 1)
    assert a != b


# ── run_ref sanitization (ADR-0201 §Minting) ────────────────────────────

def test_run_ref_prefix_stripped():
    iri = datastate_instance_iri("datastate:x", "t", "pipelinerun:run5", 0)
    assert iri == "datastate:x#t.run5.0"


def test_run_ref_inner_colons_become_dashes():
    iri = datastate_instance_iri("datastate:x", "t", "pipelinerun:task7:pipe3", 0)
    assert iri == "datastate:x#t.task7-pipe3.0"


# ── structural type-vs-instance guard ───────────────────────────────────

def test_instance_iri_is_not_a_registrable_datastate_type():
    iri = datastate_instance_iri("datastate:arc.raw_task", "task7", "p1", 3)
    frag = iri[len("datastate:") :]  # "arc.raw_task#task7.p1.3"
    assert _DATASTATE_NAME_RE.match(frag) is None
    with pytest.raises(ValueError):
        datastate_iri(frag)


def test_capacity_instance_iri_is_not_a_registrable_capacity_type():
    iri = capacity_instance_iri("capacity:planning:derive_initial_plan", "task7", "p1", 3)
    name = iri[len("capacity:planning:") :]  # "derive_initial_plan#task7.p1.3"
    assert _CAPACITY_NAME_RE.match(name) is None
    with pytest.raises(ValueError):
        capacity_iri("planning", name)


# ── prefix routing preserved (sub_mm_for_iri routes by prefix) ──────────

def test_prefix_routing_preserved():
    assert datastate_instance_iri("datastate:x", "t", "p", 0).startswith("datastate:")
    assert datastate_instance_root_iri("datastate:x", "t").startswith("datastate:")
    assert capacity_instance_iri("capacity:a:b", "t", "p", 0).startswith("capacity:")


# ── vocabulary ──────────────────────────────────────────────────────────

def test_instance_type_markers_are_not_core_node_types():
    # Instances are live-only; their type_name must NOT enter the Core
    # schema type-node set (that would be a schema statement Slice 0 avoids).
    assert NODE_TYPE_DATASTATE_INSTANCE == "DataStateInstance"
    assert NODE_TYPE_CAPACITY_INSTANCE == "CapacityInstance"
    assert NODE_TYPE_DATASTATE_INSTANCE not in NODE_TYPES
    assert NODE_TYPE_CAPACITY_INSTANCE not in NODE_TYPES


def test_type_property_keys():
    assert PROP_DATASTATE_INSTANCE_TYPE == "datastate_type"
    assert PROP_CAPACITY_INSTANCE_TYPE == "capacity"


# ── validation ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad", ["", None])
def test_empty_task_id_rejected(bad):
    with pytest.raises(ValueError):
        datastate_instance_iri("datastate:x", bad, "p", 0)


@pytest.mark.parametrize("bad", ["", None])
def test_empty_run_ref_rejected(bad):
    with pytest.raises(ValueError):
        datastate_instance_iri("datastate:x", "t", bad, 0)
