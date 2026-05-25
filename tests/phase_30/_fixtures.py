"""Phase 30 — fixtures driving invoke + BFS finder + ProblemTrace tests.

Test-only Capacity/DataState dataclasses (no Phase 31 text builtins).
Per R3 PB-40(a) layout.

Naming: ``ds:test.<name>`` for DataState IRIs (parses cleanly through
``datastate_iri`` builder when needed; these tests bypass the builder
to keep the test-only namespace deliberate).
"""

from __future__ import annotations

from typing import Any

from mindsos_capacity import (
    CATEGORY_COMPREHENSION,
    CATEGORY_PERCEPTION,
    Capacity,
    CapacityLayer,
    DataState,
    ShapeDescriptor,
    SessionProtocol,
)


# ── DataState IRI constants ────────────────────────────────────────────

DS_INPUT_IRI = "datastate:test.input"
DS_MID_IRI = "datastate:test.mid"
DS_OUTPUT_IRI = "datastate:test.output"
DS_X_IRI = "datastate:test.x"
DS_Y_IRI = "datastate:test.y"
DS_Z_IRI = "datastate:test.z"
DS_FORK_IRI = "datastate:test.fork"


def _ds(short_name: str) -> DataState:
    """Build a test DataState whose IRI is `datastate:test.<short_name>`.

    ``DataState(name="test.input")`` → IRI ``datastate:test.input`` via
    the ``datastate_iri`` builder (PHASE 27 ADR-0066). We prepend the
    ``test.`` namespace deliberately to keep test-only IRIs out of any
    real-capacity namespace.
    """
    full_name = f"test.{short_name}"
    return DataState(
        name=full_name,
        shape=ShapeDescriptor.scalar("str", opaque_tag=full_name),
    )


# ── Test capacities (hand-rolled; no Phase 31 builtins) ───────────────


def build_echo_capacity() -> Capacity:
    """test.input → test.output via identity (success path)."""
    return Capacity(
        name="test.echo",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        implementation=lambda **kw: {DS_OUTPUT_IRI: kw[DS_INPUT_IRI]},
    )


def build_failing_capacity() -> Capacity:
    """test.input → test.output via RuntimeError (exception path)."""

    def _raise(**_kw: Any) -> Any:
        raise RuntimeError("intentional fixture failure")

    return Capacity(
        name="test.boom",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        implementation=_raise,
    )


def build_step1_capacity() -> Capacity:
    """test.input → test.mid (first stage of linear pipeline)."""
    return Capacity(
        name="test.step1",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_MID_IRI,),
        implementation=lambda **kw: {DS_MID_IRI: kw[DS_INPUT_IRI] + "_step1"},
    )


def build_step2_capacity() -> Capacity:
    """test.mid → test.output (second stage of linear pipeline)."""
    return Capacity(
        name="test.step2",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_MID_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        implementation=lambda **kw: {DS_OUTPUT_IRI: kw[DS_MID_IRI] + "_step2"},
    )


def build_multi_output_capacity() -> Capacity:
    """test.input → (test.fork, test.x) — drives shortest-by-capacity invariant."""
    return Capacity(
        name="test.multi",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_INPUT_IRI,),
        outputs=(DS_FORK_IRI, DS_X_IRI),
        implementation=lambda **kw: {
            DS_FORK_IRI: f"f({kw[DS_INPUT_IRI]})",
            DS_X_IRI: f"x({kw[DS_INPUT_IRI]})",
        },
    )


def build_fork_to_output_capacity() -> Capacity:
    """test.fork → test.output (2-capacity path via multi+fork)."""
    return Capacity(
        name="test.fork_to_output",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_FORK_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        implementation=lambda **kw: {DS_OUTPUT_IRI: kw[DS_FORK_IRI]},
    )


def build_x_to_y_capacity() -> Capacity:
    return Capacity(
        name="test.x_to_y",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_X_IRI,),
        outputs=(DS_Y_IRI,),
        implementation=lambda **kw: {DS_Y_IRI: kw[DS_X_IRI]},
    )


def build_y_to_z_capacity() -> Capacity:
    return Capacity(
        name="test.y_to_z",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_Y_IRI,),
        outputs=(DS_Z_IRI,),
        implementation=lambda **kw: {DS_Z_IRI: kw[DS_Y_IRI]},
    )


def build_z_to_output_capacity() -> Capacity:
    """test.z → test.output (3-capacity path via multi+x+y+z)."""
    return Capacity(
        name="test.z_to_output",
        category=CATEGORY_PERCEPTION,
        inputs=(DS_Z_IRI,),
        outputs=(DS_OUTPUT_IRI,),
        implementation=lambda **kw: {DS_OUTPUT_IRI: kw[DS_Z_IRI]},
    )


# ── Layer builders ─────────────────────────────────────────────────────


def build_min_layer() -> CapacityLayer:
    """CapacityLayer with PERCEPTION + the 3 test DataStates; zero capacities."""
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    cl.register_datastate(_ds("input"))
    cl.register_datastate(_ds("mid"))
    cl.register_datastate(_ds("output"))
    return cl


def build_linear_pipeline_layer() -> CapacityLayer:
    """test.input → step1 → test.mid → step2 → test.output."""
    cl = build_min_layer()
    cl.register_capacity(build_step1_capacity())
    cl.register_capacity(build_step2_capacity())
    return cl


def build_branching_capacity_layer() -> CapacityLayer:
    """Shortest-by-capacity-count fixture (R2 PB-34 sentinel).

    Layout:
        test.input ─[test.multi]──▶ test.fork ─[test.fork_to_output]──▶ test.output  (2 caps)
                   └             ──▶ test.x   ─[test.x_to_y]──▶ test.y ─[test.y_to_z]──▶ test.z ─[test.z_to_output]──▶ test.output  (4 caps)

    BFS must pick the 2-cap path (via fork) and assert `len(pipeline) == 2`.
    """
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,))
    for ds_name in ("input", "mid", "output", "fork", "x", "y", "z"):
        cl.register_datastate(_ds(ds_name))
    cl.register_capacity(build_multi_output_capacity())
    cl.register_capacity(build_fork_to_output_capacity())
    cl.register_capacity(build_x_to_y_capacity())
    cl.register_capacity(build_y_to_z_capacity())
    cl.register_capacity(build_z_to_output_capacity())
    return cl


# ── Session fixture (SessionProtocol-conforming dataclass) ────────────


class _LocalTestSession:
    """Minimal SessionProtocol-conforming session for Local-scope tests."""

    def __init__(self, user_id: str = "alice") -> None:
        self.user_id = user_id
        self.session_id = f"test-session-{user_id}"

    def has(self, capability: str) -> bool:  # noqa: D401 — protocol stub
        return True  # tests don't gate on capabilities at L3


def build_session(user_id: str = "alice") -> SessionProtocol:
    """Build a tiny SessionProtocol-conforming object (test-only)."""
    return _LocalTestSession(user_id=user_id)


__all__ = [
    "DS_INPUT_IRI",
    "DS_MID_IRI",
    "DS_OUTPUT_IRI",
    "DS_X_IRI",
    "DS_Y_IRI",
    "DS_Z_IRI",
    "DS_FORK_IRI",
    "build_echo_capacity",
    "build_failing_capacity",
    "build_step1_capacity",
    "build_step2_capacity",
    "build_multi_output_capacity",
    "build_fork_to_output_capacity",
    "build_x_to_y_capacity",
    "build_y_to_z_capacity",
    "build_z_to_output_capacity",
    "build_min_layer",
    "build_linear_pipeline_layer",
    "build_branching_capacity_layer",
    "build_session",
]
