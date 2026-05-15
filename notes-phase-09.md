# Phase 09 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

L1 XRef (cross-metagraph refs)

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

Phase 09 ships the L1 cross-metagraph XRef primitive (ADR-0128 hybrid model).
53 active design picks (M0–M18 + PB-1..9 + RPB-1..8 + RR-1..18 minus RR-2
superseded by RR-16) + 13 review-chat pushbacks (P50, P51, P52, P53, P54,
P55, P56, P57, P58, P59, P61, P62, P63, P64, P66) all locked + implemented.
7 in-flight hotfixes (B-09-T1..T7) closed before tag.

== Substrate carry-forward ==

Phase 08 baseline: 1374 + 2 skipped in-container. Phase 09 inherits the
metagraph loader / streaming / refresh / after-load observer / first-L1
WAL consumer. Phase 09 cascade refactors:
* WAL replayer registration moves from module-level _REPLAYERS dict to
  per-Client client._replayers dict (P51 + P61). register_replayer /
  clear_replayers / recover all take client positional.
* WALReplayerMissingError silent narrow-catch in MetagraphLoader.load
  removed (P62) — Phase 09 ships actual L1 replayers (xref_add +
  xref_remove) registered on FalkorClient.__init__ via
  register_all_l1_replayers, so unknown kinds now propagate loud.
* Phase 07 tests/phase_07/test_wal.py refactored to per-Client form
  + new test_per_client_replayer_isolation + test_clear_replayers_per_client
  + test_recover_raises_on_unknown_kind (P62 contract).
* Phase 08 tests/phase_08/test_load_metagraph_recovery.py refactored:
  test_recover_no_replayer_silent_no_op_per_rpb_3_c REPLACED with
  test_recover_unknown_kind_raises_per_p62 (loud-fail contract).

== Manual exploration ==

All 9 row §Pass-criterion bullets exercised in-container. Recipes +
expected outputs + actual results below. Recipes use --entrypoint
/bin/bash heredocs where state-file persistence is needed (because
docker compose run --rm destroys container fs between invocations);
DB-only verbs (xref-list, load) work across separate calls.

[Exercise 1] doctor --self-test
  Command: docker compose run --rm mindsos doctor --self-test
  Result: exit 0; phase=09; 3-package version parity at 0.0.0+phase09;
          image-tag parity at phase09; indexes substring-check finds
          all 18 expected XRef labels.

[Exercise 2] xref-list against empty metagraph
  Command: heredoc — metagraph create + sync; then xref-list (table)
           + xref-list --json
  Result: empty Rich table with 6 columns (xref_id / source_id /
          target_metagraph_id / target_role / target_id / ref_type);
          --json returns []; exit 0.

[Exercise 3] programmatic add_xref + WAL :WALEntry verification
  Command: heredoc — Metagraph + Graph + Node + add_xref +
           MetagraphRepository.persist + DB Cypher read
  Result: Dirty: {<uuid>} after add → Dirty after: set() after persist;
          DB XRef row present (sid=doggo, tid=dog, rt=SPECIALISES);
          WAL entry committed (c: True). PB-6 no-dedup confirmed by
          re-running (rows accumulate; FalkorDB volume persists).

[Exercise 4] xref-list after persist (filter narrowing)
  Command: docker compose run --rm mindsos persistence xref-list
           --metagraph prog-test [--source-id doggo] [--target-metagraph mg-global]
  Result: Rich table shows row(s) with truncated 8-char IDs; --source-id
          filter narrows correctly; --target-metagraph filter via
          (target_metagraph_id, target_id) compound prefix-match works
          (P56 Box 16 probe verified DDL syntax + prefix-match support).

[Exercise 5] load --metagraph M structured summary (P52 + M17 + B-09-T1)
  Command: docker compose run --rm mindsos persistence load --metagraph prog-test
  Result: stdout is "Metagraph: ..." / "Metagraph id: ..." / "Dependent
          state: graphs=N metaedges=N ... xrefs=N ..." (single
          structured key=value line per P52, replacing Phase 08's
          9-line flat list); --json includes "XRefs": N key (M17).
  HOTFIX B-09-T1 surfaced here: see hotfix ledger below.

[Exercise 6] sync --replace refusal on XRef dependent state (M11)
  Command: heredoc — create+sync mg-prog-ex6, seed XRef row directly
           in DB, attempt sync --replace
  Result: exit 2 with "Metagraph 'prog-test-ex6' has dependent state
          (1 XRef); drop them or truncate WAL before --replace."
          Confirms M11 patch (source_metagraph_id query field) +
          RPB-4 C dependent-state refusal carried forward.

