# Capacity Graph Traversal (CGT)

**Filed:** 2026-08-01, CORE-C3R1 chat. **Status:** design agreed with the owner.
**Nothing built.**
**Verified at:** `origin/main` `60fe2ae`.
**Supersedes:** the design in `CORE_CR_FINDER_AS_CAPACITIES.md` §2 (the stratum
admissibility rule) — see §8.
**Reads with:** ADR-0071 §am-2/§am-3, ADR-0205, ADR-0206, ADR-0156,
`CORE_RECONCILIATION_PLAN.md`, `CORE_VERIFIED_FINDINGS.md`.

> **Name.** "Finder" named a purpose, not a mechanism, and the mechanism is now
> shared with execution (§2.2). *Capacity Graph Traversal* names the graph it
> walks and stays silent about why — which is the point.

---

## 1. What it is

One walk over the L3 bipartite graph of capacities and DataStates. It replaces
`ConjunctionFinder`'s top-down recursion and `BFSFinder`'s single-input walk.

---

## 2. The model

### 2.1 The walk is forward

Start from the DataStates already held. Repeatedly take every capacity whose
inputs are now available, add what they produce, stop when nothing new appears.

Everything else follows from this:

- **Reachability is the computed reachable set.** It is not read off the graph —
  a capacity declaring `PRODUCES d` says nothing about whether that capacity can
  run, because its own inputs may be unavailable. The set is the answer.
- **Self-feeding is unrepresentable.** A capacity is reached only once every
  input it needs has been produced by a step already in the DAG, so it can never
  be selected to produce something it depends on. No cycle stack, no in-flight
  set, no `max_depth`.
  ⚠ **The guards come out when this lands, not before.** The threaded cycle stack
  shipped at `4fd8baa` is still load-bearing on today's catalogs — see §6.
- **Admissibility does not arise.** Every candidate producer is a step already
  emitted. There is nothing to filter, which is why §8's stratum rule is deleted
  rather than repaired.

### 2.2 One machine, two configurations

The walk is a transition system. Nodes are states; `CONSUMES` and `PRODUCES`
edges are transitions; a condition gates each transition; an action fires when it
is taken.

|  | conditions ask | actions do |
|---|---|---|
| **finding** | is this producible? | check, list, gather |
| **executing** | is there a value here? | call the capacity body |

Both configurations differ; the transition system does not. **The recorded
transition path *is* the `Pipeline`** — so the artifact survives, and with it
ADR-0205's requirement that each abstraction level be verifiable by the level
below.

### 2.3 Three ledgers

| ledger | lifetime | holds |
|---|---|---|
| per-transition accumulator | cleared when its slot completes | the inputs gathered so far for one pending capacity |
| path record | the whole walk | steps taken, DataStates now held, alternatives seen |
| frontier | the whole walk | paths still to check |

Completion lives in the accumulator, **never as a property on a graph node** —
the L3 catalog is Global and shared, while availability is per-request, so a node
property would be clobbered by any concurrent walk. Same defect class as
`Milestone.parent_ref` and the one-slot blackboard (D-C).

### 2.4 Traversal control vs. selection

- **Traversal control** — when to stop, what order to expand — is part of the
  action set.
- **Producer selection** — given several candidates for one input, which one —
  is a **policy value** (`core.selection_policy`), never code. A value can be
  stored, attached to a request-knowledge entry, varied per request, promoted and
  **learned**; an action set can do none of those, and ADR-0206 puts judgement
  where learning can move it. `decision.select_producers` stands.
- BFS is therefore a `selection_policy` value, which is how ADR-0071 §am-2's
  "BFS is one registered strategy" is discharged. Shim **S2** is deleted.

### 2.5 Stored pipelines are sub-networks

When an input is produced by a stored pipeline, the walk recurses into that
pipeline and returns when it yields the DataState. This is the only recursion in
the design and it is what makes the walk *augmented* rather than flat.

