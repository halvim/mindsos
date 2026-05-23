══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 24 IMPLEMENTATION (design locked 2026-05-22)
══════════════════════════════════════════════════════════════════════

This handoff supersedes the pre-design version of this file. Phase 24
design is LOCKED via `PHASE_24_DESIGN_LOG.md` (5 rounds, 28 picks).
Your job is to IMPLEMENT against the locked design — no re-litigation
of locked picks; only round-by-round implementation pushbacks against
unforeseen substrate issues that surface during code build.

Project: MindsOS — folder `halvim_mindsos/` under `/Layered Intelligence/`.
Branch off `origin/main` tip (the Phase 23 retirement squash `c78146c`
on top of Phase 22 squash `c25a1bc`).

ROLE: Critical implementer + reviewer. Read project-level CLAUDE.md
at `/Layered Intelligence/CLAUDE.md` AND halvim sub-project CLAUDE.md
if present. Follow strict picks-per-pushback discipline for any
NEW pushback surfaces that arise during implementation (each
pushback ends with a pick; final picks summary at end of each round
per `feedback_pushback_format_with_picks.md`).

══════════════════════════════════════════════════════════════════════
REQUIRED READING (in this order — read the files; do NOT ask for
their content to be repeated)
══════════════════════════════════════════════════════════════════════

1. **`MEMORY.md`** — auto-loaded at chat start. Pay special attention
   to the NEW entry `project_mindsos_phase_24_design.md` (Phase 24
   design lock summary). Hard rules:
   * `feedback_pushback_format_with_picks.md`
   * `feedback_pre_impl_probe_check_existing_modules.md`
   * `feedback_phase_baseline_literal_audit.md`
   * `feedback_smoke_harness_host_native.md`
   * `feedback_pk_column_per_table_probe.md`
   * `feedback_l1_api_signature_probe_before_writing_tests.md`
   * `feedback_test_image_rebuild_after_source_change.md`
   * `feedback_release_workflow_ordering.md`
   * `feedback_release_tag_after_squash_merge_only.md`
   * `feedback_batch_fix_dont_iterate.md`
   * `feedback_sandbox_vs_mac_git_separation.md`
   * `feedback_state_file_serializer_deserializer_symmetry.md`
   * `feedback_phase_baseline_literal_audit.md` (schema bump v3 → v4
     means baseline literals across `tests/` decay)
   * `user_two_machine_setup.md` (Mac/Linux split)

2. **`halvim_mindsos/confirmation_docs/PHASE_24_DESIGN_LOG.md`** —
   the canonical record of what to build. §0 scope summary + §1
   round-by-round design ledger (28 picks) + §2 final locks
   consolidated + §5 implementation references (file layout +
   test-file breakdown) + §6 out-of-scope + §8 Phase 23 retirement
   carry-forward disposition. Read in full.

3. **`halvim_mindsos/confirmation_docs/PHASE_MAP.md`** §0 (load-
   bearing read rule) + §1 (settled cross-cutting decisions) +
   §Phase 24 row (DESIGN-LOCKED 2026-05-22) + §Phase 25 row
   (absorbed scope from Phase 24 deferrals) + §Phase 22 row (admin
   ops precedent for admin_tx + admin subgroup pattern that P24
   extends) + §Phase 16 row (similarity surface that audit gate
   consumes) + §Phase 10 row (snapshot primitives — retained,
   zero consumer per ADR-0129 §am2) + §Phase 14 row (KL bootstrap
   that propose_for_promotion uses) + §Phase 15a row (bootstrap_
   global pattern that P24 extends for eager pending-Global
   bootstrap).

