---
title: Reading a stored authority as of a date — the policy lookup and the criterion it feeds
status: Proposed
date: 2026-08-12
supersedes: none
---

# ADR-0208 — The policy lookup, and the criterion it feeds

**Status:** Proposed

`Proposed`, not `Accepted`, for the same reason ADR-0207 is: the Record renderer
does not exist. What is built here runs end to end and is gated, but the
consumer that will read the graph these capacities write has not been written,
and `Accepted` is reserved for a decision someone has read against the code it
governs.

---

## Context

The `policies` L2 role (CORE CR: the policy role, ADR-0150 amendment) shipped a
shape, an IRI builder and a sentence saying what an as-of lookup *means* —
*"select the edition whose window CONTAINS the asked-about date, NOT the latest
edition, which is a different and wrong answer for any question about the
past."* Nothing implemented that sentence, nothing wrote an edition, and no
capacity read the store. `CapacityMMWriter.record` writes only
`(capacity_iri, input IRIs, outputs)`, so a limit read inside a body and never
declared as an output never reaches the grounding graph, and a Decision Record
is rendered from that graph and nothing else.

Item 3 of `confirmation_docs/DECISION_RECORDS_V0_PLAN.md` is that lookup, and
the criterion capacity it feeds.

---

## Decisions

### D1 — The lookup is `retrieval`, not `decision`

**Reverses the owner ruling of 2026-08-09.** That ruling put the lookup at
`capacity:decision:*` because it was *"the only shape where both rules agree"* —
`family_rule_for` returning VERDICT through the category key, and
`origin_v0.DECISION_SHAPED_CATEGORIES`, which matches on category, being able to
see it.

Neither half survives reading the code. `family_rule_for` is exported and tested
and **called by no shipped module**, so what it returns for an IRI is a fact
about nothing. And `DECISION_SHAPED_CATEGORIES` exists to catch an **opaque
value consumed by a capacity that compares it against a limit** — that is the
criterion capacity, which stays `capacity:decision:*` and stays covered. What
the ruling actually bought was a lookup filed in the decision category graph and
inheriting the VERDICT don't-know contract.

`retrieval` is one of the thirteen bootstrapped `FUNCTIONAL_CATEGORIES` and its
family rule is `OPTIONAL_RETURN`, which is what a lookup that may find nothing
needs. Pinned by
`tests/decision_records/test_policy_lookup_capacity.py::test_the_lookup_is_retrieval_and_gets_the_optional_return_contract`.

### D2 — The version lives in the limit's origin record, not as a second consumed input

The plan and the shipped route probe both wire three inputs into the criterion:
income, limit, **version**. The criterion does not compute with the version. It
compares an income against a limit. The version was there so a CONSUMES edge
would exist and the Record could print *"version 2024.1"*.

That is provenance occupying the position of an operand, in the one product
where the difference between "a value the system used" and "a fact about where a
value came from" is the thing being sold. `origin_v0` already carries
`source_version`, `source_in_force_from` and `source_in_force_to`, and an origin
record is itself a **declared output**, so the version stays graph-resident and
attributable either way.

⟹ the lookup declares **two outputs** — the limit and `<limit>_origin` — and the
criterion declares **two inputs** — the income and the limit.

### D3 — The criterion writes no origin record

An origin record answers *where did this value enter MindsOS from*. A verdict
did not enter; it was derived, and the derivation is already in the grounding
graph as CONSUMES edges into the criterion's own `CapacityInstance`. Emitting
one would require a fourth `producer_kind`, widening a union `origin_v0`
declares *"closed by agreement… freeze after the second producer proves it"* —
and the policy lookup **is** the second producer. The plan's *"both emit origin
records"* line is corrected rather than implemented.

### D4 — Two refusals, two mechanisms, and the split is the point

- **`no_source_in_force`** — the store holds no edition covering the date. A
  finding about the customer's own policy set, so the lookup **returns**: the
  limit is `None`, the origin record carries the reason, the criterion sees the
  `None` and returns a not-determined verdict, and the run stays renderable.
- **`source_unreachable`** — the store could not be read. Our outage, never a
  finding about their case, so the lookup **raises**: the step fails and L-2's
  `RunStopped` node records which capacity stopped the run.

A Record that reported an outage as a gap in a customer's policy set would be
false, and a refusal that killed the step would replace a wrong answer with no
Record at all. Both halves are gated, and both are shown red by mutation.

**Overlapping in-force windows raise for a third reason.** The store
contradicts itself, and every tie-break would state an authority the store does
not carry. `AmbiguousEditionsError` is deliberately *not* mapped onto
`no_source_in_force`, which means *there is no edition*.

### D5 — The criterion checks for a missing operand, and that line is load-bearing

`core-dispatch-value-validation` is deferred (unsafe before L-2, now unblocked
but unbuilt). `_validate_inputs` checks input **presence** and never the value,
so a refused lookup arrives at the criterion as a present key holding `None` and
**nothing in core will stop it**. Every capacity that decides must check until
that lands. Stated here so the next author of a criterion does not have to
rediscover it.

### D6 — Editions are Global; the capacities are Local

An authority is shared. A per-user copy of a stated threshold is the shape that
lets one user's override silently restate what the policy said — the objection
that kept this store out of `learned-parameters`. The capacities stay Local
because `register_capacity` validates against the target realm's DataState graph
and `_mirror_global_datastates` copies Global→Local only, so the mixed-realm
arrangement is unbuildable today (`core-datastate-realm-free`). That constraint
is L3's and does not reach an L2 role graph.

### D7 — `KLHandle` declares the read surface its first caller uses

