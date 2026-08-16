"""Errors raised by the external-model client.

**Two channels, deliberately separate.** A failure here reaches a reader
twice: as customer-visible prose (``str(exc)``, which
``execute_pipeline`` writes onto L-2's ``RunStopped`` node as
``stopped_detail`` and a Decision Record prints) and as structured
attributes that only code and a traceback see. They are not the same
string and must never be merged — the precedent is
``policy_lookup_v0.PolicyStoreUnreachableError``, whose docstring states
the rule and whose pin asserts the token stays OUT of the printed text.

**Every ``str(exc)`` in this module is FIXED PROSE written by us.** No
provider message, no URL, no IRI, no request key, no ``max_calls``
number, no exception class name from outside this repo. Operator detail
lives on attributes; the underlying failure lives on ``__cause__``.

**Why the rule covers every class here, not only the outage.** Found
2026-08-16 (coordination §87 T-F1): the archived seam interpolated
``{type(exc).__name__}: {exc}`` plus a prompt IRI into the outage
message, and the demo renderer printed all of it — the critic's re-run
(§88) put a URL, a key-shaped string, an exception class and an IRI on a
customer page. Extended while building T1: ``runtime.invoke`` envelopes
EVERY exception, so the budget and replay-miss messages reach the same
node by the same path. A ceiling number and a response-set hash are
MindsOS internals and belong on a page no more than a provider's
stack does.
"""

from __future__ import annotations

from typing import Any


class LLMError(Exception):
    """Base class for every model-client failure."""

    #: May a member retry after this? Read by
    #: ``mindsos_intelligence.execution`` alongside the capacity's own
    #: ``retryable`` declaration — BOTH must say yes. Default ``False``
    #: here: most failures in this module are ours and deterministic, and
    #: the one transient failure says so explicitly.
    retryable = False

    #: The one sentence a customer may see. Subclasses override it; no
    #: call site composes a message out of anything it did not write.
    MESSAGE = "the reading service failed"

    def __init__(self) -> None:
        super().__init__(self.MESSAGE)


class RecordedResponseMiss(LLMError):
    """A replayed reading was requested and no recorded response matched.

    Deliberately fatal, and deliberately NOT retryable (the fatal-set
    exemption, critic §88 Q3): a replay store that silently fell through
    to a live provider — or to a fabricated answer — would let a Decision
    Record present an unrecorded reading as a recorded one. A miss is a
    configuration error in the recorded set, not a don't-know about the
    world.

    A miss means the prompt, its version, the model, the temperature or
    the source text changed since the set was recorded. Re-record rather
    than loosening the key. That guidance is for an operator, so it is
    here in the docstring and on the attributes below — never in
    ``str(exc)``.
    """

    MESSAGE = "this reading was not available from the recorded set"

    def __init__(self, request_key: str = "", set_size: int = 0) -> None:
        super().__init__()
        #: The key that missed. Operator-facing; never rendered.
        self.request_key = request_key
        #: How many responses the set held. Operator-facing.
        self.set_size = int(set_size)


class LLMCallBudgetExceeded(LLMError):
    """The client's ``max_calls`` ceiling was reached.

    Deliberately fatal and NOT retryable. Retrying past the ceiling
    defeats the one thing the ceiling exists to do — bound the spend on a
    batch nobody is watching (critic §88 Q3). Raise ``max_calls``
    deliberately rather than by default.
    """

    MESSAGE = "the reading budget for this run was exhausted"

    def __init__(self, max_calls: int = 0) -> None:
        super().__init__()
        #: The ceiling that was hit. Operator-facing; never rendered.
        self.max_calls = int(max_calls)


class LLMCallFailed(LLMError):
    """The transport raised: the reading service could not be reached.

    Not retried inside this package and never answered from a saved
    response instead — a silent fallback would let a run present a stale
    reading as a fresh one. The provider's own exception is on
    ``__cause__``.
    """

    #: The closed token, on the exception rather than inside its text.
    #: The literal is deliberate: this package does not import the origin
    #: vocabulary (``mindsos_capacity.builtins.origin_v0``), so the two
    #: stay decoupled — agreement is pinned by a test instead, and drift
    #: is a red gate rather than an import.
    refusal_reason = "model_unreachable"

    #: The one transient failure in this module: a network blip, a rate
    #: limit, a provider hiccup. A second attempt is worth making, and a
    #: capacity that declares itself retryable gets one.
    retryable = True

    MESSAGE = "the reading service could not be reached"


class MalformedResponse(LLMError):
    """The model answered, and its answer could not be decoded.

    A FINDING ABOUT THE ANSWER, not about the environment — so this is
    the one failure in this module that becomes a refusal on a record
    rather than a stop (coordination §85/§86 Q2 (b)). The reader catches
    exactly this and refuses ``malformed_response``, keeping :attr:`raw`
    beside the refusal so a person can see what was actually returned
    (the S-7 family discipline: retain the words).

    :attr:`raw` is the model's own output. It is not in ``str(exc)``: it
    reaches a record field the reader chooses, deliberately, rather than
    arriving on a page through a failure path nobody inspected.
    """

    refusal_reason = "malformed_response"

    MESSAGE = "the model's answer could not be read"

    def __init__(self, raw: Any = None) -> None:
        super().__init__()
        #: Exactly what the transport returned, unmodified.
        self.raw = raw


class TransportContractError(LLMError):
    """The transport returned something its contract forbids.

    Separate from :class:`LLMCallFailed` and :class:`MalformedResponse`
    on purpose. A transport that returns an ``int`` is a DEPLOYMENT BUG,
    not an outage and not a bad answer — calling it ``model_unreachable``
    blames the network for our code, and calling it
    ``malformed_response`` blames the model for our code. Neither belongs
    on a customer's page (§7A: our failures never pad their refusal
    list).

    Fatal and not retryable: the same wrong value comes back next time.
    """

    MESSAGE = "the reading service is misconfigured"

    def __init__(self, returned_type: str = "") -> None:
        super().__init__()
        #: The offending type's name. Operator-facing; never rendered.
        self.returned_type = returned_type


__all__ = [
    "LLMCallBudgetExceeded",
    "LLMCallFailed",
    "LLMError",
    "MalformedResponse",
    "RecordedResponseMiss",
    "TransportContractError",
]
