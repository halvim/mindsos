---
verified_at: unverified
---

# `mindsos_llm` — THE PLAN

**Owner: Henrique Alvim. Created 2026-09-13 from owner rulings taken that day.**
**This file is the ONLY plan for this module, and it owns the scope.**

---

## 0. HOW THIS FILE IS USED — read before doing anything here

1. **This file is the plan.** A chat works items from §3, in order. It does not invent
   scope, re-derive the item list, or reinterpret "done".
2. **Disagreeing means AMENDING, never replacing.** A chat that thinks an item is wrong
   writes the amendment into §6, in the same PR as the work, with the owner's decision
   recorded. **Deleting a plan, or working outside it and explaining afterwards, is a
   process violation.** (RULES §5.)
3. **"Done" is mechanical.** Every item's state is exactly one of `TODO`,
   `DONE(<sha>)`, `OUT(<reason>)`. Not a judgement call, and no chat may redefine it.
4. **One owner per fact.** This file owns the item list, the order and the scope.
   `STATE.recent[]` owns what shipped. `STATE.pending_designs` owns the measured detail
   behind an open item. `docs/usage/runtime/llm-capability-contract.md` owns what a
   consumer can DO. Project memory owns pointers and traps. **Nothing else owns scope**
   — pinned by `tests/architecture/test_mindsos_llm_plan_is_the_scope.py`.

---

## 1. SCOPE — OWNER RULING 2026-09-13

`mindsos_llm` is a **STAND-IN**: MindsOS cannot yet read text with its own intelligence,
so it borrows a language model for that one job **until it can**.

**END STATE — "a removable stand-in":**

> Every conclusion that leaned on the borrowed model can be **identified as such**,
> **shown** (including what was asked), and **re-run without the borrowed model** once
> MindsOS reads text itself.

⚠ **THE CAPABILITY CONTRACT TABLE IS NOT THE SCOPE.** All eleven of its rows already
pass. It answers *"what can a consumer DO"*, which is a different question from *"what
is left to build"*. The 2026-09-05 ruling that made it the completion criterion is
**SUPERSEDED** by this file.

---

## 2. THE DESIGN RULINGS — OWNER, 2026-09-13, 2026-09-18 and 2026-09-21; DELEGATED, 2026-09-20

**R1 — L3 writes the L2 record, not L0.** *"it should be L3 as this is part of the
reading text intelligence, not L0 server code."* Settles
`core-llm-recorded-set-l2-pointer-owner`, open and unowned since 2026-09-05. Candidate B
(L0 writes it beside the credential) is **REJECTED**.

**R2 — the work splits across two packages, and `mindsos_llm` is in neither.**
`mindsos_knowledge` (L2) HOLDS prompt text and versions, and the pointer + provenance of
a recorded set; payloads stay a FILE the pointer names. ⚠ **CORRECTED 2026-09-14 by owner
ruling (ADR-0210 am-4): "Local only, never Global" is the RECORDED SET's rule, not the
prompt's.** Prompt editions are **dual-scope** — Global `admin_authored` (the curated
library), Local a per-user trial — because a prompt held Local-only cannot be shown to
anyone but the user whose reading produced it, which defeats §1 for every shared
conclusion. L3 cannot write Global, so the asymmetry needs no new gate.
`mindsos_capacity` (L3) WRITES it. ⚠ `mindsos_llm` may not import either. **A chat that
opens a branch expecting to edit `mindsos_llm` has misread this plan.**

**R3 — the family is `comprehension`, NOT `llm`.** `FAMILY_RULES` already carries a
`comprehension` family and `comprehension_v0` belongs to it. A family named for the
borrowed model names **the crutch, not the work**, and goes wrong the day the stand-in
is removed — which is the scope in §1.

**R4 — L4 decides when a record is needed**, so recording is **a capacity L4 routes
to**, not a declared output fired by every reading. A recorded set spans sessions; a
per-reading output could never cover it.