**Consequence, unowned:** this opens a cycle class at the **pipeline** level —
pipeline A needs a DataState produced by pipeline B, which needs one from A. The
forward walk prevents cycles among capacities and says nothing about cycles among
pipelines. Lands with the pipeline store; recorded here so it is not rediscovered.

---

## 3. Contracts

### 3.1 Input

The walk receives `start_datastate` and `target_datastate` **from a milestone**,
after `hints → map → plan → milestones`. A request supplies hints, never
DataStates.

Two consequences. The start set is narrow — one or two named DataStates — so a
forward walk's reachable set is small and the cost objection against forward
traversal does not apply at this scale. And the input contract changes when the
milestone level lands, because `PlanResult.leaf_targets` is shim **S9**.

Where it is *called from* today is a defect, not the design: `execution.py`
composes fresh at every leaf (`:506`) and every map member (`:742`), while
`PlanResult.pipeline_refs` is used only for provenance. Under ADR-0206 §3 the
loop runs in planning. The caller moves at **C4R3**; the call sites are untouched
here.

### 3.2 Output

- The `Pipeline` (the recorded path), or
- a verdict of no-route carrying, for `required_input_unproducible`, a **list**
  of `(capacity, datastate)` pairs. A forward walk finds *every* capacity that
  came up short, not the first one that blocked construction, so the plural in
  the verdict spec is load-bearing rather than incidental.
- the ledger, returned — not written (§5).

**Demanding a missing input is not this subsystem's job.** That contract already
exists as `mindsos_capacity/needs_input.py` (the (B) half of the L4 Phase-1 seam
design, arc-solver its named first consumer). CGT reports; L4 decides whether to
ask.

---

## 4. Input groups are retired entirely

`INPUT_GROUP_FOLD` and `INPUT_GROUP_ANY_OF` are both retired, which leaves
`INPUT_GROUP_ALL_REQUIRED` as the only member of `INPUT_GROUPS`. A field with one
legal value is not a field: **"all declared inputs are required" is simply what
declaring inputs means.** So the concept goes, not two of its values.

**What comes out:** the `input_group` declaration field; ADR-0159 §amendment-1,
which introduced it; the fold branch at `capacity.py:322` and the `any_of` check at
`:326`; the membership check at `capacity_layer.py:452`; `_input_group_of`; the
finder's three-way resolution; and the corresponding export-slate entries.

**What this unblocks.** ADR-0156 §am deferred *the graph form of `input_group`* — a
typed hyperedge plus a hyperedge-aware view walk — and that deferral is recorded as
owned by no item and blocking the pipeline store. With the concept retired, the
deferred item **stops existing**. It also removes the reason `_input_group_of` reads
the declaration registry instead of the graph (Decision 8).

### 4.1 Why `fold` goes

Zero declarations in core, nilm, arc1, arc3, robot or bongard. `exceptions.py:59`
states it is unenforced; `capacity.py:322` short-circuits input validation for it,
which is half of D-A. It has no aggregation step, which is *why* D-C exists: N
producers write to one blackboard slot and overwrite each other because nothing
names a reducer.

Many-into-one is already served, shipped and adopted: a collection DataState, a
map, a fold milestone (`execution.py::_run_fold_milestone`), and the `reduction.*`
family (ADR-0204). nilm uses it.

**Modelling producer fan-in as a collection is a requirement, not a fallback.** It
is the only form whose shape is derivable from declarations and therefore
verifiable against the level below; the only one with somewhere to put the
aggregation; and the only one where installing a Skill cannot silently change the
shape of a pipeline belonging to another Skill — which is what C2R4a exists to
prevent. Late binding is the hazard, not the feature.

If open participation is wanted later it is **declared** — a collection whose
membership rule is stated — not inferred from the registry. Skill-packaging chat.

### 4.2 Why `any_of` goes

Also zero declarations. Unlike `fold` it was enforced (`capacity.py:326`), it has
no replacement — there is no optional-input mechanism — and ADR-0071 §am-2 names a
motivating consumer, ARC's `build_correspondence`. That case is superseded by the
retirement; a capacity that could work from either of two inputs is declared as two
capacities.

