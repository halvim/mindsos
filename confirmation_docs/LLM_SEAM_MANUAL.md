# How MindsOS uses a language model

**A manual for the `mindsos_llm` package and the `comprehension` reader family.**

Branch `feat/decision-records` · **rev 3**, 2026-08-08 · written against `origin/main` `5c6c5db`

Rev 3 folds in everything agreed with the Decision Records planning lane: the origin
record moved out of this family into `origin_v0`; `_reading` became `_origin`; readings
are coerced to their declared shape; a transport failure became a refusal rather than an
exception; and registration can be Local instead of Global.

Every section is marked **[BUILT]**, **[PROPOSED]** or **[NOT BUILT]**. Nothing in
here is merged. Limitations are numbered — **L-n** for MindsOS itself, **S-n** for
this seam — and every one of them reappears in §11 with a proposed fix.

---

## 1. Who this is for and what it answers

Four questions, in order:

1. What does the language model do, and what does MindsOS do? Where exactly is
   the line?
2. What actually happens, step by step, when a document is read?
3. Why does each piece of the machinery exist? What breaks without it?
4. What did building this reveal about MindsOS that needs fixing?

If you only read two things, read §3 and §11.

---

## 2. The one rule everything follows

> **The model never enters MindsOS. Its output enters — as a typed value that
> arrives with a quote from the source document, where MindsOS itself has
> checked that the quote really is in the document.**

Everything in this manual is a consequence of that sentence. If you disagree
with it, most of the design should change.

---

## 3. The division of labour

This is the section people get wrong, so it is stated twice — once as a table,
once as prose.

| | The language model | MindsOS |
|---|---|---|
| Reads messy human writing | ✅ | ❌ |
| Decides what a sentence means | ✅ | ❌ |
| Proposes a value and a supporting quote | ✅ | ❌ |
| Checks the quote is really in the document | ❌ | ✅ |
| Decides whether the reading is acceptable | ❌ | ✅ |
| Decides whether to refuse | ❌ | ✅ |
| Records what happened | ❌ | ✅ |
| Applies a rule, compares against a limit, reaches an outcome | ❌ | ✅ |

In prose: **the model proposes, MindsOS disposes.** The model is asked one
narrow question about one document and answers with a value plus the words it
based that value on. MindsOS then does something the model cannot do for
itself — it goes back to the original document and looks for those words. If
they are not there, the reading is thrown away. The model never learns whether
it passed, never sees the outcome, and never touches a decision.

This is why the marketing sentence *"the model reads, it does not decide"* is
not a promise about prompt discipline. It is enforced in two places:

- A reading capacity is **refused at registration** if it would produce a value
  that any `decision`, `comparator` or `predicate` capacity produces. **[BUILT]**
- The model client is handed **only** to capacities in the `comprehension`
  category. Anything else is handed nothing and cannot reach a model. **[BUILT]**

---

## 4. The four parts, and why they are separate

**The transport** is a function the deployment writes. It is the only code that
speaks a provider's protocol. It lives outside this repository. §6 is entirely
about it.

**`mindsos_llm`** is a new top-level package. It is *plumbing*: how to reach a
model through a transport, how to record what came back, how to replay it later,
how to stop a run spending without limit. It contains no judgement about
anything.

**`comprehension.*` capacities** are the *thinking*: what to ask, whether the
answer is acceptable, what to do when it isn't.

**`origin_v0`** holds the shape of the record that says where a value came
from. It is deliberately **not** part of the reading family: a policy lookup
produces origin too — *"from the claims policy, version 4, in force since 12
March"* — and never touches a model. If the shape lived with the readers, the
one origin statement the product turns on would be the one that could not use
it. §7A covers it.

They are separate because MindsOS already draws this line everywhere else —
capacities are cognition and get dispatched; storage, identity and persistence
are substrate and do not. A model call is I/O. Deciding whether a reading is
trustworthy is cognition. Putting both in one place would make the second
invisible to the machinery that records reasoning.

Two consequences worth knowing:

- `mindsos_llm` imports no other `mindsos_*` package.
- A capacity body **cannot import `mindsos_llm`**. It receives a capability from
  the dispatcher instead. This is not style — it is what makes the model call
  visible to dispatch, replaceable in tests, and impossible to perform from a
  capacity that has not been placed in the right category.

---

## 5. The worked example

The submission email, in full:

```
Order 4471. I purchased the item on 3 March 2026 and only got round to
claiming now. I was in hospital for three weeks after the operation.
```

Two values have to come out of it: the purchase date, and whether the customer
asserts a hospital stay.

### 5.1 Setup — once, when the Skill installs

**Step 1. The deployment builds the model client. [BUILT]**

```python
llm = LiveLLM(
    transport,                        # §6 — a function the deployment writes
    model_id="model-x",
    model_version="2026-05-01",
    temperature=0.0,
    timeout_s=30.0,
    max_calls=200,
)
```

**Step 2. The dispatcher holds the client. [BUILT]**

```python
dispatcher = L4Dispatcher(capacity_layer, llm=llm)
```

No capacity has it yet. The dispatcher hands it out per call, per step 8.

**Step 3. The Skill registers one value type per value. [BUILT]**

`claims.submission_email`, `claims.purchase_date`,
`claims.hospital_stay_asserted`.

