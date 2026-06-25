# Bongard Solver — Design Plan

**Status:** design, living · 2026-06-22 · standalone MindsOS instance (Track 2 of `intelligence_demo`)
**Posture:** critical design reviewer (skeptical, terse). This is a design record, not a build log.

**2026-06-22 — CORE ASKS LANDED ON `main` (verified against the tree, not the handoff):**
The mint triad came in **reshaped**, as two non-phase feats on `main` (`core_version` stays phase50 — NOT a tag): `composition-lifecycle Slice 1` (`b56e0ac`) + `F9` (`1be3a70`). Mapping of CC-1/2/3/4 + D1–D5 to what shipped:
- **CC-1 persistence/restart — DELIVERED (better).** F9 `FalkorDBLocalPersister`+`load_or_mint_local`/`boot_local`/`reactivate_local_capacities`; composite DAG→`learned-parameters` descriptor (ADR-0182 codec) + `COMPOSITE_DAG`+`composite_dependencies` + dep-ordered reactivation via `kahn_sort` in `mindsos_server/local_boot.py`. "Survives a restart" (§9 m2) is now substrate-true. Core named "bongard composite-persistence m2" as the consumer.
- **CC-2 — SUBSTRATE delivered; RUNNER is demo-side by design.** Shipped: `PipelineDAG`/`DAGStep`/`DAGEdge` + `Finder`/`BFSFinder`/`ConjunctionFinder` + typed `input_group {all_required|any_of|fold}` (also fixed a verified `find_pipeline` multi-input **unsoundness**). The composite `node_kind` was **deliberately deferred** ("nothing dispatches; `KIND_REACTIVE` suffices"). Per `reactivation.py`: the factory owns reconstruction + the bound `implementation`; for a composite **the executor closure is re-supplied by the consumer at boot (a demo `run_step`)**. → **Demo obligation D-M2-a:** write the reactivation factory + DAG-executor closure. Robot demo is the precedent.
- **CC-3 Global promotion — DEFERRED in core.** No `promote_capacity`; `promoted-pipelines` has no writer. Core commits to building it "when a real promoter lands, behind a target-applier seam" (placement principle, COMPOSITION_LIFECYCLE_DESIGN_LOG §0). Milestone 2 = Local mint + restart → **does NOT need it**; mint step 5 / SA-6 (Global) does. Still a future core dep.
- **CC-4 — UNCHANGED.** `capacity_layer.invoke` still hardcodes `{}`; field exists, `L4Dispatcher` delivers it. Remains the G4 demo-wiring item.
- **D1/D3/D5 WSD-decouple — RESOLVED ARCHITECTURALLY, not in code.** Core §0 "subsystems consume, core owns; promotion lands in core, WSD = producer not owner" dissolves the decoupling thesis. Mechanisms (promotion loop, ALS, index, real L4 catalog flip) ship when a consumer forces them. `CATEGORY_HINT`/`CATEGORY_DECISION` present.
- **Latent trap → D-M2-b:** Slice-2 Part 6 (invoke validates inputs vs declared `CONSUMES`) is **unbuilt** — a body's kwargs can silently diverge from declared topology. The demo composite runner must validate its own inputs until Part 6 lands.

**Process state:** these commits are on `main`, **not yet in `demo/bongard`** (this worktree still pins `phase-50-confirmed`; surfaces verified absent here, present in `MindsOS/`). Consuming them = a **deliberate pin-bump** — merge `main` (no tag) into `demo/bongard`, re-gate, update `STATE.json pinned_core`. Mac-side git. **Open decision DM-BONGARD-PIN below (§10).**

**2026-06-22 (update 2) — a follow-on core fix landed (`1f09228`); nothing I was blocked on changed.** It is a repair/hardening pass, not new capability:
- **`PipelineDAG`→`Pipeline` rename** (DAG suffix was migration-only). Canonical class = `Pipeline`; `DAGStep`/`DAGEdge` kept; `to_dict`/`from_dict`/`COMPOSITE_DAG` intact; back-compat `PipelineDAG` alias lingers. **Runner code (D-M2-a) targets `Pipeline`.**
- **Slice-1 (`b56e0ac`) was broken on `main`** — `mindsos_cli.app` unimportable; "3991 green" under-counted by 28 (baked Docker image tested **stale code**). Fixed tip `1f09228` = **4019 green with `--build`**. → **pin-bump target is now `1f09228`, not `b56e0ac`** (merging earlier would have taken a broken CLI).
- **Gate discipline (ours):** Linux gate MUST use `docker compose … run --rm --build` or the baked image silently tests stale source. Applies to the demo's RULES §4 gating.
- **Still open, unchanged:** CC-3 promotion (absent), CC-2 composite kind (deferred), Slice-2 **Part 6 input-validation unbuilt** (D-M2-b stands — runner self-validates inputs). Milestone-2 picture identical to update 1.

**2026-06-22 (update 3) — D-M2 asks RESOLVED; m2 core dependency fully closed.** Verified in tree:
- **Part 6 SHIPPED + tagged.** `invoke`/`call_capacity` validate inputs vs declared `CONSUMES` (`all_required`⇒all, `any_of`⇒≥1, `fold` not enforced v1; undeclared keys rejected). `InputContractError` (`mindsos_capacity.exceptions`, not in `__all__`); on `invoke` → `success=False` + problem-trace `error_kind=input_contract:<kind>`. ADR-0072 §am-2.
- **Tag `composition-lifecycle-s2-confirmed` = `2676b9d`** transitively carries Slice 1 + F9 + CLI-rename fix + Part 6. **This is the pin-bump target** (supersedes the `1f09228` interim). New convention: every core ship gets a `<name>-confirmed` tag (RULES §7, core repo).
- **D-M2-b RETIRED.** The runner routes through core `invoke` (validates *presence*); drop the demo presence self-check, let `InputContractError` surface. `fold` non-enforcement is irrelevant — polygon chain is `all_required`.
- **D-M2-a unchanged** — composite runner stays demo-side (`KIND_REACTIVE`, dep-order off `COMPOSITE_DAG`, executor closure at boot).
- **§7 CORRECTION:** "Promote … existing Server machinery" = the **propose/release pivot** (`PromotionItemKind.PIPELINE` in `mindsos_admin.promotion`/`mindsos_server.release`, currently `NotImplementedError`), **NOT** skill-install (ADR-0183, which installs authored bundles). m5 promotion (CC-3) = two halves per **ADR-0184**: (1) descriptor — Local `learned-parameters`→Global `promoted-pipelines` via the pivot; (2) activation — a **Global-scoped `reactivate_from_descriptors`**, else the promoted node is inert. **Open dep:** confirm operand shape vs the deferred **Part 5** (DataState operand-arity) before sizing the promotion descriptor. Build at m5 — not now.

**m2 status: core-UNBLOCKED.** Remaining gate is the Mac-side pin-bump (action below); build is mine after.

