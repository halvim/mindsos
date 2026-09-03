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

⚠ **CORRECTED 2026-09-02 WHILE DOING IT — this CR's own earlier claim that
"the pass count must NOT move" was WRONG, and it was wrong for the most
interesting possible reason.**

`tests/phase_28/test_import_isolation_phase_28.py` walked the seam's modules
through `_ISOLATED_SUBPACKAGES = ("llm",)`. The rename empties that tuple, so
its glob returns nothing and **10 parametrized tests silently vanish** (5
non-underscore modules × 2 forbidden roots) — and its
`test_every_subpackage_is_CLASSIFIED_not_merely_listed` goes **RED** on
`assert shipped, f"{sub!r} is declared isolated but has no modules"`. That
file's own docstring predicted this to the digit: *"reverting to the flat glob
turned no test red, it just quietly checked **ten fewer things**."*

**So a "pure relocation" is not behaviour-free at the guard layer**, and a
flat count would have meant a guard had been switched off by a rename. The
guard is re-established in the same ship at
`tests/llm_seam/test_import_isolation_mindsos_llm.py`, **wider than the one it
replaces**: 5 modules × 4 forbidden roots (`mindsos_server`,
`mindsos_knowledge`, plus `mindsos_capacity` and `mindsos_intelligence` —
substrate does not depend on the layers that consume it), plus a
domain-not-empty guard and the credential-owner-unreachable guard from §7c.

**Predicted delta: −10 + 22 = +12**, counted from the written test functions
and the module list, never recalled (`feedback-grep-before-quoting-any-prose`,
numeric corollary). Baseline ~4896 ⟹ expect ~4908. **A delta of anything but
+12 means something else moved — investigate before merging.**

⚠⚠ **TWO SITES THE 9-SITE CHECKLIST DOES NOT COVER, both found by the gate
and by running rather than by reading (2026-09-02).**

**(a) The Dockerfile needs a `COPY` in BOTH stages.** The image bakes source
via `COPY <pkg> ./<pkg>`, one explicit line per package, in the prod stage and
mirrored in the test stage. A package with no `COPY` line simply is not in the
image. The 9-site checklist is about *version* sites and says nothing about
this. **Every previous new-top-level package left a comment about it and the
lesson still did not carry.**

**(b) A RELATIVE import the absolute-path sweep could not see.**
`comprehension_v0.py:88` read `from ..llm.exceptions import MalformedResponse`.
Nothing matching `mindsos_capacity.llm` or `mindsos_capacity/llm` appears in
that line, so a text sweep for the old path found nothing, **and an AST scan
that filtered module names on `startswith("mindsos")` also found nothing** —
a relative `ImportFrom` carries `module="llm.exceptions"` and `level=2`. The
scan reported a clean `[]` and was wrong. ⟹ **After any package move, scan for
relative imports by `node.level`, never by the module string.** It is now the
only L3 → `mindsos_llm` import in the tree and is absolute.

⚠ **Both gaps were invisible to every local check that passed** — parity green,
ADR checker green, everything compiling, zero residual references. The suite is
what found them.

### Measured, not predicted

Run in the container pre-filter (uv venv 3.12, `pytest --collect-only`):

* `tests/phase_28` collected **145** with `llm/` restored and
  `_ISOLATED_SUBPACKAGES = ("llm",)`, and collects **135** now — the **−10** is
  measured against a simulated pre-move tree, not computed.
* `tests/llm_seam/test_import_isolation_mindsos_llm.py` collects **22**.
* Whole suite: **4932 collected, zero collection errors**; the affected suites
  (`llm_seam`, `origin_records`, `phase_28`, `architecture`, `phase_18`,
  `phase_02`, the server layer-isolation test) run **456 passed, 1 skipped, 0
  failed**.

⟹ **Net +12 confirmed. `origin/main` should collect 4920; this branch collects
4932.** Report container numbers as a prediction, never as a result (RULES §4).

### GATE RESULT — slice 1a is GREEN (2026-09-02)

`docker compose -p mindsos-llm --profile test run --rm --build mindsos-test pytest -q`
on `feat/mindsos-llm`:

> **4921 passed, 11 skipped, 1 xpassed, 0 failed** in 32:58.

4921 + 11 + 1 = **4933 outcomes** against the container's **4932 collected** —
the run is one ahead of the collect, which is the already-filed
`gate-baseline-count-off-by-one` item, not a new defect.

⚠ **What is NOT verified, stated plainly.** The `+12` is confirmed on both
sides of the move (`phase_28` collected 145 against a simulated pre-move tree
and 135 after it; the new guard collects 22) and the branch's own numbers are
internally consistent. It is **NOT** confirmed against a measured `main` gate:
the "~4896" baseline this CR first predicted from was a RECALLED number, which
is exactly what `feedback-grep-before-quoting-any-prose`'s numeric corollary
forbids — and `STATE.pending_designs` already carries
`gate-baseline-count-off-by-one`, whose own text says a recorded gate number
"is wrong by one and nobody can currently say which". **A green gate with zero
failures is the result; the delta arithmetic against `main` is not evidence
until `main` is collected.** One command closes it, and closing it also closes
that older item — expected **4920**, and whatever it says goes into `STATE`
either way:

    cd ~/mindsos-base && docker compose -p mindsos-base --profile test \
      run --rm --build mindsos-test pytest --collect-only -q | tail -2