**Decided against the recorded objection**, which is retained here so it is not
rediscovered as new: the need is named in an Accepted ADR and the declaration is
missing only because arc1's solver is disjoint from MindsOS. If it returns, it
returns as a proposal with a consumer attached, not as a revival.

**Measured consequence:** `any_of` and `fold` were the sole source of **D-E**
(duplicate-step pipelines). With them gone, the `in_flight` guard shipped at
`4fd8baa` has nothing left to catch — see §6.

## 5. Layering

- **L4 decides** when and where the walk runs, and which `selection_policy` is in
  force. Consistent with ADR-0071 §am-2.
- **L3 returns** the ledger. It cannot write to L5 — ADR-0010 §I-S1, enforced by
  `tests_server/integration/test_layer_isolation.py`. The walk also has no MM
  today (`CapacityContext.mm_handle` is optional, gated by `reads_mm`) and is
  called from `pipeline_runner.py` and `brain.py:687` where none exists.
- **L5 records a summary**, not the raw ledger. One run performs many walks
  (`execution.py` composes per leaf and per map member), so persisting every
  ledger into the per-run `capacity_mm` is volume for something mostly discarded.
- **The ledger is not a DataState.** Same ground on which the CR refused to make
  the topology one: not serialisable, and ADR-0182's codec would have to carry
  it. Derived *summaries* — missing pairs, alternatives seen, paths rejected —
  can be.

### 5.1 Ledger-capacities — direction, not scope

Capacities that consume a ledger summary and produce DataStates are accepted as a
direction. Two rules if built:

1. They run **after** the walk completes, never inside it — dispatching capacities
   in order to finish a walk is the regress withdrawn at §8.6 of the CR.
2. Their outputs may be consumed only by L4-support families, never by a
   functional category, or the disconnection invariant (§7) breaks by design.

Routed to C4R5 ("I'm not sure"), C4R8 (blame) and the dream chat. Not C3 work.

---

## 6. Conclusions from measurement

`confirmation_docs/finder_variants_model.py` reproduces both shipped phases and
adds the forward walk. Every figure below states the catalog population it was
measured against; a number without one is not evidence.

**Population:** `all_required` only, no capacity whose outputs meet its inputs,
1–2 milestone-shaped starts. 20,000 generated catalogs.

**C1. The forward walk and the shipped finder agree on reachability, exactly.**
Routes lost: **0**. Routes gained: **0**. Identical step sets: 18,067. The
rewrite cannot make a catalog stop composing.

**C2. Every divergence is the selection decision, unmade.** Forward returns more
steps in 1,917 cases, fewer in 5, same-size-different in 11. The walk keeps every
fired producer of a needed DataState; `ConjunctionFinder` takes the first by IRI.
So without a policy the walk returns a **superset**, never a wrong answer —
which is the evidence that `decision.select_producers` is load-bearing rather
than decorative. It is what reduces the superset to one producer per input.

**C3. Once `input_group` retires, nothing on `main` is defective.** D-B is closed
by the stopgap at `4fd8baa`. D-E existed only through `any_of` and `fold` — zero
duplicate-step pipelines in every `all_required` population, with or without
self-loops. D-C goes with `fold`; half of D-A goes with `capacity.py:322`.

**C4. Therefore CGT is seam work, not defect closure, and must be justified as
such.** What it delivers: the cycle stack, `in_flight` and `max_depth` are
deleted as guards with nothing left to catch; `BFSFinder` (S2) retires and
`find_pipeline` (S1) follows at C3R4; alternatives become a recorded value, which
is D-D and the PRE-5 the dream chat is waiting on; selection becomes a policy
value that can be learned. Anyone presenting this as a bug fix is working from a
superseded reading.