`read_at_version(iri, version)` resolves an IRI the caller already knows. Here
the edition's identity *is* the answer, so selection is a scan of the role-graph
for a window containing a date — `MetagraphView.iter_nodes`. The Protocol gains
`global_view()`. Without it the body would duck-type past the declaration into
the concrete `KnowledgeLayer` and nothing would record that the dependency
exists. The declaration is made failable by a test asserting a handle offering
only `read_at_version` is **not** a `KLHandle`; deleting the method turns it red.

### D8 — No new verdict dataclass, and `context.py`'s field count is untouched

`CapacityContext` ships four canonical verdict types, all L4-orchestration
shapes carrying a `rationale` string. A domain verdict has none, and the
Record's "why" comes from the grounding graph — never from prose a capacity
wrote about itself. The verdict is a typed scalar. **`decision`'s VERDICT family
rule is therefore honoured by naming convention only**, which costs nothing
today precisely because `family_rule_for` has no caller (D1), and is worth
saying out loud rather than leaving as an assumption.

### D9 — Mechanism is core; the authority, the criterion and the prose are not

`mindsos_knowledge/policies.py` (window containment, the guarded write) and
`mindsos_capacity/builtins/policy_lookup_v0.py` (a factory that builds a lookup
for any authority) are core, because the next consumer of the store must not
re-derive them (RULES §8). One particular threshold, one criterion and one prose
vocabulary are content and live in `tests/decision_records/_dr_fixtures.py`
until the demo has a home of its own.

### D10 — Append-only is enforced at the only door there is

`validate_mutation_discipline` is still uncalled system-wide and
`tests/policy_role/test_policy_role_core.py::test_append_only_is_declared_but_not_enforced`
still pins that hole — **it is not deleted by this ADR**. What is now true is
narrower and real: `write_policy_edition` refuses to replace an edition that
already exists, so the one path that populates the store cannot rewrite history.
`handle.graph().remove_node()` still can. **Nobody may write "append-only policy
store" in anything a customer reads** on the strength of this.

---

## Consequences

- The `policies` role has its first reader and its first writer.
- Runs 1, 3 and 5 of the plan's five execute end to end on `main`, composed by
  `ConjunctionFinder` and grounded through `execute_pipeline` with the real
  `L4Dispatcher`. Run 2 waits on item 5's structured-ingest reader; the reader
  here is a marked stand-in.
- Guards **G7** and **G8′** are re-homed from `tests/decision_records/test_route_probe.py`,
  which STATE marks for deletion the day L4 gains plural-start expressiveness.
  **G8′ is a gap-pin, not a guard, and is deleted the day DataStates go
  realm-free.**
- The route probe's two-lookup config B is now unused by anything shipped. It
  stays: it is a diagnostic recording what the finder can do, not a design.
- `mindsos_capacity.__all__` and `mindsos_knowledge.__all__` are **unchanged** —
  new constants are imported from their modules, per the technique items 1 and 2
  proved.

---

## Amendment 1 — D4 gains a third refusal: the date the caller ASKED ABOUT is not a date

**Amendment status:** Accepted
**Date:** 2026-08-18

### What D4 said, and why this is not a contradiction of it

D4 is titled *"Two refusals, two mechanisms, and the split is the point"*, and
its own text already carries a third mechanism — `AmbiguousEditionsError`,
*"deliberately not mapped to `no_source_in_force`, which means there is no
edition"*. **The number in the title was never the decision. The rule was**, and
D4 states it plainly:

> A Record that reported an outage as a gap in a customer's policy set would be
> false.

**This amendment applies that rule to a cause D4 did not enumerate**, by reading
it in the mirror: *a Record that reports a bad INPUT as our outage is false in
the same way.*

### The defect

`edition_in_force` parses two kinds of date — the `as_of` its caller asks about,
and the in-force window bounds the store holds. Both raised `ValueError`, and
`policy_lookup_v0` caught them together and reported both as
`PolicyStoreUnreachableError` / `source_unreachable`. The module said so about
itself in a standing NOTE and filed it as `decision-records-as-of-date-validity`.

⟹ **A caller supplying a date that is not a date, or no date at all, was told
"this is a fault on our side and is never a finding about the case"** — a
sentence that is false about their input, on a page.

### The decision

- **`as_of_not_a_date` joins the vocabulary** (`origin_v0.REFUSAL_REASONS`,
  and `REASONS_EMITTED_TODAY` because a producer emits it). It is **not** an
  `ENVIRONMENT_FAULT_REASON`: the store is fine.
- **It RETURNS, exactly as `no_source_in_force` does.** The limit is `None`, the
  origin record carries the words, the criterion sees the `None` and returns a
  not-determined verdict, and the run stays renderable. Raising would stop the
  member and cost a claim its conclusion — which is the same reasoning D4 gives
  for the gap case.
- **The origin record names the value AS GIVEN**, so the page states a fact
  about the input.
- **A malformed date the STORE holds still raises**, unchanged. Then nothing
  about the question was wrong and the outage classification is correct.
- **The two are told apart by WHICH FIELD failed to parse, never by re-parsing.**
  `policies._parse` now raises `PolicyDateError` carrying its `field`, and
  `policies.AS_OF_FIELD` is the one constant both modules compare against. A
  second implementation of "what is a date" in the lookup would be free to
  disagree with the role's, silently.

### What it does not decide

It does not type any DataState as a date. A reader refusing a non-date at read
time is defence in depth and is a separate change; **it would not have fixed
this defect**, because a refused read produces `None` and `None` is what took
the outage road.

### Why it was found

The Decision Records demo put a dated policy lookup behind its routing rule, so
an exposure stating no date printed the outage sentence on the two beats every
showing traverses. Recorded because the ADR's rule was already sufficient to
forbid it and nobody had read it in the mirror.