Why separate types: MindsOS holds **one value per type per run**. Two dates
sharing a single `date` type means the second silently replaces the first, and
everything downstream wires to the wrong one.

> **Limitation L-1 — one value per DataState type per run.**
> *Kind: expressiveness, and authoring cost.*
> The executor's blackboard is a dictionary keyed by DataState IRI
> (`pipeline_execution.py`), and the grounding writer's index is keyed the same
> way and overwrites (`capacity_mm_writer.py`). A type can therefore hold
> exactly one value for the whole run.
> **What it costs you here:** every distinct field in a claim needs its own
> registered type — purchase date and claim date cannot both be "a date". A
> ten-field claim form is ten registered types plus ten more for their reading
> records, authored per customer.
> **What it costs you elsewhere:** this is the same limit that forced a type
> split in the NILM work, where one signal type could not hold two channels.
> **Proposed fix in §11.**

> **Limitation L-8 — DataState names allow one dot only.**
> *Kind: authoring cost, minor.*
> `register_datastate` rejects `claims.purchase_date.reading` because a name is
> `<realm>.<name>` and a second dot is refused. This is why the origin record
> type is `claims.purchase_date_origin` with an underscore — a naming
> convention forced by a validator rather than chosen.

**Step 4. The Skill registers one reader per value. [BUILT]**

```python
register_reader(
    capacity_layer,
    name                 = "read_purchase_date",
    source_datastate_iri = claims.submission_email,
    value_datastate_iri  = claims.purchase_date,
    value_description    = "The date the item was purchased.",
    prompt_iri           = "prompt:claims.purchase_date",
    prompt_version       = 4,
    field_name           = "purchase_date",
    question             = "the date the item was purchased",
    description          = "Read the purchase date from the submission.",
    origin_party         = ASSERTED_BY_PARTY,
    origin_party_phrase  = "the customer",              # who asserted it
    source_identity_phrase = "their submission email",  # what was consulted
    expected_basis       = STATED,
    value_shape          = ShapeDescriptor.scalar("int", …),
    session              = dr_session,   # omit this to register Global
)
```

One call does five things:

1. Creates the value type `claims.purchase_date`.
2. Creates its paired origin type `claims.purchase_date_origin`.
3. Registers the capacity into the `comprehension` category.
4. Refuses if any decision-shaped capacity already produces that value —
   checked across **Global and the caller's Local**.
5. Refuses if either printed phrase is empty or looks like an identifier.

**`session=` decides Global or Local.** With a session, everything lands in
that user's Local metagraph and nothing touches the Global catalog. That is
the Decision Records trial: prove the shape, then promote deliberately.

> **Limitation L-14 — a Local trial is all-or-nothing.**
> *Kind: expressiveness.*
> `pipeline._view_for` returns the Global view **or** the Local view, never
> both. A Local-registered reader therefore cannot compose with a Globally-
> registered decision capacity — the finder cannot see both at once. Until the
> two-tier union view lands (`feat/capacity-two-tier-resolution`: gate-green
> when written, never merged, now 85 commits behind main), a Local trial means
> the **whole path** must be Local.

Why a factory rather than a fixed list of readers: a single "read the whole
document" capacity would produce one opaque blob. The route-finder would have
nothing to compose through, and the Decision Record would have nothing specific
to cite. One reader per value keeps both.

> **Limitation S-1 — one model call per extracted value.**
> *Kind: runtime cost — money and latency.*
> Each reader makes its own call. Ten values out of one email is ten calls, each
> sending the whole email again. On a batch of 500 historical claims that is
> 5,000 calls where 500 would do.
> **Proposed fix in §11 — and it is smaller than it looks.**

**Step 5. A prompt is named but not stored. [BUILT, incompletely]**

> **Limitation S-6 — prompts are versioned and homeless.**
> *Kind: traceability.*
> `prompt_iri` and `prompt_version` ride every reading record, on the same
> argument that puts a policy version there: the prompt materially determines
> the reading, so a Record that cannot name it cannot account for it. But
> nothing stores the prompt **text**, and nothing stops the text changing while
> the version number does not. A Record that names version 4 and cannot produce
> version 4 is a Record with a hole in it.

### 5.2 Run — one claim

**Step 6. The email arrives as `claims.submission_email`. [BUILT]**

> **Limitation L-5 — a start input has no path back to anything.**
> *Kind: traceability, and it fails silently.*
> `CapacityMMWriter.seed()` mints a node with **no incoming edge**. Only
> `root()` mints the run's grounding root, and nothing links a seed to it. So a
> value handed in as a pipeline start has no path back to the source document,
> and the product claim *"traceable to the document it came from"* is false for
> it — permanently, with no warning.
> **Owned by the Decision Records lane**, who are adding a guard that makes the
> renderer raise rather than quietly attribute an untraceable value.
> The reader side needs nothing: its outputs hang off a capacity that consumes
> the document, so they become traceable the moment the document does.

**Step 7. The route-finder returns a pipeline. [BUILT]**

Asked for the claim outcome, the finder searches the type graph and finds:
readers → elapsed days → threshold check. The readers are in that route because
they are the only registered producers of types the route needs.

