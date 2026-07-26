"""ADR-0197 slice 2 — modality table + text wiring.

Proves the phase1↔text disconnect is closed: a text-stamped input is
tokenized by the shipped ``text.space_split`` capacity inside ``interpret``,
and the tokens are consumed downstream (the hint body reports ``n_tokens``).
Also checks selection precedence and fallback.
"""

from __future__ import annotations

from mindsos_capacity import CapacityLayer
from mindsos_capacity.builtins.phase1_v0 import TRIVIAL_REQUEST_PATTERN_IRI
from mindsos_capacity.builtins.phase1_text import (
    TEXT_DERIVE_GOAL_IRI,
    TEXT_HINT_IRI,
    TEXT_MAP_IRI,
    TEXT_MODALITY_DS,
    TEXT_PROCESS_IRI,
    TEXT_REQUEST_PATTERN_IRI,
    install_phase1_text,
)
import pytest

from mindsos_knowledge import KnowledgeLayer, ROLE_REQUEST_PATTERNS
from mindsos_intelligence import (
    InputEnvelope,
    InterpretationResult,
    L4Dispatcher,
    Phase1Profile,
    interpret,
)
from mindsos_intelligence.phase_1 import InterpretationError


def _text_profile() -> Phase1Profile:
    return Phase1Profile(
        process=TEXT_PROCESS_IRI,
        hint=TEXT_HINT_IRI,
        derive_goal=TEXT_DERIVE_GOAL_IRI,
        map=TEXT_MAP_IRI,
    )


def _setup():
    cl = CapacityLayer()
    install_phase1_text(cl)
    kl = KnowledgeLayer.bootstrap()
    g = next(
        gr for gr in kl.global_metagraph().graphs.values()
        if gr.role == ROLE_REQUEST_PATTERNS
    )
    g.add_node(
        value=TEXT_REQUEST_PATTERN_IRI,
        type_name="RequestPattern",
        node_id=TEXT_REQUEST_PATTERN_IRI,
    )
    dispatcher = L4Dispatcher(
        cl,
        session=None,
        kl=kl,
        modality_profiles={TEXT_MODALITY_DS: _text_profile()},
    )
    return dispatcher


def test_text_modality_tokenizes_by_capacity() -> None:
    d = _setup()
    r = interpret(d, InputEnvelope(value="hello world foo", modality=TEXT_MODALITY_DS))
    assert isinstance(r, InterpretationResult)
    # process = the real text.space_split → structured input IS the tokens
    assert r.structured_input == ["hello", "world", "foo"]
    # the hint body consumed those tokens (disconnect closed)
    assert r.hints == {"n_tokens": 3}
    assert r.request_pattern_iri == TEXT_REQUEST_PATTERN_IRI
    assert r.mapping_confidence == 1.0


def test_unstamped_input_falls_back_to_v0() -> None:
    d = _setup()
    # No modality on the envelope → construction-bound profile (None) → v0.
    r = interpret(d, InputEnvelope(value="hi", modality=None))
    assert r.structured_input == "hi"  # identity passthrough, not tokenized
    assert r.request_pattern_iri == TRIVIAL_REQUEST_PATTERN_IRI


def test_unknown_modality_raises_not_v0() -> None:
    d = _setup()
    with pytest.raises(InterpretationError, match="unroutable modality"):
        interpret(d, InputEnvelope(value="hi", modality="datastate:image.raw"))


def test_modality_routes_to_wrong_ingress_raises() -> None:
    cl = CapacityLayer()
    install_phase1_text(cl)
    kl = KnowledgeLayer.bootstrap()
    bad = L4Dispatcher(
        cl,
        session=None,
        kl=kl,
        modality_profiles={"datastate:image.raw": _text_profile()},
    )
    with pytest.raises(InterpretationError, match="requires them"):
        interpret(bad, InputEnvelope(value="hi", modality="datastate:image.raw"))
