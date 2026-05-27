══════════════════════════════════════════════════════════════════════
NEW CHAT — MindsOS Phase 36 DESIGN + IMPLEMENTATION
══════════════════════════════════════════════════════════════════════
You are running a Phase 36 design + implementation chat for MindsOS.
Phase 36 = "L2 hybrid validators home (ADR-0139)" per the PHASE_MAP.

Layer: L2. **Net-new? YES** — `mindsos_knowledge/validators.py` does
not yet exist; ADR-0139 §Decision proposes the module + an initial
5-validator set. ADR-0139 is the canonical flip target for this phase.

Project rules + memory system live in your normal context — they are
not repeated here. Project rules (skeptical reviewer, picks-per-
pushback, alternatives format, re-litigation cue, saturate before
impl, no filler) apply throughout. Memory: load `MEMORY.md` first;
then load entries by `[[name]]` as cited below.

══════════════════════════════════════════════════════════════════════
REQUIRED READING — read in this order, BEFORE drafting R0
══════════════════════════════════════════════════════════════════════

**Canonical scope + open question** (read first; these two files
define what Phase 36 actually is):

1. `halvim_mindsos/confirmation_docs/PHASE_MAP.md` §"Phase 36" —
   features-line wording carries a load-bearing ambiguity around
   `scope` that R0 PB-1 must resolve. Same wording-vs-reality risk
   pattern that hit Phase 34 + Phase 35 inline-amendments.
2. `docs/decisions/adr/0139-hybrid-invariant-home.md` (parent tree,
   Model C) — Status `Proposed`. Read §Decision (especially
   §Semantic-invariants + §Capacity-contract code skeleton),
   §Rationale, §Consequences, §Alternatives. **The §Capacity-contract
   skeleton is load-bearing — it favours one of the scope-shape
   options below.**

**Phase 35 ship state (immediate baseline):**

3. `halvim_mindsos/confirmation_docs/PHASE_35_DESIGN_LOG.md` —
   especially §8 "Carry-forwards to Phase 36" (enumerates the 6
   load-bearing items Phase 36 inherits) and §6 (sentinel pattern
   Phase 36 will extend: chain 14a→15a→15b→35→36).
4. `docs/decisions/adr/0147-l3-per-flow-write-capacity-build-pattern.md`
   §amendment-1 (Phase 35 ship) — **per-flow discipline now strict.**
   Phase 36 wires validators ONLY where the 2 shipped capacities need
   them; do NOT pre-populate for the 4 deferred capacities' roles.
5. `halvim_mindsos/confirmation_docs/PHASE_34_CONFIRMED.md` — Phase
   34 ship + carry-forwards. ADR-0146 §amendment-1 clause 1 (failure
   modes return PTR vs raise) is still open; Phase 36 may or may not
   close it depending on R0 PB-1 outcome.

**Source surfaces Phase 36 will edit:**

6. `halvim_mindsos/mindsos_knowledge/write_handle.py` — Phase 34
   wired `graph()` / `mint_iri()` / `write_and_validate()` bodies;
   `validate_node()` + `validate_xref()` still raise
   `WriteHandleNotWiredError`. Phase 36 wires those stubs.
7. `halvim_mindsos/mindsos_capacity/builtins/consolidate.py` +
   `trace.py` — Phase 34 wired capacity bodies. Per-flow discipline
   constrains how (and whether) Phase 36 grows these.
8. `halvim_mindsos/mindsos_knowledge/identifiers.py` — `_IRI_BUILDERS`
   2-entry registry pattern; precedent shape for any per-role
   validator registry Phase 36 may build.

