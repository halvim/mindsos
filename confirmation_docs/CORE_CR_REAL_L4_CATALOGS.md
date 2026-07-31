# CORE CR — the real L4 catalogs (the "orchestrator" work, correctly scoped)

**Filed:** 2026-07-30. **Status:** SCOPING — not designed, not built.
**Verified at:** `origin/main` `01e4d0d`.

---

## 1. Correction to the framing: the orchestrator already exists

The ask was "build the orchestrator." Checked against the code — **the orchestrator
is shipped and real.** `mindsos_intelligence/orchestrator.py` drives LifecyclePhase
1→6 on a worker thread, routes every capacity call through `L4Dispatcher`, emits
chain artifacts under the MM writer lock, and (Phase 48 / ADR-0176) consolidates a
streaming Episode on every terminal path.

What is missing is **the 13 L3 capacities it dispatches.** All 13 are
`placeholder=True`, opt-in-install stubs shipped at Phase 47 so the control paths
could be exercised. The driver walks a real six-phase path; every decision it makes
along the way is a stub returning a fixed answer.

So this CR is **"build the real L3 catalogs,"** not "build the orchestrator." That
is a much better-shaped problem: the seam exists, the dispatch works, brains already
override individual slots (arc1's `arc_plan.py` / `arc_sufficient.py` are Local
shadows that win over the builtins by the shipped override mechanism). Nobody has
walked the path from placeholder to real.

---

## 2. The 13 placeholders

### `planning_v0` — 4 capacities
| Capacity | Placeholder returns |
|---|---|
| `planning.derive_initial_plan` | a single-Milestone Plan |
| `planning.decompose` | `[]` — never decomposes |
| `planning.is_leaf` | `True` — everything is a leaf |
| `planning.aggregate_outputs` | last child's output |

Consequence: **no plan is ever decomposed.** Every Request is one Milestone with one
pipeline. Multi-step planning has never run.

### `phase1_v0` — 4 capacities
| Capacity | Placeholder returns |
|---|---|
| `process.identity` | structured == raw (passthrough) |
| `hint.global` | empty hint set |
| `decision.derive_goal` | a fixed trivial goal |
| `decision.map_to_task_pattern` | a fixed pattern, confidence **1.0** |

Consequence: the `mapping_confidence_threshold` check in `phase_1.py` is **vacuous**
by default — nothing ever falls below a hardcoded 1.0.

### `orchestration_v0` — 5 capacities
| Capacity | Placeholder returns |
|---|---|
| `decision.signal_to_tier` | tier hint, else FOREGROUND |
| `scoring.attention_score` | cold-start constant |
| `decision.should_replan` | test-configurable, default `continue` |
| `predicate.sufficient` | test-configurable, default `True` |
| `phase6.attribute_blame` | a fixed BlameVerdict |

Consequence: **replan never fires on its own judgement, sufficiency is always true,
and blame attribution is a constant.**

---

## 3. The real question this CR must answer

Not all 13 are the same kind of thing. Three categories, and the split is the design
work:

**(A) Genuinely generic — core owes a real algorithm.**
`planning.decompose`, `planning.aggregate_outputs`, `planning.is_leaf`. Breaking a
goal into sub-goals is a core mechanism. Every brain needs it and none should write
it.

**(B) Generic mechanism, per-brain policy.**
`predicate.sufficient`, `decision.should_replan`, `scoring.attention_score`,
`decision.signal_to_tier`. Core should ship a real, non-trivial default that a brain
can shadow. arc1 already shadows `sufficient` — that pattern is the answer, and the
core default just needs to stop being a constant.

**(C) Inherently domain-specific — core ships an honest interface, not a body.**
`process.*`, `hint.*`, `decision.derive_goal`, `decision.map_to_task_pattern`.
A text brain, a signal brain and a grid brain interpret input differently. What core
owes here is a **real contract plus a mapper that actually consults
`request_patterns`** instead of returning a constant — not a universal body.

Getting (C) wrong is how "ships in WSD" happened: the mapping subsystem *is* text-
specific, so it got assigned to the text subsystem, and the generic half went with it.

---

## 4. Why this is the blocker for every brain

Both brains say the same thing, independently:

- nilm `control.py`: *"Rung 5 (mindsos's own orchestrator driving this) is out of
  reach until core ships the WSD/phase-1 placeholders — same as both arc brains.
  Not faked."*
- arc1 `arc_l4.py`: *"We do NOT use `Orchestrator.run_lifecycle` — it is hardwired
  to the v0 catalogs; the demo composes the primitives directly."*

So every brain hand-writes L4 control flow in Python, and each writes the same
things: an iteration loop, a fan-out, a converge-until-stable loop. That is not
brain-chat indiscipline; it is the only available move when the seam is a stub.

**Fixing this unblocks all brains at once, and is the precondition for retiring the
brain-side Python.**

---

## 5. Proposed slicing (each independently mergeable)

1. **`planning.decompose` + `is_leaf` + `aggregate_outputs`** — real decomposition.
   The largest single unlock: it is what makes a Plan a tree instead of one node.
2. **`predicate.sufficient` + `decision.should_replan`** — real defaults over the
   MM, shadowable per brain. Small; makes the replan and don't-know paths live.
3. **`decision.map_to_task_pattern`** — a real mapper that reads `request_patterns`
   and returns a real confidence. Precondition for taught-pipeline lookup, since
   that lookup keys off the pattern.
4. **`scoring.attention_score` + `decision.signal_to_tier`** — needs learned
   parameters to be non-empty; sequence after 1–3.
5. **`phase6.attribute_blame`** — needs 1 and 2 first (blame over a one-node plan
   is meaningless).
6. **`process.*` / `hint.*` / `derive_goal`** — category (C). Decide interface vs
   body before building.

Slices 1 and 3 are the ones that change what brains can do. 2 is cheap. 4–6 follow.

---

## 6. Open decisions (owner)

- **D-1.** Is this CR core's next priority, ahead of the finder work? It is bigger
  and it is what both brains are actually blocked on.
- **D-2.** For category (C), does core ship a body at all, or only a contract plus a
  registration check that a brain supplied one? Shipping a body invites the same
  mistake in reverse — a text-shaped default that every non-text brain shadows.
- **D-3.** Does `planning.decompose` decompose over Milestones only, or may it emit
  the map/fold collection nodes ADR-0199 already defines? The second is more useful
  and collides with the collection-iteration work.
- **D-4.** Do the placeholders stay after the real bodies land (as a documented test
  fixture) or are they deleted? Tests depend on their configurable verdicts.
