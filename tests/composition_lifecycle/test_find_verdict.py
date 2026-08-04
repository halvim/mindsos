"""CORE-C3R1 — the ``FindVerdict`` contract (shim S4).

Guards the four properties the CR fixed, so a later chat cannot quietly
loosen them:

* ``reason`` is a **closed set**; consumers branch on it and the dream never
  parses ``detail``;
* ``unproducible`` is **grouped by capacity** — the capacity is what separates
  required children from alternative decompositions;
* the type carries **no ``__bool__``** (CR §4);
* it is exported from ``mindsos_capacity``.
"""

from __future__ import annotations

import mindsos_capacity as mc
from mindsos_capacity import (
    FIND_BFS_EXHAUSTED,
    FIND_MAX_DEPTH_EXCEEDED,
    FIND_NO_SATISFIABLE_PRODUCER,
    FIND_REASONS,
    FIND_REQUIRED_INPUT_UNPRODUCIBLE,
    FIND_UNREGISTERED_TARGET,
    FindVerdict,
)


def test_reason_set_is_closed_and_exactly_five():
    assert FIND_REASONS == {
        FIND_BFS_EXHAUSTED,
        FIND_NO_SATISFIABLE_PRODUCER,
        FIND_MAX_DEPTH_EXCEEDED,
        FIND_REQUIRED_INPUT_UNPRODUCIBLE,
        FIND_UNREGISTERED_TARGET,
    }


def test_exported_from_package():
    for name in (
        "FindVerdict",
        "FIND_REASONS",
        "FIND_BFS_EXHAUSTED",
        "FIND_NO_SATISFIABLE_PRODUCER",
        "FIND_MAX_DEPTH_EXCEEDED",
        "FIND_REQUIRED_INPUT_UNPRODUCIBLE",
        "FIND_UNREGISTERED_TARGET",
    ):
        assert name in mc.__all__
        assert hasattr(mc, name)


def test_retired_exception_is_gone():
    """``PipelineNotFoundError`` is shim S4 and is retired, not deprecated."""
    assert not hasattr(mc, "PipelineNotFoundError")


def test_found_is_explicit_not_truthiness():
    missing = FindVerdict(reason=FIND_NO_SATISFIABLE_PRODUCER, detail="x")
    assert missing.found is False
    assert missing.pipeline is None
    assert "__bool__" not in vars(FindVerdict)


def test_unproducible_is_grouped_by_capacity_and_read_only():
    verdict = FindVerdict(
        reason=FIND_REQUIRED_INPUT_UNPRODUCIBLE,
        detail="x",
        unproducible={"capacity:c": ("datastate:d1", "datastate:d2")},
    )
    assert verdict.unproducible["capacity:c"] == ("datastate:d1", "datastate:d2")
    try:
        verdict.unproducible["capacity:other"] = ()
    except TypeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("unproducible must be read-only")
