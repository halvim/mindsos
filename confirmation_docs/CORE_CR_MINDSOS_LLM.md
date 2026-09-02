# CORE CR — `mindsos_llm`: LLM communication as a cross-layer core capability

**Branch:** `feat/mindsos-llm` (off `origin/main` @ `bb8614c`).
**ADR:** `docs/decisions/adr/0210-llm-communication-layering.md` (Proposed).
**STATE:** `pending_designs` entry `core-mindsos-llm-communication`.
**Version:** no bump. `core_version` stays `phase50` — the release-train
integer moves only on a numbered-phase ship.

---

## 1. The ask

A project that wants MindsOS to consult an external model currently has to
write the network-touching piece itself. `LiveLLM` takes a
deployment-supplied callable and that callable was never written in core.
One lane wrote it and hardened it through four adversarial rounds
(`decision_records_demo/dr_transport.py`, 419 lines, 14 guards, run live);
a second lane now needs the same thing and would otherwise copy it.

**Owner ruling: LLM communication is MindsOS machinery, not a project's
local concern.** Core ships the way any project calls a model, receives its
answer, and records the exchange. It spans layers:

| Layer | Owns |
| --- | --- |
| **L0** (`mindsos_server`) | The user's vendor choice, credential level, and credential custody. Released to L3 through a capability, never read ambiently, never written to the audit trail. |
| **`mindsos_llm`** (new top-level) | Adapters, the call, decoding, recording, replay, the credential seam. Substrate — registers nothing. |
| **L2** (`mindsos_knowledge`) | Prompt text and versions; the pointer and provenance of a recorded response set. **Local only, never Global.** |
| **L3** (`mindsos_capacity`) | The capacities L4 calls — one minted per reading. |
| **L4** (`mindsos_intelligence`) | Decides a reading is needed and routes to the capacity. |
| **L5** | Holds the answers. |

---

## 2. What this reverses, stated rather than discovered later

Three docstrings on `main` say a vendor never enters MindsOS:

* `mindsos_capacity/llm/live.py` — *"No provider SDK ships in this repo."*
* `mindsos_capacity/llm/contract.py` — *"§6.4: no vendor inside MindsOS,
  credentials in the transport's closure, the gate has no network."*
* `decision_records_demo/dr_transport.py` ¶1 — it lives outside core **by
  design**, for that reason.

**The invariant is restated, not quoted.** What was ever worth having is
this, and it survives:

> **No provider is baked in.** The adapter is selected at runtime from the
> user's stored vendor id; a second provider is a new adapter, not a change
> to core. Credentials are resolved at call time and scrubbed after; the
> gate acquires no network, no credential and no vendor dependency.

Two consequences that must not be discovered later:

1. `mindsos_capacity/llm/__init__.py` carries its own promotion trigger —
   *"a consumer outside the capacity layer, **or a vendor dependency
   arriving**. Either reopens placement: `git mv` plus the 9-site
   new-top-level-package checklist (PHASE_27 PB-29)."* This ship fires it.
   The package becomes top-level **`mindsos_llm`**, which is also the
   honest description: calling a model is used by more than L3.
2. **Any external material saying "no vendor inside MindsOS" is refutable
   the moment this merges** and must be rewritten to the restated form
   above before it is said again.

### What is NOT reversed

`falkordb` is already a hard `pyproject` dependency and
`mindsos_core/persistence/client.py` already imports a vendor SDK for the
other outside service — `mindsos_capacity/llm/__init__.py` names that
parallel itself. A vendor client living in core is not new here. What is
new is a *model* vendor, and the restatement above is what covers it.

### Terminology

**"Subsystem" does not appear in `mindsos_*` for this work.** `RULES.md` §8
defines a subsystem as a consumer that owns nothing architectural, and
`tests/architecture/test_no_subsystem_ownership.py` scans for the word.
This is core, spanning layers: a **cross-layer core capability**.

---

## 3. Decisions (owner-approved 2026-09-02)

