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
| #151 | `1dad532` | **Probe D**, and the three prose leaks it found. Tag **`prose-leaks-confirmed`** | **4652 / 11 / 1x / 0** |
| #152 | `49e3eda` | **`printable_phrase`** on the capacity declaration + ADR-0207 am-1. Tag **`capacity-printable-phrase-confirmed`** | **4666 / 11 / 1x / 0** |
| #153 | `a3751f2` | **The run manifest** (item 4c), absorbing item 4a. Tag **`run-manifest-confirmed`** | **4677 / 11 / 1x / 0** |
| #154 | `93ff31b` | **Item 5** — the structured-ingest reader, and **run 2's first test** | **4694 / 11 / 1x / 0** |
| #155 | `bbe63e4` | **The origin-union freeze** + ADR-0207 am-2. Tag **`origin-union-freeze-confirmed`** | **4711 / 11 / 1x / 0** |
| #156 | *(squash)* | **The refusal vocabulary** + the escaped findings. Tag **`refusal-vocabulary-confirmed`** | **4716 / 11 / 1x / 0** |
| #157 | *(squash)* | **Map-member manifests** — minting moves into `execute_pipeline`; the sub-MM routing gap; ADR-0201 am-4 + ADR-0207 am-3. Tag **`dr-map-manifest-confirmed`** | **4731 / 11 / 1x / 0** |
| #158 | *(squash)* | **Fold grounding** — the reducer routes through `execute_pipeline`; RULES §12 replaced by the sweep; the coordination-file pin; the run-surface sentinel. Tag **`dr-fold-grounding-confirmed`** | **4747 / 11 / 1x / 0** |

**Baseline for the next item: 4747 passed / 11 skipped / 1 xpassed / 0 failed at PR
#158's tip `714f4ee`** — carryable: the tip's parent chain sits on `origin/main`
(`3dd151b`), the pre-gate `git merge origin/main` was a no-op for exactly that
reason, so it is a **merged-state** gate. *(Predicted exactly — the eleventh
consecutive exact call.)* The line below is the previous baseline, kept for the
history of the rule that this line goes stale:

**~~Baseline for the next item: 4731 passed / 11 skipped / 1 xpassed / 0 failed at PR
#157's tip `f878886`.~~**

**The demo home is live** (not a PR row — it is a demo-branch ship, no core
gate by design): `demo/decision-records` @ `d94ca4f`, worktree `MindsOS-dr`
(long-lived), pins `dr-fold-grounding-confirmed`, registered in `STATE.demos` +
`BRANCHES.md` (`485eed0`). `decision_records_demo/dr_dump.py` is **the §12
command** — shapes `leaf` / `claim` / `noroute` / `all`, raw, zero third-party
deps — and its output was verified **by the owner** on the Linux box,
byte-identical to the build container's run. §12 checks in this lane now answer
against a dump the owner ran, as the rule requires. It is carryable — the gate ran on a tip whose parent **is**
`origin/main` (`be7aa8a`, tag `refusal-vocabulary-confirmed`), so it is a **merged-state**
gate; the `git merge origin/main` before it was a no-op for exactly that reason. Contrast
`#138`'s 4551, a **branch** gate, which is not carryable. **This line has been stale twice:
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
2. ✅ **SHIPPED — `printable_phrase` on the capacity declaration** (PR #152, tag
   `capacity-printable-phrase-confirmed`, **ADR-0207 amendment 1**). The rule moved to the
   dependency-free `mindsos_capacity/printable.py` so core registration could enforce it
   without importing from `builtins/`. ⚠ **The amendment corrects ADR-0207's own line saying
   `to_properties` does not persist custom fields — but KEEPS the rejection it supported.**
   The catalog is mutable and separately persisted, so **the renderer must never read a phrase
   from it**; item 4c snapshots the phrase into the run graph at mint time and the Record
   renders from the snapshot.
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

