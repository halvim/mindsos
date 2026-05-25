"""Phase 30 — invoke() raises CapacityRegistrationError for unknown IRI.

Per ADR-0072 §Decision's "L3 raises for its own invariants" carve-out —
unknown IRI is a caller bug, not an envelope failure. Sink stays empty.
"""

from __future__ import annotations

import pytest

from mindsos_capacity import CapacityRegistrationError

from tests.phase_30._fixtures import DS_INPUT_IRI, build_min_layer


def test_invoke_unknown_iri_raises():
    cl = build_min_layer()
    with pytest.raises(CapacityRegistrationError):
        cl.invoke("capacity:perception:no.such.cap", inputs={DS_INPUT_IRI: "x"})


def test_invoke_unknown_iri_does_not_emit_problem_trace():
    cl = build_min_layer()
    try:
        cl.invoke(
            "capacity:perception:no.such.cap",
            inputs={DS_INPUT_IRI: "x"},
            task_id="t1",
        )
    except CapacityRegistrationError:
        pass
    assert len(cl.problem_trace) == 0
