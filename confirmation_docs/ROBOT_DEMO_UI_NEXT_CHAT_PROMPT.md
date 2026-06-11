# Robot Demo — UI v10 next-chat prompt

Paste the block below to start the next UI chat. It points at files instead of repeating them.

---

We are continuing the **MindsOS Robot Demo — v10 dashboard UI** (the live, mocked frontend).
The design and the decisions to date are recorded — do **not** re-litigate settled choices.
Read the files, then continue building.

**Read first, in this order:**
1. `CLAUDE.md` (root) — project + working conventions.
2. `confirmation_docs/ROBOT_DEMO_UI_V10.md` — **the v10 design record: what v10 is, the file
   map, every decision settled so far, and the backlog (§5).** This is your entry point.
3. `confirmation_docs/ROBOT_DEMO_STATUS.md` — the Robot Demo workstream status.
4. The three **reference maps** in `demo_ui/` — `orchestrator_card_map.png`,
   `user_card_map.png`, `button_map.png`. These name every card part; use them when the
   user refers to a part, and regenerate them via `demo_ui/maps/*.py` after any card change.
5. `demo_ui/presentation_v10.html` + sidecars `graph_v10.js` / `teach_v10.js` /
   `sections_v10.js` — the code. Open the html to see current state.
6. For deeper context only as needed: `ROBOT_DEMO_PROTOTYPE_PLAN.md` (§3 phases, §4 the WS
   `state`/`brains` schema the mock follows), `ROBOT_DEMO_OPEN_QUESTIONS.md` (§4 UI / §5 the
   v10 feature list), `ROBOT_DEMO_SCENARIO.md` (the 7 beats + graph-moments).

**Your task:** continue v10 per the backlog in `ROBOT_DEMO_UI_V10.md §5` — next up is
**v10.2b** (Teach Retire + Global override), then **v10.3** (relation target-cell highlight +
focus mode). Confirm the next increment with the user before building.

**Hard constraints / conventions (also in `ROBOT_DEMO_UI_V10.md §6`):**
- **No Chromium in the sandbox** — verify headlessly (pure-sidecar node tests + cairosvg
  rasterization); live click/layout is the user-confirmed part. See memory
  `robot-demo-ui-verification`.
- **v9 (`presentation_mockup.html`) stays frozen** — never edit it.
- **Keep the three maps current** with every card change (regen via `demo_ui/maps/*.py`).
- Tabs/toggles are **buttons inside the card body**, never the header.
- Critical-design-reviewer posture; restate a plan for approval before implementing; one
  increment at a time, each something the user can open and click; show option mockups for
  approval on visual/ambiguous choices.
- The user runs all git themselves on their Mac — never git-mutate from the sandbox.

Confirm you've read the files and restate the next increment before writing code.
