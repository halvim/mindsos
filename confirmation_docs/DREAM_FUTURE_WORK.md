# Dream — Future Work (deferred out of v1)

Items intentionally deferred from the dream v1 build. Recorded here so they are not lost.
Each: the problem, what to build, and what it is blocked behind.

## 1. Path scoring system
- **Problem:** capacity paths have no confidence/score today. `ConjunctionFinder`
  picks the first satisfiable producer by `node_id` (confidence-blind). So a v1
  dream expresses a path improvement only as a promoted better pipeline (WB-2),
  never as a path-confidence update.
- **Build:** a path-confidence model so path selection is ranked and dream wins
  can raise/lower path confidence (the path half of WB-1).
- **Blocked until:** dream subsystem v1 is complete.

## 2. Correctness source of truth (per objective)
- **Problem:** the v1 signal only proves "same answer as the original run"
  (reproduction), not correctness. Objectives that require a genuinely *better*
  answer (e.g. accuracy) cannot be validated without external ground truth.
- **Build:** define a per-objective ground-truth source so the dream can validate
  genuinely-better results, not just output-equivalent ones. Unlocks accuracy-class
  objectives (deferred from D-2/D-4).
- **Blocked until:** a real ground-truth source exists per objective.

## 3. "Find related tasks" tool (cross-episode index, XE-1)
- **Problem:** a global change (L2 promotion / shared-confidence update) must not
  regress other requests. v1's write-back gate (WB-3) checks a fixed, hand-picked
  corpus because the tool to find *which* tasks a change affects does not exist.
- **Build:** the cross-episode index (XE-1) — "find all tasks using capacity X" +
  corpus-level calibration — and upgrade the WB-3 gate from fixed-corpus to
  related-task-scoped.
- **Blocked until:** dream write-back (WB) has shipped on the fixed-corpus gate.

## Related (not deferred — parallel core work)
- **Official core "Task" entity.** v1 dream uses a lightweight address/view over
  (milestone, pipeline, run-ref). The first-class core Task entity is its own
  design-first CR, decided separately; it is NOT a dream prerequisite.