**Why 1a is still split out:** mixing a 30-file rename with new behaviour
means a red gate cannot be attributed to either.

**The rest of the checklist, all done:** 21 Python references and the live
markdown ones rewritten; `pyproject` `include` and `manifest.toml` `packages`
extended; `mindsos_llm/__init__.py` given the 9th `__version__` (parity
verified across all 9 packages); `mindsos_llm` added to the package tuples in
`test_execution_surface_inventory`, `test_finder_return_annotations`,
`test_no_subsystem_ownership`, `test_retired_design_pointer`,
`test_rename_atomic`, `test_metagraph_snapshot_zero_consumers`, and
`_DOMAIN_PACKAGES` in `tests_server/integration/test_layer_isolation.py`.
`LLM_SEAM_MANUAL.md`'s name-redirect banner is **cancelled** — that ruling had
named its own expiry and the expiry fired — and ADR-0180's two path references
are updated with provenance. Three residual `mindsos_capacity/llm` strings
remain on purpose, all of them prose describing the move itself.

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

## 7b. ⚠ Two exact censuses will fire, and both must fire DELIBERATELY

**Found 2026-09-02 while sizing slice 1a**, in
`tests/architecture/test_execution_surface_inventory.py`. Two pinned sets there
are aimed squarely at this ship, and neither the CR nor the ADR anticipated
them.

### `EXPECTED_OUTSIDE_SERVICE_IMPORTS` — slice 1b reddens it, correctly

The census holds exactly two entries, both FalkorDB, and its comment names our
case by name:

> *"A third entry means a second one arrived; classify it or route it through a
> deployment-supplied seam, **the way the model client does** (the transport is
> a callable the deployment passes, so `mindsos_capacity/llm` imports **no
> network library at all** and is deliberately ABSENT from this census)."*

⟹ **The moment the Anthropic adapter imports `urllib.request` inside
`mindsos_llm`, `test_outside_service_import_census_is_exact` goes red.** That is
the guard working, not a break. Slice 1b **adds the row with its
classification**, in the same ship, per RULES §12.1 — and rewrites that comment,
because the sentence it rests on stops being true.

⚠ **The axis exists because of exactly this failure mode:** the file's own note
records *"a stub with live network IO dropped into the package left this file
6/6 green before the axis existed."* Do not silence it; classify it.

### `EXPECTED_EXTERNAL_CLIENT_CONSUMERS` — slice 1b reddens it too

One entry today: `comprehension_v0.py`. Its comment:

> *"A second entry means a second capacity consults an outside model. That is a
> design event — the declaration flag `consults_llm` was chosen over a category
> rule so this set stays enumerable — and it lands here with its row, not
> silently."*

⟹ If the L3 reading factory lands in a **new file**, that is a second entry and
a declared design event. If it extends `comprehension_v0`, the census is
unchanged. **Decide which before writing the factory**, because the census is
how that decision becomes visible.

### The relocation itself

`mindsos_llm` must be added to `_PACKAGES` in
`test_execution_surface_inventory.py` and `test_finder_return_annotations.py`,
to the scan tuples in `test_no_subsystem_ownership.py`,
`test_retired_design_pointer.py`, `test_rename_atomic.py` and
`test_metagraph_snapshot_zero_consumers.py`, and to `_DOMAIN_PACKAGES` in
`tests_server/integration/test_layer_isolation.py`. **This is the cost
`llm/__init__.py` warned about** — *"being a subpackage puts it automatically
inside the architecture guards' package tuples rather than requiring six hand
edits to be seen by them."* Miss one and the new package escapes that guard
silently.

---

## 7c. ⚠ `mindsos_llm` is a DOMAIN package: it never imports L0

`tests_server/integration/test_layer_isolation.py` enforces ADR-0010 §I-S1 — no
domain-stack package may import `mindsos_server`. `mindsos_llm` joins
`_DOMAIN_PACKAGES`, so:

> **L0 pushes into `mindsos_llm`; `mindsos_llm` never reaches into L0.** The
> session's vendor id, credential level, mode and credential **resolver** are
> injected at client construction. The LLM package cannot reach the server's
> secret store — it only ever receives a callable.

This was not stated in §3 and someone building slice 2 would reach for
`from mindsos_server import …` inside the adapter registry within an hour. It
also strengthens §5: the package that makes the call structurally cannot read
the store the credential came from.

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
**the pass count must move by the number of new tests or they did not run.**
Slice 1a's predicted delta is **+12** and is derived in §6 — a flat count there
would mean a guard was switched off by the rename, which is exactly what
`tests/phase_28`'s docstring warns about.

⚠ `feat/mindsos-llm` was created with `git worktree add -b … origin/main` and
therefore **tracks `origin/main`**. The first push must be
`git push -u origin feat/mindsos-llm`, or a bare `git push` targets `main`.

Re-run the skeptical multi-pass analysis on every plan change **and after
every completed slice** — pass summaries first with no pushbacks inside them,
then the pushback list, then decisions with Pros / Cons / choice, then next
steps. Stop after two consecutive passes with no decision reversal.
