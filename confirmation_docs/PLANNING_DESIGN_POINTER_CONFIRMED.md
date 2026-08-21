# Planning-design pointer — CONFIRMED

**Branch:** `fix/planning-design-pointer` · **Tag:** `planning-design-pointer-confirmed`
**Date:** 2026-08-21 · **Scope:** core (`mindsos_*` docstrings + `docs/` + one guard). No
behaviour change; no capacity, schema or interface is added, removed or altered.

---

## 1. What this ship is for

On **2026-08-20** the Decision Records lane asked how an input (an email, as text) enters
MindsOS and how the system decides what to do with it. It searched the tree thoroughly and
answered, with `file:line` evidence:

```
mindsos_intelligence/phase_1.py:259-262
process → hint → derive_goal → map   →   plan_construction.build
```

That answer was **shipped, coherent, Accepted by ADR-0172 — and one design generation out of
date.** The lane acted on it. The current design is **ADR-0206**, whose §3 states the steps as
`request → hint → map → plan` with *plan* a loop (`search → find → decompose → repeat`), whose
§4 retires `MAX_DEPTH`, and whose §8 deletes the thirteen `placeholder=True` capacities.

**The shape of the failure.** The tree held a complete, coherent, superseded design with
`Accepted` status and shipped code, and a current design that was `Proposed`, unbuilt, and
mentioned nowhere the superseded one was. Reading the code carefully produced the wrong answer
with full confidence. Status alone pointed the wrong way: ADR-0172 is `Accepted`, ADR-0206 is
`Proposed`.

**This ship does not build the planning loop.** That is CORE-C4 and it is large. This ship
makes the tree stop pointing a reader at the old design.

## 2. The five wrong conclusions, and where each is now closed

| Wrong conclusion | Why it looked right | Closed by |
|---|---|---|
| "The current interpret flow is `process → hint → derive_goal → map`." | It is what `phase_1.py:259-262` does, it is what ADR-0172 says, and ADR-0172 is `Accepted` while ADR-0206 is only `Proposed`. | ADR-0172 ⚠ note + §amendment-2; `phase_1.py` docstring; the two concept-doc banners; guard claim 1. |
| "`derive_goal` produces the goal, and the demo should supply a real one." | `derive_goal` is a real dispatch with a real DataState and nothing near it says it is being designed out. | `phase1_v0.py`, `phase1_profile.py`, `phase1_text.py`, `boot.py` each now say the step is **deleted**, not unimplemented. |
| "`goal` is computed and then discarded — a defect to work around." | True of the code: `plan_construction.build` is called without it (`orchestrator.py:321-324`) and nothing reads it. | `phase1_v0.py` + `task-lifecycle.md`: the right reading is *"this step is being deleted"*, not *"this step is broken"*. |
| "`RequestPattern -DECOMPOSES_INTO-> SubgoalTemplate` is the decomposition mechanism." | Declared in `mindsos_knowledge/schemas/request_patterns.py:18,28` with an IRI builder at `mindsos_knowledge/identifiers.py:271`. | `request_patterns.py` docstring: zero writers, zero readers, **not** the mechanism; retired by CORE-C2R7. |
| "The orchestrator's `while True:` is the planning loop." | It loops (`orchestrator.py:375-447`) and it is called *replan*. | `orchestrator.py` docstring: `build` is called **once**, at `:321`, outside the loop; the loop re-executes the same `plan_result` and never rebuilds a plan. |
| "`docs/concepts/planning.md` documents the current design." | Published, on the mkdocs site, reads as authoritative. Dated 2026-06-09; describes lazy DFS with `MAX_DEPTH = 3` — the placeholder architecture ADR-0206's own Context indicts. | Retitled, bannered, and the retired section marked; guard claim 1 keeps it that way. |

## 3. Verified against the tree, 2026-08-21

Re-checked, not inherited from the handoff prompt.

