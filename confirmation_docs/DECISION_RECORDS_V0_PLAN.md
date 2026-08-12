---
title: Decision Records v0 — the single-lane plan
status: IN BUILD. Owner-agreed D1–D6 on 2026-08-11. Items 1, 2 and 3 SHIPPED — see §2.0.
date: 2026-08-11
pin: RE-PINNED 2026-08-12 to origin/main fd6cefc. Written against af329eb; items 1–4 shipped
  through fd6cefc, and probe D ran against that tree (§2.3). Re-pin between items, never mid-item.
  seam feat/decision-records f7cb857 — see §2.3 decision 6, it is being archive-tagged
replaces: confirmation_docs/CORE_RECONCILIATION_PLAN.md as this lane's build order
reads with: confirmation_docs/DECISION_RECORDS_V0_HANDOFF.md (its §3 is amended here),
  CORE_CR_POLICY_ROLE.md, CORE_CR_EXTERNAL_MODEL_SEAM.md + LLM_SEAM_MANUAL.md (on the seam branch)
---

# Decision Records v0 — the single-lane plan

One lane owns core reconciliation and the Decision Records demo. This document is its build
order. It replaces `DECISION_RECORDS_V0_SLICE_PLAN.md` outright and amends
`DECISION_RECORDS_V0_HANDOFF.md` §3 where §1 below says so.

**Everything in §1 was read in the tree at `af329eb`, not inherited.** The handoff asked for
exactly that and said its own claims might not survive it. Two did not.

---

## 0. The ordering principle, and it is the thing that changed

**v0's critical path runs entirely on `main`.** The ungated LLM package is a later swap, not a
prerequisite.

The previous ordering put v0 behind `feat/decision-records` — a branch that has never been
gated, sits 23 commits behind, edits three core modules `main` has been moving, and depends on
a transport that does not exist. Nothing v0 must prove requires it.

---

## 1. What was verified at `af329eb`, and what it changes

### 1.1 HANDOFF §3.1 — the mechanism is real; the blocking claim is false

**True and confirmed.** `mindsos_intelligence/plan_construction.py::_read_solve_target` (:100)
and `::_read_leaf_target` (:188) each rebuild a dict holding only the singular
`start_datastate`, so a **planner-emitted** plan drops plural before `_select_finder` is
reached.

**False.** The handoff, `STATE.json`'s `decision-records-l4-multi-input-start` entry, project
memory, and `tests/decision_records/test_route_probe.py`'s own docstring all say the plural
`start_datastates` key has *no caller of any kind* — the docstring's exact words are
*"`_endpoint_starts` accepts plural; nothing can hand it any."*

`tests/phase_48/test_map_member_multiinput.py::test_plain_leaf_plural_starts_composes_multi_input`
hands it plural. It constructs a `PlanResult` directly with
`leaf_targets={"mLeaf": {"start_datastates": [DS_POS, DS_SIG_A, DS_SIG_B], ...}}`, calls
`execution.run(..., mm=mm, ...)`, and asserts the three-input capacity received all three. That
path is `_endpoint_starts` (`execution.py:164`) → `_select_finder` (:191) → `_compose_pipeline`
→ `ConjunctionFinder` → `_run_leaf_pipeline`, which passes `mm` to `execute_pipeline` and
therefore **grounds**. Three further tests in the same module exercise the plural key through
`shared_inputs` and a Slice-2 sub-plan. All are shipped and gated.

**Consequence for v0.** The run driver builds a `PlanResult` and calls `execution.run`. It needs
no core change, and it never calls the finder directly — so the RULES §8 objection the handoff
raised ("the GTM lane would own an L4 mechanism") does not arise. §3.1 is a real gap in the
*planner* path and is deferred; it blocks nothing here.

### 1.2 HANDOFF §3.2 — the mechanism is real; landed alone it breaks run 2

**True and confirmed, on both sides.** `mindsos_capacity/capacity.py::_validate_inputs` checks
declared-input presence, rejects unexpected keys, and validates `operand_arity` **length only** —
its own comment says *"core never inspects operand value types."* The output side is no better:
`call_capacity` reduces a returned mapping to `{iri: result[iri] for iri in outputs}` and checks
key presence alone. There is no value validation anywhere on either side, and no caller of
`ShapeDescriptor` performs one.

**But the proposed end state is unsafe in isolation.** In
`mindsos_intelligence/pipeline_execution.py::execute_pipeline`, the step loop calls
`writer.record(...)` **only after** the `if not result.success` early return. A cancelled step, a
failed step and a `needs_input` step all return before any write. So if core refuses `None` at
dispatch, the decision capacity never runs, the step fails, and **nothing reaches `capacity_mm`** —
the refusal becomes unrenderable. §3.2 would remove a confidently-wrong Record by replacing it
with no Record at all.