~~`printable_phrase`~~ ✅ → ~~run manifest (+ G2)~~ ✅ → ~~item 5~~ ✅ → ~~map-member manifests (#157)~~ ✅ → ~~fold grounding (#158, tag `dr-fold-grounding-confirmed`, critic PASS)~~ ✅ → ~~the demo's own home + `dr_dump.py` (`demo/decision-records` @ `d94ca4f`, dump **owner-verified** on the Linux box, all three shapes)~~ ✅ → **demo-critical sweep ← NEXT** (`decision-records-demo-critical-sweep` in `STATE.pending_designs` — its acceptance sentence, the regime axis DERIVED from branch conditions, lives there) → persistence smoke → item 7 → Layer B. *(This line has now been stale three times; per its own rule it moves with the table, in the same commit as the ship that advances it.)*

**The pre-filter halves from here.** The baseline is always `main` and every merge is gated, so
**the previous item's change-tree run IS the next item's baseline** — keep its log and tarball
rather than re-deriving a pristine tree. Re-run the base only when `main` moved for a reason
other than this lane's own gated merge, and say so when you do.

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
| **4a** ✅ | ~~**The pre-minted grounding root, for run 4 only.**~~ **ABSORBED and SHIPPED in PR #153** — the manifest is minted above the find, so run 4 has a graph by construction. | Run 4 renders from a graph rather than from a caught exception. |
| **4b** ✅ | **[SHIPPED — PR #152, ADR-0207 am-1]** **`printable_phrase` on the capacity declaration** (§2.3 decision 2). Optional; validated at `register_capacity` only when supplied; the rule now lives in `mindsos_capacity/printable.py`. | Gate green. Every previously-registered capacity is byte-identical on its node. |
| **4c** ✅ | **[SHIPPED — PR #153, tag `run-manifest-confirmed`]** **The run manifest.** Writer hoisted above `_compose_pipeline`; starts + capacity phrases + stop-reason phrases in the node **value** (`add_node` validates properties as primitives only); graph appended on the `LeafPipelineNotFound` path. ⚠ **CORRECTED BY PR #157 — read this row with §2.8.** The falsified-`writer=` finding **stands**: no writer is threaded into `execute_pipeline`, then or now. But *"`execute_pipeline` is UNCHANGED"* is **stale**: #157 moved the **mint** into it (a `case_label` keyword and the manifest call), because minting here covered only one of two run paths and left every map member with no manifest. Writer, no; mint, yes. | Gate green. G2 shown red with probe D's exact mutation. Run 4 renders. **Item 4a absorbed.** |
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
| 4 | Target unreachable — `execution.run` still **raises `LeafPipelineNotFound`**, because the route really is unfindable, but the run manifest is minted **before** the find, so the run now leaves a manifest-only graph. | **✅ PR #153** |
| 5 | Same case, two dates — different limits, different versions, both named | after item 3 |

**Run 5's trap, carried forward:** the recorded-reading replay key hashes the exact source text.
**The as-of date stays out of the document** and enters as its own DataState into the lookup, or
run 5 silently becomes *"different documents give different limits"* — the opposite of the point.

---

### 2.4 Where v0 actually stood, 2026-08-12 — read against the tree, not the plan

**Expectations were not met, and one gap was worse than this document claimed.**

⚠ **`G2` was overstated in §2.3 and in #153's own ship record.** G2 says *the
renderer raises rather than filling the gap*. **There is no renderer.** What #153
shipped is G2's **precondition** — the graph can now tell a premise from a gap.
The guard cannot exist until item 7. Its test is named `test_g2_…` and overstates
itself; the name is kept so the pairing is findable, and this line is the
correction.

⚠ **Run 2 — half of what v0 IS — had no committed test for four ships.** Every
seed carried an income, so the reader's refusal branch was unreachable;
`REFUSAL_FIELD_ABSENT` appeared only inside `_dr_fixtures.py`, never in an
assertion. §2.1 said probe B *"ran run 2 end to end"* — a throwaway that was never
committed. **Fourth time in this lane an argument rested on something not in the
tree.** ✅ **Closed by #154**, in both shapes (absent, and stated-but-unreadable).

**The rest of the audit, and what remains:**

| | State after #154 |
|---|---|
| Runs 1, 2, 3, 4, 5 | ✅ all gated |
| G3, G7, G8′ | ✅ named tests |
| **G5** | ✅ — was real but **unnamed** in three modules, so unfindable. Named in #154. |
| **G4** | ⚠ reading half closed by #154; both refusal shapes now structural |
| **G2** | ⚠ precondition only, until item 7 |
| **G1, G6** | ❌ need the renderer |
| **Persistence** | ❌ **no code path.** `persist_capacity_mm` is reached only from `consolidation.consolidate_request` ← the orchestrator, and `_dr_driver` calls `execution.run` directly. "From the persisted graph" is unmet and unowned. |
| **Two IRI leaks** | ❌ G6-red today: the manifest's `declared_starts` (bare IRIs, visible on the no-route page) and `source_datastate` inside every origin record |

### 2.5 After every ship — the procedure

**Canonical text is RULES §12; it is not duplicated here.** In this lane it means:
run `decision_records_demo`'s dump against the **merged** state, answer §12's six
questions in writing, and append a dated block to §2. **The item table may not
advance until the previous ship has one.** §2.4 is the first such block.

**A green gate is not the check.** Seven consecutive gates were predicted exactly
while run 2 sat untested — the gate proves the tests agree with the code, and it
cannot see a case nobody wrote a test for.

---

### 2.6 §12 check after #155 — the fix had the same hole it was fixing

**First check under RULES §12** found seven things on #154; four were real
defects, one reversed something asserted two messages earlier, and all became
#155. **The second check found #155 itself incomplete.**

⚠ **The freeze classified the union's FIELDS and left its VOCABULARIES
unclassified** — the same class of gap, in the same module, missed by the ship
that built the mechanism for it. `REFUSAL_REASONS` declares **8** tokens; the
system can emit **3**. Four of the rest are **reserved** for the LLM seam, and
**`source_unreachable` is degenerate for exactly the reason `environment_fault`
is**: advertised in every lookup's `possible_refusal_reasons`, never able to be
an actual `refusal_reason`, because that path raises and a raising step writes
no record. A renderer reading the possible list would tell a reader *"this
lookup could have told you the store was unreachable"* — and no record could
ever say it. ⟹ `origin-refusal-vocabulary-classification`.

**Not the same problem:** `RUN_STOPPED_REASONS`' `cancelled` and `needs_input`
are unreachable in *this lane's* path but genuinely reachable system-wide.

**Confirmed green by the same check:** the `RunManifest` node value is codec-safe
under `make_node_value_encoder({})` and survives a JSON round-trip. **Probe C
predated the manifest** and never covered it.

**§12 gains a seventh question**, because the six would not have found this:
**when a ship introduces a classification, a guard or a contract, what else in
the same module is of the same kind and did not get it?**

**Process failure, recorded rather than glossed.** The ADR amendment was appended
*after* the pre-filter tarball was taken, was never pre-filtered, and was
nonetheless described as having passed it. Structure was verified before the gate
and the gate then covered it — but the claim was false when made. **Tar after the
last edit; never say the pre-filter covered a file that postdates the tarball.**

---

### 2.7 §12 check after #156 — a shipped feature is missing from the demo's own shape

**Disposition is given for every finding, per RULES §12.**

| Finding | Disposition |
|---|---|
| **A map member's graph has NO manifest** | **Filed `decision-records-map-manifest-gap`. Fix next, BEFORE the demo project.** |
| **The member path never catches `LeafPipelineNotFound`** | Same entry — an unroutable member leaves no graph, and `MemberAbortError` destroys the whole claim's Record |
| #153's ship record overstates its own coverage | **Corrected in STATE** this ship |
| §12 checks were re-reading one surface | **Fixed here** — a check now nominates its surface (below) |

⚠ **`_run_member_pipeline` is a SEPARATE FUNCTION from `_run_leaf_pipeline`, and
#153 only touched the latter.** Proven by running a three-member map: three
isolated graphs, three capacity instances each, **zero manifests**. So the
manifest exists for the run shape v0's tests use and is **absent from the run
shape the demo is built on** — the headline beat is one Record per exposure, and
an exposure *is* a map member. On those graphs G2 is unavailable, nothing can
name what decided, and no stop token can be translated.

**The second half is worse.** Neither member function catches
`LeafPipelineNotFound`, so an unroutable exposure leaves no graph at all — the
hole #153 closed at leaf level — and `MemberAbortError` is all-or-nothing, so one
bad exposure destroys the **whole claim's** Record. Compounds
`core-collection-member-dont-know`.

**⟹ the map fix moves AHEAD of the demo project.** `dr_dump.py` must dump the
demo's real shape; shipped first, it would dump a leaf run and look healthy.

**What this check changed about checking.** The previous two §12 passes re-read
the same path and found progressively less. This one examined a surface nobody
had looked at and found more than both combined. **A check nominates the surface
it examines, and does not repeat the last one's.** Surfaces still unexamined:
fold/reducer runs, a submind's grounding graph, and a real persistence
round-trip.

**And a correction to my own record.** #153's tag message certified that *"every
run leaves a graph"* and *"run 4 renders"*. Both are false for map runs, and both
were written without ever having run a map. Nine consecutive gates were predicted
exactly across that period.

### 2.8 The map-manifest CR — what it built, and the two decisions it inverted

**Branch `feat/dr-map-manifest`, off `main` at `be7aa8a`.** It closes both
halves of §2.7's finding, and the fix is deliberately *not* a second mint.

**Minting moved into `execute_pipeline`.** That is the one function BOTH run
paths call — `_run_leaf_pipeline` and `_run_member_pipeline` — so *"every graph
carries a manifest"* is now a property of the executor instead of a thing each
caller has to remember. #153 minted it in `_run_leaf_pipeline`, which is why the
member path had none. `_run_leaf_pipeline` no longer mints anything and nothing
replaces it there.

**One no-route helper, two callers.** `execution._mint_no_route_graph` leaves a
manifest-only graph and re-raises; it is called from the leaf path and from
`_run_one_member`. It is caught in `_run_one_member` rather than inside
`_run_member_pipeline` because that function is deliberately **pure** — the
caller decides accept/reject, so a rejected retry persists nothing — and
persisting a graph is a caller decision.

**`declared_starts` became IRI → phrase**, and is keyed on what was actually
**seeded** rather than on `pipeline.start_datastates`: a seeded value is exactly
what becomes a parentless `DataStateInstance`, and a declared start with no
value mints no node, so naming it would promise a renderer a premise that is not
in the graph.

**`case_label` was added**, threaded from `execution.run` through every path.
Core never invents one; absent is recorded as `None` rather than as a missing
key, so a renderer can tell *"no label"* from *"could not read the label"*.

**Two decisions were inverted, and both inversions are mine to own.**

| What was asserted before | What it is now |
|---|---|
| `execute_pipeline` must not take a writer, and `_run_leaf_pipeline` is the right place to mint (#153) | The right place is `execute_pipeline`. #153's reasoning about *writers* was correct and is unchanged — no writer is threaded; what moved is the **mint**, and the earlier version was only ever right for one of two run paths |
| `source_unreachable` **is advertised** and can never be recorded — pinned as a gap to live with (#155/#156, ADR-0207 am-2's ⚠ OPEN) | It is **no longer advertised**. A producer must not advertise a refusal reason none of its records can carry. ADR-0207 **amendment 3**; the pin is inverted, keeps driving the raising path, and keeps its teeth |

**ADR-0201 amendment 4 was owed and is now written.** #153 added a new node type
to the L5 grounding vocabulary — `RunManifest` — and amended no ADR at all,
though ADR-0201 is that vocabulary's home. The amendment records the node, its
four fields, and both corrections above. **This is a §9 finding in its own
right: a new node type shipped with no ADR row.**

**Two more findings came out of the pre-filter, and both are older than this CR.**

| Finding | Disposition |
|---|---|
| **`runstopped:` and `runmanifest:` are prefixes NO sub-MM owns** — `sub_mm_for_iri` raised `KeyError` on either, for nodes sitting inside a capacity run graph | **Fixed here.** Both join `CAPACITY_PREFIXES`. It survived because neither had met the router: `RunStopped` is written only on a non-success, and the guard that walks every node of a run graph only ever sees a successful one. Moving the mint into `execute_pipeline` reddened it in one step |
| **`start_phrases` fell back to the start's own IRI** when no description was registered — this CR's own first version | **Corrected here** to `None`. The IRI fallback re-inserts the exact leak the phrase mapping replaced, on exactly the runs with no prose to dilute it. The key stays present, so the declared set is still structurally complete |

**The §12 surface this check nominated:** the sub-MM router and the two
run-scoped node types, neither previously examined. Surfaces still unexamined:
fold/reducer runs, and a real persistence round-trip.

**Shown red by mutation, eleven mutations, each reddening a distinct set:** no
manifest at all; starts as bare IRIs; phrases dropped; a core-invented label;
the label not threaded to members; not threaded to the leaf; the member no-route
catch removed; the helper's `mm is None` guard removed; the lookup advertising
`source_unreachable` again; the two run-scoped prefixes losing their room; an
undescribed start falling back to its own IRI; and every member sharing one run
ref.

**Pre-filter, two trees, `main` at `be7aa8a` as the baseline.** 52 failed on the
first change-tree run. **48 are identical by name in both trees** and are
environment-only (no Falkor / no docker in the pre-filter container). The other
**4 were mine, and one of them was the routing defect above** — the other three
are node counts that moved by exactly one, because every run now leaves a
manifest.

### 2.9 §12 check after #157 — and the check itself is now the finding

**Disposition is given for every finding, per RULES §12.**

| Finding | Disposition |
|---|---|
| **A fold leaves NOTHING in the grounding graph** | **Filed `decision-records-fold-grounding`. Not fixed here** — pre-existing since Slice 1b, and folding it into a gating CR would have thrown away a 34-minute gate mid-flight |
| Persistence round-trip of a manifest-bearing graph | **Clean, no action.** The manifest value survives `make_node_value_encoder({})` unchanged, including `case_label: None` and an undescribed start's `None` — no encoders needed |
| **§12 itself produces a drip, not a check** | **Escalated to a second lane** — see below |

**Surfaces examined this pass:** fold/reducer runs; the persistence codec.
Previously examined: the leaf run, the member run, the sub-MM router, the refusal
vocabulary, the origin union. **Still unexamined:** replan / targeted re-execution,
a submind's grounding graph, and a real Falkor round-trip.

#### The fold, in the system's own output

A two-exposure map followed by a fold, every graph in `capacity_mm` dumped:

```
graphs collected: 2
  [0] {'RunManifest': 1, 'DataStateInstance': 2, 'CapacityInstance': 1}
  [1] {'RunManifest': 1, 'DataStateInstance': 2, 'CapacityInstance': 1}

EVERY graph in capacity_mm, by role:   (the same two — nothing else exists)

Does ANY graph mention the reducer capacity:derivation:fx_reduce ?
  -> NO. The fold left nothing in the grounding graph.

The claim-level conclusion the fold produced:
  present in any grounding graph? False
```

`_run_fold_milestone` dispatches the reducer **directly** and its signature does
not even take `mm`, so it has no way to ground anything. Consequences, worst
first:

1. **The claim-level answer is unrenderable.** It lives only on the in-memory
   blackboard, which `execution.run` never hands back. Per-exposure Records
   render; the conclusion they add up to does not.
2. **The link is gone too** — no `CONSUMES` from the member verdicts to the
   conclusion, so even rendering both, nothing says one came from the other.
3. No manifest and no reducer `CapacityInstance`, so on the fold **G2 is
   unavailable** and nothing can name what decided.

Same defect as #157's, one layer up, and worse: #157's made *members*
unrenderable; this makes the **answer** unrenderable.

#### The process finding, which is bigger than the fold

**Ten gaps, one per phase, each found after the work it invalidated was already
built and gated.** §12 asks for *"a full check of the system"* after every ship
and forbids repeating the last surface, and what that has produced in practice is
**one nominated surface per ship** — a drip that guarantees a new gap every phase
indefinitely. Each costs a ~35-minute gate to confirm a ~20-minute
implementation, against a fixed demo date. It does not converge.

Two facts from the record, both uncomfortable:

- **Every gap was surfaced by RUNNING the system**, never by re-reading it.
- **Most of them were reachable by reading** — a sibling function that had the
  call and one that didn't; a prefix table versus the IRI builders. The reading
  was not pointed at the right question.

The build lane is not the right lane to grade its own method. **A second, critic
lane is being opened** to answer *"how should this system be checked so the gap
list converges in one pass"*, with `confirmation_docs/DR_CRITIC_COORDINATION.md`
as the shared record — **untracked and gitignored, per RULES §5**, living in the
shared checkout so it outlives any one lane's worktree. **A finding recorded only
there does not exist: it must reach `STATE.pending_designs` in the same ship.** It gets no worktree and no git; it reads, probes, and
proposes, and changes come back through this lane. The build lane's own
hypotheses are in that file, **folded shut**, to be opened only after the critic
has written its own answer.

**⛔ Nothing further is built until that answer is in.** Building the fold fix
first would be another 20 minutes of implementation defended by a method already
known to be leaking.

---

### 2.10 §12 check after #158 — the first check under the replaced §12

**The rule itself changed in this ship**: the owner adopted the critic's §8.3
(+§10.1.2) text as RULES §12 — the sweep — and this ship carried the edit and
built its tier-1 instrument, the surface-inventory sentinel
(`tests/architecture/test_execution_surface_inventory.py`). Design was
critic-reviewed BEFORE the gate (coordination file §13–§15: Q1 one-CONSUMES
ruling ACCEPTED, Q2 sentinel scope DEFERRED with an owner) — the first ship in
this lane whose design was independently attacked before the expensive
resource ran.

**Disposition is given for every finding, per RULES §12.4.**

| Finding | Disposition |
|---|---|
| **A mutation blanking the fold `DAGStep`'s declared outputs reddened NOTHING** — dead-but-wrong data on the constructed pipeline object, exactly where a future consumer (`dr_dump`, the renderer) would trust it | **Fixed in this ship** — made load-bearing by `test_the_fold_pipeline_object_declares_the_reducers_true_shape`, after which the mutation reds. §12.2c working as adopted |
| **The fold's Slice-A freshness was unguarded** — no test failed when `run_attempt` was dropped from the fold's run ref, so a replan would have silently overwritten the prior fold graph | **Fixed in this ship** — `test_a_replan_reattempt_folds_into_a_fresh_graph`, shown red by that exact mutation |
| **Order-as-identity hazard** (critic §14): member↔verdict correlation is by order, sound only while the ∀-abort barrier makes member order total | **Filed** into `core-collection-member-dont-know` — the CR that lets a member refuse must revisit the ruling; the consumes test's docstring carries the same sentence |
| **The sentinel's first census corrected every recalled surface list** — `mindsos_cli/commands/brain.py` holds a direct dispatch no lane had named (the critic's §8.1 census missed it too; it swept `mindsos_intelligence` + the server, not the CLI) | **Recorded** in the sentinel's classification (`cli-direct`); no action — the census-over-recall argument, demonstrated on its own author |
| **The demo-critical sweep has no queue entry** — it lived only in plan prose and the critic's §10.3 | **Filed** as `decision-records-demo-critical-sweep`, carrying §14 Q2's acceptance: the regime axis is DERIVED from branch conditions, never recalled |

**Rows this check ran** (§12.2b): the fold/reducer surface (now grounded —
nine tests drive the shape); the dispatch census (sentinel, exact); the
coordination-file closed set (pin, red both directions by mutation). **Rows
still unexamined, owned by the sweep item:** refusal regimes, replan/outage
branches derived from code, a real FalkorDB round-trip.

**Evidence** (§11 — the owner ran the gate; the pre-filter is the lane's):
two-tree whole-suite pre-filter, failure sets identical by name (36, the known
environment-only set), passed delta +16 = exactly the sixteen new tests; gate
**4747 / 11 / 1x / 0 at `714f4ee`**, predicted before the run.

**§12.5 status:** the matrix changed this ship (a surface classification was
added, two claims gained rows) — the stop condition is not near.

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