| # | Decision |
| --- | --- |
| **1** | **One capacity per reading, minted by a factory** — not one generic `call_llm`. A single capacity makes every reading structurally identical, so L4 cannot distinguish "extract the income" from "extract the date" and cannot pick a route. The prompt is call-specific and travels with the minted capacity. Precedent: `comprehension_v0.build_reader`. |
| **2** | **Adapters live in `mindsos_llm`, not in L0.** L0 is auth, sessions, authorization and audit; giving it an outbound HTTP client to a model vendor is a new egress it has never had. L0 holds the *choice* and the *credential*, nothing else. |
| **3** | **A named adapter registry.** L0 stores a vendor id (`"anthropic"`); the adapter is resolved at call time. An import-time choice cannot satisfy "the user picks on first run and can change later". |
| **4** | **Core enforces the credential mechanism and states what it cannot verify.** Resolver-callable + always-returning header helper + `finally` scrub are enforced. `verify_transport` gains a named `unverifiable` entry saying it cannot confirm this from outside a transport it did not write. See §5. |
| **5** | **Mode (live / capture / replay) is stored per user at L0** and stamped on every answer. A mode chosen in code is a mode nothing records. |
| **6** | **The credential level (1/2/3) is recorded with each answer.** It is not a secret, and it determines how reproducible the answer is. |
| **7** | **The client is per session**, built after L0 resolves that user's vendor, level and mode. Different users have different vendors; one client built at startup cannot serve them. |
| **8** | **Recorded response sets are per-user L2 Local. NEVER Global.** |
| **9** | **Level 2 ships as a contract *and* a reference broker.** An option in the picker that nothing implements is dead. |
| **10** | **Slice order** — see §6. **Slice 1 is tagged independently** so the second consumer unblocks before the broker lands. |
| **11** | **ADR-0210, status `Proposed`.** |
| **12** | **No version bump.** |

---

## 4. The three credential levels

The transport asks for a credential at call time and scrubs after. It never
knows which level produced it. Each adapter declares which levels it
supports; L0's first-run picker offers only those.

* **Level 1 — never stored.** The credential lives in the user's OS keychain
  or environment. MindsOS fetches it through a callable, builds the header,
  scrubs the header after the call. It holds the value for one request and
  writes it nowhere.
* **Level 2 — never known.** A local broker the user runs holds the
  credential. MindsOS sends the request body to the broker; the broker adds
  the credential and forwards it. MindsOS never sees the value.
  ⚠ **This is not a resolver.** The credential never reaches MindsOS, so
  there is nothing to resolve — level 2 is a *wrapper around the adapter*
  that redirects the request, and it must be built as one. A design that
  models it as "a resolver that returns nothing" will be wrong at the seam.
* **Level 3 — reduced blast radius.** The resolver returns a short-lived
  scoped token instead of a long-lived key, so a leak expires.

### ⚠ Level 3 is a property of the ADAPTER, not of MindsOS

**Verified 2026-09-02 against vendor documentation.** Anthropic's direct
Messages API authenticates with a long-lived `x-api-key` header and offers
no token-exchange or expiring-credential flow. Short-lived credentials come
from the *hosted* routes to the same models — Bedrock (STS), Vertex (OAuth),
Azure (Entra) — which are **different adapters with different wire shapes**.

⟹ The Anthropic-direct adapter supports **level 1 only** and says so.
Level 3 arrives with a hosted adapter. The seam is credential-agnostic from
slice 1 so that costs nothing later: a resolver returning a static key and
one returning a rotating token are the same interface.

### ⚠ Level 3 collides with a rule already in the contract

`mindsos_capacity/llm/contract.py` lists `no_silent_retry` among the
properties a transport must have. A token that expires mid-run forces a
refresh-and-retry, which is **indistinguishable from the silent retry the
contract forbids**. Therefore:

* refresh happens **before** the call when the token is near expiry, never
  as a reaction to a rejection;
* a 401 is a **failure**, not a quiet second attempt.

A guard pins both, or level 3 ships a hole in the property core asserts most
loudly.

---

## 5. The credential property, and why core must not claim to verify it

`dr_transport.py`'s credential hygiene took **four review rounds, and each
round narrowed a sentence rather than a mechanism.**