**Its true prerequisite is L-2** (§1.3). §3.2 is deferred and re-filed as blocked-on-L-2.

### 1.3 L-2 — the gap that is in no queue

*A capacity failure writes no node to the grounding graph.* Verified above. It appears in
`LLM_SEAM_MANUAL.md` §11.1 as **L-2**, in `DECISION_RECORDS_DEMO_PLAN.md` Phase 0 item 1, and in
project memory `decision-records-slice` item 6 — and in **none** of the handoff's six problems
and **none** of the six `pending_designs` entries opened 2026-08-10.

The seam closed the *reading* half by making a decline an ordinary successful return carrying an
empty value plus a filled origin record. The general half is open: any genuine failure — lookup,
decision, cancel — still leaves nothing. It is the largest v0-relevant core gap and it is
unowned. This plan owns it, as item 2.

### 1.4 The seam branch splits, and the origin half is free

`mindsos_capacity/builtins/origin_v0.py` (473 lines) imports exactly two things:
`typing`, and `..identifiers.parse_capacity_iri`. It is not exported from
`mindsos_capacity/__init__.py`. **Landing it edits no existing core module.**

`comprehension_v0.py` imports `origin_v0`; the dependency is one-directional. Everything with
sentinel risk lives in the other half — `context.py`'s 12th field (against
`tests/phase_42/test_typed_capacity_context.py::test_capacity_context_has_eleven_fields`),
`family_rules.py` moving `comprehension` out of `DEFERRED_DEFAULT_CATEGORIES` (5→4, pinned by
`test_phase_27_audit_doc.py`), `dispatch.py`'s category-based injection, and a new top-level
package `mindsos_llm` across `pyproject.toml`, `Dockerfile` and `mindsos_cli/manifest.toml`.

`CORE_CR_EXTERNAL_MODEL_SEAM.md` D16/S12 already ruled origin is core and *"core surface arriving
from a GTM branch is what RULES §8 exists to stop."* The split was never sequenced. It is item 1.

### 1.5 Two more corrections to the record

- **"48 cases hand-verified, no pytest" is misleading.** `tests/llm_seam/` is six pytest modules,
  1117 lines, 46 cases per the manual, including `test_reading_reaches_the_grounding_graph.py`.
  What has never happened is a **gate run**, and pytest has never been the runner. The first gate
  is a verification step, not an authoring job.
- **`CORE_CR_EXTERNAL_MODEL_SEAM.md` §5 is stale.** It states `pipeline._view_for` *"returns
  Global or Local and never both, so a Local trial means the whole path must be Local."* #122's
  union view killed that. It must not be cited when Layer B merges.

### 1.6 Unchanged, and still true

- **§3.3** — `capacity_layer.py::_mirror_global_datastates` (:742) copies Global→Local only, and
  runs only on the Local registration branch. A Global capacity cannot declare a Local DataState.
  The mixed-realm table is unbuildable as written; v0 registers all-Local.
- **§3.4** — `validate_mutation_discipline` is uncalled system-wide. `append_only` on the
  `policies` role is declared, not enforced. **Nobody writes "append-only policy store" in
  anything a customer reads.**
- **§3.5, §3.6** — as filed. Neither blocks v0.

---

## 2. Build order

### 2.0 Progress — READ THIS BEFORE PICKING UP AN ITEM

Five ships on 2026-08-11, every lane closed per RULES §10 (worktree removed, branch deleted
local and remote, both lists checked).

| PR | Squash | What | Gate |
|---|---|---|---|
| #142 | `512e975` | This plan, and the three corrections §4 owed | 4569 / 12 / 1x / 0 |
| #143 | `a310958` | **Item 1 ✅** — `origin_v0` + ADR-0207. Tag **`origin-records-confirmed`** | 4580 / 11 / 1x / 0 |
| #144 | `b325607` | `DECISION_RECORDS_DEMO_PLAN.md` revision + the owed ship records | none — docs + STATE |
| #145 | `c9754ac` | **Item 2 ✅** — L-2, the terminal node. Tag **`terminal-node-confirmed`** | **4591 / 11 / 1x / 0** |
| #146 | `cfc1795` | Demo beat: route **exposures**, not the claim | none — docs + STATE |
| #147 | `e7fd779` | Close-out: the plan doc had no progress markers | none — docs |
| #148 | `7c4c313` | **Item 3 ✅** — the policy lookup + the criterion, ADR-0208. Tag **`policy-lookup-confirmed`** | **4634 / 11 / 1x / 0** |
| #149 | `5f9c5cb` | **Item 4 ✅** — the run driver, through `execution.run`. **No tag: no `mindsos_*` touched** | **4645 / 11 / 1x / 0** |
| #150 | `fd6cefc` | The three probes, and RULES §10's close-a-lane command split in two | none — docs |
| #151 | *(squash)* | **Probe D**, and the three prose leaks it found. Tag **`prose-leaks-confirmed`** | **4652 / 11 / 1x / 0** |

