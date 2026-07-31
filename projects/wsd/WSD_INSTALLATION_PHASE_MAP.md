# WSD_INSTALLATION — Phase Map

**Authored:** 2026-06-10 at design closure (per PB-A: each downstream chat authors its own phase-map). Design authority: `WSD_INSTALLATION_DESIGN_LOG.md` (R0–R3). This map sequences the design; it does not restate it. Binding upstream contracts: `SKILL_ACQUISITION_PROCESS_PHASE_MAP.md` §5 (inheritance) + §3 (v2-trigger ledger — never pulled forward without its named trigger).

---

## §1 — Settled contract (one-paragraph summary; log is canonical)

WSD ships as **release + bundles** (inheritance §5.1): schemas, importers, capacity bodies, mechanisms = release code with own ADRs; content + registrations + L4 fills = three **sibling bundles** (`wsd-core` → `wsd-pipeline` → `wsd-learning`, chained via `requires_bundles` — R3 PB-W27, sidestepping the S8 upgrade-rejection). The capacity = `scoring.wsd_rank_senses` (fine-grained OEWN senses; Resnik-style selectional association over the **WordNet hypernym stratum** + MFS-prior fallback; mixing weights = `learned-parameters` with static defaults; per-token ranking; UD `nsubj`/`dobj`/`iobj`; multi-candidate output per WSD §4.3). Sense-correlation data lives in the **lexicon empirical-layer** (new EdgeTypes; ADMIN_AUTHORED Global preserved — ALL runtime learning routes through the S10 promotion loop: miner → `parameter-staging` (Local) → `pending-promotions` → admin application to Global). The dream miner rides `dream.maintenance` reading episode values directly (no faithful MM reconstruction at v1). Parser = spaCy via `mindsos[nlu]` optional extra; injectable; gate stays hermetic (stub + live-marked tests). **No ADR-0150 amendment anywhere in this plan** (world-axioms deferred, R2 PB-W20).

## §2 — Slots

All slots > high-water at ship time → standard 10-surface bump each. Standard pair-execution + cumulative Linux docker gate + 6-step confirm per HANDOFF §9. Rails: S (substrate), C (capacity), L (learning). 51→52→53→54→55 sequential (single tester); 56 is DWF-gated and may interleave.

> **⚠️ CORE EXTRACTION — 2026-07-31. Read this before planning any slot.**
> The `MindsOS-core` rows in slot **54** are **no longer WSD-scheduled**. They are core work,
> re-sequenced into `confirmation_docs/CORE_RECONCILIATION_PLAN.md` (CORE-C4R8). The
> 2026-06-25 pass below fixed *attribution*; this fixes *scheduling* — core builds its own
> mechanisms and no longer waits on a subsystem (RULES §8).
>
> **Two new ADRs change what this plan is built on and must be read first:**
> **ADR-0205** (abstraction levels — one graph at several resolutions; composition via
> `IntergraphHyperEdge`; no structural blobs; a Skill spans all abstraction levels) and
> **ADR-0206** (planning as a loop; milestones as DataStates; relational confidence;
> "I'm not sure"; interpretation ships as **contract only**). They redefine what a plan, a
> milestone and a pipeline *are*, and they close POST_PHASE_38 **q4**.
>
> Consequence for WSD-4: it ships the `wsd-pipeline` bundle, the NLU cookbook and the
> end-to-end scenario, which now **consumes** the core catalogs rather than containing them —
> so it cannot ship before CORE-C4R8.

> **Ownership ≠ scheduling — read before claiming any item belongs to WSD.** Phases 51–56 are WSD-**scheduled** (the slot that *builds* the work), not WSD-**owned**. Ownership of the resulting feature/code is per the **Owner column** in §2.1, which is authoritative. WSD owns only `WSD-bundle` items. `MindsOS-core` items are owned by a MindsOS layer (L0–L5/Server), ship as release code with layer-owned ADRs, and are reusable by FOL/DWF and any other consumer — WSD is merely their first consumer/forcing-function. `shared` = a MindsOS-core mechanic + a WSD-specific instance/content fill (the mechanic is core; only the fill is WSD). WSD must not be recorded as the owner of any `MindsOS-core` or `shared`-mechanic item. Per-item classification + rationale: design log §7.

