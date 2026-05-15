# Phase 10 — Next-Chat Design-Refinement Handoff Prompt

> Authored 2026-05-15 at the close of the Phase 09 ship + CI-green
> sequence. Paste the **PROMPT BODY** section below into a fresh Claude
> chat (in the MindsOS project) when ready to refine the Phase 10 row.
>
> **Design philosophy of this prompt:** navigation guide, not a content
> dump. The next chat reads the files listed below to recover scope,
> picks, and precedent. If you find yourself wanting a fact that isn't
> in this prompt, the answer is in one of the listed files.

---

## PROMPT BODY (copy from here)

Project: MindsOS (folder `halvim_mindsos/` under `Layered Intelligence`).

Your role: refine the **Phase 10 row** in `confirmation_docs/PHASE_MAP.md` §5. The row is currently a 7-line stub at lines 2983-2989. Phase 10 ships **L1 Snapshot + soft-delete + RemovalImpact** per ADR-0027 (snapshot), ADR-0028 (in-process snapshot only), ADR-0133 (soft-delete substrate), and ADR-0135 (RemovalImpact return on cascade-bearing removes).

Refine this into a full Phase NN row per `PHASE_MAP.md` §2 schema (Status / Branch / Tag / Depends / Layer / Net-new / Features / Locked decisions / Modules touched / Persistence layout impact / Automated tests / Confirmation command / Pass criterion / Risks / Rollback hazards / Doc sections / Breaking changes / Final amendments). Use the Phase 09 row (`PHASE_MAP.md` §5 lines 2716-2982) as the structural template — most recent + most complete. Phase 08 row (lines 2447-2715) for secondary precedent.

Your output is **3 artifacts**:

1. Expanded Phase 10 row text replacing the stub at `PHASE_MAP.md` §5 lines 2983+.
2. Full design log at `confirmation_docs/PHASE_10_DESIGN_LOG.md` (mirror Phase 09 structure: Step 0 audit + architectural distinction + M-picks + numbered pushback rounds + lock table + cross-chat dependencies).
3. Implementation-chat handoff prompt at `confirmation_docs/PHASE_10_NEXT_CHAT_PROMPT.md`.

Do NOT write any code. Design refinement only.

### What Phase 10 must address (load-bearing inheritance from Phase 09)

Phase 09 deferred work that Phase 10 owns. Read Phase 09's implemented memory + design log to understand the specific deferrals. The high-level inheritance points:

