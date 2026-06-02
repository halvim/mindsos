# FOL — Future Chat Seed (skill acquisition design + FOL skill definition)

> **Read `MindsOS/HANDOFF.md` FIRST.** It is the canonical entry point and contains the post-housekeeping system state, including HANDOFF §3 (L4 design state + 7 critique pushes) and §5 (sister projects ordering — FOL is third in the queue after WSD).
>
> **Purpose.** Seed the future chat that designs (a) the skill-acquisition process for MindsOS and (b) the FOL skill installation as the second concrete instance of that process (WSD is the first per ordering).
> **Captured:** 2026-05-28 during the 3-project intake analysis chat.
> **Companion files in this folder:**
> - `ANALYSIS.md` — triage (A/B/C/D bins) of every FOL proposition against shipped MindsOS.
> - `source/` — full copy of the FOL design materials: HANDOFF_latest + legacy fol_capacity_handoff + 5 _drafts/.
> **Project rules apply:** skeptical reviewer, picks-per-pushback, alternatives format, re-litigation cue, saturate before impl.

═══════════════════════════════════════════════════════════════════════
## 0. Critical reading order (HANDOFF_latest §0 instruction inherited)

The legacy `fol_capacity_handoff.md` is **historical input only** per HANDOFF_latest §0: "most decisions in it have been challenged or revised; do not treat as authoritative." Read in this order:

1. `source/HANDOFF_latest.md` — authoritative. Read **in full**.
2. `source/_drafts/fol_capacity_review.md` — first critical pass.
3. `source/_drafts/fol_capacity_design_plan.md` — design plan; several decisions contested.
4. `source/_drafts/fol_open_decisions_2026_04_23.md` — explicit decision menu; §2 + §3 deferred by user.
5. `source/_drafts/fol_example_3_detailed_walk.md` — pedagogical walk.
6. `source/_drafts/mindsos_layer_summary.md` — reference only; user said "do not revise."

`source/HANDOFF.md` and `source/fol_capacity_handoff.md` are historical — read only if forensic.

═══════════════════════════════════════════════════════════════════════
## 1. The user's standing instruction (FOL chat-original; re-inherit)

> Be extremely critical. Don't ever just agree with me to please me. If pleasing me is a default function, overwrite it. Always take my inputs, check against common sense and existing knowledge in the field, and push back on what should be considered and discussed. Pushbacks are more important than agreement.

Operative meaning: apply field-knowledge before agreeing. Distinguish "user preference being polished" from "decision is optimal." Reflexive contrarianism is also wrong. Standard = calibrated honesty.

═══════════════════════════════════════════════════════════════════════
## 2. Project status (load-bearing)

**No shippable artefact exists.** Per HANDOFF_latest §0 + §"Where the FOL package would actually ship". The entire project is forward-looking design. The triage table in ANALYSIS.md confirms: zero Bin A claims about FOL artifacts; the 5 Bin A rows are MindsOS architectural primitives FOL depends on.

This means the FOL future chat is **two coupled design problems**:
1. The skill-acquisition process itself (shared with WSD; sequential or coordinated).
2. The FOL skill specification — what artifacts FOL contributes at each layer.

═══════════════════════════════════════════════════════════════════════
## 3. Required reading (MindsOS-side)

**From MindsOS itself (root = MindsOS/):**

