---
title: Decision Records v0 — handoff into the single-lane plan
status: Input to the restructured plan. NOT a plan. Nothing here needs re-deriving.
date: 2026-08-10
gated: feat/dr-v0 3bca933 (15/1) · feat/policy-role 0441792 (4551/11/1x/0)
---

# Decision Records v0 — what was built, what was proved, what is still open

**Read this before rewriting the plan.** Everything below was either **run** or **read in
code**. Where a prior document says otherwise, this file is the correction and the prior
document is wrong. Nothing here is a proposal except §3, which is explicitly marked.

The previous plan (`DECISION_RECORDS_V0_SLICE_PLAN.md`) was written without ever running the
code. Four stub capacities falsified three of its claims in an afternoon. Treat its
*mechanism* claims as hypotheses; its *scope* judgements still hold.

---

## 1. What is now proved, by a gated test

`tests/decision_records/test_route_probe.py`, Linux docker, **15 passed / 1 skipped**.

**The route composes and executes into the grounding graph.** This was the one assumption
neither lane had evidence for — nothing in `tests/llm_seam/` had ever invoked a finder.

```
dr_read_gross_income        <- [document]
dr_lookup_filing_threshold  <- [policy_id, as_of_date]
dr_filing_requirement       <- [gross_income, filing_threshold, policy_version]
11 nodes / 11 edges; all three CONSUMES edges land on the decision's CapacityInstance
from the instances that produced them.
```

Dropping one declared input turns **9 tests red**, so the guards are failable.

**Three sub-findings the plan did not have:**

1. **A capacity with two outputs feeding one consumer fires ONCE.** The lookup produces the
   limit and the version; the decision consumes both; one step, one dispatch, one
   `CapacityInstance`. **Core defect D-E does not bite this topology** — worth recording,
   since D-E's own note says it falsifies `ConjunctionFinder`'s docstring claim that shared
   upstream producers fire once. On this shape the docstring is correct.
2. **`ConjunctionFinder` fires `target_producers[0]` sorted by `node_id` and does not
   backtrack** to another producer of the target if that one aborts. Written down nowhere.
3. **The probe is NOT the first ConjunctionFinder caller.** `mindsos_cli/commands/brain.py:712`
   (the `execute` verb) has called it and run the result since 2026-07-05. The probe is the
   first **plural-start** composition, and the first found route that **grounds** — `execute`
   runs via `mindsos_server.pipeline_runner.run_pipeline` with no `mm`, so it writes no
   `capacity_mm` graph. ⚠ **`CORE_VERIFIED_FINDINGS.md` D-A's first sentence — "the sound
   finder was never wired to anything that executes" — is STALE. Do not cite it as written.**

---

## 2. Three plan claims that are false

1. **"A single start would silently drop two inputs."** No. BFS returns `bfs_exhausted` —
   **not found at all**. `policy_id` and `as_of_date` are unreachable from the document, so
   the lookup can never fire and there is no route to under-wire. Three starts is about
   composing **at all**, not about dodging a silent drop.
2. **"Three inputs to their three producers" / "the four capacities."** Contradicts the same
   plan's §Shape. **One lookup with two outputs is correct and sufficient.** A two-lookup
   variant also works, so the choice is free.
3. **Guard G7 as worded is unsatisfiable.** "A path back to *the* grounding root" — singular —
   cannot hold for the limit and the version once there are three starts, and those are the
   two values the money sentence leans on hardest. **Restated and gated:** the parentless
   instance set is *exactly* the declared starts. Still catches the real failure — a value
   that should have been derived arriving via `seed()`, which mints with no incoming edge.

Also: **guard G8 is vacuous** as written (see §3.3) and was replaced by **G8′** — assert
nothing is registered Global at the lookup / decision IRIs.

---

## 3. Six problems, and the choice each needs

**Marked as proposals.** Each states the end state that serves the product, deliberately
ignoring what the code does today and what changing it costs. The new plan owns the
sequencing.

### 3.1 L4 cannot express a multi-input start

A decision needs three inputs from two producers. `ConjunctionFinder` wires them; nothing can
hand it three starting points. `plan_construction._read_solve_target` and `_read_leaf_target`
each rebuild a dict holding only the singular `start_datastate`, so plural is dropped before
`_select_finder` is reached. The plural `start_datastates` key #99 added has **no caller of
any kind** — not the planner, and not `brain.py`'s `execute` (its start comes from
`skill_entries`, which is structurally singular).

