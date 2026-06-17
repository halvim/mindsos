# ARC track — status & index

**Status:** Step 1 (Ontology) COMPLETE; **Step 2 (Task-Solving Pipeline) — IN DESIGN** (2026-06-15).
This folder is the ARC foundation for the intelligence demo (see `../DEMO_BUILD_NEXT_CHAT_PROMPT.md`
for the binding demo contract + build order + gate). The ontology work here is the
Skill-Acquisition byproduct that the pipeline phase builds on.

**Pipeline progress (2026-06-15):** `ONTOLOGY.md` is at **v0.6** (decisions §4 #1–15). The pipeline
is now in **active build** via the **M-series spike** (`spike/` — see `spike/README.md`): perceive +
profile LOCKED & built; **induce partially built** (`same_object`/`same_shape`/`same_point`/`moved`
+ hypotheses fold + operand **Arc metagraph** overlay) with a human debug interface. The **reason
stage** (search → verify → apply | abstain) **+ the seed-operation freeze remain open** — the next
chat's work. Canonical records: `PIPELINE.md` (Build progress + Parked problems) and `ONTOLOGY.md` §4.

## What's here

| File | What it is |
|---|---|
| `arc1.json` / `arc1_data.js` | ARC-AGI-**1** dataset (400 train + 400 eval), per-task input/output pairs. Sourced from the `arckit` PyPI bundle (verified canonical ARC-1, *not* ARC-2). |
| `arc_viewer.html` | Standalone puzzle browser — pick any task, train/eval toggle, hide-answer quiz. |
| `LEXICON.md` + `arc_lexicon_map.svg` | The named terms + definitions (MindsOS L2 `lexicon`). Map = the detailed visual. |
| `ONTOLOGY.md` | **The canonical world-model record** (v0.4). Class+relationship model (L2 `ontology`), capacity→family map (§3), **resolved-decisions table (§4 #1–14)**. |
| `PIPELINE.md` | **The pipeline design record.** Stage decomposition, locked perceive + profile capacities, layer discipline, reason-stage backlog. |
| `ICECUBER_DSL.md` | Full DSL of the 2020 ARC winner (`top-quarks/ARC-solution`) — reference for the seed-operation freeze. |
| `arc_graph_L2_ontology.svg` · `_L3_capacity.svg` · `_L5_mm_instance.svg` | **Static layer graphs — STALE** (pre-pipeline export; `arc_graphs.html` is the source of truth). |
| `arc_graphs.html` | Interactive viewer of all three graphs (updated this chat) — draggable nodes, Edit/Lock, zoom. |
| `spike/` | **The runnable spike** — live `CapacityLayer`, perceive/profile/induce capabilities, hypotheses, Arc metagraph, and the `arc_debug.html` human interface. See `spike/README.md`. |
| `PIPELINE_NEXT_CHAT_PROMPT.md` | **Opening prompt for the next chat** (continue the pipeline — reason stage). |

## What was decided (do not relitigate)

All locked decisions are in **`ONTOLOGY.md §4`** with rationale throughout the file.
Headlines: OWL structure (no DOLCE); composition = native `compositional` hyperedge;
monochrome `Object` atom + `Group` via `add`; `Shape` = colorless connected `PointSet`
*individual*; roles = `<family>:<role>` subproperties (compositional/relational/functional);
is-a split (`subclass_of`/`instance_of`/`exemplifies`); relations computed by capacities +
materialized into the task MM; capacities map onto the shipped L3 families.

## Open items carried forward

- **Reason stage** — induce → search → verify → apply | abstain (the next chat; see `PIPELINE.md`).
- **Seed operation set freeze** — freeze the minimal basis at the `id`-variant level using `ICECUBER_DSL.md`; decide type-unification vs the split-class ontology. Blocks `search`.
- **Verify DataState realm names** against the live L3 when an instance is stood up (the `arc` realm).
- **Persistence probe** (build-order step 1) — minted capacity + `learned-parameters` survive a restart? Still an open prerequisite for any cross-session claim.
- Re-export the static `arc_graph_*.svg` from `arc_graphs.html` (currently stale).

## Next phase

Continue the task-solving pipeline design (reason stage) — see `PIPELINE_NEXT_CHAT_PROMPT.md`.
