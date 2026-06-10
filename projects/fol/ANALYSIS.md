# FOL — Analysis vs Shipped MindsOS

> ⚠️ **STALE AS OF 2026-06-09 — read `projects/ANALYSIS_DELTA_2026-06.md` alongside this document.**
> This analysis is dated 2026-05-28, before Phases 43–49 shipped. Known-stale rows
> (grep-verified): B10/D1/B15 (`learned-parameters` shipped single Phase 43;
> `sense-correlations` withdrawn + regression-guarded; FOL #4 split deferred —
> NOT aligned at v1), B6/B11/D2/D3 (L4 settled + shipped Phases 46–48), B20
> (typed `CapacityContext` shipped Phase 42; residual = L3-59), C1/C5
> (re-ground against shipped L5 + the Phase-46/47 concurrency model). The delta
> addendum is the authoritative correction; this file is intentionally left
> unrewritten.

> **Project:** First-Order Logic capacity family for MindsOS (a "skill" per the user's rename — multi-layer intelligent system to be installed via the skill-acquisition process).
> **Project status:** Mid-design. **No shippable artefact exists.** HANDOFF_latest §0 explicit: "no shippable artefact exists yet. The whole project is in design." 13 open pushbacks raised but not resolved. 2 open-decision sections (§2 analytic-rule contradictions, §3 authoritative/evaluative role rename) deferred by user. The whole project is forward-looking design propositions.
> **Analysis date:** 2026-05-28.
> **Source materials:** `projects/fol/source/` — 9 files: 2 handoffs (current `HANDOFF_latest.md` + legacy `fol_capacity_handoff.md`), 5 `_drafts/` (design plan, review, example walk, open decisions, layer summary).
> **Triage shape:** A/B/C/D same as DWF. Almost all FOL propositions are B-bin (additive design) because almost nothing of L3/L4 is shipped yet in MindsOS — the conflict surface is small but real.

---

## 1. Source-material inventory

| File | Size | Role |
|---|---|---|
| `HANDOFF_latest.md` | 20KB | **Authoritative current handoff.** §0 reading order, §1 user instruction, §2 settled vs contested, §3 thirteen pushbacks, §6 missing-but-should-have-raised items, §8 14-step dependency-ordered next-chat agenda |
| `fol_capacity_handoff.md` | 48KB | Original legacy handoff; HANDOFF_latest §0 says "most decisions in it have been challenged or revised; do not treat as authoritative" |
| `HANDOFF.md` | 20KB | Duplicate of HANDOFF_latest based on size (intermediate handoff version) |
| `_drafts/fol_capacity_design_plan.md` | 76KB | Interface-level design + 5 example walks; "several decisions in here are now contested" per HANDOFF_latest |
| `_drafts/fol_capacity_review.md` | 32KB | First critical pass over legacy handoff |
| `_drafts/fol_example_3_detailed_walk.md` | 44KB | Pedagogical end-to-end walk |
| `_drafts/fol_open_decisions_2026_04_23.md` | 36KB | Explicit decision menu; §1 partially answered, §2 + §3 deferred by user |
| `_drafts/mindsos_layer_summary.md` | 20KB | Layer overview reference; HANDOFF says "do not revise" |

---

## 2. Triage table

Almost every FOL proposition is a forward-looking design proposition (B-bin). True conflicts are limited. Bins explained at top.

### Bin A — Already implemented in shipped MindsOS

| # | Proposition | Implementing phase / file | Notes |
|---|---|---|---|
| A1 | DOLCE loaded as L2 typed subgraph (FOL settled-commitment relies on DOLCE categories as sorts) | Phase 15a `mindsos_admin/importers/dolce.py` | DolceImporter writes `ontology` Global role-graph |
| A2 | OEWN loaded as L2 typed subgraph (FOL uses for lexical lookup in sense correlations) | Phase 15a `mindsos_admin/importers/oewn.py` | `lexicon` Global role-graph |
| A3 | Layer architecture L0-L5 (FOL builds on it) | Phase 02-36 entire stack | Architecture per `[[project-mindsos-architecture]]` |
| A4 | Fixed-not-learned L3 invariant (FOL settled §2.1: "Pluggable prover backends behind a `Prover` Protocol" implies L3 capacities are fixed) | Phase 27 + ADR-0084 (`l3-capacities-fixed-not-learned.md`) | L3 capacities are not learning artifacts |
| A5 | Pipeline-level confidence on `promoted-pipelines` (FOL §2.1 commitment) | ADR-0094 + Phase 13 `mindsos_knowledge/schemas/promoted_pipelines.py` | Schema shipped; population deferred to L4 |

### Bin B — Not implemented + no conflict (additive forward-looking design)

The bulk of FOL is here. Every B-row needs a future-chat go/no-go decision; none conflicts with shipped MindsOS.

| # | Proposition | Where it would land in MindsOS |
|---|---|---|
| B1 | Many-sorted FOL with DOLCE categories as sorts (`AG`, `PD`, `ED`, `Q`, `T`, `ART`, `SA`) (FOL §2.1) | L3 capacity registration metadata; capability declarations reference sort names |
| B2 | Equality (`Eq`) as first-class AST node, not built-in atom (FOL §2.1) | L3 prover-backend capacity input contract |
| B3 | Five epistemic tags on ledger: `observed | inferred | assumed | hypothesised | retracted` (FOL §2.1) | New L2 role-graph (proposed name `fol-ledger` or similar) + edge properties on every ledger statement |
| B4 | `now` as substitution parameter with `minted_at: time_anchor_iri` (FOL §2.1) | Property on ledger statements; new IRI scheme for time anchors |
| B5 | `populate_negative_closure` capacity (FOL §2.1; renamed from `populate_exception_closure`) | L3 capacity, family TBD — likely `capacity:derivation:fol_negative_closure` |
| B6 | Three-step L4 task-to-pipeline flow: `task-patterns` → `promoted-pipelines` → adapt-or-generate (FOL §2.1) | L4 orchestrator (not shipped). Already documented in MindsOS L4 design notes (`docs/dev/l4_intelligence_design_notes.md`, Task-to-pipeline flow section added 2026-04-23 per FOL §4) |
| B7 | Pluggable prover backends behind `Prover` Protocol returning `ProofBound`+`unknown_within_bound` (FOL §2.1) | L3 capacity protocol declaration + N concrete prover capacities (Vampire, E, Z3, etc.) |
| B8 | Authoritative/evaluative role names replacing canonical/operational (FOL §2.1) | L2 ledger schema vocabulary (open decision §3 not yet committed) |
| B9 | Classical FOL proof calculus + non-monotonic ledger dynamics framing (FOL §2.1) | L3 + L4 design narrative; not a code surface per se |
| B10 | New L2 role-graphs implied: `sense-correlations`, `learned-parameters` (FOL §4 — already documented in MindsOS L4 design notes) | New ROLE_* constants in `mindsos_knowledge/identifiers.py` + new schemas in `mindsos_knowledge/schemas/` — **not shipped (carry-forward from R0-PB-9)** |
| B11 | L4 task-to-pipeline three-step default flow (FOL §4 — already documented in L4 design notes) | L4 orchestrator (not shipped) |
| B12 | (FOL pushback #1) Reinstate live+dreaming training, not dreaming-only | L4 design pushback (downstream of L4 design saturation per R0-PB-1) |
| B13 | (FOL pushback #2) Coherence Loop = plural strategies (gradient descent / ES / GA / BO / REINFORCE), each its own L3 capacity | L3 capacity family expansion; new IRI scheme `capacity:coherence_loop:<strategy>` |
| B14 | (FOL pushback #3) WSD decomposed into multiple L3 capacities (tokenization, lemma+POS, sense-inventory lookup, candidate-generator strategies, scorer strategies, confidence calibrator) | **WSD analysis intersects here — see `projects/wsd/`** |
| B15 | (FOL pushback #4) Split `learned-parameters` into 3 role-graphs: `learned-scalars`, `learned-policies`, `learned-models` | L2 role-graph addition; supersedes single `learned-parameters` if accepted |
| B16 | (FOL pushback #5) Add `training-runs` role-graph with checkpointed durability | New L2 role-graph |
| B17 | (FOL pushback #6) Multi-sense top-k with k=1 default; k>1 only when ambiguous + downstream disambiguator | WSD-coupled; design decision |
| B18 | (FOL pushback #7) Reduce source enum to binary `definitional | empirical` | Simplification of B8 |
| B19 | (FOL pushback #8) External blob store + IRI manifest pattern (S3/MinIO + content-addressed hashes) for model artefacts | New L0 infrastructure surface; no MindsOS analog |
| B20 | (FOL pushback #9) Typed `CapacityContext` schema with named accessors per capacity family | L3 capacity-context redesign |
| B21 | (FOL pushback #10) Add capacity-level performance characterisation (latency profile, applicability conditions, failure modes) | Additive L3 metadata |
| B22 | (FOL pushback #11) Allow parallel foundational ontologies (BFO, UFO, YAMATO) in L2 ontology metagraph | DOLCE not "locked"; needs ontology role-graph multi-import support |
| B23 | (FOL pushback #12) Specify concurrency model (single-process / multi-process / distributed) | **L0 architectural decision; high-severity per FOL §3 table** |
| B24 | (FOL pushback #13) Coherence Loop scope drift: formal hand-off to L4 design chat | Process item; not code |

### Bin C — Not implemented + would conflict (design decision required in future chat)

| # | Proposition | Conflict surface | Picks for future chat |
|---|---|---|---|
| C1 | "L5 holds Coherence Loop populations" (FOL §2.2 contested) | L5 design says working memory is per-task scoped; long training runs (hours-to-days) don't fit either L4 process memory or L5 per-task framing. Direct conflict with `docs/dev/l5_mental_model_design_notes.md` §1.1 ("working memory, not a memoir") | Per FOL pushback #5 (add `training-runs` role-graph instead — B16) |
| C2 | Coherence Loop populations / WSD-related "Multi-sense always carried forward when ambiguous" (FOL §2.2) | Exponential ledger blowup if MindsOS L2 schema enforces single-edge-per-relation; depends on FOL pushback #6 resolution | Per pushback #6 |
| C3 | "Single `learned-parameters` role-graph for everything trainable" (FOL §2.2) | Mixes incompatible storage profiles (12-byte scalar vs 100MB neural checkpoint); fails when reaching production. The L4 design notes already shipped this proposition. If MindsOS L2 implements it as a single role-graph (memory-only schema), B19 + B15 supersede | Per pushback #4 + pushback #8 |
| C4 | FOL §3 pushback #11 (DOLCE locked) | MindsOS Phase 15a pins **only** DolceImporter for `ontology` role-graph. Architecturally `ontology` is one role-graph; multi-foundational-ontology support would require either (a) parallel role-graphs (`ontology-bfo`, `ontology-ufo`) or (b) multi-graph membership in `ontology` | Per pushback #11 |
| C5 | FOL §3 pushback #12 (concurrency model unspecified) | High-severity. MindsOS Phase 18-25 ships per-session single-thread (per `[[project-mindsos-l4-design]]`); FOL needs explicit concurrency call. Conflict if FOL assumes multi-process and MindsOS is single-thread-per-session | Per pushback #12; choice constrains prover backend in-process vs subprocess, learned-parameters write semantics, L4 process-memory placement |

### Bin D — Shipped in MindsOS but inconsistent or incomplete

| # | Issue | Evidence | Reconciliation owner |
|---|---|---|---|
| D1 | **`sense-correlations` + `learned-parameters` named in L4 design notes but never shipped as L2 ROLE_* constants or schemas.** | `mindsos_knowledge/identifiers.py:52-71` has 8 ROLE_* constants; neither `sense-correlations` nor `learned-parameters` are among them. No schema files for them in `mindsos_knowledge/schemas/`. Inherited from R0-PB-9 in `confirmation_docs/L4_L5_PLAN_NEXT_CHAT_PROMPT.md` | L4/L5 plan or WSD/FOL skill-acquisition chat; defer disposition decision |
| D2 | **L4 design notes added "Task-to-pipeline three-step flow" (2026-04-23) without L4 architecture being shipped.** | `docs/dev/l4_intelligence_design_notes.md` documents the flow; no L4 code | L4/L5 plan inherits this; FOL B11 row depends on it |
| D3 | **L4 design itself is mid-flight with 7 critique pushes pending.** | `docs/dev/handoffs/l4_session_handoff_2026-04-25.md` §3-§4 + R0-PB-1 in `L4_L5_PLAN_NEXT_CHAT_PROMPT.md` | L4/L5 plan resolves first; FOL skill-acquisition chat is downstream |

---

## 3. Cross-reference with WSD project

FOL and WSD overlap on at least 5 propositions:

| Topic | FOL position | WSD position | Resolution path |
|---|---|---|---|
| `sense-correlations` role-graph | Proposed (FOL B10) | Proposed (per WSD coordinated_change_L2) | Same; ship once |
| `learned-parameters` role-graph | Proposed (FOL B10); split per pushback #4 (FOL B15) | Proposed (per WSD coordinated_change_L2) | If pushback #4 accepted, both projects use the split |
| WSD decomposition | FOL pushback #3 = ACCEPT (decompose) | WSD coordinated_change_L3 = ACCEPT (decompose into SCMS / MSUR / ALS) | Aligned; WSD chat owns it |
| Coherence Loop fate | FOL §2.2 contested | WSD §6.1 contested (blocks WSD spec) | Same blocker; resolve once for both |
| 7 L4 critique pushes | FOL pushback #1, #2, #5 ACCEPT-recommendations | WSD §3.x explicit ACCEPT/PARTIAL-ACCEPT picks on all 7 | WSD has stated picks; FOL accepts/co-occurs |

These projects should be coordinated in one or sequential chats — see `FUTURE_CHAT_PROMPT.md` §6.

---

## 4. Cross-reference with Phase 38 19-item carry-forward + R0 slate

| Phase 38 / R0 item | FOL intersection |
|---|---|
| R0-PB-1 (Plan vs design-resolution; 7 critique pushes pending) | FOL §3 has its own 13 pushbacks plus dependencies on L4 design state. Resolution gating |
| R0-PB-4 (FOL placement) | FOL is now confirmed in-scope per user's framing (was "default = clean defer" at Phase 38). FUTURE_CHAT_PROMPT.md inherits the in-scope answer |
| R0-PB-9 (`sense-correlations` + `learned-parameters` disposition) | FOL B10 + D1 above; both FOL and WSD require these |

---

## 5. Documented design pushbacks (deferred to future chat)

Inherited from this chat's analysis (all are FOL-internal already; analysis-side corrections to my own reading):

- **Analysis-PB-A1** — The HANDOFF_latest §3 13 pushbacks are user-instructed deferred to the future chat. Not re-litigated here.
- **Analysis-PB-A2** — FOL §0 says "no shippable artefact exists yet. The whole project is in design." This means there is no Bin A claim about FOL-specific shipped artifacts; all 5 Bin A rows are about MindsOS architectural primitives FOL depends on, not FOL itself.
- **Analysis-PB-A3** — FOL is multi-layer (L1 through L4 at least). Skill acquisition for FOL must handle artifacts at every shipped layer. The 24 B-rows + 5 C-rows above are the per-layer artifact inventory.
- **Analysis-PB-A4** — FOL §6 lists 6 "things that should have been raised but weren't" — confidence threshold for L4-appended rules, definition of "match" between task and task-pattern, fallback policy on pipeline-finding failure, FOL ledger memory back-pressure, audit log for L2 writes, test data for Coherence Loop fitness. These are scope-level open questions that the FOL future chat inherits.

---

*End of analysis. See `FUTURE_CHAT_PROMPT.md` for the design-resolution chat seed.*
