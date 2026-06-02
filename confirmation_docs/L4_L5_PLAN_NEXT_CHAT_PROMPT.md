# L4 + L5 FOLLOW-UP PLAN — NEXT CHAT PROMPT (R0 seed)

> **SUPERSEDED 2026-06-02 by Chat C plan-authoring closure.**
> The active plan is `confirmation_docs/POST_PHASE_38_PHASE_MAP.md` (Phases 39-49, 4-rail DAG).
> All 11 R0 PBs in this file are resolved — see `HANDOFF.md §6.2` and `confirmation_docs/POST_PHASE_38_PHASE_MAP.md §1` for the resolutions.
> This file is retained for forensic / origin-record purposes only. Future chats should NOT use this as a chat seed; use `POST_PHASE_38_PHASE_MAP.md` per-phase rows instead.

> **Read `MindsOS/HANDOFF.md` FIRST.** It is the canonical entry point
> and contains the current state of MindsOS as of 2026-05-28. This file
> is the design-resolution seed that picks up after HANDOFF §3 + §6.
>
> Captured 2026-05-28 at the close of the post-Phase-38 housekeeping
> chat. The R0 slate below is inheritable by the next plan-design chat.
> The chat that captured this slate did NOT complete plan-authoring —
> it opened Round 0 with 11 PB candidates and stopped. Post-housekeeping
> the folder structure and provenance are settled; the design saturation
> picks up from the slate below.

══════════════════════════════════════════════════════════════════════
NEW CHAT — L4 + L5 follow-up plan design (post-housekeeping)
══════════════════════════════════════════════════════════════════════

You are running the L4/L5 follow-up plan design chat. Your goal is
to produce a phased rollout plan analogous to PHASE_MAP.md (the
L0-L3 plan) but covering: L4 (Intelligence) + L5 (Mental Model) +
FOL placement + the 19-item carry-forward backlog inherited from
Phase 38 ship.

Project rules apply: skeptical reviewer, picks-per-pushback,
alternatives format, re-litigation cue, saturate before impl, no
filler, alternatives without recommended pick by default,
deep-analysis-only-on-request.

══════════════════════════════════════════════════════════════════════
REQUIRED READING — read in this order, BEFORE drafting R1
══════════════════════════════════════════════════════════════════════

**Canonical closing state of L0-L3:**

1. `confirmation_docs/PHASE_MAP.md` §1 (settled cross-cutting
   decisions; design-only-phase + docs-only-phase sub-shape
   extensions) + §5 "Phase 38" row (Status + 4-clause §inline-amendment)
   + §6 "Doc-to-phase map" (out-of-scope rows) + §7 "Open questions"
   (q5/q9/q10 RESOLVED annotations).
2. `confirmation_docs/PHASE_38_DESIGN_LOG.md` — full; §2 picks per
   round (R0-R5 design-time + R6 post-design; 5 reversals enumerated)
   + **§4 19-item L4/L5 follow-up plan carry-forward list
   (LOAD-BEARING — this is your starting backlog)** + §5 process notes.
3. `confirmation_docs/PHASE_38_PAGE_INVENTORY.md` — drift discussion;
   1 non-benign drift (`usage/knowledge/memories.md`) + 1
   amendment-not-applied (`concepts/promotion-bridge.md`) + ~17
   amendment-history-lost benign rows.
4. `confirmation_docs/PHASE_38_CONFIRMED.md` — ship metadata +
   tester_notes; ship-mechanics context.

**L4/L5 design context (post-housekeeping locations):**

5. `docs/dev/l4_intelligence_design_notes.md` — L4 conceptual design.
6. `docs/dev/l5_mental_model_design_notes.md` — L5 conceptual design.
7. `docs/dev/use_cases_text_realm.md` — NLU + code use cases (referenced
   by both L4 and L5 design notes + by FOL/WSD chats).
8. `MindsOS/HANDOFF.md` §3 (L4 settled vs contested) + §4 (L5 design
   state) — the canonical post-housekeeping summary; the diagnostic
   that the deleted `mindsos_l4_session_handoff_2026-04-25.md` used to
   provide is absorbed into HANDOFF.md §3.

**The 7 L4 critique pushes are pending acceptance.** No L4 code has been
written. HANDOFF §3.2 lists the 7 with original-vs-critique columns;
ratification is this chat's load-bearing work.

**Memory entries:**

- `[[project-mindsos-phase-38]]` — closing-phase ship details + R6
  reversal pattern + B-38-T1 hotfix.
