# L4/L5 Plan — Three-Chat Split (now Four-Chat with parallel reframes)

**Date:** 2026-05-28
**Author:** Captured by Cowork chat after R0 saturation probe + HANDOFF/L4_L5 prompt review.
**Status:** Plan-of-record. Chat A complete (see CHAT_A_DECISIONS.md). Supersedes the implicit single-chat framing in `confirmation_docs/L4_L5_PLAN_NEXT_CHAT_PROMPT.md`.

## Current state (2026-05-29)

- **Chat A** — L4 design-resolution: **CLOSED 2026-05-28.** ~70 picks across 6 rounds. Settlement record at `CHAT_A_DECISIONS.md`.
- **Chat B** — L5 + note-fork: pending.
- **L1/L3 reframe chat** — pending; can parallelize with Chat B.
- **L2 chat** — pending; can parallelize with Chat B.
- **Chat C** — plan-authoring: waits for Chat B + reframe outputs.

---

## Why three chats, not one

The original L4_L5_PLAN_NEXT_CHAT_PROMPT.md frames a single design-resolution-then-plan-authoring effort. Probe + sister-project review surfaced this is under-scoped:

1. **L4 v1 scope is larger than "7 push resolutions."** The WSD project's `coordinated_change_L4_intelligence_and_als.md` accepts 6 of 7 pushes but ALSO proposes major new L4 machinery: ALS (Audited Learning Subsystem) as coherence-loop replacement, MSUR pipeline, SCMS BSP turn pipeline, six-phase task lifecycle, Phase 6 failure diagnosis, S8 signal source, three audit policies. Treating WSD's ACCEPT picks as "inherited" silently absorbs these architectural additions. They need ratification in their own right.
2. **L5 is gated on a not-yet-decided L0 mechanism (note-fork).** L5's retention model picked Option A (note-fork) in 2026-04-26, but note-fork itself is server-pivot v2 scope and unshipped. The L5 chat must resolve the L5/note-fork dependency before L5 phasing makes sense. That work doesn't belong in the L4 chat.
3. **Saturation pattern wants one contested-axis cluster per chat.** L4 alone is 7 push axes + ALS/MSUR/SCMS axes + L3/L4 boundary review + FOL placement decisions. Loading L5 retention + note-fork on top exceeds what a single chat can saturate without R-round explosion.

---

## Chat A — L4 design-resolution

**Goal.** Produce a settled L4 v1 architecture document that downstream chats (B, C, WSD installation, FOL installation, skill-acquisition process) inherit as foundation.

