# MindsOS × Amii — Demo Script, Talk Track & Guard Test

*Built against the shipped API (verified in `mindsos_capacity/pipeline.py`, `datastate.py`, `runtime.py`, `capacity.py`, and `mindsos_intelligence/pipeline_execution.py`). Every claim below is pinned to the code that backs it, at the strength the code supports — nothing leans on roadmap.*

---

## 0. What this demo proves — and what it deliberately does not

In ~3 minutes, live and reproducible, it shows MindsOS **compose a runnable procedure it was never given, execute it, expose the full derivation, and refuse honestly in two different ways** — then shows a stock LLM hallucinate the same two refusal cases. That is the entire "trust / evaluation gap" wedge, demonstrated rather than claimed.

It does **not** claim learning, data-efficiency, enforced store-wide provenance, or a first-class not-found verdict. Those are named as roadmap out loud. For an RL/ML research audience, the sharp built-vs-roadmap line is the credibility move — do not blur it.

---

## 1. Claim → code → exact phrasing (the strength table)

| # | Claim to make | Code that backs it | Say **exactly** this | Do **not** say |
|---|---|---|---|---|
| 1 | Composition by search | `BFSFinder` / `ConjunctionFinder` in `pipeline.py` — type-directed graph search over `PRODUCES`/`CONSUMES` edges | "It composes a runnable pipeline it was never given, by type-directed search over typed operations." | "It learns the pipeline." / "no one wrote any of this" (you wrote the *primitives*) |
| 2 | Executes end-to-end | `pipeline_execution.execute_pipeline` walks the DAG, threads typed values | "And it runs the composed pipeline, threading typed data step to step." | Only true for the **linear BFS** path — don't run a multi-input DAG live (claim 6) |
| 3 | Inspectable derivation | `Pipeline.steps` + `Pipeline.edges` (typed dataflow) | "Here is the full plan and the values it threaded — the derivation of this result." | "Every DataState in the store is provenance-linked back to raw input" — **roadmap** (only a `created_by` stamp exists today) |
| 4 | Honest refusal at the unit | `NeedsInput` (ADR-0196) enveloped in `runtime.invoke`; family don't-know contracts in `family_rules.py` (ADR-0157) | "The smallest unit refuses — it returns a typed 'I need X' instead of guessing." | Nothing to walk back — this is shipped |
| 5 | Honest no-route at task level | `PipelineNotFoundError` raised by the finder, **caught** and routed to a fallback ask-human resolver in `submind_arbiter.py` | "When no path exists, it reports that and falls back to asking — it does not fabricate an answer." | "It's a first-class don't-know verdict" — **roadmap** (`pipelinenotfound-to-dontknow`); today it's an exception handled gracefully |
| 6 | Sound multi-input composition | `ConjunctionFinder` + `tests/composition_lifecycle/test_conjunction_finder.py` | "It also composes sound multi-input DAGs — here validated structurally." | Don't **execute** a fold/fan-in live — the executor's flat blackboard can't represent fan-in yet (**roadmap**) |

---

## 2. The demo — one runnable script

Domain is deliberately operations-flavored (an industrial/energy reading → recommended action), so the same artifact seeds your customer-discovery conversations later. Save as `amii_demo.py` at the repo root and run with the project venv.

