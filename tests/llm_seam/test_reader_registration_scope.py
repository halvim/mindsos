"""Where a reader registers, and what registration refuses.

**Only two tests came across from the archive's
``test_origin_contract_and_scope.py``, and that is the finding.** That
module was 255 lines, and all but these are already on ``main`` in
``tests/origin_records/test_origin_contract.py`` — the origin half was
lifted out of the seam branch at plan item 1 (#143) and has evolved since.
Taking the module wholesale would have duplicated a shipped suite under a
second name, which is how two sources of truth for one contract begin.
What is genuinely new is reader-specific: scope, and the no-decide guard
seen from the reader's side.

**Local first is the Decision Records trial.** Nothing enters the Global
catalog until the shape is proven. Note the standing limit: today
``pipeline._view_for`` returns Global *or* Local and never both, so a
Local trial means the whole path must be Local until a two-tier union view
lands.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins import origin_v0 as origin
from mindsos_capacity.builtins.comprehension_v0 import register_reader
from mindsos_capacity.capacity import Capacity
from mindsos_capacity.datastate import DataState, ShapeDescriptor
from mindsos_capacity.exceptions import CapacityRegistrationError
from mindsos_capacity.identifiers import (
    CATEGORY_COMPREHENSION,
    CATEGORY_DECISION,
    datastate_iri,
)

SOURCE_DS = datastate_iri("claims.submission_email")
DAYS_DS = datastate_iri("claims.elapsed_days")


class _Session:
    def __init__(self, user_id):
        self.user_id = user_id
        self.session_id = "s"

    def has(self, _capability):  # pragma: no cover - not consulted here
        return True


def _register_datastate(layer, iri, kind, session=None):
    shape = (
        ShapeDescriptor.opaque(iri)
        if kind == "opaque"
        else ShapeDescriptor.scalar(kind, opaque_tag=iri)
    )
    layer.register_datastate(
        DataState(name=iri.split(":", 1)[-1], shape=shape, description="d",
                  provenance_category=CATEGORY_COMPREHENSION),
        session=session, allow_new_realm=True,
    )


def _reader(layer, session):
    return register_reader(
        layer, name="read_days", source_datastate_iri=SOURCE_DS,
        value_datastate_iri=DAYS_DS, value_description="Elapsed days.",
        prompt_iri="prompt:claims.elapsed_days", prompt_version=1,
        field_name="elapsed_days", question="how many days elapsed",
        description="Read elapsed days.",
        origin_party_phrase="the customer",
        source_identity_phrase="their submission email",
        expected_basis=origin.BASIS_STATED,
        value_shape=ShapeDescriptor.scalar("int", opaque_tag=DAYS_DS),
        session=session,
    )


def test_a_local_reader_registers_into_the_local_metagraph_only():
    layer = CapacityLayer()
    session = _Session("dr-user")
    _register_datastate(layer, SOURCE_DS, "str", session=session)
    reader = _reader(layer, session)
    local = layer.local_metagraph("dr-user").metagraph_id
    glob = layer.global_metagraph().metagraph_id
    assert reader.iri in layer._capacity_index[local]
    assert reader.iri not in layer._capacity_index.get(glob, {})


def test_the_no_decide_guard_sees_a_LOCAL_decision_capacity():
    """The mechanical form of "the model reads, it does not decide", and
    the reason it looks in both realms: a guard reading only Global passes
    silently the moment registration moves Local — which is exactly the
    configuration a Local-first trial chooses."""
    layer = CapacityLayer()
    session = _Session("dr-user")
    _register_datastate(layer, SOURCE_DS, "str", session=session)
    _register_datastate(layer, DAYS_DS, "opaque", session=session)
    layer.register_capacity(
        Capacity(name="assess_window", category=CATEGORY_DECISION,
                 inputs=(), outputs=(DAYS_DS,), implementation=lambda **kw: {},
                 description="Decide."),
        session=session,
    )
    with pytest.raises(CapacityRegistrationError):
        _reader(layer, session)
