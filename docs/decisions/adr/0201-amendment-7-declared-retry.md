# ADR-0201 — Amendment 7: bounded member retry becomes a declared capacity property

**Status:** Accepted (2026-08-16). Closes `core-member-transient-retry-mode`,
opened by the partial-record ship (#166) with the instruction to decide it
"the day the transport arrives". It arrived: the external-model reading seam
is the first capacity in the tree that can fail transiently.

## Context

Amendment 6 kept `MEMBER_RETRY_CAP = 2` and retried every plain step failure.
The register entry that shipped alongside it named the problem in its own
words: *"bounded retry has NO transient failure mode to catch in the
deterministic path — a deterministic body fails identically twice, so the
retry only ever burns a duplicate graph attempt; the mode it was built for
(flaky IO, model calls) arrives with the transport."*

Two things changed on 2026-08-16. A capacity that really can fail
transiently now exists (`comprehension_v0`, reading a document through a
deployment-supplied transport). And the failure classes on that path are not
alike: a network blip deserves a second attempt, while a spend ceiling
(`LLMCallBudgetExceeded`) and a replay miss (`RecordedResponseMiss`) must not
be retried at all — retrying past a ceiling defeats the ceiling, which is the
one thing it exists to do.

Neither fact is expressible by a blanket loop.

## Decision

**Retry requires TWO declarations to agree.**

1. **The capacity** declares whether it can fail transiently at all:
   `Capacity.retryable`, default `False`. A deterministic body fails
   identically on a second attempt, so the honest default is not to retry it.
2. **The failure** declares whether this particular one is transient:
   a `retryable` attribute on the exception. `LLMCallFailed` sets it `True`;
   `LLMCallBudgetExceeded`, `RecordedResponseMiss` and
   `TransportContractError` set it `False` and are never retried even inside
   a capacity that opted in.

`_run_one_member` consults both (`_failure_is_retryable`). Unknown on either
side takes that side's safe answer: an exception carrying no opinion is
allowed (the capacity already opted in); a declaration that cannot be
resolved is not.

Everything amendment 6 decided about STOPPING is unchanged — an exhausted or
undeclared member still stops IN PLACE with its final attempt's graph
retained, its siblings still run, and the fold still stops `partial_domain`.
What changes is only how many attempts precede the stop.

`needs_input`, `cancelled` and no-route keep their am-6 rules and never reach
this check: they are terminal on the first occurrence for reasons that have
nothing to do with transience.

## Consequences

- A failing member of an undeclared capacity now stops after ONE attempt
  instead of two. No graph count changes: `_run_member_pipeline` is pure and
  only the final attempt was ever retained.
- Three phase-48 fixtures that pin bounded retry declare `retryable=True`, so
  the behaviour they test is still the behaviour under test. The multi-input
  fixture declares it for one capacity only, so the same file also covers the
  undeclared side.
- `comprehension_v0` readers declare `retryable=True`. A total model outage
  therefore costs two calls per exposure rather than one — deliberate, and
  the fatal set bounds the pathological cases.
- The register entry `core-member-transient-retry-mode` closes.

## Alternatives considered

1. **Keep the blanket retry.** Rejected — it doubles every model outage's
   spend and latency for no gain on the deterministic paths, which are all of
   the shipped ones.
2. **Classify transience on the exception alone.** Rejected (critic §88 Q3):
   it asks every raiser across every author to label its own failures, which
   is a convention rather than a mechanism. The declaration is static,
   greppable and enforced at registration.
3. **A retry-policy object on the declaration** (counts, backoff, jitter).
   Rejected as premature: one bit answers the question in front of us, and a
   policy object invites configuration nobody has asked for.