1. The key was a bare closure free variable — live in frame locals on every
   raised link. The guard walked `str()` of each link, found nothing, and
   passed while the key sat one road over.
2. The proposed fix read the key through a callable, and the new guard was
   going to walk `str(local)` — but `repr(urllib.request.Request)` is
   `<urllib.request.Request object at 0x…>`, so the key would have been one
   attribute hop off the road the guard took, and the guard would have gone
   **green over it**.
3. Caught by the widened guard on its first run.
4. ⚠ **Caught only by running the DEFAULT opener.** Every credential guard
   injects a fake one, so the property had been asserted in exactly the one
   configuration where it holds. *Not a road the guard missed — a
   CONFIGURATION it missed.*

The three mechanisms that survived, and **none of them is the guard**:

1. `resolve_api_key` is a **callable**, so no frame binds the credential as
   a free variable.
2. Headers are built by a helper that **always returns**, so the frame that
   does hold the key is off every traceback before anything can raise.
3. The composed request's credential header is **scrubbed in a `finally`**.
   Every frame holds the *same* object, so one removal clears all of them —
   which is why this works where not-binding-it did not.

**Round four's lesson makes this externally unassertable.** A harness that
only *calls* a transport cannot reach the object that transport composed;
walking the traceback needs both the credential string and a forced failure
of the real transport, neither of which the harness controls. And any check
that injects an opener to get visibility **recreates round four's blindness
exactly**.

⟹ **Core enforces the mechanism and names the gap.** `verify_transport`
gains `credential_not_retained_on_the_composed_request` in
`UNVERIFIABLE_PROPERTIES` with the reason *"requires reaching inside the
transport; a harness that injects an opener asserts it in the one
configuration where it holds."* That file already established this pattern
for four §6.3 properties. An honest `unverifiable` line is worth more than a
guard that goes green over the key.

---

## 6. Slices

Each slice gates on the Linux box before the next begins.

**Slice 1a — the relocation, and NOTHING else.**
`git mv mindsos_capacity/llm mindsos_llm`. **Measured blast radius
2026-09-02:** 13 files import it (`context.py`, `dispatch.py`,
`comprehension_v0.py`, `origin_v0.py`, the package's own two, and 7 test
files), 21 Python references, 15 references in `.md`. A new top-level package
also makes it the **9th `__version__` site** — 8 packages carry one today —
which touches the doctor parity tests (`tests/phase_18/test_doctor_6pkg_parity.py`
and the phase 02/07/08/09/11/12 doctors).

⚠ **The gate expectation here is the OPPOSITE of the usual one.** A pure
relocation adds no tests, so **the pass count must NOT move**. The standing
rule — *"the count must move or the new tests did not run"* — does not apply
to 1a, and a flat count is the correct result rather than the tell of a stale
image. Verify instead that `--collect-only` still collects the same ids and
that `grep -c test_cli` is > 0.

**Why it is split out:** mixing a 13-file rename with new behaviour means a
red gate cannot be attributed to either. 1a is behaviour-free and therefore
cheap to prove.

**Slice 1b — seam + level 1 + Anthropic adapter + L3 factory. TAGGED.**
The credential seam, credential-agnostic. The Anthropic adapter, level 1,
ported from `dr_transport.py` **with its docstring intact** — that docstring
is the record of what was tried and rejected, and a shortened version invites
the rejected designs straight back. Its 14 guards come with it, running with
an injected opener: no network, no key. The L3 capacity factory. The
export/import path and the gate's test session from §7. Tagged
`mindsos-llm-slice-1-confirmed` so the second consumer unblocks here.

**Slice 2 — L0 custody.** Vendor id, level, mode and credential per user;
the capability that releases them; first-run and change-vendor flows. The
credential never enters the audit trail. Per-session client construction
lands here (decision 7).

**Slice 3 — level 3.** A hosted adapter with expiring credentials, explicit
pre-call refresh, 401-is-a-failure, and the guards pinning both.

**Slice 4 — level 2.** The broker contract, versioned, plus a reference
broker. The largest slice and the only one others implement against.