**R5 — the recorder consumes the READER'S ANSWER, never the vendor.** The answer already
carries `model_id`, `model_version`, `prompt_iri`, `prompt_version`, `temperature`,
`request_key`, `recorded`, `mode`, `credential_level`. ⚠ **The recorder must never build
a client.** `EXPECTED_EXTERNAL_CLIENT_CONSUMERS` holds exactly one entry
(`comprehension_v0`); a second is a declared design event, and it would give a
bookkeeping step the failure modes of a model call — outage, ceiling, undecodable
answer. It also keeps the recorder honest: it records what **was** produced, not what it
can ask for again.

**R6 — loading answers into L5 is ALREADY DONE.** `comprehension_v0` declares
`outputs=(value_datastate_iri, origin_record_iri(...))` and declared outputs reach the
grounding graph. **No item, no work.**

---

**R7 — a capacity DECLARES that it writes.** `outputs == ()` is not a write marker: it
means *"produces no DataState"*, and *"produces no DataState"* and *"mutates L2"* are
orthogonal. Measured — **both** invoke sites branch on `not declaration.outputs` to
decide whether the body gets a `CapacityContext` carrying `writeable`
(`mindsos_capacity/runtime.py:201`, `mindsos_capacity/capacity_layer.py:677`), so a
capacity that writes AND declares an output is unreachable on the direct path and
leaves `InvocationResult.write_outcome` empty. The fix is the pattern the tree already
uses twice — `reads_mm` (ADR-0200 §C3) and `consults_llm` (ADR-0180 §am-3) are
declaration flags that gate a context capability. `writes=True` completes it, and an
AST guard reconciles declaration against body exactly as the `context.llm` census does.
⚠ This does **not** converge the two context types; the legacy dict path is a separate
item. **OWNER 2026-09-18.**

**R8 — a recorded set's identity is its file's `sha256`.** The pointer is therefore
verifiable against the file it names: a re-capture of the same bytes refuses as a
duplicate, and an appended set gets its own pointer. ⚠ **So *shown* means VERIFIABLE for
a recorded set and only RETRIEVABLE for a prompt edition** (whose `append_only` is
declared-not-enforced, `core-llm-prompt-edition-append-only-unenforced`). The asymmetry
is recorded, not smoothed over. **OWNER 2026-09-18.** ⚠ **Its prompt half is SUPERSEDED
by R20 (OWNER 2026-09-21):** *shown* is verifiable for a prompt too, by content.

**R9 — nothing unverifiable is stored.** `vendor_id` is **dropped** from the pointer:
nothing stamps it on a payload and nothing can check it, so storing it would be a claim
about a recording rather than a property of it — which `mindsos_llm/recorded_sets.py`
refuses by design. It stays available on the exported envelope's `captured_over`, which
the pointer names. `credential_level` is **derived from the payloads** and refused on
contradiction or multiplicity, the rule `export_set` already enforces.
**OWNER 2026-09-18.** ⚠ **Premise CORRECTED 2026-09-20 by measurement, ruling unchanged:**
`export_set` refuses only a SUPPLIED level that disagrees; with none supplied it exports a
multi-level set silently. The refusal is new work, built in `describe_set` (R13).

**R10 — the recorder has no don't-know.** The `comprehension` family's `OPTIONAL_RETURN`
is a *reader's* shape — a reading that cannot answer returns a null value. The recorder
reads nothing: every failure is *"this file is not a recorded set"*, which refuses. The
reason is not lost — `runtime.invoke` emits a problem-trace record carrying the
exception message. ⚠ Amendment 4's *"the reason on the paired record"* named a record
its own output list does not have. **OWNER 2026-09-18.** ⚠ **Premise NARROWED 2026-09-20:**
the trace record is emitted only when a sink AND a `request_id` are both present.

