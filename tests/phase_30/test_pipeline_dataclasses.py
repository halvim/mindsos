"""Phase 30 — Pipeline + PipelineStep dataclass shape."""

from __future__ import annotations

import pytest

from mindsos_capacity import Pipeline, PipelineStep


def test_pipeline_step_frozen_dataclass():
    step = PipelineStep(
        capacity_iri="capacity:perception:test.echo",
        input_datastates=("datastate:test.input",),
        output_datastates=("datastate:test.output",),
        via_datastate="datastate:test.input",
    )
    assert step.capacity_iri == "capacity:perception:test.echo"
    assert step.input_datastates == ("datastate:test.input",)
    assert step.output_datastates == ("datastate:test.output",)
    assert step.via_datastate == "datastate:test.input"

    with pytest.raises(Exception):  # FrozenInstanceError; specific type changed across Python releases
        step.capacity_iri = "other"  # type: ignore[misc]


def test_pipeline_step_via_datastate_optional():
    step = PipelineStep(
        capacity_iri="capacity:perception:test.x",
        input_datastates=(),
        output_datastates=("datastate:test.output",),
    )
    assert step.via_datastate is None


def test_pipeline_empty_steps():
    p = Pipeline(
        start_datastate="datastate:a",
        target_datastate="datastate:a",
        steps=(),
    )
    assert len(p) == 0
    assert list(p) == []


def test_pipeline_len_and_iter():
    s1 = PipelineStep(
        capacity_iri="cap:a",
        input_datastates=("ds:in",),
        output_datastates=("ds:mid",),
        via_datastate="ds:in",
    )
    s2 = PipelineStep(
        capacity_iri="cap:b",
        input_datastates=("ds:mid",),
        output_datastates=("ds:out",),
        via_datastate="ds:mid",
    )
    p = Pipeline(
        start_datastate="ds:in",
        target_datastate="ds:out",
        steps=(s1, s2),
    )
    assert len(p) == 2
    assert list(p) == [s1, s2]