**Slice 5 — `verify_transport` properties.** No free-text fallback; a schema
declaring no top-level `properties` refuses loudly rather than refusing every
reply; unasked top-level keys refused, never stripped. Plus the
`unverifiable` entry from §5. **The core gate runs the harness against the
real shipped adapter with the network stubbed**, which no committed gate
anywhere has ever done.

---

## 7. Three additions to slice 1 that "never Global" forces

Decision 8 scopes recorded sets to a user's L2 Local. Three consequences,
each an addition to slice 1 rather than a reversal:

1. **Reproducibility needs an explicit export.** A set scoped to one user
   cannot be replayed by anyone else — which was the point of the replay
   path. A recorded set **exports to a file and imports into another user's
   Local**. Never Global, still reproducible by a third party with no key
   and no vendor account.
2. **The responses do not live *in* L2.** `RecordingStore` is a JSON map of
   `request_key` → payload; putting that in a metagraph turns every model
   answer into graph nodes. **L2 Local holds the pointer and provenance** —
   which set, when recorded, vendor, model and prompt versions — and the
   payloads stay a file the pointer names.
3. **The gate has no user.** Replay tests need a Local scope, so gate
   fixtures need a test session. Small, but it must exist before slice 1 can
   test replay at all.

---

## 8. What must not happen

1. **No trimming the ported docstring.** See slice 1.
2. **No silent repair layer, in any form** — fence-stripping, key-renaming,
   coercion, a free-text fallback, "just strip the extra keys". Every one was
   proposed and rejected with a reason recorded in that docstring.
3. **No claiming another lane's guards as core coverage** until they run in
   the core gate. Prose about a test is not a test.
4. **No credential in the L0 audit trail.**
5. **A token refresh is never a reaction to a rejection** (§4).
6. **Never mutate git from the sandbox.** Files are written here; the owner
   commits; the Linux box gates.

---

## 9. ⚠ Three stale surfaces this CR must not inherit

**Measured 2026-09-02, not reasoned.** The Decision Records repo pins
`policy-as-of-not-a-date-confirmed` → `96ba79d`, and
`git ls-tree` shows that tag **carries `mindsos_capacity/llm/`**. The pin
bump happened 2026-08-18 when the demo became its own repo
(`docs/STEP_3_HANDOFF.md:24`), the import ban was **deleted**, and step 3
imports `comprehension_v0` on purpose (`RUNNING.md`, *"what replaced the
import ban"*).

Three surfaces still say the opposite and were quoted as evidence into this
CR's own prompt:

* `dr_transport.py:17` — *"THIS BRANCH CANNOT IMPORT `mindsos_capacity.llm`"*
* `RUNNING.md:91` — the same claim
* project memory `external-model-seam` — *"the wager lane … is the first that
  could"* close the conformance gap

**All three are false.** The consequence for this CR: the conformance gap is
closeable in the Decision Records repo's own gate **today, with zero core
change**, and slice 5 is therefore about core asserting the *properties*, not
about being the first to run the harness. Per
`feedback-grep-before-quoting-any-prose`, the corrections land in the same
ship as the work that found them — the two demo-side surfaces as a demo-lane
edit, the memory in this session.

---

## 10. Process

Cowork writes; the Mac commits and pushes; the Linux box gates. Gate:

```
docker compose -p mindsos-core --profile test run --rm --build mindsos-test pytest -q
```

`--build` is mandatory (the image bakes source via `COPY`). Baseline ~4896;
**the pass count must move by the number of new tests or they did not run** —
**except slice 1a, where a flat count is the correct result** (see §6).

⚠ `feat/mindsos-llm` was created with `git worktree add -b … origin/main` and
therefore **tracks `origin/main`**. The first push must be
`git push -u origin feat/mindsos-llm`, or a bare `git push` targets `main`.

Re-run the skeptical multi-pass analysis on every plan change **and after
every completed slice** — pass summaries first with no pushbacks inside them,
then the pushback list, then decisions with Pros / Cons / choice, then next
steps. Stop after two consecutive passes with no decision reversal.