**Memory entries** (load via `[[name]]` from MEMORY.md; do NOT
re-read other phases' memory unless cited):

- `[[project-mindsos-phase-35]]` — direct baseline.
- `[[project-mindsos-phase-34]]` — Phase 34 wired surface + B-34-T1
  / T2 / T3 hotfix classes that Phase 36 must avoid.
- `[[feedback-l2-l3-write-side-import-cycle]]` — B-34-T1 lesson.
- `[[feedback-type-checking-caught-by-ast-walk]]` — B-34-T3 lesson.
- `[[feedback-dockerfile-test-stage-file-reads]]` — B-34-T2 class.
- `[[feedback-export-slate-sentinel-audit]]` — Phase 36 will add
  exports if `validators.py` lands on the public surface;
  export-count sentinels in
  `tests/phase_29/30/31/33/test_phase_NN_export_slate.py` need
  function-rename + count flip.
- `[[feedback-confirm-phase-machine-locality]]`,
  `[[feedback-release-tag-after-squash-merge-only]]`,
  `[[user-two-machine-setup]]`,
  `[[feedback-prod-image-rebuild-after-branch-switch]]` —
  ship-mechanics; mandatory for code-shipping phases.

══════════════════════════════════════════════════════════════════════
LOAD-BEARING OPEN QUESTION (R0 PB-1)
══════════════════════════════════════════════════════════════════════

**Where does validator composition live?** Three options, all
defensible:

- **A — Handle-side composition.** Add `scope: Literal['none',
  'structural', 'semantic', 'both']` kwarg to `write_and_validate`;
  handle runs validators when scope ∈ {semantic, both}. Per-role
  validator registry on the handle (same shape as `_IRI_BUILDERS`).
  *Matches PHASE_MAP §36 features-line verbatim.* Conflicts with
  ADR-0143 §Constraint posture (handle stays narrow).

- **B — Capacity-body composition.** `write_and_validate` unchanged;
  capacity bodies call validators from
  `mindsos_knowledge/validators.py` in preconditions per ADR-0139
  §Capacity-contract code skeleton. `handle.validate_node` /
  `handle.validate_xref` wire to compose role-appropriate validator
  chains (helpers, not gates). *Matches ADR-0139 §Decision verbatim;
  needs PHASE_MAP §36 inline-amendment.*

- **C — Hybrid.** Optional `validators=tuple()` kwarg on
  `write_and_validate`; capacity-authors compose from constants and
  pass the tuple. Handle stays mostly narrow; capacity bodies stay
  short. *Three places "where composition lives" can sort-of live.*

R0 PB-1 must resolve this. Reading order to probe correctly:
ADR-0139 §Capacity-contract skeleton first, then PHASE_MAP §36
features-line, then ADR-0143 §Constraint, then ADR-0147 §am-1
clause 3 (per-flow strict — constrains what Phase 36 may
pre-populate).

══════════════════════════════════════════════════════════════════════
SECONDARY OPEN QUESTIONS (R0 PB-2..N)
══════════════════════════════════════════════════════════════════════

- **Which validators actually fire today?** Per-flow discipline
  applies. The 2 shipped capacities write `memories` (Local, user-
  namespaced — no Global ref) and `problem-trace` (Global — no Local-
  to-Global ref). Likely answer: 0-1 of ADR-0139's 5 initial
  validators actually fire today; ship the module + registry, populate
  per-capacity only where needed.
- **`ValidationResult` location** — new dataclass per ADR-0139
  §Semantic-invariants; lives in `validators.py` or `exceptions.py`?
- **ADR-0146 §amendment-1 clause 1 closure** — failure modes return
  PTR vs raise. Phase 36 candidate closer if validator failures are
  the load-bearing mode; or stays open for L4 consumer to drive.
- **Export-slate** — `mindsos_knowledge.validators` module surface;
  what re-exports? Phase 33's `__all__` count (110) likely changes.
- **Sentinel chain extension** — `tests/phase_36/` file extends
  `14a→15a→15b→35→36`. Same skip-on-parent-missing pattern as Phase
  35 (`_skip_if_adr_dir_missing()`).

══════════════════════════════════════════════════════════════════════
DESIGN PASS + SHIP CHECKLIST
══════════════════════════════════════════════════════════════════════

Design pass: R0 surfaces PB-1 + secondaries; saturate per project
rules; do NOT begin impl until user says "proceed."

Ship checklist (Phase 36 is code-shipping, NOT design-only — full
mechanics apply): see `[[project-mindsos-phase-34]]` for the
canonical ship-checklist shape (Phase 14a + 15b + 35 design-only
precedent does NOT apply here). Key reminders:

- Branch off `main` at HEAD = Phase 35 squash sha (recorded in
  `PHASE_35_DESIGN_LOG.md` §7 "Ship metadata" after Phase 35 ship
  completes).
- Version bump `0.0.0+phase34 → 0.0.0+phase36` (NOT `+phase35` —
  Phase 35 skipped the bump per design-only precedent). 12 sites per
  `[[feedback-docker-compose-version-bump-site]]`.
- `mindsos confirm-phase --phase 36 --notes-file notes-phase-36.md`
  per `[[feedback-confirm-phase-machine-locality]]`. Do NOT use
  `--init-notes` on populated notes file.
- Tag `phase-36-confirmed` after squash-merge per
  `[[feedback-release-tag-after-squash-merge-only]]`.

══════════════════════════════════════════════════════════════════════
FIRST RESPONSE EXPECTATIONS
══════════════════════════════════════════════════════════════════════

1. Confirm required-reading files consumed (terse list of paths; no
   content paraphrase).
2. Open Round 0 with the design PBs surfaced from your reading.
   **PB-1 MUST be the scope-shape pick (A/B/C above);** secondary PBs
   may depend on it.
3. Stop. Wait for the user's re-litigation cue
   ("I agree with all your suggestions… reanalyze...") before R1.

DO NOT begin implementation until user explicitly says "proceed"
after design saturation (typically R3-R5).

══════════════════════════════════════════════════════════════════════
before proceeding with these tasks, reanalyze the plan and list your
push backs with options.... show me your choice…. Make sure to read
all required-reading files. The load-bearing open question is the
validator-composition scope shape (A/B/C above) — that choice
determines the entire phase's deliverable surface, including whether
PHASE_MAP §36 needs an inline-amendment (B, C) or not (A).
══════════════════════════════════════════════════════════════════════
