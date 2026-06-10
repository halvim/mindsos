# WSD — Future Chat Seed (skill acquisition design + WSD skill definition)

> ⚠️ **UPDATE 2026-06-10 — Phase 50 (SA-1) SHIPPED: the install driver EXISTS.** `mindsos_server/skills/` (manifest/preflight/records/driver/activation) + `mindsos skill` CLI + reference bundle at `tests/fixtures/skill_bundle_ref/` (your authoring template). Read `confirmation_docs/PHASE_50_DESIGN_LOG.md` — binding bundle-author rules: content props must avoid `RESERVED_PROPERTY_KEYS` (I4); content must use the target role's declared NodeTypes — type membership is enforced even at strict=False (I5); de-installed content is visible-but-marked (G1 marker-only; read-filtering is on the v2 ledger).

> ⚠️ **UPDATE 2026-06-09 — the skill-acquisition process is DESIGNED AND CLOSED.** Section A below (and §4-A's "design the install lifecycle") is DONE — do not redesign it. Read `confirmation_docs/SKILL_ACQUISITION_PROCESS_DESIGN_LOG.md` (the contract) + `confirmation_docs/SKILL_ACQUISITION_PROCESS_PHASE_MAP.md` **§5 (WSD inheritance contract — binding on this chat)**. This chat opens after `phase-50-confirmed` (SA-1 ships the install driver). Also read `projects/ANALYSIS_DELTA_2026-06.md` BEFORE `ANALYSIS.md` — several claims below (resident lifecycle, 8-role roster, L4 "nothing shipped", `sense-correlations`) are falsified by Phases 39–49; the delta is authoritative.

> **Read `MindsOS/HANDOFF.md` FIRST.** It is the canonical entry point and contains the post-housekeeping system state, including HANDOFF §3 (L4 design state + 7 critique pushes WSD has ACCEPT picks for) and §5 (sister projects ordering).
>
> **Purpose.** Seed the future chat that designs (a) the skill-acquisition process for MindsOS and (b) the WSD skill installation as the first concrete instance of that process.
> **Captured:** 2026-05-28 during the 3-project intake analysis chat.
> **Companion files in this folder:**
> - `ANALYSIS.md` — per-layer triage (A/B/C/D bins) of WSD propositions against shipped MindsOS.
> - `source/` — full copy of the WSD project: 21 files including 5 `coordinated_change_L{0-4}*.md` docs, 5 `pending_adrs/L{0-4}*.md` ADR-draft docs, WSD_DESIGN_HANDOFF, WSD_GOAL_FINALIZATION_OUTPUT, WSD_USE_CASES (116KB; 16 stress-test use cases), and demo/business catalogs.
> **Project rules apply:** skeptical reviewer, picks-per-pushback, alternatives format, re-litigation cue, saturate before impl.

═══════════════════════════════════════════════════════════════════════
## 0. Critical reading order

Per WSD_DESIGN_HANDOFF.md §11 reading list, adapted:

1. `source/WSD_DESIGN_HANDOFF.md` — authoritative 2026-04-26 handoff. Read §2 TL;DR + §3 reframing + §6 blockers + §10 open questions.
2. `source/WSD_GOAL_FINALIZATION_OUTPUT.md` — goal-finalization output (2026-04-30).
3. `source/pending_adrs/README.md` — per-layer ADR-draft organization.
4. `source/pending_adrs/L{0,1,2,3,4}.md` — 5 files; ~50 proposed ADRs total. §A drives ADR drafts; §B drives code/schema; §C drives interfaces; §D drives open sub-questions.
5. `source/coordinated_change_L{0,1,2,3,4}*.md` — 5 files; per-layer change handoffs with deeper rationale.
6. `source/WSD_ARCHITECTURE.md` — full architectural design (40KB).
7. `source/WSD_USE_CASES.md` — 16 use cases (116KB); load on demand when concrete capability questions arise.

`source/MINDSOS_DEMO_EXAMPLES.md` + `source/MINDSOS_BUSINESS_PROBLEMS.md` are post-v1 priority per WSD_GOAL_FINALIZATION_OUTPUT.

═══════════════════════════════════════════════════════════════════════
## 1. The user's standing instruction (WSD chat-original; re-inherit)

> Be extremely critical. Don't ever just agree with me to please me. If pleasing me is a default function, overwrite it. Always take my inputs, check against common sense and existing knowledge in the field, and push back on what should be considered and discussed. Pushbacks are more important than agreement.

Operative meaning: apply field-knowledge before agreeing. Standard = calibrated honesty, not contrarianism.

═══════════════════════════════════════════════════════════════════════
## 2. Project status (load-bearing)

WSD is **goal-finalized, pre-code, with 4 MindsOS-internal blockers** (WSD §6). One of those — §6.2 phantom FOL dependency — was **resolved during this housekeeping chat**: FOL materials are now at `projects/fol/source/`.

Remaining blockers:
- §6.1 Coherence loop fate (resolution cascades to FOL pushback #2-#5; resolve once)
- §6.3 Multi-domain ontology scope (v1 vs v3+)
- §6.4 Ontology learning (v1 vs v3+ research)

═══════════════════════════════════════════════════════════════════════
## 3. Required reading (MindsOS-side)

**From MindsOS itself (root = MindsOS/):**

1. `docs/dev/l4_intelligence_design_notes.md` — search for `sense-correlations` and `learned-parameters`.
2. `docs/dev/l5_mental_model_design_notes.md` — §1, §3.4 note-fork dep.
3. `docs/dev/handoffs/l4_session_handoff_2026-04-25.md` — §3 settled vs §4 contested (7 critique pushes); load-bearing for WSD's C-L4-1..C-L4-7 picks.
4. `docs/decisions/adr/0150-l2-knowledge-lifecycle.md` — role-graph expansion mechanism (§"Expansion requires an ADR amendment"); WSD's `world-axioms` proposal triggers this.
5. `docs/decisions/adr/0084-l3-capacities-fixed-not-learned.md` — WSD's "wsd capacity is fixed and deterministic" relies on this.
6. `mindsos_capacity/capacity_layer.py` — current capacity model (capacities as nodes; resident lifecycle on CapacityLayer). WSD C-L1-2 / C-L3-1 / C-L3-2 propose architectural reframes.
7. `mindsos_knowledge/identifiers.py:50-71` — current 8 ROLE_* roster.
8. **Memory:** `[[project-mindsos-phase-31]]` (resident lifecycle ship), `[[project-mindsos-l4-design]]`, `[[project-mindsos-architecture]]`.

**From this folder:**

9. `ANALYSIS.md` — per-layer triage. §2 per-layer table + §3 FOL cross-reference + §4 Phase-38/R0 carry-forward + §5 §6 blockers update.

═══════════════════════════════════════════════════════════════════════
## 4. Load-bearing decision stack (inherited; numbered for reference)

### **A — Skill-acquisition process design (load-bearing for both WSD and FOL)**

Definition: skill acquisition = the mechanism by which a multi-layer skill (L1+L2+L3+L4+L5 artifacts as a bundle) gets installed into MindsOS. Includes:
- Per-layer install lifecycle (what's installed first, what's installed last, dependency ordering).
- Bundle integrity (skill-as-a-unit vs per-layer independent install).
- Local vs Global installation tiers.
- Conflict resolution (what if a skill proposes L2 role-graphs that conflict with shipped names).
- Audit + provenance (which user, which session, which approval flow).
- De-installation / removal.
- Reference: `[[skill]]` definition per user 2026-05-28 ("a coherent capability that spans layers").

This design is shared with the FOL future chat (`projects/fol/FUTURE_CHAT_PROMPT.md` §6). **Recommended chat ordering:** skill acquisition FIRST as a shared chat, then WSD installation chat, then FOL installation chat.

### **B — WSD §6.1 — Coherence loop fate**

Three resolutions per WSD source:
- (a) `learned-parameters` written by maintenance dreams instead. WSD capacity reads it as before. Cleanest minimal-change.
- (b) `learned-parameters` dropped from v1. WSD sense-ranker weights become static config in the capacity declaration (admin-tunable, not learned).
- (c) Future-plan Entry 3 (assumption-violation grounding) ships and writes `learned-parameters` based on per-step assumption-pass patterns.

**Same blocker as FOL pushback #2-#5.** Resolve once for both projects.

### **C — Architectural reframes (the 3 real C-bin conflicts at L1+L3)**

**C-L1-2 / C-L3-1 — Capacities-as-hyperedges.** WSD proposes capacities as hyperedges with DataStates as nodes (pending_adrs/L1 §A.2 + L3 §A.1). MindsOS Phase 27-31 ships capacities as nodes. This is a **MindsOS-architecture-level reframe**, not skill-specific. Three picks:
- (a) Accept the reframe; supersede Phase 27-31 capacity-as-node ship with a v2 capacity-as-hyperedge ship.
- (b) Reject the reframe; WSD adapts to capacity-as-node.
- (c) Hybrid: WSD's "capacities" are L4-level "skill capacities" (hyperedges of L3 nodes), preserving Phase 27-31 + adding a new L4-level construct.

**C-L3-2 — Monitor lifecycle ownership.** WSD wants L4-owned (coordinated_change_L3 §9). MindsOS Phase 31 shipped CapacityLayer-owned. Three picks:
- (a) Move ownership L3 → L4; supersede Phase 31 lifecycle ship.
- (b) Hold Phase 31 form; WSD monitors register via L3 lifecycle.
- (c) Hybrid: descriptive monitor nodes at L3 (per WSD), lifecycle methods stay on CapacityLayer, L4 calls them via orchestration. Likely closest to both proposals.

**These should be ratified in the L4/L5 plan chat or skill-acquisition chat, NOT in the WSD-specific chat.** Scope mis-fit if ratified by a skill chat alone.

### **D — 7 L4 critique-push picks (C-L4-1 through C-L4-7)**

WSD has explicit ACCEPT picks on 7 of the 8 L4 critique pushes. **These belong in the L4/L5 plan chat**, not the WSD chat. WSD's picks are inputs; the L4/L5 plan chat ratifies.

### **E — `world-axioms` sub-graph addition**

pending_adrs/L2 §A.1. New v1 role-graph. ADR-0150 §am-1 requires ADR amendment for role expansion. Decision: amend ADR-0150 or reject `world-axioms` as a v1 scope item.

### **F — 6 new L2 importers**

SemCor, OntoNotes, VerbNet, SemLink, GlossTag, FrameNet-extended. Each follows the Phase 15a ImporterProtocol pattern. Sub-decisions: which ship at v1; which defer to v3+; SemCor priority confirmed in WSD §4.2.

### **G — 3 new L2 role-graphs**

`parameter-staging`, `pending-promotions`, `capacity-gaps`. Each requires an ADR-0150 amendment.

### **H — L1 InterGraphEdge naming reconciliation (C-L1-1)**

WSD proposes `InterGraphEdge` (capital G). MindsOS ships `IntergraphEdge` (lowercase g) at Phase 05b. Pure naming reconciliation; verify semantic equivalence then accept whichever name.

### **I — WSD §6.3 + §6.4 scope-defer decisions**

Multi-domain ontology + ontology learning. Recommended defer to v3+; confirm or refute.

═══════════════════════════════════════════════════════════════════════
## 5. Coordination dependencies

**Upstream:**
- L4/L5 plan chat must resolve the 7 L4 critique pushes (R0-PB-1) before WSD's C-L4-1..C-L4-7 can land as ADRs.
- ADR-0150 amendment for `world-axioms` + 3 new role-graphs must happen at L2 design level, not skill level.

**Coordinated:**
- FOL chat ratifies pushback #2-#5 (Coherence Loop) — same blocker as WSD §6.1.
- DWF chat ratifies AlignmentsImporter body — skill-acquisition is the umbrella process; both should converge on the same install lifecycle.

**Downstream:**
- FOL chat inherits whatever WSD ratifies on 7 L4 pushes.
- v3+ chats on multi-domain ontology + ontology learning inherit defer decisions.

═══════════════════════════════════════════════════════════════════════
## 6. First-response expectations for this chat

1. Confirm required-reading consumed.
2. Re-probe MindsOS for drift since 2026-05-28 (specifically: ROLE_* roster, capacity model, resident lifecycle ownership, L4 critique-push resolutions).
3. **Open R0 with section A (skill-acquisition process design).** It's most upstream; resolution shapes every other section.
4. **If section A is going to take the full chat, defer sections B-I to their own chats.** Don't try to ratify 50 ADRs in one session.
5. Stop after R0 saturation. Wait for user re-litigation cue before R1.

DO NOT begin plan-authoring (no `WSD_INSTALLATION_PHASE_MAP.md`) until user says "proceed" after design saturation.

═══════════════════════════════════════════════════════════════════════
## 7. Process notes inherited

- **WSD §6.2 phantom FOL dependency is resolved.** FOL materials at `projects/fol/source/`.
- **Use cases are stress-tests, not specs.** WSD_USE_CASES.md (116KB, 16 use cases) is for evaluating spec coverage; don't author specs by enumerating use cases.
- **Don't write code yet.** Per WSD §6 blockers + WSD §8.2 manual-pilot recommendation, code is premature.
- **The previous WSD chat operated under "extreme critique."** Don't fold under user push without field-knowledge check.

═══════════════════════════════════════════════════════════════════════
*End of FUTURE_CHAT_PROMPT.md*
