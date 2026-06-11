# Phase 42 — Design Log (Rail B slot 3: L3 X3)

**Phase:** 42 — L3 X3: bipartite topology (ADR-0156) + capacity registration contract v2 (ADR-0159) + Phase 27 dont-know audit + Model C remediation.
**Rail:** B (slot 3). **Depends on:** 41 (confirmed). Branches off `main`-tip.
**Spec:** `confirmation_docs/PHASE_42_NEXT_CHAT_PROMPT.md`. **Design ground truth:** `L1_L3_REFRAME_DECISIONS.md` §D38 + §Registration + §Phase-27–33-migration-plan; ADR-0156 + ADR-0159 (Accepted on disk).
**Status:** R0 — saturation agenda + grounding complete; pre-impl pushbacks open. Not yet branched.

---

## §0 — Process discipline (inherited)

- **Ground-first consumer discipline** (Phase 44 §5–§12; Phase 41 §5). Grep every consumer across `mindsos_*` / `tests/` / `docs/` before deleting/rewriting. Defer absent-consumer surfaces unless they are the phase's explicit contract deliverable.
- **ADR transcription parity** (Phase 43 NPB11-META) = R1 step 0. Correct the *draft/PHASE_MAP*, not the ADR. Drifts already found at R0 — see §2.
- **Test-fixture + docs sweep** (Phase 40 §10/§11 S2 lesson): a retirement sweep must include test-fixture AND docs consumers, not just production. Phase 40's gate-1 38-failure cascade came entirely from fixture hubs missed at R0. Directly applies to the TYPE_COMPAT/`discover_*` retirement + Model C doc sweep at scale.
- **Manifest high-water-mark** (Phase 40 PB-2 / §11): slot 42 ≤ high-water 44 → **no version bump**; `confirm-phase --phase 42` accepted by `_phase_exceeds_manifest`. Do not touch the 9 version surfaces.
- **Pair-execution** (Cowork prepares content; user runs git on Mac; Linux gates via docker) + **docker rebuild before each gate** + **6-step confirm-phase** on post-squash `main`.
- **Scoped grep-zero sentinel** (Phase 41 PB-2): repo-wide grep-zero is unsatisfiable; scope retirement sentinel to the shipped package.

---

## §1 — Prereq check (2026-06-05)

| Check | Result |
|---|---|
| `phase-41-confirmed` tag exists at `ba7c469` | ✅ PASS |
| `main` top-3 | ⚠️ `626ee5d` (Phase 41 closure docs) → `ba7c469` (confirm artifacts) → `9330550` (squash). Spec expected tip = `ba7c469`; the closure-docs commit `626ee5d` landed after the prompt was authored. **Benign** — branch `phase-42` off `626ee5d` (`main`-tip). |
| Tree clean except known untracked | ✅ Untracked = `ROBOT_DEMO_*`, `demo_ui/`, `prototype_zero/`, `PHASE_41_NEXT_CHAT_PROMPT.md`. Leave alone; never `git add -A`. |
| Manifest high-water-mark in force | ✅ slot 42 ≤ 44 → no version bump. |

**Ruling:** prereqs satisfied. Branch `phase-42` off `626ee5d`.

---

## §2 — ADR transcription parity register (R1 step 0, run early)

Both ADRs `status: Accepted` on disk — no status flip. Parity drifts found between PHASE_MAP / §Registration prose and the ADR code blocks:

- **P-1 (field count) — "5 new fields" is wrong; it is 6.** ADR-0159 line 33 says "**5 new fields**" then lists **six** in the code block: `concurrent`, `inline`, `max_latency_ms`, `precondition_iri`, `effect_iri`, `reads_mm`. PHASE_MAP §Phase 42 + §Registration §Settlement repeat "5 new fields" then also list six. The literal dataclass field count is **6**. `_CapacityBase` goes 11 → 17 fields. The "5" is a conceptual grouping (inline-flag + its latency declaration counted as one). **Ruling:** implement 6 fields; the test `test_typed_capacity_context.py` asserts 6; annotate the ADR/PHASE_MAP "5" as a conceptual-grouping note (correct the draft, not the contract). Carry to R1.
- **P-2 (CapacityContext field count) — PHASE_MAP says "9 fields"; ADR shows 10.** ADR-0159 code block lists: `session_id`, `user_id`, `learned_parameters_snapshot`, `mm_handle`, `cancel_token`, `current_task_iri`, `current_pattern_iri`, `version_snapshot`, `kl`, `cl` = **10**. PHASE_MAP/§Registration say "9 fields". **Ruling:** 10 fields per ADR; correct the PHASE_MAP "9".
- **P-3 (verdict-type home) — `verdicts.py` is a PHASE_MAP invention.** §migration-plan line 294 says verdict types ship "in context.py **or** verdicts.py"; ADR-0159 places all 5 verdict dataclasses inline in the `context.py` decision section. PHASE_MAP "Modules touched" hard-asserts a NEW `mindsos_capacity/verdicts.py`. **Decide at R1** (PB-5 below) — not a parity error in the ADR, a PHASE_MAP over-specification.
- **P-4 (`reads_mm`)** correctly two-valued `bool` in all three sources (R2 reversal honored). No drift.

---

## §3 — Grounding (consumer discipline; evidence-backed)