| Claim | Verdict |
|---|---|
| ADR-0206 — `Proposed`, 2026-07-31, amendment-1 `Accepted`, layer L4, 354 lines | ✅ |
| ADR-0205 abstraction levels — `Accepted` | ✅ |
| ADR-0172 — `Accepted`, no `superseded_by`, **not referenced by 0206** | ⚠ **half wrong.** `Accepted` and no `superseded_by` ✅ — but ADR-0206's front-matter `related:` **does** list `0172`, and its Related prose names it. The reference existed; it was one-directional and labelled `related`, which carries no revision semantics. |
| ADR-0206's reference to ADR-0172 reads "(lifecycle phases)" | ⚠ **mislabelled** — lifecycle phases is ADR-0171. Corrected in this ship. |
| ADRs 0104, 0105 superseded by 0173; 0106 by 0172; 0107/0108 deferred; `mindsos_capacity/builtins/planners/` absent | ✅ |
| The 13 L4 capacities all `placeholder=True` — 4 in `planning_v0.py`, 4 in `phase1_v0.py`, 5 in `orchestration_v0.py` | ✅ (13 registration sites; 16 raw `placeholder=True` matches, 3 of them prose) |
| `planning.decompose` → `[]`; `planning.is_leaf` → `True`; `decision.should_replan` → continue; `predicate.sufficient` → True | ✅ |
| `MAX_DEPTH = 3` at `plan_construction.py:28`; ADR-0206 §4 retires it | ✅ |
| `_decompose_recursive` at `plan_construction.py:352-367` terminates on the first call, every time | ✅ — `is_leaf` returns `True`, so `depth` never reaches `MAX_DEPTH`. |
| `request_knowledge`, `MilestoneRun`, `planning.search`, `planning.find`, `decision.select_decomposition` — zero hits | ✅ |
| C4 build queue — `CORE_RECONCILIATION_PLAN.md` §5, none started | ✅ — but the items are **C4R1–C4R8**, not C4R1–C4R8 *plus C4R9*; see finding F2. |
| `phase_1.py` steps at `:249-262` | ⚠ they are at **`:259-262`**. |

## 4. What changed

**ADR marking — RULES §9's prescribed shape, not a new field.**

- `docs/decisions/adr/0172-…md` — stays `Accepted`. Gains a ⚠ blockquote under its Related
  line and **§amendment-2** carrying `**Amendment status:** Proposed`, with the clause-by-clause
  table, the reasons the status is not `Superseded`, and **the flip list** (the five sites that
  change when ADR-0206 becomes `Accepted`, so that flip is one commit).
- `docs/decisions/adr/0206-…md` — gains `amends: [0172]` in front-matter (the tree's own
  machine-readable word for this; 33 ADRs use it) and its mislabel is corrected. **No status,
  decision or substance of ADR-0206 is touched.**
- `docs/decisions/superseded.md` — a row in the existing *Amendments in flight* table.

*Why not `Superseded`.* ADR-0206 does not wholly replace ADR-0172: §2 (Method δ) is **not named
anywhere in ADR-0206** — it contains no "Method δ", no "HintSet", no "MappingResult" — and
§1's step-5 internals are reframed rather than retired. Beyond substance, ADR-0206 is
`Proposed` and unbuilt, so flipping ADR-0172 today leaves **no `Accepted` ADR describing the
code that runs**; the tree's precedent is to flip on ship (ADR-0007: *"2026-05-22 — Phase 24
ship … close the supersession in code"*, ADR-0037). And the flow is jointly owned by ADR-0195
and ADR-0197, both `Accepted` and shipped, neither superseded by ADR-0206 — ADR-0197 is not
even in its `related:` list.

**Published docs.** `docs/concepts/planning.md` (retitled to name itself the shipped v0
catalog, bannered, retired section marked, and the WSD-ownership sentence corrected —
`RULES.md` §8), `docs/concepts/task-lifecycle.md` (banner + four inline corrections),
`docs/dev/internals/phase1-ingress.md` (banner), `docs/dev/l5_mental_model_design_notes.md`
(two inline notes). Banners are **blockquotes, not `!!!` admonitions** — see finding F4.