**R11 — every named L2 role is recorded in ADR-0150**, enforced by a sentinel deriving
from `ALL_ROLES`. Measured: §am-5's escape clause requires a §Revisions entry per new
**named** role, and it has been skipped twice — `policies` carries the literal
placeholder `§amendment-<N>` in `identifiers.py`, and `prompts` appears nowhere in
ADR-0150. **OWNER 2026-09-18.** ⚠ **Count CORRECTED 2026-09-20:** FOUR roles were
unregistered, not two — also `learned-pipelines`, and `request-patterns`, whose rename
never reached the ADR. All four registered by ADR-0150 amendment-12 (`537fd82`).

**R12 — `set_path` may name a bare recording OR an exported set**, detected by the
`format` key, because refusing the export format would point L2 at the one artifact a
third party cannot replay. The deriver producing the pointer payload — the manifest
**plus the sorted `request_keys`** — is **public** in `mindsos_llm.recorded_sets`;
`_derive_manifest` is private and computes no keys. ⚠ Adding a function to an existing
module is not the edit R2 forbids: R2 says the RECORDS are not held in `mindsos_llm`.
**OWNER 2026-09-18.**


---

**R13–R18 are I-10's build rulings, DELEGATED BY THE OWNER 2026-09-20** — *"some of
them you can make yourself based on the final goal instead of having me answering
them"* — ruled by the I-10 chat after convergence passes scored against §1, and
confirmed with *"go"*. Each is recorded as ADR-0210 amendment 6.

**R13 — one public `describe_set(path)` in `mindsos_llm.recorded_sets` owns the
file read.** It reads the file ONCE, hashes those bytes, detects `format` (R12),
loads bare-or-exported, and returns the derived facts — the resolved `path` it
opened, `sha256`, `responses`,
`key_schema_version`, `identities`, `prompts`, the sorted `request_keys`,
`credential_level` — refusing on contradiction or multiplicity (R9). Named for the
file it DESCRIBES, never for the L2 record it feeds: L2 vocabulary inside
`mindsos_llm` would be am-4 clause 1's error pointing the other way. The L3 body
makes no filesystem call; measured 2026-09-20, `mindsos_capacity` and
`mindsos_knowledge` contained none.

**R14 — one identity.** Address `recorded-sets-<v>:set:<sha256>`; `sha256` is the
property and the address (the `prompts` precedent). `set_id` is not stored (R8 makes
it a second spelling), nor `vendor_id` (R9).

**R15 — `credential_level` leaves the input record.** Derived (R9), and omitted
when every payload is unstamped.

**R16 — `captured_at` is `recorded_at`.** No payload carries a capture time, so
`captured_at` would be a claim about the recording; the write time is a fact about
the write. R9's rule applied to a field R9 did not name.