```python
"""amii_demo.py — MindsOS live demo: compose, run, inspect, refuse.

Runs on the shipped in-memory L3 API (no FalkorDB needed).
Three acts + one structural bonus. Each print block maps to a talk-track beat.
"""
from mindsos_capacity import (
    Capacity,
    CapacityLayer,
    DataState,
    ShapeDescriptor,
    ConjunctionFinder,
    INPUT_GROUP_ALL_REQUIRED,
    CATEGORY_PERCEPTION,
    CATEGORY_COMPREHENSION,
    CATEGORY_DECISION,
)
from mindsos_capacity.pipeline import find_pipeline
from mindsos_capacity.exceptions import PipelineNotFoundError
from mindsos_capacity.needs_input import NeedsInput
from mindsos_capacity.runtime import invoke
from mindsos_intelligence.pipeline_execution import execute_pipeline

# ── DataState IRIs (the "vocabulary" a person teaches) ────────────────
def IRI(short: str) -> str:
    return f"datastate:t.{short}"

RAW, PARSED, NORMAL, CONDITION, ACTION = (
    IRI("raw_signal"), IRI("parsed_signal"), IRI("normal_signal"),
    IRI("condition"), IRI("action"),
)
DIAGNOSIS = IRI("diagnosis")  # deliberately unreachable (no producer)

def ds(short: str) -> DataState:
    name = f"t.{short}"
    return DataState(name=name, shape=ShapeDescriptor.scalar("str", opaque_tag=name))

# ── Known operating conditions (the taught knowledge) ─────────────────
CONDITIONS = {"pressure_high": "vent", "pressure_low": "seal", "nominal": "hold"}

# ── Capacity bodies. Inputs arrive keyed by DataState IRI. ─────────────
def _parse(**kw):      return {PARSED: str(kw[RAW]).strip().lower()}
def _normalize(**kw):  return {NORMAL: kw[PARSED].replace(" ", "_")}
def _classify(**kw):
    v = kw[NORMAL]
    if v not in CONDITIONS:                       # honest refusal at the unit
        return NeedsInput(
            question=f"Unrecognized reading {v!r}; which condition is this?",
            missing=CONDITION,
            choices={c: c for c in CONDITIONS},   # ready-to-resubmit answers
        )
    return {CONDITION: v}
def _recommend(**kw):  return {ACTION: CONDITIONS[kw[CONDITION]]}

def cap(name, category, inputs, outputs, impl):
    return Capacity(
        name=name, category=category,
        inputs=tuple(inputs), outputs=tuple(outputs),
        input_group=INPUT_GROUP_ALL_REQUIRED, implementation=impl,
    )

def build_layer() -> CapacityLayer:
    cl = CapacityLayer(categories=(
        CATEGORY_PERCEPTION, CATEGORY_COMPREHENSION, CATEGORY_DECISION,
    ))
    for short in ("raw_signal","parsed_signal","normal_signal","condition","action","diagnosis"):
        cl.register_datastate(ds(short), allow_new_realm=True)
    # Four single-purpose primitives. NOTHING maps raw_signal -> action directly.
    cl.register_capacity(cap("parse",     CATEGORY_PERCEPTION,    [RAW],       [PARSED],    _parse))
    cl.register_capacity(cap("normalize", CATEGORY_COMPREHENSION, [PARSED],    [NORMAL],    _normalize))
    cl.register_capacity(cap("classify",  CATEGORY_DECISION,      [NORMAL],    [CONDITION], _classify))
    cl.register_capacity(cap("recommend", CATEGORY_DECISION,      [CONDITION], [ACTION],    _recommend))
    return cl

class DemoDispatcher:
    """Adapts the shipped runtime.invoke to execute_pipeline's dispatcher contract."""
    def __init__(self, cl): self.cl = cl
    def dispatch(self, capacity_iri, inputs, *, cancel_token=None, task_id=None, step_id=None):
        decl = self.cl.get_declaration(capacity_iri)
        return invoke(decl, inputs, task_id=task_id, step_id=step_id)

def show_dag(p):
    names = [s.capacity_iri.split(":")[-1] for s in p.steps]
    print("  composed pipeline:", " -> ".join(names) or "(empty)")
    for e in p.edges:
        src = "START" if e.producer == -1 else p.steps[e.producer].capacity_iri.split(":")[-1]
        dst = p.steps[e.consumer].capacity_iri.split(":")[-1]
        print(f"    {src} --[{e.datastate.split('.')[-1]}]--> {dst}")

# ══ ACT 1 — compose a pipeline nobody wrote, then run it ═══════════════
cl = build_layer()
print("\n[ACT 1] Goal: turn a raw reading into a recommended action.")
pipe = find_pipeline(cl, start_datastate=RAW, target_datastate=ACTION)
show_dag(pipe)                                   # claim 1 + 3 (derivation)
res = execute_pipeline(DemoDispatcher(cl), pipe, {RAW: "  Pressure High "}, task_id="demo-1")
print("  ran:", res.success, "| action =", res.outputs.get(ACTION))   # claim 2

# ══ ACT 2 — the unit refuses instead of guessing ══════════════════════
print("\n[ACT 2] Same pipeline, an out-of-vocabulary reading.")
res2 = execute_pipeline(DemoDispatcher(cl), pipe, {RAW: "gremlins"}, task_id="demo-2")
if res2.needs_input:                             # claim 4
    print("  MindsOS did NOT fabricate. It asked:")
    print("   ", res2.needs_input.question)
    print("    (an LLM asked the same thing will invent an action — show that next.)")

# ══ ACT 3 — no route at all: honest report, not a guess ═══════════════
print("\n[ACT 3] Ask for something the system has no way to produce.")
try:
    find_pipeline(cl, start_datastate=RAW, target_datastate=DIAGNOSIS)
except PipelineNotFoundError as exc:             # claim 5
    print("  No pipeline exists ->", exc)
    print("  In the running system the SubMind arbiter catches this and")
    print("  falls back to asking a human — never a fabricated 'diagnosis'.")

# ══ BONUS (structure only) — sound multi-input composition ════════════
print("\n[BONUS] Sound multi-input composition (structural — execution is roadmap).")
POLICY = IRI("policy"); ACTION2 = IRI("action2")
for short in ("policy","action2"): cl.register_datastate(ds(short), allow_new_realm=True)
cl.register_capacity(cap("load_policy", CATEGORY_PERCEPTION, [RAW], [POLICY], lambda **kw: {POLICY: "safe"}))
cl.register_capacity(cap("recommend2", CATEGORY_DECISION, [CONDITION, POLICY], [ACTION2], lambda **kw: {ACTION2: "hold"}))
dag = ConjunctionFinder().find(cl, start_datastates=(RAW,), target_datastate=ACTION2)
show_dag(dag)   # note: recommend2 shows BOTH condition and policy wired in
print("  ^ both inputs resolved by the sound finder. We validate this structurally;")
print("    executing multi-input fan-in is on the roadmap, not claimed here.")
```

