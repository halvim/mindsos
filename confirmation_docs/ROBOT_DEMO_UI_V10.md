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
- **On-screen product version = `v0.10`** (the header badge), reaching **`v1.0`** when it runs on
  live brains end-to-end. NB: the *file/track* name `v10` (and the `*_v10.js` sidecars,
  `ROBOT_DEMO_UI_V10.md`) is the internal UI-iteration label — unchanged, distinct from the
  product version. A user request could rename the files later; not done now (large doc churn).
- A short end-user guide lives at `demo_ui/HOW_TO_USE.md` (run Demo/Live, share with others).
- **No Chromium in the Cowork sandbox** → all UI work is verified headlessly. See memory
  `robot-demo-ui-verification` (pure sidecar node tests + cairosvg rasterization); live
  click/layout is the user-confirmed part.

## 2. Files (all under `demo_ui/`)

- `presentation_v10.html` — the live dashboard (open directly; schematic 3D uses **vendored**
  three.js in `vendor/three.min.js` — no CDN, no server, fully offline as of v10.5).
- `vendor/three.min.js` — local three.js global build (IIFE, ~648 KB; esbuild-bundled from
  `web/vendor/three.module.js`, **REVISION 160**). Replaces the former r128 CDN `<script>`.
  Classic global build (not ES module) so the page still opens from `file://`.
- Sidecars (pure, node-testable): `graph_v10.js` (reasoning subgraphs), `teach_v10.js`
  (teach-tab curation model), `sections_v10.js` (brain-section content model),
  `resolve_v10.js` (relation-resolution narrowing — Plan ▸ Resolve subsection),
  `datasource_v10.js` (the **mock↔live data-source seam**; live WS client).
- `mock_ws_server.js` — runnable reference WS emitter (replays the 7 beats as live frames;
  `npm i ws && node mock_ws_server.js`). Dev-only; a worked example of the backend contract.
- **`confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md`** — the authoritative server↔browser WS
  protocol for the backend (what to emit for the dashboard to go live).
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
  Model in `teach_v10.js` (node-tested).
- **v10.2b — Teach: Retire + Global override (Hybrid controls).** Library rows carry a
  contextual **row-action icon** (`.rowact`: ⊘ retire / ⇄ override / ↺ restore) **and** the
  Inspect panel repeats the action as a labelled button (`.iact`) with context — chosen
  layout = **Hybrid** (Option C). **Retire** = reversible version-freeze (Local + learned
  only; builtins/Global are not user-retireable): the item stays in the Library struck-
  through and is dropped from the Order/Sort dropdowns + compose chips; **Restore** reverses
  it. **Global override** reuses Teach-term: the ⇄ action prefills the Global term's cells,
  the user edits + saves, and a **`Local-override`** shadow is written (resolves Local-first
  via `resolveTerm`; the Global stays untouched). The dependents notice (`.idep`) surfaces
  what depends on an item **but does not pick a retire-integrity policy** — that
  (block/cascade/warn) is left as an **open MindsOS decision**, see §7. New `teach_v10.js`
  exports: `retire`/`restore`/`isRetireable`/`overrideGlobal`/`resolveTerm`/`activeTermNames`/
  `dependentsOf` + `validateTermName(..,{overrideGlobal})`; a Global seed term `corner-pack`
  was added so there is something to override. Verified headlessly: `teach_v10.js` node test
  (19/19) + a jsdom DOM-wiring test of the live handlers (20/20) + inline-script parse.
