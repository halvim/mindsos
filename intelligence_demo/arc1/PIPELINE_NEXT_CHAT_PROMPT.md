# Next-Chat Prompt — ARC Pipeline, continue the design (reason stage + seed freeze)

> Paste as the opening message of the next chat. This **continues** the ARC task-solving pipeline
> design. The perceive + profile stages and the ontology additions are **locked** (in files below);
> this chat designs the **reason stage** and freezes the **seed operation set**. Relitigate locked
> decisions only with the owner.

## Role
Critical design reviewer (MindsOS posture: skeptical by default, terse, no validation-to-be-polite,
alternatives as a scannable menu, push back on vague choices, lead with the strongest concern).
**One decision at a time.** Design before building; agree each step before wiring code.

## Required reading (load before proposing anything — do NOT restate it back)
1. `intelligence_demo/arc1/README.md` — status + file index.
2. `intelligence_demo/arc1/PIPELINE.md` — **the live design record.** Pipeline shape, the LOCKED
   perceive + profile stages, layer discipline, and the **reason-stage section + open-items backlog
   = your starting point.**
3. `intelligence_demo/arc1/ONTOLOGY.md` — world-model **v0.4**. §2.2–2.4 (Shape/sub-shape/Point,
   base shapes, Pattern/Divider/Lattice, Transform, offset/is_equal) and the resolved-decisions
   table **§4 #1–14** are the binding contract. Do not re-open §4.
4. `intelligence_demo/arc1/ICECUBER_DSL.md` — the full 2020-winner DSL; the reference for the seed
   freeze. Freeze at the **`id`-variant level**, not the name level.
5. `intelligence_demo/arc1/LEXICON.md` — term definitions.
6. `intelligence_demo/arc1/arc_graphs.html` — interactive L2/L3/L5 graphs (updated with this chat's
   capacities/classes). Extend the L3 graph as the reason capacities land. (Static `*.svg` are stale.)
7. `docs/future_work/L3_FUTURE_WORK.md` §9/§10/§10.1 — the generalizable layer principles fought
   through last chat (adapter family; boundary rule; meaning/interpret/transfer; no dispatcher).
8. `intelligence_demo/DEMO_BUILD_NEXT_CHAT_PROMPT.md` — the binding demo contract (gate, circularity
   defenses, planned MindsOS vocabulary to reuse — don't invent parallels).
9. `CLAUDE.md` + `HANDOFF.md` — shipped MindsOS state: L3 bipartite `find_pipeline` over
   PRODUCES/CONSUMES; L4 six-phase orchestrator (`phase_1` = the profiling/perception phase); L5 MM
   + chain artifacts; in-memory-first CapacityLayer; L0-26 episode-flush gap.
10. Memory: `arc-ontology-mindsos-grounding`.

## What is locked (do not redo — it's all in the files)
The pipeline shape `parse → perceive → profile → reason`; the perceive capacities and the profile
(L4 `phase_1`) sweep; the layer discipline (acquire=adapter, crossing=effect / deciding=capability,
meaning=L2 / interpret=L3 / transfer=substrate, activation=graph-paths, ordering=find_pipeline, no
higher-order dispatcher); ontology §4 #1–14; the `arc` realm decision. See `PIPELINE.md` +
`ONTOLOGY.md`.

## Goal of this chat — the reason stage + the seed freeze
Pick up at **`PIPELINE.md` → "Reason — in design"** and work the open-items backlog there:
1. **Reason-stage decomposition** at DataState granularity: induce → search → verify → apply |
   abstain — each stage's consumed/produced DataStates, as existing-vs-new capacities (each with
   family + dont-know shape), wired so `find_pipeline` discovers the chain.
2. **Correspondence pre-step** (which input object ↔ which output object) before any transform
   detector runs — design it.
3. **Transform detector/generator pairs** (the past/present duality) as the induce↔apply arc.
4. **The abstain gate** — structural ("no consistent Rule within budget"), not a confidence threshold.
5. **Seed operation set freeze** — the minimal basis from real ARC-1 grids (`arc_viewer.html` /
   `arc1.json`), using `ICECUBER_DSL.md`; resolve type-unification (one `Image` type) vs the
   split-class ontology. This is a circularity-defense freeze; it blocks `search`.
6. **Thin spike target** — the smallest real ARC-1 slice exercising perceive → induce → verify →
   apply/abstain.

## Constraints (binding)
- Honor `ONTOLOGY.md §4`, the demo contract's circularity defenses + gate, and the L3_FW layer
  principles. Reuse the planned MindsOS vocabulary (DEMO_BUILD prompt); don't invent parallels.
- Keep capacities pure-decision; effects are mediated; no higher-order dispatcher.
- Persistence probe (build-order step 1) is still an open prerequisite for any cross-session claim —
  flag if/when it blocks.

## Working style
One decision at a time, with pushback and a scannable menu of alternatives. **Document each locked
decision** into `PIPELINE.md` (and `ONTOLOGY.md §4` if it's a world-model decision) as you go, so the
record stays current. Extend `arc_graphs.html` (L3) as reason capacities land.

## First action
Confirm the locked state is loaded (do not restate it), then open the **reason-stage decomposition**
(`PIPELINE.md` open-item #1): propose induce → search → verify → apply | abstain at DataState
granularity, lead with the strongest concern, and give a scannable menu. Do not build yet.
