# Phase 09 — Next-Chat Design-Refinement Handoff Prompt

> Authored 2026-05-14 at the close of the Phase 08 ship + CI-green
> sequence. Paste the **PROMPT BODY** section below into a fresh Claude
> chat (in the MindsOS project) when ready to refine the Phase 09 row.
>
> **Design philosophy of this prompt:** navigation guide, not a content
> dump. The next chat reads the files listed below to recover scope,
> picks, and precedent. If you find yourself wanting a fact that isn't
> in this prompt, the answer is in one of the listed files.

---

## PROMPT BODY (copy from here)

Project: MindsOS (folder `halvim_mindsos/` under `Layered Intelligence`).

Your role: refine the **Phase 09 row** in `confirmation_docs/PHASE_MAP.md` §5 (currently a 7-line stub at lines 2716-2722). Phase 09 ships **L1 XRef (cross-metagraph refs)** per ADR-0128 (hybrid XRef) + ADR-0142 (XRef cutover for `ref:global` properties). The row currently reads:

```
### Phase 09 — L1 XRef (cross-metagraph refs)

  **Deps:** 07, 08. **Layer:** L1. **Net-new?** Mostly no — XRef primitive shipped; **but** ADR-0142 (XRef cutover for `ref:global`) requires migration of legacy `ref:global_*` properties — that part is **NEW CODE** if any legacy refs exist in fixtures.
  **Features:** XRef CRUD; one-shot migration from legacy `ref:` properties.
  **Tests:** XRef round-trip; migration preserves role; legacy properties not duplicated.
  **Risks:** migration path must be reversible or audited.
  **Docs:** `docs/concepts/references.md`, ADRs 0128/0142.
```

Refine this into a full Phase NN row schema per `PHASE_MAP.md` §2 (Status / Branch / Tag / Depends / Layer / Net-new / Features / Modules touched / Automated tests / Confirmation command / Pass criterion / Risks / Rollback hazards / Doc sections / Breaking changes / Final amendments). Use the Phase 08 row (`PHASE_MAP.md` §5 lines 2447-2715) as the structural template — it's the most recent and most complete row.

Your output is **3 artifacts**:

1. The expanded Phase 09 row text written into `PHASE_MAP.md` §5 (in place of the stub).
2. A full design log at `confirmation_docs/PHASE_09_DESIGN_LOG.md` (mirror of `PHASE_08_DESIGN_LOG.md` structure: Step 0 audit + M-picks + numbered pushback rounds + lock table + cross-chat dependencies).
3. An implementation-chat handoff prompt at `confirmation_docs/PHASE_09_NEXT_CHAT_PROMPT.md` (overwrite this file once the design locks).

Do NOT write any code. Design refinement only.

---

### Mandatory reads (in this order; in parallel where possible)

The Phase 08 design + ship docs are the most-load-bearing precedent — read those first, then the row stubs + ADRs + memory files.

**Phase 08 ship artifacts (full context for the substrate you inherit):**

1. **`confirmation_docs/PHASE_08_DESIGN_LOG.md`** — 4 design rounds (74 picks). Read this first to learn the row-refinement style + see how Phase 08 framed M-picks vs PB / RPB / RR / R4 rounds + final lock table.
2. **`confirmation_docs/PHASE_MAP.md` §5 Phase 08 row** (lines 2447-2715) — the structural template for your Phase 09 row.
3. **`confirmation_docs/PHASE_08_IMPLEMENTATION_LOG.md`** — what actually shipped + 9 hotfixes + 2 impl-time pushbacks (P60 + P61 A). Identifies the load-bearing classes/methods Phase 09 builds against.
4. **`confirmation_docs/PHASE_08_CONFIRMED.md` `tester_notes`** — most recent tester confirmation; 1374 + 2 skipped baseline; manual CLI exploration outcomes; substrate observations.

**Phase 09 scope inputs:**

