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

**It states what it cannot check.** Four properties of §6.3 — no silent
retry, no substituted default, the timeout honoured, the document not
logged where MindsOS cannot see it — are not observable from outside a
transport, and a harness that quietly omitted them would read as a
clean bill of health. They are reported as ``unverifiable`` by name, in
the same report as the passes (RULES §11: a list of only successes is a
pitch).

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
)


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
            returned_type=", ".join(c.name for c in self.failures)
        )


def _client(transport: Any) -> LiveLLM:
    return LiveLLM(
        transport,
        model_id="contract-probe",
        model_version="contract-probe",
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
    except TypeError as exc:
        checks.append(Check(
            "accepts_the_five_keywords", FAILED,
            f"the transport rejected the declared signature: {exc}",
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
            "answer_is_text_or_a_mapping", FAILED,
            f"returned {exc.returned_type}, which is neither",
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
        missing = [
            f for f in ("model_id", "model_version", "prompt_iri",
                        "prompt_version", "temperature", "request_key",
                        "recorded")
            if f not in payload
        ]
        checks.append(Check(
            "identity_is_stamped_above_the_transport",
            FAILED if missing else PASSED,
            f"absent: {missing}" if missing else "",
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
    "TransportReport",
    "UNVERIFIABLE_PROPERTIES",
    "verify_transport",
]
