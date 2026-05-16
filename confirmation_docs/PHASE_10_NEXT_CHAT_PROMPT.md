# Phase 10 — Implementation-Chat Handoff Prompt

> Authored 2026-05-15 at close of Phase 10 row-refinement chat. Paste the **PROMPT BODY** below into a fresh Claude chat (MindsOS project) when ready to ship Phase 10. The prompt is a **navigation guide**, not a content dump — every fact about scope, locks, and modules lives in files; the prompt routes you there.

---

## PROMPT BODY (copy from here)

Project: MindsOS (folder `halvim_mindsos/` under `Layered Intelligence`).

Your role: **implement Phase 10** per the locked design. Phase 10 ships **L1 Snapshot + soft-delete substrate + RemovalImpact + XRef setters**.

Design is fully locked. 64 active picks across 6 pre-design pushback rounds + Step 0 audit + 4 design rounds (M / PB / RPB / RR). Branch: **`phase-10`** off Phase 09 squash-merge commit `abc659f` (tag `phase-09-confirmed`).

### Read these files in this order before doing anything else

The scope, ADR matrix, modules touched, test plan, breaking changes, risks, rollback hazards, doc surfaces, and confirmation command **all live in files**. Do not assume — read.

1. `halvim_mindsos/confirmation_docs/PHASE_MAP.md` §5 **Phase 10 row** — full schema-conformant row. Read first; everything else is supporting context.
2. `halvim_mindsos/confirmation_docs/PHASE_10_DESIGN_LOG.md` — design path; 6 pushback rounds; Step 0 audit results; consolidated lock table; cross-chat dependencies (forward and backward).
3. `spaces/<id>/memory/project_mindsos_phase_10_design.md` — design-chat memory entry; concise summary.
4. `halvim_mindsos/confirmation_docs/PHASE_10_AUDIT_NOTE.md` + `halvim_mindsos/confirmation_docs/SOFT_DELETE_AUDIT_NOTE.md` — pre-existing audits that scope Phase 10 (SD1-SD5 defects in v3 baseline to address at port).
5. `halvim_mindsos/confirmation_docs/PHASE_MAP.md` §5 **Phase 09 row** (lines 2716-2982) — structural template + substrate inheritance source.
6. `spaces/<id>/memory/project_mindsos_phase_09_implemented.md` — most recent precedent; P50-P66 pushbacks; B-09-T1..T7 hotfixes; per-Client WAL replayer substrate.
7. `halvim_mindsos/confirmation_docs/PHASE_09_CONFIRMED.md` `tester_notes` + hotfix ledger.
8. `halvim_mindsos/confirmation_docs/PHASE_08_CONFIRMED.md` `tester_notes` (two-prior context per §0 read rule).

### ADRs in scope (read the ones whose status you need to verify or amend)

Pointers — read directly when implementing the relevant feature surface.

