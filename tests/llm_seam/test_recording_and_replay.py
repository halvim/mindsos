"""``mindsos_llm`` — request key, replay, and the provenance stamp.

The substrate half of the external-model seam. Everything asserted here
is about *not* letting a Decision Record misrepresent where a reading
came from: a replayed reading must say it was replayed, a recording file
must not be able to claim a model it did not come from, and a miss must
be loud rather than silently answered.
"""

from __future__ import annotations

import pytest

from mindsos_llm import RecordedResponseMiss, RecordingStore, RecordedLLM, request_key


def _key(**over):
    args = dict(
        prompt_iri="prompt:claims.purchase_date",
        prompt_version=1,
        model_id="model-x",
        model_version="2026-05-01",
        temperature=0.0,
        source_text="purchased on 3 March 2026",
    )
    args.update(over)
    return request_key(**args)


def test_request_key_is_deterministic():
    assert _key() == _key()


@pytest.mark.parametrize(
    "field, value",
    [
        ("prompt_version", 2),
        ("prompt_iri", "prompt:claims.purchase_date.reworded"),
        ("model_id", "model-y"),
        ("model_version", "2026-06-01"),
        ("temperature", 0.7),
        ("source_text", "purchased on 4 March 2026"),
    ],
)
def test_every_determinant_of_a_reading_changes_the_key(field, value):
    # A re-worded prompt, a different model or an edited document is a
    # different question. It must miss rather than silently reuse the
    # previous run's answer.
    assert _key(**{field: value}) != _key()


def test_a_miss_raises_rather_than_falling_through():
    llm = RecordedLLM(
        RecordingStore({}), model_id="model-x", model_version="2026-05-01"
    )
    with pytest.raises(RecordedResponseMiss):
        llm.read(
            prompt_iri="prompt:claims.purchase_date",
            prompt_version=1,
            source_text="purchased on 3 March 2026",
        )


def test_replayed_reading_is_stamped_recorded_and_cannot_lie_about_the_model():
    store = RecordingStore(
        {
            _key(): {
                "fields": [{"name": "purchase_date", "value": "2026-03-03",
                            "quote": "3 March 2026", "basis": "stated"}],
                # A recording file claiming to be a live answer from a
                # different model must not survive the stamp.
                "recorded": False,
                "model_id": "some-other-model",
            }
        }
    )
    llm = RecordedLLM(store, model_id="model-x", model_version="2026-05-01")
    reading = llm.read(
        prompt_iri="prompt:claims.purchase_date",
        prompt_version=1,
        source_text="purchased on 3 March 2026",
    )
    assert reading["recorded"] is True
    assert reading["model_id"] == "model-x"
    assert reading["model_version"] == "2026-05-01"
    assert reading["prompt_version"] == 1
    assert reading["request_key"] == _key()


def test_store_round_trips_through_json():
    store = RecordingStore({_key(): {"fields": []}})
    assert len(store) == 1
    assert _key() in store
    assert "fields" in store.to_json()
