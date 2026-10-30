---
verified_at: unverified
---

# The `mindsos_llm` guide — what it is, why it exists, how to use it

**Start here.** This page is the entry point for anyone (person or chat) who
needs to use or change `mindsos_llm`. It owns no scope and no rulings: scope
and rulings live in [`docs/plans/MINDSOS_LLM_PLAN.md`](../../plans/MINDSOS_LLM_PLAN.md),
what a consumer can do lives in
[`llm-capability-contract.md`](llm-capability-contract.md), and the decision
history lives in [ADR-0210](../../decisions/adr/0210-llm-communication-layering.md).
Terms already defined elsewhere are linked, not redefined.

**Terms.** *Capacity*, *role-graph* and the layers L0–L5 are defined in the
[glossary](../../concepts/glossary.md). Plan items (`I-n`) and rulings (`R-n`)
are defined in the plan's §3 and §2. The rest, as this page uses them:

- **Reader** — a capacity that reads one value out of a document with the
  model's help (`comprehension_v0`).
- **Origin record** — what a reader stores beside each value it reads: which
  model, which mode and credential level, a digest of exactly what was asked,
  the quote it was found at, or why it refused (`mindsos_capacity/builtins/origin_v0.py`).
- **Refusal** — a reader's stored answer that the value could not be read
  (quote not in the document, field absent, answer undecodable…). It is a
  finding about the document, never about our infrastructure.
- **Don't-know** — L4's answer when a request cannot be decided.
- **Episode** — the stored record of one run: its run graphs, with every value
  and origin record (`mindsos_intelligence/episode_reader.py`, `read_episode`).
- **Grounding graph** — the run graph that links each value to the capacity
  that produced it and the inputs it consumed.
- **Record** — a consumer's own output built from an Episode (core does not
  define it).
- **Credential level** — where the provider's key lives: 1 kept on the
  machine and never stored by MindsOS; 2 held by a broker the deployment runs;
  3 a short-lived token (`mindsos_llm/credentials.py`).
- **Recorded set** — a file of captured answers, each stored under its
  `request_key`, identified by the file's hash, replayed with no network.
- **`request_key`** — a hash of everything that determines an answer: the
  prompt words, schema, tool framing, token ceiling, model, temperature and
  the source text (`mindsos_llm/recording.py`).
- **Prompt edition** — one stored, versioned text of a prompt in the L2
  `prompts` role-graph.
- **Substitute** — a capacity that does not use the model, declared as able to
  produce the same value as a named reader (`Capacity(substitute_for=...)`).
- **Walk** — following everything a value was derived from, to list what
  leaned on the model.
- **Gate** — the full test-suite run on the Linux box that a change must pass
  before it merges (RULES §7).
- **Body** — the Python function a capacity runs.

---

## 1. What it is

`mindsos_llm` is **the one way MindsOS talks to a language model.** Nothing
else in core opens a connection to a model provider.

It is a **stand-in** (plan §1): MindsOS cannot yet read text with its own
intelligence, so it borrows a model for that one job until it can. Everything
in the package serves one end state, a **removable stand-in**:

> every conclusion that leaned on the model can be **identified**, **shown**
> (including exactly what was asked), and **re-run without the model**.

It holds **no cognition.** Deciding what a document says, checking it, and
refusing when the check fails is done by **reader capacities** in L3
(`mindsos_capacity/builtins/comprehension_v0.py`). `mindsos_llm` is the
substrate they run on: the wire to the provider, credentials, decoding,
recording and replay.

## 2. Why each part exists

Each line is the motivation recorded in the commit that built it.