- ADR-0027 (snapshot mutate-in-place; Accepted; gets §Revisions amendment-1).
- ADR-0028 (snapshot non-serialisable; Accepted; unchanged).
- ADR-0129 (snapshot scope narrowed to release-ship; Accepted; ship docstring + module-level deprecation note only).
- ADR-0130 (property bag; Metagraph-side accepted Phase 09; Graph-side flips Accepted in Phase 10 inline).
- ADR-0133 (soft-delete substrate; stays Proposed; gets §Revisions amendments-1+2; flips Phase 11 with filter pass).
- ADR-0135 (RemovalImpact; flips Proposed → Accepted; gets §Revisions amendments-1+2+3).
- ADR-0128 (XRef hybrid; stays Proposed until Phase 14; gets §Revisions amendment-3 closing Phase 09's RPB-3 deferral).
- ADR-0148 (cross-reference: `CompositionalImmutableError` class owner per D1-rev).

### v3 baseline source files (slim-port material; CONFIRMED present at Step 0)

- `/Layered Intelligence/mindsos_core/metagraph_snapshot.py` (271 LoC) — `MetagraphSnapshot` + `_GraphSnap` + `.of(mg)` + `.restore_into(mg)`.
- `/Layered Intelligence/mindsos_core/models/metagraph.py` — `RemovalImpact` dataclass + `remove_graph(*, cascade=True, force=False)` + `_compute_removal_impact()` helper.
- `/Layered Intelligence/mindsos_core/models/graph.py:206+` — Graph quartet setters for Edge (slim-port verbatim; add HyperEdge quartet per SD1 fix).
- `/Layered Intelligence/mindsos_core/models/metagraph.py:420+` — v3 Metagraph single-overload `deprecate_metaedge(*, at=None)`. **REJECTED at port**; adopt quartet pattern per Phase 10 M6 + SD2 fix.

### Mandatory memory consultations (do not skip)

All feedback memories listed in `MEMORY.md` apply. Especially load-bearing for Phase 10:

- `project_mindsos_phase_10_design.md` — primary inheritance.
- `project_mindsos_phase_09_implemented.md` — substrate (XRef, WAL, state-file v=4, observer).
- `project_mindsos_l1_redesign.md` — canonical Phase 10 design source.
- `feedback_state_file_serializer_deserializer_symmetry.md` — pair `_to_state` + `_state_to_` edits for v=4 → v=5.
- `feedback_phase_baseline_literal_audit.md` — Step 0 grep ALL `tests/` for literals.
- `feedback_state_version_audit_scope.md` — grep ALL `tests/` for `METAGRAPH_STATE_VERSION == 4` + `GRAPH_STATE_VERSION == 4`.
- `feedback_falkordb_compound_index_grouping.md` + `feedback_falkordb_index_ddl_quirks.md` — FalkorDB substrate.
- `feedback_confirm_phase_timeout.md` — 900s + pre-build recipe.
- `feedback_release_workflow_ordering.md` — squash-merge before tagging.
- `feedback_state_dir_env_var.md` — `~/.mindsos/`, never `$MINDSOS_STATE_DIR`.
- `feedback_terse_step_recipes.md` — execution voice during implementation.

### First actions (in order)

1. **Branch + baseline verification.** Check out `phase-10` off `abc659f`. Confirm `phase-09-confirmed` tag is reachable.
2. **Step 0 in-chat verification.** Probes 1-6 + 11 were pre-confirmed at row-design time and recorded in `PHASE_10_DESIGN_LOG.md` §"Step 0 audit". Run probes 7-10 in-chat:
   - Probe 7: schema constraint grep for `deprecated_at` / `disputed_at` keys across `halvim_mindsos/tests/` (port-time reserved-key collision; expect zero).
   - Probe 8: WAL replayer wrapper signature audit (Phase 09 P51/P61/P66 substrate accepts +8 registrations).
   - Probe 9: `_persist_client` access pattern audit (Phase 09 transient field stable for Phase 10 setters).
   - Probe 10: `CompositionalImmutableError` class usage audit (expect class survives at `exceptions.py:120`).
3. **`mg.remove_graph(` callsite audit.** Row-design pass identified 19 files containing the literal. Hard signature change per L1 pick. **If callsite count > 20, surface to user before proceeding** — Round-2 L3 (alias-method fallback) reopens.
4. **Surface ~25-step implementation order.** Suggested ordering is sketched in the design log; refine per your read of the row. Get user sign-off before coding.
5. **Pre-impl review pushbacks.** Phase 09 surfaced 13 (P50-P66) before any code landed. Phase 10 likely surfaces similar count. Number them P67+ per Phase 09 precedent. User signs off in batches.
6. **Implement.** Execution voice: every step = `command` + `expected outcome`. Pushbacks at end of round only. Per `feedback_terse_step_recipes.md`.
7. **Tester confirmation in same chat** per Phase 09 cadence. Pre-build: `docker compose --profile test build mindsos-test` BEFORE `mindsos confirm-phase`. Timeout 900s.
8. **Hotfix ledger.** Number any in-flight fixes B-10-T*. Phase 09 had 7. File new feedback memories at chat-end for any new audit classes.
9. **PR + squash-merge + tag + Release CI.** Standard cycle per `feedback_release_workflow_ordering.md`. Tag = `phase-10-confirmed`.
10. **Memory updates at chat-end.** Create `project_mindsos_phase_10_implemented.md` mirroring Phase 09's. Update `MEMORY.md` index entry (≤150 chars).

### Carry-forward locks (out of scope; DO NOT pull in)

Listed in `PHASE_10_DESIGN_LOG.md` §"Carry-forward open items". Summary: L2/L3/L4/L5 work; iterator/loader filter pass (Phase 11); soft-delete CLI (Phase 11); ADR-0129 CI lint rule (Phase 18+); Server first-start auto-trigger for `mark_xref_stale` (Phase 18+); ADR-0142 commitments 2+3; snapshot persistence to disk; L3 capacities producing XRefs.

### Communication style

Per project `CLAUDE.md` + `feedback_terse_step_recipes.md`:
- Skeptical default; concise; no filler; no emojis; no restating user messages.
- Execution voice during implementation: `command` + `expected outcome`.
- Analysis voice only when surfacing pushbacks or when user explicitly says "go deep" / "expand" / "analyze thoroughly".

### Pass criterion + risks + rollback hazards

All enumerated in `PHASE_MAP.md` §5 Phase 10 row (sections "Pass criterion", "Risks / known issues to watch", "Rollback hazards"). Read directly.

## END PROMPT BODY (copy ends here)