**This is the answer to "how does MindsOS decide to call a language model."**
It doesn't decide. There is no deliberation step weighing whether a model is
appropriate. The model is in the pipeline *structurally* — a reading capacity is
the only way to get from a document to a typed value, and the finder found the
only route. A useful consequence: you can list every value in the system that
can ever come from a model by querying the registry, before running anything.

**Step 8. The dispatcher checks the category and hands over the client. [BUILT]**

The step is `capacity:comprehension:read_purchase_date`. Its category is in
`LLM_CATEGORIES`, so the dispatcher puts the client on `context.llm`. A capacity
in any other category receives `None` and cannot reach a model.

If no client had been bound at boot, the dispatcher **raises here**. It does not
let the reader decline. A missing client is our configuration error, not a fact
about the world, and a Decision Record must never carry a refusal caused by our
own misconfiguration.

> **Limitation L-9 — there is no general way to declare "this capacity uses an
> external resource".**
> *Kind: expressiveness.*
> I used the category, which works and costs nothing. But capability
> granularity is now *category-wide*: every capacity in `comprehension` may
> reach a model, and a capacity elsewhere that legitimately needed one could
> not. The moment a second kind of external resource appears — an OCR service, a
> document store, a rate table over HTTP — this needs a real answer.

**Step 9. The reader asks. [BUILT]**

```python
context.llm.read(
    prompt_iri="prompt:claims.purchase_date",
    prompt_version=4,
    source_text=<the email>,
)
```

This is the only line in MindsOS that reaches a language model.

**Step 10. The client calls the transport and stamps the answer. [BUILT]**

Onto whatever came back, the client adds: model id, model version, prompt id,
prompt version, temperature, a request key, and `recorded: false`.

These are stamped **by the client**, never read out of the response. A saved
file therefore cannot claim to be a live reading, and cannot claim to have come
from a model other than the one configured.

**Step 11. The model's answer. [BUILT]**

```json
{"name": "purchase_date",
 "value": "2026-03-03",
 "quote": "purchased the item on 3 March 2026",
 "basis": "stated"}
```

**Step 12. MindsOS checks the quote against the email. [BUILT]**

It searches the original email text for those words — exact match first, then
ignoring line breaks, always case-sensitive. Found at characters 14–48.

**This is the single most important step in the whole design.** It is the only
point where anything the model said is tested against reality. Without it, every
downstream guarantee is just a hope about how well the prompt was written. With
it, a fabricated value becomes a refusal automatically, because a fabrication
has no words in the document to point at.

**Step 13. The reader returns two things. [BUILT]**

The value:

```
claims.purchase_date = "2026-03-03"
```

And the origin record:

```json
{
 "origin_producer_kind": "document_reading",
 "supplied_fields": ["origin_party", "origin_party_phrase",
                     "expected_basis", "quote_verified"],
 "origin_method": "read_by_model",
 "origin_method_phrase": "read by a language model",
 "source_identity_phrase": "their submission email",
 "source_datastate": "datastate:claims.submission_email",
 "question": "the date the item was purchased",
 "admitted": true,
 "refusal_reason": null,
 "refusal_detail": null,
 "environment_fault": false,

 "origin_party": "asserted_by_party",
 "origin_party_phrase": "the customer",
 "basis": "stated",
 "expected_basis": "stated",
 "quote": "purchased the item on 3 March 2026",
 "claimed_quote": "purchased the item on 3 March 2026",
 "quote_verified": true,
 "quote_offsets": [14, 48],
 "model_id": "model-x",
 "model_version": "2026-05-01",
 "prompt_iri": "prompt:claims.purchase_date",
 "prompt_version": 4,
 "temperature": 0.0,
 "request_key": "sha256:9f1c…",
 "recorded": false
}
```

The first eleven fields are the **spine** — every producer of origin writes
them, whatever it is. The rest are **producer-declared**: `supplied_fields`
names the ones a document reading *always* populates, so the renderer can
tell a normal absence from a defect. §7A explains why.

Every field is explained in §7 and §7A.

> **S-5 — closed.** `origin_method` was `inferred_by_model`, which sat beside
> `basis: stated` and read as a contradiction. It is now `read_by_model`.

**Step 14. The grounding writer records it. [BUILT]**

One capacity node, two value nodes, one CONSUMES edge from the email, two
PRODUCES edges. Everything above is now *in the graph*, not beside it.

> **Limitation L-2 — nothing is recorded unless the step succeeded.**
> *Kind: expressiveness, and it undermines the product claim.*
> `execute_pipeline` calls `writer.record` only after a successful step. A
> capacity that fails, or declines, or asks a question, returns early and leaves
> **no node at all**. I worked around this for readings by making refusal an
> ordinary successful return carrying an empty value — but a genuine capacity
> *failure* still leaves the graph silent, and a Decision Record would have to
> explain it from outside the run.

> **Limitation L-7 — there is no adjacency index on a graph.**
> *Kind: runtime cost.*
> `Graph.edges` is a flat dictionary keyed by edge id. There is no per-node
> incoming/outgoing index. So "which capacity produced this value" is a full
> scan of every edge in the graph, and a renderer doing that once per value does
> N full scans per Record. Nobody has measured it; a batch of 500 decisions will
> be the first thing that does.

**Step 15. Steps 8–14 repeat for the hospital stay. [BUILT]**