| Part | Why it was built | Commit |
|---|---|---|
| Classified failures (`exceptions`) | A reader told a customer *"your document could not be read"* when the truth was *"we could not reach the model"*. An outage now raises; only an undecodable answer becomes a refusal. | `e440808` |
| Core package, the seam rules, the Anthropic adapter, the adapter registry | Calling a model is substrate for the whole stack, not L3-private. One rulebook (`seam.py`) every adapter obeys: no repair layer, the schema is forced, unasked keys refused, no prompt words inside an adapter. The vendor is chosen at runtime from stored data. | `4f54f3d` |
| Record, replay, export (`recording`, `replay`, `recorded_sets`) | A reading must be reproducible with no network and no key, and a third party must be able to replay an exported set. | `4f54f3d` |
| The contract harness (`contract.verify_transport`) aimed at core's own adapter | Core published a contract and had never checked its own wire against it, on the path a deployment actually takes. | `511b999` |
| The harness never reports a false PASS | It passed a transport that forged identity, and dropped checks it could not run. | `f2310ae`, `44059f7` |
| Per-user configuration in L0, per-session client (`client.build_client`) | Users differ in vendor, credential level and mode. L0 stores a pointer to the credential, never the credential, and pushes a resolver down. | `329ffa7` |
| Credential level 2, the broker | A deployment can keep the key in a broker it runs, so MindsOS never sees it. | `5e97985` |
| Every answer says its mode and credential level | A stored reading must say whether it was live, captured or replayed, and the mode cannot be forged by a caller. | `3fe37db`, `44889a9` |
| A recorded set has a home in L2 | A conclusion must be traceable to the recorded set it came from; the set's identity is its file's hash. | `780ee1b` |
| An answer names what was asked by content (I-17) | *Shown* must be verifiable: prompt words, schema and framing are digested on every answer and in every origin record. | `6f04575`, `2b29252`, `933bc6d` |
| Core names no consumer | Projects built on MindsOS install core by tag; core must not know them. | `f50f1b9` |
| Excision: identify, show, re-run (I-12, I-18) | The end state in §1. | `30e5d12`, `e342af2`, `bf7bd43`, `f1603af` |
| The walk and the proof (I-19–I-21) | A re-run is proven model-free only when everything it descends from re-derives without the model. | `1721b61`, `57460ad` |
| A cut reply is refused; a recording never replaces an answer; a client asks one question once; this guide (I-22–I-25) | Found when the package was first prepared for real work: a reply cut at the token ceiling was taken as complete, a capture could silently replace a recorded answer, readers sharing a prompt paid for one question several times, and no document said what the package is for. | plan §6, 2026-10-29 |

## 3. The intended use

`mindsos_llm` is meant to be used **inside a MindsOS run**, not called from
application code. Calling the client directly works, but it produces no origin
record and no stored conclusion, so nothing in §2 after the first three rows
applies to it.

The road, and the test that exercises each step:

1. **Configure the user's model** — vendor, credential level, mode, credential
   pointer — in L0 (`mindsos_server.llm_custody`).
   *Test:* `test_l0_credential_custody.py`.
2. **Build that user's client** with `mindsos_llm.build_client(...)`. The mode
   picks the class: `live` (`LiveLLM`), `capture` (`CapturingLLM`, live plus
   saving every answer), `replay` (`RecordedLLM`, answers from a recorded set,
   no network, a miss raises). A reply the provider cut at the token ceiling
   raises `AnswerCutAtCeiling`, a stop that is never retried and never a
   refusal (plan I-22); a capture never replaces an answer it already holds
   (`RecordedAnswerConflict`, plan I-23).
   *Test:* `test_per_session_client.py`, `test_answer_provenance.py`,
   `test_a_cut_reply_is_never_an_answer.py`,
   `test_a_recording_never_replaces_an_answer.py`.
3. **Declare one reader per value** with
   `comprehension_v0.build_reader` / `register_reader`. A reader declares
   `consults_llm=True`; the model must return
   `{"fields": [{"name", "value", "quote", "basis"}]}`; the reader locates the
   quote in the source and refuses if it is not there. *"One reader per
   extracted value, not one general extractor"* — a single whole-document
   extractor gives the run nothing to compose through and a Record nothing to
   cite. Several readers may share one prompt and schema, each taking its own
   field from the same answer: a client asks one question once and answers
   repeats from that first answer (plan I-24).
   *Test:* `test_comprehension_reader.py`, `test_two_readers_one_document.py`,
   `test_a_client_asks_one_question_once.py`.
   A reader that is **handed** a model answer instead of calling the model
   declares which input carries it (`model_answer_inputs`, I-18).
   *Test:* `test_answer_fed_reader_is_paired.py`.