| Slot | Phase | Rail | Scope | Pass criteria |
|---|---|---|---|---|
| **WSD-1** | **51** | S-1 | **Riders + empirical-layer substrate.** L3-59(b): `capacity_layer.invoke` read path + CLI → typed `CapacityContext`; union-annotation drop; remaining dict-form body cleanup (incl. `builtins/text.py` `context: Any`); phase_34 test updates. L0-25 delete-sweep completeness audit (metaedge/metahyperedge/XRef sweep; resolve the standing orphan-scan xpassed). Lexicon **empirical-layer EdgeTypes** + ADR (hypernym-class correlation stratum v1; DOLCE stratum reserved; edge props: count/smoothed-score/source/corpus-version; discipline unchanged ADMIN_AUTHORED per PB-W21). | Cumulative gate green; scoped grep-zero dict-context in `mindsos_capacity/**` (read path); empirical-layer schema round-trips through the ADR-0182 persister path; L0-25 audit documented, xfail resolved or re-routed with evidence. |
| **WSD-2** | **52** | S-2 | **Corpus bootstrap.** `SemCorImporter` + `GlossTagImporter` (ImporterProtocol; path-based source per OEWN precedent; small XML fixtures in-repo; acquisition + Princeton-license notes in ADR — R3 PB-W28). Bootstrap correlation population (admin path → empirical-layer edges; GlossTag down-weighted). **Density instrumentation**: verb-sense correlation coverage report + the DWF alignment-density hook (reports when alignment data present). ADR-0181 **physical Falkor index creation** (first retrieval consumer; the three named indexes + empirical-layer lookup index). | Importer fixture round-trips; live-marked Falkor index test; density report emitted with fixture corpus; gate green. |
| **WSD-3** | **53** | C-1 | **The capacity.** Dependency-policy ADR + `[nlu]` optional extra (spaCy pinned; missing-model → family dont-know — PB-W12/W22/W26). `perception.nlu_parse` (injectable parser, stub default), `process.extract_predicate_arguments`, `scoring.wsd_rank_senses` (Resnik + MFS chain; weights via `learned-parameters` read with static defaults). REALM_NLU DataState roster ADR + registration (`nlu.parsed_text`, `nlu.predicate_arguments`, `nlu.sense_candidates` carrying `(sense_iri, score, justification_refs)` + ambiguity flag). **`wsd-core` bundle** through the Phase-50 driver (I4/I5 rules; L3 installer entry points; minimal L2 content). | CLI invoke green with stub parser; dont-know coverage (missing model / unseen verb / absent stratum); live-marked spaCy test; bundle install→uninstall→reinstall cycle green; gate green. |
| **WSD-4** | **54** | C-2 | **Bundle + e2e (core rows EXTRACTED 2026-07-31).** ⚠️ **The `MindsOS-core` rows formerly in this slot are no longer WSD-scheduled** — the `hint.*`/`predicate.*`/`decision.*` families, the atomic v0→real `planning.*`/`phase1.*`/`orchestration.*` flip, the orchestrator default flip and the `placeholder=True` roster deletion are **core work** and are now sequenced in `confirmation_docs/CORE_RECONCILIATION_PLAN.md` (CORE-C4R8). They were always marked `MindsOS-core` in §2.1; the 2026-06-25 pass fixed the *attribution*, this change fixes the *scheduling* — core no longer waits on WSD (RULES §8, ADR-0205). Interpretation (`process.*`/`hint.*`/`derive_goal`/`map_to_task_pattern`) ships as **contract only** (ADR-0206 §8); bodies arrive in bundles. **This slot now DEPENDS on CORE-C4R8** and cannot ship its e2e scenario before it. Read ADR-0205 (abstraction levels) + ADR-0206 (planning, decomposition, confidence) before planning this slot — they change what a plan, a milestone and a pipeline *are*. **`wsd-pipeline` bundle** (`requires_bundles = ["wsd-core"]`). `usage/cookbook/nlu-slice.md`. End-to-end NLU scenario test — **first real-capacity dispatch through the six-phase lifecycle (closes the Phase 49 PB-1a "two stitched slices" gap; the POST_PHASE_38 "first feature-complete demo")**. | Live end-to-end scenario green; v0 catalogs uninstalled-by-default everywhere; grep-zero `placeholder=True` in `mindsos_capacity/builtins/`; cookbook builds clean; gate green. |
| **WSD-5** | **55** | L | **Learning loop.** Promotion-loop mechanism under S10 (producer-agnostic: staging writer API; promotion review surface; admin application to BOTH targets — `learned-parameters` values + empirical-layer edges; audit-event family + preflight per S4/S6 shapes). ALS **sense-ranker subsystem** mechanism + validator (fills 1 of 11 skeletons; others stay skeletons — PB-W5 scope amendment §4). Dream-miner hook in `dream.maintenance` consolidation path emitting staging records from episode values (PB-W24(b); same-sentence window). Real **L4 manifest slot shapes** by ADR amendment (supersedes S2 opaque slots: ALS fill = mechanism+validator entry points; signal-source payload contracts). Trimmed PB-T roster: ALS audit constants + capacity-gaps tooling (PB-W7). **`wsd-learning` bundle** (`requires_bundles = ["wsd-pipeline"]`). | Dream run over fixture episodes → staging records; promotion application lands on both targets with audit trail; ALS validator rejects malformed staging; gate green. |
| **WSD-6** | **56** | S-3 | **DWF-gated enrichment.** DOLCE/FrameNet correlation stratum over the alignment graphs; `scoring.wsd_rank_senses` reads the second stratum when present (already dont-know-safe when absent). Coverage bar set at slot R0 **with the DWF density number in hand**. | Opens only after DWF ships alignment import + density report. Stratum populated from alignments; scoring uses it; ablation test (with/without stratum) recorded; gate green. |