Quote `"I was in hospital for three weeks"`, verified, `basis: stated`,
`origin_party_phrase: "the customer, in their submission email"`.

**Step 16. Decision steps run. [NOT BUILT]**

Nothing consumes these readings yet. No comparison, no threshold, no outcome.

**Step 17. The Record is rendered. [NOT BUILT]**

The renderer walks the graph and prints, using only registered prose:

> **Purchase date: 3 March 2026** — the date the item was purchased, stated by
> the customer in their submission email, read by a language model, quoted:
> *"purchased the item on 3 March 2026"*.

Note what is absent: no IRI, no capacity name, no "DataState", no confidence
score. Everything printed came from a field someone registered deliberately.

### 5.3 The same run, when the model fabricates

**Step 12′. The model returns a quote that is not in the email. [BUILT]**

Say it answers `"admitted to St Mary's on 2 June"` — plausible, and nowhere in
the document. The search in step 12 fails.

**Step 13′. The reader refuses.**

```json
{
 "origin_producer_kind": "document_reading",
 "supplied_fields": ["origin_party", "origin_party_phrase",
                     "expected_basis", "quote_verified"],
 "admitted": false,
 "environment_fault": false,
 "refusal_reason": "quote_not_found_in_source",
 "refusal_detail": "the quote supporting this value does not appear in the
                    document it was said to come from",
 "claimed_quote": "admitted to St Mary's on 2 June",
 "quote": null,
 "quote_verified": false,
 "quote_offsets": null,
 "basis": null,
 "expected_basis": "stated",
 "question": "whether the customer says they were in hospital",
 "origin_party_phrase": "the customer, in their submission email",
 "origin_method_phrase": "read by a language model",
 …
}
```

The value comes back empty. The record keeps the words the model claimed, so the
refusal is inspectable rather than just a null.

What survives a refusal is everything **registered** — `question`,
`expected_basis`, `origin_party_phrase` — because the escalation has to tell a
person *what* could not be read and *where it should have been*. Only the
**observed** facts are absent, because nothing was read to observe.

The pipeline continues. The refusal surfaces later, at the decision step that
finds it cannot evaluate its condition. The Record then reads *"could not decide,
because could not establish X."*

---

### 5.4 The same run, when the value will not fit

**The model answers *"about seven weeks"*, with a quote that verifies.** The
words really are in the document, so the fabrication check passes — but the
value is declared as a whole number of days and *"about seven weeks"* is not
one. Coercion fails and the reading is refused, `value_not_coercible`, with
the verified quote kept beside it so a person can see exactly what was read.

Without this the string would be handed to a threshold step to compare
against `30`, and the answer would be **confidently wrong** — the one failure
mode the product cannot have.

### 5.5 The same run, when the network is down

**The transport raises.** The reading is refused, `model_unreachable`, and the
record carries `environment_fault: true`.

That flag exists because two refusals that look alike are not alike. *"The
document does not say"* is a finding about the customer's case and belongs in
their refusal list. *"Our reading service was down"* is our outage and must
never appear there — a refusal list padded with our own failures stops being
the thing an engagement is sold on.

Two faults deliberately still raise rather than refusing:
`LLMCallBudgetExceeded` (a run-level policy limit of ours) and
`RecordedResponseMiss` (a fault in our recorded set). A batch stopping loudly
beats three hundred Records blaming the customer's documents for our
configuration.

---

## 6. The transport, in detail

The transport is the single most misunderstood piece, and the only one that does
not exist yet. This section is what someone needs in order to write it.

### 6.1 What it is

A plain function, supplied by the deployment at boot, that speaks one provider's
protocol. `LiveLLM` calls it and does not care how it works.

```python
def transport(
    *,
    prompt_iri: str,          # which prompt to use — an identifier, not text
    prompt_version: int,      # which version of it
    source_text: str,         # the document to read
    extraction_schema: Mapping | None,   # the shape of the answer wanted
    timeout_s: float,         # how long the client is prepared to wait
) -> Mapping | str: ...
```

### 6.2 What it must do

1. **Resolve the prompt.** Turn `(prompt_iri, prompt_version)` into the actual
   instruction text. Today there is nowhere to look this up — see S-6 — so the
   first transport will carry the text itself, which is a stopgap and should be
   named as one.
2. **Build the provider request.** Combine the prompt, the document and the
   requested answer shape into whatever that provider expects.
3. **Send it, and wait no longer than `timeout_s`.**
4. **Return the model's answer**, either already decoded into a mapping or as
   the raw text the model produced.
5. **Raise on anything going wrong.** Network failure, authentication failure,
   rate limiting, a timeout. Any exception is caught by `LiveLLM` and turned
   into `LLMCallFailed`.

### 6.3 What it must not do

- **Not decide anything.** It does not judge whether the answer is good, does
  not fill in a missing field, does not pick between two readings.
- **Not retry silently.** A retried call is a different call and the run should
  know. If retry policy is wanted it belongs above this layer, where it is
  visible.
- **Not substitute a default.** Returning an empty or invented answer when the
  call fails would put a fabricated reading into an audit record.
- **Not log the document anywhere MindsOS cannot see.** The document is the
  customer's; where it goes is a contractual question, not a coding one.

### 6.4 Why it exists at all — four reasons

