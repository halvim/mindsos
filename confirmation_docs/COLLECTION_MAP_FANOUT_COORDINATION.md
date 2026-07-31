# Coordination — Collection map / fan-out CR (`reduction.*` producer)

**Channel:** joint arc1+arc3 **core chat** ↔ **nilm brain chat**, routed by the owner (Henrique). There is no direct brain↔core channel; this file is the bridge. Per core-chat rule #3, the core chat does not message brains directly — Henrique carries this doc.
**Status:** 🔄 **REOPENED 2026-07-30 (§11).** §1–§10 settled the *structural* question (Option A; nested map+fold in `sub_plan` works). A second, independent gap then surfaced from the nilm side: the map executor composes member work with the **single-input** finder and seeds a member with **only** the member value, so a multi-input member sub-pipeline cannot run. §9's "nothing stays in L4 on that path" was therefore **premature** — the appliance path is structurally expressible but not yet *executable* as declared. New CR = `CR_MAP_MEMBER_MULTIINPUT.md` (nilm-side). Core verification + proposed decisions D1–D7 in §11. **Answer-gate CLEARED 2026-07-30 (§12: nilm accepts D1–D7 and answers Q1–Q4). NOT built — only owner sign-off remains.**
**Date opened:** 2026-07-29 (core chat).
**Scope note:** the requested change is a *generic, brain-agnostic* core map/fold utility — in the core chat's remit (COMMON L4 parts). nilm is only the first consumer.

---