**Code, where a reader lands.** `phase_1.py`, `plan_construction.py` (docstring + the
`MAX_DEPTH` constant + `_decompose_recursive`'s new docstring), `orchestrator.py`,
`phase_6.py`, `phase1_profile.py`, `planning_v0.py`, `phase1_v0.py`, `orchestration_v0.py`,
`phase1_text.py`, `identifiers.py`, `boot.py`, `request_patterns.py`.

**One guard.** `tests/architecture/test_retired_design_pointer.py` — see §5.

## 5. The guard

Two claims, both over a **domain derived by scan at test time**, never a recalled file list:

1. every file under `mindsos_*/**/*.py` ∪ `docs/**/*.md` naming a retired-design token
   (`derive_goal`; plan-level `MAX_DEPTH`) must also name `ADR-0206`;
2. every `CORE-C4Rn` cited in that domain must exist in `CORE_RECONCILIATION_PLAN.md` §5.

Excluded, each exempting real files and each held to that by
`test_exclusions_are_load_bearing`: `docs/decisions/adr/**` (an ADR is a dated record;
`about.md` says do not rewrite it — ADR-0172 carries its pointer as an amendment instead) and
`docs/_workbench/**` (not in `mkdocs.yml` nav, not published).

**Mutations observed RED before the ship** (RULES §12): `MAX_DEPTH = 3` alone → reported;
`Cold-start max-depth is 3` alone → reported; `decision.derive_goal` alone → reported; each
cleared by adding `ADR-0206`. `CORE-C4R99` → reported; `CORE-C4R7` → clean.
`FIND_MAX_DEPTH_EXCEEDED` and the finder's `--max-depth` flag are **not** dragged in
(`test_the_finder_max_depth_is_not_dragged_in`). Self-disarming is pinned by
`test_scan_is_not_empty` and `test_c4_section_declares_the_items`.

**After the ship, on the branch: claim 1 = 0 violations, claim 2 = 0 dangling** over 348
scanned files; both exclusions load-bearing (`docs/decisions/adr/**` exempts 3 real files,
`docs/_workbench/**` exempts 2). `tools/check_adr_status_consistency.py` exits 0 — 211 ADRs,
all statuses consistent across file, README and summaries.

**Run against `main` before the ship, claim 1 was red on 11 sites** — the exact size of the
hole: `phase1_text.py`, `phase1_v0.py`, `phase1_profile.py`, `phase_1.py`, `boot.py`,
`planning.md` , `task-lifecycle.md` (×2), `phase1-ingress.md`, `l5_mental_model_design_notes.md`
(×2). Claim 2 was red on 4.

**Two guards were costed and refused, on measurement, not taste.**

- *"every `Accepted` ADR revised by a `Proposed` one carries a cross-reference in both
  directions."* The tree already has the field (`amends:`, 33 ADRs, 36 pairs) and **19 of the
  36 pairs have no back-pointer today** — red on nineteen other lanes' ADRs on the day it is
  written. It also could not have caught this failure: ADR-0206 never declared that it revised
  ADR-0172, and a symmetry check has nothing to check until someone declares it. Filed as F5.
- *"every `placeholder=True` capacity is named in the ADR that retires it."* ADR-0206 §8
  deletes thirteen and names eight; `planning.derive_initial_plan`,
  `planning.aggregate_outputs`, `decision.signal_to_tier`, `scoring.attention_score` and
  `phase6.attribute_blame` are unnamed. Greening it means editing a `Proposed` ADR's substance
  — CORE-C4's work, not a docs-hygiene lane's.
- The third candidate — *"concept docs whose subject has a newer ADR carry a pointer to it"* —
  is not mechanically derivable ("whose subject has a newer ADR" has no machine form). Claim 1
  **is** the derivable form of that idea, keyed on retired vocabulary instead of on subject.

**What the guard cannot do,** stated so no one mistakes it for more: it cannot notice that a
new design has superseded an old one. That judgement is a human act and `RULES.md` §9 is where
it is recorded. This guard enforces the consequence once the pair is declared. Extending it is
one row in `RETIRED`.

## 6. Findings and dispositions (RULES §12.4)

| # | Finding | Disposition |
|---|---|---|
| F1 | `derive_goal`'s output is computed and read by nothing — but it is **not** a defect: ADR-0206 §3 deletes the step. | **Fixed in this ship** (docstrings + §amendment-2 say which reading is right). |
| F2 | **`CORE-C4R9` has never existed.** `CORE_RECONCILIATION_PLAN.md` §5 declares C4R1–C4R8; C4R9 was cited in `identifiers.py:112`, `orchestration_v0.py:19`, `phase_6.py:6`, `orchestrator.py:11`. `planning_v0.py` (C4R4) and `phase1_v0.py` (C4R8) were misrouted against the same table. | **Fixed in this ship** and **guarded** (claim 2). |
| F3 | ADR-0206's only reference to ADR-0172 is mislabelled "(lifecycle phases)" — that is ADR-0171. | **Fixed in this ship.** |
| F4 | **`!!!` admonitions do not render on the published site.** `mkdocs.yml` has no `markdown_extensions:` block at all, so `about.md`, `proposed.md` and several ADRs emit `!!! info` / `!!! warning` as literal paragraph text — `site/decisions/about/index.html:588` is `<p>!!! info "Quick facts"`. | **Filed** as `mkdocs-admonitions-unrendered`. Not fixed: site config, and enabling the extension changes rendering across the whole site. This ship uses blockquotes. |
| F5 | **19 of 36 declared `amends:` ADR pairs have no back-pointer.** | **Filed** as `adr-amends-backpointer-gap`. Guard refused on cost (§5). |
| F6 | `SubgoalTemplate` / `DECOMPOSES_INTO` / `PREREQUISITE_OF` are dead schema — zero writers, zero readers. | **Documented in this ship**; deletion stays **CORE-C2R7** (an L2 role-schema change with a migration). |
| F7 | The orchestrator's `while True:` is a **re-execution** loop wearing the word *replan* — `plan_construction.build` runs once, outside it. | **Fixed in this ship** (orchestrator docstring). |
| F8 | **The subsystem-ownership guard is blind to docs.** `tests/architecture/test_no_subsystem_ownership.py` scans `mindsos_*/**/*.py` only, so `docs/concepts/planning.md` and `task-lifecycle.md` could say WSD installation replaces the core v0 catalogs — a RULES §8 ownership claim — and stay green. | **The two pages are fixed in this ship.** The domain gap is **filed** as `ownership-guard-docs-blind`: 29 `docs/` files mention "WSD installation" and most are legitimate future-work owner columns, so extending the guard needs a triage this lane did not do. |

| F9 | `execution.py:125` and `plan_construction.py:160` defer to **CORE-C4R4** while describing *real decomposition* and *parallel siblings*, which are **CORE-C4R3** and **CORE-C2R6**; C4R4 is *lazy descent in the MM*. | **Filed** as `c4r4-cited-where-c4r3-is-meant`, deliberately **not fixed**. These citations *resolve*, so they are not the dangling class the guard catches and that C4R9 was. Re-routing them is a judgement about item semantics that belongs to whoever owns CORE-C4, not to a docs-pointer lane. Recorded rather than silently changed. |

## 7. Cost named — does this make ADR-0206 harder to change?

Yes, by five sites, and they are listed in one place so the bill is legible: ADR-0172
§amendment-2's **flip list**. Nothing here assumes the Decision Records lane's consumer-side
work on `feat/dr-fields`; if that work becomes ADR-0206's first consumer and moves it from
`Proposed` to `Accepted`, the flip list is what to execute.

## 8. Gate

Linux (`/home/sanmyaku/mindsos`), in the container, `docker compose --build`, branch tip
`1bfcb50` with `origin/main` at `c475a80`:

**4907 passed, 11 skipped, 1 xpassed, 0 failed**, 112 warnings, 2037s. RULES §7 CLI check:
**256** `test_cli` collected. The new guard alone: **10 passed**.

**The check that matters for a ship that adds tests is the collection diff**, and it was run
rather than reasoned about: `origin/main` collects **4908**, this branch collects **4918**,
**added = exactly the 10** tests of `test_retired_design_pointer.py`, **removed = none**. No
existing test changed identity, and no parametrized test gained a case from the two new files
— every file-globbing parametrized test in the tree globs a `mindsos_*` package, a specific
ADR number, or `confirmation_docs/*COORDINATION*.md`, none of which the new files match.

⚠ **Two counts do not reconcile, and are recorded rather than smoothed.** The run reports
4907 + 11 + 1 = **4919 outcomes** against **4918** collected, and a fresh collect of
`c475a80` gives **4908** where that commit's own ship record says **4907**. No rerun / flaky /
repeat / xdist / subtests plugin is pinned, there is no `pytest_generate_tests`, no
`pytest_collection_modifyitems` and no `addopts`, so the usual explanations are excluded. The
reading under which both sides behave identically is that the **baseline pass count is 4897,
not 4896** — which would mean the previous record's own correction went the wrong way. Not
asserted: the experiment that settles it is a full-gate run of `c475a80` reading its pass
count directly (~34 min). Filed as `gate-baseline-count-off-by-one`; it does not gate this
ship, because the collection diff already proves what this ship adds.

---

## 9. Round 2 (2026-08-21) — the decomposition half, which §5's guard was blind to

**§5's guard went green on a tree that still contained the decoy this lane exists to remove.**
Its token set — `derive_goal` and plan-level `MAX_DEPTH` — covers the **interpretation** half of
the design ADR-0206 supersedes and not the **decomposition** half. So
`docs/usage/knowledge/task-patterns.md`, the *published* page documenting `SubgoalTemplate` and
`DECOMPOSES_INTO`, was left telling readers that schema is how decomposition works. That page is
the actual home of the misreading recorded in §2, and a ship whose entire subject was that
misreading passed over it and certified itself green.

The derived axis of a domain cannot know which vocabulary is retired; the recalled axis is only
as complete as the recall (RULES §12.3). Both were needed and only one was checked. It surfaced
because the owner asked whether the documentation was fully updated — **not** from the lane's own
sweep, which is the part worth remembering. The lesson is written into the guard's module
docstring rather than a commit message: **when adding a row to `RETIRED`, ask what else the same
ADR retires.**

### What round 2 changed

**A third retired token** — `SubgoalTemplate | DECOMPOSES_INTO | PREREQUISITE_OF |
subgoal_template` — with its own mutation observed RED before the ship. It pulls five surfaces
into the pointer obligation: `mindsos_knowledge/identifiers.py` (the `subgoal_template_iri`
builder), `mindsos_knowledge/__init__.py`, `mindsos_cli/commands/knowledge.py` (the CLI still
mints subgoal IRIs), `docs/concepts/role-graphs.md`, and the rewritten usage page.

**ADR-0206 was undiscoverable from the L4 index.** `docs/decisions/summary/intelligence.md`
listed ADR-0172 and had **no row for 0205 or 0206 at all**. It gains a section carrying both,
and the 0172 row now names 0206 as amending it. **The new table has a `Status` column**, so
`tests/test_adr_status_consistency.py` now gates ADR-0206's status on that page — verified by
mutation: flipping the 0206 cell to `Accepted` makes the checker report
*"cell 'Accepted' != file status 'proposed'"*. One of the five sites in ADR-0172 §amendment-2's
flip list is therefore **enforced** rather than merely written down.

**Two published documents named things that do not exist** — see §10.

### Verification

Gate (Linux, `--build`, branch tip `c8727d8`, `origin/main` at `6169ce5`): **4908 passed, 11
skipped, 1 xpassed, 0 failed**, 2066s; `test_cli` **256**; the guard alone **11 passed**.
Collection diff: `origin/main` **4918** -> branch **4919**, added = exactly
`test_a_dead_schema_mention_without_the_pointer_is_reported`, removed = none. Every number was
**predicted in writing before the run** and every one matched.

⚠ **Including the off-by-one, which is the point.** Round 2 runs 4908 + 11 + 1 = **4920
outcomes** against **4919** collected — the same **+1** as round 1. The offset is therefore a
standing property of this tree, not something round 1 introduced, which leaves the
DR-leaves-the-repo record as the only data point showing a zero offset *and* the only one whose
collection number is independently known to be wrong. See `gate-baseline-count-off-by-one`; the
cheap next experiment is now `pytest -q tests_server/` against
`pytest --collect-only -q tests_server/`, which halves the search in about a minute.

Guard claims after the ship: **claim 1 = 0 violations, claim 2 = 0 dangling** over 348 scanned
files; exclusions still load-bearing (`docs/decisions/adr/**` now exempts 5 files,
`docs/_workbench/**` exempts 2). `tools/check_adr_status_consistency.py` exits 0 across 211 ADRs
with the new Status table in scope.

## 10. Round 2 finding — the docs name a role and a function that do not exist

The role is **`request-patterns`** (`ROLE_REQUEST_PATTERNS`,
`mindsos_knowledge/identifiers.py:66`) and the node type is **`RequestPattern`**. Not one
published document said so: **20 occurrences across 16 files** use `task-patterns` /
`TaskPattern`, names the code has not used since Phase 43, and `TaskPattern` appears **nowhere**
in `mindsos_*`. The code is clean, so this is a completed rename that never reached the docs.

| Where | What was wrong | Round 2 |
|---|---|---|
| `docs/concepts/role-graphs.md` | The **closed set** of role-graphs — the page a reader treats as authoritative — named a role and a node type that do not exist. | Fixed, and the row now says the schema is dead and not the decomposition mechanism. |
| `docs/usage/knowledge/overview.md` | Pointed at **`build_task_patterns_schema`** — a function that does not exist. | Fixed to `build_request_patterns_schema`. |
| `docs/usage/knowledge/task-patterns.md` | Stamped `last_confirmed_phase: 13`; listed **3** properties where ADR-0152 §2 gave the node **13** in Phase 43; presented the dead schema as usable. | Rewritten against the code. |
| `docs/dev/l4_intelligence_design_notes.md` | *"decomposition templates learned from experience"* — wrong twice: zero writers, and not the decomposition mechanism. | Fixed. |

**Not fixed, filed as `docs-name-a-role-that-does-not-exist`:** ~11 published files still carry
the stale name, plus the **file name** `docs/usage/knowledge/task-patterns.md`, its `mkdocs.yml`
nav entry, and the inbound link from `overview.md`. That is a doc-wide rename with a nav change,
and it wants its own guard — *"no published doc names `task-patterns` or `TaskPattern`"* — which
belongs **with** that rename, not ahead of it: written today it would be red on eleven files
nobody has scheduled. It is scope the owner did not approve, so it is recorded rather than taken.