**Inputs (required reading at chat-open):**
- `HANDOFF.md` §3 + §6 + §10.
- `docs/dev/l4_intelligence_design_notes.md` (full).
- **`docs/dev/use_cases_text_realm.md`** — NLU + code + cross-realm UCs (UC-NLU-1/2/3, UC-CODE-1/2/3, UC-X-1) + 4 dreaming pipelines. **B2 stress-test set #1.**
- **`projects/wsd/source/WSD_USE_CASES.md`** — 16 WSD architectural stress tests (UC-WSD-1 through UC-WSD-16). **B2 stress-test set #2.**
- 12 L4 ADRs: 0091, 0098, 0101–0112.
- `projects/wsd/source/coordinated_change_L4_intelligence_and_als.md` (LOAD-BEARING — proposes WSD's L4 architecture).
- `projects/wsd/source/pending_adrs/L4_intelligence.md` (9 §A ADRs awaiting ratification).
- `projects/fol/source/HANDOFF_latest.md` §3 pushbacks #1, #2, #5, #12.
- This file (`CHAT_PLAN_L4_L5.md`) for chat scope boundary.
- `docs/_workbench/CHAT_A_L4_BASELINE.md` (compiled from the above; written before Chat A opens; contains B2 UC-to-decision mapping in §9.5).

**B2 framing (post 2026-05-28 user pick).** Both case sets are **stress-test narratives, not pass/fail tests.** Chat A uses them for: (i) grounding picks ("does my pick break UC-X?"); (ii) negative-space mapping (picks may invalidate UCs; Chat A names which).

**Scope (50 decisions; full list in `CHAT_A_L4_BASELINE.md` §8):**
1. Ratify Pushes 1–7 (D1–D7) + Push 8 signal-thread (D8).
2. Decide L4 v1 scope vs v2/v3 deferrals on WSD's architectural additions — ALS (D9), MSUR (D10), SCMS (D11), six-phase lifecycle (D12), Phase 6 (D13), S8 (D15), audit policies (D25). **Pre-resolved: ALS adopted per Q5.**
3. Confirm L3/L4 boundary direction (monitor lifecycle — D36; action contracts — D37). **Detailed supersession routed to L1/L3 reframe chat per Q2.**
4. Decide concurrency model — D32. **Pre-resolved: pick B (single-process multi-threaded). R1 confirms.**
5. Decide `learned-parameters` split — D28 (FOL #4).
6. Confirm `sense-correlations` + `learned-parameters` v1 disposition — D34. **Pre-resolved: ship both per Q4.**
7. Confirm FOL placement — R0-PB-4 already settled as deferred-with-coordinated-graphs.
8. Confirm L4 v1 single-tenant — D35.
9. Resolve UC-surfaced decisions D41–D50 (sufficient-predicate, document-scope SCMS, multi-domain, decision-precedent retrieval, per-segment provenance, calibration target system-wide, cross-realm DataState bridge).

**Out of scope (defer to Chat B or C):**
- L5 retention model + note-fork decision (Chat B).
- Phase numbering / sentinel chain disposition (Chat C — plan-authoring mechanics).
- Carry-forward backlog absorption strategy (Chat C).
- Model C remediation timing (Chat C).
- Ship-shape defaults (Chat C).

**Output.** A revised `docs/dev/l4_intelligence_design_notes.md` plus a settlement doc (`docs/_workbench/CHAT_A_SETTLEMENT.md`) capturing every pick + rationale. Pending ADRs in `projects/wsd/source/pending_adrs/L4_intelligence.md` get triaged: ratify / defer-with-condition / reject.

**Stop conditions.** Saturation = R5 produces impl-locks only, zero reversals. If a contested axis isn't resolvable in this chat (e.g., WSD's capacities-as-hyperedges architectural reframe — Chat A is the wrong scope to ratify this), record explicitly and route to its proper chat.

---

## Chat B — L5 design-resolution + note-fork decision

**Goal.** Settle the L5 retention model and the L0 note-fork dependency. Produce a settled L5 v1 architecture document.

**Inputs (required reading at chat-open):**
- `HANDOFF.md` §4.
- `docs/dev/l5_mental_model_design_notes.md` (full, especially §3.4 2026-04-26 amendment).
- `docs/_workbench/CHAT_A_SETTLEMENT.md` (Chat A's output — L4's write-API to L5 is a constraint).
- ADR-0098 (mental-model retention default).
- Whatever `docs/PIVOT_V1_SCOPE_2026-04-26.md` becomes after housekeeping (currently absent — link dangling per mkdocs probe).
- Note-fork mechanism design materials (location TBD — may need to extract from archive).

**Scope:**
1. Resolve L5 §3.4 Option A/B/C: Option A picked in 2026-04-26 (memories use v2 note-fork). Re-confirm or re-litigate.
2. Decide note-fork ship-position: pull forward into v1, sequence after server-pivot v2, or redesign L5 retention.
3. Settle L5 v1 write contract against L4's write-API (inherited from Chat A).
4. Resolve R0-PB-3 (L4 vs L5 ordering).
5. Decide L5 tenancy (Global L5 + Local L5 stated; confirm or contest).
6. Failure-recording semantics (ref:problem_trace pointer pattern — already settled per ADR-0096; confirm vs Chat A's Phase 6 architecture if WSD's ALS lands).

**Out of scope:**
- L4 architecture (already settled in Chat A).
- Plan-of-record / phasing (Chat C).

**Output.** Revised `docs/dev/l5_mental_model_design_notes.md` + settlement doc (`docs/_workbench/CHAT_B_SETTLEMENT.md`).

---

## Chat C — Plan-authoring (PHASE_MAP analog)

**Goal.** Produce the phased rollout plan (`L4_L5_PHASE_MAP.md`) analogous to `confirmation_docs/PHASE_MAP.md`. This is the document that the L0–L3 rollout had.

**Inputs:**
- `confirmation_docs/PHASE_MAP.md` §1 (cross-cutting decisions), §5 (Phase 38 row), §7 (open questions).
- `confirmation_docs/PHASE_38_DESIGN_LOG.md` §4 (19-item carry-forward — LOAD-BEARING).
- `docs/_workbench/CHAT_A_SETTLEMENT.md`.
- `docs/_workbench/CHAT_B_SETTLEMENT.md`.
- `confirmation_docs/L4_L5_PLAN_NEXT_CHAT_PROMPT.md` R0 slate (PB-2, PB-5, PB-6, PB-7, PB-8, PB-11 — the plan-mechanics PBs).

**Scope:**
1. Phase-author L4 v1 implementation (inherits Chat A scope).
2. Phase-author L5 v1 implementation (inherits Chat B scope; gated on note-fork per Chat B pick).
3. Decide R0-PB-2 carry-forward absorption strategy (three-stream split shape).
4. Decide R0-PB-5 phase numbering (continue Phase 39+ vs reset to L4-00).
5. Decide R0-PB-6 sentinel chain disposition.
6. Decide R0-PB-7 cookbook gaps.
7. Decide R0-PB-8 Model C remediation (probe shows 16 mkdocs warnings, not 50 — substance differs from HANDOFF claim).
8. Decide R0-PB-11 ship-shape default convention.

**Out of scope:**
- Any L4 or L5 architectural picks (already settled).

**Output.** `confirmation_docs/L4_L5_PHASE_MAP.md` + an updated `HANDOFF.md` §10 reading-map entry.

---

## Dependencies

```
Chat A (L4 resolution)  →  Chat B (L5 resolution)  →  Chat C (Plan-authoring)
        ↓                          ↓                          ↓
   L4 settlement doc        L5 settlement doc          L4_L5_PHASE_MAP.md
```

Chat B can start with Chat A's draft if Chat A is mid-flight, but cannot finalize until Chat A's L4-write-API-to-L5 is settled.

Chat C cannot start until both Chat A and Chat B finalize.

WSD installation chat, FOL installation chat, and skill-acquisition process chat all wait on Chat A at minimum.

---

## Open meta-questions about this plan

These are pushbacks against THIS plan itself, surfaced before Chat A opens:

1. **Is Chat A actually single-chat-feasible?** Scope above is 8 numbered items + 7 push resolutions + ratifying WSD's 9 pending L4 ADRs. WSD ANALYSIS-PB-A3 explicitly flags some WSD propositions (capacities-as-hyperedges, monitor lifecycle ownership) as "MindsOS-architecture-level, not skill-specific — ratifying them in a WSD chat is scope mis-fit." Same risk applies to Chat A absorbing WSD's L4 additions.
2. **Should there be a Chat A.5 for the architectural reframes?** Capacities-as-hyperedges (C-L1-2 + C-L3-1) supersedes Phase 27. Monitor lifecycle ownership (C-L3-2) supersedes Phase 31. These are L1/L3 reframes, not L4 design. Could route to a separate "architectural-reframe ratification" chat.
3. **Skill-acquisition process chat is upstream of WSD/FOL installation but not in this plan.** Per `projects/README.md` ordering: skill-acquisition design ships BEFORE WSD installation. Does Chat A inherit that ordering, or does Chat C author the skill-acquisition phase plan too?
4. **Can Chat B start before note-fork itself is designed?** L5 §3.4 Option A picked note-fork, but note-fork's own design lives in server-pivot v2 materials. If those materials are missing (`PIVOT_V1_SCOPE_2026-04-26.md` is dangling per mkdocs probe), Chat B may need a prerequisite "find/redesign note-fork" step.

---

*End of CHAT_PLAN_L4_L5.md.*
