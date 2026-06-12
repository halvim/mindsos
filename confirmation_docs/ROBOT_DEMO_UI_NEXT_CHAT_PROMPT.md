# Robot Demo — UI v10 next-chat prompt

Paste the block below to start the next UI chat. It points at files instead of repeating them.
(Last refreshed 2026-06-11, after v10.2b→v10.6 shipped + the live data-source seam.)

---

We are continuing the **MindsOS Robot Demo — v10 dashboard UI** (on-screen product version
**v0.10**; reaches **v1.0** when it runs on live brains end-to-end). The design and the decisions
to date are recorded — do **not** re-litigate settled choices. Read the files, then continue.

**Read first, in this order:**
1. `CLAUDE.md` (root) — project + working conventions.
2. `confirmation_docs/ROBOT_DEMO_UI_V10.md` — **the v10 design record: what v10 is, the file map,
   every decision settled (§3 shipped increments v10.1→v10.6, §4 design decisions, §7 open items),
   and the backlog (§5).** This is your entry point — read it fully.
3. `confirmation_docs/ROBOT_DEMO_STATUS.md` — the Robot Demo workstream status (note the 2026-06-11
   "LIVE-READY" update on the `demo_ui/` line).
4. `confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md` — the server↔browser WebSocket protocol the dashboard
   speaks in live mode (frame types, field-persistence rules, commands). Read this to understand how
   `?live=` works and what the backend (DM-4) must emit.
5. The three **reference maps** in `demo_ui/` — `orchestrator_card_map.png`, `user_card_map.png`,
   `button_map.png`. They name every card part; use them when the user refers to a part, and
   regenerate via `demo_ui/maps/*.py` after any change to a mapped card.
6. `demo_ui/presentation_v10.html` + sidecars `graph_v10.js` / `teach_v10.js` / `sections_v10.js` /
   `resolve_v10.js` / `datasource_v10.js` — the code. Open the html to see current state. Also
   `demo_ui/mock_ws_server.js` (reference live emitter) and `demo_ui/HOW_TO_USE.md` (run/share guide).
7. For deeper context only as needed: `ROBOT_DEMO_PROTOTYPE_PLAN.md` (§4 the canonical WS schema),
   `ROBOT_DEMO_OPEN_QUESTIONS.md` (§2 the retire-integrity OPEN MindsOS decision, §3 resolver, §4 UI),
   `ROBOT_DEMO_SCENARIO.md` (the 7 beats), `ROBOT_DEMO_MINDSOS_PLAN.md` (the DM-* backend track).

**Current state in one line:** the UI side of "go live" is **done** — mock by default, `?live=<wsurl>`
connects real brains over the contract in #4; the only thing left for an actually-live demo is the
**backend emitting those frames (DM-4+ in `ROBOT_DEMO_MINDSOS_PLAN.md`; DM-3 in progress)**, which is
a different chat. The two live-only panels (reasoning graph, Plan▸Resolve) are intentionally blanked
until the backend produces their data.

**Your task:** continue the UI per `ROBOT_DEMO_UI_V10.md §5` backlog — next up is **v10.3b focus mode**
(spotlight the active brain; could reuse the v10.4 `#maxbackdrop` dim mechanic), then **Export/Import →
system-state files**. Confirm the next increment with the user before building. If the user instead wants
backend/live work, that's the DM track — point them there rather than hacking the UI.

**Hard constraints / conventions (also in `ROBOT_DEMO_UI_V10.md §6`):**
- **No Chromium in the sandbox** — verify headlessly. Established pattern: pure-sidecar node tests +
  a jsdom harness (strip the three.js tag, inline the 5 sidecars, stub rAF/RO/canvas) + cairosvg
  rasterization for visual checks. Live click/layout is the user-confirmed part. See memory
  `robot-demo-ui-verification`. Re-run the existing suites after any change.
- **v9 (`presentation_mockup.html`) stays frozen** — never edit it.
- **Keep the three maps current** with every change to a mapped card (regen via `demo_ui/maps/*.py`).
- **Card body** holds tabs/toggles; the **header** holds window-level controls only (help `?`, 2D/3D,
  maximize). Don't put section tabs in the header, and don't put window controls in the body.
- Critical-design-reviewer posture; restate a plan for approval before implementing; one increment at
  a time, each openable/clickable; show option mockups (cairosvg PNG) for visual/ambiguous choices.
- The mock path must stay byte-identical by default; live behaviour is gated behind `?live=`.
- The user runs all git themselves on their Mac — never git-mutate from the sandbox.

Confirm you've read the files and restate the next increment before writing code.
