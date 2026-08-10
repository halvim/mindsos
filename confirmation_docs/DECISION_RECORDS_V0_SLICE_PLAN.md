# Decision Records — Vertical Slice: build handoff

**For:** a new build chat · **From:** the Decision Records planning chat · 2026-08-08
**Read first:** `confirmation_docs/DECISION_RECORDS_DEMO_PLAN.md`,
`confirmation_docs/_to_delete/_LLM_ADAPTER_CONTRACT_COORDINATION.md` (all four replies).
**Basis:** `origin/main` `476444e` (pinned below; original audit basis `5c6c5db`).

---

## PIN — build against exactly this, and assert it

**Core moves under this slice. Pin, build, then catch up — never mid-build.**

| | Pin (set 2026-08-08) |
|---|---|
| Core base | **`origin/main` `476444e`** |
| Seam | **`feat/decision-records`, rebased onto `476444e`** |

**Why `476444e`.** Four commits landed after the `5c6c5db` audit basis, in two batches, and
both land on this slice:

- `3a3b30f` — **`mindsos_capacity/admission.py`**, a new module *both finders* consult
  before taking a capacity, plus `pipeline.py`. **The day-one route check tests exactly
  that layer.**
- `8400d6f` (#122) + `476444e` (#123) — **the Local-preferring union finder view**. A Local
  capacity now composes with a Global one, and the Local-then-Global retry is retired: one
  session-scoped find, **one verdict** instead of two.

**The rebase is free — verified, not assumed.** The seam branch is 2 commits over 27 files
and has **zero file overlap** with anything main changed in `54ee88c..476444e`. Nothing can
conflict.

**Re-verified at `476444e`, so the two findings below still stand:** `_select_finder` is
**unchanged** and still keys off start arity (D-A open), and `admission.py` is still the
layer the route check interrogates.

**Assert the pin, do not assume it.** A claim about state is a claim you have read. Put a
`test "$(git rev-parse --short HEAD)" = "<sha>"` guard in the same command box as any gate
run, or a stale checkout will hand back a green that means nothing.

**The one permitted exception to the freeze:** the seam code has **never been gated** — 48
cases hand-verified, no pytest. If its first Linux gate forces changes, those land and the
pin moves once. Nothing else moves until v0 succeeds.

**After v0 succeeds**, rebase onto whatever main has become and deal with the drift then.

*(Superseded note: an earlier revision said "do not put v0 behind
`feat/capacity-two-tier-resolution` — 85 commits behind, meaningless gate." That
characterisation was inherited second-hand and was stale. The work landed as
`feat/capacity-union-view` off `54ee88c`, +788/−49, and merged as #122/#123. It is in the
pin.)*

---

## The one rule that decides whether this succeeded

**The route must be composed by the finder and executed through `execute_pipeline`.**
Not a script that calls capacities in order. Not a hand-assembled `Pipeline`.

`BRAIN_ARCHITECTURE_AUDIT.md` records arc1 registering a 1,032-line capacity topology over
a 3,756-line solver that never executed through it. If this slice is wired by hand it
reproduces that exactly, and every downstream number is a lie about the one thing being
sold. The L4 catalog capacities are placeholders, so `run_lifecycle` yields one milestone
and one pipeline — the finder still has to find the route *within* that pipeline, and that
is the whole test of claim 4.

---

## Scope: one criterion, end to end. Nothing wider.

**The criterion is a threshold against a dated, versioned limit.** Chosen over an
eligibility test because it is literally the money sentence — *"47 against a limit of 30,
from policy version 4, in force since 12 March"* — and because it exercises the three most
under-scoped items in one pass: the policy store, as-of lookup, and version-in-the-graph.

Eligibility ("which condition failed") is the **second** slice. Do not fold it in.

**Domain:** a real, dated, versioned statutory threshold — not claims. Claims content is
held until the practitioner conversation; tax is the evidence domain and is not blocked.
Pick the smallest real rule with a dated dollar amount. Do not invent one; a synthetic
criterion will not transfer.

**Named for v0 so nobody stalls choosing:** *a filer must file a return when gross income
reaches the filing threshold in force for their status and tax year.* Real, one comparison,
a dated dollar amount that changes by year — so it exercises the policy store, the as-of
lookup and version-in-the-graph without any statutory research. Adjacent to SARA's
§63/§151 territory, so it transfers when the evidence pack starts.

**Substituting an equally minimal dated threshold is fine.** v0 tests the mechanism, and
swapping the criterion later is one registration change and no code. Do not spend v0's time
on legal sourcing.

### Shape

- **1 document** DataState — the source text, minted as the grounding root by the run
  driver.
- **1 reader** (`comprehension.*`, from the seam chat's `register_reader` factory) →
  produces the scalar value + its **`<value>_origin`** record (`origin_record_iri()`).
  Register the value with a **real `ShapeDescriptor`** — `scalar("int")`, never opaque, or
  the reader will not coerce and `"about seven weeks"` passes straight through into a
  comparison.
- **1 lookup capacity** → consumes the policy id + the as-of date, produces **the limit and
  the policy version as separate DataStates**. Not read from context. `record()` writes
  only `(capacity_iri, input IRIs, outputs)`, so anything arriving via the context snapshot
  never reaches the derivation and fails the gate at step one.
- **1 decision capacity** — family `decision`, VERDICT shape (`FAMILY_RULES` already
  declares it; it has shipped and never been used). Output names the value, the limit, and
  the version.
- **1 renderer** → one page of prose from the persisted run graph and nothing else.

### DataState count

Every distinct value needs its own type — the blackboard is one value per DataState IRI
and `CapacityMMWriter.index[...]` overwrites. Expect roughly: document, as-of date, policy
id, the scalar value, its origin record, the limit, the policy version, the verdict.
**If you find yourself reusing a type for two values, stop — that is the nilm blocker.**

### Registration scope — **mixed realms, and they compose** (rewritten 2026-08-08, #122)

**The Local-only constraint is dead.** The Local-preferring union view shipped, so a Local
reader composes with a Global lookup in the same run. The earlier instruction — *register
the whole slice Local* — is superseded and should not be followed.

**Register by what each thing is:**

| | Realm | Why |
|---|---|---|
| Reader (`comprehension.*`) | **Local** | The seam trial's deliberate choice — nothing enters the Global catalog until the shape is proven |
| Policy store + lookup | **Global** | A policy is an authority, not a user's private data |
| Decision capacity | **Global** | Same |

Keep the scope a parameter anyway — it costs nothing and the realms will move.

**The risk this creates, and it is now live rather than hypothetical.** The union rule is
**SHADOW, not merge** (`views.py:216`): a capacity IRI registered Local hides the Global
capacity of that IRI *entirely* — its node and its `PRODUCES`/`CONSUMES` edges with it.
There is no per-edge reconciliation and no signal.

So a Local capacity registered at the policy lookup's IRI **silently replaces the
authority**, and the Record would name a limit from a source nobody chose. That is the third
of the three objections to `learned-parameters` — *a Local override silently shadows a
policy* — arriving at the capacity level instead of the parameter level.

**→ New guard G8.** Assert the policy lookup and the decision capacity resolve **Global**;
a Local shadow at either IRI is a loud failure, not a quiet preference. Cheap now, and it is
the difference between a confidently wrong Record and no Record.

*(Later refinement, not v0: rather than forbidding a Local override outright, record the
shadow in the origin record so the Record can say the limit came from a local override. Only
worth building once a customer wants one.)*

### The finder selects itself — and the collision this resolves

`_select_finder`: **more than one start ⇒ `ConjunctionFinder`, exactly one ⇒ `BFSFinder`**,
and BFS wires only the single `via` datastate it arrived on.

A single start (the document alone) would select BFS, and the decision capacity's three
inputs from three producers would be **silently dropped**. `policy_id` and `as_of_date` are
not values the Record attributes to a source, so they are legitimate starts:
**{document, policy_id, as_of_date} = 3 starts ⇒ ConjunctionFinder, automatically.** No
explicit override, and the as-of date lands outside the document where the replay key needs
it.

**This depends on a known-open core defect — D-A. Do not copy the pattern thinking it
generalises.** `_select_finder` keys off **start** arity, not **input** arity (defect D-A
from the map-member multi-input CR, re-scoped into CORE-C3). The three starts above work
*because there are three starts*, not because the decision capacity has three inputs. **A
future capacity with three inputs and a single start silently gets BFS and loses two.**
Recorded here so that when D-A is fixed nobody wonders why the starts were chosen this way.

**Day one, before anything else:** register the four capacities Local, ask the finder for
the route, assert it wires the decision's three inputs to their three producers. If
ConjunctionFinder cannot, every downstream item here is void.

**This check has no precedent on either side.** Nothing in the seam lane's
`tests/llm_seam/` has ever invoked a finder — every pipeline there is hand-built. The
package proves readers execute, ground and refuse *given* a pipeline; nobody has proved one
can be **found**. Run this before the policy store and before the decision capacity, and
report the result to both lanes.

**The route check is now a better test than it was.** Under #122 there is **one
session-scoped find over the union view**, and the Local-then-Global retry is retired — so
`ComposeFailed` carries **one** verdict, not two. That also removes the hazard flagged
earlier: a not-found no longer arrives as an ambiguous pair that reads like run 4.

Register the reader Local and the lookup/decision Global, exactly as the slice will really
run, and the check exercises the mixed-realm path rather than a v0 workaround.

---

## Five runs it must produce

The slice is not done until all five render.

| # | Run | Proves |
|---|---|---|
| 1 | Clean outcome | The route composes and executes; the Record names value, limit, version |
| 2 | Value absent from the document | Reading refusal — graph-resident, names the missing item in prose |
| 3 | No policy in force at that date | Lookup refusal — the limit itself is unavailable |
| 4 | Target unreachable (a required capacity unregistered) | `FindVerdict`, no pipeline, **no grounding graph unless the root is pre-minted** |
| 5 | Same case, two different dates | Different limits, different versions, both named |

Run 4 is the one that needs core work: mint the grounding root **before** the finder runs,
or there is no graph to render and claim 3's second half has nothing behind it.

Run 5 is the money sentence. Run 2 is the demo's punchline in miniature.

**Run 5 has a trap that will destroy it silently — amended 2026-08-08 on the seam chat's
catch.** The recorded-reading replay key hashes the **exact source text**. If the as-of
assessment date is interpolated into the document, the two runs have different text,
different keys, and the second misses; re-recording to fix it leaves two saved readings of
what is meant to be one document, and the demonstration quietly becomes *"different
documents give different limits"* instead of *"the same document at a different date gives
a different limit"* — which is the opposite of the point.

**Keep the as-of date out of the document.** It enters as its own DataState into the policy
lookup, which is what consumes it anyway. Then the reading is provably identical across both
runs and the date is the only thing that changed.

---

## Work items and their dependencies

### v0 scope (amended 2026-08-08 — owner steer: get an end-to-end slice testable)

**v0 is runs 1 and 2, and guards G2, G3, G7, G8.** Run 1 proves the route composes, executes
and renders from the persisted graph; run 2 proves refusal is graph-resident.

Deferred to v0.1, each because it needs machinery v0 does not: **run 3** (the lookup's
no-version path — `REFUSAL_NO_SOURCE_IN_FORCE` already exists in the seam's reason set),
**run 4** (root-before-find, a core change and the biggest lift), **run 5** (two policy
editions plus the replay-key discipline). G1 and G6 land with the renderer.

**G2 and G3 are not cuttable.** A v0 rendering a Record from anywhere other than the
persisted grounding graph is arc1 at small scale: it looks like success and proves nothing
about the only claim being sold.

**Independent of the seam — start immediately, off `origin/main`, registering Local:**

- **A. Policy store.** Append-only, `in_force_from` / `in_force_to`, read through a lookup
  capacity. **Not** `learned-parameters` — that is the *learned* store, and Local shadows
  Global per knob, so a user override could silently shadow a policy limit.
  Must hold **text, not just a version number** (the same store takes the seam chat's
  prompt bodies — see their Q4).
- **B. The decision capacity.** One criterion. Family `decision`, VERDICT.
  A generic `compare(number, number)` is **not** available: the finder is type-directed and
  a fully generic comparator would wire itself into unrelated routes. Type it to this
  criterion.
- **C. The run driver.** Mints the document as the grounding root before the finder runs.
  Currently owned by nobody — it is this chat's, and it is what makes G7 satisfiable.
- **D. Guards.** v0: **G2, G3, G7, G8**. Written **before** the renderer; each demonstrably failable. Wire `origin_v0.opaque_into_decision(capacity_layer, user_id=<local user>)` in — it is scope-aware, so pass the Local user id or it finds nothing and passes vacuously. G1, G4, G6 land with the renderer / v0.1.

**Waits on the seam branch being *pushed* — not merged (amended 2026-08-08):**

Merging to `main` means a full gate cycle plus review of core surface, for a slice that
exists to prove the shape. Branch E/F off `feat/decision-records` and run end to end as soon
as it is pushed; merge after the slice is the evidence for merging. The seam code is
readable now at `~/Documents/Claude/Projects/_dr-seam-staging/` at repo-relative paths.

- **E. Wire the reader in** and run v0's two runs end to end.
- **F. The renderer**, against the real graph the slice produces (not a fixture — a real
  one now costs the same and proves more).

---

## Guards

- **G1** Renderer imports none of: blackboard, capacity context, L2 snapshot, `Pipeline`,
  `chain_artifacts`.
- **G2** Remove one capacity instance from the graph → renderer raises, never fills the gap.
- **G3** No Record without the capacities having executed and written.
- **G4** Refusal present in the graph, both shapes. Exactly one *run-stopped* node per run;
  a reading refusal (a step that succeeded and produced no value) **composes with** it and
  is not double-counted.
- **G6** Rendered output contains none of: capacity, pipeline, DataState, metagraph, layer,
  verdict, IRI, or any `xxx:` form. Composes with the seam chat's
  `test_printed_phrases_carry_no_identifiers` — theirs guards what enters the record,
  G6 guards what leaves the renderer. Neither subsumes the other.
- **G7** Every `DataStateInstance` the Record attributes to a source has a path back to the
  grounding root. Catches the silent case: `seed()` mints with **no incoming edge**, so a
  value handed in as a start input is unattributable, permanently and quietly.
- **G8** The policy lookup and the decision capacity resolve **Global**. The union view's
  rule is **shadow, not merge** (`views.py:216`), so a Local capacity at either IRI replaces
  the authority entirely, with no signal — and the Record would name a limit from a source
  nobody chose. Loud failure, not a quiet preference.

---

## Renderer rules

- Prose comes from **registered** `description` on the DataState and Capacity, plus the
  seam chat's `origin_party_phrase` / `origin_method_phrase` / `question` / `quote`.
  A phrase dictionary inside the renderer is the hand-maintained mirror again.
- **Phrasing precedence: observed wins.** Phrase from `basis` when a reading was admitted,
  from `expected_basis` only when it refused. Phrasing from `expected_basis`
  unconditionally would make an expected/observed mismatch print as a lie.
- Never source the "why" from `rationale` on the shipped verdict types. It is a
  model-explanation-shaped field and has never been used.

---

## Definition of done

1. All five runs execute through the finder + `execute_pipeline` and render.
2. Guards G1–G4, G6, G7 exist, are green, and each has been shown red.
3. Gate green on Linux against the merged state.
4. One page of output a non-technical reader understands with no glossary.

---

## Explicitly out of scope

The other five decision ops · any claims content · SARA's nine sections · the batch
harness · Summary A/B · an HTTP API · a web UI · the CORE-C abstraction-levels build-out
(verified not to block this: the grounding graph uses **intra-graph** edges, so the C2R3
metagraph-boundary blocker does not apply here).

---

## Environment

- Worktree off the **seam chat's branch**, not `origin/main`, for items E and F.
  Items A–D can sit on `origin/main`.
- **Ask the owner to create the worktree.** One created from the Cowork sandbox records
  session-mount paths and cannot be removed from the Mac — see
  [[no-sandbox-git-mutations]] for the teardown order if it happens anyway.
- Cowork edits files; the Mac runs git; Linux runs every test. Device-side checks are a
  pre-filter only.
