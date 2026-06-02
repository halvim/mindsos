### Background

Phase 38 closes the L0-L3 numbered-phase rollout. Design-time picked
docs-only-shape (R3-PB-D + R5-PB-B); execution-time converted to
code-shipping per R6-PB-A — tester preferred running the canonical
`mindsos confirm-phase` wrapper rather than the design-only-precedent
PR-only ship pattern. The wrapper's doctor preflight enforces
`--phase NN` against `manifest.toml [mindsos] phase` + docker-compose
image tags; the conversion required a 12-site version bump
(`+phase36 → +phase38`) and image retag (`mindsos:phase38-{prod,test}`).
Tag `phase-38-confirmed` after PR squash-merge; release.yml runs on
the tag push.

The chat-prompt seed framed Phase 38 as "end-to-end vertical slice
with text-realm + nlu-slice + code-slice cookbooks" (PHASE_MAP §38
features line). Saturation across 6 design rounds reframed scope four
times before locking — see Design saturation below. R6 added a fifth
reversal post-design at ship-shape level.

### Design saturation

6 design rounds (R0+R1+R2+R3+R4+R5) + 1 post-design reversal round
(R6). 5 reversals total, the first four traceable to probes R0 hadn't
run, the fifth to tester preference at execution:

1. **R1-PB-A** reversed R0-PB-5 (no new "session create" verb needed;
   `mindsos server login` already exists at Phase 19, writes
   `~/.mindsos/token`). Surface narrowed from "new CLI verb (~50 LOC)"
   to "`--session-token` flag on `capacity invoke` (~10 LOC)."
2. **R2-PB-A** picked option (b) — wire `bootstrap_kl_from_falkordb`
   into `_construct_invoke_layer` to make Local-write cookbook
   persistent.
3. **R3-PB-A** reversed R2-PB-A: `local_persister.py:57-58` documents
   that Phase 25 ships only `InMemoryLocalPersister`;
   `SQLiteLocalPersister` + `FalkorDBLocalPersister` are unshipped.
   Wiring Falkor for Global doesn't fix Local-write evaporation.
   Local-write end-to-end cookbook demo deferred to L4 follow-up plan
   as a coherent unit (persister + Falkor wire-up + `--session-token`
   flag together).
4. **R3-PB-B** + **R3-PB-D** reverted R0-PB-1 + R1-PB-A: defer
   `--session-token` flag entirely; revert ship shape to docs-only at
   design-time.
5. **R4-PB-A** reversed R0-PB-3 + R2-PB-E: `mkdocs build` against
   halvim tree emits hundreds of broken-`decisions/adr/NNNN-*.md`
   cross-link WARNINGs across `concepts/*.md` + `api/*.md` pages
   because ADRs live in parent project tree per Model C. Strict-lift
   requires Model C remediation (link-strip OR `mkdocs-redirects`
   plugin OR halvim-side ADR shims) — parent-tree architectural work,
   not Phase 38 scope. Strict-lift deferred to L4/L5 follow-up plan.
6. **R6-PB-A** (post-design, mid-ship 2026-05-28) reversed R3-PB-D +
   R5-PB-B's application-to-Phase-38 — tester preferred running
   `mindsos confirm-phase` wrapper to produce `PHASE_38_CONFIRMED.md`
   as a template-parity artifact with code-shipping phases.
   Conversion required 12-site version bump + image retag. R5-PB-B's
   docs-only sub-shape definition stays valid as a future precedent;
   Phase 38 itself opts out at execution.

R5 produced impl-locks only at design-time, zero reversals — matched
the Phase 36 R5 saturation signature. R6 is the post-design reversal
captured mid-ship after the design pass had closed.

Load-bearing R0 finding: **the chat-prompt's "cookbook scope" question
was not the load-bearing question.** The real question was the
persistence state of L2 Local at the closing phase — which determines
whether cookbook prose can truthfully demonstrate Local-write
end-to-end. The answer (no) cascaded through R2/R3/R4 reversals.

### Test results

- **In-container sentinel run:** `docker compose run --rm mindsos-test
  pytest tests/phase_38/ -v` → **6 PASS in 0.11s** (zero skips).
  Sentinels: `test_capacity_deferral_anchors_updated`,
  `test_cookbook_text_realm_present`,
  `test_phase_38_page_inventory_artifact_present`,
  `test_phase_map_section_1_design_only_phase_extension`,
  `test_phase_map_section_38_inline_amendment_present`,
  `test_three_authored_pages_present`.
- **Cumulative regression:** **3379 passed / 57 skipped / 109 warnings
  in 1894.06s (0:31:34)** (Phase 36 baseline 3373/57 + 6 new Phase 38
  cases). No literal-decay from the 5-anchor edit in
  `mindsos_capacity/__init__.py`.
