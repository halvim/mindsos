---
title: Origin records — where a value came from, for any producer
status: Proposed
date: 2026-08-08
supersedes: none
---

# ADR-0207 — Origin records

**Status:** Proposed

**Status is `Proposed`, not `Accepted`.** No consumer exists yet — there is no
Record renderer and no policy lookup — and RULES §9 reserves `Accepted` for a
decision someone has read against the code it governs. The shape was authored on
a go-to-market branch (`feat/decision-records`) and RULES §8 says a subsystem
owns nothing architectural; landing the module in core is what this ADR records,
not ratification of the field set.

*(Filed 2026-08-08 as `confirmation_docs/ADR-02XX-origin-record-DRAFT.md` with the
number deliberately unassigned, because the CORE-C2 and C3 lanes were active and
might have claimed 0207 concurrently. Both are paused; the number is assigned
here.)*

---

## Context

Decision Records sells one sentence:

> *"Denied: elapsed days 47 against a limit of 30, from the claims policy,
> version 4, in force since 12 March."*

Producing it requires every value in a run to carry where it came from, and the
acceptance gate requires that to be rendered from the run's grounding graph and
from nothing computed beside it.

The shape was first built inside the `comprehension` family, because a language
model reading a document was the first producer of origin.

## Decision

**Origin is a core concept, not a comprehension one.** The record shape, the
taxonomy and the guards live in `mindsos_capacity/builtins/origin_v0.py`;
`comprehension_v0` becomes one *producer* of that shape.

### Why — the deciding argument

Not "two producers wanted a shared shape". That would have justified leaving it
in `comprehension` with a second consumer.

**The single most load-bearing origin statement in the product — which policy,
which version, in force when — is produced by a `decision`-family lookup and
never touches a language model.** If the shape lives in the comprehension
family, the one origin statement the product turns on is the one that cannot use
it, and the renderer ends up phrasing two shapes that mean the same thing.

A third producer already exists in outline (structured ingest), and it is what
makes the *"same answers, different origins"* comparison possible: the same
cases run once from a structured export and once from prose, where the values
match and only the origins differ.

### What the shape is

- **A spine of twelve fields every producer writes**, including
  `origin_producer_kind`, `supplied_fields` and `possible_refusal_reasons`.
- **Producer-declared fields** — quote and basis for a reading, version and
  in-force window for a lookup — that some producers supply and others do not.
- **A closed union**, `ORIGIN_UNION`, currently 30 fields.
- **A global refusal vocabulary**, with each producer declaring the subset it
  could ever emit.

### Three rules that carry the design

**1. Never infer from absence.** A missing `quote` on a lookup record is normal;
on a document reading it means something went wrong. Absence cannot mean the
same thing across producers, so every record declares what its producer *always*
supplies. Inside that list a missing value is a defect; outside it, normal.

**2. Tokens branch, phrases print.** Every token has a paired registered phrase,
and `assert_printable_phrase` refuses anything containing `:` at registration. A
Decision Record forbids every IRI and every MindsOS term, and code must never
branch by parsing English. This is the shipped `FindVerdict.reason` / `.detail`
split.

**3. Denormalised on purpose.** `origin_producer_kind` and `supplied_fields` are
written onto every record, never looked up from the module at render time. An
Episode archived today and rendered in a year must not depend on a module that
has since gained a producer — and `persist_capacity_mm` persists the run graphs
while the L3 catalog is persisted separately and remains mutable, so a
render-time lookup would silently show the wrong origin.

### Two fields, not one

`origin_party_phrase` names *who asserted it* ("the customer");
`source_identity_phrase` names *what was consulted* ("their submission email",
"the claims policy"). They were one welded string until the money sentence was
assembled from the union and would not come out: a lookup consults an authority
and has no asserting party. Every producer supplies the source; only some supply
a party.

### The refusal vocabulary is global, not per-producer

The renderer branches on `refusal_reason`, so it must branch on **one**
vocabulary rather than one whose meaning depends on who wrote the record — the
same argument that produced `supplied_fields`. Each record therefore carries
`possible_refusal_reasons`, and `build_origin_record` raises if a producer emits
a reason it did not declare.

