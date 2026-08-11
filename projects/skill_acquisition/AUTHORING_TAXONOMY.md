# Skill Authoring — Component Taxonomy (P0 spine)

**Status:** DRAFT v0.1 · 2026-08-11 · awaiting Henrique review before P1.
**Scope:** the *front half* of skill acquisition — how a domain becomes a set of grounded,
installable skill components. NOT the install/packaging lifecycle (that is
`SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md` / Phase 50 — see naming note §0).
**Source of evidence:** the only worked example is ARC (`demo/arc`:
`arc1/ONTOLOGY.md`, `LEXICON.md`, `PIPELINE.md`, `CAPACITY_CREATION_GUIDE.md`) + the
grounding invariant (memory `arc-grounding-invariant`). This doc reverse-engineers the
*implicit* method ARC walked into an *explicit*, domain-agnostic component list.

---

## §0 — Naming (RESOLVED 2026-08-11)

This effort **is** "skill acquisition" — going from a raw domain to grounded, evolving skill
components (construction **+ modification**, §6). The Phase-50 bundle/install work
(`SKILL_ACQUISITION_PROCESS_*`, ADR-0183) is renamed *skill **installation*** — it packages and
installs an already-acquired skill. **Rename of the shipped install docs is tracked as separate
housekeeping** (touches committed docs/ADRs; not done mid-design).

---

## §1 — The implicit ARC method (what actually happened)

ARC built its skill in this order. Each step produced a durable artifact:

1. **Frame the ground.** Pick the domain; define the single substrate node (`rawtask`) every
   derived term must trace back to. Decide scope (ARC-1, 2D, monochrome atom).
2. **Lexicon.** Name every term + definition (L2 `lexicon`).
3. **Ontology.** Classes + a *closed* relationship vocabulary (4 role families:
   compositional / relational / functional / attribute), is-a splits
   (`subclass_of`/`instance_of`/`exemplifies`), and the located/normalized axes (L2 `ontology`).
4. **DataStates + capacities.** Every *derived* class → a DataState; every derivation/comparison
   → a capacity, tagged to a shipped L3 family, with a `dont-know` contract, wired by
   PRODUCES/CONSUMES (L3).
5. **Pipeline/control shape.** `parse → perceive → profile → reason(induce→search→verify→apply|abstain)`.
   Mandatory cheap profilers run in `phase_1`; everything else is composed at reason-time by
   `find_pipeline`. **No higher-order dispatcher** (no capacity selects/calls capacities).
6. **Grounding check.** The done-test: a provenance walk reaches the ground from every node,
   with zero silent inline compute. Mechanized by a `tools/check_*` provenance checker.
7. **Use-case validation.** Solve ≥1 reference task end-to-end (verify on demos, produce the
   withheld answer); abstain honestly otherwise.

---

## §2 — The component taxonomy

The generalizable components, each tagged with: **layer** it targets, its **grounding
obligation**, and its **owner** (who/what produces it — Architect = human judgment,
**LLM** = machine-generatable from a contract, **Harness** = mechanically derived/enforced).

| # | Component | Layer | What it is | Grounding obligation | Owner |
|---|---|---|---|---|---|
| **K0** | **Ground / substrate** | — | the single raw input node every term traces to (`rawtask`) | is the root of the provenance DAG; defined, not derived | **Architect** |
| **K1** | **Domain scope + corpus** | — | what's in/out; where examples come from (fixture vs adapter) | bounds what must be grounded | **Architect** |
| **K2** | **Lexicon** | L2 `lexicon` | named terms + definitions | every term must also appear as an ontology class **and** an L3 node — no orphan terms | **LLM** draft → Architect curate |
| **K3** | **Ontology** | L2 `ontology` | classes + relationship vocabulary + is-a structure + axes | structure decisions (axes, role families, DOLCE-or-not) are judgment; the *catalog* is fillable | **Architect** (structure) + **LLM** (catalog rows) |
| **K4** | **DataStates** | L3 | one per *derived* class; the data nodes the graph walks | each carries an `l2_roles` backlink to its ontology class; lives in a declared realm | **Harness** (derived from K3) |
| **K5a** | **Capacity contract** | L3 | consumes/produces DataState IRIs + family tag + dont-know contract | the PRODUCES/CONSUMES topology *is* the grounding wiring | **LLM** (from K3+K4) |
| **K5b** | **Capacity body** | L3 | the pure compute (off-graph helper; ARC keeps bodies inline/stub per D3) | I/O interface is fixed by K5a → LLM cannot drift it; correctness checked by harness | **LLM** (against fixed contract) + **Harness** (test) |
| **K6** | **Pipeline / control shape** | L4 | what runs mandatorily (`phase_1` sweep) vs composed at reason-time (`find_pipeline`) | preparation set stays small + universal; reason-time stays graph-composed | **Architect** |
| **K7** | **Reasoning convention** | L4/L3 | induce→search→verify→apply\|abstain; rule representation; MDL; abstain semantics | hardest, most judgment-heavy; abstain is structural, not low-confidence | **Architect** |
| **K8** | **Grounding checker** | tooling | provenance-DAG walker; the done-test made executable | proves K0–K7 grounded — but at **two distinct levels** (§5): *transcribed* (topology registered) vs *executed* (the layer actually runs it) | **Harness** |
| **K9** | **Use-case validation** | tooling | end-to-end solve on a reference task | demonstrates the composed skill works, not just type-checks | **Architect** (picks task) + **Harness** (runs) |
| **K10** | **Change unit + blast radius** | tooling | a *modification*: target component + change + the recomputed set of downstream provenance dependents | re-runs K8 on the affected subgraph only; reports new orphans **and** executed→transcribed downgrades; pins unaffected contracts | **Architect** (declares change) + **Harness** (computes radius, re-grounds) |