- **v10.3a — Plan ▸ Resolve subsection (relation-resolution target-cell highlight).** Chose
  **A** (target-cell highlight) over the focus-mode half of the original v10.3; placed it
  **inside the Plan section as a "Resolve" subsection** (NOT a new top-level section — the
  four-section set stays settled). On a beat that resolves a spatial clause it renders a
  compact 3×3 grid that **animates the candidate set narrowing** (timed step-through, ~650 ms/
  step) — beat 3 "Box above Tube" goes 9 → 3 (row above the Tube) → 1 (tie-break: directly
  above) and the Box drops on the winner; Arm 1's absolute "Sheet @ center" resolves 9 → 1.
  Brains/beats with no resolution show a "no spatial relation resolved this beat" placeholder.
  **Snap-to-final guard:** every (re)start clears any in-flight timer, so fast beat-scrubbing
  can't strand a half-animation. Honest-tag discipline: the beats are scripted, so this SHOWS
  the resolution — `resolve_v10.js` is shaped like a future MappingResult chain-artifact, not
  a live solver. Verified headlessly: `resolve_v10.js` node test (13/13) + a jsdom test that
  drives the timed animation to the winner and the snap-to-final scrub (10/10) + inline parse;
  v10.2b regression re-checked (20/20).
- **v10.4 — Maximize-height button on every card (Option A).** A per-card header control
  (`.maxbtn`, inserted into `.hdrright` before `.help` on all 7 cards) that sets the card to
  **screen height** (`position:fixed`, `top` = 10 px, height = `innerHeight − 20`) with
  **width + x unchanged**, raises it over a dimmed `#maxbackdrop`, and flips the glyph to a
  restore icon. **One maximized at a time** (maximizing another restores the first); **Esc or
  backdrop-click restores**; restore returns the card to its stored LAYOUT box. The
  ResizeObserver is **guarded** so the maximized height is never written back into LAYOUT
  (would corrupt the saved layout). Glyph = vertical-expand (not a fullscreen square) since
  width is fixed. Verified via jsdom (18/18: per-card button, fixed-fill + pin-to-top,
  one-at-a-time, backdrop + Esc restore, width-unchanged, restore-to-LAYOUT-height) + inline
  parse; teach (20/20) + resolve (10/10) regressions re-checked. **Maps regenerated:**
  `orchestrator_card_map` + `user_card_map` now show `.maxbtn` (button_map unaffected —
  `.maxbtn` is not a `.uitab`).
- **v10.5 — Presentation hardening.** Three orthogonal fixes so a live showing can't fail on
  network/browser: (1) **Vendored three.js** — the r128 CDN `<script>` is replaced by local
  `vendor/three.min.js` (esbuild IIFE global, r160), killing the network dependency while
  keeping `file://` open-by-double-click (a classic global build, NOT an ES module, which
  `file://` would CORS-block). (2) **WebGL fallback** — `detectCaps()` on load; if WebGL is
  unavailable the cell auto-switches to the existing 2D canvas, hides the 3D toggle, and
  `init3D` is also wrapped in try/catch so a runtime renderer failure degrades gracefully.
  (3) **color-mix fallback** — if `CSS.supports('color-mix…')` is false, `body.nofx` swaps the
  color-mix selected-fills (`.uitab.on`/`.bsec.on`/`.maxbtn.on`/header tint) for solid-accent
  fills. A **dismissible `#capbanner`** names whichever fallback is active. NOT a browser
  hard-gate. Verified via jsdom (13/13: unsupported → nofx + banner + 2D forced + dismiss;
  supported → no banner, 3D toggle visible; no CDN ref remains; vendor file present) + the
  three prior suites re-checked (20/20 + 10/10 + 18/18). **Caveat to eyeball live:** r128→r160
  changed default lighting/color-space, so the 3D cell may render a touch darker than before;
  functionally fine, and the 2D fallback is unaffected. The remaining "present from a tested
  machine" advice (§7) still stands — vendoring removes the network risk, not the
  unknown-hardware risk.
