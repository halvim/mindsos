"""composition-lifecycle — typed input_group field (ADR-0159 §amendment-1).

The field is additive + default-valued (every pre-amendment capacity is
unchanged); ``register_capacity`` validates the value against the
three-member set.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import (
    INPUT_GROUP_ALL_REQUIRED,
    INPUT_GROUP_ANY_OF,
    INPUT_GROUP_FOLD,
    INPUT_GROUPS,
    CapacityRegistrationError,
)

from tests.composition_lifecycle._fixtures import cap, layer


def test_default_is_all_required():
    c = cap("plain", ("a",), ("b",))
    assert c.input_group == INPUT_GROUP_ALL_REQUIRED


def test_input_groups_membership():
    assert INPUT_GROUPS == {
        INPUT_GROUP_ALL_REQUIRED,
        INPUT_GROUP_ANY_OF,
        INPUT_GROUP_FOLD,
    }


@pytest.mark.parametrize("mode", sorted(INPUT_GROUPS))
def test_valid_input_group_registers(mode):
    cl = layer("a", "b")
    cl.register_capacity(cap("c", ("a",), ("b",), mode))
    assert cl.get_declaration("capacity:perception:c").input_group == mode


def test_invalid_input_group_rejected_at_registration():
    cl = layer("a", "b")
    bad = cap("c", ("a",), ("b",))
    bad.input_group = "majority_vote"  # _CapacityBase is a non-frozen dataclass
    with pytest.raises(CapacityRegistrationError) as exc:
        cl.register_capacity(bad)
    assert "input_group" in str(exc.value)


def test_to_properties_does_not_emit_input_group():
    """Decision 8: the field stays on the declaration; no graph-layer
    structure is emitted for it at v1 (the finder reads the registry)."""
    c = cap("c", ("a",), ("b",), INPUT_GROUP_FOLD)
    assert "input_group" not in c.to_properties()