**What to display on screen:** the console output. The `show_dag` block *is* your "trace" — the composed plan plus (from `res.outputs`) the values it threaded. That is honest claim 3. Do not open the graph store and imply per-DataState provenance edges; there aren't any yet.

---

## 3. Talk track (keep it under 3 minutes, state each claim at table strength)

**Open (15s).** "The field's problem in 2026 is that agents act faster than anyone can verify them. I'll show a system that composes what it does, shows its work, and refuses honestly — live, no slides."

**Act 1 (40s).** "I taught it four small typed operations and one goal. I did *not* wire them together. It searched the type graph and composed this pipeline itself, then ran it and returned the action. The chain you see is the derivation — the plan plus the values it carried." *(claims 1–3)*

**Act 2 (30s).** "Same pipeline, a reading it was never taught. It doesn't guess — the unit returns a typed 'I need X.' Watch an LLM given the identical situation invent an action." *(claim 4 + LLM contrast)*

**Act 3 (30s).** "Now I ask for something it has no path to. It reports 'no pipeline' and, in the running system, falls back to asking a human. Making that a first-class verdict instead of a caught exception is on our roadmap — today it's the exception, handled gracefully." *(claim 5, stated honestly)*

**Bonus + close (25s).** "It also composes sound multi-input procedures — validated structurally here; executing fan-in is roadmap. Everything I just showed runs on shipped code. The learning layer and store-wide provenance are designed and not built — which is exactly the collaboration I'd want Amii's help to validate." *(sets up the ask)*

---

## 4. The LLM contrast (make it fair, not a strawman)

Give a stock model the **same** limited context — the three known conditions — and the same two hard inputs (`"gremlins"` and the "diagnosis" request). Show it produce a confident, plausible, wrong action rather than "I don't know." Keep the prompt visible so the room sees you didn't rig it. The point is not "LLMs are dumb" — it's "same information, one system fabricates and one refuses." One screen, side by side.

---

## 5. Guard test — so the live path cannot break on stage

Drop this at `tests/composition_lifecycle/test_demo_compose_execute.py`. It covers the *exact* path you demo (compose → execute end-to-end, the refusal, and the no-route), so a green gate means the demo is safe. This is the one piece of building worth doing — it serves the demo instead of expanding scope.