### Blast radius — TYPE_COMPAT / `discover_*` (grep, full repo)
- **Live source (`mindsos_capacity/`):** `capacity_layer.py` (register_capacity calls `discover_for_capacity`; raises `DiscoveryFailedError`), `discovery.py` (324 LOC, module), `views.py` (`successors_of` walks `EDGE_TYPE_COMPAT`), `pipeline.py` (`find_pipeline` via `consumers_of` + `outputs` property reads), `identifiers.py` (`EDGE_TYPE_COMPAT`), `schemas.py` (EDGE_TYPE_COMPAT EdgeType reg), `exceptions.py` (`DiscoveryFailedError`), `__init__.py` (exports).
- **`discovery.py` occupancy:** clean delete. Only 2 importers — `__init__.py` (exports) + `capacity_layer.py` (one call site). `SuccessorHop` lives in `views.py`, `DiscoveryFailedError` in `exceptions.py` — not orphaned by the module delete; retire them separately.
- **Tests:** ~38 TYPE_COMPAT hits across `tests/phase_29` (retires whole) + `tests/phase_30` (find_pipeline edits) + `tests/phase_33/test_outputs_terminator_discovery.py` (retire/rewrite) + `tests/_shared/sentinel_paths.py` (one ref).
- **Docs (corrects the R0 sub-probe's "0 hits"):** **47 `TYPE_COMPAT` hits across ~17 files.** LIVE/scrub: `docs/usage/capacity/{overview,categories,building,retrieval}.md`, `docs/decisions/summary/capacity.md`, `docs/getting-started/whats-new-v4.md`, `docs/future_work/L3_FUTURE_WORK.md`. HISTORICAL/keep: ADR-0069, ADR-0086 (superseded — must retain the term they document), ADR-0156 (self-documents the retirement), `docs/changelog/CHANGELOG.md`, ADRs 0063/0064/0065/0071/0085/0145 (contextual). **Consequence:** the PHASE_MAP pass-criterion `grep -rn "TYPE_COMPAT\|discover_for_capacity\|discover_for_datastate\|rediscover_all"` **returns zero** is **repo-wide-unsatisfiable** (same class as Phase 41). Scope the sentinel to `mindsos_capacity/**/*.py` (importability + package grep); scrub the LIVE docs; keep HISTORICAL ADRs/changelog. See PB-3.

### Phantom / existence check (PHASE_MAP "Modules touched")
- **EXIST (edit targets, real):** `capacity.py`, `capacity_layer.py`, `pipeline.py`, `views.py`, `discovery.py`, `identifiers.py`, `exceptions.py`, `builtins/consolidate.py`, `mindsos_instances/` (registry + models), `tests/phase_29/`, `tests/phase_30/`, `tests/phase_33/test_outputs_terminator_discovery.py`, `tests/_shared/sentinel_paths.py`.
- **ABSENT (net-new, correctly so — NOT phantoms):** `context.py`, `verdicts.py` (see P-3), `tools/migrate_phase_42_bipartite.py`, `confirmation_docs/PHASE_27_DONT_KNOW_AUDIT.md`, `IntergraphEdgeInstance` / `IntergraphHyperEdgeInstance` (absent repo-wide — to add).
- **No Phase-41-style phantom edit-target found.** Every claimed *edit* target exists; every *create* target is correctly absent. The Model C "~50 filename normalizations across `docs/decisions/summary/{...}.md`" claim still needs sizing at R1 (the summary tree exists; the "~50" count is a Phase-38-carry-forward estimate, not yet ground-verified).

### `_CapacityBase` today (capacity.py)
11 fields: `name, category, inputs, outputs, implementation, description, cost_prior, latency_ms_prior, node_type, node_kind, is_adapter`. `to_properties()` serializes `inputs`/`outputs` as node-property lists (these stop serializing; move to edges). → 11 + 6 = 17 fields.

### CapacityContext / `context["kl"]`
Only **one** live body destructures context as a dict: `mindsos_capacity/builtins/consolidate.py` (`context.get("kl")`). `trace:problem` body to re-check at impl. So "~2-3 bodies" is at most 2. `read_at_version` is **NOT implemented** on KnowledgeLayer (deferred → Phase 48 per CLAUDE.md / Phase 44 S6). The `KLHandle` Protocol *declares* `read_at_version` — see PB-4.

### Export slate
`mindsos_capacity.__all__` = **112** (Phase 41). Sentinels at `tests/phase_29/30/31/33/34` assert 112. Phase 42 net delta (PB-6): retire `SuccessorHop`, `EDGE_TYPE_COMPAT`, `discover_for_capacity`, `discover_for_datastate`, `rediscover_all`, `DiscoveryFailedError`, `CapacityLayer.rediscover` (method, not export) + add `EDGE_PRODUCES`, `EDGE_CONSUMES`, `CapacityContext`, 4 Protocols, 5 verdict types (+ optional `inputs_of`/`outputs_of`). Net non-zero → re-flip the 112 literal in all sentinel files; resolve exact count at impl per Phase 40 PB-9 precedent.

### Migrator idiom
Established detector/migrator pattern: `tools/check_phase_43_confidence_state.py` + `tools/check_rename_state.py` — lazy `falkordb` import, `_connect()`, `_all_graphs(db)`, node scan by type, report. Global-only scope (Locals in-memory pending Phase 44 persisters). Idempotence via `register_capacity(if_exists="upsert")` edge-existence check (ADR-0156 line 43). See PB-7 (detector-vs-migrator form under Phase 39/43 precedent).

---

## §4 — R0 S-surface agenda (locked targets for R1)

- **S1 — `_CapacityBase` +6 fields** (P-1). Defaults preserve Phase 27–33. `to_properties()` drops `inputs`/`outputs`.
- **S2 — `register_capacity` rewrite.** Replace `discover_for_capacity` call with produces/consumes IntergraphEdge emission walking `declaration.inputs`/`outputs`; add `if_exists: Literal["raise","upsert"]="raise"`; +~20 LOC validation (inline⇒max_latency_ms; precondition/effect resolve to `predicate.*`).
- **S3 — `discovery.py` delete whole** (324 LOC; clean). Retire `EDGE_TYPE_COMPAT` (identifiers + schemas), `DiscoveryFailedError` (exceptions), `SuccessorHop` + `rediscover` (views/layer), exports.
- **S4 — `views.successors_of` → two-hop bipartite walk** + `inputs_of`/`outputs_of` helpers (declaration-registry primary, graph-walk fallback).
- **S5 — `pipeline.find_pipeline` bipartite BFS** (semantic-preserving vs Phase 30 cases).
- **S6 — `context.py` NEW**: `CapacityContext` (10 fields, frozen, `MappingProxyType` version_snapshot) + 4 Protocols + `CancelTokenView` + 5 verdict types (home decided PB-5).
- **S7 — `mindsos_instances` Phase 06 amendment**: `IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance` (8 → 10 catalog).
- **S8 — consolidate.py (+ trace?) body migrate** `context["kl"]` → `context.kl`.
- **S9 — one-pass Global migrator** `tools/migrate_phase_42_bipartite.py` (PB-7 form).
- **S10 — Phase 27 dont-know audit deliverable** + the L3-57 FAMILY_RULES decision (PB-8).
- **S11 — Model C remediation**: scrub LIVE docs (PB-3), `mkdocs build --strict` lift, filename normalization (size at R1).
- **S12 — sentinel chain** `tests/phase_42/test_adr_amendment_sentinels.py` (ADR-0156 + 0159 + 8 amendments) + export-slate re-flip (PB-6).

---

## §5 — Pre-impl pushbacks — options + chosen pick

### Round 1 (2026-06-05) — picks ruled
- **PB-3 — grep-zero sentinel scope.** A (pick, user-ruled): scope sentinel to `mindsos_capacity/**/*.py`; scrub LIVE docs; keep HISTORICAL ADRs/changelog. Phase 41 PB-2 precedent. Repo-wide is unsatisfiable (47 docs hits across ~17 files; ADRs 0069/0086/0156 + changelog must retain term).
- **PB-4 — `KLHandle.read_at_version` declares a method KL doesn't implement (deferred Phase 48).** A (pick): ship the Protocol method as declared (structural type; no v1 caller — only `consolidate` uses write methods); document "Phase 48 wires KL impl." Contract-ahead-of-consumer pattern.
- **PB-5 — verdict-types home.** A (pick): all 5 verdict dataclasses inline in `context.py`; **drop `verdicts.py`** (PHASE_MAP over-specification P-3). Correct PHASE_MAP "Modules touched".
- **PB-6 — export-slate delta.** Track only. Net non-zero: retire `SuccessorHop, EDGE_TYPE_COMPAT, discover_for_capacity, discover_for_datastate, rediscover_all, DiscoveryFailedError`; add `EDGE_PRODUCES, EDGE_CONSUMES, CapacityContext`, 4 Protocols, 5 verdicts (± `inputs_of`/`outputs_of`). Re-flip `==112` literal across phase_29/30/31/33/34; exact count at impl (Phase 40 PB-9 pattern).
- **PB-7 — migrator vs detector.** **Ground-first (pick, user-ruled):** at impl R1 verify whether bootstrap re-`register_capacity`s Global capacities. If yes → ship a *detector* (`check_phase_42_bipartite_state.py`: no node carries `inputs`/`outputs` props + every capacity has produces/consumes edges). If Global persists un-re-registered capacity nodes → ship the full migrator. Follows Phase 39/43 migrator→detector precedent. Note: under the detector outcome, `if_exists="upsert"` is the only edge-emission path at next boot → upsert correctness load-bearing regardless (see PB-10/Round 2).
- **PB-8 / L3-57 — FAMILY_RULES reconciliation (the genuine decision).** **Option 3 (pick, user not yet ruled — recommended):** rename `derive`→`derivation` + `signal`→`signalling` (typo-class vs shipped vocabulary); add `consolidate`→DATASTATE_MARKER + `trace`→DATASTATE_MARKER (groundable from shipped `consolidate:mm`/`trace:problem`); leave comprehension/decomposition/path-finding/interaction/learning-methods explicitly listed in the audit as "default by design, shape ratified at owning install chat" + a sentinel pinning that deferred list. Fixes 4 of 9 fall-throughs now; converts the other 5 from silent fall-through to test-pinned documented deferral. ADR-0157 §amendment (partial). Ground truth: 13 shipped `FUNCTIONAL_CATEGORIES` = perception, comprehension, derivation, decomposition, combination, path-finding, retrieval, scoring, trace, signalling, interaction, learning-methods, consolidate.

### Round 2 (2026-06-05) — deeper / gate-facing
- **PB-9 — single query-time source of truth.** Pick: **edges** are the single query-time source for `find_pipeline`/`successors_of`; declaration registry is authoring/fallback only. The `to_properties()` strip breaks the current `cap.properties["outputs"]` frontier read — rewrite is load-bearing, not polish. Prevents Global (props stripped) vs Local divergence.
- **PB-10 — `if_exists="upsert"` idempotency / Falkor multi-statement non-atomicity.** Pick: ground `_has_edge` helper existence (ADR-0156 R0 probe #7) at R1; if absent, build the edge-existence check. Load-bearing under the PB-7 detector outcome (upsert is the boot-time emission path).
- **PB-11 — IntergraphEdge persistence pattern (HIGHEST uncertainty).** Pick: read the Phase 05b IntergraphEdge persistence lock (Pattern A direct vs Pattern B anchor; ADR-0156 R0 probe #5) **before** sizing/writing S4 (`successors_of`) + S5 (`find_pipeline`). Anchor-based persistence changes the two-hop walk shape and invalidates the ~50/~20 LOC estimates.
- **PB-12 — `precondition_iri`/`effect_iri` validation has no v1 satisfier** (no `predicate.*` capacity ships pre-WSD/FOL). Pick: ship structural check (present ⇒ well-formed IRI) unconditionally; make "resolves to predicate family" a soft/skip-if-family-absent check — testable on negative path, no fabricated predicate fixture.
- **PB-13/14 — gate-cascade budget.** Bipartite emits 2 edges/I-O vs TYPE_COMPAT's 1 transitive. Pick: pre-audit `tests/phase_30` + `tests/phase_32` (Integration B) fixtures for edge-count/TYPE_COMPAT-presence assertions at R1 before locking (Phase 40 §11 fixture-hub lesson). Treat **Integration B green** as the real semantic-preservation criterion, not the unit tests.
- **PB-15 — 2 instance subclasses ship ahead of consumer** (capacity-MM instantiation Phase 46+). No deferral (ADR-0156 locks; reframe pattern). `test_intergraph_instances.py` = isolated instantiation/persistence only. Track.
- **PB-16 — `mkdocs build --strict` clean criterion has unbounded surface.** Pick: run `mkdocs build --strict` at R1 to enumerate the actual warning set first; if TYPE_COMPAT/capacity-local → keep criterion; if broad unrelated debt → flag + scope the lift to capacity docs, don't absorb unrelated doc debt into Phase 42.

### Round 3 (2026-06-05)
- **PB-17 — `SuccessorHop` retirement de-risked (ground-first).** ADR-0156 probe #8 ("SuccessorHop in problem-trace serialization") resolves to **zero production consumers**: `SuccessorHop` lives only in `views.py`; `successors_of` has no production caller (`pipeline.py:20` states the BFS does not call it); no problem-trace coupling. Rewritten `successors_of` return type is a free choice; retirement is safe.
- **PB-18 — produces/consumes schema-registration shape (track).** `EDGE_TYPE_COMPAT` was a regular `EdgeType`; produces/consumes are cross-graph → `IntergraphEdgeType`. Confirm at R1 that `schemas.py` registers them as `IntergraphEdgeType` + L3 `MetagraphSchema` supports it (inverse of Phase 43's `memory_contains_episode` same-role-graph case). Mechanical once confirmed.

### Round 4 (2026-06-05) — whole-plan reanalysis (user re-request)
- **PB-21 — PB-8 Option 3 is gate-safe; one Phase 40 test repoint.** `tests/phase_40/test_family_rules_lookup.py::test_permissive_default_for_unkeyed_category` asserts `consolidate:mm`/`trace:problem` → DATASTATE_MARKER *via permissive default*. Option 3 adds `consolidate`/`trace` as explicit keys → asserted value unchanged (no gate break) but the test's intent (default path) is invalidated. **Resolution:** repoint the test to a still-deferred category (comprehension/decomposition) + add positive assertions for the renamed `derivation`/`signalling` keys (currently untested — rename ships unverified otherwise). Phase 40 ADR-sentinel (`"FAMILY_RULES" in text`) unaffected.
- **PB-19 — commit-staging (process).** Pick: stage `phase-42` commits by concern (source → tests → migrator/detector → docs/Model C → ADRs) then squash. Localizes gate-1 root cause (Phase 43 PR1/PR2 precedent for comparable scope).
- **PB-20 — R1 ordering (process).** Pick: 05b IntergraphEdge pattern probe (PB-11) → S1/S2/S3 → S4/S5 walks → boot-grounding → migrator/detector (PB-7) → fixture pre-audit (PB-13/14) → Model C/strict enumeration (PB-16). Do not write a walk before 05b is grounded.

### Saturation status — SATURATED (4 rounds, 2026-06-05)
All design forks closed. PB-8 = Option 3 (user-ruled). Remaining items are R1-grounding gates resolved against evidence at impl: PB-7 detector/migrator, PB-10 `_has_edge`, PB-11 05b pattern, PB-13/14 fixture pre-audit, PB-16 strict-warning enumeration, PB-18 IntergraphEdgeType registration. Process: PB-19 staged commits, PB-20 R1 order. Ready to lock R1 + branch `phase-42` off `626ee5d`.

---

## §6 — Locked R1 scope + sequence (2026-06-05, user-ruled "lock R1 + prep branch")

**Branch:** `phase-42` off `main`-tip `626ee5d`. No version bump (slot 42 ≤ high-water 44). Commit staging by concern (PB-19): `source → tests → migrator/detector → docs+ModelC → ADRs`, then squash; tag `phase-42-confirmed` at the post-squash confirm-artifacts commit.

**R1 execution order (PB-20 — strict; each grounding gate resolved before the work it blocks):**

1. **G0 — Phase 05b IntergraphEdge persistence-pattern probe (PB-11).** Read the 05b lock (Pattern A direct vs B anchor). Output: the Cypher/walk shape for produces/consumes. *Blocks S4/S5.* Also confirm `_has_edge` helper existence (PB-10); build if absent.
2. **G1 — fixture pre-audit (PB-13/14).** Grep `tests/phase_30` + `tests/phase_32` for edge-count / TYPE_COMPAT-presence assertions; enumerate the expected gate-1 churn before touching source.
3. **G2 — `mkdocs build --strict` warning enumeration (PB-16).** Capture the actual warning set; decide criterion scope (full vs capacity-local) per the count.
4. **S1 — `_CapacityBase` +6 fields** (P-1; defaults preserve 27–33; `to_properties()` drops `inputs`/`outputs`).
5. **S2 — `register_capacity` rewrite** (produces/consumes emission; `if_exists` kwarg; +~20 LOC validation; PB-12 soft predicate check).
6. **S3 — delete `discovery.py`; retire `EDGE_TYPE_COMPAT`/`DiscoveryFailedError`/`SuccessorHop`/`rediscover`.**
7. **S4/S5 — `successors_of` + `find_pipeline` bipartite rewrite** (PB-9 edges single query-time source; uses G0 shape).
8. **S6 — `context.py`** (CapacityContext 10 fields + 4 Protocols + CancelTokenView + 5 verdicts inline; PB-4/PB-5).
9. **S7 — `mindsos_instances` Phase 06 amendment** (IntergraphEdgeInstance + IntergraphHyperEdgeInstance; 8→10).
10. **S8 — body migration** `context["kl"]`→`context.kl` (consolidate; re-check trace).
11. **PB-7 boot-grounding → S9 migrator-or-detector.** Verify Global boot re-registration; ship detector if re-registered, full migrator if not.
12. **S10 — Phase 27 audit deliverable** + PB-8 Option 3 (rename `derive`→`derivation`/`signal`→`signalling`; add `consolidate`/`trace`; test-pin deferred 5) + ADR-0157 §amendment-1 + PB-21 Phase 40 test repoint.
13. **S11 — Model C** (scrub LIVE docs; strict-lift per G2; filename normalization) + S12 sentinel chain + export-slate re-flip (PB-6).

**Export-slate (PB-6):** re-flip `==112` across phase_29/30/31/33/34 export-slate sentinels; exact count resolved at S1/S6 (Phase 40 PB-9 pattern).

---

## §7 — G0 grounding results (2026-06-05, in-session; branch `phase-42` cut off `626ee5d`)

- **PB-11 resolved (de-risked).** IntergraphEdge persistence = **Pattern B (anchor-node)** per `INTERGRAPH_EDGES_DESIGN.md §3.1`, but confined to Falkor Cypher (Phase 07/08 loaders abstract it). At model level IntergraphEdges are a flat dict `mg.intergraph_edges`, walked via `Metagraph.iter_intergraph_edges()`. The bipartite walk is a two-hop in-memory filter over that dict — Pattern B never enters the walk. S4/S5 ~50/~20 LOC estimates HOLD.
- **PB-10 resolved.** No reusable `_has_edge` (only `discovery._edge_already_exists`, dies with the delete). `if_exists="upsert"` idempotency = ~10-LOC tuple-match helper over `iter_intergraph_edges()` (source/target/type_name) before `mg.add_intergraph_edge`.
- **PB-18 resolved (no IntergraphEdgeType work).** The L3 metagraph is built `Metagraph(NAME)` with **`schema=None`** (schemas attach to graphs, not the metagraph; `bootstrap.create_global`). `add_intergraph_edge` step-8 `require_intergraph_edge_type` is guarded by `if self.schema:` → skipped. So PRODUCES/CONSUMES IntergraphEdges create without any IntergraphEdgeType registration. The pre-existing `EDGE_PRODUCES`/`EDGE_CONSUMES` graph-level EdgeTypes in `build_category_schema` are vestigial (kept, descriptions refreshed to the bipartite reality). Only the `EDGE_TYPE_COMPAT` EdgeType registration dropped (ADR-0156).

- **PB-22 (NEW conflict — ADR-0156 vs ADR-0021 regex).** ADR-0156 specifies `EDGE_PRODUCES="produces"`/`EDGE_CONSUMES="consumes"` (lowercase), but `IntergraphEdge.__post_init__` enforces `EDGE_TYPE_IDENTIFIER_RE = ^[A-Z][A-Z0-9_]{0,63}$` (uppercase-only); lowercase raises at construction. Precedent: `EDGE_TYPE_COMPAT="TYPE_COMPAT"` (retiring) + `EDGE_MEMORY_CONTAINS_EPISODE="MEMORY_CONTAINS_EPISODE"` (Phase 43) both uppercase. **Pick: Option A** — values `"PRODUCES"`/`"CONSUMES"` (uppercase rel-type); constant names unchanged; ADR-0156 body lowercase = instance-layer (D-B46) label form, noted in ADR-0156 §amendment. **RULED A (user, 2026-06-05): analyze + choose → Option A is the only regex-compliant form.** **IMPL FINDING:** `EDGE_PRODUCES="PRODUCES"` + `EDGE_CONSUMES="CONSUMES"` *already ship* in `identifiers.py` (lines 158-159), already uppercase — Option A is zero-code-change beyond retiring `EDGE_TYPE_COMPAT`. ADR-0156 §amendment notes the body lowercase = instance-layer label form.

---

## §8 — Implementation record

### Commit 1 (source: bipartite core, S1–S5) — built 2026-06-05, compiles + sentinel-clean
Files: `capacity.py` (+6 fields; `to_properties` drops inputs/outputs), `identifiers.py` (retire `EDGE_TYPE_COMPAT` + its `__all__` entry; PRODUCES/CONSUMES already uppercase), `capacity_layer.py` (`register_capacity` bipartite emission + `if_exists` + `_validate_contract_fields` + module-level `_has_intergraph_edge` idempotency helper; retire `register_datastate` discovery hook + `rediscover` method + discovery/`DiscoveryFailedError` imports), `views.py` (edge-sourced `producers_of`/`consumers_of` + new `inputs_of`/`outputs_of` + two-hop `successors_of`→`List[str]`; retire `SuccessorHop` + `_hop_from_edge`), `pipeline.py` (`find_pipeline` reads `view.outputs_of`/`inputs_of`), `exceptions.py` (retire `DiscoveryFailedError`), `schemas.py` (retire `EDGE_TYPE_COMPAT` EdgeType; refresh PRODUCES/CONSUMES descriptions), `__init__.py` (retire 6 exports; docstring scrub). **DELETE** `discovery.py` (`git rm`). All live docstrings scrubbed of the 4 sentinel tokens. `__all__` **112→106** (−`DiscoveryFailedError`,−`SuccessorHop`,−`discover_for_capacity`,−`discover_for_datastate`,−`rediscover_all`,−`EDGE_TYPE_COMPAT`). `py_compile` green; package-scoped sentinel grep clean outside `discovery.py`. **Export-slate sentinels (phase_29/30/31/33/34) will need 112→106+S6-additions re-flip in the test commit.**
Remaining source: S6 `context.py` (NEW — **built**, 11 exports, `__all__` 106→117), S7 `mindsos_instances` 2 subclasses, S8 body migration. Then tests, migrator/detector (PB-7), docs/Model C, ADR amendments.

### PB-23 (NEW scope fork — surfaced at S8) — CapacityContext invoke-plumbing + body migration
**Finding:** `invoke` builds a **dict** context carrying `kl`, `session_id`, `session_user_id`, and the full `session` object (write bodies call `session.has(cap)` per ADR-0146 §am-1). 3 bodies read dict-style (consolidate/trace/text); 4 test files assert it (phase_30/33/34/36). ADR-0159's 10-field `CapacityContext` has **no session-object field** → can't carry write-body capability-gating needs. Migrating bodies to `context.kl` requires `invoke` to build a `CapacityContext`, which ripples into ADR-0072 envelope + forces resolving an **ADR-0146-vs-ADR-0159 conflict** (does the L3 body get the session?) that is L4-boundary territory.
- **Opt 1 — full conversion now:** invoke→CapacityContext + 3 bodies + 4 tests + resolve session gap. Largest; cascade risk; resolves an L4-owned conflict prematurely; exceeds PHASE_MAP "mechanical ~2-3 bodies".
- **Opt 2 (pick) — ship CapacityContext as forward contract; defer invoke-plumbing + body migration to Phase 46.** Typed module ships fully + isolated-tested; invoke keeps dict; bodies unchanged. Real consumer = L4 substrate (Phase 46). Re-scope PHASE_MAP body-migration row → Phase 46 (tracked). Consumer-discipline-correct (Phase 44 §5–12); no cascade.
- **Opt 3 — dual-access shim:** half-measure; ships untested-against-real-context plumbing.
- **Pick: Opt 2. RULED Opt 2 (user, 2026-06-05).** S8 (body migration + invoke→CapacityContext) **deferred to Phase 46**; bodies unchanged; CapacityContext ships as forward contract; export-slate = 117. PHASE_MAP Phase 42 "body migration" feature row + "CapacityContext shape" breaking-change row re-scope to Phase 46 (tracked in the PHASE_MAP edit at S11). §6 R1 step 10 (S8) struck.

### PB-24 (decided, not asked — consumer-discipline, consistent w/ PB-15) — instance-subclass materialise deferral
S7 ships `IntergraphEdgeInstance` + `IntergraphHyperEdgeInstance` as first-class for **instantiation + persistence** (catalog `models/__init__` + `mindsos_instances/__init__` + reconstruction `_KIND_TO_CLASS` + repository `_kind_for`; registry KIND dispatch is automatic via `type(inst).KIND`). **`materialise` (clone-into-Core) is DEFERRED to Phase 46** — its only consumer is capacity-MM instantiation (Phase 46); the `materialise()` fallthrough `TypeError` documents it; subclass docstrings note it. Test scope (`test_intergraph_instances.py`) = instantiation + registry + repository/reconstruction round-trip, NOT materialise.

### Commit 2 (source: CapacityContext + instance subclasses, S6+S7) — built 2026-06-05, compiles
Files: `mindsos_capacity/context.py` (NEW — 10-field frozen `CapacityContext` + `MMHandle`/`KLHandle`/`CapacityLayerHandle`/`CancelToken` Protocols (`@runtime_checkable`) + `CancelTokenView` + 5 verdict dataclasses; import-isolated — no mindsos_knowledge/mindsos_instances imports, Any/forward-refs per Phase 28 invariant), `mindsos_capacity/__init__.py` (+11 exports → `__all__` **106→117**), `mindsos_instances/models/element_instance.py` (+2 subclasses), `mindsos_instances/models/__init__.py` + `mindsos_instances/__init__.py` (catalog 8→10), `reconstruction/instance_loader.py` (`_KIND_TO_CLASS` +2), `persistence/instance_repository.py` (`_kind_for` +2). `py_compile` green. No version bump (`mindsos_instances.__version__` stays `0.0.0+phase44`).
**Remaining:** tests (phase_27 dataclass +6 fields, phase_28 register edge-emission + schemas EDGE_TYPE_COMPAT removal, phase_29 retire-whole, phase_30 find_pipeline, phase_33 outputs_terminator retire/rewrite, phase_36 unaffected-check, export-slate flip 112→117 across phase_29/30/31/33/34, NEW tests/phase_42/* 8 files), Phase 27 audit doc + L3-57 (PB-8 Opt 3 + PB-21 phase_40 test repoint), Model C docs + mkdocs strict (PB-3/PB-16), ADR amendments (0156/0159 + 8) + PHASE_MAP re-scope rows (PB-23).

### PB-7 RESOLVED → detector (ground-first, 2026-06-05)
**Grounding:** `CapacityLayer()` is constructed **fresh in-memory** at every CLI/server entry (`mindsos_cli/commands/capacity.py:95,261`) — no `MetagraphLoader.load` / Falkor reconstruct of the Global L3 metagraph; `create_global` builds only graphs; capacities come from idempotent `install_*` calls (now running the bipartite `register_capacity`). `GLOBAL_FALKOR_GRAPH` is a defined name with **no writer** in shipped code. ∴ no persisted Global capacity state → a one-pass migrator is **dead code**. Phase 39/43 migrator→detector reversal repeats.
**Shipped:** `tools/check_phase_42_bipartite_state.py` (detector, mirrors `check_rename_state` / `check_phase_43_confidence_state`): scans Falkor for capacity nodes still carrying `inputs`/`outputs` props; exit 0 clean / exit 1 + wipe-and-rebootstrap remediation; idempotent; `--help` + `py_compile` green. PHASE_MAP "one-pass migrator" + `tools/migrate_phase_42_bipartite.py` row + `test_migrator_idempotent.py` re-scope to this detector form (tracked at S11 PHASE_MAP edit).

### Commit 3 (migrator/detector stage) — built 2026-06-05
File: `tools/check_phase_42_bipartite_state.py` (NEW detector). Companion test ships in the test stage (`tests/phase_42/test_bipartite_detector.py`, replacing the PHASE_MAP `test_migrator_idempotent.py`).

### Commit 4 (test stage, part 1 — retirements + slate/sentinel fixes) — built 2026-06-05, py_compile green
PB-13/14 fixture pre-audit done: `phase_29/_fixtures.py` is **local** (no Phase-41-style trap); the phase_29 slate file **survives** (count carrier). **Deletes (git rm) 13 phase_29 files** (the discovery/successor/rediscover/schema-is-none/adr-sentinel suite + `_fixtures.py`); **keeps** `__init__.py` + `test_phase_29_export_slate.py`. **Export-slate flip 112→117** across phase_29/31/33/34 (function renamed `*_is_117` + ledger updated). **phase_30 slate**: removed the 5 retired names from the durable `phase_29_set`. **phase_28 `test_schemas`**: drop `EDGE_TYPE_COMPAT` import + four→three edge-types assertion. **phase_38 doc sentinel**: anchor #1 updated to the new `__init__` "retired per ADR-0156" text (broken by the commit-1 docstring scrub). **`tests/_shared/sentinel_paths.py`**: `discovery.py` entry (deleted commit 1, broke `test_image_completeness`) replaced with `context.py`. All edits `py_compile` green (full pytest gate is Linux-docker-only — sandbox lacks FalkorDB/tomli).
PB-13/14 confirmed low: phase_30 find_pipeline fixtures register DataStates→capacities then assert pipeline results (edge-based now, same values) — no edits needed. The 3 artifact-coupled tests (`test_phase_27_audit_doc`, `test_mkdocs_strict_clean`, `test_adr_amendment_sentinels`) land WITH their artifacts in commits 6-8.

### Commit 5 (test stage, part 2 — behavior tests) — built 2026-06-05, py_compile green
NEW `tests/phase_42/__init__.py` + 5 behavior tests: `test_bipartite_register.py` (produces/consumes emission + node-props-stripped + if_exists raise/upsert-idempotent + inline⇒max_latency_ms), `test_pipeline_find_bipartite.py` (Phase-30 semantic preservation: linear + shortest-by-count; successors_of two-hop; inputs_of/outputs_of/producers_of/consumers_of), `test_typed_capacity_context.py` (10 fields + frozen + MappingProxyType read-only + 4 runtime_checkable Protocols + CancelTokenView is_set-only + 5 frozen verdicts), `test_intergraph_instances.py` (KIND/structural-keys/export/`_KIND_TO_CLASS`/catalog==10), `test_bipartite_detector.py` (module load + CAPACITY_NODE_TYPES + --help exit 0, no Falkor). Reuses `tests/phase_30/_fixtures`. **REWRITE** `phase_33/test_outputs_terminator_discovery.py` → counts PRODUCES edges (bipartite terminator semantic). `py_compile` green; imports verified in `__all__`.
### Commit 6 (Phase 27 audit + L3-57 / PB-8 Opt 3) — built 2026-06-05, py_compile green
`family_rules.py`: rename `derive`→`derivation` + `signal`→`signalling`; add `consolidate`+`trace` (DATASTATE_MARKER, grounded by shipped write caps); new `DEFERRED_DEFAULT_CATEGORIES` frozenset (comprehension/decomposition/path-finding/interaction/learning-methods) — NOT package-exported (keeps `__all__`=117). NEW `confirmation_docs/PHASE_27_DONT_KNOW_AUDIT.md` (13-category table + Opt-3 decision + deferred list). NEW `tests/phase_42/test_phase_27_audit_doc.py` (doc presence/shape + deferred-list↔frozenset consistency pin + reconciled-keys/old-keys-gone). PB-21: `tests/phase_40/test_family_rules_lookup.py` — repointed `test_permissive_default_for_unkeyed_category` to comprehension/decomposition + added `test_renamed_and_added_category_keys_phase42`. ADR-0157 **§amendment-1** appended. Static verify: derive/signal gone, derivation/signalling/consolidate/trace present, deferred∩keys=∅.
### PB-16 RESOLVED → Option B (scoped strict-lift; self-chosen, 2026-06-05)
**Enumerated:** `mkdocs build --strict` fails with **17 warnings, zero TYPE_COMPAT/Phase-42-related** — all pre-existing server-pivot-era debt (2 missing nav handoffs, ~14 broken cross-links to never-vendored docs: release-model, PIVOT_V1_SCOPE, HANDOFF_SERVER_PIVOT, ADRs 0058/0059/0121, instancing.md, mental-model.md, …, 1 page-not-in-nav 0054). **Phase 42 introduces 0 new strict warnings** (changed docs absent from the list; audit doc lives in confirmation_docs/, outside nav). **Decision (Opt B):** scope the Model C lift to Phase 42's surface — scrub the live capacity TYPE_COMPAT pages; assert **non-strict build succeeds** (exit 0, verified) as a no-regression guard; track the 17 pre-existing warnings as a **docs-maintenance-chat** item (NOT Phase 42). PHASE_MAP "mkdocs --strict clean" pass-criterion re-scoped accordingly (recorded at commit 8 PHASE_MAP edit). Matches the PB-3 / Phase 41 "scope an unsatisfiable criterion to the shipped package" precedent.

### Commit 7 (Model C docs, Opt B) — built 2026-06-05, non-strict build exit 0
Scrubbed live capacity docs to bipartite/PRODUCES-CONSUMES: `usage/capacity/{overview,categories,building,retrieval}.md` (now TYPE_COMPAT-free), `getting-started/whats-new-v4.md` (dropped retired `add_type_compat` bullet), `decisions/summary/capacity.md` (ADR-0069/0086 rows annotated **Superseded by ADR-0156**). Historical ADRs left intact (decision records; supersession is the canonical update). NEW `tests/phase_42/test_mkdocs_strict_clean.py` (Opt-B guard: non-strict build exit 0 via subprocess + skipif-no-mkdocs; usage/capacity TYPE_COMPAT-free assertion). `py_compile` green.
### Commit 8 (ADR amendments + sentinel chain + PHASE_MAP re-scope) — built 2026-06-05, anchors verified
ADR-0069 + ADR-0086 → **status: Superseded** by ADR-0156 (frontmatter + header). ADR-0156 + ADR-0159 → **§Implementation (Phase 42)** footers. **8 amendment paragraphs**: 0070/0071/0132 (per ADR-0156), 0072/0078/0143/0146/0147 (per ADR-0159) — each `§Amendment (Phase 42 — ADR-015x)`. NEW `tests/phase_42/test_adr_amendment_sentinels.py` (chains from phase_41; anchors 0156/0159 Accepted+Implementation, 0069/0086 Superseded, the 8 amendment markers). PHASE_MAP Phase 42 block: **As-shipped deltas** paragraph recording PB-7 (detector), PB-23 (Phase-46 body-migration/invoke deferral), PB-22 (uppercase), PB-24 (materialise deferral), PB-16 (scoped strict), the 6-not-5 / 10-not-9 parity, __all__ 112→117, grep-zero scoping, L3-57 Opt 3. `py_compile` green; all sentinel anchors verified present.

### Gate 1 (Linux docker, 2026-06-05): 8 failed / 3661 passed / 9 skipped — 2 root causes, test-only
- **RC1 (2 fails) — `to_properties` inputs/outputs stripped (S1) but two tests still asserted their presence** (missed in the test sweep): `phase_27/test_capacity_dataclass.py::test_capacity_to_properties_shape`, `phase_28/test_capacity_layer_register_capacity.py::test_register_capacity_happy_path_global`. Fix: assert `inputs`/`outputs` absent from props + declaration fields retained; phase_28 now asserts the PRODUCES/CONSUMES edges instead. Corpus swept for `properties["inputs"|"outputs"]` — only these 2.
- **RC2 (6 fails) — surviving `phase_29` slate still asserted the 5 retired exports present** (`PHASE_29_NEW_EXPORTS` present-check + parametrized importable). Flipped to retirement checks (`PHASE_29_RETIRED_EXPORTS`: absent from `__all__` + unresolvable), mirroring the Phase 41 phase_31 pattern.
- Both test-only; no source regression. `py_compile` green. Re-gate after fixup commit.

### Build complete — ready for push-all + single Linux gate
8 commits on `phase-42` (1 source bipartite, 2 source context+instances, 3 detector, 4 test retire+slate, 5 test behavior suite, 6 audit+L3-57, 7 Model C docs, 8 ADR amendments). All `py_compile` + grep + non-strict-mkdocs verified in-sandbox; **cumulative pytest gate runs on Linux docker** (sandbox lacks FalkorDB/tomli). Expect 1-2 gate-driven follow-ups per Phase 43 precedent — most-likely surfaces: phase_30 find_pipeline fixtures (low — verified result-based not edge-count), phase_32 Integration B (semantic-preservation), any test registering capacities + inspecting node inputs/outputs props. No version bump (slot 42 ≤ high-water 44).
