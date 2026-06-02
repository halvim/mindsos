# DWF Mapping — Future Chat Seed (knowledge acquisition design)

> **Read `MindsOS/HANDOFF.md` FIRST.** It is the canonical entry point and contains the post-housekeeping system state.
>
> **Purpose.** Seed the future chat that designs (a) the knowledge-acquisition process for MindsOS and (b) the DWF Mapping installation as the first consumer of that process.
> **Captured:** 2026-05-28 during the 3-project intake analysis chat.
> **Companion files in this folder:**
> - `ANALYSIS.md` — triage of every DWF proposition against shipped MindsOS (A/B/C/D bins).
> - `source/` — full copy of the DWF project zip (53 files; some HANDOFF-referenced ready-to-import bundles are absent — see DWF-PB-1).
> **Project rules apply:** skeptical reviewer, picks-per-pushback, alternatives format, re-litigation cue, saturate before impl.

═══════════════════════════════════════════════════════════════════════
## 0. Scope of the future chat

This chat designs the **knowledge-acquisition process** (renamed from the earlier "knowledge installation" framing — see WSD's `skill-acquisition` sibling). Knowledge acquisition = the mechanism by which finished knowledge artifacts (DWF being the load-bearing first example) get installed into MindsOS L2 as one or more role-graphs.

It also designs the DWF-specific installation as the first concrete instance of that process.

**Do NOT begin code or PHASE_MAP authoring in this chat.** Design pushbacks must saturate first per the project rules.

═══════════════════════════════════════════════════════════════════════
## 1. Required reading

**From MindsOS itself (root = MindsOS/):**

1. `docs/decisions/adr/0150-l2-knowledge-lifecycle.md` §82 + §amendment-1 — alignment role-graph naming + Global-only-at-v1.
2. `docs/decisions/adr/0149-l2-role-schemas-strict-false-and-tightening-rule.md` — strict=False policy.
3. `mindsos_knowledge/identifiers.py` — `alignment_role()` helper + source-prefix table + ROLE_* constants.
4. `mindsos_knowledge/schemas/alignment.py` — `AlignmentAnchor` shared-anchor pattern + 8-type closed vocab + `extra_edge_types` kwarg.
5. `mindsos_knowledge/bootstrap.py` — KL alignment-prefix handling.
6. `mindsos_admin/importers/{dolce,oewn,framenet}.py` — three shipped importers as templates.
7. `mindsos_admin/importers/__init__.py` — ImporterProtocol contract.
8. **Memory:** `[[project-mindsos-phase-15a]]`, `[[project-mindsos-phase-15b-shipped]]` — context for the deferred AlignmentsImporter body.

**From this project's source/ folder:**

9. `source/HANDOFF_latest.md` — full v6 handoff. §3 (deliverable layout), §5e (MindsOS-import design decisions D-MI-1..6), §9 (open questions).
10. `source/CHANGES_v5_to_v6.md` — v5→v6 expansion to OEWN↔FrameNet; v7 roadmap placeholder.
11. `source/dulplus-reference.md` — DULplus class reference; the `dul:` IRI prefix vocabulary the alignment uses.
12. `source/oewn-dulplus-master.tsv` (16MB, 104,728 rows) — the primary deliverable. Header: `oewn_id\tpos\tdulplus_class\tmethod\tprimary_lemma\tprovenance\tgloss`.

**From this folder:**

13. `ANALYSIS.md` — the A/B/C/D triage. Section 2 (triage table) + section 3 (Phase-38 carry-forward intersection) + section 4 (design pushback summary).

═══════════════════════════════════════════════════════════════════════
## 2. Load-bearing question stack (inherited R0 PBs)

These are the design pushbacks the analysis chat surfaced and the user deferred to this chat. Each has an analysis-time recommended pick; you may inherit or re-litigate.

### **PB-1 (PRIORITY per user) — `AlignmentsImporter` body design + knowledge-acquisition process couple**

`mindsos_admin/importers/AlignmentsImporter` was deferred at Phase 15b → Phase 28 review closure → never landed. DWF can't import until the body ships. User pick: design alongside the knowledge-acquisition process.

**Recommended approach (analysis-side default):** the knowledge-acquisition process is the same generalized abstraction; AlignmentsImporter is one concrete instance. Other instances: DolceImporter / OewnImporter / FrameNetImporter (already shipped). Generalize their common shape into a `KnowledgeAcquisitionContract` that AlignmentsImporter conforms to.

Body shape sketch:
- Read alignment data (canonical input format = TSV with required columns; secondary inputs = the 4 other DWF formats if you accept the burden).
- Group rows by source-entity IRI per the `AlignmentAnchor` shared-anchor pattern (Phase 13 PB-14).
- Emit one `AlignmentAnchor` per source entity with `ref:<role>` to the entity.
- Emit N outgoing edges per anchor, typed via `ALIGNMENT_EDGE_TYPES` (extend with `extra_edge_types` kwarg if BROAD_MATCH semantics needed beyond shipped 8-type vocab).
- Per-edge properties: `confidence: float` (D-MI-3), `method: str` (D-MI-1), `provenance: str` (D-MI-1).

Open sub-decisions:
- (1a) Canonical input format. Pick one of: master TSV / Cypher / MeTTa / JSON-LD / NTriples / CSV. Master TSV is the project's authoritative deliverable; recommended.
- (1b) Multi-class handling. Per-anchor multi-edge vs single-edge collapse via method priority. AnchorPattern allows multi-edge.
- (1c) Idempotency: MERGE semantics on (anchor_iri, edge_iri) pairs.
- (1d) Validation: hybrid validator surface per ADR-0139 (KL semantic + L1 structural).

### **PB-2 — "Finalized" is overstated.**

DWF reports 89.2% acceptable precision (Phase 9f LLM judge). v7 roadmap (`FINAL_PACKAGE/` empty dir per CHANGES_v5_to_v6) is unexecuted. ~11.5k known-wrong edges if imported as-is.

**Picks (no recommended default; user-deferred):**
- (a) Import to Global as-is; accept 10.8% error rate as v1 baseline.
- (b) Import to Local with `quality_tier: review_pending`; promote to Global per release-model after audit. Conflicts with PB-5.
- (c) Pause import; finish §9 audits + execute v7 first.
- (d) Import to Global but tag the 10.8% as `disputed` (per ADR-0133 soft-delete). Requires audit subset identification — DWF doesn't enumerate which 10.8% are wrong.

### **PB-3 — Version drift.**

DWF target = DULplus (207 classes) + OEWN 2025; MindsOS pins = DOLCE-DUL 4.1 (107 classes) + OEWN 2024. FrameNet version unspecified in v6.

**Picks (no recommended default; user-deferred):**
- (a) Hold MindsOS pins; re-run DWF pipeline against OEWN 2024 + DUL 4.1. Phase 9f LLM-judge re-run not reproducible.
- (b) Bump MindsOS pins to match DWF (OEWN 2025 + DULplus). Cascading ADR amendments.
- (c) Drop the DWF rows that don't resolve in MindsOS pins (intersection-only import). Silent data loss.
- **Analysis-blocked:** no side-by-side OWL files in the zip; exact class-IRI overlap can't be predicted. Recommend running a class-set intersection probe on whatever OWL files exist in `source/` before locking pick.

### **PB-4 (consumed by PB-1)** — AlignmentsImporter design.

Merged into PB-1.

### **PB-5 — Local-vs-Global alignment tension.**

PB-2 pick (b) wants Local-tier import; ADR-0150 §am-1 forbids it. Requires ADR amendment.

**Picks (no recommended default; user-deferred):**
- (a) Amend ADR-0150 §am-1 to permit Local alignment with promotion path.
- (b) Skip Local; accept 10.8% error rate as Global-baseline.
- (c) Ship alignment data as a separate role-graph entirely (not `alignment:*`).

### **PB-6 — Edge-type schema for SKOS-cognate semantics.**

**Downgraded from C to B during analysis** — MindsOS ships `CLOSE_MATCH` / `BROADER_THAN` / `NARROWER_THAN` already. DWF predicate choice is non-conflict.

### **PB-7 — Naming-convention reconciliation (D1; load-bearing for ANY consumer).**

Three alignment role-graph naming conventions ship in MindsOS code+docs+tests (the analysis section 2 D1 row). DWF importer needs ONE canonical form.

**Picks (no recommended default):**
- (a) `<a><->b>` (the `alignment_role()` helper return).
- (b) `<a>:<b>` (the ADR-0150 §82 form, used in `bootstrap.py` + Phase 14 tests).
- (c) `<a>-<b>` (the Phase 36 validator form).

Recommend resolving FIRST before PB-1 body design.

═══════════════════════════════════════════════════════════════════════
## 3. Other open questions inherited from HANDOFF §9

- HANDOFF §9.1 — Is `dul:Quality` the right class for ALL pertainyms? Or finer DULplus distinction?
- HANDOFF §9.2 — Should the 791 within-synset multi-class Framester assignments be preserved as secondary edges in MindsOS? (Bin C6.)
- HANDOFF §9.3 — Phase 4 novel adj/adv rules ontologically defensible?
- HANDOFF §9.4 — Method → confidence score calibration correct?
- HANDOFF §9.6 — Phase 9a upstream consistency repair: graph-level restructuring possible?

═══════════════════════════════════════════════════════════════════════
## 4. Analysis-side findings to inherit

- The DWF zip is **missing the ready-to-import bundles** (`release-v4/mindsos-imports/`, `release-v6/data/oewn-framenet-alignment.tsv`, `release-v6/mindsos-imports/`). User said files were in their respective folders; re-probe confirmed those directories are empty in the zip. Either obtain the bundles before code, or treat the master TSV at workspace root as the canonical input (PB-1 sub-1a default).
- The master TSV has **104,728 rows, not the claimed 107,518** (2,790 discrepancy unexplained in source materials).
- The v7 "triangle-driven DOLCE revision" is named but unexecuted per `CHANGES_v5_to_v6.md`. `FINAL_PACKAGE/` directory is empty.
- The Phase 28 "review closure" target named in Phase 15b for AlignmentsImporter body was never honored. PB-1 inherits this debt.

═══════════════════════════════════════════════════════════════════════
## 5. First-response expectations for this chat

1. Confirm required-reading consumed (terse paths list).
2. Re-probe MindsOS for any drift since 2026-05-28 (look at `mindsos_admin/importers/`, `mindsos_knowledge/identifiers.py`, ADR-0150 amendments).
3. **Open R0 with PB-7 (naming reconciliation) FIRST.** Its resolution is upstream of every other PB body. Don't let PB-1 saturate against an unresolved naming convention.
4. Then PB-1. Then PB-2/3/5.
5. Stop. Wait for user re-litigation cue before R1.

DO NOT begin plan-authoring (no `DWF_INSTALLATION_PHASE_MAP.md` drafting) until user says "proceed" after design saturation.

═══════════════════════════════════════════════════════════════════════
*End of FUTURE_CHAT_PROMPT.md*