```python
"""Guard test for the Amii demo path: compose + execute end-to-end,
honest unit-refusal, and honest no-route. Mirrors amii_demo.py."""
import pytest
from mindsos_capacity import (
    Capacity, CapacityLayer, DataState, ShapeDescriptor,
    INPUT_GROUP_ALL_REQUIRED, CATEGORY_PERCEPTION, CATEGORY_COMPREHENSION,
    CATEGORY_DECISION,
)
from mindsos_capacity.pipeline import find_pipeline
from mindsos_capacity.exceptions import PipelineNotFoundError
from mindsos_capacity.needs_input import NeedsInput
from mindsos_capacity.runtime import invoke
from mindsos_intelligence.pipeline_execution import execute_pipeline

def IRI(s): return f"datastate:t.{s}"
RAW, PARSED, NORMAL, COND, ACTION, DIAG = map(IRI, (
    "raw_signal","parsed_signal","normal_signal","condition","action","diagnosis"))
CONDITIONS = {"pressure_high": "vent", "nominal": "hold"}

def _ds(s):
    n = f"t.{s}"; return DataState(name=n, shape=ShapeDescriptor.scalar("str", opaque_tag=n))
def _cap(name, cat, ins, outs, impl):
    return Capacity(name=name, category=cat, inputs=tuple(ins), outputs=tuple(outs),
                    input_group=INPUT_GROUP_ALL_REQUIRED, implementation=impl)

def _classify(**kw):
    v = kw[NORMAL]
    if v not in CONDITIONS:
        return NeedsInput(question=f"unknown {v!r}", missing=COND, choices={c: c for c in CONDITIONS})
    return {COND: v}

@pytest.fixture
def cl():
    layer = CapacityLayer(categories=(CATEGORY_PERCEPTION, CATEGORY_COMPREHENSION, CATEGORY_DECISION))
    for s in ("raw_signal","parsed_signal","normal_signal","condition","action","diagnosis"):
        layer.register_datastate(_ds(s), allow_new_realm=True)
    layer.register_capacity(_cap("parse",     CATEGORY_PERCEPTION,    [RAW],    [PARSED], lambda **kw: {PARSED: str(kw[RAW]).strip().lower()}))
    layer.register_capacity(_cap("normalize", CATEGORY_COMPREHENSION, [PARSED], [NORMAL], lambda **kw: {NORMAL: kw[PARSED].replace(" ", "_")}))
    layer.register_capacity(_cap("classify",  CATEGORY_DECISION,      [NORMAL], [COND],   _classify))
    layer.register_capacity(_cap("recommend", CATEGORY_DECISION,      [COND],   [ACTION], lambda **kw: {ACTION: CONDITIONS[kw[COND]]}))
    return layer

class _Disp:
    def __init__(self, cl): self.cl = cl
    def dispatch(self, ci, inputs, *, cancel_token=None, task_id=None, step_id=None):
        return invoke(self.cl.get_declaration(ci), inputs, task_id=task_id, step_id=step_id)

def test_composes_and_executes_end_to_end(cl):
    pipe = find_pipeline(cl, start_datastate=RAW, target_datastate=ACTION)
    assert [s.capacity_iri.split(":")[-1] for s in pipe.steps] == ["parse","normalize","classify","recommend"]
    res = execute_pipeline(_Disp(cl), pipe, {RAW: "  Pressure High "}, task_id="t")
    assert res.success and res.outputs[ACTION] == "vent"

def test_unit_refuses_out_of_vocab(cl):
    pipe = find_pipeline(cl, start_datastate=RAW, target_datastate=ACTION)
    res = execute_pipeline(_Disp(cl), pipe, {RAW: "gremlins"}, task_id="t")
    assert res.needs_input is not None and not res.success

def test_no_route_raises_not_found(cl):
    with pytest.raises(PipelineNotFoundError):
        find_pipeline(cl, start_datastate=RAW, target_datastate=DIAG)
```

If any of these three fail when you run them, that is the demo breaking *before* the room, which is the entire point of having them.

---

## 6. Scope guard (read before you "improve" anything)

This demo runs on **shipped** code. The four roadmap items — store-wide provenance edges, the first-class not-found verdict, executing multi-input fan-in, and finder backtracking — are **not** on the path to this demo and must not be built for it. Their absence is disclosed in the talk track, and that disclosure is what earns the room. Build the guard test; ship the conversation.
```
