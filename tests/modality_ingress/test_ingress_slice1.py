"""ADR-0197 slice 1 — environment-threaded spine + InputEnvelope.

Guards the two load-bearing invariants of the first slice:

* the all-v0 interpretation path is **byte-identical** after the spine was
  de-hardcoded (the env-threaded rewrite dispatches the same steps with the
  same inputs), and
* an :class:`InputEnvelope` with ``modality=None`` is equivalent to passing
  the raw value, and ``source`` never affects interpretation.
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.phase1_v0 import (
    TRIVIAL_TASK_PATTERN_IRI,
    install_phase1_v0,
)
from mindsos_knowledge import KnowledgeLayer
from mindsos_intelligence import (
    InputEnvelope,
    InterpretationResult,
    L4Dispatcher,
    interpret,
)


def _dispatcher() -> L4Dispatcher:
    cl = CapacityLayer()
    install_phase1_v0(cl)
    return L4Dispatcher(cl, session=None, kl=KnowledgeLayer.bootstrap())


def test_v0_all_placeholder_path_unchanged() -> None:
    r = interpret(_dispatcher(), "hello world")
    assert isinstance(r, InterpretationResult)
    # identity process is a passthrough → structured == raw
    assert r.structured_input == "hello world"
    assert r.hints == {}
    assert r.goal == {"goal": "v0:trivial-goal"}
    assert r.task_pattern_iri == TRIVIAL_TASK_PATTERN_IRI
    assert r.mapping_confidence == 1.0
    assert r.resolved_reference is None


def test_envelope_raw_value_equivalent_and_source_ignored() -> None:
    raw = interpret(_dispatcher(), "hi")
    env = interpret(
        _dispatcher(),
        InputEnvelope(value="hi", modality=None, source="button:go"),
    )
    assert isinstance(env, InterpretationResult)
    assert env.structured_input == raw.structured_input == "hi"
    assert env.task_pattern_iri == raw.task_pattern_iri
    assert env.mapping_confidence == raw.mapping_confidence
    # source is provenance only — it changes nothing about interpretation.
