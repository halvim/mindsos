"""The origin record names what was asked, BY CONTENT — plan item I-17, gate 3.

Plan rulings R23, R32, R33, R34; ADR-0210 amendment 7. Gate 2 put the digests
and the framing on the ANSWER; nothing a reader writes carried them, so a
stored conclusion could name its prompt but never prove it was the one that
ran. Each test pins one claim:

* a reading's record carries the prompt digest, the schema TEXT and digest,
  the framing and the key version — equal to what the client stamped, and
  enough to show the schema and verify it (R23, R32, R34);
* a refusal for an undecodable answer carries them too, plus the model
  identity, the mode and the level (R33) — before this gate it carried none
  of them, I-11's mode and level included.

No network, no credential, no FalkorDB. The persisted round trip is
``test_a_reading_reaches_its_source_text.py``'s, which now recomputes the key
from the record alone.
"""

from __future__ import annotations

import json

from mindsos_capacity.builtins.comprehension_v0 import build_reader
from mindsos_capacity.builtins.origin_v0 import (
    BASIS_STATED,
    REFUSAL_MALFORMED_RESPONSE,
    origin_record_iri,
)
from mindsos_capacity.identifiers import datastate_iri
from mindsos_llm.live import CapturingLLM, LiveLLM
from mindsos_llm.recording import RecordingStore, schema_digest, text_digest

SOURCE_DS = datastate_iri("asked.submission")
VALUE_DS = datastate_iri("asked.days_waited")
RECORD_DS = origin_record_iri(VALUE_DS)
TEXT = "It took seven days to hear back."
WORDS = "read how many days the customer waited"
SCHEMA = {"type": "object", "properties": {"fields": {"type": "array"}}}
FRAMING = dict(tool_name="extract", tool_description="pull the fields out", max_tokens=512)

#: The fields this gate adds — hand-written, never imported from ``origin_v0``:
#: a checker's list derived from the code it checks cannot notice the code
#: dropping one.
ASKED = (
    "prompt_digest", "schema_digest", "tool_name", "tool_description",
    "max_tokens", "key_schema_version",
)


class _Ctx:
    def __init__(self, llm):
        self.llm = llm


def _reader():
    return build_reader(
        name="read_days_waited_asked",
        source_datastate_iri=SOURCE_DS,
        value_datastate_iri=VALUE_DS,
        prompt_iri="prompt:asked.days",
        prompt_version=2,
        field_name="days",
        question="how many days the customer waited",
        description="Read how many days the customer says they waited.",
        origin_party_phrase="the customer",
        source_identity_phrase="their submission",
        expected_basis=BASIS_STATED,
        extraction_schema=SCHEMA,
    )


def _client(transport):
    return LiveLLM(transport, model_id="m-1", model_version="v-1",
                   credential_level=1, resolve_prompt=lambda **_: WORDS, **FRAMING)


def _read(llm):
    out = _reader().implementation(**{SOURCE_DS: TEXT}, context=_Ctx(llm))
    return out[RECORD_DS]


def test_a_readings_record_carries_what_was_asked_and_the_schema_verifies():
    """MUTATION: in ``comprehension_v0._record`` write ``resp.get("schema")``
    for ``FIELD_SCHEMA_DIGEST`` — red here, and in the union freeze's check
    that every live field carries a value somewhere (it would carry none)."""
    sent = {}

    def transport(**call):
        sent.update(call)
        return {"fields": [{"name": "days", "value": 7, "quote": "seven days",
                            "basis": BASIS_STATED}]}

    record = _read(_client(transport))
    assert record["prompt_digest"] == text_digest(sent["prompt_text"])
    assert record["tool_name"] == sent["tool_name"] == "extract"
    assert record["tool_description"] == sent["tool_description"]
    assert record["max_tokens"] == sent["max_tokens"] == 512
    assert record["key_schema_version"] == "2"
    shown = json.loads(record["extraction_schema"])
    assert shown == SCHEMA == sent["extraction_schema"]
    assert schema_digest(shown) == record["schema_digest"], (
        "the schema a record SHOWS must re-hash to the digest of the schema "
        "the client SENT, or the record is showing a different question"
    )


def test_an_undecodable_answers_refusal_names_what_was_asked():
    """R33. MUTATION: drop ``getattr(exc, "asked", None)`` from the
    malformed-response ``_refuse`` call — red here."""
    live = _client(lambda **_: "this is not json")
    record = _read(CapturingLLM(live, RecordingStore()))
    assert record["refusal_reason"] == REFUSAL_MALFORMED_RESPONSE
    for field in ASKED + ("model_id", "request_key", "credential_level"):
        assert record[field] is not None, field
    assert record["prompt_digest"] == text_digest(WORDS)
    assert record["mode"] == "capture"
    assert record["credential_level"] == 1