- **`mkdocs build`:** exits 0; warnings unchanged from Phase 36
  baseline (same Model C ADR cross-links; none introduced by Phase 38).
- **Cookbook smoke target:** the 11-step cookbook prose in
  `docs/usage/cookbook/text-realm.md` was transcribed from
  `tests/phase_32/test_integration_b.py` which is load-bearing-tested
  at Phase 32 ship (1/1 PASS in cumulative). Step 7 envelope shape +
  Step 11 audit counts (`EVT_BOOTSTRAP: 1, EVT_LOGIN: 2, EVT_LOGOUT:
  1`) reproduce against a fresh compose env.
- **`mindsos doctor --self-test`:** OK after R6-PB-A's 12-site version
  bump + image retag — manifest `phase = "38"` matches compose image
  tags `mindsos:phase38-{prod,test}` and `--phase 38` arg.

### Ship surface (halvim tree; phase-38 branch)

**Version + image (R6-PB-A; 12 sites):**

- `pyproject.toml` `version = "0.0.0+phase38"`.
- `mindsos_cli/manifest.toml` `version = "0.0.0+phase38"` + `phase = "38"`.
- `docker-compose.yml` image tags `mindsos:phase38-{prod,test}`.
- 7 package `__init__.py` `__version__ = "0.0.0+phase38"`:
  `mindsos_admin`, `mindsos_capacity`, `mindsos_cli`, `mindsos_core`,
  `mindsos_instances`, `mindsos_knowledge`, `mindsos_server`.

**PHASE_MAP edits (R3-PB-H direct edits + §inline-amendment blocks):**

- §38 — 4-clause §inline-amendment per R5-PB-A: features-line reframe,
  pass-criterion revision, §6 cookbook OOS rows, §6 Get Started +
  Concepts OOS rows. Status line updated post-R6-PB-A to record the
  docs-only → code-shipping conversion.
- §1 — 1-clause §inline-amendment per R5-PB-B: design-only-phases row
  extended with **docs-only phase** sub-shape definition. R6-PB-A
  follow-up note: Phase 38 itself opts out of the sub-shape at
  execution; the definition stays valid as a future precedent.
- §6 cookbook sub-table — 2 rows direct-revised to `**out of scope**`:
  `nlu-slice.md`, `code-slice.md`.
- §6 Get Started + Concepts sub-tables — 3 rows direct-revised to
  `**out of scope**`: `facts-and-figures.md`, `layers.md`,
  `society-of-mind.md`.
- §7 q5 + q9 + q10 — inline RESOLVED-at-Phase-38 annotations per
  R5-PB-H.

**Authored pages (R1-PB-E):**

- `docs/index.md` — rewritten from Phase 00 stub to v4 docs homepage.
  `last_confirmed_phase: 38`.
- `docs/getting-started/whats-new-v4.md` — NEW. v4 release headlines +
  layer-by-layer summary + L4/L5 carry-forward list.
- `docs/concepts/glossary.md` — NEW. ~50 terms-of-art entries
  covering L1/L2/L3/L0 vocabulary used across the docs + source.

**Cookbook (R3-PB-F + R4-PB-I):**

- `docs/usage/cookbook/text-realm.md` — NEW. 11-step prose
  walk-through; transcribes Phase 32 Integration B's ScenarioState
  with light narrative rewrite. Keeps `"the cat sat"` fixture;
  documents seed-text choice explicitly. Anchors against
  `tests/phase_32/test_integration_b.py` for smoke-stability.

**Front-matter backfill (R1-PB-F — step-0 corrected from 29-pages to 2):**

- `docs/dev/review-checklist.md` — NEW `last_confirmed_phase: 36`.
- `docs/usage/knowledge/versioning.md` — NEW `last_confirmed_phase: 17`.

**CHANGELOG backfill (R5-PB-G):**

- `docs/changelog/CHANGELOG.md` — 21 missing per-phase entries
  appended (Phases 18, 19, 20, 21, 22, 24, 25, 26a, 26b, 27, 28, 29,
  30, 31, 32, 33, 34, 35, 36, 14a, 38). Front-matter set to
  `last_confirmed_phase: 38` (R6-PB-A post-conversion form;
  `last_design_only_phase` dropped since Phase 38 ships code-shipping).
  Prior front-matter state (16 / 17) was stale relative to actual
  ship history.

**Capacity deferral anchors (R5-PB-C; step-0 corrected count 4 → 5):**

