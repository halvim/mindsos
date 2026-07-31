# Brain architecture audit — what is MindsOS, what is loose Python

**Filed:** 2026-07-30 by the core finder-soundness chat.
**Purpose:** hand this to each brain's chat so it can move its Python onto MindsOS
mechanisms. Findings are quoted from the brains' own source.
**Audited:** `arc1-brain` (`arc1_brain/`), `nilm_brain`
(`projects/amii_study/nilm_brain/`). Not audited: bongard, robot, arc3, wsd, fol.

**Principle being applied** (`RULES.md` §8): a brain is a MindsOS *user*, not a
separate architecture. Anything a brain writes in Python that MindsOS should own is
either a missing core feature or a misuse of an existing one. A problem in a brain
is a problem in MindsOS, and the reverse.

---

## 0. What is already right — the template

**The REPL is reconciled.** Both brains boot through shipped core:

```python
# arc1_brain/repl.py — the whole file is 21 lines
from mindsos_server.boot import boot_brain
from mindsos_cli.commands.brain import BrainREPL, loop
...
stack = boot_brain(client, user="arc1")
install_arc(stack.cl, stack.session)
loop(BrainREPL(stack, viz_spec=viz_spec))
```

nilm's is the same shape and its docstring states the goal explicitly:

> *"The engine — boot, persister, REPL, `save` — is core; the only nilm-specific
> lines are the `Solver` install, the two `learn_pipeline` calls, and the
> appliance-state reload. (The brain-agnostic goal is to skill-package nilm so even
> this shim goes away and `mindsos brain` runs it.)"*

**This is the target shape for everything else in this document:** core owns the
engine, the brain contributes a small typed hook (`viz_spec`, an install function),
and the brain-specific file shrinks toward zero.

---

## 1. arc1-brain

### 1.1 The solver is disjoint from MindsOS. Its own docstring says so.

`arc1_brain/arc_solver.py`, lines 19–24:

> **Layering note (D3 evidence).** This solver is *self-contained*: it imports only
> `arc_grids` and takes `(profile, raw_task)` — it never touches the `CapacityLayer`
> or `find_pipeline`. The registered reason topology (`arc_capacities`) and this
> executable solver are **disjoint artifacts**; the "grounding" is a hand-maintained
> mirror, not an execution path.

Scale of the disjoint half:

| File | LOC | What it is |
|---|---|---|
| `arc_solver.py` | 1392 | the actual reasoning (stages 1–6) |
| `arc_grids.py` | 725 | grid primitives |
| `solve/pipeline.py` | 567 | a hand-written 10-step pipeline |
| `arc_profile.py` | 308 | profiling |
| `arc_search.py` | 297 | capability-token index |
| `solve/evaluate.py` | 284 | evaluation |
| `solve/runner.py` | 183 | a hand-written runner |
| **total** | **~3756** | **none of it runs through MindsOS** |

Against `arc_capacities.py` (1032 LOC) — the registered capacity topology that
*describes* the above but never executes it.

**Consequences that matter to core:**
- Every core mechanism arc asks for is being judged against a topology that has
  never actually run. arc's finder measurements are over a catalog whose capacities
  do not execute the solver.
- `solve/pipeline.py`'s docstring: *"The whole pipeline is recomputed from scratch on
  every invocation (no checkpoints)."* That is a hand-rolled substitute for the
  pipeline execution + grounding core already ships.
- `solve/runner.py` re-implements what `execute_pipeline` does, without grounding,
  without the MM, without Episodes.

**What arc1 should do:** make `arc_capacities` the execution path. Each `stage_*`
function in `arc_solver.py` becomes a capacity body consuming and producing declared
DataStates. The 10-step `solve/pipeline.py` becomes a composed Pipeline. `solve/
runner.py` deletes in favour of `execute_pipeline`.

**What core owes first:** real `planning.*` catalogs (see
`CORE_CR_REAL_L4_CATALOGS.md`) — without decomposition, a 10-step solve cannot be a
Plan.