- **`XRef.target_stale: bool` + `deprecated_at: Optional[datetime]` setters.** Phase 09 P53 dropped both fields from the dataclass; Phase 10 ships them ALONGSIDE the soft-delete substrate (don't ship inert again). Phase 09 ADR-0128 §Revisions amendment 3 documents the deferral.
- **Reverse-dangling XRef cleanup on Metagraph removal.** Phase 09 RPB-3 locked forward-cascade only via `:XREF_OF`; XRefs whose `target_metagraph_id = m.id` (pointing INTO the removed metagraph) become dangling. Phase 10 ships the cleanup (sets `target_stale = True`).
- **Snapshot mechanics for the M3 forward-compat slots.** Phase 09 didn't surface snapshot interaction with `_xrefs_dirty` / `_persist_client` transient state. Phase 10 design must address whether `MetagraphSnapshot.of(mg)` deep-copies the dirty set + `mg.xrefs` dict + inverse indexes (yes — per ADR-0027 + ADR-0130 §Tradeoffs note).
- **`load --metagraph M` summary line growth.** Phase 09 P52 replaced the 9-line list with a structured `Dependent state:` key=value line that grows additively. Phase 10 likely adds new buckets (snapshots + RemovalImpact previews?). Tests assert by KEY not position; preserve the additive-growth contract.

### Mandatory reads (in this order; do NOT re-read older confirmation docs unless debugging a regression)

The complete read list is in the memory files + the ADRs listed below. Read in parallel where possible. **Read the Phase 09 implemented memory + the Phase 10 row stub first** — the rest is precedent and substrate context.

1. **`spaces/<id>/memory/project_mindsos_phase_09_implemented.md`** — what Phase 09 shipped + what it deferred to Phase 10. Read first.
2. **`confirmation_docs/PHASE_MAP.md` §5 Phase 10 row stub** (lines 2983-2989) — the input to refine.
3. **`confirmation_docs/PHASE_MAP.md` §1** — settled cross-cutting decisions; per-phase workflow; supersession policy.
4. **`confirmation_docs/PHASE_MAP.md` §5 Phase 09 row** (lines 2716-2982) — full schema template + Phase 09 inheritance source.
5. **`confirmation_docs/PHASE_MAP.md` §5 Phase 08 row** (lines 2447-2715) — secondary template (substrate + observer pattern).
6. **`confirmation_docs/PHASE_09_CONFIRMED.md` `tester_notes` + Hotfix ledger** — most recent tester confirmation; manual-exploration patterns; hotfix audit classes that Phase 10 inherits (B-09-T2 FalkorDB grouping; B-09-T3+T6+T7 phase-baseline literals; B-09-T4 serializer/deserializer symmetry).
7. **`confirmation_docs/PHASE_08_CONFIRMED.md` `tester_notes`** — two-prior context per §0 read rule.
8. **`docs/decisions/adr/0027-metagraph-snapshot.md`** — snapshot semantics. Status check: Proposed/Accepted? Phase 10 may need to flip.
9. **`docs/decisions/adr/0028-snapshot-in-process-only.md`** — explicit non-persistence constraint.
10. **`docs/decisions/adr/0133-soft-delete-via-deprecated-at.md`** — soft-delete substrate. Read for `target_stale` + `deprecated_at` shape that Phase 09 deferred.
11. **`docs/decisions/adr/0135-removal-impact-return-shape.md`** — RemovalImpact dataclass + cascade-bearing remove APIs.
12. **`docs/decisions/adr/0129-tombstone-rows-for-soft-delete.md`** — `:Tombstone` row pattern (Phase 07 already ships per-(graph, element) tombstones via `build_create_tombstone`).
13. **`docs/decisions/adr/0130-property-bag-on-metagraph-graph.md`** — Accepted in Phase 09 (M7); §Tradeoffs notes snapshot must deep-copy properties.
14. **`docs/decisions/adr/0128-hybrid-xref-cross-metagraph-refs.md`** — Phase 09 stays Proposed (P50). §Revisions amendment 3 documents `target_stale` + `deprecated_at` deferral. Phase 10 closes the deferral.
15. **`docs/decisions/adr/0118-per-user-transactional-promotion.md`** — auto-upgrade contract. Snapshot + RemovalImpact may need to interact with promotion lock.

### v3 baseline source files (slim-port source material, NOT runtime code)

Locate equivalents at `/Layered Intelligence/mindsos_core/` before locking the row. Likely candidates:

16. **`/Layered Intelligence/mindsos_core/models/snapshot.py`** (if exists) — `MetagraphSnapshot` dataclass + `.of(mg)` + `.restore_into(mg)` shape.
17. **`/Layered Intelligence/mindsos_core/models/removal_impact.py`** (if exists) — `RemovalImpact` dataclass shape.
18. **v3 XRef.py target_stale + deprecated_at field declarations** (covered by Phase 09 design log already; cross-reference for the Phase 10 setter contract).
19. **`/Layered Intelligence/mindsos_core/models/metagraph.py::remove_graph(force=True)`** (if v3 has `force` kwarg) — RemovalImpact return shape + cascade-vs-refuse behavior.

### Mandatory memory consultations (your auto-memory directory; read in this order)

1. **`project_mindsos_phase_09_implemented.md`** — primary inheritance source.
2. **`project_mindsos_phase_08_implemented.md`** — Phase 08 substrate (loader + observer pattern).
3. **`project_mindsos_phase_07_implemented.md`** — Phase 07 substrate (Repository + WAL + Tombstones already shipped per P69 A).
4. **`project_mindsos_l1_redesign.md`** — 11+6 redesign locks; M9+N1 soft-delete via `deprecated_at`/`disputed_at`; M10 `RemovalImpact`. **The canonical Phase 10 design source.**
5. **`reference_mindsos_four_edge_primitives.md`** — primitive distinction (4 + XRef = 5).
6. **`reference_mindsos_layer_handoffs.md`** — per-layer handoff path index.
7. **`feedback_falkordb_compound_index_grouping.md`** — Phase 09 B-09-T2; ANY new diagnose / parity check must use distinct (kind, label) pair count.
8. **`feedback_phase_baseline_literal_audit.md`** — Phase 09 B-09-T3+T6+T7 audit class. Step 0 must grep ALL `tests/` for literal phase strings, summary shape literals, and index counts the new phase changes.
9. **`feedback_state_file_serializer_deserializer_symmetry.md`** — Phase 09 B-09-T4 audit class. State-file bumps adding new fields MUST pair serializer + deserializer edits in the recommended-implementation list.
10. **`feedback_state_version_audit_scope.md`** — state-file version literals across ALL `tests/` (Phase 10 likely bumps metagraph state-file v=4 → v=5 for `xrefs[].target_stale` + `xrefs[].deprecated_at` + soft-delete fields on other primitives).
11. **`feedback_falkordb_index_ddl_quirks.md`** — Phase 07 substrate (DDL syntax + grouping).
12. **`feedback_release_workflow_ordering.md`** — squash-merge before tagging.
13. **`feedback_confirm_phase_timeout.md`** — pre-build before confirm-phase; 900s timeout.
14. **`feedback_state_dir_env_var.md`** — recipe-authoring rule (`~/.mindsos/`, never `$MINDSOS_STATE_DIR`).
15. **`feedback_workflow_bash_octal_trap.md`** — Phase 10 `NN=10` is octal-safe (Phase 08 fix carries).
16. **`feedback_tag_regex_audit.md`** — 6-site checklist; `phase10-*` matches existing regex unchanged.
17. **`feedback_test_budget_unlimited.md`** — uncapped (Phase 08 RPB-7 user override).
18. **`feedback_terse_step_recipes.md`** — execution communication style.
19. **`feedback_docker_compose_invocation.md`** — Phase 02+ entrypoint behavior + `--rm` fs-destroy quirk (Phase 09 surfaced state-file persistence + user-context split).
20. **`feedback_docs_source_of_truth.md`** — Model C hybrid; ADR file edits at project-root, single chunk-N commit.
21. **`feedback_new_top_level_package.md`** — 5-site checklist (Phase 10 likely no new top-level pkg; verify).
22. **`feedback_dockerfile_test_stage_file_reads.md`** — 6-site checklist for new host files tests read.
23. **`user_two_machine_setup.md`** — Mac/Linux split + canonical per-phase workflow (a)-(l).

### Carry-forward locks + out-of-scope items

Pull from the row + design log. Do NOT pull anything in that isn't in the Phase 10 stub's `Features` line + the Phase 09 deferrals enumerated above. Some likely-out-of-scope items:

- **L2 / L3 / L4 / L5 layer work.**
- **Server first-start migration hook** (Phase 18+; ADR-0142 commitment 3).
- **L2 `MetagraphView.follow_ref` read-fallback** (Phase 14; ADR-0142 commitment 2).
- **Cypher schema migration utility** (Phase 11).
- **Cypher integrity scanner extension** (Phase 11).
- **Snapshot persistence to disk** (ADR-0028 — explicitly in-process only).
- **L3 write capacities producing XRefs** (Phase 33+; ADR-0145).

### Communication style

Design chat uses analysis voice (multi-round refinement; numbered pushbacks per round; user signs off each round before moving forward). NOT execution voice. Per project `CLAUDE.md`: skeptical default; concise; no filler; no emojis; no restating user messages. The user will explicitly say "go deep" / "expand" / "analyze thoroughly" if they want long-form output.

### First action

1. Read the Phase 09 implemented memory + Phase 10 row stub + Phase 09 row + relevant ADRs in parallel (the docs/memory list above).
2. Surface a Step 0 pre-design audit: confirm Phase 09 squash-merge on main + tag exists; confirm v3 baseline files for snapshot + RemovalImpact + soft-delete are present at `/Layered Intelligence/mindsos_core/`; confirm ADR statuses; confirm Phase 09 deferred fields (`target_stale` + `deprecated_at`) absence in halvim `mindsos_core/models/xref.py`; identify state-file v=4 → v=5 audit cost (grep ALL `tests/` for `_state_version == 4` literals + `METAGRAPH_STATE_VERSION == 4`).
3. Wait for user sign-off on Step 0 audit.
4. Then propose Round 1 meta-plan (M-picks for Phase 10) with numbered options + your recommendation per the Phase 09 design log structure.

### Memory updates at chat-end (after design locks)

Create `project_mindsos_phase_10_design.md` mirroring `project_mindsos_phase_09_design.md`. Update MEMORY.md index entry. Write `confirmation_docs/PHASE_10_NEXT_CHAT_PROMPT.md` (the implementation-chat handoff). The implementation chat then takes over per the standard cycle.

## END PROMPT BODY (copy ends here)