- `mindsos_capacity/__init__.py` lines 100, 111, 115, 117, 119 — five
  carry-forward bullet lines updated from "Phase 30+/32+ per Phase NN
  PB-X carry-forward" form to "deferred to L4 follow-up plan per
  Phase 38 R4-PB-D" form, with the original text preserved verbatim
  in `(was: "...")` parens for audit trail. Anchor #2
  (ProblemTraceSink) was already L4-pointing and left untouched.
  R4-PB-D's L4-deferral picks are unaffected by R6-PB-A's ship-shape
  reversal.

**Nav (R4-PB-B narrowed at step-0):**

- `mkdocs.yml` — 4 nav additions:
  1. "Get started > What's new (v4)" entry pointing at
     `getting-started/whats-new-v4.md`.
  2. "Concepts > Glossary" entry pointing at `concepts/glossary.md`
     (above existing "Identity and IRIs" row).
  3. NEW "Usage > Cookbook (Phase 38)" subsection containing the
     single "Text realm — vertical slice" entry pointing at
     `usage/cookbook/text-realm.md`.
  4. `Home: index.md` already present (rewritten not added).
- Step-0 probe revealed R4-PB-B's "fix capacity-write-flows broken
  nav + CHANGELOG orphan" premise was a false positive
  (basename-only-regex artifact). Both were already correctly
  path-qualified in nav.

**Ship artifacts:**

- `confirmation_docs/PHASE_38_PAGE_INVENTORY.md` — NEW. 7-column
  audit table (path / exists / `last_confirmed_phase` /
  `last_design_only_phase` / §6 highest / drift? / drift class)
  across 74 docs pages. Drift summary: ~12
  `amendment-history-lost` (benign convention artifact), 4
  `front-matter-newer-than-§6-mention`, 1 `amendment-not-applied`
  (`promotion-bridge.md` — Phase 24 §6-promised amendment appears
  not applied; flagged for L4/L5 verification), 1 REAL drift
  (`usage/knowledge/memories.md` exists on disk + carries
  `last_confirmed_phase: 13` but §6 says **out of scope** — flagged
  for L4/L5 reconciliation; recommended action: re-include in §6
  as Phase 13).
- `confirmation_docs/PHASE_38_DESIGN_LOG.md` — NEW. Mirrors Phase 35
  structure. §0 scope-at-chat-open, §1 required-reading consumed
  (probe inventory), §2 picks per round (R0-R5 design-time + R6
  post-design with 5 reversals enumerated inline), §3 ship surface
  with literal §inline-amendment texts, §4 19-item L4/L5 follow-up
  plan carry-forward list, §5 process notes.

**Sentinel file (R3-PB-G refined at R5-PB-D; R4-PB-C rename):**

- `tests/phase_38/__init__.py` — empty.
- `tests/phase_38/test_phase_38_doc_sentinels.py` — NEW. 6 sentinel
  functions per R5-PB-D. Filename `test_phase_38_doc_sentinels.py`
  per R4-PB-C — Phase 38 ships zero ADR amendments at design-time
  and the prior `test_adr_amendment_sentinels.py` ancestor filename
  misrepresents content. Sentinel chain semantics are per-phase, not
  per-filename — documented in module docstring.

### Ship surface (parent tree per Model C)

**Zero parent-tree changes at Phase 38** per R0-PB-6 + R0-PB-7 +
R4-PB-A (out of scope: parent-tree ADR consolidation,
`_source_backup/` retention, Model C ADR-link remediation).

### Hotfixes (none)

Zero hotfixes during ship. Step-0 probe corrected 3 design-time
miscounts before any code edit: (a) front-matter backfill scope
29 → 2 pages, (b) capacity deferral anchor count 4 → 5, (c)
mkdocs.yml nav-fix scope from "fix 3 issues" to "add 3 entries + new
Cookbook section." Each correction was caught before the
corresponding Edit ran.

One verification iteration during step-0 of Task #17 (sentinel
verification): `test_capacity_deferral_anchors_updated` flagged
stale "Phase 32+" inside the new `(was: "...")` historical citations.
Fixed by tightening the negative-anchor regex to strip `(was: "...")`
parens before searching. NOT counted as a hotfix per the
design-time-vs-impl boundary.

One post-design reversal during ship (R6-PB-A): tester preferred
running the wrapper; doctor preflight blocked on `--phase 38`
vs manifest `phase = "36"` drift; 12-site version bump performed
mid-ship to satisfy doctor parity. The five artifacts that named
"docs-only ship" / "no version bump" / "no `mindsos confirm-phase`"
(PHASE_38_DESIGN_LOG, PHASE_MAP §38 Status + §1 §am, CHANGELOG entry,
sentinel test docstring, notes-phase-38.md) were updated mid-ship to
record the conversion. NOT counted as a hotfix (it's a design-time
pick reversed at execution, not a bug fix).