**Not in `CORE_C3R1_ADMISSION_CONFIRMED.md` §9.** The nearest entry, §9.7, is about the
`_select_finder` **default**, which is a different item.

**Choice:** finding moves into planning (ADR-0206 §3, C4R3), and finder selection stops being
an arity heuristic — `decision.select_producers` is the right home, because how to build a
route is a decision the system makes. **Note `CORE_RECONCILIATION_PLAN.md`'s C2R4 ruling:
start-arity `_select_finder` is already "transitional by construction."** Any stopgap
passthrough extends something core has committed to deleting; say so out loud if one is taken.

**Blocks:** the run driver (item C). Until it lands, a driver must call the finder directly,
which makes the GTM lane own an L4 mechanism (RULES §8).

### 3.2 Nothing stops a capacity running on a value that is not there

`_validate_inputs` (`capacity.py:303`) checks input **presence** only — it never inspects the
value. The seam's reader declines with `{value: None, record}`, which passes validation, so
the decision capacity is invoked with `None` and compares it to a threshold.

**Choice:** core validates values against the declared `ShapeDescriptor` at dispatch and
refuses. A capacity declaring `scalar("int")` must be unable to receive `None`. A per-body
check means every future capacity has to remember, and the one that forgets emits a
confidently wrong Record — the exact failure the product is sold against.

**Blocks:** run 2 (reading refusal), which is half of v0.

### 3.3 DataStates have realms, and should not

`register_capacity` validates inputs/outputs against the **target realm's** DataState graph,
and `_mirror_global_datastates` copies **Global→Local only**. So a Global capacity cannot
declare a DataState that `register_reader(session=…)` created Local. The slice plan's
mixed-realm table (reader Local, lookup + decision Global) is **unbuildable as written**.

Everything went Local as a result, which made **G8 vacuous** — there is no Global capacity to
shadow — and left #122's union view untested by the slice built to exercise it.

**Choice:** DataStates carry no realm. A type is a type; only capacities are owned. Then a
Local reader and a Global authority compose, and G8 asserts something real again.

### 3.4 `append_only` is a word, not a behaviour

`validate_mutation_discipline` is **uncalled system-wide** — stated outright in
`schemas/dataset.py`. The new `policies` role declares `append_only` and nothing prevents an
edition being overwritten in place.

**Choice:** enforce it at the write path. A store whose purpose is *what did this authority
say on that date* cannot have a declared-but-unenforced history. Until then, **nobody writes
"append-only policy store" in anything a customer reads.**
`tests/policy_role/test_policy_role_core.py::test_append_only_is_declared_but_not_enforced`
pins the gap and goes red when it closes.

### 3.5 The finder does not record which producer it chose

`CORE_VERIFIED_FINDINGS.md` **D-D**: `fire` takes `satisfiable[0]` sorted by IRI and records
nothing, so the graph is indistinguishable from one where a single option existed.

**Choice:** the choice becomes a node in the grounding graph. *"The reasoning is the record"*
is false while the system can silently prefer one authority over another and leave no trace.
Not v0-blocking — one producer per DataState — but it is a **claim-1 integrity hole**, not
finder hygiene, and should be filed as one.

### 3.6 Two executors, and only one grounds