- `[[project-mindsos-l4-design]]` — L4 architecture sketch from a
  prior chat (2026-04-22 — predates the 2026-04-25 critique).
- `[[project-mindsos-architecture]]` — 5-layer overview.
- `[[reference-mindsos-layer-handoffs]]` — current paths to L0/L1/L2/L3/L4
  handoff docs.
- `[[feedback-wrapper-parity-vs-docs-only-ship]]` — Phase 38 R6 lesson.

══════════════════════════════════════════════════════════════════════
R0 PUSHBACK SLATE (DRAFTED 2026-05-28 — INHERIT AS R0 OR REDRAFT)
══════════════════════════════════════════════════════════════════════

The prior chat opened R0 with these 11 PB candidates after consuming
required reading + probing shipped reality. Each has my pick from
that chat; treat as inheritable R0 unless the next chat redrafts.

The next chat should start by either:
  (i) accepting the slate as-is and going straight to R1, or
  (ii) re-opening any subset for re-litigation (e.g., persistence
       probe may have changed if MindsOS shipped Falkor persisters
       in the interim), or
  (iii) redrafting from scratch with new probes.

----------------------------------------------------------------------
### R0-PB-1 — Plan vs design-resolution. (Probe-derived; load-bearing.)

**Concern.** The chat-prompt assumes "produce a phased rollout plan
analogous to PHASE_MAP.md." But L4's
`mindsos_l4_session_handoff_2026-04-25.md` says **seven critique pushes
are pending acceptance** and **"No L4 code has been written. The open
critique items must be resolved first."** You cannot phase a plan whose
foundation is contested. Phase 38 R3-PB-A class repeats here: locking
a plan against an unshipped/unsettled foundation.

**Pick:** (b) — open this chat as a **design-resolution pass on the 7
pushes + L3/L4 boundary** before any phased-plan authoring. The
plan-authoring stage starts only after those resolve.

- **(a) Phase the design as-is.** Treat 2026-04-22 handoff as locked;
  ignore the 2026-04-25 critique. Pros: fastest to a PHASE_MAP. Cons:
  high probability of mid-plan reversals; the L4 designer is on record
  saying the design is contested.
- **(b) Design-resolution first; phasing second.** Resolve 7 pushes +
  L3/L4 boundary in this chat. Then a follow-up chat authors the
  phased plan. Pros: phase plan is built on settled foundation. Cons:
  this chat may close without a PHASE_MAP file.
- **(c) Hybrid — phase only the uncontested L4 surface (e.g., Mental
  Model L5 substrate + L4 persistence prereqs), defer the contested
  L4 orchestrator to a v2 plan.** Pros: ships something. Cons: L5
  retention depends on L4-writes, so "uncontested L5" is mostly empty.

----------------------------------------------------------------------
### R0-PB-2 — Carry-forward scope absorption.

**Concern.** "19-item L4/L5 carry-forward backlog" is named as
inherited. But the 19 items split into 3 classes of very different
shapes: (A) L4-blocking persistence work (`FalkorDBLocalPersister`,
Falkor-backed L3 bootstrap, `--session-token` flag) — these are **L0
substrate**, not L4 features; (B) L3 surface gaps (`add_type_compat`,
`include_deprecated`, `validate_xref` body) — these are **L3 cleanup**,
not L4; (C) docs/mechanics (Model C, CHANGELOG, page drift) — these
are **cross-cutting**, not layer-scoped. Treating all 19 as "L4/L5
plan" mis-shapes the plan.

**Pick:** (c) — split the 19 into 3 streams. L0/L3 cleanup ships as
bug-fix PRs against `main` (out-of-band of any phase); L4/L5 substrate
prerequisites become the plan's Phase 39-4N opener (Falkor persisters
+ cross-layer rewrite handler); docs/mechanics ship under a separate
"closing-phase docs sweep" mini-plan.

- **(a) Absorb all 19 into the L4/L5 plan.** Pros: single backlog,
  one plan-of-record. Cons: plan-shape distorted by non-L4 work;
  persistence-substrate phases buried in "L4 plan."
- **(b) Carry-forwards become independent bug-fix PRs; plan is pure
  L4/L5.** Pros: clean L4/L5 plan. Cons: persistence carry-forwards
  are actual L4 blockers; ignoring them invites Phase 38 R3-PB-A
  again.
- **(c) Three-stream split.** Pros: each stream gets a workflow
  appropriate to its scope. Cons: more bookkeeping.

----------------------------------------------------------------------
### R0-PB-3 — L4 vs L5 ordering.