**Baseline for the next item: 4652 passed / 11 skipped / 1 xpassed / 0 failed at PR
#151's tip `2560511`.** It is carryable — #151 was a **merged-state** gate (`merge-base
--is-ancestor` proved the tip contained `origin/main`, which had not moved from `fd6cefc`),
unlike `#138`'s 4551, which was a branch gate and is not. **This line has been stale twice:
it still read 4591 while the table above it recorded 4634 and 4645. Update it with the
table, in the same commit.**

**⏭ PROBE D HAS RUN — read §2.3, then the item table below, which it changed.** Items 1
through 4 are done; do not rebuild them. **Next is the capacity printable phrase, then the
run manifest, then item 5.**

⚠ **"Run 2 does not wait on item 5" was wrong, and ADR-0208's Consequences were right.**
Probe B ran run 2's *machinery* end to end, which is true and is why item 5 is small. But the
stand-in reader stamps `origin_method=read_by_model` on **both** its branches and no model
exists, so runs 1, 2 and 3 all render **false provenance today** — in the product whose claim
is provenance. Run 2 executes; it does not ship.

**Item 4's acceptance was wrong and is corrected below.** *"Mints the document as
the grounding root before the find"* is not buildable through `execution.run`,
for three reasons read in the code at `7c4c313`: `CapacityMMWriter.index` is
per-instance and in-memory and `execute_pipeline` builds its **own** writer, so a
root minted elsewhere is invisible to its re-seed guard and a document that is
also a start gets minted **twice**, both parentless; a caller cannot construct a
matching writer anyway, because `_run_leaf_pipeline` composes its `run_ref` from
a private format string; and `root()` mints an **isolated node** — the only
linking method, `link_provenance`, writes an XRef *out* to `knowledge_mm`, not an
edge *down* to the run. **`CapacityMMWriter.root()` and `link_provenance` have no
production caller at all** — only `tests/phase_48/test_knowledge_mm_writer.py`.
That is the third time in this lane a document has built an argument on a
mechanism nothing calls (`family_rule_for` was the first two). **Grep before
quoting a mechanism.**

Pre-minting is meaningful in exactly one place and it is **run 4**: `execution.run`
**raises `LeafPipelineNotFound`** when no route is found — it does not fall back
— so an unreachable target leaves **no grounding graph at all**, not even a
`RunStopped`. There the pre-mint is the only thing that would exist; here it
would duplicate a seeded start. It is now item **4a**.

**Item 3 changed shape after the code was read, as items 1 and 2 both did — the
detail is ADR-0208 and the four that matter are these.** (a) The lookup is
`capacity:retrieval:*`, not `capacity:decision:*`: the 2026-08-09 ruling rested
on `family_rule_for`, which **has no caller in any shipped module**, and on
`DECISION_SHAPED_CATEGORIES`, which guards the capacity that *compares* a value
— the criterion, not the lookup. (b) The **version is not a third input** to the
criterion; it is `source_version` inside the limit's origin record, which is
itself a declared output and therefore already graph-resident. So the lookup has
two outputs — the limit and `<limit>_origin` — and the criterion has two inputs.
(c) The criterion writes **no** origin record: a verdict did not enter from
anywhere, and emitting one would need a fourth `producer_kind` in a union
`origin_v0` says to freeze after its second producer, which this lane **is**.
(d) `no_source_in_force` **returns** and `source_unreachable` **raises** — a
finding keeps the run renderable, an outage is reported by L-2 as a stopped run,
and a Record that confused the two would be false.

**Two things items 1 and 2 both proved, and the next item should try the same trick first:**

1. **Constants imported from `mindsos_capacity/identifiers.py` rather than exported from
   `mindsos_capacity/__init__.py` cost nothing.** `NODE_TYPE_CAPACITY_INSTANCE` is the
   precedent; both ships followed it, and `mindsos_capacity.__all__` stayed at **146** with
   `test_export_count_is_146` untouched. The `policies` role's 22-sentinel blast radius is
   what happens when you cannot avoid the export slate; this is how you can.
