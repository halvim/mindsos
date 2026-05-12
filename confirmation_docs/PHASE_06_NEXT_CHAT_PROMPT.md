# Phase 06 Implementation — Next-Chat Handoff Prompt

> Authored 2026-05-11 in the 06 row-refinement chat. Paste the **PROMPT BODY** below into a fresh Claude chat (MindsOS project) when ready to implement Phase 06.
>
> **Design philosophy of this prompt:** navigation guide, not content dump. Scope, locks, ADR amendments, override allow-list, cascade chain, JSON shapes, future-work entries — none of that is repeated here. The implementation chat reads the files listed below to recover that context.

---

## PROMPT BODY (copy from here)

Project: MindsOS (folder `halvim_mindsos/` under `Layered Intelligence`).

Your role: implement Phase 06 on a `phase-06` branch off `origin/main`. **Design is fully locked** in the prior chat (2026-05-11, 6 reanalysis rounds, 6 meta-plan picks (M1–M6) + 44 numbered design pushbacks (P1–P44), 2 user overrides at P13 B + P24 B). The full pick log + rationale per pick lives in `confirmation_docs/PHASE_06_DESIGN_LOG.md` — canonical record of what was decided and why.

Do not re-litigate locked decisions. If implementation surfaces a contradiction with the locked row, surface it as a numbered pushback (continuing P45+) before continuing. Bar: "I cannot implement what was locked," not "I'd have picked differently." Round-7 reshape precedent from 05d (which reversed 12 design picks at the start of implementation) is permitted but not required.

CASC-1 cascade: `05a → 05b → 05c → 05d → 06`. 05d SHIPPED 2026-05-08 (tester-confirmed 1013 + 2 skipped in-container; tag `phase-05d-confirmed`). You are unblocked.

**Branch:** `phase-06` off `origin/main` (NEVER off `phase-05d`).
**Tag on confirm:** `phase-06-confirmed`.
**Confirmation doc target:** `confirmation_docs/PHASE_06_CONFIRMED.md`.
**Implementation log target:** `confirmation_docs/PHASE_06_IMPLEMENTATION_LOG.md`.

### What 06 ships

Read the canonical row text. Do not rely on a summary in this prompt; the row is the source of truth:

> **`confirmation_docs/PHASE_MAP.md` §5 Phase 06 row** (look for `### Phase 06 — L1 Instancing (\`mindsos_instances\`) — sibling package with 8 instance subclasses + cascade-observer`)

The row has sub-sections §A–§J. Read all of it. The per-subclass override allow-list table (§B) is load-bearing — implementation enforces it per-subclass.

### Mandatory reads (in this order; do NOT re-read older confirmation docs unless debugging a regression)

  1. **`confirmation_docs/PHASE_06_DESIGN_LOG.md`** — full pick log (M1–M6 + P1–P44) with rationale per pick + 2 user overrides. **Read this first** if you need to understand *why* a particular decision was made.
  2. **`confirmation_docs/PHASE_MAP.md` §5 Phase 06 row** — canonical scope, override allow-list, cascade chain, ADR amendments, CLI surface, risks, future-work. Implementation target.
  3. **`confirmation_docs/PHASE_MAP.md` §1** — settled cross-cutting decisions; per-phase workflow; supersession policy.
  4. **`confirmation_docs/PHASE_MAP.md` §5 Phase 05d row** — most-recent predecessor. 06 inherits unconditionally: ADR-pointer precedent, observer-hook precedent (`register_attach_handler` in 0132 — 06 adds the symmetric `register_remove_observer`), state-version audit scope rule.
  5. **`confirmation_docs/PHASE_MAP.md` §5 Phase 05c row** — two-prior context per §0 read rule.
  6. **`confirmation_docs/PHASE_05d_CONFIRMED.md` `tester_notes`** — most recent tester confirmation; recipe-deviation lessons.
  7. **`confirmation_docs/PHASE_05d_IMPLEMENTATION_LOG.md`** — 05d's round-7 reshape ledger (P31–P44). Tells you how an implementation chat *legitimately* reverses prior locks when surface contradictions emerge. Use as template if you need round 7.

### ADRs to read (read the FILES, not paraphrases)

  - `docs/decisions/adr/0015-instancing-model.md` — instancing concept.
  - `docs/decisions/adr/0019-materialisation-is-lazy.md` — lazy materialisation lock.
  - `docs/decisions/adr/0025-instance-overrides-via-ov-prefix.md` — `ov__` override property prefix (already in `RESERVED_PROPERTY_PREFIXES` from Phase 04; serialization concern is Phase 07).
  - `docs/decisions/adr/0026-composite-overrides-bundle-only.md` — bundle-only rule; no propagation.
  - `docs/decisions/adr/0132-instancing-moved-to-mindsos-instances.md` — **WILL BE MATERIALLY AMENDED in this PR per row §G + P2 A.** Read the current file first; you'll rewrite parts of the Decision section.