**2026-06-23 — m2 SCOPE LOCKED (probe-grounded; see the in-memory mint probe this chat).**
- **PB-1 — m2 = lifecycle proof, NOT minting power.** The probe showed a minted `square` node = m1's generic chain + a string comparison; m1 already recognizes square/pentagon, so vertex-count mint adds *zero recognition power*. m2 proves the **mint lifecycle** (teach → validate → name → persist → restart → re-invoke) with **m1 as the oracle**. Do not overclaim it as "minting works"; the hard discriminative mint is concept-mint (§9 step 5). One-node-per-shape (G1.2) is justified by downstream referenceability + promotion granularity, not recognition.
- **PB-9 — params live IN the descriptor.** Persist the calibration (`per_edge_tau`, `plateau_min_frac`, band, τ_fit) into the `learned-parameters` descriptor so a restart restores the *exact* calibrated capacity, not a recalibration. Otherwise "survives a restart" is only half-true.
- **PB-10 — teach-triggered, not autonomous.** Bongard has no organic recurrence signal (you hand it the shapes), and SA-1 "what counts as recurring" is ⚠ unstressed here. So m2 mints on a **teach** trigger; autonomous detection (SA-1) defers to a producer with a real recurrence signal (WSD). Attribution: the shared invariant (e.g. n=4) is computed by a **registered capacity** [SYSTEM], the label comes from **the human** [HUMAN], Claude stays out of the runtime decision path (the probe's closure-comparison discriminator was Claude-in-the-loop — m2 must register it as a predicate).
- **First build = the durability de-risk (the only unproven piece).** Persist a nested-`COMPOSITE_DAG` descriptor through `FalkorDBLocalPersister` → fresh KL/CL → `boot_local` → `invoke` the minted composite, no code registration. The in-memory probe covered everything else; the F9 round-trip test only carried a *flat* `steps` list, so the nested-dict-through-the-real-persister path is untested. Linux-gated (needs live FalkorDB). Fail fast here before the teach/naming layer.
- **Deferred:** `per_edge_tau` scale-hardening (only bites at r<22 / mixed shapes — not currently generated); revisit if held-out emits r<22. CC-3 Global promotion stays the m5/ADR-0184 seam. Scope fence: **Local mint + restart only.**

**2026-06-23 — m2 invariant model DECIDED + recognition layer BUILT (supersedes the A/B/C invariant question).**
- **Invariant = an atom-relation predicate, not a feature vector.** A minted shape is a conjunction of relations over a universal atom basis — **vertices** (count), **segments** (normalized lengths), **angles** (interior degrees): `square = n==4 ∧ sides-equal ∧ angles==90`. Auditable, compositional, scale/rotation-invariant (relations compare atoms to each other). This collapses shape-mint and concept-mint into one mechanism (PLAN §2) — m2 is a minimal slice of it (count + side-equality + angle-target), the full relation vocabulary (isosceles/rhombus/parallelism…) deferred.
- **Two tiers (Henrique's formula/tolerance split):** *definitional law, built-in* = interior angle sum `(n-2)·180` (a parse-**validity** gate; discriminates nothing among n-gons — every quad sums to 360); *minted definition, example-derived* = the relation set, where the **formula sets each target** (regular n-gon angle `(n-2)·180/n`, so 90° is derived not learned) and the **example spread sets the tolerance width** (floored — the τ_fit discipline).
- **Durability de-risk PASSED on Linux** (31→ now 35 suite): nested `COMPOSITE_DAG` descriptor round-trips `FalkorDBLocalPersister` across a restart + reactivates + invokes (`test_m2_durability`). The only unproven m2 piece is now closed.
- **Recognition BUILT as 3 `[SYSTEM]` capacities** (`bongard/shapes.py`, PB-10 — no Claude in the decision path): `extract_shape_atoms` (SHAPE→atoms), `induce_definition` (teach examples→definition, the learning step), `matches_definition` predicate (atoms+definition→bool). Validated through `cl.invoke` (`tests/test_shapes.py`, 4 tests): teach 3 squares → accepts held-out squares, **rejects rectangles (down to 1.2:1), rhombus, pentagon**. Induced def `{n=4, target 90°, side_tol 0.06, angle_tol 2°}` (tols floored — clean squares measure tight); honest boundary ~1.1:1 rectangle.
- **Mint flow BUILT (option A — minted node is a predicate over the parse).** `bongard/mint.py`: a minted shape consumes `SHAPE` and runs `extract → matches[stored definition]` (perception is shared, run once). `mint_shape(solver, kl, persister, name, examples)` perceives → induces the definition → writes the `learned-parameters` descriptor (`COMPOSITE_DAG` + definition dict + calibration params, PB-9) → persists → registers Local (usable now). Human name supplied at teach time (Local-only; no Local→Global yet). `shape_reactivation_factory` rebuilds the runner at boot and seeds the stored definition. `Solver` got a backward-compatible inject hook (`cl=/session=/register=`) so perception runs on the durable CL. In-memory test green (factory-built runner discriminates square vs rectangle through `cl.invoke`); the **restart integration test** (`tests/test_mint.py::test_taught_square_survives_restart`: teach square → persist → fresh KL/CL → `boot_local` reactivates → reloaded node still accepts squares / rejects rectangles, no code registration) is the m2 milestone — Linux-gated.

**2026-06-20 session — decided + recorded (pointers, not restated):**
- **E** proposer = deterministic ε-sweep (seeded-RANSAC fallback); learned deferred behind the F contract under the restated §1 bound. (§10 E)
- **H** budget = threshold-primary; caps K + R=1 monotone re-segment; dormant op ceiling. (§10 H)
- **G1** mint representation = a persisted L3 **composite** node (declarative pipeline-over-seeds), backed by `promoted-pipelines`+`learned-parameters`; needs core CC-1/2/3. (§7 ratified block + §10 G1)
- **§12** = ten code-grounded gaps verified vs phase50. **§13** = core-change rationale. **§14** = autonomous skill-minting process (two-path intake + neural-leaf generalization).
- **Two-path model** (composite=mint=auditable vs primitive/neural-leaf=install=opaque) was *discovered by designing this solver*; recorded for generalization in `../skill_acquisition/SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md §6` (tagged `bongard-solver`).
- **Handed to the core-modification chat:** `CORE_CHANGES.md` (CC-1/2/3/4) + `WSD_DECOUPLING_DIAGNOSIS.md` (D1–D5: detach general mechanisms from WSD).
- **Status:** design saturated vs phase50. Milestone-1 perception = only no-core-dependency build lane; milestone 2+ gated on the core chat.

---

## 0. What this is / scope boundary

A **standalone MindsOS instance** that solves **Bongard-LOGO** via auditable analysis-by-synthesis. Primary purpose is a **development forcing-function**: build real, currently-missing MindsOS features (perception capacities, the mint Skill) and surface integration gaps. A demo is a **byproduct**, not the goal.

- **Ours (build here):** the Bongard instance — its ontology + perception capacities + concept capacities + verifier + parse/control wiring.
- **External, coordinated:** the **Mint Skill** belongs to the **autonomous skill-minting process** — *not* the shipped `skill-acquisition` chat (tag `skill-acquisition-2026-06-09`), which designed only **bundle installation** (TOML manifest + data → admin-gated Global install). That closed chat **routed the autonomous promotion/minting loop to WSD** (producer-agnostic contract). So minting is genuinely undesigned; the Bongard mint is a **producer** under WSD's producer-agnostic contract and should conform to / inform it, not fork it. We design the **Bongard-grounded instance** of mint here as the worked example (see §14 for the proposed general process). **Reuse** the shipped install/promote tail; design only the minting front.
- **ARC:** reference-only. Patterns transfer (analysis-by-synthesis, the capacity-chain shape); artifacts/realm/ontology do **not**. ARC is reserved for another priority.

---

## 1. Capability target (the claim, deferred but anchored)

> Acquire a new, named, reusable concept from a handful of examples — by minting structure over an ontology — such that the result is an **inspectable parse**, it **generalizes** to held-out instances, it **abstains honestly** when it can't, and acquisition costs **few examples and no large training run**.

= auditable + low-compute-*learning* + bounded generality. "Can learn anything" is dropped as a selection criterion (proven by depth + transfer, not breadth).

**Thesis upgrade specific to this instance:** perception is **built from scratch as an auditable parse**, not a borrowed black box — licensed *only* because the shapes are clean/synthetic. This pushes the auditability moat down into the leaf.

---

## 2. Architecture (one frame)

Analysis-by-synthesis: **ontology graph (structured generative model) + perception leaves + a proposer + verify/backtrack/abstain inference + a mint Skill.** Perception and concept-acquisition use the **same** planning/mint machinery — pipelines composed from pipelines; a named shape/concept is a *minted composite* over seeds.

---

## 3. Domain

**Bongard-LOGO**, **clean synthetic shapes**, **polygon family first (curves deferred)**.

- **Held-out generator** = primary concept signal (sample fresh +/− per problem → measurable generalization, kills few-shot underdetermination).
- **Reconstruction / fit-error** = per-percept signal.
- Cheap symbolic verifier was *swapped*, not lost: held-out + reconstruction are the verifiers; the verify→blame→replan→abstain machinery is intact, just running on those signals.

---

## 4. Bongard instance — ontology (built fresh, own realm)

- **Atom layer (new, between Point and Shape):** **segment** + **vertex**.
- **Vertex = shared endpoint** of two segments (not an infinite-line intersection).
- **Shape = closed simple polygon.** `triangle ⟺ 3 segments, 3 vertices, each vertex joins exactly 2 segments, closed simple loop` (closure + simplicity exclude the hash/asterisk/3-loose-strokes cases).
- **The polygon *schema* is definitional** (closed-simple-loop over segments/vertices); you don't learn what "a polygon" is. But **individual shapes past the triangle seed are minted composites** — square/pentagon are acquired (milestone 2), not pre-given templates. (Resolves the §7/§9 tension: only the triangle seed is handed in.)
- **Two atom families:** straight (segment, vertex) — now; curved (arc/curvature) — deferred as a second family.

---

## 5. Perception subsystem (built, auditable)

**Capacity chain** (each a registered L3 capacity; recursive sub-pipeline — pipelines from pipelines):

| Capacity | consumes → produces | role |
|---|---|---|
| `pixels → point-set` | image → foreground point-set | grounding leaf, **swappable / domain-specific** |
| `point-set → segments` | point-set → straight segments | grounding (line-art) |
| `segments → vertices` | segments → shared-endpoint vertices | derivation |
| `{segments,vertices} → polygon` | → `Shape{type,…}` | comparator/predicate |

**Control = hypothesize-verify-backtrack loop** (completed shape):

1. global pass → candidate figures (individuation) + gist
2. per figure: proposer emits ranked atom hypotheses
3. verify top hypothesis — **reconstruction preferred** (render & compare), reusing detector/generator pairs
4. **conclude | re-hypothesize | re-segment | abstain** (dual backtrack: wrong label *or* wrong boundary; abstain on budget exhaustion)
5. assemble scene parse; concept hypothesis *may* feed back top-down to re-rank/disambiguate (the F seam — **interface-only at v1, body deferred**, see §F)

**Confidence = segment-fit residual** (scale-normalized point-to-line; whole-shape reconstruction demoted to optional — see §D). Shape-level verify is symbolic. **Abstain** when a region won't fit segments (e.g., it's a curve → route to curve family or abstain).

> **Code-grounded corrections (see §12):** the shape verifier registers as a `predicate` (`NO_DONT_KNOW`) returning hard true/false — the **control loop owns the abstain/re-segment verdict, not the predicate** (G5). Grounding-leaf abstain = **emit the `CATEGORY_PERCEPTION` dont-know marker DataState** (G8). The per-figure hypothesize-verify-backtrack loop is **demo-built control**, not shipped L4 (whole-pipeline replan only) (G6). τ_fit/K from `learned-parameters` are **not auto-delivered to read bodies** — the demo wires the snapshot (G4).

**Reusable feature = the grounding contract:** raw signal → normalized point-set → ontology shape. Generalizes as **"any point-set," not "any picture"** — the grounding leaf is swappable per domain; everything above it is shared.

**F — integration contract (DECIDED 2026-06-20, interface-only):**
- **Bottom-up half:** perception hands up `Shape{type, vertices, pose, confidence}` **or abstain**.
- **Top-down half:** down = `ParsePrior{ expected_atoms, expected_figure_count, pose_hint?, source_concept_iri, strength }`. Three rules: **rank-not-score** (reorders the candidate queue / breaks ties; never changes reconstruction-fit confidence, never injects a candidate bottom-up didn't generate), **held-out firewall** (priors apply only to training-example parses; held-out is always parsed prior-free — that is the generalization verdict), **provenance** (`prior_applied` tag).
- **Build now (mandatory seam):** the two interface slots only — proposer returns its **ranked candidate list** (not a collapsed winner) + accepts an optional `ParsePrior` **as a consumed DataState** (default unbound — *not* a `CapacityContext` field; that surface is frozen and read-bodies get a dict, see §12 G7). **Defer the `re_rank` body.** Empirically checked against the NVlabs dataset: Bongard-LOGO's clean-polygon subset never produces a genuine ambiguous-parse tie (vertices are exact via the action program; hard images = curves / edge-decoration / open free-form strokes → all **abstain**, not tie). So for this instance the body is **never built** — the reusable asset is the contract, not the algorithm.

---

## 6. Concept subsystem

A **concept = a predicate over the scene parse** (objects + relations). Search over predicates → verify against the **held-out generator** → conclude | abstain. Concept artifacts live in L2 `concepts`. The iconic open-ended Bongards will be **honest abstains**, not solves — that's the moat working, not a failure.

---

## 7. Mint Skill (Bongard-grounded instance → feeds Skill-Acquisition)

> **Code-grounded correction (see §12 G1/G2/G3/G9):** the durable mint artifact is a **`promoted-pipeline` + `learned-parameters` record**, not a free-standing "new L3 node" (no pipeline-nesting, no capacity-node persistence, no capacity-node promotion verb ship at phase50). The L3 node is an in-memory handle rehydrated from that record. This also makes "composite, never a primitive" structural (a pipeline *is* a composition of seeds) and collapses steps 4+5 into one admin gate.

> **G1 ratified — mint representation (DECIDED 2026-06-20; REVISED 2026-06-20 once core changes were put on the table).**
> Core insight: a capacity is a **bound Python implementation**, which is *why* the index is in-memory and there is no node-promotion verb (arbitrary Python can't round-trip). But a **composite's body is declarative — a pipeline over seeds = graph data** — so composites *can* persist + promote; primitives can't. The §7 "composites auto / primitives human" rule **is the persistence boundary**, not bureaucracy. This makes the proper unit a real L3 node, not a workaround record.
> - **G1.1 unit** = a **persisted L3 composite capacity node** (its declarative pipeline-over-seeds body is its persistence backing in `promoted-pipelines` + `learned-parameters`). Requires core **CC-1/CC-2/CC-3** (§13). *(Earlier pick — an ephemeral handle over a record — was the demo-side workaround for those missing core features; superseded now that a core chat will land them.)*
> - **G1.2 granularity** = **one distinct named composite node per minted shape** (square ≠ pentagon), *not* a single `polygon(n)` with a stored integer — that trivializes shape-mint into parameter-fitting (the §11 "pipe-runs ≠ minting" trap). Polygon family needs **no pipeline-nesting** (flat composite over atom capacities); defer nesting like F/E; pressure may return at concept-mint (milestone 5).
> - **G1.3 persistence/rehydrate** = **core CC-1** (`bootstrap_capacity_from_falkordb` round-trip), not a demo boot hack. Makes §9-milestone-2 "survives a restart" true.
> - **G1.4 promotion** = **core CC-3** (`promote_capacity`): node + backing pipeline + params, atomic, via the pending-promotions audit chain, admin-gated; human-naming at the Local→Global boundary; dedup is the same gate → **steps 4+5 are one admin gate**.

Mint is a **Skill**: cross-layer intelligence. **L3-the-layer is extensible; each capacity-function is fixed.** A minted capacity is a **new L3 node** (a *composite / specialization of seeds — never a new primitive*), with an **L2 footprint** (`learned-parameters`, `promoted-pipelines`). Adding nodes is allowed; inventing primitives is not.

**Five-step shape:**

1. **Identify** (L3, auto) — compression/reuse flags a recurring composite, or a **gap** if uncomposable.
2. **Validate** (L3, auto) — held-out/verifier confirms generalization.
3. **Provisional register** (new L3 node + L2 record, auto, **Local**, machine-named e.g. `composite_0427`) — usable immediately.
4. **Present + name** (**human**, at the **Local→Global** boundary) — show the parse + example occurrences; human supplies the label; route through `alignment` for dedup.
5. **Promote** (**Global, admin-gated** — existing Server machinery) — enters shared knowledge.

- **Composites** (self-grounding: meaning = parse) flow 1→5, provisional auto-name is fine.
- **Uncomposable structure** → `capacity-gaps` (L2) → human defines/names a new primitive. A true new primitive *requires* a human (it's un-grounded); the system never autonomously mints one.
- **Human placement:** at Local→Global, not per-Local-mint (per-mint human gating caps learning at review bandwidth and reintroduces the bottleneck autonomy was meant to remove).
- **Differentiator to foreground:** human-*namable* candidates are free from analysis-by-synthesis — the candidate is a parse you can show a person. A net's candidate is a weight cluster. Human-in-the-loop naming is a feature the architecture uniquely enables, not a concession.

---

## 8. Layer mapping

**Invariant:** compute/decide = **L3** · trigger/orchestrate = **L4** · knowledge artifact = **L2** · per-task trace = **L5** · graph substrate = **L1**.

| Step | L2 | L3 | L4 | L5 |
|---|---|---|---|---|
| Perception chain | ontology atoms + learned tolerance | the 4 capacities | hypothesize-verify-backtrack lifecycle | parsed instances + chain artifact |
| Shape-mint (Skill) | new polygon node + composite + params | mint computation | trigger + promotion-proposing | source episodes |
| Scene parse | relation types | comparator/predicate | multi-object orchestration | scene instances |
| Concept search+verify | `concepts` | search + `validate` | held-out loop | concept chain |
| Concept-mint (Skill) | predicate → `concepts`/`promoted-pipelines` | mint computation | promotion-proposing | evidence episodes |
| Top-down feedback | — | re-scoring | concept prior → perception loop (F seam) | updated parse |

---

## 9. Sequence / milestones

**2026-06-22 — MILESTONE 1 BUILT + sandbox-green (29 tests), pending Linux gate.**
Package `projects/bongard_demo/bongard/` on the pinned `composition-lifecycle-s2-confirmed` core, all in-memory (`CapacityLayer()` + `DuckSession`), no `mindsos_*` edits. Chain runs through real `cl.invoke`: `pixels→point-set→boundary→segments→vertices→polygon`. Verdicts on the m1 set: triangle/square/pentagon **solve** (correct vertex count + type); circle **abstain(fit)**; open_strokes/near_miss **abstain(structure)**; bowtie **abstain(fit)**; held-out polygons (9 size/pos/rot variants) solve **prior-free**.
Build findings (forcing-function payoff — implementation surfaced these, not the spec):
- **Tracer choice is the leaf's load-bearing decision.** NN-walk stranding fabricated spurious corners; **angle-sort around the centroid** is correct *for the convex polygon family* and immune to stranding. Non-convex/concave shapes need a connectivity tracer — that is the next leaf swap (and the real home of the geometric structure gate, see below).
- **Gate taxonomy is three, not two.** PLAN §10 D's "fit gate + structure gate" splits the structure gate into **topological** (raster: single closed stroke — `topology.py`; catches open/disconnected, R=0 since re-segment can't repair topology) and **geometric** (predicate: simple/closed ring — catches self-intersection, triggers R=1). Under the angle-sort tracer the **fit gate subsumes the geometric gate** (a convex-hull reconstruction can't match a self-intersecting stroke, so its residual is high → fit-abstain). So R=1's productive path is the **non-convex seam** — unit-tested directly, not exercised by m1 rendered samples (consistent with PLAN §10 H "clean polygons individuate first pass").
- **Selection is parsimony-primary, not RMS-primary.** RMS-primary rewards over-fit N-gons and lets a fine polygon fit a circle within τ_fit (defeating the gate). Correct: among τ_fit-passers under a **polygon-complexity cap** (`max_sides`, the curve discriminator), pick **fewest vertices**. *(`max_sides` SUPERSEDED 2026-06-23 — replaced by per-edge-fit + ε-persistence conjunction; see §10 D revision.)*
- **τ_fit is scale-banded.** Normalized residual from 1px pixelation grows ~1/size, so a single-seed (r=40) calibration under-covers small shapes; the Global-default floor (0.012) covers r≈20–55 (measured: polygons ≤0.008 vs circle ~0.018). Per-problem Local recalibration is the m2+ path. Vertex-split artifacts needed a `max(abs_floor, frac·diag)` close-vertex merge to generalize across scale.
- **G4 confirmed in the build:** read bodies get a plain dict context (core hardcodes empty `learned_parameters` for reads), so the demo threads `Params` via the read-path `context` dict. **D-M2-b confirmed retired:** `input_group=all_required` + core Part-6 `_validate_inputs` enforce predicate input presence; the body does not re-check.
Modules: `ontology` `harness` `render` `signals` `leaf` `topology` `geometry` `calibration` `segments` `predicate` `control`. Tests: `test_ontology/render/perception`. **Next:** Linux gate `pytest projects/bongard_demo`, then milestone 2 (Local shape-mint on the F9/composite-persistence substrate).

1. **Perception chain on a single polygon** — `pixels→…→polygon`, with abstain. **← BUILT (above).**
2. **Shape-mint = mint milestone 1** — after triangle, mint square/pentagon from the same atoms (cheapest test of the mint mechanism; the worked example handed to Skill-Acquisition).
3. **Multi-object scene parse** (objects + relations).
4. **Concept search + held-out verify** (no concept-mint yet).
5. **Concept-mint = mint milestone 2** (the research-hard 20%).
6. **Top-down feedback** (concept → perception disambiguation).

### 9.1 Build & gate (demo ops — established 2026-06-22)

- **Package:** `projects/bongard_demo/bongard/` (modules listed in the §9 m1 block); tests `projects/bongard_demo/tests/`; `conftest.py` puts the demo on `sys.path`.
- **Gate (Linux only, `--build` mandatory):** `docker compose -p mindsos-bongard --profile test run --rm --build mindsos-test pytest projects/bongard_demo`. Without `--build` the baked image tests stale source (the bug that hid Slice-1's broken CLI).
- **Demo-gating isolation done this chat (non-`mindsos_*`, allowed on `demo/bongard`):** `docker-compose.yml` → own `mindsos-bongard-falkordb` container + no host-port publish (avoids the `mindsos-core` stack's 6379); `Dockerfile` test stage → `COPY projects/bongard_demo`. Image tags stay `mindsos:phase50-*` (doctor-test parity — do not rename).
- **m1 is in-memory** (`CapacityLayer()` + `DuckSession`, no FalkorDB). **m2 is the durable path** — real FalkorDB via F9 `boot_local`/`FalkorDBLocalPersister`; the gate stack's FalkorDB is already up for it.
- **m2 entry surfaces to verify-then-use:** `mindsos_capacity.Pipeline`/`DAGStep`/`DAGEdge` + `to_dict`/`from_dict`; `mindsos_capacity.reactivation` (`COMPOSITE_DAG`, `register_reactivation_factory`, `reactivate_from_descriptors`, `INSTALLER_SENTINEL`); `mindsos_server.local_boot` (`boot_local`, `load_or_mint_local`); ADR-0185/0186/0187 (F9), ADR-0184 (CC-3 promotion seam, m5).

---

## 10. Open decisions

- ~~**F top-down half**~~ — **DECIDED 2026-06-20** (interface-only; see §5 §F). Build the two interface slots, defer the body, never build it for Bongard.
- ~~**E proposer**~~ — **DECIDED 2026-06-20.** Deterministic, and **stays** deterministic for this instance (learned = interface-compatible deferral, not roadmap).
  - **Mechanism:** **polyline simplification + ε-sweep** (Douglas–Peucker/Visvalingam over an ordered boundary trace; sweep ε to emit the ranked candidate family F's interface mandates; rank by RMS residual, vertex-count parsimony as tiebreak). **RANSAC line-fitting = fallback** when contour-tracing fails (open/branching strokes) — **must be seeded** (nondeterminism breaks the audit story); reports the same point-to-line residual D scores on, so the verifier is unchanged. Hough **rejected** (infinite lines conflict with §4 shared-endpoint vertex).
  - **Shared knob:** one tolerance ε at `point-set → segments`, calibrated off the triangle seed (D), both *proposes* segmentations and *gates* them. Proposer + verifier share a single parameter.
  - **Why not learned (clean Bongard):** mirrors F — vertices are exact (action-program-generated), so there is no ambiguity to learn against; a trained proposer also reintroduces the §1 black-box leaf the thesis pushes down into perception. The reusable asset is the ranked-candidate **contract** (already built for F), not a trained ranker.
  - **§1 bound restated** (former INTELLIGENCE_PARADIGM_HANDOFF §4.2, **lost post-reorg — restated here, original unrecoverable**): any learned prior (proposer or concept) must be fit from *a handful of examples* and persisted in `learned-parameters` (the τ_fit discipline from D) — **never** a gradient-trained model over a corpus. A neural proposer requiring a training run is **out of bounds** for this instance. A deferred learned proposer qualifies *only* if few-shot and slotted behind the F ranked-candidate contract (no teardown).
- ~~**D reconstruction mechanics**~~ — **DECIDED 2026-06-20.** Two reframes + config:
  - **Tolerance lives at `point-set → segments`**, as a point-to-line residual — *not* whole-shape reconstruction. Shape-level verify (`{segments,vertices} → polygon`) is a **symbolic predicate** (count + closure + simplicity), no rendering. Whole-shape render-and-compare is **demoted to an optional global sanity check** (earns its place only when the leaf goes messy / borrow-the-leaf future). Departure from §5-as-written, accepted.
  - **Calibration is circular** (need ε to parse, need parses to calibrate ε) → **bootstrap ε off the definitional triangle seed** (known answer), then generalize. Ordering constraint.
  - **Fit metric:** scale-normalized point-to-line residual (normalized by figure bbox-diagonal — mandatory, size is a Bongard nuisance). **RMS = accept score; max-residual = abstain guard.** Maps onto §5's dual backtrack (RMS "good-enough line"; max-residual spike → missed corner/curve → re-segment/abstain).
  - **Abstain = two gates:** (a) *fit gate* — best segmentation RMS > τ_fit → "won't fit straight segments" → curve family / abstain (this is the curve + edge-decoration rejector); (b) *structure gate* — atoms don't close into a simple polygon → re-segment/abstain. A margin/tie gate is retained but expected **dormant** (per §F: clean Bongard yields no ties).
  - **Calibration → `learned-parameters`:** percentile from a handful of clean seed parses — `τ_fit = (max accepted residual)×(1+slack)`. Stored **Local per problem**, seeded by a **Global default**. Few examples, no training run (satisfies §1).
- ~~**H budget policy**~~ — **DECIDED 2026-06-20.** Threshold-primary, not search-budget. Decided-E (deterministic ε-sweep) makes the inner re-hypothesize loop **self-bounding** (finite candidate set); inner-loop exhaustion = "no candidate passed D's gates" = a **semantic** abstain, not "out of budget." So abstain is **threshold-driven** (D's τ_fit / max-residual / structure gate), not a hypothesis/backtrack accountant (rejected as the §11 easy-20% trap — degrades abstain reasons to "out of tries," muddies the §6 moat).
  - **Two hard caps only:** (K) ε-sweep resolution — sweep ~8–16 values bracketing the seed-calibrated τ_fit band, tuned on seed parses, stored **Local** like τ_fit; (R) re-segment depth = **1**. Plus a generous, **dormant** per-problem op ceiling as a pure safety valve (uninformative abstain, logged as such).
  - **Re-segment must be monotone:** tie the single re-individuation to D's max-residual spike (it localizes the bad corner) → split *there*. Can't localize → abstain immediately (R effectively 0). Makes R=1 a meaningful retry, not a blind one.
  - **Why R=1:** a clean polygon individuates correctly first pass; needing >1 ≈ the curve / edge-decoration / open-stroke case → abstain is the correct verdict, not more search.
- **~~D curve discriminator = `max_sides` cap~~ — REVISED 2026-06-23 (this chat, probe-grounded; design-only, not yet in code).**
  The flat `max_sides=8` cap is wrong: it abstains on legitimate high-N polygons (a clean 12-gon "plus" abstained as `fit`) and the cap is forced because at n=12 a circle and a true 12-gon are **fit-indistinguishable** (circle r=40 first passes τ_fit at exactly n=12, rms 0.0119). Replace the cap with a **two-signal conjunction**, both already computable from the existing ε-sweep:
  - **(a) per-edge fit** (not aggregate RMS): a true edge has per-edge rms≈0 (plus edges 0.000); a curve's chords bow (circle-12 edges ~0.013). Disaggregating localizes a bad region (edge-decoration / one curved side). The aggregate already half-carried this — the circle leaked only because τ_fit was loose, not because the signal was absent.
  - **(b) ε-persistence** (scale-space stability): sweep ε and read vertex count. A polygon holds a **wide stable plateau** (square=4, pentagon=5, plus=12 across ε 0.004–0.10); a curve **wanders** (circle: 12→16→20→…→8→4, no real plateau).
  - **Rule:** *polygon = a vertex count that is BOTH ε-stable across a wide band AND per-edge-fit-passing.* A curve satisfies neither at once — its only plateau (circle n=8) **fails** per-edge fit, and its fit-passing counts (n≥12) are **unstable**. This **drops `max_sides` entirely**, is fully auditable ("n=12 held across ε 0.004–0.10, every edge rms≈0"), and is scale/N-invariant.
  - **Corroboration (not load-bearing): turn-angle** is N-invariant (plus corners 90° at any sampling; circle's induced corners shrink 30→22→13° as N grows). **Edge length** is the weakest — overlaps at the n=12 collision point (circle 0.20 vs plus 0.24); keep only as a tiebreak / for mixed-shape localization.
  - **Calibration check:** the ε band must span the plateau (very tight ε fragments via pixelation; very coarse merges corners).
  - **IMPLEMENTED + VALIDATED 2026-06-23** (demo-side, in-memory sandbox). Code: `geometry.epsilon_profile` + `geometry.per_edge_max_residual`; `segments.select_polygon` rewritten (persistence + per-edge, takes the trace); `calibration.Params` drops `max_sides`, adds `per_edge_tau` + `plateau_min_frac` + a wider/denser band (lo 0.004 / hi 0.12 / k 24). **Settled thresholds: `plateau_min_frac = 0.5` (of the valid ε steps); `per_edge_tau = 0.013`.** Verified by the full **29-test `test_perception` suite, all green** = the in-scope set: convex polygons (triangle/square/pentagon) + held-out polygons at varied size/pos/rot (incl. the small r=22 case) + the standard negatives (circle/bowtie/open_strokes/near_miss). The **plus (a clean 12-gon) now solves** — the original motivation. **Both gates load-bearing:** circle is rejected by *persistence* (widest plateau 7/24 = 0.29 < 0.5); bowtie holds a wide plateau but fails *per-edge fit* (0.016 > 0.013). Threshold rationale: small in-scope polygons sit at per-edge ≈0.0105 (r≈22), bowtie at 0.016 → `per_edge_tau` between them; `per_edge_tau` shares τ_fit's r≈20–55 band (per-problem recalibration = m2+). Two tuning corrections caught by verification: pass-1 `T_edge=0.006` false-abstained clean square + held-out pentagon; pass-2 `0.010` false-abstained the small r=22 triangle → `0.013`.
  - **Out of m1 scope (NOT a validation claim): non-convex shapes.** m1 is the convex polygon family (PLAN §4; angle-sort tracer is convex-only — non-convex = future tracer swap). L-hex / concave-dart parse only incidentally and **stroke-dependently** (L-hex solves at stroke=0, abstains at stroke=1; dart abstains either way). Their abstain is acceptable/honest, not a discriminator failure.
  - **Separate logged item (NOT this discriminator): topology-gate thin-line fragility.** A 1px-stroke concave vertex leaves `endpoints=1` → `topology.analyze` reports not-single-closed → structure-abstain before geometry. `stroke≥1` sidesteps it. Tied to non-convex support; defer with the tracer swap.
  - *Owner: demo-side (`segments.select_polygon` + `calibration.Params`: drop `max_sides`, add per-edge-fit + plateau-width gate). Attribution: geometry/run-data = SYSTEM (`cl.invoke` + `geometry.epsilon_sweep`); the discriminator design = Henrique + Claude this chat.*
- **Curve atom family** — deferred; known future decision.
- **Persistence** — **confirmed in code (§12 G1/G2):** CapacityLayer is in-memory-first and ships *no* persistence path at phase50; a runtime-minted capacity node dies on restart. The durable unit is the `promoted-pipeline` + `learned-parameters` record; "survives a restart" requires a **demo-side rehydrator** (named, not assumed) that rebuilds the L3 handle from that record at boot.
- ~~**G1 mint representation**~~ — **DECIDED 2026-06-20** (see §7 ratified block: unit = promoted-pipeline + learned-parameters record; one named pipeline per shape; eager boot rehydrator; promote via existing machinery, steps 4+5 = one gate). Prerequisite to the Skill-Acquisition contract.
- **Skill-Acquisition coordination contract** — the consume/produce interface; design mint here as the worked example, hand it over, avoid divergence. **Now built on the G1-ratified unit** (pipeline+params record, not a capacity node) — hand *that* shape to the chat.

---

## 11. Standing risks

- **The concept/relational mint loop (step 5) is the genuine unbuilt research piece.** Steps 1–4 will run fast and feel like progress; the project succeeds or fails at 5. Shape-mint (step 2) is the cheap early proof the mechanism works at all. "Pipe runs" ≠ "it can mint."
- **Perception is the easy-20% trap** — buildable and satisfying while the core sits untouched. Guard the budget.
- **Don't seal perception before F's top-down half** or step 6 forces a teardown.
- **Mint-design divergence** with the Skill-Acquisition chat — coordinate or the two specs drift.
- **"From scratch" perception expires** the moment shapes stop being clean; revert to borrow-the-leaf for messy images.

---

## 12. Code-grounded integration gaps (verified against pinned core `phase50`, 2026-06-20)

From reading shipped `mindsos_*` (not the handoff). Severity: **⛔ reframes a decision** · **⚠ material wiring** · **✎ wording** · **✓ cleared**. Owner = where the fix lands (demo-side = buildable under `projects/bongard_demo/`; core-on-main = a `mindsos_*` change that must land on `main` first, then merge the tag).

- **G1 ⛔ (§2/§5/§7) — the minted artifact is a `promoted-pipeline` + `learned-parameters` record, not "a new L3 node."** Three shipped facts converge: `pipeline.find_pipeline` is a **flat v0 BFS** over the bipartite edge set ("enough to prove the vertical slice — L4's real pipeline-finder will extend this"), so **pipelines-from-pipelines / recursive sub-pipeline has no substrate**; `_capacity_index` is **in-memory** (no persistence at phase50); promotion machinery (`promote_to_global` / `promoted-pipelines` / `pending-promotions` / `CAN_*promote_pipeline*`) is **pipeline+param-scoped — there is no promote-a-capacity-node verb**. **Fix:** reframe §7 so the durable/promotable/dedup-able unit is a promoted-pipeline + learned-parameters; the L3 capacity node is an in-memory registration handle rehydrated from that record. *Owner: demo-side representation; pipeline-nesting (if ever wanted) = core-on-main.*
- **G2 ⚠ (§7/§9) — a minted capacity does not survive restart.** `CapacityLayer` is in-memory-first; no persistence path ships. **Fix:** rehydrate the L3 node from its L2 record (per G1) at session boot — **name that rehydrator**; §9 milestone-2 "survives a restart" depends on it. *Owner: demo-side. Subsumed by G1.*
- **G3 ⚠→moot (§7 / Skill-Acq) — "never a new primitive" is unenforced in code.** `capacity.py` has node *kinds* (REACTIVE/MONITOR/ADAPTER/Dream) but **no primitive-vs-composite distinction, no seed-reference field**. **Fix:** adopting G1 **dissolves this** — a promoted-pipeline is *by construction* a composition of existing seed capacities, so it structurally cannot be a new primitive. If the capacity-node framing is kept instead, a demo-side tag + registration check is required. *Owner: demo-side.*
- **G4 ⚠ (§D/§E/§H) — `learned-parameters` is not auto-delivered to read bodies.** Only `L4Dispatcher` populates `learned_parameters_snapshot`, from a **caller-supplied dict**; `capacity_layer.invoke` hardcodes `{}` and only for *write* bodies; **read bodies get a plain dict with no params**. τ_fit (D) and K (E) won't arrive automatically. **Fix:** demo wires the L2 `learned-parameters` read → snapshot (own dispatcher) or passes params as inputs / read-path context. *Owner: demo-side wiring.*
- **G5 ⚠ (§5/§D/§H) — "comparator/predicate" is two different contracts; the choice forbids the predicate from abstaining.** `comparator`→`OPTIONAL_RETURN` vs `predicate`→`NO_DONT_KNOW`; only `predicate` is a registrable `FUNCTIONAL_CATEGORY`. **Fix:** the shape verifier is a `predicate` returning hard true/false (count+closure+simplicity); the **control loop** converts a false-closure into re-segment/abstain. The abstain verdict is **not** the predicate's. *Owner: demo design — register it as `predicate`.*
- **G6 ⚠ (§5/§8) — L4's shipped lifecycle is fixed six-phase + whole-pipeline replan, not the per-figure backtrack loop.** `orchestrator.run_lifecycle` replans/invalidates the **whole pipeline** on v0 catalogs that "dispatch no real L3 capacity." **Fix:** §8 row 1 re-attributes the hypothesize-verify-backtrack loop to **demo control wiring (L4-style)**, not core L4 (consistent with §0). *Owner: demo-side.*
- **G7 ✎ (§5/§E/§F) — `CapacityContext` is frozen + read bodies get a dict.** Carry `ParsePrior` as a **consumed DataState** (migration-proof against the deferred read-path → typed-context migration), not a context field. *Owner: demo-side; wording.*
- **G8 ✎ (§5) — perception-family abstain mechanism.** Grounding leaves register under `CATEGORY_PERCEPTION` → dont-know shape = `DATASTATE_MARKER`; so D's fit-gate abstain = **"emit the dont-know marker DataState."** *Owner: wording.*
- **G9 ✎ (§7) — "route through alignment for dedup" = the admin promotion gate.** Alignment naming/validators/`similarity.py` exist, but the dedup path has "no v1 consumer; the release-ship audit gate is the canonical dedup choke point." So §7 steps 4 and 5 are **one gate**, not two; no runtime per-mint dup check. *Owner: wording.*
- **G0 ✓ (§4) — cleared.** `register_datastate(allow_new_realm=True)` with a session registers a Local `bongard.*` realm; "own realm" needs **no core change**. De-risked.

---

## 13. Proposed MindsOS core changes (hand to a core chat)

This demo is a forcing-function (§0): these are **general** core capabilities it surfaced, not Bongard-specific. Bar = "a better general way to do things, reusable in future" (2026-06-20 directive), not "Bongard needs it." **Implementation is tracked in `CORE_CHANGES.md`** (the separate log; prefer demo-side shims, log native core design, isolate any local core edit off `demo/bongard`). This section holds the **rationale**; the file holds the **state**.

**The mint triad (CC-1/2/3) is one coherent package: "make minted composites first-class persistent, promotable L3 nodes."** That is the core feature this whole project forces. It gates milestone 2; it does **not** block milestone 1 (perception registers fine in-memory at phase50).

- **CC-1 — Capacity-node persistence (FalkorDB round-trip).** Build the anticipated `bootstrap_capacity_from_falkordb` helper + persister so `CapacityLayer._capacity_index` round-trips (today: "in-memory first; persistence adapters live separately").
  *Why:* in-memory-only means every mint evaporates on restart. *For:* mint step 3, §9 milestone-2, all downstream consumers. *Constraint:* only **composites** round-trip (declarative body); primitives carry arbitrary Python → not persistable. Pairs with CC-2.
- **CC-2 — Composite capacity kind + generic composite-runner. (Linchpin.)** A `node_kind` whose implementation is a **stored pipeline over seed capacities**, executed by a real runner (replacing the v0 BFS `find_pipeline` the code says "L4's real pipeline-finder will extend"). Flat-over-seeds for v1; deep nesting is a follow-on.
  *Why:* today `register_capacity` only binds arbitrary Python — there is no declarative composite, so nothing persistable/promotable exists. *For:* the mint's core representation; the architecture's own stated "new L3 node … composite of seeds." Without CC-2, CC-1/CC-3 have nothing to operate on.
- **CC-3 — `promote_capacity` (Local→Global) verb.** Mirror `propose_for_promotion`/`promote_pipeline` for a composite node: node + backing pipeline + params, atomic, through the `pending-promotions` audit chain, admin-gated (`CAN_WRITE_GLOBAL`).
  *Why:* promotion machinery is pipeline/param-scoped; no node path. *For:* mint step 5, the human-naming boundary; dedup folds into this gate (G9).
- **CC-4 — L4 substrate auto-loads `learned-parameters` into the dispatch snapshot.** At dispatch, read the session's L2 `learned-parameters` into `CapacityContext.learned_parameters_snapshot` (today only `L4Dispatcher` delivers it, from a caller-supplied dict; CLI `invoke` passes `{}`; read bodies get a bare dict).
  *Why:* otherwise every caller re-wires param delivery. *For:* D's τ_fit, E's K, the general "a capability reads its Local params" contract. **Lower priority** — overlaps the already-deferred read-path→typed-context migration (ADR-0175 / Phase 49).

**Deferred — not now (resisting over-rotation onto core):**
- **CC-5 runtime alignment-dedup consumer** (mint step-4 auto-dedup): the admin gate (CC-3) covers it for v1; "no v1 consumer" is an intentional core deferral. Revisit only if per-mint pre-promotion dedup is needed.
- **CC-6 generalized backtracking lifecycle** (the §5 per-figure hypothesize-verify-backtrack loop generalized into L4): let the demo build + prove the shape first (§0), then propose core absorb it. Premature to spec as core.

**Stays demo-side even with core freedom (not core gaps):**
- Grounding leaf (`pixels → point-set`) — domain-specific/swappable by design (§5).
- Bongard ontology atoms + `bongard.*` realm — instance ontology (G0 already works).
- Shape-verifier as `predicate` + control-loop-owns-abstain (G5) — correct as-designed.
- `ParsePrior` as a consumed DataState (G7) — architecture-honest even with freedom; don't bolt instance fields onto the frozen `CapacityContext`.

---

## 14. Proposed autonomous skill-minting process (Bongard as the worked example)

**Scope correction (see §0):** the shipped `skill-acquisition` chat designed **bundle install**, not autonomous minting; the minting/promotion loop was routed to WSD under a **producer-agnostic contract**. Bongard mint is a *producer* under that contract. Design the **minting front (SA-1..4)**; **reuse** the shipped install/promote tail (SA-5..7 lean on the ADR-0180 gate + `installed-skills`/`promoted-pipelines`/`pending-promotions`/`capacity-gaps`). One example (clean polygons) under-constrains the general process — items tagged ⚠ are speculative, ✓ are Bongard-grounded.

**Organizing invariant (the reusable insight):** the **composite/primitive line = the autonomy line = the persistence line = the inspectable/opaque line** (G1). The system autonomously mints exactly what it can persist and inspect — **declarative composites** (pipeline-over-seeds, graph data). A **primitive** is arbitrary code/weights: un-grounded, un-persistable, opaque → it *requires* a human. So "composites auto, primitives human" is not policy; it's forced by what can round-trip.

**Two intake paths (skill-acquisition is user-facing "teach MindsOS any skill"; bongard-solver IS an instance of it):**
1. **Autonomous mint** (this §14 — the open producer front): declarative composites over seeds. Auditable, few-shot, no training run. Flows into the shipped install/promote tail as "a second producer of the same artifacts" (skill_acquisition log S10-C).
2. **Human-authored install** (the *shipped* bundle path, skill_acquisition log S1–S13): opaque artifacts — code, trained models, **neural leaves**. Admin-installed.

"Add **any** skill" = the union — autonomous where inspectable, human-install where opaque. The autonomy is **not** promised for arbitrary skills (preserves §1's deliberate narrowing + the moat).

**Neural-leaf generalization (the requested part):** a neural leaf is opaque → a **primitive** → path 2 (install), never autonomously minted. The **grounding contract** (raw signal → normalized *typed* atoms, §5) **quarantines** the leaf: black-box internals, typed output → the minted structure above it stays auditable. *Not "mint neural leaves" — "an installed neural leaf grounds an autonomously-minted structure; auditability lives above the leaf."* The clean-polygon slice uses a symbolic leaf; skill 1 (solving) **will need the neural leaf at the messy-image / curve milestone** — so this path is **planned-and-then-tested**, not hypothetical (it's the milestone that grounds §6.2). Full record + producer-front detail: `projects/skill_acquisition/SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md §6` (tagged `bongard-solver`).

> **Generalizable discovery (record, per Henrique 2026-06-20):** the **two-path intake model** was *discovered by implementing the bongard solver* — it wasn't visible from the abstract spec. Two acquired skills here: skill 1 = bongard solving (a path-1 composite grounded by a path-2 neural leaf — the two-path model in one skill); skill 2 = minting (the CC-1/2/3 *mechanism* that produces composites, not a domain skill — "acquired" by landing those core changes). Generalize both later; this is the forcing-function paying out.

| Step | Layer | New / Reuse | Grounding |
|---|---|---|---|
| **SA-1 Trigger / candidate detection** — watch L5 episodes for recurring composable structure (reuse/compression signal) or an uncomposable gap | L4 trigger + L3 compute | **New** | ⚠ — "what counts as recurring" is hand-wavy; Bongard doesn't stress it |
| **SA-2 Candidate construction** — assemble the recurring sub-structure into a composite pipeline over existing seeds | L3 | **New** (needs CC-2) | ✓ square/pentagon |
| **SA-3 Validation** — run candidate against a domain **validation oracle**; require generalization + min support *k* | L3 | **New** + pluggable oracle contract | ✓ held-out generator |
| **SA-4 Provisional register** — register composite Local, machine-named; persist backing to `promoted-pipelines` + `learned-parameters` | L3+L2 | **New** (needs CC-1) | ✓ |
| **SA-5 Present + name** — show inspectable parse + occurrences; human labels; alignment dedup | human | **Reuse** alignment; **new** presentation artifact | ✓ the differentiator (parse, not weights) |
| **SA-6 Promote** — admin-gated Global via ADR-0180 + CC-3 | Global | **Reuse** | ✓ |
| **SA-7 Gap handling** — uncomposable → `capacity-gaps`; human defines a primitive (never autonomous) | human | **New** consumer | ⚠ — polygons never trigger it |

**Cross-cutting features the general process needs:**
- **Validation-oracle contract** — the domain supplies the verifier (held-out generator for Bongard); the general process abstracts this as a slot.
- **Support threshold** *k* — don't mint one-offs.
- **Composite-only invariant** — autonomous mint emits only composites (the organizing invariant above).
- **Episode provenance** — each mint links to its source L5 episodes (auditability).
- **Inspectable-candidate artifact** — the parse shown to a human at SA-5; the architecture's unique enabler (a human-namable candidate, not a weight cluster).

**Coordination:** SA-5/SA-6 must conform to WSD's producer-agnostic promotion contract (its intended home), not reinvent it. SA-1..SA-4 (the minting front) is the open part this demo specifies and proves.
