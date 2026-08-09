# CORE CR — the external-model seam (Decision Records)

**Filed:** 2026-08-08. **Status:** BUILT on `feat/decision-records`, not gated, not merged.
**Verified at:** `origin/main` `5c6c5db`. **Manual:** `confirmation_docs/LLM_SEAM_MANUAL.md`.
**ADR:** `confirmation_docs/ADR-02XX-origin-record-DRAFT.md` (Proposed, number unassigned).

The go-to-market handoff says the external-model reading stage "is a doctrine question
before it is an implementation one, and it should not arrive quietly under this work."
This is that question, answered, with the implementation that follows.

Decisions D1–D11 were settled before the Decision Records planning lane reviewed the seam;
D12–D22 came out of that review. Where the review overturned something, the original is
kept and struck rather than deleted.

---

## 1. The governing line

**The model never enters MindsOS. Its output does — as a typed value that arrives with a
quote from the source document, where MindsOS itself has checked the quote is in the
document.**

---

## 2. Where the split falls

| Concern | Owner |
|---|---|
| Provider protocol, credentials | The **transport** — a function the deployment writes, outside this repo |
| Transport, recording, replay, call ceiling | `mindsos_llm` — substrate, no cognition, imports no other `mindsos_*` |
| Asking, checking, declining | `comprehension.*` capacities — cognition, therefore dispatched |
| The record shape and its guards | `mindsos_capacity/builtins/origin_v0.py` — not comprehension's, see the ADR |
| Handing the capability to a body | `mindsos_intelligence/dispatch.py` |

---

## 3. Decisions

**D1 — The extraction is a capacity; the call is substrate.** A body importing a provider
client would put the call outside dispatch, outside the registry and outside the test seam.

**D2 — `CapacityContext` gains a 12th field, `llm`.** A narrowed capability injected by L4,
following `writeable` (ADR-0180): the body receives a callable, never a client, never
credentials, never a principal.

**D3 — Injection is by category, not a per-capacity flag.** ~~A `consults_llm` field on
every declaration.~~ Overturned during review: capacities already live in per-category
graphs, so membership of `LLM_CATEGORIES` (`comprehension` by default) *is* the
declaration. No new core field, and "what can call a model?" is one registry query.

**D4 — A declaration in an LLM category with no client bound is an error, not a
don't-know** (`LLMUnavailableError`). A body that quietly declined on a deployment fault
would put an unexplained refusal into a Decision Record.

**D5 — One reader per extracted value, not one general extractor.** A factory, not a
catalogue. A single "read the document" capacity produces one opaque payload: nothing for
the finder to compose through, nothing for a Record to cite.

**D6 — Every reading is checked against the source.** The model must return a verbatim
quote; the body locates it in the source text; not found ⟹ refused, with the claimed words
retained. Fabrication becomes a refusal by construction.

**D7 — Uncertainty is structural, never a self-reported number.** A model-supplied
confidence is another output of the process under question. What is recorded is what
MindsOS established: quote verified or not, where, and the registered `expected_basis`.

**D8 — The prompt is versioned and its version reaches the graph.** Same argument as the
policy version. A re-worded prompt is a different question and misses the recorded set
rather than reusing the previous answer.

**D9 — Replay exists for the build gate, not for the demo.** ~~Replay by default.~~
Overturned by the owner: a demo running from saved answers is a scripted demo and deserves
to be called one. Live is the default for anything a customer watches; replay is how the
suite runs without a network. Every reading is stamped `recorded: true|false`.

**D10 — The family's don't-know shape is `OPTIONAL_RETURN`, and it is not `NeedsInput`.**
`NeedsInput` short-circuits output validation, so a reader raising it leaves **no node in
the grounding graph** explaining the gap. Ratifies `comprehension` out of
`DEFERRED_DEFAULT_CATEGORIES` (PHASE_27_DONT_KNOW_AUDIT §amendment-2; four remain).

**D11 — "The model does not decide" is enforced at registration**, not asserted in a doc.

**D12 — A transport failure is a refusal, flagged as ours.** `model_unreachable` sets
`environment_fault`. A run that dies on venue wifi must leave something renderable, and
*"our reading service was down"* must never pad a customer's refusal list —
*"the document does not say"* is a finding; an outage is not.

**D13 — `LLMCallBudgetExceeded` and `RecordedResponseMiss` still raise.** A run-level
policy limit and a fault in our recorded set. A batch stopping loudly beats 300 Records
blaming the customer's documents for our configuration. Batch-level accounting for the
stop belongs to the Decision Records lane.

**D14 — The reader coerces to the declared shape and refuses on failure**
(`value_not_coercible`). *"About seven weeks"* is a reading failure and belongs in the same
record as the quote that caused it. A separate transform capacity would mean two DataState
types per value and a second refusal path for the renderer to phrase.

**D15 — An opaque value consumed by a decision-shaped capacity is a defect every time.**
Three layers: `register_reader` raises; a registry walk (`opaque_into_decision`) catches
the pairing whichever side registered first; and the same rule in
`CapacityLayer.register_capacity` is filed as a **separate CR** — core surface, not this
branch's to add.

