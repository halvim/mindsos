# Robot Demo — UI v10 (live prototype) · design record

Canonical record of the **v10 dashboard UI** work. v10 is the live frontend that
reopened the frozen v9 freeze deliberately. This doc captures the decisions and the
file map; it does **not** restate code — read the files it points to.

> Companion docs (do not duplicate): `ROBOT_DEMO_STATUS.md` (workstream status),
> `ROBOT_DEMO_PROTOTYPE_PLAN.md` (§3 Phase plan, §4 the WS `state`/`brains` schema),
> `ROBOT_DEMO_OPEN_QUESTIONS.md` (§4 UI / §5 the v10 feature list), `ROBOT_DEMO_SCENARIO.md`
> (the 7 beats + graph-moments). The reference *maps* below are the source of truth for
> what each card part is **named** — use them to refer to parts.

## 1. What v10 is

- A **new** file, `demo_ui/presentation_v10.html`, branched from the frozen
  `demo_ui/presentation_mockup.html` (**v9 stays untouched**).
- Built as the **real frontend view layer fed by a mock data source** shaped like the
  future WebSocket `state`/`brains` payload (`ROBOT_DEMO_PROTOTYPE_PLAN.md §4`), so the
  Phase-D swap to live brains replaces the data source, **not** the view layer.
- Honesty tag retained: **"mock data · not wired to live brains."**
- **No Chromium in the Cowork sandbox** → all UI work is verified headlessly. See memory
  `robot-demo-ui-verification` (pure sidecar node tests + cairosvg rasterization); live
  click/layout is the user-confirmed part.

## 2. Files (all under `demo_ui/`)

- `presentation_v10.html` — the live dashboard (open directly; schematic 3D uses CDN three.js, no server).
- Sidecars (pure, node-testable): `graph_v10.js` (reasoning subgraphs), `teach_v10.js`
  (teach-tab curation model), `sections_v10.js` (brain-section content model).
- **Reference maps** (the part-name vocabulary — keep current with every card change):
  `orchestrator_card_map.png` (brain card), `user_card_map.png`, `button_map.png`.
- `maps/*.py` — the scripts that regenerate the three maps (run `python3 maps/<name>.py`).
- `presentation_mockup.html` — frozen **v9** baseline (reference only).

## 3. Shipped increments

- **v10.1 — Graph tab.** Per-section graph view (the `⌗` view-mode), animated across the
  7 scripted graph-moments. Data + renderer in `graph_v10.js`. **The graph content is a
  deliberate placeholder** — to be replaced once real server comms exist (it has no v1
  consumer beyond illustration).
- **v10.2a — Teach: Library + Inspect + teach-term.** Teach tab = Library / Teach term /
  Demonstrate. Teaching a Local position term flows it into the Order/Sort dropdowns.
  Model in `teach_v10.js` (node-tested). **Retire + Global override deferred → v10.2b.**

## 4. Design decisions settled this chat (the "why", not in code)

**Brain cards** (see `orchestrator_card_map.png` for part names):
- Sections (tabs) = **Task · Plan · Pipeline · Capabilities**, in that order. Overview/
  Hint/Map/P-Run were tried and removed. **All sections are always available** — the
  reach/not-reached gating was a fake and was removed.
- **Capabilities** section holds the capability list. **Flags are per-section**
  (`FLAG_SECTION`: fault→Task, gap→Plan, learn→Pipeline, promo+gate→Capabilities).
- **Intent** is pinned above the tabs; **decision** text shows inside Plan/Task (current
  default — movable on request).
- **View-mode** (Panel / graph) lives **inside each section** as icon-only buttons.

**Button system** (see `button_map.png`): one class **`.uitab`** drives every card tab/
toggle (brain sections, view-mode icons, User Order/Sort/Teach, Teach sub-tabs, teach-term
mode). Contract: idle = panel bg + **per-card accent** border + **white** text; selected =
**darker accent fill** (`color-mix(in srgb, var(--acc) 70%, #0e1116)`) + white text. Accent
is per card (Orchestrator purple / Arm 1 blue / Arm 2 orange / Conveyor green / User cyan
`#53b0be`). **All cards render identically — no inactive-brain dimming** (removed, so text +
icon colours match across all four). The **card state** is a spaced status **chip**.

**User card** (see `user_card_map.png`): tabs are **bordered groups** reflecting two kinds
of interaction — **TASK** box (Order + Sort = ask the system to do a task) and **CHANGE
SYSTEM** box (Teach). The gap between boxes is the divider. **Export / Import** carry tray
icons and are **reserved for system-state file import/export** (functionality TBD — current
layout-JSON behavior left in place). The **Edit layout / Layout** buttons were removed.

## 5. Backlog / next (deferred, in priority order)

1. **v10.2b** — Teach **Retire** (version-freeze + dependents block/cascade/warn) +
   **Global override → Local shadow** (`ROBOT_DEMO_OPEN_QUESTIONS.md §5`; `SCENARIO.md`).
2. **v10.3** — relation-resolution **target-cell highlight** (3×3 narrowing per clause) +
   **focus mode** for the brain panels (`OPEN_QUESTIONS §4`, offered-not-built).
3. **Export / Import → system-state files** — wire the retained buttons to real import/
   export of system state (replaces the placeholder layout-JSON handlers).
4. **Graph content** — replace the placeholder subgraphs with real per-section graphs once
   wired to live data.
5. *(Optional)* **Real-clip 3D cell** — on the execution beat, play the baked 46-clip set
   via the standalone player engine (`web/player.html`) instead of the schematic.
6. **Phase-D wiring** — connect to the real WS backend (DM-* in `ROBOT_DEMO_MINDSOS_PLAN.md`).
   The mock data already follows the §4 schema, so this is a data-source swap.

## 6. Working conventions (carried)

Critical-design-reviewer posture; restate a plan before implementing; one increment at a
time, each openable; verify headlessly before presenting; **keep the three maps current
with every card change**; v9 stays frozen; tabs/toggles are buttons inside the card body
(never the header). See memories `robot-demo-ui-v10`, `robot-demo-ui-verification`.