5. **`confirmation_docs/PHASE_MAP.md` §5 Phase 09 row stub** (lines 2716-2722) — what's there now.
6. **`/Layered Intelligence/docs/decisions/adr/0128-hybrid-xref-cross-metagraph-refs.md`** — ADR-0128 (project-root per Model C hybrid; NOT in halvim_mindsos). Hybrid XRef design: first-class `XRef` for cross-metagraph (Local → Global; pivot's auto-upgrade runs here); `ref:<role>` strings for intra-metagraph.
7. **`/Layered Intelligence/docs/decisions/adr/0142-xref-cutover-for-ref-global.md`** — ADR-0142. Cutover migration from legacy `ref:global_*` properties → first-class `XRef` rows.

**v3 baseline source files (slim-port source material; project-root):**

8. **`/Layered Intelligence/mindsos_core/models/xref.py`** — XRef dataclass source.
9. **`/Layered Intelligence/mindsos_core/persistence/xref_repository.py`** — XRef persist source.
10. **`/Layered Intelligence/mindsos_core/persistence/xref_migration.py`** — `ref:global_*` cutover migration source (ADR-0142).
11. **`/Layered Intelligence/mindsos_core/reconstruction/xref_loader.py`** — XRefLoader source. Per Phase 08 RR-10 A this becomes an `after_load` observer subscriber.

**Phase 07 ship artifacts (substrate underpinning Phase 09):**

12. **`confirmation_docs/PHASE_MAP.md` §5 Phase 07 row** — Phase 07 row precedent (esp. ADR file edits + Phase 07 chunk-7 Model C precedent).
13. **`confirmation_docs/PHASE_07_CONFIRMED.md`** — Phase 07 substrate (FalkorDB Client + repositories + WAL + integrity).

**PHASE_MAP cross-cutting + schema:**

14. **`confirmation_docs/PHASE_MAP.md` §1** — settled cross-cutting decisions (per-phase workflow, supersession, doctor checks, etc.).
15. **`confirmation_docs/PHASE_MAP.md` §2** — per-phase row schema (Status / Branch / ... / Final amendments). Use this as the structural template.
16. **`confirmation_docs/PHASE_MAP.md` §7 Open questions** — surface any Q items that touch XRef or the `ref:global` cutover.

---

### Mandatory memory consultations (your auto-memory directory; read in this order)

1. **`project_mindsos_phase_08_implemented.md`** — full Phase 08 ship summary + what Phase 09 inherits (observer pattern; persist precedents; CLI surface conventions). Includes the **key learnings for forward phases** section — Phase 09 should consume those directly.
2. **`project_mindsos_phase_07_implemented.md`** — Phase 07 substrate (Client / repositories / WAL / integrity / 14-index bootstrap / `mindsos persistence` 5-verb CLI subapp). Phase 09 inherits all of this.
3. **`project_mindsos_l1_redesign.md`** — 11+6 L1 redesign locks; W1-W6 mitigation index; ADR status across the cascade. **M2 Hybrid XRef** is the relevant lock for Phase 09: first-class `XRef` for cross-metagraph (Local → Global); `ref:<role>` strings for intra-metagraph.
4. **`reference_mindsos_four_edge_primitives.md`** — semantic distinction between the 4 edge primitives. XRef is a **5th primitive** (cross-metagraph; not in the 4-primitive table). Mind the distinction in any vocab decisions.
5. **`reference_mindsos_layer_handoffs.md`** — per-layer handoff paths. Pre-pivot HANDOFF.md predates Phase 08; treat as historical for current cross-layer context.
6. **`feedback_workflow_bash_octal_trap.md`** (B-08-T9) — Phase 09's `printf '%02d'` sites in release.yml are now safe (fixed in Phase 08). Phase 09's NN=09 would have hit the SAME trap; the Phase 08 fix is permanent.
7. **`feedback_tag_regex_audit.md`** — 5-site (now 6-site per B-08-T9) checklist for tag-regex changes. Phase 09 image tag `phase09-*` matches the existing regex; no extension needed.
8. **`feedback_new_top_level_package.md`** — 5-site checklist. Phase 09 likely does NOT add a new top-level package (`mindsos_core.models.xref` + `mindsos_core.persistence.xref_*` + `mindsos_core.reconstruction.xref_loader` are submodules of existing packages). Confirm at Step 0.
9. **`feedback_confirm_phase_timeout.md`** — pre-build before `confirm-phase`. Inherited; Phase 09 retains the 900s timeout from Phase 07.
10. **`feedback_state_dir_env_var.md`** — recipe-authoring rule (`~/.mindsos/`, never `$MINDSOS_STATE_DIR`). Inherited.
11. **`feedback_release_workflow_ordering.md`** — squash-merge BEFORE tagging from main. Inherited.
12. **`feedback_state_version_audit_scope.md`** — grep ALL `tests/` for `_state_version` literals if Phase 09 bumps any state file. **Phase 09 likely DOES bump metagraph state-file v=3 → v=4** (adds `xrefs[]` array) — surface this in M-picks.
13. **`feedback_test_budget_unlimited.md`** — test budget rule. Inherited unconditionally.
14. **`feedback_terse_step_recipes.md`** — execution voice (impl chat only; design chat uses analysis voice).
15. **`feedback_docker_compose_invocation.md`** — Phase 02+ entrypoint form; `--rm` destroys container fs. Inherited.
16. **`feedback_docs_source_of_truth.md`** — Model C hybrid; ADRs live at project-root, NOT in halvim_mindsos. Phase 09's ADR file edits (0128 flip + 0142 flip if implemented) land at project-root per Phase 07 chunk-7 + Phase 08 ADR-0124 precedent.
17. **`feedback_cli_config_manifest_fallback.md`** — env-then-manifest-then-default. Inherited.
18. **`feedback_dockerfile_test_stage_file_reads.md`** — Dockerfile test stage COPY checklist (6th site of `feedback_new_top_level_package.md`).
19. **`user_two_machine_setup.md`** — Mac/Linux split + per-phase workflow (a)-(l).
20. **`project_mindsos_phase_08_design.md`** — Phase 08 design lock state. Phase 09 inherits observer pattern, persist precedents, dispatcher isolation choice.

---

### Round-0 Step-0 audit checklist (run BEFORE refining the row)

Per Phase 08 Step 0 audit precedent. Each item: TRUE / FALSE / ANOMALY with file:line evidence.

1. **Phase 08 squash-merge on main + tag exists.** `git log origin/main --oneline -3` includes `d5b6e98 Phase 08 — L1 Reconstruction ... (#15)`; tag `phase-08-confirmed` present.
2. **v3 XRef sources exist at project-root.** All 4 files: `models/xref.py`, `persistence/xref_repository.py`, `persistence/xref_migration.py`, `reconstruction/xref_loader.py`. Report LoC for each.
3. **halvim_mindsos has NO xref code yet.** `find halvim_mindsos -name '*xref*' -type f` returns 0 results.
4. **ADRs 0128 + 0142 exist at project-root.** Frontmatter `status`. (Phase 09 design picks include whether to flip Accepted inline per M3 A precedent.)
5. **`mindsos_core/models/metagraph.py` has `register_after_load_observer`** (Phase 08 PB-4 A) — Phase 09's XRefLoader subscribes via this.
6. **`mindsos_core/_observers.py::_dispatch_after_load`** has per-observer exception isolation (RR-9 A) — Phase 09's XRefLoader inherits the isolation.
7. **`mindsos_instances/registry.py::attach_registry`** subscribes the after-load observer for InstanceLoader (PB-4 A) — Phase 09's XRefLoader follows the same subscription idiom (different attach helper, or extension of attach_registry, or new XRef-side helper).
8. **`mindsos_cli/commands/persistence.py`** `sync --metagraph M --replace` already includes XRef in the dependent-state check (Phase 08 RPB-4 C) — confirm the XRef bucket query handles the `:XRef` label that Phase 09 will introduce.
9. **State-file versions.** graph=4 / metagraph=3 / metagraph_schema=3 / schema=2. Phase 09 likely bumps metagraph v=3 → v=4 to add `xrefs[]` array; per `feedback_state_version_audit_scope.md` grep ALL `tests/` for hard-coded `_state_version` literals.
10. **Manifest phase.** Currently `[mindsos] phase = "08"`. Phase 09 bumps to "09".
11. **Pre-existing `ref:global_*` data in fixtures.** Grep `tests/` + `~/.mindsos/` state files for `ref:global` literals. If zero, ADR-0142 cutover migration is no-op-on-current-fixtures (still ships the code for future legacy data).

Report Step 0 findings as a brief audit summary; wait for user sign-off before opening Round 1.

---

### Suggested round structure (mirror Phase 08)

Phase 08 closed at 4 rounds (target was 3; 1 extra surfaced edge cases). Aim for **3 rounds** of pushbacks; one extra round if edge cases surface late. Per round:

- **Round 1 (PB-N)** — strategic picks. Where does XRef live (Core vs sibling)? Per-metagraph XRefRegistry vs `mg.xrefs` dict? CLI surface: new `mindsos xref` subapp vs extension of `mindsos persistence`? ADR-0128 / 0142 flip Proposed → Accepted or stay Proposed? State-file bump v=3 → v=4 or carry as Phase 11 cypher migration?
- **Round 2 (RPB-N)** — cross-cutting concerns. Migration safety (RPB-4 C-style refusal on conflicting data); WAL integration (XRef writes use `WriteAheadLog.entry()`?); observer ordering (after instances per RR-10 A vs new step in MetagraphLoader); identity-preservation under refresh + XRef rehydration.
- **Round 3 (RR-N)** — implementation details. Per-XRef OCC predicate; CLI verbs (`mindsos xref add` / `remove` / `migrate-legacy` / `inspect`); Cypher representation (typed rel vs labeled-node); test scaffolding (extend `metagraph_equality.py` for xrefs; new fixture for legacy `ref:global_*` data).
- **Round 4 (R4-N) if needed** — edge cases + mechanical bumps (manifest, compose tags, doc footprint, sentinel paths).

Per Phase 08 user override 2026-05-13 (RPB-7), **test budget is uncapped**. Do not project a cap.

---

### Carry-forward locks Phase 09 inherits unconditionally

Read them from the listed files; do NOT re-litigate:

- ADR-0030 / 0121 / 0122 / 0123 / 0124 / 0126 / 0127 / 0130 — all Accepted (Phase 07/08).
- ADR-0125 STAYS Proposed (server-side; Phase 18+).
- ADR-0132 (instancing sibling package) — preserved.
- Model C docs hybrid (`feedback_docs_source_of_truth.md`).
- 3-package version-string parity (Phase 06 P62 A).
- Confirm-phase 900s timeout (Phase 07 M12).
- Tag regex permits `phase09-{prod,test}` (Phase 05a unchanged).
- `feedback_workflow_bash_octal_trap.md` — release.yml is now base-10-safe (B-08-T9 fix).
- 6-site Dockerfile + sentinel + pyproject + doctor + host-install audit when adding any new module a test reads (Phase 06 + 07 + 08 cumulative checklist).
- `tests/phase_NN/conftest.py` re-export pattern for `falkor_client` (B-08-T2 precedent — bake into Phase 09 scaffolding).

---

### Explicitly OUT of Phase 09 scope (defer to later phases)

These are surfaced to keep Phase 09 focused; surface as "Out of scope" in the row:

- Snapshot + soft-delete + RemovalImpact (Phase 10 per current PHASE_MAP).
- `persistence reset --force` (Phase 11).
- Per-role mutation-flag tracking + `RefreshUnsafeError` enforcement (Phase 08 PB-5 B class-only carry-forward).
- Graph `.properties` writer (Phase 07 P9 C deferral; carry-forward).
- Cypher schema migration utility (Phase 11).
- L2 / L3 / L4 / L5 layer work.
- Server-side anything (Phase 18+).

---

### Communication style

Design-refinement chat uses **analysis voice**: pros/cons, alternatives, tradeoffs, evenhanded options. Skeptical default per project `CLAUDE.md`. Concise; no filler; no emojis; no restating user messages.

**NOT** execution voice (terse step recipes) — that's for the Phase 09 implementation chat per `feedback_terse_step_recipes.md`.

When proposing M-picks or pushback options: name 2-4 alternatives + your pick + one-line rationale. User signs off pick-by-pick or instructs differently.

---

### First action

1. Read the 16 docs + 20 memory files above (in parallel where possible; design log + Phase 08 row + ADRs 0128/0142 first).
2. Run the Round-0 Step 0 audit per the checklist above.
3. Report Step 0 findings as a brief audit summary (file + line citations + anomalies). Do NOT propose row content yet.
4. Wait for user sign-off before opening Round 1 (M-picks).

---

### Cross-chat output targets

When the design locks (whichever round closes), write:

- **`confirmation_docs/PHASE_09_DESIGN_LOG.md`** — full pick log (Step 0 + M-picks + each round's PB / RPB / RR / R4 if needed + lock table + cross-chat dependencies). Mirror Phase 08 design log structure.
- **`confirmation_docs/PHASE_MAP.md` §5 Phase 09 row** — replace the 7-line stub at lines 2716-2722 with the full row per `PHASE_MAP.md` §2 schema. Use Phase 08 row (lines 2447-2715) as the template.
- **`confirmation_docs/PHASE_09_NEXT_CHAT_PROMPT.md`** — overwrite this file with the implementation-chat handoff (mirror the Phase 08 implementation-handoff prompt structure: 16 mandatory doc reads + 20 memory consultations + Step 0 audit + suggested 28-step implementation order + likely hotfix patterns + out-of-scope list).

## END PROMPT BODY (copy ends here)

---

## Notes for Henrique (NOT part of the prompt)

- Save this file before opening the new chat. Memory files load automatically when the new chat starts in the same project workspace.
- Reload cost in the next chat is 16 doc reads + 20 memory file reads. Bounded; expected to fit comfortably.
- The Phase 08 ship pattern (design chat → implementation chat → tester confirm → squash-merge + tag) is the reference for Phase 09. Each phase = 2 chats minimum (design + implementation).
- Phase 09 row currently is a 7-line stub. The next chat's job is to expand it to a full row (~250 LoC like Phase 08).
- ADR-0142 (XRef cutover) is the genuinely-NEW-code portion of Phase 09. ADR-0128 (XRef primitive) is mostly a slim port. Both ADRs are Proposed at project-root; whether to flip Accepted inline (M3 A precedent) is a Round 1 design pick.
