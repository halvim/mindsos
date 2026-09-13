"""The transport contract, as a harness a DEPLOYMENT can run (S-3).

**Why this is product code and not a test.** The transport is written by
the deployment, not by us (§6.4: no vendor inside MindsOS, credentials in
the transport's closure, the gate has no network). "Your transport
behaves correctly" therefore has to be checkable *where the transport
lives* — against a live provider, in the deployment's own environment,
by someone who does not have this repo's test tree. A harness under
``tests/`` is not installed by ``pyproject`` and cannot be imported
there. So it ships here, and the core gate runs the very same function
against fakes (critic §85 Q1's condition, owner ruling 7).

**It states what it cannot check.** The §6.3 properties named in
:data:`UNVERIFIABLE_PROPERTIES` are not observable from outside a
transport, and a harness that quietly omitted them would read as a
clean bill of health. They are reported as ``unverifiable`` by name, in
the same report as the passes (RULES §11: a list of only successes is a
pitch). *The tuple is the list; this sentence does not carry a count,
because a count written in prose beside a tuple goes stale and this one
twice did.*

**Usage.** The failure checks need transports that fail on purpose, which
a live provider will not do on demand — pass them and they run, omit them
and they are reported skipped:

    report = verify_transport(my_transport, prompt_iri=..., prompt_version=1,
                              source_text="...")
    print(report)
    report.raise_if_failed()
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple

from .exceptions import (
    LLMCallFailed,
    MalformedResponse,
    TransportContractError,
    TransportSignatureError,
)
from .live import LiveLLM

PASSED = "passed"
FAILED = "failed"
SKIPPED = "skipped"
UNVERIFIABLE = "unverifiable"

#: §6.3 properties no external observer can establish. Named, never
#: silently omitted.
UNVERIFIABLE_PROPERTIES: Tuple[Tuple[str, str], ...] = (
    ("no_silent_retry",
     "a retried call is invisible from outside the transport"),
    ("no_substituted_default",
     "an invented answer is indistinguishable from a real one here"),
    ("timeout_honoured",
     "requires controlling the provider's latency"),
    ("document_not_logged_elsewhere",
     "where the document goes is a contractual question, not a code one"),
    # ADR-0210 §5. The scrub is ENFORCED in ``seam.send``'s ``finally`` and
    # guarded on both the success and failure paths — but only against the
    # object THIS repo composed. A harness that merely calls a transport
    # cannot reach the request that transport built, and one that injects an
    # opener to reach it asserts the property in the one configuration where
    # it holds. That is round four, and naming it is the honest move.
    ("credential_not_retained_on_the_composed_request",
     "requires reaching inside the transport; a harness that injects an "
     "opener asserts it in the one configuration where it holds"),
)


#: The fields the client stamps over whatever the transport returned.
#: This harness states them ITSELF rather than importing the client's own
#: list: a copy DERIVED from the code under test cannot notice a field that
#: code stopped writing, which is the silent under-check this one list can
#: produce. ``tests/llm_seam/test_transport_contract.py`` reconciles the two
#: BY BEHAVIOUR — it reads what a live call actually stamps — so the
#: independence costs nothing and the drift is still caught (RULES §12's
#: seventh practice: check the claim at its strongest reading).
#: ⚠ NAMES ONLY, NEVER VALUES. A declaration that can carry a value is one a
#: caller can pass, and that is the defect ADR-0210 decision 5 closed for
#: ``mode``.
STAMPED_ABOVE_THE_TRANSPORT: Tuple[str, ...] = (
    "model_id",
    "model_version",
    "prompt_iri",
    "prompt_version",
    "temperature",
    "request_key",
    "recorded",
    "mode",
    "credential_level",
)

_FORGED = "forged-by-the-contract-probe"


def _forging_transport(**_: Any) -> Mapping[str, Any]:
    """A transport that answers with every stamped field filled in wrongly.

    ⚠ **Fabricated here, never a parameter.** The property under test —
    *identity is stamped ABOVE the transport* — is a property of THIS
    repo's client, not of the consumer's transport. A ``forging_transport=``
    keyword would report SKIPPED for every consumer who did not know to pass
    one, which is the same silence this check exists to end, and it would ask
    the deployment to supply the fixture that proves our claim.
    """
    forged = {name: _FORGED for name in STAMPED_ABOVE_THE_TRANSPORT}
    forged["answer"] = "a forged answer"
    return forged


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str = ""

    def __str__(self) -> str:
        tail = f" — {self.detail}" if self.detail else ""
        return f"[{self.status.upper():<12}] {self.name}{tail}"


@dataclass(frozen=True)
class TransportReport:
    """The raw result. Print it; it is meant to be read unedited."""

    checks: Tuple[Check, ...]

    @property
    def ok(self) -> bool:
        return not any(c.status == FAILED for c in self.checks)

    @property
    def failures(self) -> Tuple[Check, ...]:
        return tuple(c for c in self.checks if c.status == FAILED)

    def __str__(self) -> str:
        return "\n".join(str(c) for c in self.checks)

    def raise_if_failed(self) -> None:
        if self.ok:
            return
        raise TransportContractError(
            violation=", ".join(c.name for c in self.failures)
        )


def _client(transport: Any) -> LiveLLM:
    # ``credential_level=None`` is a decision, not an omission: this harness
    # probes somebody else's transport and cannot know the terms its
    # credential was obtained under. ``LiveLLM`` takes no default precisely so
    # that this line has to say so.
    return LiveLLM(
        transport,
        model_id="contract-probe",
        model_version="contract-probe",
        credential_level=None,
        max_calls=8,
    )


def verify_transport(
    transport: Any,
    *,
    prompt_iri: str,
    prompt_version: int,
    source_text: str,
    extraction_schema: Optional[Mapping[str, Any]] = None,
    failing_transport: Any = None,
    garbage_transport: Any = None,
    wrong_type_transport: Any = None,
) -> TransportReport:
    """Run every contract check that can be run against ``transport``."""
    checks = []

    try:
        payload = _client(transport).read(
            prompt_iri=prompt_iri,
            prompt_version=prompt_version,
            source_text=source_text,
            extraction_schema=extraction_schema,
        )
    except TransportSignatureError as exc:
        # Caught BEFORE its base class below — a transport that will not
        # accept the call is a different defect from one that answers
        # wrongly, and reporting the first as the second is what sent the
        # earlier version of this harness green on a broken transport.
        checks.append(Check(
            "accepts_the_five_keywords", FAILED, exc.violation,
        ))
    except MalformedResponse:
        checks.append(Check("accepts_the_five_keywords", PASSED))
        checks.append(Check(
            "answer_is_text_or_a_mapping", FAILED,
            "returned text that does not decode to a JSON object",
        ))
    except TransportContractError as exc:
        checks.append(Check("accepts_the_five_keywords", PASSED))
        checks.append(Check(
            "answer_is_text_or_a_mapping", FAILED, exc.violation,
        ))
    except LLMCallFailed:
        checks.append(Check("accepts_the_five_keywords", PASSED))
        checks.append(Check(
            "answer_is_text_or_a_mapping", SKIPPED,
            "the call failed; re-run when the provider is reachable",
        ))
    else:
        checks.append(Check("accepts_the_five_keywords", PASSED))
        checks.append(Check("answer_is_text_or_a_mapping", PASSED))
        # ⚠ ``mode`` and ``credential_level`` joined this list with ADR-0210
        # decisions 5 and 6. They belong to THIS check by its own name: both
        # are stamped above the transport — one from the class that answered,
        # one from what L0 pushed into it — so a transport cannot supply
        # either, which is the property the check is named for.
        missing = [f for f in STAMPED_ABOVE_THE_TRANSPORT if f not in payload]
        # ⚠ This check asks PRESENCE, and that is now deliberate rather than
        # a gap: OVERRIDE is asked separately, below, against a probe this
        # module fabricates. TWO CHECKS, NOT ONE, because the two reds are
        # different diagnoses — presence-red is a payload that never carried
        # the fields, override-red is a client that stopped stamping them.
        # (Until that second check existed this one stood alone and a
        # consumer's report read PASS on a transport that forges identity:
        # ``core-llm-contract-identity-check-asks-presence-not-override``.)
        checks.append(Check(
            "identity_is_stamped_above_the_transport",
            FAILED if missing else PASSED,
            f"absent: {missing}" if missing else "",
        ))

    # ⚠ CORE'S OWN PROPERTY, AND IT ALWAYS RUNS. The check above asks whether
    # the stamped fields are PRESENT on the consumer's answer; this one asks
    # whether they are OURS. The probe is fabricated (see
    # :func:`_forging_transport`) rather than supplied, because an optional
    # ``forging_transport=`` would read SKIPPED for everyone who did not know
    # to pass one — the same silence the check exists to end.
    try:
        forged = _client(_forging_transport).read(
            prompt_iri=prompt_iri,
            prompt_version=prompt_version,
            source_text=source_text,
            extraction_schema=extraction_schema,
        )
    except Exception as exc:  # noqa: BLE001 — the probe answers; anything else is the finding
        checks.append(Check(
            "identity_overrides_a_transport_that_supplies_its_own", FAILED,
            f"the fabricated probe raised {type(exc).__name__}",
        ))
    else:
        survived = [
            f for f in STAMPED_ABOVE_THE_TRANSPORT if forged.get(f) == _FORGED
        ]
        checks.append(Check(
            "identity_overrides_a_transport_that_supplies_its_own",
            FAILED if survived else PASSED,
            f"the transport's own value survived on: {survived}"
            if survived else "",
        ))

    if failing_transport is None:
        checks.append(Check(
            "raises_rather_than_returning_on_failure", SKIPPED,
            "pass failing_transport= to run this",
        ))
    else:
        try:
            _client(failing_transport).read(
                prompt_iri=prompt_iri, prompt_version=prompt_version,
                source_text=source_text, extraction_schema=extraction_schema,
            )
        except LLMCallFailed:
            checks.append(Check("raises_rather_than_returning_on_failure", PASSED))
        except Exception as exc:  # noqa: BLE001 — any other type is the finding
            checks.append(Check(
                "raises_rather_than_returning_on_failure", FAILED,
                f"raised {type(exc).__name__}, expected LLMCallFailed",
            ))
        else:
            checks.append(Check(
                "raises_rather_than_returning_on_failure", FAILED,
                "returned a value where it should have raised",
            ))

    if garbage_transport is None:
        checks.append(Check(
            "undecodable_text_is_a_malformed_answer", SKIPPED,
            "pass garbage_transport= to run this",
        ))
    else:
        try:
            _client(garbage_transport).read(
                prompt_iri=prompt_iri, prompt_version=prompt_version,
                source_text=source_text, extraction_schema=extraction_schema,
            )
        except MalformedResponse as exc:
            checks.append(Check(
                "undecodable_text_is_a_malformed_answer",
                PASSED if exc.raw is not None else FAILED,
                "" if exc.raw is not None else "the raw answer was not retained",
            ))
        except Exception as exc:  # noqa: BLE001
            checks.append(Check(
                "undecodable_text_is_a_malformed_answer", FAILED,
                f"raised {type(exc).__name__}, expected MalformedResponse",
            ))
        else:
            checks.append(Check(
                "undecodable_text_is_a_malformed_answer", FAILED,
                "returned a value where it should have refused",
            ))

    if wrong_type_transport is None:
        checks.append(Check(
            "a_forbidden_return_is_a_deployment_bug", SKIPPED,
            "pass wrong_type_transport= to run this",
        ))
    else:
        try:
            _client(wrong_type_transport).read(
                prompt_iri=prompt_iri, prompt_version=prompt_version,
                source_text=source_text, extraction_schema=extraction_schema,
            )
        except TransportContractError:
            checks.append(Check("a_forbidden_return_is_a_deployment_bug", PASSED))
        except Exception as exc:  # noqa: BLE001
            checks.append(Check(
                "a_forbidden_return_is_a_deployment_bug", FAILED,
                f"raised {type(exc).__name__}, expected TransportContractError",
            ))
        else:
            checks.append(Check(
                "a_forbidden_return_is_a_deployment_bug", FAILED,
                "returned a value where it should have raised",
            ))

    for name, why in UNVERIFIABLE_PROPERTIES:
        checks.append(Check(name, UNVERIFIABLE, why))

    return TransportReport(tuple(checks))


__all__ = [
    "Check",
    "STAMPED_ABOVE_THE_TRANSPORT",
    "TransportReport",
    "UNVERIFIABLE_PROPERTIES",
    "verify_transport",
]