---

## §3 — The owner split is the whole design (the Goal-1 / Goal-2 tension, resolved)

Goal 2 ("isolate components → hand to an LLM") and the grounding invariant collide *unless* the
boundary handed to the LLM is the **contract, never the component**:

- **LLM gets:** K2 drafts, K3 catalog rows, **K5a contracts** (fixed in/out DataState IRIs +
  family + dont-know), and **K5b bodies against those fixed contracts**.
- **LLM never decides:** K0/K1/K6/K7 (judgment), the *axis/role-family structure* of K3, or the
  produces/consumes wiring (that's the grounding skeleton — Harness owns it).
- **Why this works:** the body's interface is pinned by K5a, so a generated body can't invent
  ungrounded inputs; grounding is enforced by K8 (the provenance walker) + a unit test, **not**
  by trusting the model. This is exactly ARC's D3 discipline (registered Capacity = topology +
  provenance; real compute = an off-graph helper).

**Corollary:** Goal 1 (the validation reference) is just K8's criteria made human-readable, applied
per-component. The reference and the LLM contract are two projections of the same K-table — which
is why the taxonomy is the spine and both deliverables derive from it (P1).

---

## §4 — Open questions for P1 (do not answer yet)

1. **K3 structure transfer.** ARC's axis/role-family structure is perception/spatial-shaped. Does
   it survive a lexical (WSD) or symbolic (FOL) domain, or is part of K3 itself domain-specific?
   (This is the P2 generalization test; flagged early because it bears on how much of K3 is LLM-fillable.)
2. **Teach vs transfer vs acquire.** The validation reference must state *which* it validates. Peer
   transfer (Local↔Local, robot DM-7) and human teaching are different mechanisms from
   acquire-from-scratch; the grounding done-test is common, the provenance *source* differs.
3. **Reconciliation hook (standalone caveat).** Per the locked scope this is standalone, but a skill
   that never maps onto Phase-50 bundle slots can't be installed. K2–K5 map cleanly (L2 content /
   L3 DataStates+capacities); K6/K7 hit the "opaque L4 slot" gap. Reconcile at P2, don't bolt now.

---

## §5 — Findings from the live (unfinished) ARC solver — 2026-08-11

ARC is the only worked example, but it has **not passed its own done-test** (most of the reason
stage is registered topology, not executed). Treat it as in-progress evidence, not a template.
Two findings sharpen the taxonomy:

1. **Grounding is two levels, not one (D3-spike).** The registered reason-layer topology and the
   executable solver are currently **disjoint** — the solver computes inline and never invokes the
   layer. So "grounded" splits into **transcribed** (the provenance DAG exists in the graph) vs
   **executed** (the composed pipeline actually runs through `capacity_layer.invoke`). Only one
   capacity (`touching_delta`) is executed-grounded today. **Consequence for K8/K9:** the validation
   reference must report *both* levels per component — transcribed-but-not-executed is the dominant
   real state and the reference must name it, not score it as "done." This is the single most useful
   thing ARC teaches about validating a teach/transfer.

