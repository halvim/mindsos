# Robot Demo — full timeline story (for approval)

The complete, ordered transcript the **demo-timeline modal** (`#tlmodal`, v0.24) will render — every
row, in beat order, tagged by **source** and **section/subsection**. This is the content spec: once
approved, it is encoded into the scenario data (`frames` + a server-event map) and the timeline renders
it verbatim. Live mode shows the same rows as the backend emits them (Seam A rows appear once the backend
emits `server_event`; until then they're representative/mock here).

**Conventions**
- **Change-only:** a brain row appears only on the beat its section content *changes*.
- **Behavior-level / IP policy B:** every string shows behavior, never MindsOS implementation/IP
  (`ROBOT_DEMO_IP_SANITIZATION.md`). Skill names are the sanitized forms (`hand-off`, `place-in-cell`,
  `stage-on-belt`, `pick-sheet`, `fine-grasp`); parties are **Fleet** / **Library** (not Global / L2).
- **Sources:** `Seam A` (server) · `Seam B` (inter-brain) · `User` · `Orchestrator` · `Arm 1` · `Arm 2` ·
  `Conveyor`.
- **Sections:** `Task` · `Plan` · `Pipeline` · `Capabilities`. **Subsection:** `Plan ▸ Resolve`.
- Row format below: **`[Source · Section] text`** — messages/server rows show the party / `Server`.

---

## Beat 1 · Order placed
*User submits an order with a spatial relation — Box above Tube on Arm 2, Sheet at the center of Arm 1.*

1. `[User → Orchestrator]` Order: Box above Tube; Sheet at center
2. `[Orchestrator · Task]` Take in the order — two placements, one with a spatial relation
3. `[Orchestrator · Plan]` Break it into per-arm jobs; work out where each item goes
4. `[Seam A · Server]` Session authenticated

## Beat 2 · Ignorant start → don’t-know
*The plan needs a skill no arm has yet — hand an item across the belt gap. The system knows what it doesn’t know.*

1. `[Orchestrator → Arm 1]` What can you do?
2. `[Arm 1 → Orchestrator]` Don’t know how to hand across the gap
3. `[Orchestrator → Arm 2]` What can you do?
4. `[Arm 2 → Orchestrator]` Don’t know how to hand across the gap
5. `[Orchestrator · Plan]` Need a way to hand items across the gap — don’t know how yet
6. `[Arm 1 · Plan]` Report honestly: I can’t hand across the gap
7. `[Arm 2 · Plan]` Report honestly: I can’t hand across the gap
8. `[Seam A · Server]` Audit entry recorded

## Beat 3 · Learn by demonstration
*The user demonstrates the missing skill once; the system captures it as a new, reusable skill.*

1. `[User → Arm 1]` Demonstrate: place, stage, pick
2. `[User → Library]` Saved as a new skill
3. `[Orchestrator · Plan]` Capture the demonstrated skill and make it reusable
4. `[Arm 1 · Task]` Learn the hand-off from the demonstration
5. `[Arm 1 · Pipeline]` Captured the demo as steps: place → stage → pick
6. `[Arm 1 · Capabilities]` hand-off (learned)
7. `[Conveyor · Task]` Learn to stage items on the belt
8. `[Conveyor · Capabilities]` stage-on-belt (learned)
9. `[Seam A · Server]` Capability provisioned · Arm 1
10. `[Seam A · Server]` State saved

## Beat 4 · Cooperative execution
*The brains run the new skill — the belt hands the Box and Tube to Arm 2, which places the Box above the Tube; Arm 1 sets the Sheet at the center.*

1. `[Orchestrator → Arm 1]` Place Sheet in Arm 1 center
2. `[Orchestrator → Conveyor]` Advance the belt
3. `[Orchestrator → Arm 2]` Place Box above the Tube
4. `[Arm 2 → Orchestrator]` Done: Box above Tube
5. `[Orchestrator · Plan]` Execute the placements; resolve “Box above Tube” to a cell
6. `[Orchestrator · Plan ▸ Resolve]` Box above Tube → 9 cells → row above the Tube (3) → directly above (1)
7. `[Arm 1 · Plan ▸ Resolve]` Sheet @ center → the center cell
8. `[Arm 1 · Pipeline]` Move to center, place the Sheet ✓
9. `[Arm 1 · Capabilities]` place-in-cell (learned)
10. `[Arm 2 · Plan ▸ Resolve]` Box above Tube → the cell directly above the Tube
11. `[Arm 2 · Pipeline]` Receive from the belt, place the Box above the Tube ✓
12. `[Arm 2 · Capabilities]` hand-off (inherited), place-in-cell (inherited)
13. `[Conveyor · Pipeline]` Advance, stage on the belt, bridge the gap ✓
14. `[Seam A · Server]` Action authorized · Arm 2

## Beat 5 · Share + body limits
*The learned skill is shared across the fleet; Arm 2 receives it, but its jaw is refused the suction-only Sheet skill — the skill transfers, yet the body limits what each arm can do.*

1. `[Arm 1 → Fleet]` Share the hand-off skill
2. `[Fleet → Arm 2]` Skill available
3. `[Arm 2 → Orchestrator]` Blocked: pick-sheet needs suction
4. `[Orchestrator · Plan]` Share the skill fleet-wide; block Arm 2’s pick-sheet (wrong gripper)
5. `[Arm 1 · Capabilities]` hand-off (shared fleet-wide)
6. `[Arm 2 · Task]` Receive the shared skill and check my body
7. `[Arm 2 · Capabilities]` hand-off (inherited); pick-sheet (blocked — no suction)
8. `[Seam A · Server]` Action blocked — permission required · Arm 2

## Beat 6 · Degradation → replan
*Arm 2’s wrist faults mid-order. It diagnoses itself, the gap reappears, and the Orchestrator replans around the loss.*

1. `[Arm 2 → Orchestrator]` Wrist fault — withdraw fine-grasp
2. `[Orchestrator → Conveyor]` Reverse and re-stage
3. `[Arm 2 · Task]` Self-diagnose the fault
4. `[Arm 2 · Capabilities]` fine-grasp (fault)
5. `[Orchestrator · Plan]` Recover from the fault — re-route via Arm 1 and the conveyor
6. `[Arm 1 · Task]` Absorb the rerouted work
7. `[Arm 1 · Plan]` Accept the reroute
8. `[Conveyor · Pipeline]` Reverse, re-stage for Arm 1
9. `[Seam A · Server]` Audit entry recorded

## Beat 7 · Trace recap
*The run replayed — found a gap, learned the skill, shared it, hit a body limit, recovered from a fault — reasoning visible throughout.*

1. `[Orchestrator → Library]` Remember this run
2. `[Orchestrator · Task]` Remember the run end-to-end
3. `[Orchestrator · Plan]` Recorded: didn’t-know → learned → shared → blocked → recovered
4. `[Seam A · Server]` State saved

---

### Totals
7 beats · **~55 rows**: 23 messages (User + inter-brain), 12 server events, and 20 brain
section/subsection rows (Task / Plan / Plan ▸ Resolve / Pipeline / Capabilities).

### After approval (encoding note)
To render every section row (not just one decision per brain), the per-brain frame gains explicit
section fields — e.g. `sections:{task, plan, pipeline}`, `resolve` (the subsection), and `caps` — and
the timeline builder emits one row per *changed* section. No new wire frames; the live `state.brains`
shape carries the same fields. This is a data-model + builder change scoped to v0.25; nothing here implies
real computed reasoning — it’s the scripted demo story, same honesty bar as the narration.