**C5. Capacity-level cycles are legitimate and permanent.** The failures that
motivated the stopgap were, without exception, round trips between two *different*
capacities — `d0 → d1` by one and `d1 → d0` by another. Encode/decode,
compress/decompress and serialise/parse are all of this shape. **The graph is
supposed to contain cycles.** They cannot be forbidden at registration (contrast
§7.1, which forbids only the meaningless case), so the walk must tolerate them —
and a forward walk does, for free, because it never asks whether something *could*
be produced, only ever uses what *has* been.

**C6. The conformance shapes are unchanged.** AND chain, diamond convergence and
unused-branch pruning give identical results under the shipped finder and the
forward walk.

**C7. A recorded figure is wrong.** The duplicate-step count in CR §1, ADR-0071
§am-3 and the `ConjunctionFinder` docstring is **20**; the delivered script
produces **25** on the population those documents describe.

## 7. Invariants

1. **A capacity's outputs must not intersect its inputs.** A refined DataState is
   a different DataState — `A` and `A'` are separated by the capacity that
   transforms one into the other, and that separation is what makes them
   distinct.

   **[CORRECTED 2026-08-04 — this is NOT a registration check.]** It ships as a
   **producer-eligibility refusal inside the finder**: when choosing which capacity
   produces a DataState, do not pick one that consumes it. No capacity is refused at
   registration and no brain fails to boot. Grounds: measured as a *rate* over the
   same 20,000 catalogs, the blanket predicate gives 0.46% vs 2.69% for no rule, and
   the narrow (sole-producer) variant gives **3.20% — worse than no rule**; neither is
   causal, because the failures come from cycles between two *distinct* capacities,
   which are legitimate and permanent. Separately, arc1's `rotate` / `reflect` /
   `move` / `recolor` are **closed operations on a type** — a rotated shape is a shape
   — so the refinement principle above holds for refinement and not for endomorphism,
   and a registration raise would have destroyed transform composition.

   **It does not fix arc3's case at all** (arc3 executed it): `moved` fails first and
   is not a self-loop. Symptom to expect: `viz_spec` recomposition silently loses any
   segment routing through a refused pick — a missing picture, not an error.

1b. **A consumer declaring `operand_arity=N` is not satisfied by a producer supplying
   one value.** The higher-value predicate, on the **same shared admission seam**.
   `operand_arity` is invisible to both finders today, so a composed route into a
   Form-B consumer passes compose and raises at execute — the same
   wrong-answer-reported-as-right class as D-A and D-C. Executed in two catalogs:
   **arc3 14 of 27, arc1 16 of 45**, on **both** finders.

   **Both predicates go in a shared step-admission check that BOTH finders read** —
   not `ConjunctionFinder`'s local `eligible` (`pipeline.py:489`), which `BFSFinder`
   never calls. Under #99's `_select_finder` a single start selects `BFSFinder`, so
   predicates on `eligible` alone would miss every single-start brain.

   **Form B is not routable over scalars** — a type-level walk cannot decide *which
   two* components to pair, exactly as it cannot decide which shape to rotate (§8's
   arc1 ruling). The composable form is a **collection**, and the collection input
   **keeps `operand_arity`** so the length check survives the migration. That target
   is contingent on `COLLECTION_ITERATION_ADOPTION_GUIDE.md` §14.1(a), unanswered
   since 2026-07-30; until it is answered, brain-side dispatch bridges are the only
   available shape and are correct.

2. **No capacity outside CGT may consume a `core.*` traversal DataState.** If one
   ever does, domain searches begin routing through the traversal itself. This is
   **gate-enforced by a guard test**, not a docstring — the repo's own recorded
   lesson is that chats believe the artifact in front of them
   (`tests/architecture/test_no_subsystem_ownership.py` exists for this reason).
3. **CGT is floor.** It ships Global and is not user-removable: a capacity is in
   the floor set if the system cannot serve *any* request without it. Nothing
   enforces this until C2R1 lands the Local-install path, so there is a window in
   which uninstalling `decision.select_producers` breaks finding. **That window is
   handed to the C2 chat in writing**, not left in a confirmation doc.