`mindsos_server.pipeline_runner.run_pipeline` and
`mindsos_intelligence.pipeline_execution.execute_pipeline` are both live. The shipped finder
path (`brain.py`'s `execute`) uses the one that writes **no grounding graph**.

**Choice:** one executor, and it grounds. A Decision Record renders from the `capacity_mm` run
graph and nothing else, so a path that executes without grounding cannot produce one.

---

## 4. What exists, gated, on two branches

| | |
|---|---|
| `feat/dr-v0` `3bca933` | `tests/decision_records/test_route_probe.py`. **15 passed / 1 skipped** (the skip is `origin_v0`, which lives on `feat/decision-records`). A **diagnostic that owns nothing** — it calls `ConjunctionFinder` directly on purpose and says so in its docstring. |
| `feat/policy-role` `0441792` | The `policies` L2 role + `confirmation_docs/CORE_CR_POLICY_ROLE.md`. **4551 passed / 11 skipped / 1 xpassed / 0 failed**, merged with `origin/main` `c97d99a`. |

**`test_l4_cannot_express_plural_starts_this_is_D_A` goes RED the day §3.1 lands.** That is
the signal to delete the probe, and it is why the probe was merged rather than archived — a
document asserting a gap goes stale silently; a test cannot.

### The `policies` role, in one paragraph

17th L2 role, dual-scope, `append_only`, one NodeType `PolicyEdition`, **zero edge types** —
edition ordering is derived from the in-force window, never stored (ADR-0192's criterion).
The node's **`value` payload is the edition text**; `value` is a `RESERVED_PROPERTY_KEYS`
member so the criterion's operand is the **`stated_value`** property. As-of lookup selects the
edition whose window **contains** the date — *not* the latest, which is a different and wrong
answer for any question about the past. Rejected: `learned-parameters` (learned ≠ fixed; Local
shadows Global per knob) and `dataset:policies` (a corpus is not an authority, and a Record
names which authority). **Amends ADR-0150; amendment number unassigned.**

**The closed-set guard is stronger than any document claims.** Adding a role breaks **22
sentinels across 15 files** in **nine distinct shapes** — `len(ALL_ROLES)`, dispatch-table
sizes, role-set literals, metagraph graph counts, the `_IRI_BUILDERS` key set, the kahn
scheduler order tuple, CLI `roles --list --json` output, `read-local --json` role graphs, and
a Phase-14 **import-time parity assertion** in `mindsos_admin/bootstrap.py::_GLOBAL_ROLE_ORDER`
that fires 21 collection errors from modules with no visible connection to roles. **Do not
simplify this.** It is why a 17th role cannot be added quietly.

---

## 5. Not built

- **The lookup capacity** — `capacity:decision:*`, as-of selection by window containment, and
  two refusal reasons: `no_source_in_force` (a finding about the customer's own policy set,
  `environment_fault` **false**) and `source_unreachable` (an environment fault).
- **The decision capacity, the run driver, the renderer.**
- **Runs 3, 4, 5** and guards G1, G4, G6.
- **The seam package has never been gated** — `feat/decision-records`, 48 cases hand-verified,
  no pytest. Its first gate may move things.

---

## 6. Settled and worth not re-opening

- **`capacity:decision:<name>`** is the only IRI shape where both rules agree: `family_rule_for`
  returns VERDICT via the category key, and `origin_v0.DECISION_SHAPED_CATEGORIES` matches on
  **category only** so the D15 opaque guard can fire. `capacity:dec_rec:*` was rejected — it
  silently gets `DATASTATE_MARKER` **and** the guard passes vacuously. Cost: a 14th category
  graph, outside ADR-0065's thirteen.
- **One lookup, two outputs.** §1.
- **G7 restated, G8 → G8′.** §2.

---

## 7. Method notes that earned their place

- **The container pre-filter predicts the gate exactly** — predicted 4548, gate returned 4548 —
  if built right: `uv venv --python 3.12` (`requires-python = ">=3.12"`; 3.10 fails on
  `datetime.UTC`, 3.11 on a mappingproxy dataclass default), **install `pytest tomli
  argon2-cffi typer`**, and diff against a pristine copy **by name, never by count**.
- **A `ModuleNotFoundError` is a silently unrun test file, not background noise.** `typer` was
  missing, `test_knowledge_cli.py` never ran, and it carried two of the three sentinels the
  gate then failed on. **Install the dep; do not classify the import error.**
- **Read the right ref.** A gate clone's local `main` is stale — reading it as `origin/main`
  produced a confident, wrong "main moved again". The tell was free: `git log <base>..main`
  printed nothing while the diff showed −2517 lines, i.e. main was an **ancestor**.
- **`origin/main` moved three times in one session** (`28c735d` → `ab30f5b` → `c97d99a`).
  Assert the pin in the same command box as any worktree creation or gate run.
- **One clone, many lanes.** `-p <name>` isolates containers, **not the checkout**. `--build`
  COPYs the working tree, so another lane's checkout mid-build silently corrupts a result.
  Never `git reset --hard` there; `git merge --ff-only` refuses instead of discarding.
- **Testing an abstract contract against ONE concrete artifact** found two field-set holes in
  two attempts, and four stub capacities found three wrong plan claims. Both beat eight
  exchanges of correspondence.
