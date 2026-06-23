# Robot Demo — timeline story (v0.26 REBUILD, in progress)

The content the demo-timeline modal (`#tlmodal`, shipped v0.24) renders: a chronological, change-only
transcript, tagged by source + section/subsection. **This is a working spec being rebuilt beat-by-beat
with the user.** Once a beat's rows are approved they are encoded into the scenario data (`frames` + the
builder) and the modal renders them verbatim.

> **Branch note (2026-06-22):** the original v1 of this doc + `ROBOT_DEMO_SCENARIO.md` +
> `ROBOT_DEMO_IP_SANITIZATION.md` live on the **`robot-demo-animation`** branch and are **NOT on
> `demo/robot`** (this worktree). The two robot branches have diverged — see §"Environment" below and
> the next-chat prompt. This file is recreated here so the v0.26 design output isn't lost; reconcile
> when the branches merge.

## Status
- **v1 REJECTED by the user** — too thin: it skipped perception + the actual feasibility reasoning, and
  split Submit from the dont-know across its beats 1 & 2.
- **Method (decided 2026-06-22):** work beat-by-beat WITH the user. For each beat: (1) enumerate ALL
  actions/comms exhaustively (the superset), then (2) a curation pass collapses + sanitizes (IP policy B)
  into the actual render rows. Encode only after the user approves a beat's rows.