4. **ADRs at `/Layered Intelligence/docs/decisions/adr/`**. Read in
   full:
   * **ADR-0114** [Accepted] — release manifest + version DB schema;
     2 tables; schema v3 → v4; CHECK constraints; manifest_json
     SHIPPED + FAILED shapes.
   * **ADR-0115** [Accepted] — release-ship audit gate; two-pass
     `compute_similarity`; AuditGateResult; v1 narrow (Release
     Summary + SimilarityWarning only).
   * **ADR-0120** [Proposed at P24; impl at P25] — cross-layer
     rewrite handler contract; P24 contract-only (no consumer).
   * **ADR-0118 §am1** [Accepted] — admin location correction +
     v1 scope narrow + lazy migration defer to P25 + multi-role
     rollback corrected semantics.
   * **ADR-0141 §am1** [Accepted] — admin location correction +
     halvim-no-op vacuous (KL never ported promote).
   * **ADR-0144 §am2** [fully Accepted] — §Placement closes; two-
     pass audit gate; `SimilarityWarning.source` discriminator.
   * **ADR-0129 §am2** [Accepted, snapshot vestigial] — drop inline
     pattern; module retained; lint rule dropped; Phase 23 §7 #1-4
     re-opened.
   * **ADR-0007** [Superseded] — banner closes; cross-user atomic
     premise replaced.
   * **ADR-0049 / 0053 / 0056** [→ Superseded at P24 ship] — per
     Phase 16 §am1 lock; no further ADR edits beyond Status header.
   * **ADR-0002 §am2** [+2 caps] — roster 7 → 9.
   * **ADR-0006 §am1** [Accepted] — RELEASE_SHIP_LOCK rename;
     threading.RLock substrate.
   * **ADR-0010** [Accepted, unchanged] — layer isolation; new
     `mindsos_server → mindsos_admin` edge codified via test (no
     ADR amendment).
   * **ADR-0125** [Accepted] — lazy local hydration; the reason
     snapshot is vestigial in release_update (PB-7 probe).
   * **ADR-0140 §am1** [Accepted] — admin permanent-home precedent
     that PB-8 followed.

5. **PIVOT_V1_SCOPE_2026-04-26.md** at `/Layered Intelligence/docs/`
   — §6.A code change summary, §7.1 PromotionProposal shape (P24
   ships full per PB-18), §7.2 pending-Global storage (P24 eager
   bootstrap per PB-15), §7.4 multi-Local rollback (forward-only),
   §7.5 release manifest (P24 narrows to 2 tables per ADR-0114),
   §7.6 audit events (P24 ships 4 of 8 per PB-6 + PB-11), §7.8
   ImpactReport (P24 narrows to 2 sections per ADR-0115).

══════════════════════════════════════════════════════════════════════
PRE-IMPL PROBE (run BEFORE writing any code — surface drift early)
══════════════════════════════════════════════════════════════════════

