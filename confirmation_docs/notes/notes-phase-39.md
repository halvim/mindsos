# Phase 39 — Notes

> Tester fills two fields: `phase_title` and `tester_notes`. Everything else
> in `confirmation_docs/PHASE_NN_CONFIRMED.md` is auto-derived by
> `mindsos confirm-phase`. Read PHASE_MAP §1 (Confirmation doc as artifact)
> for the rationale.

## phase_title

The phase title as it appears in `confirmation_docs/PHASE_MAP.md` §3 / §4 / §5.
Example: `Tooling infrastructure`

L2 `memories` → `episodic_memories` atomic rename + L2-35 alignment reconciliation + ADR-0146 §am-3 multi-NodeType dispatch

## tester_notes

Free-form. What you observed, anything surprising, deviations from PHASE_MAP's
pass criterion, open questions for the next phase chat. This is the
load-bearing field — read by future phase chats per PHASE_MAP §0.

Rail A slot 1 of 11 in the post-Phase-38 plan. Shipped per the design
pass closure at `confirmation_docs/PHASE_39_DESIGN_LOG.md`.

Saturation: R0→R3 design pass + R1/R2 impl-shape + R2/R3 ADR-text
rounds; three consecutive reversal-free rounds. Saturation criterion
satisfied (HANDOFF §9).

Implementation surface: 6 commits on `phase-39` + 2 gate-fix-up commits
(5b, 5c). ~80 file touches: 12 source files (incl. schema rename + 3
ADR files + 1 ADR cross-ref) + 28 test files (24 rename + 7 new
Phase 39 + sentinel_paths) + 14 active docs + 6 project-status files +
manifest + tools/check_rename_state.py + Dockerfile (COPY tools/) +
docker-compose.yml + pyproject.toml + 6 package __version__ strings.

Cumulative gate: 3501 passed / 8 skipped / 0 failed (Linux docker
pytest). mkdocs build clean (~15 pre-existing carry-forward broken-link
warnings; zero new from Phase 39 docs renames).

Surprises / deviations:

1. PB-R1-A docs scope. Design log §3 budgeted "1 docs rename." Reality
   at impl: ~14 active docs files touched. The phased pick
   (concepts/api/usage/dev/summary atomic; stale ROLE_MEMORIES examples
   in non-amend-target ADRs deferred to Phase 43) was made at R1
   PB-R1-A. Phase 43 will absorb the ADR-example cleanup when
   ADR-0152/0153 ship adjacent amendments.

2. PB-R1-D `consolidate.py` interim-semantic-wrongness. Phase 39 keeps
   `type_="Memory"` writing per-task entries through the
   Memory-composite NodeType. Per D-L2-17, Episode is the per-task
   entry; Memory is the composite. Phase 48 retargets per L5 D-B47.
   Inline `NOTE(phase-48-retarget)` comment added at the call site in
   `mindsos_capacity/builtins/consolidate.py` flagging the two-phase
   tech debt.

3. Doctor self-test + version-parity tests. Phase 39's manifest bump
   required advancing __version__ in all 6 packages (mindsos_core,
   mindsos_cli, mindsos_capacity, mindsos_server, mindsos_instances,
   mindsos_admin) + pyproject.toml + docker-compose.yml image tags
   (phase38-prod/test → phase39-prod/test). Phase 30/31/34 export-slate
   sentinel-flips also advanced inline (per the
   sentinel-flip-at-target-phase pattern). Caught by gate at commit 5;
   resolved in commit 5b/5c.

4. Dockerfile `tools/` copy. Phase 39 is the first phase shipping a
   runtime tool under `tools/`. Test-stage Dockerfile previously did
   not copy `tools/` into the test image;
   tests/phase_39/test_check_rename_state_script.py failed at
   integration. Added `COPY tools ./tools` to the test stage with
   comment naming the consumer. Forward-compat for any future `tools/`
   additions.

Forward references:

- Phase 43 (Rail A slot 2; schema-v2) inherits the renamed role; ships
  D-L2-17 fully (Episode + Memory properties + memory_contains_episode
  IntergraphEdge + mutation_discipline + CONTENT_FIELDS/METADATA_FIELDS).
- Phase 43 also ships ADR-0150 §amendment-5 (4 new role-graphs +
  Phase 39's "explicitly NOT added" exclusion list migrated per
  PB-R2-B).
- Phase 48 (L5 v1) retargets `consolidate:mm` to write Episode per D-B47.