### §2.1 — Owner column (authoritative; added 2026-06-25, ownership-clarification pass — see design log §7)

`MindsOS-core` = owned by a MindsOS layer; release code + layer-owned ADR; reusable by FOL/DWF. `shared` = MindsOS-core mechanic + WSD-specific fill (only the fill is WSD-owned). `WSD-bundle` = WSD-specific content shipped in a `wsd-*` bundle / `projects/wsd/`.

| Slot | `MindsOS-core` (WSD is only the first consumer) | `shared` (mechanic = core / fill = WSD) | `WSD-bundle` |
|---|---|---|---|
| **51** | L3-59(b) CapacityContext read-path + CLI + union-drop + phase_34 cleanup (L3); L0-25 delete-sweep audit (L0) | lexicon empirical-layer EdgeTypes + ADR (machinery = L2 lexicon feature / sense-correlation strata = WSD) | — |
| **52** | ADR-0181 physical Falkor index creation (L0 persistence) | density instrumentation + DWF alignment-density hook (report mechanism = core / verb-sense metric = WSD) | `SemCorImporter`, `GlossTagImporter`, bootstrap correlation population (content) |
| **53** | — | dependency-policy ADR + `[nlu]` optional-extra pattern (policy precedent = core, FOL reuses / spaCy specifically = WSD); REALM_NLU DataState roster (realm reserved Phase 40 = core / NLU DataStates = WSD) | `perception.nlu_parse`, `process.extract_predicate_arguments`, `scoring.wsd_rank_senses` bodies; `wsd-core` bundle |
| **54** | **MOVED OUT 2026-07-31 → CORE-C4R8** (`confirmation_docs/CORE_RECONCILIATION_PLAN.md`). Formerly: `hint.*`/`predicate.*`/`decision.*` additive families; atomic v0→real `planning.*`/`phase1.*`/`orchestration.*` flip; first-real-capacity-dispatch e2e milestone (closes Phase 49 PB-1a) — the e2e milestone still lands here but now *consumes* the core catalogs. | — | `wsd-pipeline` bundle; `usage/cookbook/nlu-slice.md` |
| **55** | promotion-loop mechanism (producer-agnostic, S10; FOL reuses); real L4 manifest slot-shapes (ADR amendment, L4 substrate); ALS audit constants + capacity-gaps tooling | ALS sense-ranker (subsystem contract = core / sense-ranker fill = WSD); dream-miner hook in `dream.maintenance` (consolidation hook = core / miner content = WSD) | `wsd-learning` bundle |
| **56** | — | DOLCE/FrameNet enrichment-read in `scoring.wsd_rank_senses` (second-stratum read mechanism = core / stratum content = DWF+WSD) | — |

