"""``capacity:comprehension:record_reading_set`` end to end (``mindsos_llm`` I-10).

Through a real in-memory KnowledgeLayer and ``CapacityLayer.invoke`` — the
direct path, which is the one R7 found unreachable for a capacity that writes
AND declares an output. What the tests hold:

* the run graph NAMES the set: the declared output is the pointer's IRI;
* the pointer is VERIFIABLE against the file it names (R8);
* a re-capture of the same bytes refuses (R18);
* a file that is not a recorded set refuses, with no don't-know, and the
  reason reaches the problem trace (R10);
* the installer registers exactly the shape the factory declares (I-16).
"""

from __future__ import annotations

import hashlib
import json

import pytest

from mindsos_capacity import CapacityLayer, CapacityRegistrationError
from mindsos_capacity.bootstrap import ensure_datastate_graph
from mindsos_capacity.builtins.recorded_set_v0 import (
    DS_READING_SET_RECORD,
    DS_RECORDED_SET_POINTER,
    install_recorded_set_capacities,
    recorded_set_datastates,
)
from mindsos_capacity.identifiers import CATEGORY_COMPREHENSION, capacity_iri
from mindsos_knowledge import KnowledgeLayer
from mindsos_knowledge.recorded_sets import (
    RecordedSetExistsError,
    recorded_set_at,
    recorded_sets,
)
from mindsos_llm.live import CapturingLLM, LiveLLM
from mindsos_llm.recorded_sets import RecordedSetRefused, export_set
from mindsos_llm.recording import RecordingStore

from tests.phase_34._fixtures import build_user_session


CAP_IRI = capacity_iri(CATEGORY_COMPREHENSION, "record_reading_set")
ANSWER = {"fields": [{"name": "days", "value": 7, "quote": "seven days"}]}


def _recording(*texts, level=1):
    store = RecordingStore()
    for text in texts:
        CapturingLLM(
            LiveLLM(lambda **_: dict(ANSWER), model_id="m-1", model_version="v-1",
                    credential_level=level, temperature=0.0),
            store,
        ).read(prompt_iri="prompt:p", prompt_version=1, source_text=text)
    return store


def _layer():
    kl = KnowledgeLayer.bootstrap()
    layer = CapacityLayer(kl=kl)
    install_recorded_set_capacities(layer)
    return kl, layer


def _record(layer, session, path, request_id="R1"):
    return layer.invoke(
        CAP_IRI,
        {DS_READING_SET_RECORD: {"set_path": str(path), "recorded_by": "alice", "note": "trial"}},
        session=session,
        request_id=request_id,
    )


# ── the installer ─────────────────────────────────────────────────────


def test_install_registers_the_capacity_and_both_datastates():
    layer = CapacityLayer()
    install_recorded_set_capacities(layer)
    assert CAP_IRI in {d.iri for d in layer.iter_declarations()}
    graph = ensure_datastate_graph(layer.global_metagraph(), strict=layer._strict)
    assert DS_READING_SET_RECORD in graph.nodes
    assert DS_RECORDED_SET_POINTER in graph.nodes


def test_the_installed_declaration_writes_and_declares_its_pointer():
    """R7 + ADR-0210 am-4: writes AND names what it wrote."""
    layer = CapacityLayer()
    install_recorded_set_capacities(layer)
    d = next(d for d in layer.iter_declarations() if d.iri == CAP_IRI)
    assert d.writes is True
    assert d.outputs == (DS_RECORDED_SET_POINTER,)
    assert d.inputs == (DS_READING_SET_RECORD,)
    assert d.category == CATEGORY_COMPREHENSION


def test_install_is_idempotent():
    layer = CapacityLayer()
    install_recorded_set_capacities(layer)
    install_recorded_set_capacities(layer)
    assert len([d for d in layer.iter_declarations() if d.iri == CAP_IRI]) == 1


def test_partial_install_state_is_refused():
    layer = CapacityLayer()
    layer.register_datastate(recorded_set_datastates()[0])
    with pytest.raises(CapacityRegistrationError, match="partial install state"):
        install_recorded_set_capacities(layer)


# ── the recorder, end to end ──────────────────────────────────────────


def test_recording_a_set_appends_a_verifiable_pointer_and_names_it_in_the_run(tmp_path):
    f = tmp_path / "alice.json"
    f.write_text(export_set(_recording("a", "b")), encoding="utf-8")
    kl, layer = _layer()
    session = build_user_session("alice")

    result = _record(layer, session, f)

    assert result.success is True, result.error
    assert result.write_outcome is None, "a write that declares an output returns it in outputs"
    iri = result.outputs[DS_RECORDED_SET_POINTER]
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    assert iri == f"recorded-sets-v1:set:{sha}"

    node = recorded_set_at(kl.local_view("alice"), sha)
    assert node.properties["file_uri"] == str(f.resolve())
    assert node.properties["sha256"] == sha, "R8: verifiable by re-hashing the named file"
    assert node.properties["responses"] == 2
    assert node.properties["credential_level"] == 1
    assert node.properties["note"] == "trial"
    keys = node.value["request_keys"]
    assert keys == sorted(json.loads(f.read_text(encoding="utf-8"))["responses"])


def test_the_pointer_is_local_to_the_recording_user(tmp_path):
    f = tmp_path / "alice.json"
    f.write_text(_recording("a").to_json(), encoding="utf-8")
    kl, layer = _layer()
    assert _record(layer, build_user_session("alice"), f).success is True
    assert len(recorded_sets(kl.local_view("alice"))) == 1
    assert recorded_sets(kl.local_view("bob")) == []


def test_a_recapture_of_the_same_bytes_is_refused(tmp_path):
    f = tmp_path / "alice.json"
    f.write_text(_recording("a").to_json(), encoding="utf-8")
    _, layer = _layer()
    session = build_user_session("alice")
    assert _record(layer, session, f).success is True
    again = _record(layer, session, f, request_id="R2")
    assert again.success is False
    assert isinstance(again.error, RecordedSetExistsError)


def test_a_file_that_is_not_a_set_refuses_and_the_reason_reaches_the_trace(tmp_path):
    """R10: no don't-know — the capacity refuses, and runtime.invoke carries
    the message to the problem trace because a request_id is present."""
    f = tmp_path / "mixed.json"
    mixed = _recording("a", level=1)
    for key, payload in json.loads(_recording("b", level=2).to_json()).items():
        mixed.put(key, payload)
    f.write_text(mixed.to_json(), encoding="utf-8")
    _, layer = _layer()

    result = _record(layer, build_user_session("alice"), f, request_id="R9")

    assert result.success is False
    assert isinstance(result.error, RecordedSetRefused)
    assert result.outputs == {}
    traced = [r for r in layer.problem_trace.records() if r.request_id == "R9"]
    assert traced and "credential levels" in traced[-1].payload["message"]
