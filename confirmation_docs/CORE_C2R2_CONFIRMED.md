# CORE-C2R2 — CONFIRMED

**Shipped:** 2026-08-04. **Squash:** `92d7421` (PR #114, `main`).
**Tag:** `compositional-unordered-confirmed`.
**Merged-state gate:** **4492 passed / 12 skipped / 1 xpassed / 0 failed**, `test_cli` **256**,
containerised full run on Linux with live FalkorDB, 33m45s, at `ffe7bf0` (which contains
`origin/main` `6f089c5`). Baseline 4472 at `0496e7f`; the delta is CORE-C3R1's ship, #113's
signature sweep, and this item's net +2 tests. Pre-filter: `tools/check_adr_status_consistency.py`
green at 204 ADRs.

**Reads with:** `docs/decisions/adr/0205-abstraction-levels.md` **§amendment-3** (the decision
record), `CORE_C2_DECISIONS.md` §2 and §9.2, `CORE_RECONCILIATION_PLAN.md` §3 and §12,
`CORE_VERIFIED_FINDINGS.md` §13.

---

## 1. What shipped

**P8-A is lifted.** `Metagraph` validation **step 10** refused `compositional=True` with
`ordered=False`. It is retired in **both** `add_intergraph_hyperedge` and
`update_intergraph_hyperedge`; the update copy was already unreachable, because the early
compositional refusal means `ihe.compositional` is always `False` by the time control reaches
it. The slot is kept as a comment so the locked **P14-A** 16-step order stays legible, and the
comment carries the argument rather than pointing at a document.

**It is a deliberate override, not a restoration.** ADR-0205 §am-1.1 located the original
rationale in `INTERGRAPH_EDGES_DESIGN.md` (*"compositional implies identity-bearing composition
… set semantics is incompatible"*), and §am-2.3 established that **no citation of ADR-0148
supports the override** — 0148's own claim that `ordered=False` is the compositional default was
a reconstruction error, corrected at ADR-0148 §am-1. The override stands on its own ground:

> `ordered` expresses a **total** order over members. A plan's milestones are a **set** whose
> **partial** order lives in sibling dependency links, so that *parallel* is the **absence** of
> a link (ADR-0206 §2). An ordered member list cannot express a partial order ⟹ without the
> lift, **a plan with two parallel milestones is inexpressible.**

The identity argument survives for the cases it was written about. `ordered=True` compositional
links remain expressible and `cat = c + a + t` is unaffected — pinned by a test.

## 2. Behaviour, pinned

`TestStep10CompositionalOrderedFalseRefusal` becomes `…Permitted`. Four assertions:

| | |
|---|---|
| compositional + `ordered=False` **constructs** | the lift |
| members are **sorted and deduped** | `ordered=False` set semantics is unchanged by the lift |
| dedup-collapse to **1-1 still refuses** at step 8 | P14-A survives; a single-member composition is an `IntergraphEdge` (§am-1.2) |
| `cat = c + a + t` still constructs | `ordered=True` compositional is untouched |

## 3. Three rulings recorded here, built later

- **§am-3.2 — a pipeline's step order is DERIVED.** Recomputed from the steps' `CONSUMES` /
  `PRODUCES` plus the start DataStates (topological sort, **first-by-IRI** tie-break), never
  stored. A stored member order **can contradict** the level below and the model cannot detect
  it; a derived order cannot, because it *is* those declarations. Same criterion ADR-0192 used.
  **Stored form only** — `Pipeline.steps`, `execute_pipeline` and every brain-facing call are
  unchanged. A capacity firing twice in one stored pipeline becomes inexpressible, which is
  intended (defect **D-E**; repeated application is collection → map). **Lands at C2R4.**
- **§am-3.3 — D1 is CLOSED by having no consumer**, so `mindsos_core` is **not** amended and
  §am-1.5's terminality stands. Pipelines carry no confidence; the milestone confidence is
  *appropriateness*, **child → parent**, which is **same-graph 1-1** and therefore a plain
  intra-graph `Edge` under §am-1.3 (Ruling A); `in_force` must not exist because dormancy is
  derived on read. **Re-opens at C2R5**, with the first item that writes.
- **§am-3.4 — a pipeline with no steps is not a pipeline.** Requested of CORE-C3 as an
  `already_held` distinction on `FindVerdict`; **C2R4 refuses it at the store if C3 declines.**

## 4. Four findings — `CORE_VERIFIED_FINDINGS.md` §13

1. **An ordered hyperedge's member order does not survive persistence.** The builder writes
   `:MEMBER` with no ordinal (`MERGE` collapses duplicates); the loader reads
   `collect(DISTINCT …)`; the loader selects `ih.ordered` and never passes it; and a reloaded
   metagraph is schema-less, so P9-A re-derives `ordered=True` regardless. `FalkorDBLocalPersister`
   is this path. **Reachability: DECLARED, not live** — nothing above `mindsos_core` writes a
   hyperedge yet, and C2R4 would have been the first. **This is why §am-3.2 derives.**
2. **`MetagraphView` has no intergraph accessor at all.** §12.1 named only `KLWriteHandle`;
   `get_edges` / `step` are intra-graph. **C2R3's scope is the read path as well.**
3. **Zero-step pipelines are storable today** — `learn_pipeline` validates only the codec
   round-trip, which an empty pipeline passes.
4. **§12.7 is withdrawn** — `input_group` blocks nothing.

## 5. What C2R3 inherits

- The **read** half of the link mechanism, not only the write half (§13.2).
- The persistence defect in §13.1 is **not** C2R3's to fix — §am-3.2 removes the ladder's
  exposure to it. If a later item ever needs an ordered hyperedge to round-trip, it fixes the
  builder and loader then, with a test that asserts order and duplicates survive. **No such
  test exists today**, which is why the gate is silent about it.
- The **resource graph** (`CORE_RECONCILIATION_PLAN.md` §12.2) ships as C2R3's **first
  consumer**, immediately after it and not inside it.

## 6. Method note — three corrections this item made to its own evidence

Recorded because all three have the same shape and the third is the reason the rule is now
written down.

1. *"RULES §9 does not exist"* — asserted from an unfetched worktree. It landed at `64cfd34`.
2. *"`projects/amii_study/ondevice_profile.py` is a live declaration in this repo"* — it is
   **untracked**, absent from `origin/main`, and was **deleted** at `0943d4b`. Residue of a
   deletion, read out of a checkout by `grep -rn`.
3. *"`origin/main` is merged into `feat/core-c2r2`"* — written up as done in two coordination
   sections before the merge was ever run.

> **A claim about "the repo" is a claim about refs**, and **a claim about state is a claim you
> have read.** `git grep <ref>` / `git ls-files`, not `grep -rn` over a checkout — a checkout
> contains deleted files and other lanes' leftovers. `git log --all -- <path>` before calling a
> path absent. The **branch** for "merged"; the **gate** for "green". An intention written in
> the past tense is indistinguishable from a fact to every later reader.

`CORE_C3R1_COORDINATION.md` logged six instances of the first form across five chats in one
round before this item added the third form. It is not an individual failure mode.