## §3 — Deferred / v2-trigger ledger (additions; SA §3 inherited unchanged)

| Item | Trigger | Owner |
|---|---|---|
| `world-axioms` role-graph (+ ConceptNet distillation + CC-BY-SA review) | First axiom-consuming capacity; ownership note: NPB14-4 guard comment says "FOL-chat-owned" — resolve there | FOL chat or demo-scenario chat |
| OntoNotes / VerbNet / SemLink / FrameNet-extended importers | First consumer (coarse clusters → OntoNotes; role-mapping → VerbNet/SemLink) | Future WSD v1.x / FOL |
| Remaining ~10 ALS subsystem mechanisms | Per-subsystem first consumer | Future chats |
| HITL channel; further scheduler infra | First interactive-approval consumer; first non-dream schedule | Future chat |
| Beam / pairwise joint inference | v1.5 quality push | WSD v1.x |
| Oblique arguments; cross-sentence FEs | v2 per WSD §5.2 | WSD v1.x |
| Faithful episode→MM reconstruction + `replay_recorded` differentiation | First consumer needing full-MM replay | Future chat (was Phase-48 PB-9 WSD-gated; miner doesn't need it — PB-W24) |
| Bundle upgrade path | First real revision of a shipped wsd-* bundle | SA §3 row, unchanged |
| Coarse sense clusters; multi-domain ontology; ontology learning | v3+ (W9/W13 ratified defers) | v3+ chats |
| Action contracts (precondition/effect fields) | L4-v2 (PB-W23; keeps Chat A C-L4-2 as direction) | L4-v2 chat |

## §4 — Scope amendments to `POST_PHASE_38_PHASE_MAP.md` §6 WSD row (recorded here; the row is historical)

1. Importers: 6 → **2** (SemCor + GlossTag) at v1 (PB-W3).
2. "ALS subsystems #1–#11 mechanism + validator catalogs" → **consumed subsystems only** (sense-ranker; capacity-gaps tooling) (PB-W5).
3. `world-axioms` → **deferred** (PB-W20; §3 row above; ownership contradiction documented).
4. PB-T roster → **trimmed** (PB-W7; §3 row above).
5. The §6 row's "ratifies WSD-specific ADRs from `pending_adrs/`" is satisfied by disposition, not wholesale: C-bin closures per design log §1 PB-W8; the ~50 pending ADR-drafts are superseded inputs, not a ratification queue.

## §5 — FOL inheritance contract (what FOL_INSTALLATION_CHAT consumes from here)

1. **Coherence-loop fate ratified (a-ALS)** — cascades to FOL pushbacks #2–#5; do not re-litigate without file-level evidence (PB-W4).
2. **Dependency-policy ADR** (slot 53) is the precedent for the prover dependency (optional extra + dont-know on absence).
3. **Sibling-bundle pattern** (PB-W27) for multi-slot skill delivery.
4. `learned-parameters` 3-way split remains FOL-owned (schema docstring, D-L2-12) — untouched here.
5. `training-runs` / `fol-rules` / `fol-ledger` stay guard-excluded until FOL's own ADR-0150 §am; `world-axioms` ownership question routed to FOL (§3).
6. Promotion-loop mechanism (slot 55) is producer-agnostic per S10 — FOL's trainers are additional producers, not a new regime.

## §6 — DWF coordination

- Slots **51–56 reserved by this map** (recorded in HANDOFF; DWF takes 57+ or later per its own map — `WSD_INSTALLATION_DESIGN_LOG.md` §3.3).
- DWF's binding deliverable to this plan: the **alignment-density number** (verb-sense FrameNet + DOLCE coverage) — gates slot 56 R0.
- Single-tester serialization: gate runs coordinate through Henrique when both chats are mid-ship.

*End of WSD_INSTALLATION_PHASE_MAP.md.*