[Exercise 7] load --to-json round-trip (RR-8 + RR-18 + state-file v=4)
  Command: heredoc — load --metagraph M --to-json + cat the file
  Result: JSON file written with top-level "xrefs" array; each entry
          has 8 keys (xref_id / source_metagraph_id / source_id /
          target_metagraph_id / target_role / target_id / ref_type /
          properties). NO target_stale or deprecated_at keys (P53
          deferred fields confirmed absent).

[Exercise 8] programmatic legacy-property migration (M9 + RPB-2)
  Command: heredoc — node with ref:global_lexicon + ref_type properties;
           migrate_in_memory(mg, target_metagraph_id="mg-global")
  Result: Before: properties={"ref:global_lexicon": "tgt-1",
          "ref_type": "SPECIALISES"}, xrefs=0. After: created=1,
          properties={}, xrefs=1, flag=2026-...ISO timestamp.
          Confirms M9 flag rename ("xref:migrated_at"); confirms
          v3-verbatim migration body works on halvim port.

[Exercise 9] WAL crash + recovery (M16 + PB-8)
  Command: heredoc — WriteAheadLog.begin without commit (simulated
           crash); recover(client, mid) replays via MERGE-based
           xref_add replayer; idempotent re-recover
  Result: Begin written; WAL count=1 / XRef before recover: 0 /
          Replayed: 1 / XRef after recover: 1 / WAL count after: 0.
          Confirms M16 WAL crash safety; PB-8 MERGE-based replayer
          idempotency; per-Client replayer registration (P51 +
          register_all_l1_replayers via FalkorClient.__init__).

[Extra A] AND-composed filter on xref-list (PB-2 multi-filter)
  Command: xref-list --metagraph M --source-id X --ref-type Y --json
  Result: returns intersection of source_id AND ref_type matches.

[Extra B] xref-list against unknown metagraph (P63 anchor guard)
  Command: xref-list --metagraph ghost-mg-does-not-exist
  Result: error message + exit 2.

[Extra C] doctor index parity (M15 + B-07-T4 substring grouping)
  Command: persistence diagnose
  Result (after B-09-T2 hotfix): indexes_present: 14 / expected: 14.
  HOTFIX B-09-T2 surfaced here: see hotfix ledger below.

[Extra D] state-file v=3 → v=4 auto-migration (RR-7 + RR-12)
  Command: heredoc — drop synthetic v=3 metagraph file; load via
           state_mod.load_metagraph_state which auto-migrates
  Result: loaded _state_version=4; loaded xrefs=[]; CURRENT_VERSION=4.
          Confirms _v3_to_v4 single-step migration adds xrefs[]
          default; idempotent re-migration safe.

== Hotfix ledger ==

B-09-T1 — `_load_metagraph_cmd` in mindsos_cli/commands/persistence.py
missed wiring `attach_xref_loader(mg)` alongside `attach_registry(mg)`
before the manual after-load dispatch. Result: `load --metagraph M`
summary always reported xrefs=0 even when :XRef rows existed in DB
(XRefLoader observer never subscribed → never fired). Patch: insert
`from mindsos_core.reconstruction import attach_xref_loader` +
`attach_xref_loader(mg)` call after `attach_registry(mg)`. Surfaced
during Exercise 5 manual run.

B-09-T2 — `mindsos persistence diagnose` reported `indexes_present: 14
/ expected: 18` after Phase 09 added 4 :XRef indexes. Root cause:
FalkorDB v4.18.3 groups multi-property indexes per (kind, label) pair
into a single `db.indexes()` row, so 18 logical indexes returned 14
rows. Diagnose was comparing row count vs `len(DEFAULT_INDEXES)` (the
logical-index count). Patch: compute `expected` as the count of
distinct (kind, label) pairs in `DEFAULT_INDEXES` (`expected =
len({(kind, label) for (kind, label, _prop) in DEFAULT_INDEXES})`).
Phase 07 had the same potential mismatch but only surfaced when XRef's
4-property grouping made the gap visible. Surfaced during Extra C
manual run.

B-09-T3 — tests/phase_07/test_bootstrap.py hard-coded
`len(DEFAULT_INDEXES) == 14`, the bootstrap call-count assertion at
14, and `kinds.count("node") == 11` per the Phase 07 P95 B baseline.
Phase 09 M15 grew DEFAULT_INDEXES to 18 (4 new :XRef entries) → 3
related assertions failed in the automated suite. Patch: replace
hard-coded literals with dynamic `len(DEFAULT_INDEXES)` references in
both the count test and the bootstrap-emits-statements test; update
split test to expect 15 node + 3 rel after Phase 09 additions; rename
test_default_indexes_count_equals_14 → test_default_indexes_count_phase07_baseline_plus_phase09_xref
+ add an inline assertion that 4 :XRef entries exist. Audit miss
analogous to state-file version literals — Phase 07 baseline counts
in non-state tests are subject to the same B-05d-T1 / B-08-T1 class
of regression. Surfaced during confirm-phase Box 17.