**No vendor inside MindsOS.** If a provider SDK were imported by core, changing
provider would be a change to core, and every customer would inherit the choice.
With a transport, changing provider is one line at boot.

**Credentials never enter MindsOS.** API keys live in the transport's closure.
No capacity, no context, no graph node ever holds one, so no credential can leak
into a Decision Record or a persisted Episode.

**The seam is testable.** Every test in `tests/llm_seam/` substitutes a small
function for the transport. Nothing is mocked, nothing is patched — the seam is
a parameter.

**The build gate has no network and no API key.** Without an external transport
there is no way to test the reading path at all.

### 6.5 What it returns, and who parses it

> **Limitation S-2 — the transport currently owns parsing, and nobody owns the
> transport.**
> *Kind: correctness risk.*
> `LiveLLM` today requires a `Mapping`. That means somebody's unwritten,
> untested function decides what to do when a model returns malformed JSON, or
> prose wrapped around JSON, or a truncated answer. Decoding is substrate work
> and it should not sit in unowned code — and a decode failure should become a
> refusal, not an exception from outside the system.
> **Proposed fix in §11.**

### 6.6 What is not the transport's job

Everything the client already does around it, and it is worth being explicit so
a transport author does not duplicate it:

- **Identity stamping** — model, prompt, version, temperature. `LiveLLM` does it,
  and does it *after* the transport returns, so a transport cannot misreport
  which model answered.
- **The request key** — computed by the package from the six things that
  determine a reading.
- **The call ceiling** — `max_calls` is enforced before the transport is called.
- **Recording and replay** — `CapturingLLM` and `RecordedLLM` wrap the transport
  without it knowing.

### 6.7 The minimum honest transport

For the first demonstration, a transport that does the following is enough:
holds one prompt's text per `(prompt_iri, prompt_version)`; sends prompt +
document to one provider asking for structured output; returns what came back;
raises on anything else. Roughly fifty lines. What makes it honest rather than a
placeholder is that it never invents an answer and never retries quietly.

> **Limitation S-3 — no transport exists and no test covers one.**
> *Kind: unbuilt.*
> The one piece that touches the network is unwritten and ungated. Everything in
> §6 is a specification, not a description.

> **Limitation S-7 — there is no policy for a failed call inside a batch.**
> *Kind: unbuilt.*
> `LLMCallFailed` propagates. On a batch of 500 historical decisions, one
> network blip ends the run. What a failed case means — skip it, mark it
> unreadable, retry once at the batch level — is a decision nobody has made.

---

## 7. `mindsos_llm` and the reader, feature by feature

### 7.1 `LLMHandle` — the wire **[BUILT]**

A capacity body never imports the package. It receives a capability on
`context.llm`, put there by the dispatcher.

**Why.** A body that imported a client directly would make the model call
invisible to the dispatcher, impossible to substitute in a test, and reachable
from any capacity in the system. The capability form also means a body never
holds credentials or a session.

**Why by category.** Capacities already live in per-category graphs, so
membership of `comprehension` *is* the declaration that this capacity may
consult a model. No new field on every capacity, and "what in here can call a
model?" is one registry query. Cost: L-9.

### 7.2 `LiveLLM` **[BUILT, except the transport]**

**`temperature` defaults to 0.** It is one of the things that determines a
reading, so it belongs in the request key and on the record. Zero by default
because a Decision Record naming a temperature of 0.9 invites a question nobody
wants to answer.

**`max_calls` is mandatory.** A batch over a few hundred decisions, at several
readers per case, is thousands of calls. Without a ceiling the first mistake is
discovered on an invoice. Exceeding it raises `LLMCallBudgetExceeded`.

**A failed call raises and does not fall back.** No retry, no substituting a
saved answer. A silent fallback would let a run present a stale reading as a
fresh one.

### 7.3 `RecordedLLM` — replay **[BUILT]**

Answers from a saved file of previous model responses, looked up by request key.

**The one reason that survives scrutiny:** the test suite has no network.
Without saved answers, nothing about reading can be tested in the build gate.

**It is not for the buyer demonstration.** A demo running from saved answers is
a scripted demo and deserves to be called one. Live is the default for anything
a customer watches.

**A miss raises.** If a miss quietly went live, or quietly returned nothing, a
Record could present an unrecorded reading as a recorded one.

### 7.4 `CapturingLLM` **[BUILT]**

Wraps any client and saves every answer, keyed exactly as `RecordedLLM` will
later look it up. Someone has to produce the saved file, and the only
alternative is writing the model's answers by hand — precisely the failure this
design exists to prevent.

### 7.5 `request_key` **[BUILT]**

A hash over six things: prompt IRI, prompt version, model id, model version,
temperature, and the exact source text. Each one changes the reading, so each
one changes the key. The practical consequence is deliberate: re-word a prompt
and the saved set goes stale, and every lookup misses loudly.

### 7.6 The `recorded` stamp **[BUILT]**

Every reading carries `recorded: true|false` into the graph. Per reading, not
per deployment, because a global setting is something you have to remember and
mixed runs would otherwise be indistinguishable.

### 7.7 One reader per value **[BUILT]**

A general extractor returns one opaque object: the finder cannot compose through
it and the Record cannot cite any specific part of it. Cost: S-1.

### 7.8 The mandatory quote **[BUILT]**