```
cd halvim_mindsos
# Verify baseline branch state.
git fetch origin && git log --oneline origin/main | head -5
# Expected: c78146c (Phase 23 retirement) + c25a1bc (Phase 22) at top.

# Verify Phase 22 surfaces intact (admin_tx + admin subgroup).
grep -n "admin_tx\|_assert_not_sole_admin\|admin_promote_user" mindsos_server/admin.py | head -10
grep -n "LastAdminError\|AlreadyAnAdminError\|SessionNotFoundError" mindsos_server/errors.py | head

# Verify Phase 16 similarity surface intact (target_mg keyword + intra-mg + cross-mg).
grep -n "def compute_similarity\|target_mg\|matched_is_candidate" mindsos_admin/similarity.py | head

# Verify Phase 10 snapshot primitives intact (retained per ADR-0129 §am2; zero consumer at P24).
ls mindsos_core/metagraph_snapshot.py
grep -n "class MetagraphSnapshot\|def of\|def restore_into" mindsos_core/metagraph_snapshot.py | head

# Verify MetagraphRepository.persist write-through (the PB-7 probe finding that justified
# PB-13(a) snapshot drop — re-confirm before locking implementation).
grep -n "def persist\|_client.run_query\|metagraph\." mindsos_core/persistence/metagraph_repository.py | head -30

# Verify Phase 24 surfaces ABSENT.
find mindsos_server -name "release.py" -o -name "locks.py" 2>&1
find mindsos_admin -name "promotion.py" -o -name "audit_gate.py" 2>&1
grep -rn "RELEASE_SHIP_LOCK\|release_update\|propose_for_promotion\|pending_global" mindsos_admin/ mindsos_server/ 2>/dev/null | grep -v "\.pyc\|docstring" | head

# Verify ADR Status states match the design-log claims.
head -10 ../docs/decisions/adr/0118-per-user-transactional-promotion.md   # Status: Accepted
head -10 ../docs/decisions/adr/0141-delete-shipped-promote.md             # Status: Accepted
head -10 ../docs/decisions/adr/0144-similarity-at-release-ship-audit-gate.md  # Status: Accepted
head -10 ../docs/decisions/adr/0129-metagraph-snapshot-narrowed-to-release-ship.md  # Status: Accepted
head -10 ../docs/decisions/adr/0007-metagraph-snapshot-rollback.md        # Status: Superseded
head -8 ../docs/decisions/adr/0114-release-manifest-and-version-db-schema.md  # NEW; Accepted
head -8 ../docs/decisions/adr/0115-release-ship-audit-gate.md             # NEW; Accepted
head -8 ../docs/decisions/adr/0120-cross-layer-rewrite-handler-contract.md  # NEW; Proposed

# Verify capability roster baseline.
grep -n "CAN_\|ALL_CAPABILITIES\|ADMIN_CAPS" mindsos_server/capabilities.py | head -20

# Verify schema baseline.
grep -n "_SCHEMA_VERSION" mindsos_server/_schema.py | head

# Verify CLI Typer apps (server_app + user_app + admin_app exist; release_app does NOT yet).
grep -n "Typer\|add_typer\|^def \|^@" mindsos_cli/commands/server.py | head -25

# Verify version baseline.
grep -h '__version__' mindsos_*/__init__.py 2>/dev/null

# Verify cumulative test green count baseline (Phase 22 ship: 2802/28).
# Run after first implementation round — pre-impl baseline assumes test count holds.
```

If ANY surface mismatch surfaces (e.g., persist mutates in-memory after
all; capability roster already has CAN_PROPOSE_MUTATION; release.py
already exists), STOP and report. The design log assumes the probe
findings above hold.

══════════════════════════════════════════════════════════════════════
IMPLEMENTATION SHAPE (everything lives in PHASE_24_DESIGN_LOG.md §5)
══════════════════════════════════════════════════════════════════════

Build out per design log §5 implementation references. The file
layout + per-file responsibility + ~22 phase_24/ test file list is
in §5; the per-pick rationale is in §1 ledger; the locked picks
table is in §2. Do NOT re-derive these in chat.