**Concern.** L5 design notes §3.4 (2026-04-26 amendment): **"L5 v1
ships gated on the v2 note-fork mechanism landing. L5 cannot ship a
coherent retention model without it."** The note-fork is unshipped
and is itself **server-pivot v2** scope. So L5 isn't just downstream
of L4 — it's downstream of an unshipped L0 feature. Naive "L4-then-L5"
sequencing hides this.

**Pick:** (c) — L4 first, but L5 is **gated on note-fork** (which
itself becomes a prerequisite phase or is rejected via design pick on
§3.4 Option B/C). Plan structure: L4 phases land first; L5 phases
wait on note-fork ship; if note-fork is rejected, L5 retention model
is redesigned before L5 ships.

- **(a) L4 then L5 sequentially.** Pros: clean order. Cons: L5 ships
  in a vacuum if note-fork doesn't land.
- **(b) Interleave L4 + L5.** Pros: L5 substrate validates against
  L4 writes early. Cons: L5 retention contract not stable until
  note-fork decision; rework risk.
- **(c) L4 first; L5 gated on note-fork decision (resolve §3.4
  first).** Pros: makes the gating explicit; forces a pick on Option
  A/B/C from L5 notes §3.4. Cons: introduces an L0 prereq into the
  L4/L5 plan.

----------------------------------------------------------------------
### R0-PB-4 — FOL placement.

**Concern.** PHASE_MAP §7 q8 left FOL with "default = clean defer."
The L4 design notes show FOL has already shaped L2 role-graphs
(`sense-correlations`, `learned-parameters` added 2026-04-23 *from
FOL Layer design*). FOL has tendrils already; "abandon" is no longer
clean.

**Pick:** (b) — L4/L5 plan ships **without** FOL phases, but the L4
plan's L2-role-graph additions either ship
`sense-correlations`/`learned-parameters` (if L4's WSD + coherence
consumers are in v1 scope) or formally drop them with FOL.

- **(a) Absorb FOL into this plan as Phase L4-NN+.** Pros: complete
  coverage. Cons: FOL is its own multi-month design.
- **(b) Plan is L4 + L5 only; FOL stays deferred; settle the 2
  FOL-implied role-graphs.** Pros: scope bounded. Cons: 2 role-graphs
  need disposition decision now.
- **(c) FOL as a sibling follow-up plan (L6 plan).** Pros: orthogonal
  scopes. Cons: pre-commits to FOL existing — premature.
- **(d) Formally abandon FOL.** Pros: cleanest. Cons: drops a design
  direction without final-pass review.

----------------------------------------------------------------------
### R0-PB-5 — Phase numbering.

**Concern.** Minor mechanics, but Phase 38 closed L0-L3, and
continuing "Phase 39 …" mixes the L0-L3 closed plan with the new
L4/L5 plan. Tooling (`mindsos confirm-phase --phase NN`, CI workflow
phase-regex, manifest `[mindsos] phase` literal, the 12-site
version-bump script, sentinel chain) all assume monotonic integer
phase numbers within a single plan.

**Pick:** (a) — continue from Phase 39 (least tooling work). Add a
new `[mindsos_plan]` field to `manifest.toml` distinguishing
`l0_l3` vs `l4_l5` if collisions arise.

- **(a) Continue Phase 39+.** Pros: zero tooling changes. Cons:
  visually mixes plans.
- **(b) Reset to Phase L4-00.** Pros: scopes the new plan
  explicitly. Cons: every confirm-phase / CI workflow / sentinel
  test / manifest field needs regex update; 12+ touch points.
- **(c) Decimal / split namespace (e.g., 39.0, 39.1).** Pros: clean
  version comparison. Cons: ditto (b) regex pain.

----------------------------------------------------------------------
### R0-PB-6 — Sentinel chain disposition.

**Concern.** `14a → 15a → 15b → 35 → 36 → 38` is the L0-L3-closing
sentinel chain. Extending it into L4/L5 phases means every L4 phase
becomes a chain link with backward-flip cost. Starting a new chain
(`L4-00 → L4-…`) decouples but may lose useful regression coverage.

**Pick:** (b) — start a new chain for L4/L5 phases; the Phase 38
chain is closed-class.

- **(a) Extend `…38 → 39 → 40 → …`.** Pros: continuous evidence
  trail. Cons: each new link requires a sentinel test that flips a
  Phase 38 assertion; growing fragility.
- **(b) New chain rooted at L4's first design-only phase.** Pros:
  scope-clean. Cons: a future audit cross-checks both chains.
- **(c) No chain for L4/L5.** Pros: simplest. Cons: drops a
  regression-evidence convention.