2. **`capacity_mm` carries no schema** (`Metagraph.schema is None`) and
   `capacity_persister`'s encoder dispatches only on `DataStateInstance`, passing everything
   else through. So a new instance node type with a primitive value costs **no type
   registration and no persister change**.

**One design point L-2 settled that is easy to re-derive wrongly:** `record_stopped()` and
`record_cancelled()` are **two methods on purpose**. Cancellation's check precedes
`dispatcher.dispatch`, so the step never ran, so it mints the `RunStopped` node **alone** —
no `CapacityInstance`. Minting one would claim a capacity executed when it did not, which is
what guard **G3** exists to refuse, and `record_stopped()` raises if handed the cancelled
reason. That distinction was found by reading the code *after* the shape had been agreed.

---

### 2.1 What three probes established, 2026-08-12 — read this before scoping item 5

Run as throwaway experiments against the shipped tree; **nothing here was committed as code**.
Same method as the day-one route probe and the four stub capacities: run it, do not argue
about it. All three changed the plan.

**Probe A — the prose probe.** Dumped a driven run's grounding graph and hand-wrote the Record
from *only* what is in it. **The graph is roughly 80% sufficient.** The clean run composes to:

> *The return as filed states a gross income of 61,000, read by a language model from their
> filed return. The filing-threshold policy, version 2024.1, in force since 2024-01-01, sets
> the gross income at which a return must be filed at 29,200. Therefore: a return must be
> filed.*

Three defects, two of them in already-merged code — tracked as `pending_designs`
**`decision-records-record-prose-convention`**:

1. **Registered prose leaks an identifier.** `policy_limit_datastates`' generated default
   description reads *"where the value of `dr.filing_threshold` came from"* — a DataState
   **name** in prose the renderer prints. `assert_printable_phrase` guards
   `source_identity_phrase` and `question` but **not descriptions**, which is the surface that
   matters. One-line fix in `mindsos_capacity/builtins/policy_lookup_v0.py`; it is a code
   change and needs its own gate.
2. **The stand-in reader lies in the Record.** It stamps `origin_method=read_by_model` /
   *"read by a language model"* and **no model exists**. False provenance, in the product whose
   claim is provenance. Item 5 must stamp `structured_ingest` until a model is real.
3. ~~**The connective sentence.**~~ **WITHDRAWN by probe D (§2.3).** The guess here was
   that registered descriptions would have to become printable statements. They do not:
   **DataState descriptions are not on the render path at all.** The generic "Therefore:"
   template is enough, and the per-criterion template — the hand-maintained mirror the audit
   warns about — is not needed. What survives is one field on the *capacity* declaration,
   which is a different change; see §2.3 decision 2.

**Probe B — the exposure probe. It reversed this lane's own largest push-back.** Three
exposures on one claim, through a `map` milestone over the *existing* capacities, **no core
change**: 61,000 → *a return must be filed*; 12,000 → *no return is required*; income absent →
***not determined***. Three isolated grounding graphs, one per exposure. **L-1 does not
collide** — members get isolated sub-blackboards and each member run grounds separately. So
`DECISION_RECORDS_DEMO_PLAN.md`'s headline beat — *a per-exposure refusal standing beside a
per-exposure answer, on the same claim* — **works today**. It also ran **run 2** end to end,
which is why item 5 shrinks to *"make the stub honest"*.

⚠ **What survives, and it is a guard rail rather than a blocker.** With the store unreachable
the member capacity **raises**, and `MemberAbortError` kills the **whole claim** — observed:
*"member 0 failed after 2 attempt(s) (all-or-nothing abort)"*, having retried twice on
identical in-memory input first (which also confirms
`COLLECTION_ITERATION_OPEN_REVIEW_FINDINGS.md` finding 1 for this path). Benign today, because
our only raising path is a global outage. **The day anyone writes a member capacity that
raises on a per-exposure problem, one bad exposure destroys the whole claim's Record.** Tracked
as `pending_designs` **`core-collection-member-dont-know`** — and note that ADR-0208's refusal
design *is* the "unenforced, undocumented convention" finding 2 names, shipped one level down.

**Probe C — the persistence probe. Green.** Every node value this lane produces is codec-safe
under `make_node_value_encoder({})` with **no encoders at all**: origin records persist as
`dict`, `RunStopped` as `str`. Item 7's *"rendered from the **persisted** graph"* is reachable
without a `DataState.encode`. **Caveat:** that is the value-codec half; a real FalkorDB
round-trip was not runnable in the pre-filter container and is still unproven.

