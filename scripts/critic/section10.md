
## 10. Critic close-out — §9 read; corrections to §8 owned; the hold lifts

*(critic lane, 2026-08-13, after a self-critique pass on §8 and a read of §9.
Convention kept: nothing above is edited; corrections land here, dated.)*

### 10.1 Corrections to §8, owned before anyone builds on it

1. **§8.2's table was part prediction, part demonstration, and did not say so.**
   Rows 7, 9, 10 were demonstrated by running; the other seven are predictions of
   what the sweep would catch. §9.3 has since *demonstrated* two more (Q5, Q6) —
   run by the build lane, which is the §12 discipline working as written.
2. **§8.7's attack on H1 partially boomerangs.** My grep census caught call sites
   H1's recalled list missed (`phase_1`, submind, `pipeline_runner`) — and H1's
   list caught **regimes** my census missed (replan, outage, refusal). Neither
   axis alone closes. Amended method: **surfaces = call sites × execution
   regimes, both derived from code, UNIONed with the recalled seam list, closed
   by the sentinel.** §9.3's Q5 result sharpens tier 2 the same way: a
   quantified claim must state its **domain** ("every run *given an `mm`* leaves
   a graph") — an unstated domain is how gap 7 hid, and I accept the correction.
3. **§8.4's build order over-served.** Full sweep before the renderer delays the
   demo for rows the demo never traverses. Split: **demo-critical rows** (map,
   fold, no-route, refusal, replan/retry, persistence-codec) run before the
   renderer; the rest (CLI executor, remaining submind cells — Q5 already closed
   the first) run in parallel or after.
4. **§8.4 item 1's pre-filter prediction is mooted** — the real gate ran (4731,
   §9.1). The critic's container env-baseline (failure names on `be7aa8a`) is
   archived for future name-diffs; no further claim rests on it.
5. **§8's "fix direction" sentence read as a ruling.** Two directions existed
   (route the reducer through `execute_pipeline`; or ground the dispatch in
   place). The build lane's STATE entry chose the first with its own argument —
   the hand-mint is how the member path diverged in the first place — and the
   critic concurs. Recording this so the choice is visibly theirs, not smuggled.

### 10.2 §9 accepted, one answer owed and here it is

**§9.4 — narrow §5; do not delete. Evidence, not preference:** the two tracked
coordination files are **cited by three committed confirmation docs**
(`MAPFOLD_PLANNER_OVERRIDE_E2E_CONFIRMED.md`, `CORE_CR_MAP_MEMBER_MULTIINPUT.md`,
`RESIDENT_BRAIN_RUNTIME_CONFIRMED.md` — RAN: grep at `f878886`). Deleting them
breaks committed citations; an unenforced absolute rule decays (§10.3 of RULES
knows this). So: §5 says a **live** coordination file stays untracked and lives
in the shared checkout; the two tracked ones are named as closed history frozen
where citations expect them; the closed-set is pinned by a one-line guard test
(new coordination file tracked ⟹ red) so the narrowing cannot drift.

### 10.3 The hold lifts

The critic is done for this round. In order:

1. **Close this lane**: merge #157, tag `dr-map-manifest-confirmed`, RULES §10.
2. **Next lane: `decision-records-fold-grounding`** — filed, cause known, both
   probes on record. Acceptance should include: reducer `CapacityInstance` +
   conclusion `DataStateInstance` + CONSUMES edges from member verdicts, manifest
   on the fold's graph, shown red by mutation.
3. **Then demo home + `dr_dump.py`**, dumping leaf, map **and fold** shapes.
4. **Demo-critical sweep rows** (10.1.3) before item 7; renderer requirements so
   far: per-exposure title from the start instance's value (§9.3 Q6), manifest
   phrases for kinds, `case_label` for the claim.
5. **Persistence smoke** (real Falkor, Linux) → **item 7** → Layer B. Unchanged.

§12's replacement text (§8.3) stands with 10.1.2's amendments folded in; it goes
to RULES whenever the owner wants it — the build lane should not self-adopt it
mid-lane.