The only mechanism here that tests a model claim against something outside the
model. Exact match first, then whitespace-insensitive so line wrapping does not
matter, always case-sensitive because changing a document's casing is not
quoting it. Offsets always point into the untouched document.

### 7.9 Two outputs, not one **[BUILT]**

The grounding writer records a capacity's **declared outputs and nothing else**.
Provenance returned any other way — a side field, a log line, an attribute on
the value — never becomes a node, and can therefore never legally appear in a
Decision Record.

### 7.10 A separate origin type per reader **[BUILT]**

`claims.purchase_date_origin`, not one shared `origin` type — forced by L-1. A
shared type would have the second reader in a run displace the first's
provenance and the graph would wire the wrong producer.

### 7.11 Refusal by value + record, not by `NeedsInput` **[BUILT]**

> **Limitation L-3 — `NeedsInput` erases the node that explains the gap.**
> *Kind: expressiveness.*
> MindsOS has a `NeedsInput` verdict for "I can proceed if you answer this". It
> looks like the right tool and it is not: raising it short-circuits output
> validation, so **no node reaches the graph** saying why the value is missing.
> The Record would have to state the reason from outside the run — the one thing
> the product claim forbids. I avoided it entirely.

> **Limitation L-4 — `NeedsInput.missing` is an identifier, not a phrase.**
> *Kind: rendering.*
> It carries a DataState IRI. A Decision Record forbids every IRI and every
> MindsOS term, so anything using `NeedsInput` needs a registered phrase behind
> it — the same tokens-branch / phrases-print split this seam uses.

### 7.12 The closed set of refusal reasons **[BUILT]**

`model_declined`, `field_absent`, `quote_not_found_in_source`,
`malformed_response`. Closed because consumers branch on them; a free-text
reason means something downstream parses English.

### 7.13 Structural uncertainty, no confidence score **[BUILT]**

A model-reported confidence is another output of the same process being
questioned. Putting it in an audit record launders a guess into evidence. What
is recorded instead is what MindsOS established.

### 7.14 `expected_basis` versus `basis` **[BUILT]**

- `expected_basis` — **registered**. Is this field supposed to be *stated* in
  the document or *inferred* from it? Known before any model runs, present on
  every record including refusals.
- `basis` — **observed**. What the model reported. Empty when nothing was read.

> **Limitation S-4 — `basis` is a model self-report and a headline claim rests
> on it.**
> *Kind: claim risk.*
> The product claim is *"what was read from a source and what was inferred from
> context remain distinguishable."* That distinction is carried by `basis`, and
> `basis` is something the model said with nothing checking it.
> `quote_verified` is established by MindsOS; `basis` is not.

### 7.15 Tokens branch, phrases print **[BUILT]**

`origin_party` is a closed token; `origin_party_phrase` is registered prose.
A Record is read by claims managers and lawyers and forbids every IRI and every
MindsOS term, but code still needs something stable to branch on and must not
branch by parsing English. Registration rejects a phrase containing `:`.

> **Limitation L-6 — registration metadata does not persist to the graph.**
> *Kind: traceability, and it is contested.*
> `Capacity.to_properties()` persists only name, category, node kind, adapter
> flag, cost, latency, description and the placeholder flag. Custom registration
> fields — origin, the registered phrases — are not on the node. So this seam
> copies them onto each reading record instead.
> The Decision Records lane argues this is **correct**: a Record must state what
> was true when the decision ran, not what is true when someone opens it, and
> the L3 catalog is separately persisted and mutable, so reading it at render
> time would silently show the wrong origin for an archived Episode. Recorded
> here as an open architectural question rather than a defect.

---

---

## 7A. `origin_v0` — the record shape, and why it is not ours

**A policy lookup produces origin too.** *"From the claims policy, version 4,
in force since 12 March"* is the sentence the whole product turns on, it is
produced by a decision-family capacity, and it never touches a language
model. If the record shape lived in the reading family, that sentence would
be the one statement that could not use it — so the shape lives in
`origin_v0` and a reader is one **producer** of it.

Three producer kinds are named today: `document_reading` (this family),
`structured_ingest` (a value arriving already typed from an export), and
`policy_lookup`. The second is what makes the *"same answers, different
origins"* comparison possible — the same cases run once from a structured
export and once from prose, where the values match and only the origins
differ.

### The spine

Eleven fields every producer writes, whatever it is: `origin_producer_kind`,
`supplied_fields`, `origin_method`, `origin_method_phrase`,
`source_identity_phrase`, `source_datastate`, `question`, `admitted`,
`refusal_reason`, `refusal_detail`, `environment_fault`.

### Never infer from absence

A missing `quote` on a lookup record is normal. A missing `quote` on a
document reading means something went wrong. Absence cannot mean the same
thing across producers, so every record carries `supplied_fields` — what its
producer *always* populates. Inside that list, missing is a defect. Outside
it, missing is normal, and the renderer reads it with `.get()` rather than
inferring from a key.

### Two phrases, not one