### 2.3 Probe D — it ran, and it decided six things

**Method: a generic renderer sketched over the four graphs items 3 and 4 already produce** —
clean, no-edition-in-force, store-unreachable, and unroutable — with every symbol it could not
turn into prose recorded rather than filled in. Nothing committed as code. Same rule as the
other four probes: run it, do not argue about it.

**Result 1 — the graph alone renders the derivation body.** In a **question → answer →
therefore** form, run 1 composes with no external lookup of any kind:

> *Q. What gross income does the return state?* — **61000**, from *their filed return*.
> *Q. What filing threshold was in force on 2024-04-15?* — **29200**, from *the
> filing-threshold policy* (version 2024.1, in force from 2024-01-01).
> **Therefore: a return must be filed.**

Run 3's refusal renders too — *"Nothing. the filing-threshold policy has no edition covering
2019-04-15."* Every word of that comes from **origin-record fields**, which are ordinary graph
values because an origin record is a declared output.

**Result 2 — exactly three things cannot be said, and that list IS the run manifest.**

| Gap | Why | Bites |
|---|---|---|
| the declared start set | a parentless `DataStateInstance` is structurally identical to one whose producer was removed | every page |
| a phrase per capacity | a `CapacityInstance`'s only content is its IRI, and the criterion writes no origin record (ADR-0208 D3) | *"Therefore… decided by"*, *"Stopped at"* |
| a phrase per stop reason | `RunStopped.value` is the token `step_failed` | the outage page |

**Result 3 — the G2 mutation produced a worse failure than G2 describes.** Deleting the
criterion's `CapacityInstance` did **not** make the renderer raise. It printed
***"Given: a return must be filed"*** — a derived conclusion silently reclassified as a
premise. Nothing in today's graph would let any renderer catch that.

**Result 4 — three corrections to this document's own guesses.** `origin_method_phrase`
already exists in the record (*"read by a language model"*), so the How-line needed nothing.
`environment_fault` is present, unused, and is the field that separates our outage from a
finding about the case — a renderer must consume it. `source_datastate` holds an **IRI** and
must be treated as a link, never printed.

**Result 5 — two more shipped prose leaks**, both fixed in #151: the outage message carried
the `source_unreachable` token and the G6-banned word *"layer"*, and two of three messages
interpolated an arbitrary upstream exception into customer-facing text.

#### The six decisions, owner-agreed 2026-08-12

1. **The run manifest carries three things** — the declared start set, a phrase per capacity
   IRI, a phrase per stop reason. Probe D's three unrenderables, and nothing speculative.
2. **A `printable_phrase` field on the capacity declaration**, validated by
   `assert_printable_phrase`. `description` is a *question* — *"whether the stated income
   reaches the threshold in force"* renders as *"decided by whether the stated income
   reaches…"*. **Lands before item 5.**
3. **Phrases in the manifest, not IRIs.** Carrying IRIs would make the renderer read the
   declarations graph, and *"from the graph and nothing else"* would stop being true.
4. **Minted in `_run_leaf_pipeline`, above the find.** Verified at `fd6cefc`: `run_ref` is
   composed at `execution.py:554`, **after** `_compose_pipeline` at `:544`, which is where
   `LeafPipelineNotFound` raises (`:285`) — so at raise time no writer, no run ref and no
   graph have ever existed. Hoist the writer, give `execute_pipeline` an optional `writer=`
   (28 call sites, none affected by an optional kwarg), append `writer.graph` to
   `capacity_graphs` on the raise path. **Item 4a is absorbed by this**, and item 4's three
   objections dissolve because there is then only ever one writer.
5. **"Persisted" in item 7 means a real FalkorDB round-trip.** The claim is that the Record is
   reconstructible from stored evidence; a Record that only renders from objects still in
   memory has not shown that. Note the driver reaches persistence through nothing today —
   `persist_capacity_mm` is called only from `consolidation.consolidate_request`, i.e. the
   orchestrator, and `_dr_driver` calls `execution.run` directly.
6. **Item 5's reader is core** (`mindsos_capacity/builtins/`), content stays in
   `_dr_fixtures.py`; it owes a tag. **`feat/decision-records` is archive-tagged now** per
   RULES §10.1 and the seam re-lands from the tag at item 8.

#### Order

`printable_phrase` → run manifest (+ G2 as its acceptance) → item 5 → item 7.

**Item 6 is deleted.** Its only content was G2, which §3 already said waits for the renderer,
and which probe D proved is unimplementable until the manifest lands. G3, G7 and G8′ shipped
with item 3.


