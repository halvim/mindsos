# Concept: Request, Task, Episode, Dream

Status: DRAFT for approval. Foundational concept doc. Defines the vocabulary and
the dream-learning model. Naming decisions here (Request / Task) imply a
codebase rename planned in the last section.

---

## 1. Why this doc

The word "task" is currently overloaded: in the code it names the *top-level*
unit created from an input, but conceptually we also want it to name the
*recursive solvable unit* at every level of the solve tree. This doc splits the
two, names them, and defines how they are remembered (Episode) and improved
(Dream).

---

## 2. Core concepts

### Request (previously: "task")
A **Request** is what the system receives as input. It is **loosely defined** —
the system does not yet know what it means or what to do with it. Interpretation
(hint -> map -> plan) **calibrates** the Request into an actionable form and
produces a top-level pipeline (P0).

- One input = one Request.
- Carries the interpretation artifacts: hints, map (task pattern + confidence),
  plan.
- Loosely defined: the same-looking input may calibrate differently over time,
  so a Request is identified for learning by its **map pattern**, not its raw
  text.

### Task (the recursive solvable unit — keeps the name "task")
A **Task** is any solvable node in the solve tree: input datastate(s) -> solve
-> output datastate(s). The tree is self-similar:

```
Request
  P0                      (top-level pipeline)
   -> P1.1  P1.2  P1.3    (sub-pipelines = Tasks)
        -> P2.1 ...       (Tasks)
             -> capacity  (leaf Task)
```

Every P[i,j] is a Task. Tasks are **precisely defined** — each solves a specific
sub-problem with a known input/output contract — which is *why* their
confidences (hint/map/plan at the levels that have them, and path selection) can
be measured and updated.

### Capacity (leaf Task)
A **capacity** is the base case: a Task with no sub-pipeline (ds_in -> ds_out).
It is **atomic** — it does exactly one thing and **cannot be improved
internally**. It can only be **substituted** (a different capacity, or a small
pipeline that outperforms it and is promoted).

### Definedness gradient (intentional, not a defect)
- **Request** — loosely defined; needs *calibration* (hint/map/plan confidence).
- **Task (interior)** — precisely defined; *optimizable* by trying alternative
  maps and alternative graph paths.
- **Capacity (leaf)** — atomic; not improvable, only *substitutable*.

---

## 3. Episode

An **Episode** is the whole remembering of one Request: the entire solve tree
(all Tasks, pipelines, capacities, and datastates), saved as a unit.

An Episode records:
- **The Request** — the raw input (the reload anchor) and its interpretation
  (hints, map + confidence, plan).
- **The tree** — plan/sub-task decomposition; every Task and the pipeline that
  solved it.
- **Datastates** — inputs consumed and results produced at each step. These
  double as the **sandbox fixtures** for dream replay (stand-ins for anything
  external) and as the baseline results to compare against.
- **Baseline metrics** — the measurements each objective reads (e.g. mapping
  confidence, step count, capacity cost, timing, result).
- **A searchable index** — so the Dream can query the Episode by task /
  pipeline / capacity / datastate without walking the whole tree.

### Episodes are written incrementally (mandatory, always-on)
An Episode is **not** assembled once at the end. It is persisted **as the Request
is solved** — a continuous, mandatory runtime process, never batched at task
completion:
- **open** the Episode at Request start (with the raw input);
- **append** as each pipeline-run completes (and each interpret/plan phase) —
  the per-run capacity graph is the streaming unit;
- **close** by stamping the terminal outcome.

This makes a crash mid-solve leave a real *partial* Episode (promotes ADR-0179 §3
from deferred to mandatory), not just a failed tombstone. Durability spine is an
inline flush at run/phase boundaries (crash-consistent); an async background
writer is an optional optimization, not the default. The Dream reader must
tolerate **open / incomplete** Episodes (use up to the last durable run; latest
replan attempt wins). Requires a durable (not in-memory) checkpoint store.

Notes:
- Episodes are saved **incrementally but coherently**; any node is independently
  addressable via the index once written.
- Backfill: an Episode missing a metric a *new* objective needs can be
  **replayed** to record it — but a replayed metric is a *current-state*
  measurement, not the original run's number.

---

## 4. Dream

The **Dream** replays an Episode to **improve the system internally**. Signature:

```
dream(task, objective, signal, strategy)
```

- **task** — the Task (or Request) node to optimize (any node in the Episode).
- **objective** — a pluggable optimization target (fewer steps, cheaper, higher
  confidence, faster, more reusable, ...). New objectives can be added.