`origin_party_phrase` names **who asserted it** ("the customer").
`source_identity_phrase` names **what was consulted** ("their submission
email", "the claims policy").

They were a single welded string until the money sentence was assembled from
the field set and would not come out. A policy is not a party asserting
anything; it is an authority being consulted. Every producer supplies a
source; only some supply a party.

### The union is v0 and not frozen

Twenty-nine fields today. It is closed **by agreement** — `build_origin_record`
raises if a producer invents a field, because two producers is where invention
starts and the renderer would end up reading keys nobody declared. But it is
not frozen: neither consumer exists yet, and a field set frozen before its
consumers are built is a guess with a process attached.

### `environment_fault` is derived, never passed

A producer cannot label its own outage as a finding about the customer's
case. The flag is computed from the refusal reason inside
`build_origin_record`.

## 8. What ends up in the graph

For each reading, one capacity node and two value nodes:

```
claims.submission_email  ──CONSUMES──▶  read_purchase_date
                                              │
                                    ┌─────────┴─────────┐
                              PRODUCES              PRODUCES
                                    ▼                   ▼
                        claims.purchase_date   claims.purchase_date_origin
                             "2026-03-03"          {the record above}
```

The renderer starts at a value, follows PRODUCES backwards to the capacity that
made it, then forwards to that capacity's reading record, and writes the
sentence from registered prose. Nothing it prints comes from anywhere but this
graph. Each of those hops is a full edge scan today — L-7.

---

## 9. What is built, what is not

**Built and hand-verified**

- `mindsos_llm`: `LiveLLM`, `CapturingLLM`, `RecordedLLM`, `RecordingStore`,
  `request_key`, and the error types.
- `LLMHandle` and the `llm` field on `CapacityContext`.
- Category-based hand-off, and the error when no client is bound.
- The reader factory, quote verification, **coercion to the declared shape**,
  the closed refusal set (seven reasons), the origin fields,
  `expected_basis` / `basis`, and the two prose fields.
- **`origin_v0`** — the spine, the union, `build_origin_record` with contract
  validation, and the scope-aware registry walks.
- The registration guard that stops a reader producing a decision's output,
  **checked across Global and Local**.
- **Local or Global registration** via `register_reader(session=…)`.
- **`opaque_into_decision`** — the registry walk for an opaque value a
  decision capacity consumes, order-independent.
- **Six** test modules under `tests/llm_seam/`, 46 cases.

**Not built**

- The transport (S-3). The one piece that touches the network.
- Any decision capacity. Nothing consumes a reading.
- The Record renderer.
- A store for prompt text (S-6).
- The document-to-root link (L-5, owned elsewhere).
- The `register_capacity` half of the opaque-into-decision rule — core
  surface, filed as a separate CR rather than added from this branch.

**Not run under the real test suite.** Everything above was verified by hand
against the code on the development machine. The build gate has not run.

---

## 10. Two more things a reader should know

**Live readings are not reproducible (S-8).** The same document may read
differently on two runs. This does not break a Decision Record — a Record states
what happened on the run that produced it — but the answer to *"why did it say
something different?"* has to exist before the first demonstration. The honest
framing is that MindsOS offers **verifiability**, not reproducibility: every
reading can be checked against the document without re-running anything.

**Nothing consumes a reading yet.** No decision capacity exists. This is the
largest gap in the whole picture and it is not this package's to close.

---

## 11. Improvements — the list

**Status of this list.** Every entry is a **proposal**, not a decision. Nothing
here is agreed, and a go-to-market branch owns nothing architectural. Each entry
that survives review should be filed as a real change request outside this
manual; this list is a starting point, not the record.

### 11.1 MindsOS limitations found by designing Decision Records

| ID | Limitation | Kind | Proposed change | Owner |
|---|---|---|---|---|
| **L-1** | One value per DataState type per run | expressiveness + authoring cost | Give the executor's blackboard and the grounding index a compound key — the DataState IRI plus an occurrence discriminator the capacity declares. A capacity that consumes "two dates" then declares two operands of one type instead of forcing two types. The operand-arity machinery (ADR-0198) already models same-type operands on the input side; this is the same idea on the value side. | core |
| **L-2** | Nothing is recorded unless the step succeeded | expressiveness | Have `execute_pipeline` write a terminal node on **every** non-success return — failure, decline, cancellation — before returning. One node type, carrying the capacity, the closed reason and the detail. Without it, no refusal can ever be rendered from the graph. | core (Decision Records lane calls this Phase 0) |
| **L-3** | `NeedsInput` short-circuits output validation, so it leaves no node | expressiveness | Let a body return `NeedsInput` **alongside** its declared outputs rather than instead of them, so the partial work and the question both reach the graph. | core |
| **L-4** | `NeedsInput.missing` is a DataState IRI | rendering | Add a registered human phrase beside the identifier — tokens branch, phrases print. Same split this seam uses for `origin_party`. | core |
| **L-5** | `seed()` mints start values with no incoming edge | traceability, silent | Link every seeded value to the run's grounding root, or refuse to seed a value that is not reachable from it. A guard that fails a Record naming an unreachable value is the minimum. | Decision Records lane |
| **L-6** | Registration metadata does not persist to the capacity node | traceability, **contested** | Two positions on record: persist declared metadata onto the node, or accept that denormalising onto each record is correct for an archive. Do not resolve this in a manual. | core, with the Decision Records lane |
| **L-7** | No adjacency index on a graph; every provenance hop is a full edge scan | runtime cost | Maintain per-node incoming and outgoing edge indexes on `Graph`, updated in `add_edge` / `remove_edge`. Measure first: one Record over a twenty-reading run is the cheap experiment. | core |
| **L-8** | DataState names allow one dot only | authoring cost, minor | Either allow a qualified third segment, or document the constraint where people meet it. Today it silently shapes naming conventions. | core |
| **L-9** | No general way to declare that a capacity uses an external resource | expressiveness | Leave the category rule alone until a second external resource exists. Then a declared-capability mechanism, resolved at dispatch the way `reads_mm` is. Building it now would be speculative. | core, deferred |
| **L-10** | All 13 L4 catalog capacities are placeholders, so the full lifecycle yields one milestone and one pipeline | expressiveness | Out of scope here. Recorded because it bounds what any demonstration can honestly claim about planning. | core, existing CR |
| **L-11** | Stored parameter values have no version history, and the only store is the *learned*-parameters store where Local shadows Global | correctness | An append-only versioned store with an in-force date, read through a lookup capacity so the version enters the derivation. Found by the Decision Records lane; also the answer to S-6. | Decision Records lane |
| **L-12** | A refusal at find time has no grounding graph at all | expressiveness | A Record shape rendered from the finder's verdict, since nothing executed. Found by the Decision Records lane. | Decision Records lane |
| **L-13** | The capacity index stores `(Node, Graph, declaration)` tuples | trap | Anything iterating the index and expecting declarations silently sees nothing — it cost me a guard that appeared to work. A typed accessor would remove the class. | core, minor |

### 11.2 Limitations of this seam

| ID | Limitation | Kind | Proposed change |
|---|---|---|---|
| **S-1** | One model call per extracted value | runtime cost | *(still open)*  **Two changes, both small.** Let readers over the same document share one prompt — they already select their own field out of a list of fields, so nothing structural changes. Then add a response cache inside the client, keyed by the request key it already computes. Identical prompt + identical document = identical key = one call, and every other reader is a cache hit. Ten readers become one call. Per-value prompts stay available where accuracy matters more than cost. |
| **S-2** | The transport owns parsing | correctness risk | *(still open)*  Accept **either** raw text or a mapping from the transport. If text, decode inside `mindsos_llm`; a decode failure becomes the `malformed_response` refusal that already exists rather than an exception from unowned code. Accepting a mapping keeps provider-native structured output usable. **Do this before anyone writes a transport**, or the responsibility gets settled by accident. |
| **S-3** | No transport exists and none is tested | unbuilt | Write the fifty-line minimum in §6.7 and a contract test that runs against a fake provider. |
| **S-4** | `basis` is a model self-report carrying a headline claim | claim risk | Rename the observed field to `basis_reported_by_model` so a Record can never present it as established, and lean on the registered `expected_basis` as the check. Deriving `basis` mechanically does not work: `2026-03-03` does not appear in *"3 March 2026"*, so a genuinely stated date would be misclassified. This may mean the claim needs rewording rather than the code needing a field. |
| ~~**S-5**~~ | ~~`origin_method` misnamed~~ | — | **CLOSED** — now `read_by_model`. |
| **S-6** | Prompts are versioned but the text has nowhere to live | traceability | Use the same versioned store as L-11. Store the **text**, not just the number, or a Record names a version nobody can produce. |
| **S-7** | No policy for a failed live call inside a batch | partly closed | Decide at the batch layer, where it is visible: skip and mark the case unreadable, or one retry with a fresh request key. Never inside `LiveLLM`. |
| **S-8** | Live readings are not reproducible | claim risk | Do not fix — state it. Offer verifiability instead of reproducibility, and make sure the sentence exists before the first demonstration. |

### 11.2b Closed since rev 2

| ID | Was | How it closed |
|---|---|---|
| **L-2** *(reading half)* | Nothing recorded unless the step succeeded | A reading refusal is now an ordinary successful return carrying an empty value plus a filled-in origin record, so it reaches the graph. A genuine capacity *failure* still leaves nothing — the general fix is the Decision Records lane's Phase 0. |
| **S-4** *(bounded)* | `basis` is a model self-report | Not renamed — the planning lane made `basis` the field claim 2 is sold on, so the open question is whether the **claim** is right, not the field name. `expected_basis` is registered and bounds the damage. |
| **S-5** | `origin_method` misnamed | Renamed to `read_by_model`. |
| **new** | A transport failure had no refusal reason at all | `model_unreachable` + `environment_fault`. |
| **new** | The reader returned the model's value unparsed | Coerced to the declared shape; `value_not_coercible` on failure. |
| **new** | Origin was a comprehension concept | Lifted to `origin_v0`; `_reading` → `_origin`. |
| **new** | `origin_party_phrase` was two facts in one string | Split into party and source identity. |
| **new** | The no-decide guard read only Global | Scope-aware across Global and Local. |

### 11.3 If only three things are done

1. **S-2** — settle who parses the model's output **before a transport
   exists**, because after that it is a rewrite rather than a decision. This
   is the only one with a deadline.
2. **S-1** — the call-per-value cost is the difference between a batch that is
   affordable and one that is not, and the fix is a shared prompt plus a cache
   keyed by the request key the package already computes.
3. **L-2** — the reading half is closed, but a genuine capacity failure still
   leaves no node. Until that is fixed, any refusal that is not a reading
   refusal is unrenderable.
