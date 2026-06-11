You are the Phase 51 (WSD-1) ship chat for the MindsOS project — Rail S-1 of
the WSD installation plan: riders + lexicon empirical-layer substrate. Design
is CLOSED (WSD_INSTALLATION_CHAT, 2026-06-10); you implement, recording
impl-locks + grounding-driven refinements only (Phases 39-50 precedent).
Re-open a settled pick only on a grounding-driven reversal with file-level
evidence.

READ FIRST, in this order (this prompt repeats nothing they contain):
1. `HANDOFF.md` — §3.1.23 (current ship state) + §9 (ship discipline:
   pair-execution Cowork↔Mac↔Linux, no sandbox git mutations, gate-box
   checkout verification, docker test-image rebuild before every gate,
   python3 on the gate host, no gh/mindsos CLI there, squash-before-confirm,
   6-step confirm, ADR transcription parity check as R1 step 0).
2. `confirmation_docs/WSD_INSTALLATION_PHASE_MAP.md` — §2 WSD-1 row is your
   scope + pass criteria VERBATIM; §1 the settled contract; §3 the ledger
   you must not pull forward.
3. `confirmation_docs/WSD_INSTALLATION_DESIGN_LOG.md` — the decision record
   behind every pick you consume: §1 PB-W2 (empirical-layer is the
   sense-correlations home), §2 PB-W14/W15 (hypernym stratum is what your
   EdgeTypes must support), §4 PB-W21 (discipline: ADMIN_AUTHORED unchanged;
   no runtime-writer surface in your slot), §5 R3 favorable findings
   (hypernym edges already shipped; L3-59(b) ripple containment).
4. `docs/future_work/L3_FUTURE_WORK.md` L3-59 + `mindsos_capacity/context.py`
   + `capacity_layer.py` invoke read path — the surfaces your migration
   flips. Phase 48 A1′ record (`PHASE_48_DESIGN_LOG.md`) explains exactly
   what was left "one more phase" for you.
5. `tests/maintenance/test_l0_25_falkor_local_persister_live.py` (the
   standing xpassed) + `PHASE_44_DESIGN_LOG.md §7` — the L0-25 sweep-audit
   seam.
6. `mindsos_knowledge/schemas/lexicon.py` + `schemas/alignment.py`
   (extra_edge_types precedent) + ADR-0182 + `PHASE_50_DESIGN_LOG.md` I4/I5
   — your schema-amendment templates and constraints.

PREREQ CHECK (first action):
- `git tag --list | grep phase-50-confirmed` present; `main` at/after the
  WSD design-closure docs commit (WSD_INSTALLATION_PHASE_MAP.md +
  WSD_INSTALLATION_DESIGN_LOG.md + this file must be ON main — if absent,
  stop and ask Henrique to commit them Mac-side first).
- Untracked corpus (ROBOT_DEMO_*, A2_REDO_*, demo_ui/, sim/,
  prototype_zero/, web/, .fuse_hidden*) — NEVER `git add -A`.
- Confirm Phase 51 > current manifest high-water (50) → full 10-surface
  bump applies (manifest checklist in POST_PHASE_38_PHASE_MAP §1).

R0 EXPECTATIONS:
- Draft the slot's ADRs (empirical-layer edge vocabulary; any L3-59(b)
  closure amendment) BEFORE code; run the parity check against them at R1.
- Budget: this is a riders slot — scope is mechanical except the EdgeType
  property set (count/smoothed-score/source/corpus-version are the design
  log's sketch; finalize at R0 against what slot-52's importers and
  slot-53's scorer will actually read — write the consumer columns down
  before locking).
- The L0-25 audit may surface sweep gaps: fixes in-slot if small; route to
  the ledger with evidence if structural.
- 2-PR split is the natural seam (PR1 = L3-59(b) + L0-25 riders; PR2 =
  empirical-layer schema + ADR) — confirm or collapse at R0 with rationale.

OUTPUT EXPECTATION: ship per HANDOFF §9 end-to-end — green cumulative Linux
gate, ADRs on disk, squash-merge, `PHASE_51_CONFIRMED.md` + tag
`phase-51-confirmed` at the confirm commit, `PHASE_51_DESIGN_LOG.md`
(impl-locks + I-findings), closure edits (HANDOFF §3.1.x append, CLAUDE.md
downstream-progress paragraph, phase-map §2 row → SHIPPED) so the Phase 52
chat opens cleanly.