----------------------------------------------------------------------
### R0-PB-7 — Cookbook gaps (`nlu-slice.md` + `code-slice.md`).

**Concern.** Both OOS'd at Phase 38 R0-PB-2 because no `nlu` or
`code` builtins shipped at L3. The L4/L5 plan likely ships an
orchestrator demo. PB: does it ship those cookbooks (which forces
nlu + code builtin capacity authoring) or do they stay OOS permanently?

**Pick:** (b) — ship them only if L4's orchestrator demo *uses* nlu
or code builtins as load-bearing examples. Otherwise leave OOS.

- **(a) Authoring those cookbooks is mandatory L4/L5 scope.**
- **(b) Conditional — author iff L4 demo uses them.**
- **(c) Permanently OOS.**

----------------------------------------------------------------------
### R0-PB-8 — Model C remediation timing.

**Concern.** Strict-lift deferred to L4/L5 per R4-PB-A. 121
`decisions/adr/NNNN-*.md` cross-link occurrences in halvim docs.
Real question: does Model C itself stay (split halvim docs + parent
ADRs) or get unified (halvim becomes self-contained)?

**Pick:** (a) — Model C stays; remediation is a single dedicated
phase (recommended approach β from PHASE_38_DESIGN_LOG §4 item 10 =
`mkdocs-redirects` plugin with path-prefix redirect to parent tree).

> **NOTE (2026-05-28 housekeeping, confirmed by build probe):** This PB
> is **substantially moot**. Housekeeping copied parent-tree ADRs +
> L4/L5 design notes INTO the MindsOS docs tree. Build probe:
> `mkdocs build --site-dir /tmp/probe` emits **50 warnings, all the
> same class** — summary pages link to short-form ADR filenames (e.g.,
> `0022-batched-writes.md`) while actual filenames have descriptive
> suffixes (`0022-batched-writes-via-unwind.md`). Six summary pages
> affected: `decisions/summary/{core,knowledge,server,capacity,intelligence,cross-layer}.md`.
> Scope: ~50 link rewrites across 6 files — filename normalization,
> not architectural Model C work. Recommend folding into a mini-phase
> alongside strict-lift, not treating as a separate decision. R0-PB-8
> pick should default to (a) but with much smaller scope estimate.

- **(a) Discrete remediation phase using `mkdocs-redirects` (β).**
- **(b) Strip ADR cross-links across ~30 pages (α).**
- **(c) halvim-side ADR shim pages with `external_url` (γ).**
- **(d) Unify the trees (parent ADRs move to halvim).**

----------------------------------------------------------------------
### R0-PB-9 — `sense-correlations` + `learned-parameters` disposition. (Probe-derived.)

**Concern.** Both L2 role-graphs are named in L4 design notes (added
2026-04-23 from FOL design) but neither has a `ROLE_*` constant in
`mindsos_knowledge/identifiers.py` or a schema file in
`mindsos_knowledge/schemas/`. They are L4 writer-targets that L4 v1
may need; if FOL is deferred (R0-PB-4) they may be unneeded.

**Pick:** (c) — defer both. Add a §inline-amendment to L4 design
notes recording the deferral. Reopen if/when WSD or coherence
consumer enters scope.

- **(a) Ship both as part of plan.**
- **(b) Ship `learned-parameters` only.**
- **(c) Defer both with a §am to design notes.**

----------------------------------------------------------------------
### R0-PB-10 — Single-tenant vs multi-tenant L4 scope.

**Concern.** L4 handoff §11 (2026-04-26 update): **"Cross-layer
rewrite handler for L4 = v2.** When alice's draft node is promoted,
the v1 system rewrites refs in KL and Capacity. L4 process-state
refs to drafts won't be rewritten until L4 ships its handler." So L4
v1 has a known multi-tenant correctness gap on promotion.

**Pick:** (b) — L4 v1 single-tenant only. The L4 rewrite handler
ships in an L4-v2 follow-up; this plan ends at L4-v1.

- **(a) L4 v1 ships multi-tenant from the start.**
- **(b) L4 v1 single-tenant; L4-v2 handler is a sibling follow-up.**
- **(c) Block plan on rewrite handler shipping first.**

----------------------------------------------------------------------
### R0-PB-11 — Ship-shape default (docs-only-precedent vs code-shipping).

**Concern.** Phase 38 R6 lesson is fresh: design-time picked
docs-only, execution-time reverted to code-shipping. The L4/L5 plan
has 2-4 likely design-only phases (resolution of 7 pushes; FOL
formal-decision; L3/L4 boundary review).