---

**Pin: `origin/main` `af329eb`** at the time of writing; **build item 3 against `cfc1795`
or later.** Assert the sha in the same command box as any gate run or worktree creation, and
**merge `origin/main` into the lane before gating** — `origin/main` moved four times during
item 2 alone, and `merge-base --is-ancestor` refuses otherwise. Re-pin between items, never
mid-item.

| # | Item | Acceptance |
|---|---|---|
| **1** ✅ | **[SHIPPED `a310958`]** **Lift `origin_v0` to `main`** as its own core CR — the module, its ADR (number assigned, `Proposed`), and its tests. Trim `tests/llm_seam/test_origin_contract_and_scope.py` of anything importing `comprehension_v0`; what it loses moves to Layer B. Correct the route-probe docstring in the same commit (§4). | Gate green. No existing `mindsos_*` module edited. `parse_capacity_iri` is the only core import. |
| **2** ✅ | **[SHIPPED `c9754ac`]** **L-2 — a terminal node on every non-success.** `execute_pipeline` writes one node before every non-success return: failure, decline, cancellation. One node type carrying the capacity IRI, a closed reason and a detail. | A deliberately failing step leaves a node naming it. Shown red first. Gate green. |
| **3** ✅ | **[SHIPPED — ADR-0208]** **The lookup capacity + the criterion.** Lookup: `capacity:retrieval:<name>` (**not** `decision` — §2.0), as-of selection by **window containment**, two outputs (the limit and **its origin record**, not the version) as separate DataStates, refusals `no_source_in_force` (`environment_fault` false, **returns**) and `source_unreachable` (true, **raises**). Criterion: family `decision`, typed to this criterion — never a generic comparator — and it **checks for a missing operand**, because `core-dispatch-value-validation` is deferred and core will not. Only the lookup emits an origin record. | The `policies` role gains its first reader **and its first writer**. One lookup, two outputs, fires once. |
| **4** ✅ | **[SHIPPED]** **The run driver.** Builds a `PlanResult` with plural `leaf_targets[...]["start_datastates"]` and calls `execution.run(..., mm=..., solve_seed=...)`. **The pre-minted grounding root is REMOVED from this item** — see above; it is item 4a. The driver states endpoints and nothing else: L4 derives the finder from start arity, and an AST guard pins that the driver references no finder name and no `finder` plan key. | The route is *found* and *grounded* — not hand-assembled, not a script calling capacities in order. Precedent: `tests/phase_48/test_map_member_multiinput.py`. |
| **4a** | ~~**The pre-minted grounding root, for run 4 only.**~~ **ABSORBED 2026-08-12 into the run manifest (§2.3 decision 4)** — the manifest is minted above the find, so run 4 has a graph by construction and this is no longer a separate item. | — |
| **4b** | **A `printable_phrase` on the capacity declaration** (§2.3 decision 2), validated by `assert_printable_phrase`. | An instance can be named in prose without reading the declarations graph. **Lands before item 5.** |
| **4c** | **The run manifest** (§2.3 decisions 1, 3, 4). Hoist the writer above `_compose_pipeline`, mint starts + capacity phrases + stop-reason phrases, optional `writer=` on `execute_pipeline`, append the graph on the `LeafPipelineNotFound` path. | **G2 is the acceptance**, shown red with probe D's exact mutation. Run 4 renders. G7 becomes checkable from the graph. |
| **5** | **A structured-ingest reader.** `PRODUCER_STRUCTURED_INGEST`, already a constant in `origin_v0`. Two declared outputs — the value with a real `ShapeDescriptor` (`scalar("int")`, never opaque) and its `<value>_origin`. Refuses with `field_absent`. No model, no transport. | Runs 1 and 2 execute end to end on `main`. This is also claim 5's control arm, so it is not throwaway. |
| ~~**6**~~ | **DELETED 2026-08-12** — its only content was G2, now item 4c's acceptance (§2.3). **G3, G7 and G8′ landed with item 3** — G7 and G8′ were already gated in `test_route_probe.py` (#137) and are now **re-homed** into `tests/decision_records/test_lookup_decision_route.py`, because STATE marks the probe for deletion the day L4 gains plural-start expressiveness and deleting it must not take two guards with it. | Below. |
| **7** | **The renderer**, against the real graph items 3–5 produce, plus **G1** and **G6**. Form is **question → answer → therefore** (§2.3), not composed statements. | One page a non-technical reader understands with no glossary, rendered from the **persisted** `capacity_mm` graph and nothing else — and *persisted* means **a real FalkorDB round-trip** (§2.3 decision 5), not the live `Graph` objects the driver hands back. |
| **8** | **Layer B.** Merge `origin/main` into `feat/decision-records`, reconcile the three core modules, gate it, merge, then swap item 5's reader for `comprehension_v0`'s. | First gate of the LLM seam. A verification step, not a blocker. |