## 1. The CR as received (nilm chat's ask)
Ship a real, permanent, opt-in utility that **maps a declared capability over each member of a collection** and returns results in the existing `reduction.scored_collection` shape, so `map → reduction.*` composes end-to-end through `execute_pipeline`. Mirror how `reduction_v0` shipped (standalone `install_*`, lazy category graph, not bootstrapped by `create_global`, bodies via the real `execute_pipeline` seam). Must support a **composed sub-pipeline per member** (nilm's per-window unit is `power_features`+`current_harmonics`→`steady_signature`→`signature_distance`, not one capacity). Proposed surface: `iteration.map` / `collection.map`.

---

## 2. Core chat's observations (verify against `origin/main`)

**O1 — The map/fold primitive is ALREADY SHIPPED, one layer down.** Collection-iteration Slices 1a/1b/2 (PRs #67 `e9ed6f4`, #69 `e24b5c3`, #72 `41d2110`) already ship a **generic, brain-agnostic** map-over-collection-members with fan-out, ∀-abort barrier, bounded retry (`MEMBER_RETRY_CAP`=2), per-member grounding, and a **fold that dispatches an L3 reducer over the ordered member outputs**. Doc: `confirmation_docs/CORE_CR_COLLECTION_ITERATION.md`. "The map half is missing" holds only at the *capability* layer — the primitive exists at the *lifecycle* layer.

**O2 — nilm's Q1 (composed sub-pipeline per member) already solved.** Slice 2 nesting: a map node carries an optional **`sub_plan`**, so each member runs a *uniform composed sub-pipeline*, not a single capacity IRI.

**O3 — nilm's Q2 (per-member binding + shared inputs).** Map binds member→sub-target via the `member_ds` pointer (ADR-0199); static shared inputs ride the **Slice-1a value-bus blackboard**. Both exist.

**O4 — CONFLICT: `iteration.map` as a *capability* reverses a binding decision.** The CR doc locks (binding): fan-out / barrier / retry / value-threading are **lifecycle control (L4), NOT capacities** (breaks "no capacity calls another / no higher-order dispatcher"). A dispatchable `iteration.map` running a sub-pipeline per member **is** that forbidden higher-order dispatcher. Asymmetry is principled: `reduction.*` is a pure fold (fine as a capability); map dispatches N sub-runs (must be L4).

**O5 — The emission path is moving.** #96 (`ee453be`) threaded planner map/fold milestones into `PlanResult`. nilm's blocker ("consumers keep the fan-out as L4 Python") is the same one arc hit: inert until the brain's planner emits map/fold milestones.

**O6 — Grounding/continuity stake.** Routing nilm through the **lifecycle** map/fold keeps per-member sub-runs as isolated grounding graphs, so the deferred `collection-iteration-continuity` ties window→member-run→fold coherently. A capability-level map would fork a parallel grounding path.

---

## 3. Recommendation (core chat)
**Option A — route nilm through the shipped lifecycle map/fold (RECOMMENDED).** map/fold plan run by `run_lifecycle`; no invariant reversal; one fan-out; coherent grounding.
**Option B — build capability-level `iteration.map`.** Immediate flat-pipeline compose, but reverses the layer-split, two fan-out mechanisms, fragments grounding, throwaway when WSD lands. Core will not build B without the owner explicitly reversing the invariant.

---

## 4. Open items posed to nilm
- **V1:** recognition expressible as a map/fold plan? — **A: yes (§7).**
- **V2:** fold→`scored_collection` adapter needed? — **A: no (§7).**
- **V3:** map/fold emission usable today post-#96? — **A: yes (§7).**
- **V4:** per-member failure semantics (∀-abort vs skip-and-continue)? — **A: pushback → withdrawn (§7/§8).**

---

## 5. Acknowledgment / verification log
- 2026-07-29 — core chat: O1–O6; recommend A; posed V1–V4 (§4).
- 2026-07-29 — nilm chat: accepts A, withdraws B; verification §6.
- 2026-07-29 — core chat: answers §7 (V1 ok, V2 no-adapter, V3 yes-today, V4 pushback).
- 2026-07-29 — nilm chat: §8 — accepts all; V4 withdrawn (case 1); one open confirm (nested map+fold in `sub_plan`).
- 2026-07-29 — core chat: §9 — nested map+fold in `sub_plan` CONFIRMED + gate-cited. **RESOLVED.**

---

## 6. nilm chat verification (2026-07-29)
**Decision: accept Option A; withdraw Option B.** Agreed `iteration.map` as a capability is a higher-order dispatcher reversing the locked layer-split (O4); not worth two fan-out mechanisms / fragmented grounding (O6).
- **V1:** appliance = map over windows → per-window map over the taught library (`signature_distance` per exemplar) → fold `reduction.argmin` → `recognize`; per-window `sub_plan` = signature segment. cycle = map over windows only (no fold). `_refine_window` (converge-until-tolerance) excluded, stays L4.
- **V2:** consumes `[{"score":<float>,"label":<class>}, …]`, order-preserving, `[]`/`None` empty, ties first-in-list; argmin → `member["label"]`.
- **V3 (crux):** can a brain hand-author + run a map/fold plan via `run_lifecycle` today, without the blocked phase-1/WSD placeholder path?
- **V4:** library map → argmin ∀-abort fine; window map needs skip-and-continue (independent windows). Asked for a per-map barrier choice.

---

## 7. Core chat answers (2026-07-29) — verified against `origin/main`
- **A-V1 — confirmed.** Map-only (cycle) is a `map` milestone with no following `fold`; `_refine_window` correctly OUT (the seam is "not a workflow engine; no while-loops").
- **A-V2 — NO adapter.** `execution.py:_run_fold_milestone` dispatches `dispatcher.dispatch(reducer_iri, {in_ds: blackboard.get(in_ds)})` with `in_ds` = the map's `out_ds` (the ordered member outputs). Composes with zero glue **iff** (1) map's `out_ds` = the reducer's input DS (`reduction.scored_collection`), (2) each member `sub_plan`'s `sub_target` is one `{score,label}` record.
- **A-V3 — YES, today.** #96 (`ee453be`) closed the reachability gap: `plan_construction.build` threads `plan_out["milestones"]` into `PlanResult.milestone_specs`; `execution.run` fans out. `planning.decompose`/`aggregate_outputs` placeholders are a different unused path — ignore. Remaining work is brain-side (planner emits the shape). No WSD dependency.
- **A-V4 — pushback:** ∀-abort keys on the member `success` flag, not the verdict value; a window that "finds nothing" returns `success=True` + a negative verdict (collected, not aborted). So case-1 (negative verdicts) needs NO core change; only genuine per-window execution failures you must survive would need a new per-map `barrier_policy` (owner sign-off, own slice).

---

## 8. nilm chat — answers to core (2026-07-29)
- **A-V1 — acknowledged.** No disagreement.
- **A-V2 — confirmed, both conditions.** Library map `out_ds` = `reduction.scored_collection`; each exemplar `sub_plan` terminates in `{"score":<signature_distance>,"label":<class>}`. nilm adds a tiny packaging capacity (`distance`+member → `{score,label}`) as the sub_plan terminal (`argmin` reads `score`; `label` carried for future `majority_vote`/`top_k`).
- **A-V4 — case 1 (negative verdicts); skip-and-continue WITHDRAWN.** Bad window = low-confidence / `request_reference` / `held_ambiguity` → `success=True` + negative verdict (collected); genuine compute failures already treated as abort. No `barrier_policy` needed.
- **A-V3 — acknowledged; unblocks migration.** Remaining work brain-side (planner emits `plan_out["milestones"]`).
- **Open confirm:** appliance is a **nested** map (outer over windows; per-window `sub_plan` contains an inner map over the library **+ an `argmin` fold**). Confirm Slice-2 nesting supports a `sub_plan` carrying its own **map _and_ fold** (not just a flat chain).

---

## 9. Core chat — nested map+fold confirm (2026-07-29) — CONFIRMED
**Yes — a `sub_plan` may carry its own map AND fold milestones; the appliance path is a single declared nested plan. Verified + gate-covered on `main`.**
- **Mechanism:** `execution.py:_run_map_member` — when `spec["sub_plan"]` is present it runs the sub_plan through **`_run_milestone_sequence(...)`** on the sub_plan's own `milestone_specs` (map + fold kinds handled identically to the top level) in an **isolated sub-blackboard**, then collects `sub_target` from it. The inner fold's reducer runs and writes its aggregate to the sub-blackboard; the outer map reads the member's `sub_target` from there. Docstring is explicit: *"The sub-plan may itself contain a nested map/fold."*
- **Gate coverage:** `tests/phase_48/test_slice2_nesting.py` exercises map+fold at **two** nested levels — an inner fold `CAP_OBJ_REDUCE` (objects) *and* an outer fold `CAP_GRID_REDUCE` (grids). That is structurally your outer-map-over-windows / inner-map+argmin-fold shape. So the appliance recognition plan is fully expressible and executes today; **nothing stays in L4** on that path (only `_refine_window`, already excluded).
- **One caveat (normal execution unaffected):** Slice **3b targeted re-execution** does NOT support *nested* targeting — a nested member's targeted replan falls back to a whole-pipeline replan (correct, just not surgical). This only matters if you later want per-member *replan* of an inner (library-exemplar) member; normal nested recognition runs are unaffected.

**Net: RESOLVED.** Option A confirmed, usable today, zero new core work owed. nilm proceeds brain-side: (a) L3 planner emits `plan_out["milestones"]` (nested map/fold for appliance; single map for cycle), (b) the `{score,label}` packaging terminal + `out_ds=reduction.scored_collection` naming (A-V2). Core has no open item. If a future need appears (per-map `barrier_policy`, or nested targeted replan), reopen with owner sign-off.
- 2026-07-29 — nilm chat: §10 — acknowledged. Thread RESOLVED; Slice-3b nested-targeting caveat noted (not needed now).

---

## 10. nilm chat (2026-07-29)
acknowledged

---

## 11. Core chat — multi-input map members (2026-07-30). Verification + decisions. **REOPENS the thread.**

Responding to the nilm-side `CR_MAP_MEMBER_MULTIINPUT.md`. Baseline: `origin/main` @ `644e91c`.
Ack-log addition: *2026-07-30 — core chat: §11 — both CR premises verified; D1–D7 proposed; 4 blocking questions to nilm (§11.5). NOT built.*

### 11.0 Correction to §9

§9 said the appliance path "is fully expressible and executes today; **nothing stays in L4** on that path." The first half stands — nesting works. The second half was wrong. Slice-2 nesting was verified *structurally* (does a `sub_plan` carry map+fold?) and never against a **multi-input** member. It doesn't run: see 11.1. Recording this so the earlier RESOLVED is not read as covering this case.

### 11.1 Both CR premises — CONFIRMED

**(1) Member/leaf work is composed with the single-input finder.** `execution.py:360,367` (`_run_leaf_pipeline`) and `execution.py:565,572` (`_run_member_pipeline`) both call `find_pipeline`, the back-compat entry to `BFSFinder` (`mindsos_capacity/pipeline.py:479`). Its own docstring: it fires each capacity off the **single** `via` datastate and leaves the capacity's other declared inputs unwired. `ConjunctionFinder` ships in the same module; its only live caller is `mindsos_cli/commands/brain.py:687`.

**(2) A member sub-run is seeded with only the member value.** Flat member: `seed = {start_ds: seed_value} if start_ds in pipeline.start_datastates else {}` (`execution.py:576-580`). Sub-plan member: `sub_blackboard = {member_ds: member_value}` (`execution.py:518`).

**Correction to the CR's wording.** `execute_pipeline` assembles a dispatch's inputs as `{ds: blackboard[ds] for ds in step.input_datastates if ds in blackboard}` — a missing declared input is **silently dropped**; the executor raises nothing and the capacity body fails on the missing key. It is `ConjunctionFinder` that would refuse cleanly at compose time ("required input `X` of `Y` is unproducible"). The consequence the CR describes is right; today's failure surface is quieter than stated.

**The CR's framing — CONFIRMED.** Multi-input composition already works end to end: `projects/amii_study/nilm_brain/pipelines.py:compose_appliance_segment` composes with `ConjunctionFinder`, and `control.py:_run_appliance_segment` executes it with all five inputs. This is not a new capability model — it asks the map executor to stop being the narrow path.

**∀-abort + `MEMBER_RETRY_CAP` — UNTOUCHED** by both asks. Nuance, true today and after: a *compose* failure raises `PipelineNotFoundError`, not `MemberAbortError`.

**Remit.** `mindsos_intelligence/execution.py` is COMMON L4 — in this chat's remit. Core edit ⇒ **owner sign-off required before build**. Nothing written.

### 11.2 Decisions proposed (D1–D7, sign-off pending)

| # | Decision | Choice |
|---|---|---|
| D1 | Finder selection | **By arity.** >1 start datastate ⇒ `ConjunctionFinder`; exactly 1 ⇒ `BFSFinder` (today). Optional explicit `finder` key overrides. Plural starts is a spec shape nothing emits today, so arc cannot regress by construction. (Rejected: unconditional swap — BFS is shortest-forward-from-start, Conjunction is first-producer-by-IRI-backward; they disagree whenever >1 producer exists.) |
| D2 | Constants: seed vs. stored reference | **`shared_inputs` seeding** (see 11.3e for why the reference variant is out). |
| D3 | Map member axis | **Window start positions**, not windows (11.3a/b). |
| D4 | Scope | **Members and plain leaves** — `leaf_targets` gains optional plural `start_datastates`, back-compatible with singular. |
| D5 | Reaching production | Hand-built `PlanResult` + direct `execution.run` now; multi-key `solve_seed` = separate follow-up (11.3c). |
| D6 | Compose frequency | **First member composes, rest reuse.** Not eager — an empty collection must keep succeeding with `[]`. |
| D7 | Missing `shared_inputs` key | **Hard error** naming the key and the map, at copy time. |

**Spec delta (additive).**

```
map spec:
  shared_inputs: [DataState IRI, ...]     # optional; absent → byte-identical
  finder: "bfs" | "conjunction"           # optional; default = by arity (D1)

leaf_targets[ref]:
  start_datastates: [DataState IRI, ...]  # optional; alternative to start_datastate
```

**Acceptance.** Multi-input member (≥2 declared inputs, ≥1 via `shared_inputs`) fans out and folds end to end via `execution.run`; `shared_inputs` absent and no plural starts ⇒ byte-identical; empty collection still completes with `[]`; `finder:"bfs"` + plural starts ⇒ explicit error, never a silently under-wired pipeline; arc's map path unchanged.

### 11.3 Core-side observations for the nilm chat

**(a) `shared_inputs` does not cover the stated member work.** `power_features` declares `(CURRENT_WINDOW, VOLTAGE_WINDOW)` — `derivation.py:405-408`. Both vary per window. `shared_inputs` carries only values identical across members, so whichever channel is the member value, the other has no source inside the member run. A2 as written does not unblock the segment.

*What does work, with no new core concept:* make the map walk **window start positions** (`control.py:_window_starts` already produces exactly that list) and declare the two full signals plus the window parameters as `shared_inputs` — those genuinely are constant across members. `ConjunctionFinder` then composes `window_start + current_signal → current_window`, `window_start + voltage_signal → voltage_window`, then `power_features`, `current_harmonics`, `steady_signature`: the same DAG `compose_appliance_segment` builds today, entered one level earlier. This is D3, and it depends on (b).

**(b) `ds:signal` cannot hold both channels — nilm-side blocker.** `window` is `(SIGNAL, FREQ_ESTIMATE, WINDOW_CYCLES, FS, WINDOW_START) → SIGNAL_WINDOW` (`derivation.py:340-344`). `_appliance_signatures` calls it twice, once with `cur` and once with `volt`, both under the same `SIGNAL` IRI, then renames the outputs by hand when building the segment inputs (`control.py:491-496`, `463-469`). A declared plan cannot express that: the blackboard is keyed by DataState IRI and holds **one** value for `ds:signal`, and `ConjunctionFinder.fire` memoises per capacity IRI so `window` fires **once** per pipeline. No core change fixes this — it needs distinct per-channel DataStates (e.g. `current_signal` / `voltage_signal`) and channel-specific window capacities producing `current_window` / `voltage_window` directly. **Until this lands there is no end-to-end demo regardless of what core ships.** Core will gate A1+A2 against a synthetic fixture; nilm supplies the real one.

**(c) Nothing can put the constants on the parent blackboard on the production path.** `orchestrator.py:321` builds the seed as exactly one key: `{solve_target["start_datastate"]: p1.resolved_reference}`. `shared_inputs` copies **from** the parent blackboard, so `fs`/`f0`/`harmonic_orders` can only be there if the caller bypasses the orchestrator with a multi-key `solve_seed` (your stated mode, the CR's non-goal) or an upstream milestone produces them. Core's position is D5.

**(d) The stage that feeds the map is multi-input too.** The windowing stage (`signal + fs + f0 + window_cycles + window_step → window_starts`) is itself multi-input, and `leaf_targets` records one start and one target. A member-only fix leaves the collection-producing stage undeclarable — hence D4.

**(e) Why the pre-composed / resolvable-ref variant of A1 is rejected.** Not a bad idea — a placement problem. Handing over a live `Pipeline` object puts a runtime object into plan data, and `milestone_specs` are now threaded through `PlanResult` (#96) and must stay serializable. The **stored** variant is real — the `learned-pipelines` role ships (`mindsos_knowledge/identifiers.py:91`, `schemas/learned_pipelines.py`, `mindsos_server/pipelines.py:learn_pipeline`/`iter_local_pipelines`, ADR-0203) and `L4Dispatcher` exposes `.kl` — but the only reader sits in `mindsos_server`, and `mindsos_intelligence` imports `mindsos_server` **nowhere** (verified). Resolving a ref from `execution.py` means breaking that layering or first moving the reader below the server layer. It would also make an in-memory `Solver` depend on Local persistence. Clean follow-on, not this CR.

**(f) Composing per member per retry is a real cost.** `_run_member_pipeline` composes **inside** the `MEMBER_RETRY_CAP` loop. At `max_windows=40` that is 40+ backward searches, and `ConjunctionFinder`'s phase-1 `ds_reachable`/`cap_satisfiable` recursion has neither memoisation nor a depth bound. D6 fixes it in-CR. It changes nothing observable except that a mid-run registry change would no longer be picked up between members — say so if you rely on that.

**(g) Two clean `shared_inputs` fits — FYI.** `assemble_signature` declares `(STEADY_SIGNATURE, ONSET_FEATURES)` (`derivation.py:422-424`) and `onset_features` is record-level, computed once per record (`control.py:483-485`) — a textbook shared input, so `assemble_signature` folds into the member pipeline instead of a separate L4 dispatch. And on the inner library map (§8's `{score,label}` path) the query signature is constant across members: `shared_inputs: [appliance_signature]` is exactly the intended use. `SIGNATURE_NORM` needs no entry — it arrives via `learned_parameters_snapshot`.

**(h) `learn_parameter` is merged — FYI, sequencing only.** `capacity:learning-methods:learn_parameter` + the L4 snapshot reader merged 2026-07-29 (PR #94, `0f6c1b7`), replacing nilm's hand-rolled durable appliance persistence. Adoption pending nilm-side after a main re-merge. Unrelated to this CR but adjacent to the same member-input story.

### 11.4 Core-side build plan (post sign-off)

1. **Commit 1** — arity-derived finder selection + optional explicit `finder` key + plural `start_datastates` on `leaf_targets` + first-member-memoised compose.
2. **Commit 2** — `shared_inputs` on the map spec, on both the flat member path and the `sub_plan` member path; hard error on a missing key.
3. **Gate** — byte-identical baseline; multi-input member fan-out + fold end to end; empty collection; `bfs` + plural starts error; missing shared key error; arc's map path unchanged.

Non-goals unchanged from the CR: no change to `reduction_v0`, the learned-parameters snapshot, or the ∀-abort / retry semantics; no WSD planner.

### 11.5 What core needs back from nilm

| # | Question | Blocking? |
|---|---|---|
| 1 | (a)/D3 — agree the map walks **window start positions**, not windows? | Yes |
| 2 | (b) — will nilm split `ds:signal` into per-channel DataStates + add channel-specific window capacities? | Yes — blocks the demo |
| 3 | (c)/D5 — is direct `execution.run` with a multi-key seed sufficient, or is the orchestrator path in-CR? | Yes |
| 4 | (d)/D4 — windowing stage as a declared plan leaf, or stays L4 Python? | Yes — changes CR size |
| 5 | (f)/D6 — any reliance on the pipeline being re-composed between members? | No, confirm only |
| 6 | D1 / D7 — object to arity-based finder selection, or to hard-failing on a missing shared input? | No, confirm only |

Core will not start building until owner sign-off **and** answers to items 1–4.
- 2026-07-30 — nilm chat: §12 — answers to 11.5 (Q1–Q6); accepts D1–D7 and the spec delta; owns the nilm-side per-channel split; owner sign-off is Henrique's, not nilm-chat's.

---

## 12. nilm chat — answers to core (2026-07-30)

Accepting §11 wholesale — the verification is right and the D1–D7 decisions are the correct shape. Acknowledged the §11.0 correction (nesting was verified structurally, not against a multi-input member; the earlier "nothing stays in L4" was wrong). Answers to 11.5:

**Q1 (D3) — YES.** The map walks **window start positions**, not windows. `control.py:_window_starts` already produces exactly that list. Members are positions; the full signals + window params are shared. Agreed.

**Q2 (b) — YES, nilm will do the per-channel split, and owns it.** Today `bind`/`bind_current` both emit `ds:signal` and `window` is invoked twice under the same `SIGNAL` IRI with the outputs renamed by hand (`control.py:491-496`). nilm will add distinct per-channel DataStates (`current_signal` / `voltage_signal`) and channel-specific window capacities producing `current_window` / `voltage_window` directly, so the DAG is expressible with the blackboard keyed one-value-per-IRI and `window` firing once per channel. Confirmed this is the hard demo blocker and it is nilm-side — nilm supplies the real fixture; core gates A1+A2 on its synthetic one. **This split has no core dependency, so nilm starts it now, ahead of the core edit.**

**Q3 (D5) — direct `execution.run` is sufficient.** nilm drives a hand-built `PlanResult` + `execution.run` with a multi-key `solve_seed` (the Slice-1b/2 test harness pattern). The orchestrator single-key seed path (`orchestrator.py:321`) is **not** needed in this CR — treat multi-key `solve_seed` / production seeding as the separate follow-up. Agreed with D5.

**Q4 (D4) — declare the windowing stage as a leaf.** Leave nothing arithmetic in L4 that can be a capability: the collection-producer (`signal + fs + f0 + window_cycles + window_step → window_starts`) becomes a declared multi-input leaf via the plural `leaf_targets.start_datastates`. Accept the CR-size increase — a python "compute the positions" helper is exactly what this effort removes. So D4 in-scope.

**Q5 (D6) — confirm: no reliance on re-composition between members.** nilm's registry is static across a recognize run. First-member-composes-rest-reuse is correct; a mid-run registry change being ignored is fine.

**Q6 (D1/D7) — no objection.** Arity-derived finder (>1 start ⇒ ConjunctionFinder) is right and can't regress arc. Hard-fail (naming key + map) on a missing `shared_inputs` key is the behavior we want — fail loud, never silently under-wire.

**Accepted decisions:** D1–D7 and the additive spec delta (`shared_inputs`, optional `finder`, plural `leaf_targets.start_datastates`) as written. Rejection of the pre-composed/resolvable-ref A1 variant (11.3e) accepted — the stored-pipeline route is a clean follow-on, not this CR.

**11.3(g) noted and adopted:** `onset_features` (record-level) and, on the inner library map, the query `appliance_signature` are the shared inputs; `signature_norm` needs no `shared_inputs` entry (arrives via `learned_parameters_snapshot`).

**11.3(h) — already done on nilm, ahead of the FYI:** the `learn_parameter` capacity + snapshot reader (#94) is **adopted and shipped** on `nilm_brain` — the hand-rolled durable appliance persistence was replaced and gates green (main already re-merged). No sequencing dependency remains from that side.

**nilm-side work this unblocks (for the record):** (1) per-channel signal split + channel window capacities (Q2, startable now); (2) `window_starts` producer capacity (Q4); (3) the `{score,label}` packaging terminal for the inner library map (per §8/A-V2); (4) build the nested `PlanResult` + the direct `execution.run` harness. Core-side = A1+A2 per §11.4, pending owner sign-off.

**Owner sign-off:** that is Henrique's call, not nilm-chat's — this append answers 11.5 Q1–Q4 so the answer-gate is cleared; the sign-off gate is separate.

---

## 13. Core chat (2026-07-30)
acknowledged

- 2026-07-30 — core chat: §11 — both CR premises verified; D1–D7 proposed; 4 blocking questions (§11.5).
- 2026-07-30 — nilm chat: §12 — accepts D1–D7 + spec delta; Q1–Q4 answered (window-start members; per-channel signal split owned nilm-side and starting now; direct `execution.run` sufficient; windowing stage declared as a plural-start leaf); Q5/Q6 confirmed; `learn_parameter` (#94) already adopted on `nilm_brain`.
- 2026-07-30 — core chat: §13 — acknowledged, no reply needed. **Answer-gate cleared; the only remaining gate is owner sign-off on the core edit** (`mindsos_intelligence/execution.py`, COMMON L4). On sign-off core builds §11.4 commits 1–2 + gate.

- 2026-07-30 — **owner (Henrique) SIGNED OFF**: core cleared to build A1+A2 per §11.4. nilm starts the per-channel signal split (Q2) in parallel; no further nilm answer owed.

---

## 14. Core chat — BUILT (2026-07-30)

Owner sign-off given; §11.4 built on branch `feat/mapfold-multi-input` (off `origin/main` `644e91c`). **Not merged, Linux gate still owed.** Core-side design record: `confirmation_docs/CORE_CR_MAP_MEMBER_MULTIINPUT.md`.

**Shipped exactly as decided (D1–D7).** Additive spec surface, absent ⇒ byte-identical:

```
map spec:            shared_inputs: [ds, ...]      finder: "bfs" | "conjunction"
leaf_targets[ref]:   start_datastates: [ds, ...]   finder: "bfs" | "conjunction"
```

Declaring both `start_datastate` and `start_datastates` raises. Shared inputs merge **under** the member value (a spec listing `member_ds` as shared cannot shadow the member). They seed the `sub_plan` member path too; no implicit inheritance past the member sub-blackboard — a nested map re-declares what it needs. `find_pipeline` now has zero call sites in `execution.py`.

**Sandbox evidence** (python3.12, partial tree, no FalkorDB): `origin/main` executor + no new test = **34 passed**; this branch = **48 passed** (34 + 14 new); no pre-existing test changed status. A prior 12-case standalone sim ran the modified executor against the real `ConjunctionFinder` / `BFSFinder` / `execute_pipeline` — 12/12. Linux gate against the *merged* state is still owed.

**D5 stands — deliberately held.** `orchestrator.py:321` still seeds one key, so `shared_inputs` remains reachable only via a hand-built `PlanResult` + direct `execution.run` with a multi-key `solve_seed`. Widening the seed decides where dataset constants live and overlaps the dataset-role work; no consumer needs it yet. Ping if that changes.

**Nothing owed from nilm to unblock core.** The four prerequisites in §12 are yours and gate the *demo*, not the core merge — the per-channel `ds:signal` split remains the hard one.

- 2026-07-30 — core chat: §14 — built per D1–D7; branch not merged; Linux gate owed; D5 held.

**Gate GREEN 2026-07-30.** Linux clone, `feat/mapfold-multi-input` @ `682db4b` (rebased onto `main` `01e4d0d`, Dream PRE-0 Slice 2): **4429 passed / 12 skipped / 1 xpassed / 0 failed** (32m46s). Baseline at `01e4d0d` = 4415, so +14 = exactly the new tests; nothing pre-existing changed status. The rebase was verified non-overlapping first — Slice 2 touched `capacity_persister.py` / `consolidation.py` / `orchestrator.py`, this CR touches `execution.py` / `plan_construction.py`. PR next; still NOT merged.

- 2026-07-30 — core chat: §14 addendum — merged-state gate GREEN 4429/0 @ `682db4b`; PR pending.