B-09-T4 — Load-bearing: `_metagraph_to_state` in
mindsos_cli/commands/metagraph.py serializer was never updated to
include `xrefs[]`. Phase 09 RR-7 + RR-12 + RR-18 added the migration
chain + state-file v=4 + deserializer (`_state_to_metagraph` reads
xrefs[]) + the .fromdb.json sibling payload (which is its own
function) — but the canonical state-file writer was missed. Result:
5 failures in tests/phase_09/test_state_file_xrefs_round_trip.py
(serialize / round-trip / dirty-empty / inverse-indexes / sort-by-id
all asserted against an absent `xrefs` key). Patch: append
`"xrefs": sorted(...)` block to the dict returned by
_metagraph_to_state with the 8-field shape per P53 + sorted by
xref_id per RR-8. Audit miss — RR-18 covered the read side; the
symmetric write side wasn't in the recommended-implementation list.
Surfaced during confirm-phase Box 17.

B-09-T5 — tests/phase_09/test_doctor_phase09.py called
`_load_manifest(_repo_root() / "mindsos_cli" / "manifest.toml")` with
a positional path arg; the doctor module's `_load_manifest()` takes
no arguments (reads from the default repo path internally). TypeError
on call. Patch: drop the positional arg. Surfaced during confirm-
phase Box 17.

B-09-T6 — tests/phase_08/test_doctor_phase08.py hard-coded
`phase == "08"`, `version == "0.0.0+phase08"`, and
`mindsos:phase08-prod / -test` compose-tag literals. Phase 09 bump
broke 3 assertions. Patch: rewrite as parity-against-manifest tests
(assert phase field is a 2-digit str; version encodes same phase as
phase field; mindsos_cli + mindsos_core + mindsos_instances +
pyproject + docker-compose all agree with manifest). Future phase
bumps no longer require edits here. Same audit class as B-09-T3.
Surfaced during confirm-phase Box 17.

B-09-T7 — tests/phase_08/test_cli_persistence_load_metagraph.py
::test_load_metagraph_9_line_flat_summary asserted the Phase 08
R4-5 A 9-line flat-list summary literal shape. Phase 09 P52 + M17
replaced the 9-line list with a single structured `Dependent state:
key=value ...` line that grows additively. Patch: rename to
test_load_metagraph_dependent_state_summary; assert by KEY presence
not by line count (mirror M17 + P52 spec for forward-compat).
Surfaced during confirm-phase Box 17.

== Recipe deviations (worth surfacing for future phases) ==

* `docker compose run --rm` destroys container fs between invocations.
  State files written by `mindsos metagraph create` in one container
  are NOT visible to subsequent `mindsos persistence sync` calls in a
  fresh `--rm` container. Workaround: chain create + sync inside one
  `--entrypoint /bin/bash` heredoc. (Re-affirms
  feedback_docker_compose_invocation.md.)
* User-context split: regular `docker compose run --rm mindsos <verb>`
  runs as the `mindsos` user (state files in /home/mindsos/.mindsos/);
  `--entrypoint /bin/bash` overrides entrypoint.sh's gosu drop and
  runs as root (state files in /root/.mindsos/). Mixing the two leads
  to "no state file" or "no such file or directory" errors. Stay in
  one mode per exercise.
* Mac → Linux sync gap: B-09-T1 hotfix on Mac filesystem did not
  appear in the Linux container until git push from Mac + git fetch +
  reset on Linux + docker compose build --no-cache. `docker compose
  build mindsos` (without --no-cache) used cached layers and skipped
  the patched file. Surfaced because the comment portion of the patch
  landed in an earlier image build but the import + call lines did
  not. (Re-affirms feedback_release_workflow_ordering.md sync prereq.)
* Future-phase audit class: Phase 07-baseline numeric / string literals
  (index counts, file counts, summary line counts, phase-string
  hard-codes in doctor tests) are subject to the same audit-cost as
  state-file version literals. Step 0 audit should grep ALL tests for
  hard-coded baseline counts AND phase-string literals that the new
  phase changes (B-09-T3 + B-09-T6 surfaced this; consider filing a
  feedback memory).
* Symmetric serializer/deserializer audit: when a state-file version
  bumps with a new array field, BOTH the serializer (_metagraph_to_state)
  AND the deserializer (_state_to_metagraph) need extending. Phase 09
  RR-18 covered only the read side; the symmetric write side missed
  → B-09-T4 surfaced. Future phases should pair both edits in the
  recommended-implementation list.

== Sign-off ==

Phase 09 ready to ship. confirm-phase shows 0 failures + cumulative
count ≥ Phase 08 baseline (1374 + 2 skipped) + Phase 09 additions
(~30 new test files; substrate refactor tests included). PR +
squash-merge + tag phase-09-confirmed + Release CI follow per
workflow steps (j)–(l) in user_two_machine_setup.md.