4. **Run it through the dispatcher with the client bound:**
   `L4Dispatcher(layer, llm=client)`. Only a capacity that declared
   `consults_llm=True` receives the client; one that declared it with no
   client bound is a deployment error, not a don't-know.
   *Test:* `test_dispatch_llm_injection.py`,
   `test_reading_reaches_the_grounding_graph.py`.
5. **Persist the run as an Episode.** Each reading leaves a value and an origin
   record (`origin_v0`) naming the model, mode, credential level and what was
   asked by content.
   *Test:* `test_the_record_names_what_was_asked.py`,
   `test_a_reading_reaches_its_source_text.py`.
6. **Excise.** `mindsos_intelligence.excision`: `identify` lists what the model
   produced; `show` shows what was asked, verified, and nothing in place of
   what fails; `rerun` re-derives one reading through a declared substitute
   (`Capacity(substitute_for=...)`) with no model bound; `walk` lists every
   value that leaned on the model; `prove` / `proven_walk` say whether a value
   is proven model-free, and why not.
   *Test:* `test_excision_identifies.py`, `test_excision_shows.py`,
   `test_excision_reruns.py`, `test_the_walk_lists_what_leaned_on_the_model.py`,
   `test_a_rerun_is_proven_model_free.py`.

**Prompt words** reach the model through the client's `resolve_prompt`,
which the deployment supplies. For `show` to display them, the same words must
be stored as a prompt edition in the L2 `prompts` role (written by
`capacity:comprehension:write_prompt_edition`); nothing in core wires the
resolver to that role, so keeping the two the same is the deployment's job,
and `show` detects it when they differ (plan R36).

## 4. Modes and credential levels — which to use

| Situation | Mode | Credential level |
|---|---|---|
| A test, a gate, a demo with no network | `replay` | none (answers say `null`) |
| Making a recorded set from real calls | `capture` | 1 or 2 |
| Production reading | `live` | 1 (key kept on the machine, never stored by MindsOS) or 2 (key held by a broker the deployment runs) |

## 5. Adding a vendor

Adapters are added **when a deployment needs one**, by design: an adapter is a
module exposing `VENDOR_ID`, `SUPPORTED_LEVELS` and `build_transport`,
registered explicitly in `mindsos_llm/adapters/__init__.py`, and obeying the
rules in `seam.py`. Core ships the Anthropic adapter. A vendor that needs a
credential level core does not list yet (for example a local model with no
credential, or a short-lived token — plan I-14) brings that level with it.
Prove a new adapter with `contract.verify_transport` (contract rows 7 and 9).

## 6. Limits

- **Removing the model needs a substitute the consumer declares.** `rerun`
  and `prove` re-derive a value only through a capacity declared with
  `substitute_for`; without one, a value is reported *not yet excisable* or
  *not proven*. Substitutes are the consumer's: core cannot know how a given
  value is read without a model.
- **What core cannot check:** that a capacity does only what it declares, and
  the other items in the contract's "What this document does NOT claim".

## 7. Which document answers what

| Question | Document |
|---|---|
| What can I do with it today? | [`llm-capability-contract.md`](llm-capability-contract.md) |
| What is left to build, and in what order? Which rulings bind? | [`MINDSOS_LLM_PLAN.md`](../../plans/MINDSOS_LLM_PLAN.md) §2–§3 |
| Why was each design decision taken? | [ADR-0210](../../decisions/adr/0210-llm-communication-layering.md) and its amendments |
| The level-2 broker wire | [`llm-broker-contract.md`](llm-broker-contract.md) |
| What the package is, in the code | `mindsos_llm/__init__.py` docstring; `seam.py` docstring for adapter rules |
| How a reader reads and refuses | `mindsos_capacity/builtins/comprehension_v0.py` docstring |
| History before core (Aug 2026) | `confirmation_docs/LLM_SEAM_MANUAL.md`, `confirmation_docs/CORE_CR_MINDSOS_LLM.md` — history; where they disagree with ADR-0210, ADR-0210 wins |
