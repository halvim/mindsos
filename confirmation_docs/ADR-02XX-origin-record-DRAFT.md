---
title: Origin records — where a value came from, for any producer
status: Proposed
implemented: no
date: 2026-08-08
supersedes: none
---

# ADR-02XX — Origin records

**DRAFT. The number is unassigned deliberately** — 0206 is the highest on
`main` and the CORE-C2 / C3 lanes are active and may claim 0207 concurrently.
The owner assigns at merge. Filed under `confirmation_docs/` following the
existing `ADR-0150-amendment-9-DRAFT.md` precedent.

**Status is `Proposed`, not `Accepted`.** This arrives from a go-to-market
branch, and RULES §8 says a subsystem owns nothing architectural. Recording
the decision does not ratify it.

---

## Context

Decision Records sells one sentence:

> *"Denied: elapsed days 47 against a limit of 30, from the claims policy,
> version 4, in force since 12 March."*

Producing it requires every value in a run to carry where it came from, and
the acceptance gate requires that to be rendered from the run's grounding
graph and from nothing computed beside it.

The shape was first built inside the `comprehension` family, because a
language model reading a document was the first producer of origin.

## Decision

**Origin is a core concept, not a comprehension one.** The record shape, the
taxonomy and the guards move to `mindsos_capacity/builtins/origin_v0.py`;
`comprehension_v0` becomes one *producer* of that shape.

### Why — the deciding argument

Not "two producers wanted a shared shape". That would have justified leaving
it in `comprehension` with a second consumer.

**The single most load-bearing origin statement in the product — which
policy, which version, in force when — is produced by a `decision`-family
lookup and never touches a language model.** If the shape lives in the
comprehension family, the one origin statement the product turns on is the
one that cannot use it, and the renderer ends up phrasing two shapes that
mean the same thing.

A third producer already exists in outline (structured ingest), and it is
what makes the *"same answers, different origins"* comparison possible: the
same cases run once from a structured export and once from prose, where the
values match and only the origins differ.

### What the shape is

- **A spine of twelve fields every producer writes**, including
  `origin_producer_kind`, `supplied_fields` and `possible_refusal_reasons`.
- **Producer-declared fields** — quote and basis for a reading, version and
  in-force window for a lookup — that some producers supply and others do
  not.
- **A closed union**, `ORIGIN_UNION`, currently 30 fields.
- **A global refusal vocabulary** of seven reasons, with each producer
  declaring the subset it could ever emit.

### Three rules that carry the design

**1. Never infer from absence.** A missing `quote` on a lookup record is
normal; on a document reading it means something went wrong. Absence cannot
mean the same thing across producers, so every record declares what its
producer *always* supplies. Inside that list a missing value is a defect;
outside it, normal.

**2. Tokens branch, phrases print.** Every token has a paired registered
phrase, and `assert_printable_phrase` refuses anything containing `:` at
registration. A Decision Record forbids every IRI and every MindsOS term,
and code must never branch by parsing English. This is the shipped
`FindVerdict.reason` / `.detail` split.

**3. Denormalised on purpose.** `origin_producer_kind` and `supplied_fields`
are written onto every record, never looked up from the module at render
time. An Episode archived today and rendered in a year must not depend on a
module that has since gained a producer — and `persist_capacity_mm` persists
the run graphs while the L3 catalog is persisted separately and remains
mutable, so a render-time lookup would silently show the wrong origin.

### Two fields, not one

`origin_party_phrase` names *who asserted it* ("the customer");
`source_identity_phrase` names *what was consulted* ("their submission
email", "the claims policy"). They were one welded string until the money
sentence was assembled from the union and would not come out: a lookup
consults an authority and has no asserting party. Every producer supplies
the source; only some supply a party.

### The refusal vocabulary is global, not per-producer

The renderer branches on `refusal_reason`, so it must branch on **one**
vocabulary rather than one whose meaning depends on who wrote the record —
the same argument that produced `supplied_fields`. Each record therefore
carries `possible_refusal_reasons`, and `build_origin_record` raises if a
producer emits a reason it did not declare.

The set was comprehension-only until the policy lookup was described: *"no
policy in force at that date"* is one of the slice's five runs and had no
reason at all. `no_source_in_force` (a finding about the customer's case) and
`source_unreachable` (an environment fault, the exact analogue of
`model_unreachable`) close it.

### Environment faults are not findings

`environment_fault` is **derived** from the refusal reason, never passed, so
a producer cannot mislabel its own outage as a fact about the customer's
case. *"The document does not say"* belongs in a customer's refusal list;
*"our reading service was down"* does not, and a refusal list padded with
our outages stops being the artifact an engagement is sold on.

### The union is v0 and not frozen

Neither consumer exists — no Record renderer, no policy lookup. A field set
frozen before its consumers are built is a guess with a process attached.
`ORIGIN_UNION` is closed **by agreement**: a new producer kind is a
negotiation, not a pull request. Freeze after the second producer proves it.

## Placement

`mindsos_capacity/builtins/` — the established home for opt-in families core
does not bootstrap. `reduction_v0` is the precedent: not a member of
`FUNCTIONAL_CATEGORIES`, category graph created lazily at first register.
Nothing here is bootstrapped and nothing enters a Global catalog unless a
caller registers it.

**Registration is Global or Local.** `register_reader(session=...)` places
the DataStates and capacity in that user's Local metagraph. Local-first is
the Decision Records trial: prove the shape without touching the Global
catalog, and promote deliberately.

## Consequences

**Guards must be scope-aware, and this is the trap.** A guard reading only
the Global index passes silently the moment registration moves Local —
exactly the configuration a Local-first trial chooses. `metagraphs_in_scope`
exists for this and every walk in the module uses it.

**A Local trial is all-or-nothing today.** `pipeline._view_for` returns
Global *or* Local and never both, so a Local-registered capacity cannot
compose with a Global one. Until the two-tier union view lands
(`feat/capacity-two-tier-resolution`), the whole path must be Local. This is
a constraint on the demo, not on the design.

**An opaque value consumed by a decision capacity is a defect every time.**
`opaque_into_decision` walks the registry and finds the pairing whichever
side registered first. It must be called from the test that boots the whole
Skill, not a package-scoped test — the pairing spans lanes. Making this an
error inside `CapacityLayer.register_capacity` is the right end state and is
filed as a separate CR; it is core surface and not this branch's to add.

## Alternatives rejected

- **Leave the shape in `comprehension`.** The policy lookup would import
  from a reading family, or reinvent the shape.
- **A per-producer free-form `detail` mapping** to keep the union small.
  Free-form provenance under another name; the renderer would parse keys
  nobody declared.
- **Look origin up from the capacity registration at render time.**
  `Capacity.to_properties()` does not persist custom fields, and the catalog
  is mutable and separately persisted — an archived Episode would render the
  wrong origin with no drift signal.
- **One slot for version and basis.** They answer different questions —
  *was the value present or derived* versus *which edition was consulted* —
  and a reader over a versioned document legitimately has both.