### The rule that decides whether this succeeded

**The route must be composed by the finder and executed through `execute_pipeline`.** Not a
script that calls capacities in order. Not a hand-assembled `Pipeline`. `BRAIN_ARCHITECTURE_AUDIT.md`
records arc1 registering a 1,032-line capacity topology over a 3,756-line solver that never
executed through it; a hand-wired slice reproduces that exactly and every downstream number is a
lie about the one thing being sold.

### The five runs

v0 is **runs 1 and 2**. Runs 3, 4 and 5 follow item 2 landing, not before.

| # | Run | Status |
|---|---|---|
| 1 | Clean outcome — the Record names value, limit, version | **v0** |
| 2 | Value absent — reading refusal, graph-resident, names the missing item in prose | **v0** |
| 3 | No policy in force at that date — lookup refusal | after item 2 |
| 4 | Target unreachable — **`execution.run` RAISES `LeafPipelineNotFound`** and writes nothing at all, so there is no graph and no `RunStopped`. Verified 2026-08-12, `tests/decision_records/test_run_driver.py::test_a_single_start_plan_raises_rather_than_under_wiring` | **item 4a** |
| 5 | Same case, two dates — different limits, different versions, both named | after item 3 |

**Run 5's trap, carried forward:** the recorded-reading replay key hashes the exact source text.
**The as-of date stays out of the document** and enters as its own DataState into the lookup, or
run 5 silently becomes *"different documents give different limits"* — the opposite of the point.

---

## 3. Guards

- **G1** Renderer imports none of: blackboard, capacity context, L2 snapshot, `Pipeline`,
  `chain_artifacts`.
- **G2** Remove one capacity instance from the graph → the renderer raises, never fills the gap.
  **Acceptance on the run manifest, not on the renderer, and not its own item** — probe D ran
  this mutation and the renderer printed *"Given: a return must be filed"* instead of raising,
  because nothing in the graph distinguishes a gap from a start. It is unimplementable until
  the manifest lands (§2.3).
- **G3** No Record without the capacities having executed and written.
- **G7** *(restated — the original wording was unsatisfiable with three starts)* The parentless
  `DataStateInstance` set is **exactly** the declared starts. Still catches the real failure: a
  value that should have been derived arriving via `seed()`, which mints with no incoming edge.
- **G8′** Assert nothing is registered Global at the lookup or decision IRIs. **Labelled as a
  gap-pin, not a guard** — the same class as
  `tests/policy_role/test_policy_role_core.py::test_append_only_is_declared_but_not_enforced`. It
  pins the all-Local reality §1.6 forces, and it is **deleted the day DataStates go realm-free**.
  Say so in its docstring.
- **G4, G6** land with the renderer / after item 2.

**Where they live after item 3.** G3, G7 and G8′ are in
`tests/decision_records/test_lookup_decision_route.py`; G7 and G8′ are also
still in `test_route_probe.py`, which is correct — the probe pins the finder's
own behaviour and the route test pins the shipped route. G2 and G1 wait for the
renderer. All six of item 3's guards were **shown red by mutation**, not merely
observed green.

Three incompatible G8 rulings existed on record — build against `SPECIALISES` (slice plan), do
not build it (project memory), G8′ (handoff). Under §1.6's all-Local reality only G8′ is
satisfiable. This document is the ruling.

---

## 4. Corrections owed regardless of this plan