### Mandatory memory consultations (your auto-memory directory; read in this order)

  1. **`project_mindsos_phase_06_design.md`** — full lock state for 06 (mirrors PHASE_06_DESIGN_LOG in memory format). Primary reload pack.
  2. **`project_mindsos_phase_05d_implemented.md`** — what shipped in 05d + carry-forward patterns 06 inherits.
  3. **`project_mindsos_l1_redesign.md`** — M7 lock (instancing → `mindsos_instances` sibling); ADR-0132 status.
  4. **`reference_mindsos_layer_handoffs.md`** — per-layer handoff path index.
  5. **`feedback_test_budget_unlimited.md`** — unconditional inheritance.
  6. **`feedback_terse_step_recipes.md`** — execution communication style (NOT design voice; phase execution is terse `command + expected outcome` recipes).
  7. **`feedback_state_dir_env_var.md`** — recipe-authoring rule (`~/.mindsos/`, never `$MINDSOS_STATE_DIR`). **Note:** Phase 06 ships no new state file, but CLI tests still execute in-container — recipes still use `~/.mindsos/`.
  8. **`feedback_release_workflow_ordering.md`** — squash-merge BEFORE tagging; release.yml fails otherwise.
  9. **`feedback_tag_regex_audit.md`** — 5-site checklist (unlikely-triggered in 06, but read).
  10. **`feedback_docker_compose_invocation.md`** — Phase 02+ entrypoint behavior; rebuild image after pulling test-side fixes.
  11. **`feedback_state_version_audit_scope.md`** — **NOT triggered in 06** (P8 B: no state-file bumps). Read anyway as awareness; if a P45+ pushback adds a state-file bump, this audit scope applies.
  12. **`user_two_machine_setup.md`** — Mac/Linux split + canonical per-phase workflow steps (a)-(l).
  13. **`project_mindsos_architecture.md`** — 5-layer overview.

### Sandbox-vs-container test split (per row §Tests)

Phase 06 ships `mindsos_instances` library code + small Core hook + new CLI subapp. Mac sandbox has Python 3.10 + missing FalkorDB; container has 3.12 + FalkorDB.

**Sandbox-safe (run during implementation):**
  - Subclass construction + invariants.
  - SubGraphInstance edge-validity invariants.
  - Override mutation (set/clear/reserved-key rejection).
  - Materialisation per subclass (type mapping, fresh-UUID-per-call, structural fields, user-property merge).
  - Composite mutability + duplicates + cycle detection + cross-metagraph rejection.
  - Cascade observer (in-memory; no FalkorDB).
  - Canonicalize utility.

**Container-only (defer to tester run):**
  - CLI subprocess tests (4 verbs × pass + override + materialise paths).
  - Any test importing FalkorClient (none expected in 06).

Per 05d precedent: sandbox passes ~80% of total tests; tester confirms full count in-container. Tester baseline projection: 1013 (05d) → ~1230 in 06.

### Per-phase workflow

Standard cadence (a)–(l) per `user_two_machine_setup.md` + PHASE_MAP §1. Key reminders:
  - Squash-merge PR to main BEFORE tagging `phase-06-confirmed` (per `feedback_release_workflow_ordering.md`).
  - Bump version strings: `mindsos_core/__init__.py:__version__`, `pyproject.toml`, `compose.yml`, manifest — all `+phase05d` → `+phase06`.
  - Doctor self-test should pass with no new checks needed (P8 B = no state-file kind to validate).
  - Confirmation doc + implementation log MUST exist on `main` before tag (release.yml step 10:21 enforcement).

### Locked decisions that often surprise implementers (read these picks first)

  - **P2 A:** ADR-0132 says "move from Core" but Core has no `instance.py`. You're shipping fresh code, not moving. ADR-0132 gets a material rewrite in this PR (not just a pointer line).
  - **P24 B + P31 A + P44 A:** Cascade-delete is a Phase 06 invariant. Implementation requires a remove-observer hook in `mindsos_core` (Graph + Metagraph remove methods). ~15 LOC in Core. Recursive cascade through composites.
  - **P36 A:** Per-subclass override allow-list is load-bearing. Implementation enforces it per subclass at `set_override` time. GraphInstance ships with EMPTY allow-list — this is intentional; do not "fix" it.
  - **P13 B:** SubGraphInstance is a `(graph_id, node_ids: set[str], edge_ids: set[str])` triple. NOT a graph-minus-nodes. Strict edge-endpoint-membership invariant per P20 A.
  - **P33 B:** `type_name` is in the universally-forbidden override set for Edge/HyperEdge/MetaEdge/MetaHyperEdge instances. Even though §B's per-subclass allow-list includes structural fields, `type_name` is excluded across all of them.
  - **P38 A + P41 A + P42 A:** CLI is 4 verbs with `--materialise` flag (no separate materialise verb). `compose` takes inline JSON `--member-spec` flags. `--override key=val` parses value as JSON fragment (numbers/booleans bare; strings need quoting).
  - **P8 B:** NO state-file changes in Phase 06. If you find yourself bumping a state-file version, you've gone outside scope.

### Future-work entries to file (5 total; per row §Future-work)

Add to `_source_backup/root/mindsos_future_plans.md` "Instancing semantics" section (where Phase 06 entries belong):
  - (i) GraphInstance override surface — Phase 10 fills.
  - (ii) Composite combine helper — when L4 ships.
  - (iii) Cross-metagraph composite members — when L4/L5 demonstrates use case.
  - (iv) Soft-delete × cascade-through-composites — Phase 10 picks behavior.
  - (v) Type-name override permission — if L4/L5 polymorphic-template use case surfaces.

Confirm each entry filed before squash-merge.

### Confirmation doc + implementation log + memory

After tester confirmation, create:
  - `confirmation_docs/PHASE_06_CONFIRMED.md` (tester baseline, recipe verbatim, deviations, bug ledger).
  - `confirmation_docs/PHASE_06_IMPLEMENTATION_LOG.md` (round-7 ledger if you ran one; otherwise the bug ledger from implementation).

After ship, write memory:
  - `project_mindsos_phase_06_implemented.md` — canonical shipped-state memory.
  - Update `MEMORY.md` index entry.
  - File any new feedback memories from lessons learned (per 05c/05d pattern).