- **v10.6 — Live data-source seam (mock ↔ live brains).** The dashboard's `states` array now comes
  from a `DataSource` (`datasource_v10.js`): `makeMockSource` (today's baked beats, byte-identical
  default) or `makeLiveSource` (a WebSocket client). Activated by **`?live=<wsurl>`** — no other
  change flips the demo from mock to live; the view layer is untouched. Live behaviour: opens the
  socket, flips the honesty tag (connecting → **live — connected** / disconnected / error),
  **follows** incoming `state` frames (unless the user scrubs back), appends `message` frames to the
  log, applies `pose` updates to the cell, and routes Submit/Play/Pause/Reset/Teach to `sendCommand`.
  The two **mock-only panels** (graph + Plan▸Resolve) are **suppressed in live** with a "feed not yet
  emitted" placeholder, since the backend has no producer for them yet. Wire protocol =
  `ROBOT_DEMO_PROTOTYPE_PLAN.md §4` made precise in **`ROBOT_DEMO_WS_CONTRACT.md`** (frame types,
  field-persistence semantics, commands, reference emitter). Reference emitter `mock_ws_server.js`
  replays the 7 beats. Verified headlessly: `datasource_v10.js` node test (15/15) + jsdom live-mode
  test with a stub socket (15/15) + **end-to-end over a real WebSocket** against the spawned mock
  server (7/7) + all four prior suites re-checked (20/20 + 10/10 + 18/18 + 13/13). **This is the
  UI-side completion of "go live"; the remaining work is the backend emitting these frames (DM-4+).**

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

1. **v10.3b — focus mode** for the brain panels (the second half of the original v10.3;
   target-cell highlight shipped as v10.3a). Spotlight the active brain (dim/scale others);
   the cheap, layout-safe version is dim-others + subtle scale, no reflow (`OPEN_QUESTIONS §4`).
   Could reuse the v10.4 `#maxbackdrop` dim mechanic.
2. **Export / Import → system-state files** — wire the retained buttons to real import/
   export of system state (replaces the placeholder layout-JSON handlers).
4. **Graph content** — replace the placeholder subgraphs with real per-section graphs once
   wired to live data.
5. *(Optional)* **Real-clip 3D cell** — on the execution beat, play the baked 46-clip set
   via the standalone player engine (`web/player.html`) instead of the schematic.
6. **Phase-D wiring** — connect to the real WS backend (DM-* in `ROBOT_DEMO_MINDSOS_PLAN.md`).
   The mock data already follows the §4 schema, so this is a data-source swap.

## 7. Open decisions documented for later (NOT decided in the UI)

- **Retire referential-integrity policy — open MindsOS decision (UI surfaces, does not
  decide).** When a retired item has dependents (modeled case: `stage-at-position`, which
  `handoff-via-belt` depends on), v10.2b shows the dependency (`.idep` notice) and lets the
  user proceed reversibly. The actual semantic is a single parameter left open for a future
  MindsOS chat: **block** (refuse until dependents retired first) / **cascade** (retire item
  + dependents together) / **warn** (surface + proceed, dependents keep their frozen
  version — what the UI currently illustrates). Mirrors `ROBOT_DEMO_OPEN_QUESTIONS.md §2`.
- **Presentation rendering risk — mostly mitigated (v10.5).** three.js is now vendored
  (no network); `color-mix` and WebGL are feature-detected with solid-fill + 2D fallbacks and
  a dismissible banner. **Residual risk:** unknown presentation hardware — still present from a
  known-good, tested machine + current Chrome/Edge. Also eyeball the 3D cell once: r160 default
  lighting may look slightly darker than the old r128.
- **New Teach-pane part vocabulary (not yet in the reference maps).** `.rowact` (row-action
  icon), `.iact` (inspect action button), `.idep` (dependents notice), `#ov_banner`
  (override banner). The three maps depict the Order pane / a brain card / the button system,
  none of which changed — so no regen was required; capture a Teach-pane map only if the
  Teach surface needs a named-part reference later.
- **New Plan-section part vocabulary (v10.3a).** `.rsub` (the Resolve subsection inside the
  Plan section body), `.rgrid` (the 3×3 narrowing grid), `.rclause` / `.rcap` (clause + stage
  caption). The orchestrator_card_map shows the *Capabilities* section, not Plan, so no map
  regen was required; add a Plan-section map only if the Resolve subsection needs a named-part
  reference later.

## 6. Working conventions (carried)

Critical-design-reviewer posture; restate a plan before implementing; one increment at a
time, each openable; verify headlessly before presenting; **keep the three maps current
with every card change**; v9 stays frozen; tabs/toggles are buttons inside the card body
(never the header). See memories `robot-demo-ui-v10`, `robot-demo-ui-verification`.