**R17 — the payload is a `dict`** (ADR-0182's codec encodes it), and
`storage_mode` is declared AND written — `prompts` declared it and never wrote it.

**R18 — a re-capture of the same bytes REFUSES** (`PromptEditionExistsError`'s
shape), and `file_uri` is the resolved absolute path with no scheme — taken from
`describe_set`'s `path`, never from the caller, so a pointer cannot name one file
and hash another.

---

**R19–R28 are I-12's design rulings, 2026-09-21.** R19, R20 and the split into I-17
+ I-12 are **OWNER** rulings; R21's full reach is **OWNER** (P2). R22–R28 were ruled by
the I-12 chat against §1 and each cites its authority. Recorded as ADR-0210 amendment 7.

**R19 — "re-run without the borrowed model" means RE-DERIVE, not replay.** The
conclusion's value DataState is produced again, from the same source text, by a
producer that does not consult the model; the result is compared with the stored
conclusion. Replaying the recorded answer reproduces the MODEL's output without a
vendor — reproducibility, not removability — so it is not excision. **OWNER
2026-09-21** (Q1). ⚠ Consequence: the re-run does not read a recorded set, so **I-12
does not depend on I-10**; I-10 stays DONE and serves replay (contract rows 5, 6).

**R20 — "shown" means VERIFIABLE for everything that was asked**, prompt words and
extraction schema included. **Supersedes R8's asymmetry for prompts.** ⚠ Measured
2026-09-21: the words sent come from a `resolve_prompt` the DEPLOYMENT injects into the
adapter (`adapters/anthropic.py`, *"the only source of prompt words"*), and nothing in
core ties it to the `prompts` role — so enforcing `append_only` would NOT have made a
shown prompt the one that ran. The extraction schema is in no record at all: not on the
origin record, not on the declaration (it lives in the reader's closure), not in
`request_key`. **OWNER 2026-09-21** (Q2, option ii).

**R21 — the client hands the transport EVERYTHING the model receives**: prompt words,
extraction schema, tool name and description, model, temperature, `max_tokens`. The
transport adds only wire syntax and the credential. ⚠ Measured 2026-09-21: `LiveLLM` and
the adapter each take their own `model_id` and `temperature`, and nothing checks they
agree — so the stamped values are a configuration claim, not a fact about the call.
Every stamp becomes a fact about what the client sent (R9's rule). *"The transport sends
exactly what it was handed"* joins `UNVERIFIABLE_PROPERTIES` by name. **OWNER
2026-09-21** (P2).

**R22 — `request_key` v2 hashes what was asked BY CONTENT**: the prompt words' digest,
the schema's digest, the framing (tool name, description, `max_tokens`), model,
version, temperature and the source text. `KEY_SCHEMA_VERSION` bumps, so a v1 set misses
loudly (the key's own rule). Authority: R20, R21, and the key's docstring (*"everything
that materially determines a reading"*), which v1 does not meet.

**R23 — the origin record carries the schema TEXT and both digests.** A prompt edition
is addressed by `prompt_iri` + `prompt_version`, which do not identify a schema, so the
schema is shown from the record and verified against the answer's stamp. The prompt
words stay in the `prompts` role; no digest is stored beside the text it describes
(am-4's own argument). Authority: R20.

**R24 — *shown* is verified by RECOMPUTING `request_key`** from the prompt edition's
text, the record's schema, the answer's stamped model settings and the source text found
in the grounding graph. One match verifies all of what was asked; a mismatch names that
the shown material is not what ran. Authority: R20, R8's pattern (identity is content).

**R25 — a substitute producer** outputs the same value DataState from the same source
DataState and declares `consults_llm=False` (ADR-0180 §am-3). None registered ⟹ the
report says **not yet excisable** — the honest state of every real conclusion until
MindsOS reads text. Authority: R19.

**R26 — *identified* is `origin_method == read_by_model`, in EVERY mode** (a replayed
answer is still the model's), refusals the model produced included;
`environment_fault` refusals excluded (no reading happened). Authority: ADR-0210 am-4
("Identified: already").

**R27 — the domain of "every conclusion" is a conclusion in a PERSISTED Episode's
grounding graph** — the only place its source text lives. The origin record holds the
source's type, a quote and a one-way key; a recorded payload holds the answer only.
Proven by `tests/llm_seam/test_a_reading_reaches_its_source_text.py`. Authority: RULES
§12.3 (a quantified claim states its domain).

**R28 — L4 locates and dispatches; L3 compares.** Reading an Episode and choosing a
producer is control flow (L4, R4); judging agreement between two values is a
capability (L3, R1). Authority: R1, R4.

## 3. THE ITEM LIST

| id | item | filed as | state |
|---|---|---|---|
| I-1 | relocation, seam, level 1, Anthropic adapter, record / replay / export | core-mindsos-llm-communication | DONE(4f54f3d) |
| I-2 | the capability contract harness | core-mindsos-llm-communication | DONE(511b999) |
| I-3 | L0 credential custody + per-session client | core-mindsos-llm-communication | DONE(329ffa7) |
| I-4 | level-2 broker contract + reference broker | core-mindsos-llm-communication | DONE(5e97985) |
| I-5 | an answer carries its mode and credential level | core-mindsos-llm-communication | DONE(3fe37db) |
| I-6 | `verify_transport` asks OVERRIDE, not only presence | core-llm-contract-identity-check-asks-presence-not-override | DONE(f2310ae) |
| I-7 | a contract check never vanishes from the report | core-llm-contract-identity-check-asks-presence-not-override | DONE(44059f7) |
| I-0 | this plan, tracked; RULES §5 plan rules; the scope guard; and the prose corrections at the eight sites that contradicted §1 and §2 | core-docs-one-owner-per-fact | DONE(76b17e4) |
| I-8 | the L2 record shapeS — **two records, different authors**: the prompt edition (a `prompts` role of its own, dual-scope — ⚠ **the `policies` reuse is WITHDRAWN by ADR-0210 am-5**) and the recorded-set pointer (new Local-only `recorded-sets` role) — plus the recorder's contract, `capacity:comprehension:record_reading_set` (R3, R4, R5). ADR-0210 amendment + a sentinel; no product code | core-llm-recorded-set-l2-pointer-owner | DONE(711dc16) |
| I-9 | prompt bodies have a home: a conclusion stamped `prompt_iri` + `prompt_version` can show the text it names | core-llm-prompt-text-has-no-home | DONE(a1687f2) |
| I-10 | a recorded set has a home in the graph: pointer + provenance in L2 Local, payloads stay a FILE | core-llm-recorded-set-l2-pointer-owner | DONE(780ee1b) |
| I-11 | `mode` and `credential_level` reach the origin record. Required under §1, no longer deferred; prerequisite discharged at `fe0e19a`. ⚠ **NOT blocked by I-8** — measured: `origin_v0.py` imports only `..identifiers` and `..printable`, so it has no L2 dependency, and the change is two names in `PRODUCER_DECLARED` plus two lines in `comprehension_v0._record` reading fields the answer already carries beside the seven at lines 353-359 | core-llm-l3-may-declare-answer-mode-and-level | DONE(44889a9) |
| I-12 | the excision capability: identify a conclusion as model-produced, show what was asked, re-run it without the model. Becomes the twelfth contract row. **Specified 2026-09-21 by R19–R28**; blocked by I-17 | core-llm-excision-capability | TODO |
| I-13 | a transport's other keys survive into the answer | core-llm-transport-extra-keys-survive-into-the-answer | OUT(trigger: a consumer iterates an answer's keys, or a third-party transport's output is stored) |
| I-14 | level 3 / hosted adapter, the old "slice 3" | core-llm-level-3-awaits-a-hosted-adapter | OUT(trigger: a consumer wants Bedrock, Vertex or Azure) |
| I-15 | a capacity **declares** that it writes (R7): `writes=True` on the declaration, both invoke sites gate the `writeable` injection on it instead of on `outputs == ()`, and an AST guard reconciles the declaration against the body — the `context.llm` census shape. **Blocks I-10**, whose ruled declared output is unreachable without it | core-capacity-write-is-declared-not-inferred | DONE(8f1f7d4) |
| I-17 | an answer names what was asked BY CONTENT (R20–R23): the client resolves and hands the transport everything the model receives, stamps the prompt and schema digests, `request_key` v2, and both digests plus the schema text reach the origin record. **Blocks I-12**, whose *shown* is unverifiable without it | core-llm-answer-names-what-was-asked | TODO |
| I-16 | I-9's writer gets its installer. Measured 2026-09-17: nothing in the tree calls `build_write_prompt_edition`, and `install_learn_parameter_capacities` is the precedent it skipped — so a `DONE` item is a declaration L4 cannot route to | core-llm-prompt-edition-has-no-installer | DONE(6e6514e) |

**DONE WHEN: I-0, I-8, I-9, I-10, I-11, I-12, I-15, I-16, I-17.**

**ORDER: I-0 ✅ → I-8 ✅ → I-11 ✅ → I-9 ✅ → I-15 ✅ → I-16 ✅ → I-10 ✅ → I-17 → I-12.**
I-9 and I-10 are blocked by I-8, the L2 record shape, and may ship in either order once
it is ruled. ⚠ **I-9's dependency is the ROLE decision only** — measured: no prompt text crosses the
transport seam, so the text is in no ANSWER. ⚠ **It does NOT follow that no run writes it**
(ADR-0210 am-5 withdraws that): per R2 an L3 write capacity takes the text as an INPUT
record, as `learn_parameter` takes a value it did not compute. ⚠ **I-11 is NOT blocked by anything and can start today** — see its row.
I-12 needs all three. ⚠ **CORRECTED 2026-09-21 by R19:** I-12 needs I-9 and I-11
and **I-17**; it does NOT read a recorded set, so I-10 is not its prerequisite.

---

## 4. STANDING CONSTRAINTS — do not re-derive

- `mindsos_llm` may not import `mindsos_capacity`, `mindsos_knowledge`,
  `mindsos_server`, `mindsos_intelligence` or `mindsos_broker`.
- L2 Local, **never Global** — reproducibility needs an explicit export/import.
- No silent repair layer anywhere, including inside a broker.
- No credential in the L0 audit trail. A token refresh is never a reaction to a rejection.
- `mindsos_llm` is **not** a subsystem (RULES §8; a guard scans for the word).
- Every change to `mindsos_*` takes the full RULES §7 ceremony: gate, CLI check, tag.

---

## 5. WHY THIS FILE EXISTS

Scope lived in four documents that each restated it and each went stale: the CR (written
before slices 1b–5 existed), ADR-0210, `STATE.pending_designs[79]` (stale about its own
build state **twice**), and a capability table promoted to "definition of done" by a
ruling in a chat. Every chat reconstructed the plan from fragments, and reconstruction
is where opinion entered.

⚠ **Separately, `core-llm-recorded-set-l2-pointer-owner` sat open for eight days because
Rule 1 turns a consumer-less question into a trigger — the rule that stops premature
building also stopped the decision.** R1 closes it. **A question the OWNER must answer is
not subject to Rule 1; put it to him instead of filing it.**

### ⚠ Known gap in the guard
`tests/architecture/test_mindsos_llm_plan_is_the_scope.py` cannot cross-check this file
against `STATE.pending_designs`, because **`STATE.json` is not COPYed into the test
image** (measured: zero occurrences in the `Dockerfile`; `docs` is copied at line 289).
Adding it would let any other lane's STATE edit redden this guard, which is worse.
**Re-open trigger: `STATE.json` enters the image for some other reason.**

---

## 6. AMENDMENT LOG

*(date — what changed — who approved. An entry without an approval line is not an
amendment.)*

- **2026-09-13** — file created. **Owner ruled:** scope = "a removable stand-in" (§1),
  superseding the 2026-09-05 capability-table criterion; R1 L3 writes, not L0; R3 the
  family is `comprehension`, not `llm`; R4 L4 decides when a record is needed; R5 the
  recorder consumes the answer, never the vendor. R2 and R6 measured from the tree and
  confirmed by the owner.
- **2026-09-16** — **ADR-0210 amendment 5 WITHDRAWS amendment 4's clause 1**, approved by
  the owner. (a) A prompt edition does **not** reuse `policies`: that role was created by a
  CONSUMER of this system (Decision Records) and its own file says the store's identity is
  part of the claim a Record makes, so a module generic to any text interpretation does not
  borrow it. `prompts` is a role of its own, dual-scope, closed set 17 → 18. (b) *"No run
  can write a prompt edition"* does not follow from *"no prompt text crosses the seam"* —
  R2 says L3 writes what L2 holds, and the text arrives as an input record.
  ⚠ **Both errors have one cause: a design question answered by looking for a matching
  shape in the tree instead of by reading the plan.** Measurement verifies a claim; it
  cannot generate a decision. R2 already held the answer.

- **2026-09-14** — **I-8 ruled and recorded as ADR-0210 amendment 4**, **approved by the
  owner** ("agreed with D2... proceed"). Three things it settles, each measured before it
  was written. **(a) TWO L2 records, not one.** The prompt edition is AUTHORED and reuses
  the existing `policies` role graph — `schemas/policies.py` already argues that a
  versioned prompt body is the same shape as a statutory threshold — and the recorded set
  is a pointer node in a NEW Local-only `recorded-sets` role. **(b) OWNER RULING: prompt
  editions are DUAL-SCOPE**, correcting §2 R2 above and ADR-0210 amendment 3; only recorded
  sets are Local-only. **(c) the recorder DECLARES its pointer IRI as an output** rather
  than being a write terminator, because the ruling that rejected L0 did so on the ground
  that nothing in the run graph would then name the set. ⚠ Two gaps were FILED rather than
  guessed: `append_only` is declared-not-enforced so a shown prompt is retrievable but not
  verifiable, and the shipped manifest carries no `request_key`s — which is why the
  `RecordedSet` payload must carry them, or I-12 cannot get from a conclusion to its set.

- **2026-09-14** — two corrections to this file, found by the post-ship passes on
  `76b17e4` and **approved by the owner** ("amend"). **(a) I-0 shipped as `76b17e4` and
  was still recorded `TODO`** — the plan's first item was to commit itself and it did not
  record its own commit. ⚠ The scope guard cannot catch this: a `TODO` listed in
  `DONE WHEN` is legal, which is correct for the guard and was a gap in the editing.
  **(b) I-11 was placed behind I-8 and is not blocked by it** — measured:
  `mindsos_capacity/builtins/origin_v0.py` imports only `..identifiers` and
  `..printable`, so the origin record has no L2 dependency whatever, and I-11 is two
  names in `PRODUCER_DECLARED` plus two lines in `_record` reading fields the answer
  already carries. It was holding a cheap, ready item behind a ruling it never needed.

- **2026-09-18** — **six rulings, R7–R12 in §2, and two new items, I-15 and I-16**,
  **approved by the owner** ("confirmed... proceed"), after a convergence round run on
  final quality rather than on remaining time — the owner's instruction was explicit:
  *"do not recommend anything based on time... otherwise we will have to fix it in the
  future and that become even longer."* ⚠ **The round REVERSED two of this chat's own
  earlier recommendations**, which were argued from elapsed time and are wrong on the
  merits: keeping amendment 4's declared output as an L4-only capability (now R7's
  explicit declaration), and amending ADR-0150 for the new role without backfilling the
  two roles that skipped it (now R11's sentinel plus the backfill).
  **Two measurements produced R7 and I-16, and neither was known when I-8 was ruled:**
  both invoke sites key the write-context injection on `not declaration.outputs`, and
  `build_write_prompt_edition` has no caller anywhere in the tree.
  ⚠ **I-15 is ordered BEFORE I-10 rather than folded into it** — two claims in one gate
  is a ship the RULES §12 sweep cannot audit.

- **2026-09-18 (post-ship)** — **I-15 SHIPPED `8f1f7d4`** (PR #225, tag
  `capacity-declares-writes-confirmed`), gate 5248 passed / 0 failed, id diff
  **+13 / −0 exact**, four mutations each one red at the predicted test. Six
  findings and their dispositions are in `STATE.recent[0]`; the two worth the
  plan's memory: **an unscoped version of the new registration refusal would
  have outlawed every Monitor** (found by reading the declarations, not by the
  gate), and **reverting the `runtime.py` branch reddened nothing** until the
  claim it was missing was written — RULES §12.2(c), a mutation that reddens
  nothing is a finding, not a pass. One item filed rather than absorbed:
  `core-capacity-two-context-types`.

- **2026-09-18 (post-ship)** — **I-16 SHIPPED `6e6514e`** (PR #227, tag
  `prompt-edition-installer-confirmed`), gate 5257 passed / 0 failed, id diff
  **+9 / −0**, three mutations each one red at the predicted test. I-9's
  writer is now installable, and a **zero-argument capacity factory whose
  module defines no installer is a red test** — the class, with no allowlist,
  because every installer-less factory in the tree is parameterised.
  ⚠ **Two findings about the INSTRUMENTATION, not the tree:** a prediction
  was built on a literal this chat echoed instead of counted (+10 predicted,
  +9 measured, the tree right), and a box reported `failed=0` from grepping a
  crash dump that contained no results at all. Both are in
  `STATE.recent[0]`. **I-10 is next, and it is now unblocked in the way R7
  intended: its recorder may declare its pointer as an output AND write.**

- **2026-09-20** — **R11 ENFORCED AS I-10's PREREQUISITE, and R13–R18 delegated.**
  PR #233 (`537fd82`, tag `role-register-confirmed`) shipped ADR-0150 amendment-12
  and the sentinel that derives the register's domain from `ALL_ROLES`. It shipped
  BEFORE I-10 rather than inside it for the reason I-15 did — one claim per gate —
  and needed no plan amendment, since R11 already authorised it. ⚠ **Three rulings'
  premises were corrected by measurement, none reversed:** R11 undercounted the
  unregistered roles by two (`learned-pipelines`, and `request-patterns`, whose
  rename never reached the ADR); R9's *"the rule `export_set` already enforces"* is
  half true (it checks only a SUPPLIED level); R10's problem trace needs a sink AND
  a `request_id`. **R13–R18** are I-10's build rulings, **delegated by the owner**
  (*"some of them you can make yourself based on the final goal"*) and confirmed with
  *"go"* / *"proceed"*. Filed: `core-llm-recorded-set-has-no-file-writer` — nothing
  in the tree writes the file a pointer names.

- **2026-09-21 (post-ship)** — **I-10 SHIPPED `780ee1b`** (PR #237, tag
  `recorded-set-home-confirmed`), after its prerequisite PR #233 (`537fd82`, R11).
  Gate at `c285793`: 5375 passed / 0 failed; collected ids **+41 / −0, predicted and
  read back file by file**; six single-line mutations, each red exactly where
  predicted. CI then gated `d19103d`, rebased over PR #236 — another lane's
  widening of the role-count guard, measured to couple to no numbered claim — and
  the squash equals that tree. ⚠ **One design tightening during the build, recorded
  as R18:** `file_uri` comes from the path `describe_set` hashed, never from the
  caller, so a pointer cannot name one file and carry another's identity. ⚠ **Two
  instrumentation faults, both caught by their own fields:** a mutation row whose
  anchor never matched ran green on an unmutated tree (its empty bytes-changed
  field exposed it), and a tag box read a FAILED diff as "0 files differ" — a
  failed check must never read as a passing one. **I-12 is next and last**: every
  prerequisite it names now exists.

- **2026-09-21** — **I-12 SPECIFIED: rulings R19–R28 and a new item, I-17**, approved
  by the owner (*"agreed with q1 and q2"*, *"agreed with P1 and P2"*). The premise was
  measured first, as the handoff required. **Three measurements changed the design:**
  (a) a stored conclusion carries `request_key` but not its source text — the text is
  reachable only through the persisted grounding graph (R27, now guarded); (b) the
  prompt words sent come from a deployment-injected `resolve_prompt` that nothing ties
  to the `prompts` role, so the handoff's question *"enforce append_only?"* was the
  wrong question — the shown prompt was not even the same SOURCE as the sent one (R20);
  (c) the extraction schema is recorded nowhere, and `LiveLLM` and the adapter each hold
  their own model and temperature (R21). **R19 (owner): re-run means re-derive, not
  replay** — which removes I-10 from I-12's prerequisites (§3 note corrected in place).
  **I-17 is split out of I-12** for I-15's reason — one claim per gate: it changes the
  seam in `mindsos_llm` (R2 forbids records there, not the seam). ⚠ ADR-0210 am-6's
  *"I-12 scans the role's nodes"* cited no ruling and is superseded by R19: I-12 builds
  no set lookup. Filed: `core-llm-answer-names-what-was-asked` (I-17).