**Sequencing recommendation (not locked — implementer's call):**
1. Schema v3 → v4 migration + DDL (ADR-0114 substrate).
2. Capability roster +2 caps + audit events +4 EVT_* constants
   (ADR-0002 §am2 + PB-27 payload shapes).
3. `mindsos_server/locks.py` (RELEASE_SHIP_LOCK threading.RLock).
4. `mindsos_admin/promotion.py::propose_for_promotion` (ATOM admin-
   direct only; admin_tx ordering per PB-25; NotImplementedError for
   source_user_id + non-ATOM kinds).
5. `mindsos_admin/audit_gate.py::run` (two-pass compute_similarity
   per PB-24; AuditGateResult; BlockingFindingError).
6. `mindsos_server/release.py::release_update` (RLock + admin_tx +
   audit-gate-snapshot pattern per PB-26 + EmptyReleaseError per
   PB-21 + FAILED-row forensics per PB-28).
7. `mindsos_admin/bootstrap.py` extension (eager pending-Global per
   PB-15).
8. CLI `mindsos server release` Typer subgroup (PB-14) + exit-code
   mapper (codes 7/8).
9. `tests/phase_24/` file build-out per design log §5 list (~22
   files).
10. `tests/phase_24/test_import_isolation_phase24.py` (ADR-0010
    codifying `mindsos_server → mindsos_admin` allowed; reverse
    forbidden; KL forbids both).
11. Cumulative green sweep + 9-site version bump.

══════════════════════════════════════════════════════════════════════
PROCESS DISCIPLINE
══════════════════════════════════════════════════════════════════════

Per `user_two_machine_setup.md` + PHASE_MAP §1:

* **Mac**: code editing (Claude session), `git add/commit/push`,
  `gh pr create`, `gh pr merge --squash`, final `git tag` + push.
  Mac has NO docker. Mac Python 3.9.6 — do NOT `pip install -e .` on
  Mac.
* **Linux**: `git pull`, `docker compose --profile test build
  mindsos-test` (pre-build to avoid 600s confirm-phase timeout per
  `feedback_confirm_phase_timeout.md`; 900s in Phase 07+), all
  `docker compose run --rm mindsos-test pytest ...` runs, all
  **host-native** `mindsos <verb>` smoke (per
  `feedback_smoke_harness_host_native.md`).
* **confirm-phase**: host-native is canonical. Run from Python ≥ 3.12
  venv on Linux host (`pip install -e . --user --break-system-packages`
  after pulling phase-24 branch).
* **Test order**: current-phase isolated tests (`tests/phase_24/`)
  GREEN BEFORE cumulative sweep (`tests/`) per
  `feedback_test_order_current_then_cumulative.md`.
* **Schema-version baseline literal audit** per
  `feedback_phase_baseline_literal_audit.md`: schema v3 → v4 bump
  decays literals across `tests/`. Static grep ALL tests at Step 0;
  patch once + rebuild test image (`mindsos-test`) before re-running
  per `feedback_test_image_rebuild_after_source_change.md`.

**Version bump path: `+phase22 → +phase24`** (skip `+phase23` per
PHASE_MAP §1 design-only-phases clause; precedent: Phase 14a + Phase
15b skipped their slots). Phase 17 retirement DID earn `+phase16 →
+phase17` because it shipped 5-LOC; Phase 23 retirement did NOT
(zero code beyond a one-line docstring fix). Do not use Phase 17 as
the version-bump precedent here.

**9-site version bump checklist** per `feedback_new_top_level_package.md`:
* 6 pkg `__init__.py` (mindsos_core / mindsos_knowledge / mindsos_cli /
  mindsos_admin / mindsos_instances / mindsos_server)
* `pyproject.toml` [project] version + description
* `mindsos_cli/manifest.toml` [mindsos] phase + version
* `docker-compose.yml` image tags (2 occurrences — prod + test)

**Tag `phase-24-confirmed` AFTER squash-merge only** (per
`feedback_release_tag_after_squash_merge_only.md`). 8-step ordering
strict per `feedback_release_workflow_ordering.md`. Confirmation doc
at `confirmation_docs/PHASE_24_CONFIRMED.md` (auto-generated by
`confirm-phase --phase 24 --notes-file notes-phase-24.md` per
`feedback_confirm_phase_file_paths.md`).

**Sandbox vs Mac git separation** per `feedback_sandbox_vs_mac_git_separation.md`:
Claude sandbox uses Edit/Write for files; HAND the user the
`git add / git commit / git push / gh pr create / gh pr merge --squash /
git tag / git push origin <tag>` commands for them to run on Mac.
Do not run those from inside the Claude sandbox.

══════════════════════════════════════════════════════════════════════
LOCKED ADR DELTA AT SHIP (11 touches — design log §4)
══════════════════════════════════════════════════════════════════════

Confirm at ship — these are ALREADY in their target Status / amended
state per the design pass (this chat). Implementation chat does NOT
re-write these unless implementation surfaces a substrate gap that
needs a §amendment:

3 new drafts (already Accepted in design pass):
* ADR-0114 (release manifest + version DB schema)
* ADR-0115 (release-ship audit gate)
* ADR-0120 (cross-layer rewrite handler contract — Proposed; impl at P25)

4 Status flips (already in target state):
* ADR-0007 Accepted-with-banner → Superseded
* ADR-0118 Proposed → Accepted (+ §am1)
* ADR-0141 Proposed → Accepted (+ §am1)
* ADR-0144 → fully Accepted (§am1 retires; §am2 documents §Placement)

3 indirect Supersessions (Status header flip only at this ship):
* ADR-0049 Accepted → Superseded
* ADR-0053 Accepted → Superseded
* ADR-0056 Accepted → Superseded

3 documentary §amendments (already written):
* ADR-0129 §am2 (snapshot vestigial; module retained; lint rule
  dropped; Phase 23 §7 #1-4 re-opened)
* ADR-0118 §am1 (admin location + scope narrows + multi-role
  semantics)
* ADR-0141 §am1 (admin location + halvim no-op vacuous)

1 cap-roster §amendment (already written):
* ADR-0002 §am2 (+CAN_PROPOSE_MUTATION + CAN_APPROVE_RELEASE; roster
  7 → 9)

1 rename-ratification §amendment (already written):
* ADR-0006 §am1 (RELEASE_SHIP_LOCK rename + threading.RLock
  substrate + per-user mutex retained unchanged)

If implementation surfaces a substrate gap (e.g., FalkorDB FK
behavior differs from SQLite assumption; Phase 16 `compute_similarity`
target_mg keyword has unexpected signature; admin_tx pattern misses
a Phase 24-specific race) — surface a NEW §amendment or NEW
implementation-chat pushback round per CLAUDE.md "ADR decisions
could be changed if we get to new decisions in this chat." Halvim
precedent: implementation rounds routinely produce documentary
§amendments (Phase 18-22 produced 5-9 §am batches each).

The 3 indirect Supersessions (0049 / 0053 / 0056) ship only as
Status header flips at the implementation chat's ADR sweep — NO
body edits beyond the Status line + a date stamp. They were locked
at Phase 16 §am1; Phase 24 is the mechanical closer.

══════════════════════════════════════════════════════════════════════
EXIT CRITERIA
══════════════════════════════════════════════════════════════════════

Phase 24 squash-merges to main; `phase-24-confirmed` tag pushed
AFTER merge; `release.yml` green; GitHub Release created.

ADR Status table at ship matches the design-log §4 ADR delta
(11 touches).

Cumulative green count grows from Phase 22's 2802 by the phase_24/
isolated count (~estimated 100-150 tests across ~22 files; actual
to be discovered during build).

Phase 24 writes `confirmation_docs/PHASE_25_NEXT_CHAT_PROMPT.md` as
exit artifact (substantive per Phase 23 retirement §3 PB-ε(a)
precedent — Phase 25 absorbs source-user propose + lazy migration +
4 deferred audit events + ADR-0120 impl; not a one-liner).

Memory entry `project_mindsos_phase_24_implemented.md` written +
indexed in MEMORY.md (replaces / supplements `project_mindsos_phase_24_design.md`).

══════════════════════════════════════════════════════════════════════
FIRST RESPONSE EXPECTATIONS
══════════════════════════════════════════════════════════════════════

1. Confirm required-reading files read (terse list — file names
   only; do not paraphrase content).
2. Run pre-impl probe; report any surface drift.
3. Confirm intent to follow the design log §5 implementation
   references file layout + the recommended sequencing above.
4. Surface 0-3 implementation pushbacks if probe-time substrate
   findings disagree with design-log assumptions (with picks per
   `feedback_pushback_format_with_picks.md`).
5. Ask ONE highest-value missing-constraint question if any (e.g.,
   "PromotionResult dataclass shape locked at PB-? — please confirm
   `audit_event_id` field type is int or AuditEventID NewType"). DO
   NOT write code in the first response.

══════════════════════════════════════════════════════════════════════
