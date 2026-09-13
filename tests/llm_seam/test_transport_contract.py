"""The transport contract harness — S-3, and the reason it is product code.

The transport is written by the DEPLOYMENT (§6.4: no vendor inside
MindsOS, credentials in the transport's closure, the gate has no network).
"Your transport behaves correctly" therefore has to be checkable where the
transport lives, by someone who does not have this repo's test tree — so
the harness ships in ``mindsos_llm.contract`` and this file runs
the same function the demo will run against a live provider (critic §85
Q1's condition, owner ruling 7).

The second thing it must do is SAY WHAT IT CANNOT CHECK. The §6.3
properties named in ``UNVERIFIABLE_PROPERTIES`` are unobservable from
outside a transport, and a harness that quietly omitted them would read as
a clean bill of health. *The tuple is the list; no count is written here,
because a count in prose beside a tuple is what went stale twice.*
"""

from __future__ import annotations

import pytest

from mindsos_llm import contract
from mindsos_llm.contract import (
    FAILED,
    PASSED,
    SKIPPED,
    UNVERIFIABLE,
    UNVERIFIABLE_PROPERTIES,
    verify_transport,
)
from mindsos_llm.exceptions import TransportContractError
from mindsos_llm.live import LiveLLM

ANSWER = {"fields": [{"name": "days", "value": 7, "quote": "seven days"}]}

GOOD = lambda **_: ANSWER
GOOD_TEXT = lambda **_: '{"fields": [{"name": "days", "value": 7}]}'
RAISES = lambda **_: (_ for _ in ()).throw(RuntimeError("connection reset"))
GARBAGE = lambda **_: "here you go: about seven weeks"
WRONG_TYPE = lambda **_: 7


def _verify(transport, **over):
    return verify_transport(
        transport, prompt_iri="prompt:p", prompt_version=1,
        source_text="the document", **over,
    )


def _status(report, name):
    return {c.name: c.status for c in report.checks}[name]


def test_a_correct_transport_passes_every_runnable_check():
    report = _verify(GOOD, failing_transport=RAISES, garbage_transport=GARBAGE,
                     wrong_type_transport=WRONG_TYPE)
    assert report.ok
    assert not [c for c in report.checks if c.status == FAILED]


def test_a_text_returning_transport_is_equally_correct():
    """S-2: returning the model's raw text is a legal transport, which is
    what lets the demo's fifty lines skip JSON-mode plumbing entirely."""
    assert _verify(GOOD_TEXT).ok


def test_a_transport_that_returns_instead_of_raising_FAILS():
    report = _verify(GOOD, failing_transport=GOOD)
    assert not report.ok
    assert _status(report, "raises_rather_than_returning_on_failure") == FAILED


def test_a_transport_returning_a_forbidden_type_FAILS_the_answer_check():
    report = _verify(WRONG_TYPE)
    assert not report.ok
    assert _status(report, "answer_is_text_or_a_mapping") == FAILED


def test_a_transport_with_the_wrong_signature_FAILS():
    report = _verify(lambda prompt_iri: ANSWER)
    assert not report.ok
    assert _status(report, "accepts_the_five_keywords") == FAILED


def test_the_optional_checks_are_reported_SKIPPED_not_omitted():
    """A live provider will not fail on demand, so these are skipped
    against one. Skipped and named beats absent."""
    report = _verify(GOOD)
    for name in ("raises_rather_than_returning_on_failure",
                 "undecodable_text_is_a_malformed_answer",
                 "a_forbidden_return_is_a_deployment_bug"):
        assert _status(report, name) == SKIPPED


def test_the_unverifiable_properties_are_always_named():
    """RULES §11: a list of only successes is a pitch. The properties in
    ``UNVERIFIABLE_PROPERTIES`` cannot be established from outside a
    transport and the report names every one of them every time, including
    when everything else passes."""
    report = _verify(GOOD, failing_transport=RAISES, garbage_transport=GARBAGE,
                     wrong_type_transport=WRONG_TYPE)
    reported = {c.name for c in report.checks if c.status == UNVERIFIABLE}
    assert reported == {name for name, _ in UNVERIFIABLE_PROPERTIES}
    assert report.ok, "unverifiable is not failed - it is unknown, and said so"


def test_the_report_prints_as_something_a_person_reads():
    text = str(_verify(GOOD))
    assert "PASSED" in text and "UNVERIFIABLE" in text
    assert "no_silent_retry" in text


def test_raise_if_failed_names_the_failures():
    report = _verify(WRONG_TYPE)
    with pytest.raises(TransportContractError) as exc:
        report.raise_if_failed()
    assert "answer_is_text_or_a_mapping" in exc.value.violation


def test_raise_if_failed_is_quiet_when_the_contract_holds():
    _verify(GOOD).raise_if_failed()


# ── identity: PRESENCE and OVERRIDE are two checks, not one ────────────


OVERRIDE = "identity_overrides_a_transport_that_supplies_its_own"


def test_a_transport_that_supplies_its_own_identity_is_overridden():
    """The probe answers with every stamped field filled in wrongly and the
    client stamps over all of them. Unlike the three failure probes this
    one takes no keyword: it is fabricated, so it runs for every consumer
    rather than only for the ones who knew to ask."""
    report = _verify(GOOD)
    assert _status(report, OVERRIDE) == PASSED
    assert report.ok


def test_the_override_check_goes_RED_when_the_client_stops_stamping(monkeypatch):
    """RULES §9: a guard is born red. The failure is fabricated — a client
    that hands back the transport's answer untouched — so no offence has to
    be committed to the tree to prove the check can see one.

    It also shows why this is TWO checks: the same report reads PASS on
    ``identity_is_stamped_above_the_transport``, because every field is
    present. Presence-green with override-red is a client that stopped
    stamping; both red is a payload that never carried the fields."""

    class _NoStamp(LiveLLM):
        def read(self, **kwargs):
            return dict(contract._forging_transport(**kwargs))

    monkeypatch.setattr(
        contract, "_client",
        lambda t: _NoStamp(t, model_id="probe", model_version="probe",
                           credential_level=None, max_calls=8),
    )
    report = _verify(GOOD)
    check = {c.name: c for c in report.checks}[OVERRIDE]
    assert check.status == FAILED
    for field in contract.STAMPED_ABOVE_THE_TRANSPORT:
        assert field in check.detail, f"{field} survived unnamed"
    assert _status(report, "identity_is_stamped_above_the_transport") == PASSED


def test_the_declared_stamped_set_is_what_a_live_call_actually_stamps():
    """``STAMPED_ABOVE_THE_TRANSPORT`` is stated by the harness rather than
    imported from the client, because a list derived from the code under
    test cannot notice a field that code stopped writing. The two are
    reconciled HERE, and BY BEHAVIOUR — what a real client puts on an answer
    over a transport that supplied none of it — which is RULES §12's seventh
    practice: check the claim at its strongest reading, not by declaration.

    A field added to the client's stamp and not to the tuple reddens this;
    so does one removed from the client and left in the tuple."""
    bare = LiveLLM(lambda **_: {"answer": "42"}, model_id="m",
                   model_version="v", credential_level=None, max_calls=2)
    payload = bare.read(prompt_iri="prompt:p", prompt_version=1,
                        source_text="doc")
    assert set(contract.STAMPED_ABOVE_THE_TRANSPORT) == set(payload) - {"answer"}