### 1.2 Two drivers exist side by side

- `arc_l4.py` (242 LOC) — bespoke driver. Its docstring: *"We do NOT use
  `Orchestrator.run_lifecycle` — it is hardwired to the v0 catalogs; the demo
  composes the primitives directly."*
- `arc_lifecycle.py` (123 LOC) — routes through the real `run_lifecycle`. Its own
  status: *"Slice 2a (this state) … Still honest `dont_know`."*

So through real MindsOS, arc fetches a task and returns "don't know"; the solving
happens in the disjoint half. `arc_lifecycle.py` is the correct direction and should
absorb `arc_l4.py`, not run beside it.

### 1.3 What arc1 already does right — keep

- `arc_plan.py`, `arc_sufficient.py` — Local capacity **shadows** that override core
  builtins by IRI. This is the shipped, intended override mechanism. Exactly right.
- `viz_spec.py` — the per-brain hook into the shared viewer.
- `arc_corpus.py` — the corpus moved into the Local `dataset:arc1` graph, read off
  `CapacityContext` rather than a Python closure. Correct direction.

---

## 2. nilm_brain

nilm is substantially more integrated than arc1 and documents its own boundary
honestly. `control.py`:

> - **Composition** is the finder's job: the recognition segment … is composed once
>   by `ConjunctionFinder` and executed by core's `execute_pipeline` — never a
>   hand-rolled walk (D8).
> - **Iteration/refinement** is L4's job (A4/C4): parse/bind, the window fan-out,
>   and the repeat-until-converged 3-4 loop are Python control flow here.
> - Every `invoke`/`dispatch` checks `success` (C7).

`pipelines.py` states the acceptance test in the right terms:

> *"That the finder returns this pipeline AND it executes to real values is the
> objective acceptance gate, not a narrative."*

### 2.1 Where nilm still writes Python that core should own

| nilm code | What it substitutes for | Core status |
|---|---|---|
| the window fan-out in `control.py` | map over a collection | partly shipped (ADR-0199 map/fold); the multi-input map CR is on `feat/mapfold-multi-input`, unmerged |
| repeat-until-converged 3–4 loop | iterative refinement | **no core mechanism** |
| `harness.py::DuckSession` (23 LOC) | a minimal Local session | **no core primitive** (copied in arc1 + bongard) |
| re-teaching pipelines on every boot in `repl.py` | pipelines re-loaded at boot | `learn_pipeline` exists; nothing auto-loads them |

### 2.2 nilm's blockers that are core's, not nilm's

From project memory + the coordination doc:
- `ds:signal` cannot hold two channels; nilm calls `window` twice under one IRI and
  renames outputs in Python. Needs a per-channel DataState split — **nilm-side**,
  but only because core's blackboard is one value per DataState IRI.
- `solve_seed` is single-key, so multi-key seeding is unavailable.

---

## 3. Cross-brain: the same three gaps, written three times

1. **Iterative refinement** — a repeat-until-converged loop. nilm hand-writes it;
   arc1's 10-step recompute is a degenerate form. **No core mechanism.**
2. **A minimal Local session** (`DuckSession`) — three copies of the same ~12 lines
   across nilm, arc1 and bongard. **Should be a core primitive.**
3. **Driving the lifecycle at all** — both brains bypass `run_lifecycle` for the
   same stated reason. **Blocked on the real L4 catalogs.**

---

## 4. Recommended reading order for a brain chat

1. `RULES.md` §8 — a subsystem or brain owns nothing architectural.
2. This document, section 0 — the REPL is the template.
3. Your brain's section above.
4. `CORE_CR_REAL_L4_CATALOGS.md` — what core owes you, and when.

**Ask core before writing Python control flow.** If your brain needs a loop, a
fan-out, a retry or a session, that is a core mechanism that is missing or that you
have not found. Filing it as a core CR is cheaper than the third copy of it.