- **Beat 1 = enumerated below (this chat).** Beats 2–7 = TBD in the next chat.
- **Beat 1 CURATED + APPROVED 2026-06-22** — the 39-event superset (intake → don't-know) was sliced
  into **7 finer beats** and curated to a **19-row render** (see "CURATED RENDER" below). Curation
  decisions: Q1 collapse (Beat 5 capability exchange 6→1 row; perception 4→2); Q2 **drop** the Seam-C
  body-reach row (no `seamC` source key; mechanism not behavior); Q3 **keep** the Conveyor query; Q4
  order **locked** (Box above Tube → Arm 2; Sheet at center → Arm 1). All display strings verified
  against `ROBOT_DEMO_IP_SANITIZATION.md` (now on this branch) — no uncovered tokens.

## Conventions
- **Change-only:** a brain row appears only on the beat its section content *changes*.
- **IP policy B:** every string is behavior-level, never MindsOS implementation/IP. Parties = **Fleet** /
  **Library** (not Global / L2). (Canonical map: `ROBOT_DEMO_IP_SANITIZATION.md` — currently on
  `robot-demo-animation`; the demo_ui IP-guard test encodes the rule here.)
- **Sources:** Seam A (Server) · Seam B (inter-brain) · User · Orchestrator · Arm 1 · Arm 2 · Conveyor ·
  (Seam C body, if surfaced).
- **Sections:** Task · Plan · Pipeline · Capabilities. **Subsection:** Plan ▸ Resolve.
- Channels/fields the rows draw from: `ROBOT_DEMO_WS_CONTRACT.md` (`message`, `state.brains`, `server_event`,
  `resolve`).

---

## Beat 1 · Order placed — FULL enumeration (superset; curate before encoding)

Redefined: **from just-after Submit → the dont-know realization** (this MERGES v1's beats 1+2). 39 candidate
events across 9 sub-phases. Format: `[Source → Target · Channel/Section]` behavior-text — *(real mechanic, internal)*.

**A. Submit & intake**
1. `[User → Orchestrator · cmd]` Order placed: Box above Tube (Arm 2); Sheet at center (Arm 1) — *(place_order)*
2. `[Seam A · Server]` Order received — *(manager session receives request)*
3. `[Seam A · Server]` Request authorized — *(capability auth; gate ✓)*
4. `[Seam A · Server]` Audit entry recorded — order received
5. `[Orchestrator → User]` Got it — working on your order — *(ack callout)*

**B. Perception / world intake (NEW vs v1 — the big add)**
6. `[Orchestrator · Task]` Look at the table — *(fiducial → symbolic world graph; L3 perception)*
7. `[Orchestrator · Task]` Found three items: a Box, a Tube, a Sheet
8. `[Orchestrator · Task]` Match each requested placement to a real item — *(order is by attribute, not ID)*
9. `[Orchestrator · Task]` Build the picture of the world — items, shelves, the belt gap

**C. Understand the order**
10. `[Orchestrator · Task]` Take in the order — two placements, one spatial relation — *(L5 HintSet)*
11. `[Orchestrator · Plan]` One placement is relative (Box above Tube), one is fixed (Sheet at center)

**D. Choose an approach**
12. `[Orchestrator · Plan]` Have I done this kind of job before? — *(retrieve task-patterns; L5 MappingResult)*
13. `[Orchestrator · Plan]` Approach: break the order into per-arm jobs

**E. Decompose & allocate**
14. `[Orchestrator · Plan]` Break the order into per-arm jobs — *(L3 decomposition)*
15. `[Orchestrator · Plan]` Sheet at center → Arm 1 (left side)
16. `[Orchestrator · Plan]` Box above Tube → Arm 2 (right side)
17. `[Orchestrator · Plan]` Box & Tube start on Arm 1's side — they must cross to Arm 2 — *(reach geometry)*

**F. Discover what each brain can do (Seam B — query-capabilities)**
18. `[Orchestrator → Arm 1]` What can you do? / `[Seam A]` Read authorized — Arm 1
19. `[Arm 1 → Orchestrator]` I can move and grip
20. `[Orchestrator → Arm 2]` What can you do?
21. `[Arm 2 → Orchestrator]` I can move and grip
22. `[Orchestrator → Conveyor]` What can you do? — *(v1 skipped this; Conveyor is the only bridge — OPEN Q3)*
23. `[Conveyor → Orchestrator]` I can move the belt and hold items

**G. Assemble the plan & test feasibility (the WHY — 2nd big add)**
24. `[Orchestrator · Plan]` Assemble the steps: place the Sheet; get Box+Tube across; place them — *(L4 plan)*
25. `[Orchestrator · Plan]` Placing into a shelf cell — does any arm know how? — *(no `place-at-cell` composite)*
26. `[Orchestrator · Plan]` Crossing the gap — is there a way to hand an item across? — *(no hand-off Plan)*
27. `[Seam C · Arm body]` The arms can't reach the middle of the belt — *(reach-envelope check — OPEN Q2)*
28. `[Orchestrator · Plan]` No brain can hand items across — and none knows the placement skill — *(feasibility fails)*

**H. The don't-know (family-specific dont-know contract)**
29. `[Orchestrator → Arm 1]` Do you know how to hand an item across the gap?
30. `[Arm 1 → Orchestrator]` Don't know how to hand across the gap — *(report dont-know; flag gap)*
31. `[Orchestrator → Arm 2]` Do you know how to hand an item across the gap?
32. `[Arm 2 → Orchestrator]` Don't know how to hand across the gap — *(flag gap)*
33. `[Arm 1 · Plan]` Report honestly: I can't hand across the gap
34. `[Arm 2 · Plan]` Report honestly: I can't hand across the gap
35. `[Orchestrator · Plan]` Need a way to hand items across the gap — don't know how yet — *(headline; flag gap)*
36. `[Orchestrator · Capabilities]` Gap noted: hand-off is missing — *(writes capacity-gap)*

**I. Surface & persist**
37. `[Orchestrator → User]` I don't know how to do this yet — can you show me? — *(gap notification / demo prompt)*
38. `[Seam A · Server]` Audit entry recorded — gap detected
39. `[Seam A · Server]` State saved — *(gap persisted; episode recorded)*

### Open curation questions (decide with user before encoding Beat 1)
1. **39 is too many rows** — collapse (e.g. the 3 query round-trips 18–23 → one Seam-B exchange; perception 6–9 → 2 rows).
2. **Render the Seam-C body-reach row (27)?** Or is reach geometry too much mechanism for the behavior-level view?
3. **Include the Conveyor capability query (22–23)?** Or keep Seam B arms-only like v1?
4. **Confirm the Beat-1 order is LOCKED** = "Box above Tube (Arm 2) + Sheet at center (Arm 1)" (matches the baked frames).

---

## Beat 1 · CURATED RENDER — APPROVED 2026-06-22

The approved render set for the intake → don't-know region: **7 beats, 19 numbered steps.** This is
what the demo-timeline modal displays verbatim once encoded. Legend: **[COMM]** inter-party
communication · **[DEC]** brain decision (card section) · **[ACT]** system action (Seam A server
event). `cbeat` = 0-based global storyline beat. *internal:* = the real mechanic, **never displayed**
(IP policy B) — recorded here for fidelity only.

### Beat 1 · Order placed — `cbeat 0` (sections: Task)
1. **[COMM]** User → Orchestrator — "Order: Box above Tube; Sheet at center" · *internal: place_order*
2. **[ACT]** Seam A · Server — "Session authenticated" · *internal: manager session opens (login)*
3. **[DEC]** Orchestrator · Task — "Break down the order; work out where each item goes" · *internal: order intake*

### Beat 2 · Look at the table — `cbeat 1` (sections: Task)
4. **[DEC]** Orchestrator · Task — "Look at the table — found a Box, a Tube, and a Sheet" · *internal: fiducial → symbolic world graph; perception*
5. **[DEC]** Orchestrator · Task — "Match each requested placement to a real item" · *internal: order is by attribute, not ID*

### Beat 3 · Understand the order — `cbeat 2` (sections: Task, Plan)
6. **[DEC]** Orchestrator · Task — "Two placements, one spatial relation" · *internal: HintSet*
7. **[DEC]** Orchestrator · Plan — "One placement is relative (Box above Tube), one is fixed (Sheet at center)"
8. **[DEC]** Orchestrator · Plan — "Done this kind of job before? — break it into per-arm jobs" · *internal: retrieve task-patterns; MappingResult*

### Beat 4 · Split into per-arm jobs — `cbeat 3` (sections: Plan)
9. **[DEC]** Orchestrator · Plan — "Sheet at center → Arm 1 (left side)" · *internal: decomposition*
10. **[DEC]** Orchestrator · Plan — "Box above Tube → Arm 2 (right side)"
11. **[DEC]** Orchestrator · Plan — "Box & Tube start on Arm 1's side — they must cross to Arm 2" · *internal: reach geometry*

### Beat 5 · What can each brain do? — `cbeat 4` (Seam-B exchange, compressed)
12. **[COMM]** Orchestrator ↔ Arm 1 / Arm 2 / Conveyor — "Asked Arm 1, Arm 2 and the Conveyor what they can do → move & grip; move the belt & hold items" · *internal: query_capabilities() ×3, collapsed to one row*

### Beat 6a · No way across the gap — `cbeat 5` (sections: Plan — the climax)
13. **[DEC]** Orchestrator · Plan — "No brain can hand items across, and none knows how to place an item into a shelf cell" · *internal: feasibility fails (no hand-off plan, no place-at-cell composite)*
14. **[COMM]** Arm 1 → Orchestrator — "Don't know how to hand across the gap" · *internal: DONT_KNOW(handoff-via-belt)*
15. **[COMM]** Arm 2 → Orchestrator — "Don't know how to hand across the gap"
16. **[DEC]** Orchestrator · Plan **[gap flag]** — "Need a way to hand items across the gap — don't know how yet" · *internal: headline; writes the gap flag*

### Beat 6b · Ask for help & remember — `cbeat 6` (sections: Capabilities)
17. **[DEC]** Orchestrator · Capabilities — "Gap noted: hand-off is missing" · *internal: writes capacity-gap*
18. **[COMM]** Orchestrator → User — "I don't know how to do this yet — can you show me?" · *internal: gap notification / demo prompt*
19. **[ACT]** Seam A · Server — "Audit entry recorded · State saved" · *internal: gap detected + gap persisted (episode recorded)*

**Trimmed from the 39-event superset** (kept here for traceability): order-ack callout ("Got it…"),
the routine order auth/audit server rows (gate_ok is significant-only), the world-build perception row,
the restated decompose header, the per-arm "Read authorized" rows, the two feasibility-probe questions
("is there a way to hand across?" / "does any arm know the cell-placement?"), the explicit
"Do you know how…?" ask round-trips, and the two arm "Report honestly" decision rows (duplicate the
message replies). **Dropped:** the Seam-C arm-body reach row (Q2).

---

## Encoding (after all beats are curated)
Richer per-section row model — per-brain frame gains `sections:{task, plan, pipeline}` + `resolve` + `caps`;
the `timeline.js` builder emits one row per *changed* section. **Fold in `state.cbeat`** (shipped on the wire
2026-06-15; group the timeline by `cbeat`) and make `mock_ws_server.js` emit `cbeat` for the headless e2e.
No new wire frames — `state.brains` already carries these fields. Same honesty bar as the narration; nothing
here implies real computed reasoning, it's the scripted demo story.

## Environment (read before working — a prior chat got burned)
The robot demo spans **two unreconciled branches**: `demo/robot` (this worktree, `MindsOS-robot/` — has the
DM-7/DM-8 backend in `robot_demo/`, the active `ROBOT_DEMO_DM7_UI_COORDINATION.md`, and the **complete v0.25**
UI) and `robot-demo-animation` (has `ROBOT_DEMO_SCENARIO.md`, `ROBOT_DEMO_IP_SANITIZATION.md`, the old
`ROBOT_DEMO_UI_BACKEND_COORDINATION.md`). The main `MindsOS/` folder may be checked out to an unrelated branch
(`feat/composition-lifecycle`). Confirm you're in the robot worktree before editing; never git-mutate from the
sandbox (pair-execution: the user drives git on the Mac).
