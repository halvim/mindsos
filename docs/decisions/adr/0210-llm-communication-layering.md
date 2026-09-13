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