**D16 — Origin is core, not comprehension.** See the ADR. Deciding argument: the product's
most load-bearing origin statement is produced by a `decision`-family lookup that never
touches a model.

**D17 — `<value>_origin`, not `<value>_reading`.** ~~`reading_record_iri`.~~ A policy
lookup does not produce a reading. Per value, never one shared type — the executor holds
one value per DataState IRI, so a shared type would displace the first producer's
provenance. `_origin` and not `.origin`: DataState names allow one dot.

**D18 — Never infer from absence.** `origin_producer_kind` + `supplied_fields` on every
record, denormalised, so a missing `quote` on a lookup is normal and on a reading is a
defect.

**D19 — Two phrases, not one.** `origin_party_phrase` (who asserted it) and
`source_identity_phrase` (what was consulted). Found by assembling the money sentence from
the union: a lookup consults an authority and has no asserting party.

**D20 — `basis`, `source_version`, `source_in_force_from`, `source_in_force_to` are
separate fields.** One slot would mean the renderer reads a field whose meaning depends on
who wrote it. A reader over a versioned document legitimately has both.

**D21 — An expected/observed `basis` mismatch is recorded, not refused.** With a verified
quote, a mismatch is ordinary language variation. Refusing would make the demo escalate on
it, which turns a refusal list from a finding into noise. A *systematic* mismatch is a
registration defect and belongs in the batch report.

**D22 — `origin_method` is `read_by_model`.** ~~`inferred_by_model`.~~ It sat beside
`basis: stated` and read as a contradiction.

**D23 — The refusal vocabulary is global, and each producer declares its subset.**
~~A comprehension-only set of four reasons.~~ The renderer branches on `refusal_reason`, so
it must branch on one vocabulary rather than one whose meaning depends on the writer — the
`supplied_fields` argument applied to reasons. `possible_refusal_reasons` joins the spine
(now twelve fields; union 30), and `build_origin_record` raises if a producer emits a reason
it did not declare, so "could never say this" is distinguishable from "happened not to".

**D24 — Two reasons added for the lookup, and the environment/finding split holds.**
`no_source_in_force` — a versioned source consulted, no edition covering that date. A
**finding about the customer's case**: a gap in their own policy set that nobody reviewed,
so it belongs in the refusal list and `environment_fault` stays false.
`source_unreachable` — the store itself is down, the exact analogue of `model_unreachable`
and an environment fault for the same reason. `REFUSAL_NO_VERSION_IN_FORCE` was renamed
`REFUSAL_NO_SOURCE_IN_FORCE` for consistency with the `source_*` field family.

---

## 4. Why provenance is a declared output

`CapacityMMWriter.record` writes a capacity's **declared outputs and nothing else**.
Anything returned another way never becomes a node, and can never legally appear in a
Decision Record. Each reader therefore declares two outputs: the value and its origin
record.

---

## 5. Scope — Global or Local

`register_reader(session=...)` registers into that user's Local metagraph; without a
session, Global. Local-first is the Decision Records trial.

**Two consequences.** Guards must be scope-aware — a Global-only guard passes silently the
moment registration moves Local, which is exactly the configuration a Local trial chooses.
And `pipeline._view_for` returns Global *or* Local and never both, so a Local trial means
the **whole path** must be Local until `feat/capacity-two-tier-resolution` lands.

---

## 6. What is not built

- **The transport.** The one piece that touches the network. §6 of the manual specifies it.
- **Any decision capacity.** Nothing consumes a reading.
- **The Record renderer.**
- **A store for prompt text.** Versions ride the record; the text has no home. Same store
  as the policy version — Decision Records lane.
- **The document-to-root link.** Decision Records lane (their G7).
- **`basis` is a model self-report** and a headline claim rests on it. Renaming it to
  `basis_reported_by_model` is proposed and deliberately **not** done: the planning lane
  made `basis` the field claim 2 is sold on, so the open question is whether the *claim* is
  right, not the field name.

---

## 7. Files

| Path | What |
|---|---|
| `mindsos_llm/` | New top-level package: `LiveLLM`, `CapturingLLM`, `RecordedLLM`, `RecordingStore`, `request_key`, error types. |
| `mindsos_capacity/builtins/origin_v0.py` | The origin shape, taxonomy, contract validation, scope-aware guards. |
| `mindsos_capacity/builtins/comprehension_v0.py` | Reader factory, quote location, coercion, refusal set. |
| `mindsos_capacity/context.py` | `LLMHandle` Protocol + the 12th `CapacityContext` field. |
| `mindsos_capacity/family_rules.py` | `comprehension` → `OPTIONAL_RETURN`; leaves the deferred set. |
| `mindsos_intelligence/dispatch.py` | Category-based injection + `LLMUnavailableError`. |
| `tests/llm_seam/` | Six modules. |

New-top-level-package checklist applied for `mindsos_llm`: `pyproject.toml` include,
`mindsos_cli/manifest.toml` packages, both Dockerfile stages, `__version__`.

**The gate has never run on any of this.** Everything reported as passing was hand-run on
the development machine without pytest.