The set was comprehension-only until the policy lookup was described: *"no
policy in force at that date"* is one of the slice's five runs and had no reason
at all. `no_source_in_force` (a finding about the customer's case) and
`source_unreachable` (an environment fault, the exact analogue of
`model_unreachable`) close it.

### Environment faults are not findings

`environment_fault` is **derived** from the refusal reason, never passed, so a
producer cannot mislabel its own outage as a fact about the customer's case.
*"The document does not say"* belongs in a customer's refusal list; *"our
reading service was down"* does not, and a refusal list padded with our outages
stops being the artifact an engagement is sold on.

### The union is v0 and not frozen

Neither consumer exists — no Record renderer, no policy lookup. A field set
frozen before its consumers are built is a guess with a process attached.
`ORIGIN_UNION` is closed **by agreement**: a new producer kind is a negotiation,
not a pull request. Freeze after the second producer proves it.

## Placement

`mindsos_capacity/builtins/` — the established home for opt-in families core
does not bootstrap. `reduction_v0` is the precedent: not a member of
`FUNCTIONAL_CATEGORIES`, category graph created lazily at first register.
Nothing here is bootstrapped and nothing enters a Global catalog unless a caller
registers it. The module is deliberately **not** exported from
`mindsos_capacity/__init__.py` and imports only `typing` and
`identifiers.parse_capacity_iri`, so landing it edits no existing core module.

**Registration is Global or Local.** A producer registered with a session places
its DataStates and capacity in that user's Local metagraph; without one, Global.
Local-first is the Decision Records trial: prove the shape without touching the
Global catalog, and promote deliberately.

## Consequences

**Guards must be scope-aware, and this is the trap.** A guard reading only the
Global index passes silently the moment registration moves Local — exactly the
configuration a Local-first trial chooses. `metagraphs_in_scope` exists for this
and every walk in the module uses it.

**A Local trial is no longer all-or-nothing, but mixed realms are still
unbuildable — for a different reason.** The 2026-08-08 draft of this ADR said
`pipeline._view_for` returns Global *or* Local and never both, so the whole path
had to be Local until a two-tier view landed. **That is stale**: the
Local-preferring union view shipped in PRs #122 and #123, so one session-scoped
find now sees both realms and carries one verdict. What blocks a mixed-realm
registration today is elsewhere: `register_capacity` validates a capacity's
declared inputs and outputs against the **target realm's** DataState graph, and
`_mirror_global_datastates` copies **Global→Local only**, so a Global capacity
cannot declare a DataState that a Local registration created. Until
`pending_designs.core-datastate-realm-free` closes, a trial mixing a Local
producer with a Global authority does not compose, and the trial registers
all-Local. This is a constraint on the demo, not on the design.

**An opaque value consumed by a decision capacity is a defect every time.**
`opaque_into_decision` walks the registry and finds the pairing whichever side
registered first. Called from a package-scoped test it only sees what that
package registered; the pairing spans lanes, so the load-bearing call is from
the test that boots the whole Skill. Making this an error inside
`CapacityLayer.register_capacity` is the right end state; it is core surface
beyond this module and is tracked as
`pending_designs.core-register-capacity-opaque-into-decision`.

## Alternatives rejected

- **Leave the shape in `comprehension`.** The policy lookup would import from a
  reading family, or reinvent the shape.
- **A per-producer free-form `detail` mapping** to keep the union small.
  Free-form provenance under another name; the renderer would parse keys nobody
  declared.
- **Look origin up from the capacity registration at render time.**
  `Capacity.to_properties()` does not persist custom fields, and the catalog is
  mutable and separately persisted — an archived Episode would render the wrong
  origin with no drift signal.
- **One slot for version and basis.** They answer different questions — *was the
  value present or derived* versus *which edition was consulted* — and a reader
  over a versioned document legitimately has both.

---

## Amendment 1 — a capacity carries the phrase that names it (2026-08-12)

**Amendment status:** Proposed. **Opened by:** `decision-records-capacity-printable-phrase`.

Rule 2 above — *tokens branch, phrases print* — was written for the values a
producer reports on. It applies unchanged to the **producer itself**, and probe
D showed the gap by rendering all four Decision Records run graphs and finding
that nothing in a graph can name a capacity: a `CapacityInstance` carries the
capacity IRI and nothing else, and the criterion writes no origin record (ADR-0208
D3). So *"decided by…"* and *"stopped at…"* had no prose to use.

**`_CapacityBase` gains `printable_phrase`.** Optional, so every capacity
registered before it is unchanged. Validated by `CapacityLayer.register_capacity`
only when supplied, against the same rule this ADR's `assert_printable_phrase`
enforces — which now lives in `mindsos_capacity.printable` as a pure
`printable_phrase_problem`, because core cannot import from `builtins/`.
`assert_printable_phrase` keeps its name, its message and its
`OriginContractError`; registration raises `CapacityRegistrationError` from the
same rule. One rule, two exception types, each owned by its layer.

**It is deliberately not `description`.** A description answers *what does this
capacity do*, is written for a developer, and in the shipped criterion is a
question — *"whether the stated income reaches the threshold in force"* — which
renders as *"decided by whether the stated income reaches the threshold in
force"*. One field cannot answer both that and *what is this called*.

**One sentence in "Alternatives rejected" above is now half wrong, and the half
that survives is the load-bearing half.** *"`Capacity.to_properties()` does not
persist custom fields"* is no longer true: it persists `printable_phrase` when
one is declared. The rejection itself **still stands** — *the catalog is mutable
and separately persisted, so an archived Episode would render the wrong prose
with no drift signal.* That is exactly why the renderer must never read the
catalog: `decision-records-run-manifest` **snapshots the phrase into the run
graph when the run starts**, and the Record renders from that snapshot. The
registered property exists so the manifest has something to copy, not so a
renderer can reach back for it.

---

## Amendment 2 — the union is frozen by classification (2026-08-12)

**Amendment status:** Proposed. **Opened by:** the first RULES §12 check.

This ADR says the union is *"closed by agreement… freeze after the second
producer proves it."* **Three producers have shipped** — document reading, the
policy lookup (ADR-0208), structured ingest (PR #154) — **and the freeze never
happened.** A §12 check found what that cost: the system writes **16 of 30**
fields, and one of them can never carry information at all. Neither fact was
recorded anywhere, because an unclassified union cannot distinguish *"nobody
has built that producer yet"* from *"that field is dead"*.

**The freeze is a classification, not a deletion.** Nothing is removed. Every
field is now exactly one of:

- **`FIELDS_WRITTEN_TODAY`** — some shipped producer emits it, on some path.
- **`FIELDS_RESERVED`** — declared for a producer that does not exist, **each
  naming that producer**. Fourteen fields, twelve of them the LLM seam's.
  Anonymity is forbidden: *"someone might need it"* is how a union stops
  meaning anything.
- **`FIELDS_DEGENERATE`** — written on every record, but whose informative
  value is unreachable. Worse than an unwritten field, because it looks live
  and reads as evidence.

Orthogonally, every field is **`FIELDS_PRINTED`** or **`FIELDS_STRUCTURAL`** —
rendered, or read only to walk the graph and branch.

### The one degenerate field, and why it is pinned rather than deleted

`environment_fault` is **always False, structurally**. It is derived from
`ENVIRONMENT_FAULT_REASONS`, and *both* of those reasons — `model_unreachable`
and `source_unreachable` — are on **raising** paths. A raising step writes no
origin record at all: `execute_pipeline` records the stop, not an output. So no
record carrying this field can ever have been produced by an outage.

**A renderer must take *"was this our fault"* from L-2's `RunStopped` node, and
never from this field.** It is pinned by a test that fails the day the hole
closes — the same shape as `test_append_only_is_declared_but_not_enforced` —
rather than deleted, because removing a field from a union this ADR declares
closed is a negotiation and the pin buys the time to have it.

### Two contract changes that came with the freeze

**A refusal must carry prose.** `refusal_detail` was optional, so a producer
could refuse with a bare token and leave a Record with nothing to print.
`build_origin_record` now refuses that. All three shipped producers already
supplied one, so this pins a contract rather than changing it. It also removes
the reason a `refusal_reason_phrase` field looked necessary: the **token
branches, the detail is the prose**, and adding a generic phrase would have
duplicated the specific one worse.

**`source_datastate` is structural and must never be printed.** It holds a
DataState IRI and rides on every record both shipped producers write. Its prose
counterpart already exists and is `source_identity_phrase`.

### What makes this a freeze rather than a comment

The classification is **checked by running the producers**, not by reading the
lists: every field called live must actually appear in an emitted record, no
reserved field may appear in one, and `environment_fault` must never be `True`.
A producer that stops writing a field, or a new field added without a
classification, turns the gate red. Shown red by mutation on all four paths.

## Amendment 3 — a producer advertises only what a record can carry (2026-08-13)

**Amendment status:** Proposed. **Opened by:** `decision-records-map-manifest`,
closing the OPEN question amendment 2 left on `source_unreachable`.

Amendment 2 classified `source_unreachable` as degenerate and then wrote:
*"⚠ OPEN: whether a producer should stop ADVERTISING a reason it cannot
record."* It should, and `policy_lookup_v0` no longer does.

`possible_refusal_reasons` rides on **every** record a producer writes, admitted
or refused, so that a renderer can tell *"this producer could never say that"*
from *"this producer happened not to"*. That is its whole job, and it only works
if the list is about **records**. The store-unreachable path **raises**
(`PolicyStoreUnreachableError`), and a raising step writes no origin record at
all — `execute_pipeline` records the stop, not an output. So a possible-list
naming it told a renderer *"this lookup could have told you the store was
unreachable"*, which is a sentence no record could ever be the evidence for.

**The token is not deleted.** It remains in the closed `REFUSAL_REASONS` set,
remains the machine-readable `refusal_reason` on the exception, and still
reaches a reader — through L-2's `RunStopped` node, which is where *"was this
our fault"* belongs. It also stays classified `REASONS_DEGENERATE`, because that
classification is about what a **record** can carry, and no record can carry it.

**This changes every record the lookup emits**, which is why amendment 2 filed
it as a decision rather than doing it as a tidy-up. The rule it settles is
general: *a producer must not advertise a refusal reason none of its records can
carry.* The guard is the inverted pin — the test that asserted the reason WAS
advertised now asserts it is not, over the records the shipped producers
actually emit, and it still drives the raising path so the pin keeps its teeth.
