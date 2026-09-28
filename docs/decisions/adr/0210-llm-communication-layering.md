# ADR-0210 — LLM communication is a cross-layer core capability: L0 holds the credential, `mindsos_llm` holds the wire, L3 mints one capacity per reading

**Status:** Accepted (2026-09-02). Owner-ruled 2026-09-02; **slice 1 merged at
`4f54f3d` (PR #199), tagged `mindsos-llm-slice-1-confirmed`, gate 4984/11/1x/0.**

⚠ **Accepted names the DECISION, not the build.** Slice 1 (the relocation, the
credential seam, the Anthropic adapter, the runtime registry, recorded-set
export/import), **slice 5** (`511b999`, PR #202, tag
`llm-capability-contract-confirmed`, gate 5003/11/1x/0) and **slice 2** (L0
credential custody and the per-session client — `329ffa7`, PR #203, tag
`mindsos-llm-slice-2-confirmed`, gate 5076/11/1x/0) are all in the tree.
**Slice 4** (credential level 2 — the broker contract and a reference broker,
`5e97985`, PR #204, tag `mindsos-llm-slice-4-confirmed`, gate 5152/11/1x/0) is
in the tree as well; see amendment 1. **Slice 3 is DEFERRED** with a named
re-open trigger, because level 3 is a property of the ADAPTER and core ships
one adapter declaring level 1 only (`core-llm-level-3-awaits-a-hosted-adapter`).
**Slice 3 is all that remains of the slice list.** ⚠ The sentence this replaced
said *"slice 4 is NOT built"* and survived the ship that built it — an ADR
header is a surface like any other and goes stale the same way.

⚠ **SLICE 2 CREATED THE FIRST `mindsos_server` → `mindsos_llm` IMPORT, and this
ADR did not name it.** It is legal — §I-S1 forbids the domain package importing
L0, not the reverse — and it is unavoidable: `seam.require_resolver` is an
`isinstance` check, so whoever builds a `Resolver` imports
`mindsos_llm.credentials`, and `mindsos_llm/__init__.py` does
`from . import adapters`, so there is no narrow import. **Decision 2 ("L0 holds
the choice and the credential, nothing else") is therefore held by a guard
rather than by structure:** `test_L0_builds_no_transport_and_no_client` walks
every module in `mindsos_server` by AST, from the filesystem, and refuses
`build_transport` / `build_client` / `LiveLLM` / `CapturingLLM` / `RecordedLLM`.

⚠ **What L0 stores for a credential (owner ruling 2026-09-05, built in slice 2):
a TYPED RESOLVER SPEC whose KINDS THE DEPLOYMENT REGISTERS**, symmetric with
`adapters.register`, so `git grep` answers *which credential sources can this
deployment use*. A kind is a module exposing `KIND_ID`, `SUPPORTED_LEVELS`,
`validate(spec)` and `build(spec) -> Resolver`; core ships exactly one, `env`.
**The stored value is a POINTER, never a secret** — level 1 is never STORED,
level 2 is never KNOWN, and only level 2 is "never sees it".

⚠⚠ **SUPERSEDED 2026-09-13 BY `docs/plans/MINDSOS_LLM_PLAN.md` — SEE AMENDMENT 3.**
The paragraph below records the 2026-09-05 ruling as it stood. The capability
table is a *consumer capability* contract, not the scope of the work; **the plan
file owns the scope now.** *Original paragraph follows.*

⚠ **THE DEFINITION OF DONE IS NOT THIS SLICE LIST.** Owner ruling 2026-09-05:
"complete" for `mindsos_llm` means the pass/fail table in
`docs/usage/runtime/llm-capability-contract.md` — what a consuming project can
do with `pip install mindsos-runtime` and no change to core, each row naming the
module that answers it and the guard that pins it. **ELEVEN rows as of
2026-09-10** (nine at the ruling, a tenth with slice 4, an eleventh with
amendment 2); all PASS. ⚠ The row count is stated here because it has been
wrong in this file twice — quote the table, do not recall its size.

⚠ **That table's own status column was stale from birth and is fixed at
`36a2c59`:** rows 7 and 9 read PARTIAL and FAIL while `511b999` — the commit
that added the document — closed both. L0 custody gets **no row**, ruled in
slice 2: every row is what a *consumer* can do with no change to core, and
custody is *deployment* configuration guarded in `mindsos_server`.

Implementation state lives in `STATE.json` (`pending_designs` →
`core-mindsos-llm-communication`, and `recent`), never here — this repo has no
`status:`/`implemented:` split yet, and that split is itself an open core item.

⚠ **CORRECTED 2026-09-05: this ADR used to say slice 2 opens with the question
of which layer owns the L2 pointer to a recorded set. It does not.** L0
credential custody and a recorded-set pointer share nothing but the word "L2",
and §7.2 of the CR already rules that L2 Local holds the pointer — only *which
layer writes it* is open. Refiled as `core-llm-recorded-set-l2-pointer-owner`;
it does **not** gate slice 2.
⚠⚠ **RULED 2026-09-13 — SEE AMENDMENT 3.** *Which layer writes it* is no longer
open: **L3 writes it.** `docs/plans/MINDSOS_LLM_PLAN.md` carries the ruling.

Supersedes the
placement half of the `mindsos_capacity/llm` package docstring, whose own
promotion trigger this ADR fires. CR:
`confirmation_docs/CORE_CR_MINDSOS_LLM.md`.

## Context

`LiveLLM` consults an external model through a **deployment-supplied
callable**, and that callable was never written in core. A project wanting
MindsOS to read a document therefore writes the network-touching piece
itself. One lane did — `dr_transport.py`, 419 lines, 14 guards, four
adversarial review rounds, run against a live provider. A second lane now
needs the same capability and would otherwise produce a third copy.

Three docstrings on `main` state that this is intentional:
`live.py` (*"no provider SDK ships in this repo"*), `contract.py` (*"§6.4: no
vendor inside MindsOS, credentials in the transport's closure, the gate has
no network"*), and `dr_transport.py` ¶1 (it lives outside core by design).

The owner's ruling is that this is wrong as a design, not merely as a
convenience: **calling a model is MindsOS machinery.** Every project built on
MindsOS needs to call, receive and record, and none of them should write the
wire.

## Decision

**LLM communication is a core capability spanning layers.**

* **L0 (`mindsos_server`)** owns the user's **vendor id**, **credential
  level**, **mode** and **credential custody**. Released to L3 through a
  capability, never read ambiently, **never written to the audit trail**. L0
  gains no outbound network client.
* **`mindsos_llm`** — a new top-level package — owns adapters, the call,
  decoding, recording, replay and the credential seam. Substrate: it
  registers nothing.
* **L2 (`mindsos_knowledge`)** owns prompt text and versions, and the
  **pointer and provenance** of a recorded response set. **Local only, never
  Global.** The response payloads themselves stay a file the pointer names —
  a JSON map of `request_key` → payload does not belong in a metagraph.
* **L3 (`mindsos_capacity`)** owns the capacities L4 calls: **a factory mints
  one capacity per reading**, never a single generic `call_llm`. A single
  capacity makes every reading structurally identical, so L4 cannot
  distinguish one reading from another and cannot pick a route. The prompt is
  call-specific and travels with the minted capacity.
* **L4** decides a reading is needed and routes to the capacity. **L5** holds
  the answers.

**The vendor is resolved at runtime** from a named adapter registry keyed by
the id L0 stored. An import-time choice cannot satisfy "the user picks a
vendor on first run and can change it later".

**The client is per session**, built after L0 resolves that user's vendor,
level and mode. **Mode and credential level are stamped on every answer.**

### Three credential levels, offered as the adapter supports them

1. **Never stored** — the credential lives in the user's keychain or
   environment, is fetched through a callable at call time, and the header is
   scrubbed in a `finally` after the call.
2. **Never known** — a local broker the user runs holds the credential and
   adds it. ⚠ This is **not a resolver**; the credential never reaches
   MindsOS, so level 2 is a *wrapper around the adapter*, and modelling it as
   "a resolver returning nothing" is wrong at the seam. MindsOS ships the
   broker contract **and** a reference broker.
3. **Reduced blast radius** — the resolver returns a short-lived scoped token.

⚠ **Level 3 is a property of the adapter, not of MindsOS.** Anthropic's
direct Messages API authenticates with a long-lived `x-api-key` and offers no
token-exchange flow; expiring credentials come from the hosted routes
(Bedrock STS, Vertex OAuth, Azure Entra), which are different adapters. The
Anthropic-direct adapter is level 1 only and says so. The seam is
credential-agnostic from slice 1 so this costs nothing later.

⚠ **Level 3 collides with `no_silent_retry`.** A token expiring mid-run
forces refresh-and-retry, which is indistinguishable from the silent retry
`contract.py` requires a transport not to do. Refresh happens **before** the
call on near-expiry, never as a reaction; **a 401 is a failure, not a quiet
second attempt.** Guards pin both.

### The invariant is restated, not quoted

> **No provider is baked in.** The adapter is selected at runtime from the
> user's stored vendor id; a second provider is a new adapter, not a change
> to core. Credentials are resolved at call time and scrubbed after; the gate
> acquires no network, no credential and no vendor dependency.

Anything external saying *"no vendor inside MindsOS"* becomes refutable on
merge and must be rewritten to this form.

### The credential property is enforced, not verified

`dr_transport.py`'s credential hygiene took four review rounds, and **each
round narrowed a sentence rather than a mechanism**. Round four was caught
only by running the DEFAULT opener — every credential guard injects a fake
one, so the property had been asserted in exactly the configuration where it
holds. *Not a road the guard missed, a configuration it missed.*

Core therefore **enforces the three mechanisms** — resolver callable,
always-returning header helper, `finally` scrub of the composed request — and
`verify_transport` gains `credential_not_retained_on_the_composed_request` in
`UNVERIFIABLE_PROPERTIES`, reason: *"requires reaching inside the transport; a
harness that injects an opener asserts it in the one configuration where it
holds."* A harness that only calls a transport cannot reach the object that
transport composed, and any check injecting an opener recreates round four's
blindness exactly. `contract.py` already established this pattern for four
§6.3 properties.

## Consequences

* **`mindsos_capacity/llm` relocates to top-level `mindsos_llm`** — its own
  docstring names *"a vendor dependency arriving"* as the promotion trigger,
  requiring `git mv` plus the 9-site new-top-level-package checklist
  (PHASE_27 PB-29). Calling a model is used by more than L3, so the top-level
  home is also the honest description.
* **Recorded sets are never Global**, which means reproducibility needs an
  **explicit export**: a set exports to a file and imports into another user's
  Local, so a third party can re-run a result with no key and no vendor
  account.
* **The core gate needs a test session** — replay tests need a Local scope.
* `comprehension_v0` stays the reading capacity; nothing about
  quote-verification or the origin record changes.
* **"Subsystem" is not used for this work in `mindsos_*`.** `RULES.md` §8
  defines it as a consumer owning nothing architectural — the opposite of
  what this ADR establishes — and
  `tests/architecture/test_no_subsystem_ownership.py` scans for the word.
* `falkordb` is already a hard dependency with a vendor SDK import in
  `mindsos_core/persistence/client.py`, so a vendor client inside core is not
  new; a *model* vendor is, and the restated invariant covers it.
* No version bump. `core_version` stays `phase50`; the release-train integer
  moves only on a numbered-phase ship.

## Alternatives rejected

* **One generic `call_llm` capacity.** Rejected: every reading becomes
  structurally identical, so L4's route search cannot tell readings apart and
  a route must be hand-wired rather than found.
* **Adapters inside `mindsos_server`.** Rejected: L0 is auth, sessions,
  authorization and audit; an outbound client to a model vendor is an egress
  it has never had.
* **Core ships only assertions, no wire code** (the reviewing lane's first
  answer). Rejected by owner ruling: it leaves every project writing the wire,
  which is the problem.
* **Level 2 as a resolver returning nothing.** Rejected: the credential never
  reaches MindsOS, so there is nothing to resolve; it is a different request
  path.
* **A core guard asserting the credential property.** Rejected: see above —
  it would repeat round four's configuration blindness.

---

## Amendment 1 — level 2 as built (slice 4, 2026-09-07)

**Amendment status:** Accepted. The decision above stands; this records the
four shapes it did not fix, each settled against the tree rather than reasoned
from this document's prose.

**1. Level 2 is declared SEPARATELY from the wire's levels.** The obvious build
— widen the Anthropic adapter's `SUPPORTED_LEVELS` to `(1, 2)` — was rejected.
That tuple is documented as a promise about the *provider's wire*, and the
provider never learns a broker exists; level 2 is a fact about the adapter's
code, namely that it can compose its request without a credential. One tuple
carrying both meanings would also have forced the resolver to become optional
in `build_transport`, which is the one function that must never take a
credential optionally. ⟹ `BROKERED_LEVELS` alongside `SUPPORTED_LEVELS`,
`build_brokered_transport` alongside `build_transport`, and
`adapters.offerable_levels` — the union — as what a picker offers and what L0
validates a stored level against. The registry refuses an adapter that declares
one half without the other.

**2. The reference broker is a NEW TOP-LEVEL PACKAGE, `mindsos_broker`.** It is
the one program in this tree that deliberately holds a credential, and
`mindsos_llm` is designed to be structurally unable to. Putting it inside that
package would have needed a bespoke guard to say nothing imports it; as a
separate package the property is enforced by the guard already there —
`mindsos_broker` joins `FORBIDDEN_ROOTS` in
`tests/llm_seam/test_import_isolation_mindsos_llm.py`. The dependency runs one
way: the broker imports the contract, the contract never imports the broker.

**3. The broker endpoint rule is NOT `require_https`.** That function states its
own reason — *"`https` rather than 'has a scheme': this request carries a
credential."* A brokered request carries none, so the rule that applies is
about the customer's source text leaving the machine: `https` anywhere, or
`http` on a loopback **literal**. Not `localhost`: a name is resolved, and what
it resolves to is not core's to promise. The broker's own *upstream* hop does
carry the credential and keeps `require_https` unchanged.

**4. L0 custody of a level-2 configuration is DEFERRED with a named trigger**
(`core-llm-level-2-l0-custody`). `llm_config.credential_kind` is `NOT NULL`,
every kind declares the levels its SOURCE can produce, and at level 2 there is
no credential for a source to produce — a broker is a wrapper around an
adapter, not a kind, and modelling it as one is what this ADR already rejects.
So a level-2 row cannot be stored today, deliberately, and level 2 is
configured by the deployment at client construction. Re-open when a first-run
picker must offer it. ⚠ The deferral is *pinned rather than asserted*: the
`level-vs-SOURCE` case in `tests/llm_seam/test_l0_credential_custody.py` is
`set_llm_config` refusing exactly that configuration.

⚠ **A FINDING AGAINST THIS ADR, MEASURED NOT RECALLED.** The Decision section
above says *"Mode and credential level are stamped on every answer."* **They are
not.** `LiveLLM.read` stamps `model_id`, `model_version`, `prompt_iri`,
`prompt_version`, `temperature`, `request_key` and `recorded`, and nothing
else; `credential_level` appears once in the tree, as an *optional supplied*
field of `recorded_sets.export_set`'s manifest — in the module whose own rule
is that a manifest is derived, never supplied. So decisions 5 and 6 are
unbuilt, and the argument `credential_kinds`' docstring makes for the
level/kind pairing check — *"the level is stamped on answers, so an unchecked
pairing corrupts provenance"* — currently rests on a property the payload does
not have. The line above is left standing because it is the DECISION and the
decision is not withdrawn; the gap is filed as
`core-llm-answer-carries-no-mode-or-level` and was **not** adopted into slice 4,
because adding payload fields moves `recorded_sets`' derived manifest and every
guard asserting a payload's key set — its own ship, not a rider on this one.

⚠ **CLOSED by amendment 2 below.** The paragraph above is kept as written
because it is the measurement that found the gap, and because one clause of it
turned out to be wrong in a way worth keeping visible — see amendment 2's first
correction.

---

## Amendment 2 — decisions 5 and 6 as built (2026-09-10)

**Amendment status:** Accepted. The decision is unchanged; the tree has caught
up with it. `core-llm-answer-carries-no-mode-or-level` is closed.

**Two corrections to amendment 1's own prose, both measured.**

1. *"Every guard asserting a payload's key set"* — **there are none.** No check
   in the tree asserts a payload's exact keys: `recorded_sets.REQUIRED_PROVENANCE`
   and `contract`'s identity check are both SUBSET checks, and `import_set`
   compares the derived *manifest*, not payload keys. Adding fields was
   therefore additive, and the cost that had been used to defer this was
   largely imaginary. **Grep the predicate, not the sentence.**
2. *"`credential_level` appears exactly once in the tree"* — it appears in
   `client.build_client`, `mindsos_server/llm_custody.py`, `_schema.py` (a
   `NOT NULL CHECK (… IN (1,2,3))`) and `audit.py`'s
   `EVT_LLM_CREDENTIAL_RELEASED` payload. What appears once is the *stamped
   payload field*, which is the claim that mattered.

**1. Mode is stamped by the CLASS, never by an argument.** `LiveLLM.MODE`,
`CapturingLLM.MODE`, `RecordedLLM.MODE`. This is the rule `recorded` has
followed since slice 1 — hardcoded `False` and `True`, never passed in — and it
is adopted for the same reason: *a mode a caller can pass is a mode a caller
can forge*, and an answer stamped `replay` by a client that just called a
provider is a lie no later check can catch. ⟹ `client.MODES` is no longer three
literals beside three other literals; it is **derived from the three classes**,
so a mode this package offers that no class serves is unwritable. The SQL
`CHECK` parity guard is now a three-way check through that derivation.

**2. `CapturingLLM` overrides `mode` and only `mode`, before the store write.**
`recorded` still passes through as `False` — it answers *"was this replayed?"*,
and a capture was not. `mode` answers *"which of the three produced it?"*, and
only this object knows the answer is `capture`. ⚠ **The ordering is a claim:**
the saved copy is the artifact a third party replays, so a stored payload
stamped `live` beside a returned payload stamped `capture` would be two copies
of one answer disagreeing about how it was obtained. Guarded on both doors.

**3. The credential level is pushed in and has NO DEFAULT.** L0 owns it;
`build_client` passes the *resolved* level, which at levels 1 and 3 may come
from `resolver.level` rather than from a keyword. `LiveLLM` takes it as a
required keyword-only `Optional[int]`: `None` is a real value — a
`contract.verify_transport` probe genuinely has no level and says so — but a
default would let a level nobody chose reach an answer, which is the
*optional-supplied* shape this ADR criticises two paragraphs up.

**4. A replayed answer reports `credential_level = None`.** Not the level the
answers were captured under: that would be this class making a claim about a
run it is not serving, and `replay.py`'s standing rule is that provenance is
stamped, never read out of the recorded blob. The capture-time level is a
property of the recorded SET and lives in its export manifest.

**5. `export_set`'s supplied `credential_level` is now CHECKED, not trusted.**
It was supplied *because the payloads did not carry it*; they do now, so the
value stopped being redundant and became **falsifiable** — an export could
declare a level its own responses deny. It is refused on two doors: a
disagreeing single level, and a mixed set no single value describes (mirroring
`replay_config`'s multi-identity refusal). ⚠ A set recorded *before* this
amendment carries no such key and is exported unchecked — an absent key is not
the same as a key whose value is `None`, and collapsing the two would have
refused every pre-existing set for no verification gain. `credential_level` is
deliberately **not** added to `REQUIRED_PROVENANCE`, exactly as `recorded`
never was.

**6. Neither field enters `request_key`, and that is now pinned by asking the
function's SIGNATURE.** The key is documented as *"everything that materially
determines a reading"*, and neither does: a set captured at level 1 must replay
to a client configured at level 2, and a captured answer must replay at all.
Nothing pinned the key's input set before this ship.

**What this amendment does NOT do.** It does not carry the two fields into
`mindsos_capacity`'s origin records. That is not a scope choice: `mindsos_llm`
may not import `mindsos_capacity` (`FORBIDDEN_ROOTS`), so this package is
structurally unable to make that change, and which payload fields L3 declares
is L3's decision. Filed as `core-llm-l3-may-declare-answer-mode-and-level`.

⚠ **A FINDING AGAINST THE HARNESS THIS SHIP PUBLISHES.**
`contract.verify_transport`'s `identity_is_stamped_above_the_transport` asks
**presence, not override**. A consumer's transport that returns its own
`model_id` *is* overridden — `LiveLLM` stamps after decoding — but the shipped
harness never tries it and reports PASS, while the in-repo guard
`test_identity_is_stamped_above_the_transport_and_overrides_it` does try it. The
published check is the weaker of the two, and has been since slice 1. Closing it
means a `forging_transport=` alongside the three fixture transports, which is a
change to a published signature and not this ship's ruling. Filed as
`core-llm-contract-identity-check-asks-presence-not-override`.

⚠ **CORRECTION 2026-09-13, and the correction is the point.** *"a change to a
published signature"* above is **FALSE**, and it was repeated into a
`pending_designs` entry and a next-chat prompt before anyone read the `def`.
`verify_transport` already takes `failing_transport`, `garbage_transport` and
`wrong_type_transport`, each `Any = None`, so a fourth probe keyword is
**additive and backward compatible**. The real cost is a new check NAME in a
report consumers read. The finding above stands as written — it is a dated
record of what this ship saw; only its COSTING was wrong.


## Amendment 3 — the scope is a plan file, and L3 writes the L2 record (2026-09-13)

**Amendment status:** Accepted. The decision above stands. This records two owner
rulings that change *what is left to build* and *who owns that question*.

**The scope of `mindsos_llm` now lives in `docs/plans/MINDSOS_LLM_PLAN.md`**, and
nothing else may state it — pinned by
`tests/architecture/test_mindsos_llm_plan_is_the_scope.py`. The 2026-09-05 ruling
that "complete" means the capability table is **superseded**: all eleven of its
rows pass, and the module is not finished, because that table answers *what a
consumer can DO* rather than *what is left*. The end state the owner chose is **a
removable stand-in** — every conclusion that leaned on the borrowed model can be
identified as such, shown (including what was asked), and re-run without the model
once MindsOS reads text itself.

**`core-llm-recorded-set-l2-pointer-owner` is RULED: L3 writes the L2 record**, in
the owner's words, *"this is part of the reading text intelligence, not L0 server
code."* L0-writes-it is rejected. Four rulings follow from it and are recorded in
full in the plan's §2:

* `mindsos_knowledge` **holds** the record; `mindsos_capacity` **writes** it;
  `mindsos_llm` is in neither and may not import either.
* The capacities join the existing **`comprehension`** family, **not** a new `llm`
  family — a family named for the borrowed model names the crutch rather than the
  work, and goes wrong the day the stand-in is removed.
* **L4 decides when a record is needed**, so recording is a capacity L4 routes to,
  not a declared output of every reading: a recorded set spans sessions.
* ⚠ **The recorder consumes the reader's ANSWER, never the vendor.** It must never
  build a client. `EXPECTED_EXTERNAL_CLIENT_CONSUMERS` holds exactly one entry; a
  second would give a bookkeeping step the failure modes of a model call — an
  outage, a ceiling, an answer that will not decode.

⚠ **Why this sat open for eight days:** Rule 1 turns a question with no present
consumer into a *trigger*, and every chat after 2026-09-05 was therefore required
not to decide it. **A question the OWNER must answer is not subject to Rule 1.**

## Amendment 4 — the L2 record shape and the recorder's contract (2026-09-14)

**Amendment status:** Accepted. The decision above stands. This records plan item
I-8 — what `mindsos_knowledge` stores, who writes it, and one correction to
amendment 3's scope wording. The item list and the order live in
`docs/plans/MINDSOS_LLM_PLAN.md`.

**THERE ARE TWO L2 RECORDS AND THEY ARE NOT WRITTEN BY THE SAME PATH.** Amendment 3
named one owner for both. Measured, they have different authors and different
lifetimes.

**1. The prompt edition is AUTHORED, not recorded — and it reuses the `policies`
role graph.** No new role. `mindsos_knowledge/schemas/policies.py` already makes the
argument in its own words: *"`in_force_from` / `in_force_to` / version / text is the
**same** shape for a statutory dollar threshold and for a versioned prompt body, and
that generality is the entire argument for the role existing."* A prompt edition is a
`PolicyEdition` whose `policy_id` is the `prompt_iri`, whose `edition_id` and
`version` carry the `prompt_version`, and whose node payload (`value`) is the prompt
text. A conclusion stamped `prompt_iri` + `prompt_version` resolves against exactly
that node.

⚠ **The recorder cannot write it, and no run can.** Measured: the transport signature
is `(prompt_iri, prompt_version, source_text, extraction_schema, timeout_s)` — **no
prompt text crosses the seam**, so it is in no answer and reaches no L3 body. A prompt
edition enters L2 the way every other authority does: authored, admin-gated in Global,
or written Local as a trial. **I-9 is an authoring-and-resolution path, not a recorder
concern**, and it depends on this amendment only for the role decision.

**2. CORRECTION to amendment 3 — prompt editions are DUAL-SCOPE; only recorded sets
are Local-only.** Owner ruling, 2026-09-14. The Decision section's *"Local only, never
Global"* attaches to the recorded set — as the Consequences section already states it,
*"Recorded sets are never Global"* — and **not** to prompt text. A prompt body held
Local-only cannot be shown to anyone but the user whose own reading produced it, which
defeats this module's end state for every shared or exported conclusion. `policies` is
already bootstrapped in **both** realms under one `append_only` schema: Global
`admin_authored` (a curated prompt library), Local a per-user trial before anything is
shared. **L3 cannot write Global**, so the asymmetry needs no new gate.

⚠ **`append_only` is DECLARED, NOT ENFORCED** — `schemas/policies.py` says so outright
(`validate_mutation_discipline` is uncalled system-wide). A prompt edition can be
overwritten today, so *shown* currently means **retrievable, not verifiable**. ⚠ **A
digest cannot close this from the answer side**: the text never crosses the seam, so no
client can stamp one, and a digest stored beside the text it describes proves nothing.
Filed rather than guessed, as `core-llm-prompt-edition-append-only-unenforced`.
**Re-open trigger: a consumer must prove a shown prompt is the one that ran.**

**3. The recorded set is a POINTER NODE in a new Local-only role, `recorded-sets`.**
⚠ **Its property list is SUPERSEDED by amendment 6** (no `set_id`, `vendor_id` or
`captured_at`; `credential_level` derived). The role and the payload stand.
One NodeType, `RecordedSet`; no edge types — the `learned-parameters` /
`learned-pipelines` / `policies` zero-edge shape. Discipline `append_only`: a capture
is never rewritten, and a re-export is a new node.

* **Properties**, the queryable scalars: `set_id`, `file_uri`, `sha256`, `responses`,
  `key_schema_version`, `captured_at`, `recorded_by`, `credential_level`, `vendor_id`.
* **Payload** (`value`, `StorageMode.FALKOR_BLOB`): the **derived manifest** plus the
  sorted `request_keys`. ⚠ **The keys are load-bearing.** A stored conclusion carries
  `request_key`; the manifest as shipped carries counts, identities and prompts and
  **no keys at all**, so without them a pointer cannot be resolved *from a conclusion*
  and I-12 has nothing to stand on. Keys are hashes and a set of any size exceeds
  `INLINE`'s ~4 KB, which is what `FALKOR_BLOB` exists for (ADR-0151).
* **Never Global**, unchanged — one user's readings are not another's knowledge.
  Reproducibility stays with `export_set` / `import_set`.

**4. The recorder's contract.** ⚠ **Its input, derivation path and don't-know are
SUPERSEDED by amendment 6** (`credential_level` leaves the input; the file is read by
`describe_set`; the recorder refuses and has no don't-know). The rest stands.
`capacity:comprehension:record_reading_set` — the
**`comprehension`** family per amendment 3, never an `llm` one.

* **Input** — one record DataState, `core.reading_set_record`: `set_path` (str),
  `recorded_by` (str), optional `note`, optional `credential_level`.
* **Output** — `(recorded_set_iri,)`. **Declared, NOT a write terminator.**
  `learn_parameter`'s `outputs=()` is the write-terminator precedent and it is the
  wrong one here: the question this ADR carried for eight days rejected L0 precisely
  because *"nothing in the run graph then names the set"*. A declared output grounds
  the pointer the way `origin_record_iri` grounds a reading.
* **The manifest is DERIVED in the body, never supplied** — `RecordingStore.from_path`
  then `mindsos_llm.recorded_sets`' deriver. ⚠ **This IS amendment 3's "consumes the
  reader's answer", not a way around it:** a recorded set's payloads *are* the answers,
  stamped by the client at capture time. What the rule forbids is asking the vendor
  again, and nothing on this path can — the deriver opens a file. A supplied manifest is a claim about a
  recording instead of a property of it, which that module refuses by design.
* ⚠ **This does not make the recorder an external-client consumer.** Measured:
  `test_external_client_consumer_census_is_exact` keys on `context.llm`, not on
  importing `mindsos_llm`. `comprehension_v0.py` is already the one legal
  `L3 -> mindsos_llm` import; a second, to `recorded_sets`, builds no client and
  reaches no vendor. `EXPECTED_EXTERNAL_CLIENT_CONSUMERS` stays at one entry, and
  amendment 3's rule holds in substance — the recorder records what **was** produced,
  not what it can ask for again.
* **Write path** — `context.writeable(...)` -> `KLWriteHandle` per ADR-0180, exactly
  `learn_parameter`'s shape: the body holds no session and makes no authorization
  decision. **Always `scope="local"`.**
* **L4 routes it** (amendment 3): not a declared output of a reading, because a set
  spans sessions.
* **Don't-know** — the `comprehension` family's shape is `OPTIONAL_RETURN`, which the
  declared output makes coherent: nothing to record is a null `recorded_set_iri` with
  the reason on the paired record. ⚠ **`family_rule_for` has no caller in any shipped
  module**, so this is a documented contract and not a gate; this amendment does not
  pretend otherwise.

**Against the end state.** ⚠ *Shown* below names a `PolicyEdition` — **withdrawn by
amendment 5**: a prompt is a `PromptEdition` in the `prompts` role. *Identified*: already — `origin_producer_kind`
`document_reading` and `origin_method` `read_by_model`, widened by I-11. *Shown*: the
`PolicyEdition` the conclusion's `prompt_iri` + `prompt_version` name. *Re-run without
the model*: the conclusion's `request_key`, the `RecordedSet` payload that lists it,
and `ImportedSet.replay_config` off the file the pointer names. ⚠ **SUPERSEDED by
amendment 7** (plan R19): re-run means re-derive with a producer that does not consult
the model; replay is not excision.

## Amendment 5 — the prompt store is its own role; amendment 4 clause 1 is WITHDRAWN (2026-09-16)

**Amendment status:** Accepted. The decision above stands. This corrects amendment
4, which is otherwise unchanged: its recorded-set half, its recorder contract and
its dual-scope ruling all hold.

**WHAT IS WITHDRAWN.** Amendment 4's clause 1 said a prompt edition reuses the
existing `policies` role graph and is *"AUTHORED, not recorded — the recorder
cannot write it, and no run can"*. **Both halves are withdrawn.**

**(a) `policies` is a consumer's store, and this module is generic.** The policy
role was created by the Decision Records CR, and `identifiers.py` states in the
same breath as the shape argument that *"a policy is an authority a decision
cites. That is not cosmetic here: a Decision Record states which authority, which
edition, in force when, so the store's identity is part of the claim being
made."* `mindsos_llm` is a stand-in for reading text with a borrowed model, for
**any** consumer; borrowing a store whose identity belongs to one of them leaves
a prompt indistinguishable from an authority to anything enumerating that graph,
with an id prefix as the only separation. Amendment 4 took the shape argument and
ignored the identity argument on the same page.

**(b) "no run can write it" does not follow from the measurement.** It is true and
remains true that **no prompt text crosses the transport seam** — the call carries
`prompt_iri`, `prompt_version`, `source_text`, `extraction_schema`, `timeout_s`.
What follows is only that the text is in no ANSWER. **Plan ruling R2 says L3
writes what L2 holds**, and an L3 write capacity receives the text as an INPUT
record, exactly as `learn_parameter` receives a value it did not compute.

⚠ **Why this is recorded rather than quietly fixed.** Amendment 4's clause 1 cited
nothing. Each of R1–R6 is a plan ruling with an owner and a date; that clause was
neither, and it was written because a design question was answered by looking for
a matching shape in the tree instead of by reading the plan. **Measurement
verifies a claim; it cannot generate a decision.** The plan already held the
answer.

**THE SHAPE, per R2 and R3.**

* **`prompts` — a role of its own**, dual-scope (Global the curated library,
  Local a per-user trial, per amendment 4's owner ruling, which stands). One
  NodeType `PromptEdition`, no edge types, `append_only`. The node's **payload is
  the text**; `prompt_iri` and `prompt_version` are properties **and** the node's
  address, so a stored conclusion resolves its own prompt with no other lookup.
  The closed role-set moves **17 → 18**.
* ⚠ **One conversion, named once.** `prompt_version` is an `int` on every answer
  and a string inside an IRI. `mindsos_knowledge.prompts.edition_id_for` is the
  only crossing, used by both the writer and the reader; a second `str()`
  elsewhere is how a write of `3` and a read of `"3"` come to miss silently, and
  the miss reads as *"never stored"* rather than as *"asked in a different
  alphabet"*.
* **`capacity:comprehension:write_prompt_edition`** — the `comprehension` family
  per R3, input `core.reading_set_record`'s sibling `core.prompt_edition_write`,
  `outputs=()` (the `learn_parameter` write-terminator precedent), writing through
  `context.writeable` at `scope="local"`. It never touches `context.llm`.
* **A missing edition REFUSES.** Every conclusion written before this role existed
  names a version that was never stored; the store says so rather than returning
  the nearest version. A reader shown a prompt that is not the one that ran has
  been told something false.

⚠ **`append_only` is still DECLARED, NOT ENFORCED** — unchanged from amendment 4,
still filed as `core-llm-prompt-edition-append-only-unenforced`. The writer's
duplicate refusal is the only enforcement there is, so *shown* means retrievable,
not verifiable.

## Amendment 6 — the recorded set as I-10 builds it; amendment 4 clauses 3 and 4 CORRECTED (2026-09-20)

**Amendment status:** Accepted. The decision above stands. This transcribes plan
rulings **R8, R9, R10, R12** (OWNER 2026-09-18) and **R13–R18** (delegated by the
owner 2026-09-20) into the ADR that amendment 4 left contradicting them. Amendment
4's recorded-set half otherwise holds: a Local-only `recorded-sets` role, one
NodeType `RecordedSet`, zero edges, `append_only`, the sorted `request_keys` in the
payload, and a recorder that declares its pointer as an output.

**WHAT IS CORRECTED IN AMENDMENT 4** — superseded here, not rewritten there; the
record of what was ruled first stays readable.

1. **Clause 3's property list.** `set_id`, `vendor_id` and `captured_at` are gone.
   `set_id` would be a second spelling of the identity R8 makes the file's
   `sha256`; `vendor_id` is stamped by nothing and checkable by nothing (R9);
   `captured_at` is a claim about the recording that no payload carries, where
   `recorded_at` is a fact about the write (R16, R9's rule). The properties are
   `sha256`, `file_uri`, `responses`, `key_schema_version`, `recorded_at`,
   `recorded_by`, `storage_mode`, and — only when present — `credential_level`
   and `note`.
2. **Clause 4's input.** `credential_level` leaves `core.reading_set_record`
   (R15): it is DERIVED from the payloads (R9), and a supplied value beside a
   derived one is the falsifiable field R9 removed `vendor_id` for.
3. **Clause 4's don't-know is WITHDRAWN** (R10). A file that is not a recorded set
   refuses; the recorder reads nothing, so it has nothing to be unsure of. The
   `comprehension` family keeps `OPTIONAL_RETURN` — that is the READER's shape,
   and this amendment does not touch it. ⚠ R10's *"the reason is not lost"* holds
   on one condition, measured: `runtime.invoke` emits the problem-trace record only
   when both a sink and a `request_id` are present.
4. **Clause 4's derivation path.** Not `RecordingStore.from_path` in the body, but
   **`mindsos_llm.recorded_sets.describe_set(path)`**, public (R12, R13). It reads
   the file ONCE, hashes those bytes, detects `format` (R12), loads a bare map
   through `RecordingStore` or an export through `import_set` — which already
   refuses a manifest that does not describe its responses — and returns the
   derived facts. It is named for what it DESCRIBES, a file, not for the L2 record
   that file feeds. The capacity body makes no filesystem call: measured before
   I-10, `mindsos_capacity` and `mindsos_knowledge` contained none, and they still
   do not.

**THE SHAPE, AS BUILT.**

* **Identity** (R8, R14): the node address is `recorded-sets-<v>:set:<sha256>`
  and `sha256` is also a property — the `prompts` precedent, where the address
  fields are properties too. The hash is over the FILE's bytes, so the same
  responses held as a bare map and as an export are two files and two pointers.
  A re-capture of the same bytes REFUSES (R18, `PromptEditionExistsError`'s
  shape): `append_only`, and the identity is the content.
* **`file_uri`** (R18) is the resolved absolute path `describe_set` opened — never
  a caller's argument, so a pointer cannot name one file and hash another — with
  no scheme: nothing parses it, and a scheme would imply a resolver that does not exist. Portability
  is the export's job, not the pointer's.
* **`credential_level`** (R9, R15) is derived and refused on contradiction or
  multiplicity. ⚠ **This is new work, not reuse:** R9 called it *"the rule
  `export_set` already enforces"*, and measured that is half true — `export_set`
  refuses only a SUPPLIED level that disagrees; with none supplied, a multi-level
  set exports silently. `describe_set` refuses it. A set whose every payload
  predates decisions 5 and 6 stamps nothing, and the property is omitted.
* **Payload** (R17): a `dict` — the derived manifest (`responses`,
  `key_schema_version`, `identities`, `prompts`) plus the sorted `request_keys` —
  which ADR-0182's codec encodes into `_value_json`. `storage_mode` is declared in
  `STORAGE_MODE_FIELDS` AND written on the node; `prompts` declared it and never
  wrote it.
* **The recorder** (R7, amendment 4): `capacity:comprehension:record_reading_set`,
  `writes=True`, `outputs=(core.recorded_set_pointer,)`, writing through
  `context.writeable` at `scope="local"`, with its installer in the same module
  (I-16's guard requires it).

**What *shown* means here** (R8): **verifiable.** Re-hash the file `file_uri`
names and compare it with `sha256`. A prompt edition is only retrievable, because
its `append_only` is declared and not enforced
(`core-llm-prompt-edition-append-only-unenforced`).

**For I-12 — measured, and forced by the shape.** ⚠ **SUPERSEDED by amendment 7:**
this paragraph prescribed I-12's lookup without a ruling, and plan R19 makes it
unnecessary — I-12 re-derives and reads no recorded set. The measurement stands:
getting from a conclusion to its set is a DECODE SCAN. Property bags are primitives-only, so the sorted keys cannot
be lifted out of the payload, and ADR-0182 rule 5 makes a JSON-encoded value
opaque to Cypher. I-12 scans the role's nodes and binary-searches each decoded key
list; the role is Local and per-user, which bounds it.

**Filed, not built:** `core-llm-recorded-set-has-no-file-writer` — nothing in the
tree writes a recorded-set file (`CapturingLLM` fills a store in memory; `export_set`
has no caller outside tests), so the file a pointer names is operator-produced today.

## Amendment 7 — excision is re-derivation, and an answer names what was asked by content (2026-09-21)

**Amendment status:** Proposed — I-17 and I-12 of `docs/plans/MINDSOS_LLM_PLAN.md`
flip it to Accepted as each ships. The decision above stands. This transcribes plan
rulings **R19–R28** (R19, R20, R21 and the I-17 split OWNER 2026-09-21; R22–R28 ruled
against the plan's §1 end state, each citing its authority there).

**WHAT CHANGES.**

1. **Re-run means RE-DERIVE** (R19). The conclusion's value DataState is produced
   again from the same source text by a producer declaring `consults_llm=False`
   (R25), and compared with the stored value (R28: L4 locates and dispatches, L3
   compares). Replaying a recorded answer is reproducibility, not excision.
   Amendment 4's *"Against the end state — re-run"* and amendment 6's *"For I-12"*
   paragraph are superseded in place.
2. **Shown is VERIFIABLE for all of what was asked** (R20), superseding amendment
   6's *"a prompt edition is only retrievable"*. ⚠ **Measured:** the words sent come
   from a `resolve_prompt` the deployment injects into the adapter, and nothing ties
   it to the `prompts` role; the extraction schema is recorded nowhere; `LiveLLM` and
   the adapter each hold their own model and temperature. So the fix is not
   `append_only` enforcement — it is making the answer name its question by content.
3. **The transport receives everything the model receives** (R21) — prompt words,
   schema, tool name and description, model, temperature, `max_tokens` — and adds
   only wire syntax and the credential. *"The transport sends exactly what it was
   handed"* is added to `UNVERIFIABLE_PROPERTIES` by name. ⚠ This changes the
   transport signature for every consumer and the checks behind contract rows 7, 9
   and 10.
4. **`request_key` v2** (R22) hashes the prompt digest, the schema digest, the
   framing, the model settings and the source text; `KEY_SCHEMA_VERSION` bumps and a
   v1 set misses loudly. The origin record carries the schema text and both digests
   (R23), and *shown* is verified by recomputing the key (R24).
5. **Domain** (R27): a conclusion in a persisted Episode's grounding graph — the only
   place its source text lives. Guarded by
   `tests/llm_seam/test_a_reading_reaches_its_source_text.py`.

**What does not change.** `mindsos_llm` still holds no L2 record (R2); a digest is
never stored beside the text it describes; the recorded-set role (am-6) stands and
keeps serving replay.

**I-17's build rulings — plan R29–R35 (2026-09-22).** Ruled by the I-17 chat against
the plan's §1, each citing its authority in the plan.

6. **The transport call** (R29) is `prompt_text`, `source_text`, `extraction_schema`,
   `tool_name`, `tool_description`, `model_id`, `temperature`, `max_tokens`,
   `timeout_s` — and **not** `prompt_iri` / `prompt_version`. The adapter is built
   with wire configuration only (credential or broker, endpoint, opener).
   ⚠ **This supersedes amendment 4's measurement *"no prompt text crosses the
   seam"***, which was true and was the defect. Its guard,
   `tests/architecture/test_adr_0210_am4_l2_record_shape.py`, is **repointed, not
   deleted**: the words must cross and the name must not. Amendment 5's
   consequence stands — a prompt edition is still written as an input record; an
   answer carries a digest of the words, not the words.
7. **`request_key` v2 hashes content only** (R30); **replay poses its question by
   digest** (R31) — the deployment's own replay hashes its current words, a third
   party's `replay_config` supplies digests and framing derived from the set, and a
   set with more than one framing refuses.
8. **The framing is stamped and recorded** (R32): `tool_name`, `tool_description`,
   `max_tokens`, on the answer and on the origin record.
9. **An undecodable answer's refusal names what was asked** (R33): the client's
   stamps travel on `MalformedResponse`.
10. **`key_schema_version` is derived** (R34), per answer; unstamped means `"1"`,
    a mixture refuses.
11. **`model_version` is a configured label** (R35), not a fact about the call.

**Build state.** I-17 ships in three gates: (1) the seam, clause 6 — **built,
PR #242**; (2) clauses 4 (the key and the answer's stamps), 7, 10, and the
client halves of 8 and 9 — **built, I-17 gate 2**; (3) the origin-record half of
clauses 4, 8 and 9. The amendment stays **Proposed** until I-12 ships,
because clauses 1 and 5 are I-12's.