**Pick:** (a) — at R0 of each design-only-candidate phase in the new
plan, explicitly surface "design-only vs code-shipping" as a
load-bearing PB; **and** at design-time, picking docs-only requires
explicit tester confirmation per
`[[feedback-wrapper-parity-vs-docs-only-ship]]`.

- **(a) Per-phase explicit ship-shape PB at R0.**
- **(b) Default to code-shipping always.**
- **(c) Default to docs-only when no src changes.**

══════════════════════════════════════════════════════════════════════
LOAD-BEARING R0 FINDING — probe persistence reality first
══════════════════════════════════════════════════════════════════════

`mindsos_server/persistence/local_persister.py:57-58` documents:

> Phase 25 ships `InMemoryLocalPersister` only.
> `SQLiteLocalPersister` + `FalkorDBLocalPersister` land at the
> first user-Local-write phase.

This is the load-bearing fact that cascaded Phase 38 R2 → R3 →
R4 reversals. **Re-probe at R0 of the next chat** to confirm
whether persistence has landed since:

```
grep -rn "FalkorDBLocalPersister" mindsos_server/persistence/
grep -rn "SQLiteLocalPersister" mindsos_server/persistence/
```

Also probe CLI verb roster + current `mkdocs build` WARNING count +
ADR file inventory at `docs/decisions/adr/`.

══════════════════════════════════════════════════════════════════════
FIRST RESPONSE EXPECTATIONS
══════════════════════════════════════════════════════════════════════

1. Confirm required-reading files consumed (terse paths list).
2. Run the persistence + CLI + ADR probes named above.
3. EITHER inherit the R0 slate above as-is, OR re-open any subset for
   re-litigation, OR redraft from scratch (cite probe deltas
   justifying redraft).
4. Stop. Wait for user re-litigation cue ("I agree with all your
   suggestions… reanalyze...") before R1.

DO NOT begin plan-authoring (no L4/L5_PLAN_MAP.md drafting) until
user says "proceed" after design saturation (typically R3-R5).

══════════════════════════════════════════════════════════════════════
PROCESS NOTES INHERITED FROM PHASE 38
══════════════════════════════════════════════════════════════════════

- **Probe-first.** 4 of Phase 38's 5 reversals were traceable to
  probes R0 didn't run. Probe persistence-layer state +
  `mkdocs build` WARNING count + CLI verb roster + ADR inventory
  before locking R0 picks.
- **Tester ship-shape preference may override design-time picks.**
  Phase 38 R6 lesson per
  `[[feedback-wrapper-parity-vs-docs-only-ship]]`. At R0 of any
  docs-only-leaning phase, surface ship-shape as explicit PB.
- **Sentinel chain semantics are per-phase, not per-filename.**
  Filename pattern follows closest ancestor matching content.
- **Saturation pattern (Phase 36 + Phase 38 R5):** R5 produces
  impl-locks only, zero reversals — that's the signature of a
  ready-to-ship design pass.

══════════════════════════════════════════════════════════════════════
HOUSEKEEPING CONTEXT (2026-05-28) — COMPLETED
══════════════════════════════════════════════════════════════════════

The post-Phase-38 housekeeping completed 2026-05-28. As of this writing:

- `Layered Intelligence/` parent tree archived as
  `_archive_Layered_Intelligence/` under `Projects/`.
- `halvim_mindsos/` renamed to `MindsOS/` as the new Cowork project root.
- Parent-tree Model C anchors absorbed into MindsOS:
  - 144 ADRs at `MindsOS/docs/decisions/adr/`
  - L4 + L5 design notes at `MindsOS/docs/dev/`
  - `use_cases_text_realm.md` at `MindsOS/docs/dev/`
- 5 archive handoffs + 2 already-extracted handoffs consolidated into
  `MindsOS/HANDOFF.md` (originals stay in archive for forensics).
- 3 sister-project intake at `MindsOS/projects/` (DWF, WSD, FOL).
- Test code-breaking refs to parent-tree paths fixed (14 files
  switched from `_REPO_ROOT.parent / "docs"` to `_REPO_ROOT / "docs"`).
- Build artifacts + Phase 04 release tarball cleaned from root.
- Notes-phase-NN.md moved to `confirmation_docs/notes/`.

**Re-probe the filesystem at chat-open** to verify state. See HANDOFF.md
§7.3 for the canonical folder structure.

══════════════════════════════════════════════════════════════════════
*End of L4_L5_PLAN_NEXT_CHAT_PROMPT.md*
