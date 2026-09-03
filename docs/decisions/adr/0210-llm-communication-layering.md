# ADR-0210 — LLM communication is a cross-layer core capability: L0 holds the credential, `mindsos_llm` holds the wire, L3 mints one capacity per reading

**Status:** Proposed (2026-09-02). Owner-ruled 2026-09-02. Supersedes the
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