2. **The composer is itself a component with a soundness obligation (D-A).** `find_pipeline` (BFS,
   type-static, value-blind) was proven to compose multi-input reason capacities **unsoundly** (fires
   on one input, drops the rest; folds collapsed to singletons). It is sound only for linear
   perceive/transform chains. Reason-time composition of conjunctions/folds needs a separate
   `ConjunctionFinder` (backward hyperpath) — ARC's CORE PROPOSAL §5 (parts 1–4 implemented). **K6 is
   therefore split:** the *control shape* (what's mandatory vs reason-time) and the *composition
   mechanism* (which finder, with what soundness guarantee) are distinct sub-components, and the
   second carries a verifiable soundness obligation. A skill author who picks the wrong finder gets
   silent wrong answers, not a failed grounding walk.

3. **Profile filtering is value-aware, not topology-aware (D7).** Comparators always emit their Delta
   (value `None` when no change), so the type is never topologically absent — a value-blind finder
   can't prune per-task. The per-task filter is an instance-level L3 predicate over swept values.
   Minor for the taxonomy, but it's why K6's "mandatory sweep" can't be expressed as graph topology.

---

## §6 — Acquisition is a lifecycle, not a pipeline (modification in scope) — 2026-08-11

Per Henrique: skill **modification** is part of acquisition. This reframes the process from a
one-way build (domain → finished skill) into **CRUD-with-re-grounding over the K-table**. Each
component (K0–K9) can be *created*, *modified*, or *retired*; K10 is the cross-cutting mechanism
that keeps grounding intact across changes.

- **Construction = modification with nothing pinned.** A from-scratch build is the degenerate case
  where every contract is new. A modification is construction with most contracts **frozen** — which
  is *why* modification is more LLM-tractable per component (fixed neighbours) yet more dangerous in
  aggregate (the author can't see the blast radius; the harness must).
- **The defining work of modification is blast radius, not generation (K10).** A change to one
  component invalidates its downstream provenance dependents. The harness walks the same DAG K8 uses,
  scopes the affected subgraph, re-grounds *only* that, and reports two failure classes: **new
  orphans** (dangling provenance) and **executed→transcribed downgrades** (e.g. a changed K5a contract
  orphans its K5b body). ARC has neither — reversals are tracked by hand in `ONTOLOGY §4`.
- **Reuse concepts, mind the gap.** Version-a-component / deprecate-not-delete / pin-dependents mirror
  D'1 retention + node deprecation — but those are *runtime/episode* state. Design-time authored
  revision (ARC's ontology v0.4→v0.9) has no shipped machinery; K10 is new.
- **The validation reference IS the modification check.** Goal 1's reference is not a one-shot gate;
  it is the re-grounding walk re-run after every change, two-level per component (§5.1) + K10's two
  failure classes. Built against ARC's *current* state, it doubles as a live progress audit.

### §6.1 — Two kinds of change (the surface accepts both; check-depth differs — §7)

- **Authored (design-time)** — a human/LLM-author revises ontology/capacities; recorded as
  decisions/ADRs; re-grounded via K10. **What ARC does.** Touches *structure* → full blast radius.
- **Learned (runtime)** — the promotion loop (`parameter-staging → pending-promotions →
  learned-parameters`) adjusts *parameters* from experience; already designed, WSD-owned (install
  log S10). Touches *values*, not topology → cheap path (K9 re-validate, no K10). Lexicon stays
  `ADMIN_AUTHORED`.

Both enter the **one unified surface** (§7); the surface dispatches check-depth by what the change
touches. The learned *mechanism* (when/how the loop fires) stays WSD-owned — this process owns only
the change-set interface it presents to and the re-grounding it runs.

---

## §7 — The unified modification surface (RESOLVED 2026-08-11: one surface for add + modify + retire)

Per Henrique: one surface to add new skills **or** modify current ones. Design = a **transactional
change-set over the K-table**, applied to a (possibly empty) prior grounded state, then re-grounded.

**The operation (one shape for all of create / modify / retire):**

1. **Declare** a change-set: ops over K0–K10 (`add` / `modify` / `retire` a component). Create =
   empty prior state (blast radius = whole graph). Modify = diff (blast radius = downstream
   dependents). Retire = removal (dangling-dependent check).
2. **Preflight** (reuse install S4): collisions, unknown roles, realm conflicts, missing requires.
3. **Topo-order** (reuse `kahn_sort`): apply ops in dependency order — a capacity can't ground
   before its consumed DataState exists; re-grounding waits until the *whole* set is applied
   (mid-transaction would see transient orphans).
4. **Fill** (LLM): freeze unaffected contracts; the LLM regenerates only in-scope K2/K3-rows/K5a/K5b.
5. **Re-ground** (the genuinely new step): run K8 over the affected subgraph; dispatch check-depth —
   *structural* change → K10 blast radius (orphans + executed→transcribed downgrades); *value*
   change → K9 re-validation only.
6. **Commit or atomic-abort** (reuse install): on any failure, abort the whole change-set; on
   removal, **deprecate-not-delete** + reverse-dependency refuse (reuse de-install semantics).

**Why this is mostly built:** steps 2/3/6 are the Phase-50 install transaction re-pointed at
authored content. The two new pieces are **the change-set vocabulary over K0–K10** and **the
re-grounding step (5)**. The surface's output — a grounded, validated change-set — is exactly what
the installer packages into a bundle, so acquisition → installation hands off on the same shape
(closes the P2 reconciliation hook early).

**Trap avoided:** unify the *interface*, not the *cost*. One vocabulary; check-depth scales with
what the change touches (structure vs value). Flattening it either under-checks structural changes
(silent orphans) or over-checks value changes (every runtime tweak pays a full re-ground).

---

## §8 — Stage model: logical-design → prototype → commit → package (2026-08-11)

**Correction to the P0 framing:** ARC is **not** built as MindsOS code. It is designed *logically
first* (world-model, capabilities, reasoning), with *suggested* MindsOS housing, and prototyped in a
spike before any commitment. Per Henrique this is itself a process worth formalizing. It adds a
**stage axis** to acquisition and makes grounding/validation **stage-aware**. It also *explains* §5:
the transcribed↔executed gap is not a defect — it is the prototype↔commit boundary, and ARC is
mid-prototype.

Each K-component (K0–K10) carries a `housing: suggested | committed` status; the **same** unified
surface (§7) operates throughout — `commit` is just the op that lowers suggested → committed.

- **A — Logical design.** Define the K-table logically; housing = *suggested* ("this would be an L3
  capability," "this an L2 ontology class"). Artifacts = ONTOLOGY/LEXICON/PIPELINE-style docs. No
  MindsOS registration.
- **B — Prototype + test.** Build a spike; run the use-case task(s); iterate hard — formats churn,
  so this is where the §7 surface and the LLM fill (Goal 2) earn their keep. Inline bodies,
  off-graph compute, #8-only solutions are **allowed here**. Grounding checked *logically* (every
  term in ontology + lexicon + intended-L3; provenance-to-ground on the logical graph; nothing
  computed silently that isn't named).
- **C — Commit / ground.** Lower suggested housing into real MindsOS form: register
  DataStates/capabilities, wire PRODUCES/CONSUMES, invoke the layer. Flips housing suggested→committed
  and grounding transcribed→executed (§5).
- **D — Package / install.** The Phase-50 bundle (renamed *installation*, §0).

**The §5 two grounding levels are the stage-exit bars:** logical/transcribed = exit bar for **B**;
executed = exit bar for **C**. The validation reference is therefore **stage-aware** — at B it
*flags* un-committed housing + checks logical grounding; at C it *enforces* executed grounding.
Applying C's bar during B is the failure mode that makes a reference useless (screams every iteration).

### §8.1 — The discipline that makes logical-first safe (the integration risk)

Logical-first defers MindsOS-integration risk; that is acceptable **only if fit is checked
continuously**. ARC is the counter-example — `find_pipeline` can't soundly compose multi-input reason
caps (D-A) and the reason stage is still inline: fit problems found late, after heavy logical
investment. So Stage A/B must carry a **MindsOS-fit checklist** forward as live design rules:

- no higher-order dispatcher (no capability selects/calls capabilities via the layer);
- every relationship fits the 4 role families (compositional / relational / functional / attribute);
- composition expressed as the native compositional hyperedge;
- every capability tagged to a shipped L3 family + carries a dont-know contract;
- multi-input / fold composition has a *sound* finder, not BFS `find_pipeline` (K6 composition obligation, §5.2);
- provenance-to-ground holds on the logical graph.

Same content as the validation reference's structural checks, applied at B instead of C. A logical
design that violates these is *prototyping a skill that cannot be grounded.*

### §8.2 — Prototyping needs a bounded exit (or skills never finalize)

"A lot of testing before finalizing the format" is real, but without an exit criterion prototyping
runs forever. **Exit B → C when:** (1) logical grounding invariant passes, (2) use-case task(s)
solve, (3) the §8.1 fit-checklist is clean. By this bar ARC is **mid-B** (generalize-beyond-#8
unbuilt; reason stage partly inline) — the process *names* that rather than mislabeling it done.