---

## 8. Raised and settled — do not re-open

Recorded for the same reason ADR-0071's §8 exists: a proposal that was tested and
dropped comes back unless the drop is written down.

**8.1 Stratum admissibility — a real defect, a real fix.** The CR §2 rule ("a
producer is admissible only if its satisfiability stratum is strictly below the
DataState's") is **deleted, not repaired**. Measured against the shipped finder
over 20,000 catalogs: **376 self-feeds, 246 lost routes, 243 silently narrowed
folds**. It fails on `any_of`, whose stratum is `1 + min` over inputs, so a
capacity can rank strictly below a DataState it consumes; and on `fold`, whose
later producer is genuinely later and still required, which no comparison of two
numbers can express. In a forward walk the question does not arise.
`core.reachability_strata` keeps only its reachability role;
`core.producer_candidates` carries no filter. **This entry is owed to the CR's §8
as a ninth rejected alternative, with these numbers** — a silent rewrite of §2
would make stratum filtering look unconsidered rather than tested.

**8.2 "A `PRODUCES` edge proves producibility" — not a proposal.** Raised as a
design objection and withdrawn: nobody was going to implement it, so stating it as
a decision implied an alternative that did not exist. It is a definition, absorbed
into §2.1. The counterexamples offered for it — a capacity refining its own
output, two capacities needing each other, a capacity whose input nothing
produces, a capacity given one of two required inputs — are **not failures**. In a
forward walk none of those capacities is reached, and the answer is don't-know,
which is correct.

**8.3 Self-loops as the cause of D-B — false.** Claimed and disproved in the same
session. Forbidding a capacity from producing its own input halves the pre-stopgap
failure rate and does not close it, because the real cause is the two-capacity
cycle of C5. §7.1 is worth having for hygiene and for arc3; it is not a fix.

**8.4 `fold` and `any_of` defects as blocking — they were unreachable.** Probe-level
narrowing of folds and D-C's blackboard overwrite are real behaviours of code no
catalog ever reaches. They were weighted as blocking and are not. §4 removes the
path rather than fixing it.

**8.5 Forward-walk exploration cost — dissolved.** Objected to on the grounds that
a forward walk explores everything reachable rather than what the target needs.
The walk receives `start_datastate` from a milestone, not a request (§3.1), so the
start set is one or two DataStates and the reachable set is small. Not a concern
at this scale.

**8.6 Selection as an action set — rejected.** Encoding "walk until X" and "return
the shorter path" as swappable actions keeps pluggability but puts the policy in
code, where it cannot be stored, varied per request, promoted or learned. Split
instead: traversal control is actions, producer selection is a value (§2.4).

**8.7 Method rules that produced 8.2–8.4.** State the population before quoting a
figure; a generator emitting catalogs the system would refuse to register measures
nothing. Measure each variant separately; summing across them hid that only the
pre-stopgap rule was failing and produced a wrong causal claim. Do not measure a
rule nobody proposed.

## 9. Owed

- CR §2 edited in place with §8 above added as a ninth rejected alternative.
- `20` → `25` in CR §1, ADR-0071 §am-3, and the `ConjunctionFinder` docstring.
- An ADR amending ADR-0071 §am-2 and §am-3 once built.
- The §7.3 floor rule as an ADR-0205 amendment when C2R1 lands Local install.
- The §2.5 pipeline-level cycle class, to whichever item owns the pipeline store.
- arc3: invariant §7.1 and its `grouped` self-loop.
- **ADR-0159 §amendment-1 superseded** — the `input_group` field it introduced is
  retired (§4). ADR-0071 §am-2's `any_of` case (`build_correspondence`) goes with it.
- **ADR-0156 §am's deferred `input_group` graph form is withdrawn, not deferred** —
  it no longer has a subject. Tell whichever item owns the pipeline store, since
  that deferral was recorded as blocking it.
