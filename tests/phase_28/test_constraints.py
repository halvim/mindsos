"""Phase 28 — admin-authored CONSTRAINT edges."""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    Capacity,
    CapacityLayer,
    CapacityLayerError,
    CATEGORY_PERCEPTION,
    CATEGORY_RETRIEVAL,
    ConstraintViolationError,
    CONSTRAINT_MUTUALLY_EXCLUSIVE,
    CONSTRAINT_RATE_LIMIT,
    EDGE_CONSTRAINT,
)

from ._fixtures import text_raw_datastate, text_tokens_datastate


def _layer_with_two_perception_caps():
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION, CATEGORY_RETRIEVAL))
    cl.register_datastate(text_raw_datastate())
    cl.register_datastate(text_tokens_datastate())
    raw = text_raw_datastate()
    tokens = text_tokens_datastate()
    cap_a = Capacity(
        name="text.alpha", category=CATEGORY_PERCEPTION,
        inputs=(raw.iri,), outputs=(tokens.iri,),
        implementation=lambda **kw: {tokens.iri: []},
    )
    cap_b = Capacity(
        name="text.beta", category=CATEGORY_PERCEPTION,
        inputs=(raw.iri,), outputs=(tokens.iri,),
        implementation=lambda **kw: {tokens.iri: []},
    )
    cl.register_capacity(cap_a)
    cl.register_capacity(cap_b)
    return cl, cap_a, cap_b


def test_add_constraint_happy_path_mutually_exclusive():
    cl, a, b = _layer_with_two_perception_caps()
    edge = cl.add_constraint(a.iri, b.iri, CONSTRAINT_MUTUALLY_EXCLUSIVE)
    assert edge.type_name == EDGE_CONSTRAINT
    assert edge.properties["constraint_kind"] == CONSTRAINT_MUTUALLY_EXCLUSIVE
    constraints = cl.iter_constraints()
    assert len(constraints) == 1
    assert constraints[0].edge_id == edge.edge_id


def test_add_constraint_with_rate_limit_and_note():
    cl, a, b = _layer_with_two_perception_caps()
    edge = cl.add_constraint(
        a.iri, b.iri, CONSTRAINT_RATE_LIMIT, rate_limit=10, note="dev throttle"
    )
    assert edge.properties["rate_limit"] == 10
    assert edge.properties["note"] == "dev throttle"


def test_add_constraint_rejects_unknown_kind():
    cl, a, b = _layer_with_two_perception_caps()
    with pytest.raises(ConstraintViolationError, match="Unknown constraint kind"):
        cl.add_constraint(a.iri, b.iri, "NONSENSE_KIND")


def test_add_constraint_rejects_missing_endpoint():
    cl, a, _ = _layer_with_two_perception_caps()
    with pytest.raises(ConstraintViolationError, match="must be registered"):
        cl.add_constraint(
            a.iri,
            "capacity:perception:nonexistent",
            CONSTRAINT_MUTUALLY_EXCLUSIVE,
        )


def test_add_constraint_rejects_cross_category():
    cl, a, _ = _layer_with_two_perception_caps()
    raw = text_raw_datastate()
    tokens = text_tokens_datastate()
    retrieval_cap = Capacity(
        name="retrieve.gamma", category=CATEGORY_RETRIEVAL,
        inputs=(raw.iri,), outputs=(tokens.iri,),
        implementation=lambda **kw: {tokens.iri: []},
    )
    cl.register_capacity(retrieval_cap)
    with pytest.raises(ConstraintViolationError, match="Cross-category constraints"):
        cl.add_constraint(a.iri, retrieval_cap.iri, CONSTRAINT_MUTUALLY_EXCLUSIVE)


def test_constraint_violation_error_subclass_of_capacity_layer_error():
    assert issubclass(ConstraintViolationError, CapacityLayerError)