### Carry-forwards to L4/L5 follow-up plan

19-item consolidated list in PHASE_38_DESIGN_LOG.md §4. Headlines:

Code surfaces (9 items): `--session-token` flag; Falkor-backed L3
bootstrap; `FalkorDBLocalPersister` (the load-bearing missing piece);
`add_type_compat` admin API + bulk rediscover; `include_deprecated`
parameter discipline; Per-user Local ProblemTraceSink dict;
`--install-builtins=<family>` CLI flag; `handle.validate_xref` body;
4 unconsumed L2 validators.

Docs surfaces (8 items): `mkdocs build --strict` lift (Model C
remediation; R4-PB-A); `nlu-slice.md` + `code-slice.md` cookbooks;
`facts-and-figures.md`; `layers.md` + `society-of-mind.md` concept
pages; per-page ADR cross-reference cleanup (~17 pages); PHASE_MAP §5
row ADR amendment-text consolidation (~15 deferrals; parent-tree-only
via Model C); `usage/knowledge/memories.md` §6 drift;
`concepts/promotion-bridge.md` Phase 24 amendment verification.

Phase-mechanics carry-forwards (2 items): per-phase `notes-phase-NN.md`
parity standardization; CHANGELOG `last_design_only_phase` convention
generalization.

### Process notes

- **Saturation pattern observation (R5-PB-I).** 4 design-time
  reversals + 1 post-design reversal across 6 rounds + 1 post-design
  round is a high reversal density. Each design-time reversal
  traceable to a probe R0 hadn't run; the post-design reversal
  traceable to tester preference overriding the design-time pick.
  Lesson for future closing-phase or layer-boundary phases: probe
  **persistence implementation status** of every type the phase
  narrative depends on; probe **current `mkdocs build` WARNING
  output** before locking strict-lift criteria; probe **current CLI
  verb roster** before proposing new verbs. AND acknowledge that
  design-time picks about ship-shape may be reversed at execution if
  the tester prefers the canonical workflow.
- **Design-time docs-only → execution-time code-shipping (R6-PB-A).**
  Design picked docs-only because Phase 38 has zero net-new runtime
  code (Phase 14a/15b/35 precedent). At ship execution the tester
  preferred the canonical `mindsos confirm-phase` workflow over the
  PR-only design-only convention. Wrapper's doctor preflight enforces
  manifest parity, which required the 12-site version bump + image
  retag. Phase 38 now ships with tag `phase-38-confirmed`, release.yml
  invocation, and template-parity `PHASE_38_CONFIRMED.md` artifact.
- **Two-machine workflow** ([[user-two-machine-setup]]): Mac for file
  edits + git + PR; Linux required for the docker test image rebuild
  + sentinel run + cumulative regression + `mindsos confirm-phase`
  wrapper invocation. Linux participation this phase: pull +
  `--no-cache` rebuild of `mindsos-test` + 6-sentinel pytest run +
  cumulative regression (~32 min) + post-R6-PB-A second rebuild for
  the `phase38` image tags + wrapper invocation.
- **Branch off main** at HEAD = Phase 36 squash sha `72ca8fc` per
  PHASE_MAP §1 "branch off `origin/main`, never off prior phase's
  branch." Branch name `phase-38`. Commit shas: `1e44152` (initial
  14-file ship) + R6 conversion commits (version bump + artifact
  reconciliation + notes-phase-38.md hand-author) + wrapper-generated
  `PHASE_38_CONFIRMED.md` commit from Linux.
- **Sentinel chain** extends `14a → 15a → 15b → 35 → 36 → 38`. Chain
  member filenames follow the pattern of the closest ancestor that
  matches each member's content
  (`test_phase_38_doc_sentinels.py` here; chain semantics are
  per-phase, not per-filename — module docstring documents this).
- **R5-PB-G CHANGELOG backfill** is the largest doc-edit in the
  ship — adds ~21 per-phase entries spanning Phase 14a through Phase
  38. Pattern: CHANGELOG.md had drifted since Phase 17's ship (last
  entry pre-Phase 38 was Phase 17 RETIRED). Each entry pulls a terse
  summary from the corresponding memory entry or
  `PHASE_NN_CONFIRMED.md`. Phase 38 entry includes the
  design-time-vs-execution-time ship-shape reconciliation note.
- **Load-bearing R3-PB-A finding** — `local_persister.py:57-58`
  ("Phase 25 ships `InMemoryLocalPersister` only") was the single
  fact that reframed the entire Phase 38 scope. Carry the lesson:
  design saturation against shipped reality must probe
  persistence-layer state explicitly when the phase narrative depends
  on persistence semantics.