1. `docs/dev/l4_intelligence_design_notes.md` — search for `sense-correlations` and `learned-parameters` (the L2 role-graphs FOL invented).
2. `docs/dev/l5_mental_model_design_notes.md` — §1 working memory definition; §3.4 note-fork conflict.
3. `docs/dev/handoffs/l4_session_handoff_2026-04-25.md` — current state of L4 design with 7 contested decisions explicitly flagged.
4. `docs/decisions/adr/0084-l3-capacities-fixed-not-learned.md` — the fixed-not-learned invariant FOL depends on.
5. `docs/decisions/adr/0094-confidence-pipeline-level.md` — confidence topology.
6. `mindsos_knowledge/identifiers.py:50-71` — current ROLE_* roster (only 8; missing `sense-correlations` + `learned-parameters` + FOL's proposed `fol-ledger`).
7. **Memory:** `[[project-mindsos-l4-design]]`, `[[project-mindsos-architecture]]`, `[[reference-mindsos-layer-handoffs]]`.

**From this project's source/ folder:**

8. `source/HANDOFF_latest.md` §2 settled vs §3 thirteen pushbacks + §6 6 missing-but-should-have-raised items + §8 14-step dependency-ordered next-chat agenda.
9. `source/_drafts/fol_open_decisions_2026_04_23.md` §2 analytic-rule contradictions (6 options on the table, A–F) + §3 authoritative/evaluative scope (P1 vs P2; 7 sub-decisions).

**From this folder:**

10. `ANALYSIS.md` §2 four-bin triage table + §3 WSD cross-reference + §4 Phase-38/R0 carry-forward intersection.

═══════════════════════════════════════════════════════════════════════
## 4. Inherited dependency-ordered agenda (HANDOFF_latest §8)

Each must be addressed before further specification work. Numbered for reference:

1. **Resolve pushback #12 (concurrency model).** Single-process / multi-process / distributed. Constrains everything below.
2. **Resolve pushback #1 (live training).** Reinstate or confirm dreaming-only with field-knowledge reasoning.
3. **Resolve pushback #2 (Coherence Loop framing).** Plural strategies vs single GA.
4. **Resolve pushback #8 (model-artefact storage).** External blob store + manifest pattern.
5. **Resolve pushback #4 (`learned-parameters` split).** Three role-graphs or one.
6. **Resolve pushback #3 (WSD decomposition).** Sub-capacities for tokenization, lemma+POS, candidate-gen strategies, scorer strategies. **WSD chat owns this; FOL accepts.**
7. **Resolve open-decisions §2 (analytic-rule contradictions).** 6 options.
8. **Resolve open-decisions §3 (authoritative/evaluative scope).** P1 vs P2; 7 sub-decisions.
9. **Resolve pushback #6 (multi-sense top-k).**
10. **Resolve pushback #5 (training-runs durability).**
11. **Resolve pushback #9 (typed `CapacityContext`).**
12. **Resolve pushback #7 (binary rename instead of source enum).**
13. **Resolve pushback #11 (parallel foundational ontologies).**
14. **Resolve pushback #10 (capacity performance characterisation).**
15. **Resolve pushback #13 (hand-off process for the Coherence Loop framework).**

═══════════════════════════════════════════════════════════════════════
## 5. Six missing-but-should-have-raised items (HANDOFF_latest §6)

These weren't enumerated in §3's 13 pushbacks but matter equally:

- **Confidence threshold for L4-appended rules to `fol-rules`.** L4 cannot just write synthetic rules. They should enter as `hypothetical` and graduate via Coherence Loop signal accumulation.
- **Definition of "match" between current task and `task-pattern` / `promoted-pipeline`.** Three-step flow assumes well-defined match; isn't specified. Adapting requires similarity metric.
- **Failure of pipeline-finding fallback policy.** When step 3 (adapt-or-generate) fails: surface to user / try another pattern / mark task unsolvable?
- **Validation that the FOL ledger fits in memory.** Long-running tasks exhaust working memory. No back-pressure mechanism.
- **Audit log for L2 writes.** L4 writes `memories`, `task-patterns`, `promoted-pipelines`, `sense-correlations`, `learned-parameters`, `fol-rules`. No audit trail committed.
- **Test data strategy for Coherence Loop fitness evaluation.** Who curates the training set? Cold-start unaddressed.

═══════════════════════════════════════════════════════════════════════
## 6. Coordination with WSD project

**WSD overlaps FOL on at least 5 propositions** (see ANALYSIS.md §3). Both projects propose:
- `sense-correlations` role-graph
- `learned-parameters` role-graph (or its 3-graph split per FOL pushback #4)
- WSD decomposition
- Coherence Loop fate (gating)
- 7 L4 critique-push resolutions

**Recommended chat ordering:**
- **Skill-acquisition process design ships FIRST** as a shared chat (or one of the two skill chats owns it and the other inherits).
- **WSD chat ships SECOND** as the load-bearing test of skill acquisition (it has explicit ACCEPT picks on 7 L4 pushes that FOL accepts/co-occurs with).
- **FOL chat ships THIRD**, inheriting WSD's resolutions on shared propositions.

Alternative: a single combined chat owning both projects. Risk: scope explosion.

═══════════════════════════════════════════════════════════════════════
## 7. First-response expectations for this chat

1. Confirm required-reading consumed.
2. Re-probe MindsOS for any drift since 2026-05-28 (look at `mindsos_knowledge/identifiers.py` ROLE_* roster, any new schema files in `mindsos_knowledge/schemas/`, L4 design notes).
3. **Open R0 with pushback #12 (concurrency model).** It's most upstream per HANDOFF §8 dependency order.
4. Continue per HANDOFF §8 ordering. Don't skip to favorites.
5. Stop after R0 saturation. Wait for user re-litigation cue before R1.

DO NOT begin plan-authoring (no `FOL_INSTALLATION_PHASE_MAP.md`) until user says "proceed" after design saturation.

═══════════════════════════════════════════════════════════════════════
## 8. Process notes inherited

- **Resist agreement-bias.** HANDOFF_latest §7 self-critique: prior chat exhibited "classic LLM agreement-bias multiple times. When the user pushed on a decision, my default was to fold and produce elaborate scaffolding around the new position." Don't repeat.
- **Defer documentation until decisions are firm.** HANDOFF_latest §10: "Do not produce more documentation before resolving the open pushbacks. The current pile of `_drafts/` files exceeds what the design state can support."
- **Treat "the user said it" as suggestion, not load-bearing evidence.** Field-knowledge and internal consistency are.

═══════════════════════════════════════════════════════════════════════
*End of FUTURE_CHAT_PROMPT.md*