- **signal** — mandatory. Encodes **correctness**, not just a metric: it tells
  the Dream whether an alternative's result is actually *valid*. Without a
  correctness signal, calibration drifts toward "matches last time" and can
  reinforce a suboptimal original. The signal's truth source must be defined
  per objective.
- **strategy** — a pluggable search strategy over alternatives (the space is too
  large to exhaust; strategy bounds it).

### Rules
- **Runs against the system as it is** (not as it was). No historical
  system-state snapshots. The Dream reloads the *task*, and today's system
  re-attacks it.
- **Isolated + sandboxed.** The Dream runs on a fork of the mental model
  (`fork_dream_mm`), never on the live system. Any capacity that **cannot be
  contained in the sandbox cannot be used in the Dream** — a capacity must
  declare its side-effect class, and non-sandboxable ones are excluded (and any
  Task solvable only through them is out of scope).

### Optimization moves by level
- **Request / map** — try the **lower-confidence maps** the live system skipped
  (it picks highest confidence); if a lower-confidence map is validated by the
  signal, its confidence can be raised.
- **Interior Task / path** — a graph holds **multiple valid paths**; the live
  finder picks the highest-confidence one, and the Dream tests the others.
  Fruitful even with an unchanged capability set.
- **Capacity** — cannot be improved; only **substituted** (better capacity, or a
  promoted pipeline).

### Write-back (how a Dream win becomes a permanent improvement)
- **Confidence updates** — hint / map / plan / path confidences.
- **Pipeline promotion** — an improved pipeline is promoted to L2 (Global).
- **Scope of effect:** a Task-local pipeline improvement affects only that Task.
  But **L2 promotions and shared-confidence updates are global** — they can
  change other Requests. Those writes need a **validation gate** before they go
  live (a promotion must not regress related Episodes).

### Intra- vs cross-episode
- **Intra-episode** — trying alternative maps/paths within one Episode; measuring
  steps/cost/confidence/result.
- **Cross-episode** — calibrating a map pattern's confidence across many
  Episodes; judging "reusable / general"; deciding a promotion helps many Tasks.
  These need a **cross-episode index** ("find all Tasks using capacity X"), which
  does not exist today.

---

## 5. Open decisions (not yet settled)
1. **Write-back validation gate** — what validates an L2 promotion / shared
   confidence change before it hits the live system.
2. **Capacity side-effect declaration** — the marker that makes sandbox
   eligibility checkable (none exists today).
3. **Correctness signal source** — where per-objective ground truth comes from
   (esp. for "accuracy"; the baseline result alone only confirms reproduction).
4. **Cross-episode index** — structure for corpus-level queries and calibration.
5. **Episode node granularity** — confirmed one Episode = whole tree, all nodes
   indexed; which trivial leaves (if any) are excluded from indexing.

---

## 6. Naming / rename plan

**Decision:** current top-level "task" -> **Request**. "Task" is freed to mean
the recursive solvable unit (any pipeline node); "capacity" stays the leaf.

### Rename (current top-level "task" -> "Request")
Approximate code footprint (core packages, indicative counts):
- `task_id` (~182) -> `request_id`
- `task_run` / `TaskRun` (~51 / ~25) -> `request_run` / `RequestRun`
- `task_input` / `task_input_ref` (~27) -> `request_input` / `request_input_ref`
- `raw_task` (~11) -> `raw_request` (the grounding-DAG root datastate)
- ~48 code files, ~106 docs touch "task".
- `Request` is currently unused as a noun (only `request_cancel`) — no collision.

### Needs a separate decision: `task_pattern` (~77) + `ROLE_TASK_PATTERNS`
`task_pattern` is the **map result for the top-level Request**, so conceptually
it is a *Request*-pattern. But it is also a knowledge-layer role
(`ROLE_TASK_PATTERNS`) and the most embedded identifier. Renaming it touches the
knowledge layer broadly. **Recommend: decide separately** — either
`request_pattern` (consistent) or leave `task_pattern` as an established
knowledge role and accept the mild inconsistency.

### Add (new "Task" concept)
The recursive Task is **not yet a named entity** in code. It currently exists as
a Milestone (plan node) paired with a Pipeline. Introducing "Task" means naming
that pairing as the addressable, indexable unit the Episode index and the Dream
operate on. This is an **addition**, not a rename.

### Suggested sequencing
1. Land this concept doc (vocabulary agreed).
2. Rename top-level task -> Request (mechanical, high-churn, low-risk).
3. Decide `task_pattern` separately.
4. Add the Task unit + Episode searchable index (feeds the Dream).
5. Then the Dream-specific gaps (sandbox marker, write-back gate, correctness
   signal, cross-episode index).