> ✅ **ALL FOUR ARE DONE.** 1–3 landed in `512e975` (#142); 4 opened
> `core-terminal-node-on-non-success`, which then shipped as item 2 (`c9754ac`). The
> `register_capacity` half of D15 was opened as
> `pending_designs.core-register-capacity-opaque-into-decision` in `a310958` (#143). The
> list is kept because the *reasoning* is why the corrections were needed.

1. **`tests/decision_records/test_route_probe.py`** — the docstring of
   `test_l4_cannot_express_plural_starts_this_is_D_A` says *"`_endpoint_starts` accepts plural;
   nothing can hand it any."* False (§1.1). The test's assertions are still correct and still go
   red the day the planner path lands, so **correct the docstring, do not delete the test.**
2. **`STATE.json` `decision-records-l4-multi-input-start`** — carries the same false sentence.
   Replace with the narrower true one: no *planner-emitted* plan can express plural;
   `execution.run` over a directly-constructed `PlanResult` can, and is gated.
3. **`STATE.json` `core-dispatch-value-validation`** — add the L-2 dependency, so the next lane
   cannot build it first.
4. **`STATE.json` `pending_designs`** — add **`core-terminal-node-on-non-success`** (L-2). It is
   item 2 here; the entry exists so it stays owned if this lane closes.

Also unowned and worth an entry when someone touches it: the `register_capacity` half of D15's
opaque-into-decision rule, which `CORE_CR_EXTERNAL_MODEL_SEAM.md` D15 filed as "a separate CR"
that was never opened.

---

## 5. Deferred, with reasons

| Item | Why not now |
|---|---|
| §3.1 planner plural starts | Not blocking (§1.1). Its end state is finding moving into planning (ADR-0206 §3, C4R3) with selection at `decision.select_producers`. A passthrough patch extends `_select_finder`, which `CORE_RECONCILIATION_PLAN.md` C2R4 already rules *"transitional by construction"*. |
| §3.2 dispatch value validation | ~~Unsafe before L-2~~ — **that reason died when L-2 shipped as `c9754ac`**; STATE has read UNBLOCKED since 2026-08-11. Still unbuilt and unowned. ADR-0208 D5 is the argument *for* it. |
| §3.3 realm-free DataStates | v0 registers all-Local and works. Closing it deletes G8′ and makes #122's union view testable. |
| §3.4 append-only enforcement | v0 writes one edition. It constrains what we **say**, not what we build. |
| §3.5 recorded producer choice | One producer per DataState in v0. It is a claim-1 integrity hole, not finder hygiene — file it as one. |
| §3.2 revisited after item 3 | Still deferred, and item 3 is why it matters: the criterion's own `None` check is the **only** thing standing between a refused lookup and a confidently wrong verdict. Every future criterion must remember. That is the argument for building it, not against. |
| §3.6 executor unification | v0 uses the one that grounds. Retiring `mindsos_server.pipeline_runner.run_pipeline` is C3R4. |
| Everything in `CORE_C3R1_ADMISSION_CONFIRMED.md` §9 | The `.found` architecture guard (§9.1) and the `input_group` retirement (§9.3) are both correct and neither blocks. §9.1 rises the moment item 4 puts a new consumer on the finder's output. |

**Out of scope entirely:** the other five decision ops · any claims content · SARA's nine sections ·
the batch harness · an HTTP API · a web UI · the CORE-C abstraction-levels build-out (the grounding
graph uses intra-graph edges, so the C2R3 metagraph boundary does not apply).

---

## 6. Standing risks

- **No transport exists** (`LLM_SEAM_MANUAL.md` S-3). No plan can produce a live run today; v0 is
  replay-only by construction. Fine for a gate, fatal for a demo.
- **S-2 has a real deadline** — whether the transport or `mindsos_llm` parses the model's output
  must be settled **before a transport is written**, or it becomes a rewrite instead of a decision.
- **All 13 L4 catalog capacities are placeholders**, so `run_lifecycle` yields one milestone and
  one pipeline. That bounds what any demonstration may honestly claim about planning.
- **One value per DataState IRI** (`L-1`). Every distinct value needs its own type. If you find
  yourself reusing a type for two values, stop — that is the nilm blocker.
- **A guard authored after the renderer** will pass and will mean nothing.

---

## 7. Method

- **A claim about state is a claim you have READ.** `origin/main` for main, the branch tip for a
  branch, the gate for green. A gate clone's local `main` is stale. `origin/main` moved five times
  in one recent session.
- **Assert the SHA in the same command box** as any gate run or worktree creation.
- **Cowork edits files; the Mac runs git; Linux runs every test, in docker, with `--build`**
  (RULES §4/§5). A container or device pre-filter is a prediction, never a result.
- **The container pre-filter predicts the gate exactly if built right** — `uv venv --python 3.12`,
  install `pytest tomli argon2-cffi typer`, diff against a pristine copy **by name, never by
  count**. A `ModuleNotFoundError` is a silently unrun test file, not background noise.
- **STATE.json is edited by many lanes at once and the device bridge can serve a stale snapshot.**
  Apply STATE edits with a small idempotent script run **on the Mac**, guarded to abort rather than
  clobber if its anchor is absent. Never commit a sandbox-staged copy over the live file.
- **Four stub capacities falsified three plan claims in an afternoon**, and reading two modules
  falsified two handoff claims in this one. Both beat further correspondence.
