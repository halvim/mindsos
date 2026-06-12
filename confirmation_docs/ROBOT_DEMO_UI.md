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

- A **new** file, `demo_ui/presentation.html`, branched from the frozen
  `demo_ui/presentation_mockup.html` (**v9 stays untouched**).
- Built as the **real frontend view layer fed by a mock data source** shaped like the
  future WebSocket `state`/`brains` payload (`ROBOT_DEMO_PROTOTYPE_PLAN.md §4`), so the
  Phase-D swap to live brains replaces the data source, **not** the view layer.
- Honesty tag retained: **"mock data · not wired to live brains."**
- **The on-screen product version IS the increment number** (the header badge), and it is the only
  version label in this doc. Each shipped UI increment bumps the minor by `+0.01`; **`v1.0` is reserved
  for live brains end-to-end.** Anchor: `v0.10` = the **live-seam** state (the increment formerly tracked
  as `v10.6`); the teach-model Export/Import increment bumps the badge to **`v0.11`**; focus mode will be
  `v0.12`; and so on toward `v1.0`. The §3 shipped list is renumbered to this scheme (each entry shows
  its former `v10.x` track label in parentheses for traceability). **Filenames no longer carry the
  `v10` suffix** — renamed 2026-06-12: `presentation_v10.html`→`presentation.html`, the `*_v10.js`
  sidecars→`*.js`, and this doc `ROBOT_DEMO_UI_V10.md`→`ROBOT_DEMO_UI.md` (all 71 references updated).
- A short end-user guide lives at `demo_ui/HOW_TO_USE.md` (run Demo/Live, share with others).
- **No Chromium in the Cowork sandbox** → all UI work is verified headlessly. See memory
  `robot-demo-ui-verification` (pure sidecar node tests + cairosvg rasterization); live
  click/layout is the user-confirmed part.

## 2. Files (all under `demo_ui/`)

- `presentation.html` — the live dashboard (open directly; schematic 3D uses **vendored**
  three.js in `vendor/three.min.js` — no CDN, no server, fully offline as of v10.5).
- `vendor/three.min.js` — local three.js global build (IIFE, ~648 KB; esbuild-bundled from
  `web/vendor/three.module.js`, **REVISION 160**). Replaces the former r128 CDN `<script>`.
  Classic global build (not ES module) so the page still opens from `file://`.
- Sidecars (pure, node-testable): `graph.js` (reasoning subgraphs), `teach.js`
  (teach-tab curation model), `sections.js` (brain-section content model),
  `resolve.js` (relation-resolution narrowing — Plan ▸ Resolve subsection),
  `datasource.js` (the **mock↔live data-source seam**; live WS client).
- `mock_ws_server.js` — runnable reference WS emitter (replays the 7 beats as live frames;
  `npm i ws && node mock_ws_server.js`). Dev-only; a worked example of the backend contract.
- **`confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md`** — the authoritative server↔browser WS
  protocol for the backend (what to emit for the dashboard to go live).
- **Reference maps** (the part-name vocabulary — keep current with every card change):
  `orchestrator_card_map.png` (brain card, Capabilities section), `plan_card_map.png` (brain card,
  **Plan ▸ Resolve subsection** — `.rsub`/`.rlabel`/`.rclause`/`.rgrid`/`.rcap`),
  `comms_card_map.png` (the **Messages** card — tabbed **Server (Seam A) / Inter-brain (Seam B)**,
  in that order; *shipped v0.13*), `user_card_map.png`, `button_map.png`.
- `maps/*.py` — the scripts that regenerate the five maps (run `python3 maps/<name>.py`;
  needs `cairosvg`).
- `presentation_mockup.html` — frozen **v9** baseline (reference only).

## 3. Shipped increments

- **v0.4 (was v10.1) — Graph tab.** Per-section graph view (the `⌗` view-mode), animated across the
  7 scripted graph-moments. Data + renderer in `graph.js`. **The graph content is a
  deliberate placeholder** — to be replaced once real server comms exist (it has no v1
  consumer beyond illustration).
- **v0.5 (was v10.2a) — Teach: Library + Inspect + teach-term.** Teach tab = Library / Teach term /
  Demonstrate. Teaching a Local position term flows it into the Order/Sort dropdowns.
  Model in `teach.js` (node-tested).
- **v0.6 (was v10.2b) — Teach: Retire + Global override (Hybrid controls).** Library rows carry a
  contextual **row-action icon** (`.rowact`: ⊘ retire / ⇄ override / ↺ restore) **and** the
  Inspect panel repeats the action as a labelled button (`.iact`) with context — chosen
  layout = **Hybrid** (Option C). **Retire** = reversible version-freeze (Local + learned
  only; builtins/Global are not user-retireable): the item stays in the Library struck-
  through and is dropped from the Order/Sort dropdowns + compose chips; **Restore** reverses
  it. **Global override** reuses Teach-term: the ⇄ action prefills the Global term's cells,
  the user edits + saves, and a **`Local-override`** shadow is written (resolves Local-first
  via `resolveTerm`; the Global stays untouched). The dependents notice (`.idep`) surfaces
  what depends on an item **but does not pick a retire-integrity policy** — that
  (block/cascade/warn) is left as an **open MindsOS decision**, see §7. New `teach.js`
  exports: `retire`/`restore`/`isRetireable`/`overrideGlobal`/`resolveTerm`/`activeTermNames`/
  `dependentsOf` + `validateTermName(..,{overrideGlobal})`; a Global seed term `corner-pack`
  was added so there is something to override. Verified headlessly: `teach.js` node test
  (19/19) + a jsdom DOM-wiring test of the live handlers (20/20) + inline-script parse.
- **v0.7 (was v10.3a) — Plan ▸ Resolve subsection (relation-resolution target-cell highlight).** Chose
  **A** (target-cell highlight) over the focus-mode half of the original v10.3; placed it
  **inside the Plan section as a "Resolve" subsection** (NOT a new top-level section — the
  four-section set stays settled). On a beat that resolves a spatial clause it renders a
  compact 3×3 grid that **animates the candidate set narrowing** (timed step-through, ~650 ms/
  step) — beat 3 "Box above Tube" goes 9 → 3 (row above the Tube) → 1 (tie-break: directly
  above) and the Box drops on the winner; Arm 1's absolute "Sheet @ center" resolves 9 → 1.
  Brains/beats with no resolution show a "no spatial relation resolved this beat" placeholder.
  **Snap-to-final guard:** every (re)start clears any in-flight timer, so fast beat-scrubbing
  can't strand a half-animation. Honest-tag discipline: the beats are scripted, so this SHOWS
  the resolution — `resolve.js` is shaped like a future MappingResult chain-artifact, not
  a live solver. Verified headlessly: `resolve.js` node test (13/13) + a jsdom test that
  drives the timed animation to the winner and the snap-to-final scrub (10/10) + inline parse;
  v10.2b regression re-checked (20/20).
- **v0.8 (was v10.4) — Maximize-height button on every card (Option A).** A per-card header control
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
- **v0.9 (was v10.5) — Presentation hardening.** Three orthogonal fixes so a live showing can't fail on
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
- **v0.10 (was v10.6) — Live data-source seam (mock ↔ live brains).** The dashboard's `states` array now comes
  from a `DataSource` (`datasource.js`): `makeMockSource` (today's baked beats, byte-identical
  default) or `makeLiveSource` (a WebSocket client). Activated by **`?live=<wsurl>`** — no other
  change flips the demo from mock to live; the view layer is untouched. Live behaviour: opens the
  socket, flips the honesty tag (connecting → **live — connected** / disconnected / error),
  **follows** incoming `state` frames (unless the user scrubs back), appends `message` frames to the
  log, applies `pose` updates to the cell, and routes Submit/Play/Pause/Reset/Teach to `sendCommand`.
  The two **mock-only panels** (graph + Plan▸Resolve) are **suppressed in live** with a "feed not yet
  emitted" placeholder, since the backend has no producer for them yet. Wire protocol =
  `ROBOT_DEMO_PROTOTYPE_PLAN.md §4` made precise in **`ROBOT_DEMO_WS_CONTRACT.md`** (frame types,
  field-persistence semantics, commands, reference emitter). Reference emitter `mock_ws_server.js`
  replays the 7 beats. Verified headlessly: `datasource.js` node test (15/15) + jsdom live-mode
  test with a stub socket (15/15) + **end-to-end over a real WebSocket** against the spawned mock
  server (7/7) + all four prior suites re-checked (20/20 + 10/10 + 18/18 + 13/13). **This is the
  UI-side completion of "go live"; the remaining work is the backend emitting these frames (DM-4+).**
- **v0.11 (was v10.7) — Teach-model Export/Import (files).** The User-card **Export / Import** buttons (previously
  reserved, still wired to the old layout-JSON path) now save/load the **teach model** as a real `.json`
  file — the only "system state" the browser actually owns (taught Local terms, `Local-override`
  shadows, retire-flags). Export = `Blob` download `mindsos-teach-<date>.json` = `{seedVersion, terms,
  composites}`; Import = file-picker → **full-snapshot replace** of `TERMS`/`COMPOSITES` in place, then
  refresh library + every position dropdown + compose chips. **Full snapshot, not a delta** —
  `seedComposites()`/`seedTerms()` already ship some `Local`/`Global` seed rows, so an "all Local rows =
  user delta" export would duplicate seeds on reseed; a `seedVersion` stamp (`=1`) + a console warn on
  mismatch covers seed drift. **Import is disabled under `?live=`** (teach state is backend-owned; the WS
  contract has no bulk-import path — only the per-demonstration `teach` command); Export stays on. The
  old layout-JSON read/write + the `#io` textarea + the stale edit-mode hintbar were removed. Verified
  headlessly: 28/28 (pure snapshot round-trip incl. retire/override survival; jsdom export→file, file→
  import→dropdowns-repopulated, live-disables-Import; teach sidecar regression). No map regen (no mapped
  card changed — Export/Import are `button_map` window-level controls whose behavior, not shape, changed).
  - **v0.11 follow-ups (2026-06-12, no badge bump — fixes, not a new increment):** (1) **per-card hover
    tooltips** — every card (3 static + 4 brain) carries a `data-desc`; hovering its title bar shows a
    styled `#cardtip` with the description (the prior tiny `?`-only native title was easy to miss). jsdom
    40/40. (2) **`plan_card_map.png`** added (Plan ▸ Resolve subsection part names). (3) Doc fix: Export/
    Import are **header-toolbar** buttons, not user-card. (4) Logged the pending repurpose of the header
    Export/Import to **demo system-state (L5 episode) import/export** (planning note; teach-model save/load
    then moves into the Teach tab) — not yet built.
- **v0.12 — Subsection sub-cards.** Subsections inside a section now render in a **reusable sub-card
  container** combining all three reviewed options: a bordered box (`.subsec`) + a **per-card accent
  rail** (`.subsec::before`, inherits `var(--acc)`) + a **collapsible header** (`.subhdr` with `.subttl`
  + `.subchev`; click toggles, collapsed shows header only). Body = `.subbody`. **Subsections start
  expanded;** collapse state persists across beat re-renders via a module `collapsedSubs` Set (keyed
  `<brain>:<sub>`). The v10.3a **Resolve** block was rehoused as the first subsection (`mgr:resolve`) —
  its content classes (`.rclause`/`.rgrid`/`.rcap`/`.rnone`) now live inside `.subbody`; the old
  `.rsub`/`.rhead`/`.rlabel`/`.rsub-empty` markup was removed. The container is reused verbatim for any
  future subsection (Decision/Steps/…). Verified headlessly 48/48 (subsecHTML expand/collapse, Resolve
  wraps in `.subsec`, DOM header-click collapse + persistence). **Map regenerated:** `plan_card_map.png`
  now shows the sub-card with `.subsec`/`.subhdr`/`.subbody`/rail + collapse chevron.

- **v0.13 — Server panel (live‑server showcase), as a tab on the Messages card.** The inter‑brain
  card (`#card_log`) is renamed **"Messages"** and gains a `.uitab` tab row — **Server · Seam A**
  (first) and **Inter‑brain · Seam B** (second). Server tab = a steel‑accent (`--acc:#6f8092`) vitals
  strip (sessions · Falkor · uptime · endpoint) + a color‑coded server‑event feed (bootstrap/login/
  skill‑install/gate ✓/gate ✗/persist/audit) with real `EVT_*` constants. Honors "Server = orthogonal
  runtime envelope" (a tab, not a 5th brain — placement option C). **Default tab is mode‑aware:** mock
  leads with the **Inter‑brain log** (the real scripted content), `?live=` leads with the **Server
  feed**. Server feed is **live‑only**: mock shows a representative sequence (labeled `mock`), `?live=`
  shows a "backend producer pending (DM‑4+)" placeholder until DM‑4 emits `server_status`/`server_event`
  (contract in `ROBOT_DEMO_L5_EXPORT_IMPORT_PROMPT.md`). Verified headlessly 57/57 (tab order, mode‑aware
  default, mock feed render incl. the gate denial, tab‑switch, live placeholder). **Map:**
  `comms_card_map.png` matches the build.
- **IP sanitization (policy B, 2026‑06‑12, no badge bump — content/policy pass).** Product decision:
  everything reaching a participant's browser (panel text **and** the raw WS frames) shows **behavior,
  not MindsOS implementation/IP**. Canonical rule + token→generic mapping: **`ROBOT_DEMO_IP_SANITIZATION.md`**.
  Applied across **all feeds**: the baked beat text (intent/decision/caps), the Inter‑brain messages
  (`query_capabilities()`→"What can you do?", `DONT_KNOW(handoff‑via‑belt)`→"Don't know how to hand
  across the gap", `promote Local→Global`→"Share fleet‑wide", parties `Global`→**Fleet** / `L2`→
  **Library**), the Server feed (generic vitals + events, no `EVT_*`/FalkorDB/capability names), the
  flag/badge labels (`↑ promoted`→`↑ shared`, `⊘ gated`→`⊘ blocked`), the Teach Library skill names
  (`handoff‑via‑belt`→`hand‑off`, `place‑at‑cell`→`place‑in‑cell`, `stage‑at‑position`→`stage‑on‑belt`),
  the graph‑view labels, the `TaskRun` section header→`Task`, and `mock_ws_server.js`. Verified by a
  headless guard test (Suite 9: cumulative inter‑brain log carries no internal tokens); 60/60 total.
  DM‑4 told to emit pre‑sanitized frames (coordination doc addendum). Borderline‑kept (flag if you
  want them changed): the section tab label **"Pipeline"** and the tab labels **"Seam A/Seam B"** —
  mild jargon, not changed yet. Source‑code comments are out of scope (would need a build‑step strip).

- **v0.14 — L5 export/import (teach relocation + header scaffold).** Teach‑model Export/Import
  **relocated into the Teach tab** (Library sub‑tab, "vocabulary file" `#tv_export`/`#tv_import`;
  `#tv_import` disabled under `?live=`). The **header Export/Import** are repurposed to **L5
  system‑state**: Export downloads a mock **demo‑state** snapshot (`mindsos-demo-state-<date>.json`,
  schema per `ROBOT_DEMO_L5_EXPORT_IMPORT_PROMPT.md`) — live sends `export_state`; Import parses a
  snapshot, branches on `kind` (`demo-state`/`episode-audit`), and shows an inline `#l5msg`
  confirmation — live sends `import_state`. **Scaffold only** — the per‑mode **Export chooser** (audit
  a brain / demo state), the **reasoning/audit view** (goal #2, a new visual surface → mockup‑gated),
  and **demo‑state restore** land next. Verified 64/64 (relocation, header demo‑state download,
  import‑branch confirmation). No new map (no mapped card changed).

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
SYSTEM** box (Teach). The gap between boxes is the divider.

**Export / Import location — CORRECTION.** These two buttons live in the **header toolbar**
(top-right, next to ▶ Play / ↺), **not** in the user card — earlier text here was wrong. As of
v0.11 they save/load the **teach model** as a `.json` file (taught terms + overrides + retire-
flags), Import disabled under `?live=`. The old layout-JSON behavior + the **Edit layout /
Layout** buttons were removed. **REPURPOSE APPROVED (user, 2026-06-12):** the header Export/Import
become **L5 export/import** (two modes — A: per-brain episode/reasoning audit; B: whole-demo
reloadable state); the teach-model save/load relocates into the **Teach tab**. Backend contract
authored + approved: **`ROBOT_DEMO_L5_EXPORT_IMPORT_PROMPT.md`** (for the DM-4 chat). Not yet built
on the UI side — see §5.

**Decisions changed this chat** (the project invited revisiting): the original backlog "Export/
Import → system-state files" is scoped to the **teach model** (the browser is a view; the backend
owns live state); chose **full-snapshot over delta** (seed rows include `Local`/`Global`, so a
delta would double-seed); and **focus mode is reframed to a manual "solo this card" toggle** —
the as-specced *auto-spotlight the active brain* is dropped because it reverses the settled
"all cards render identically" call and is undefined on the cooperation beats (3–4 brains active).

## 5. Backlog / next (deferred, in priority order)

1. **v0.15 (focus mode, reframed: manual "solo this card")** — second half of the original
   v10.3. **NOT** auto-spotlight-the-active-brain (dropped — reverses "all cards equal" + is
   undefined when several brains are active). Instead a per-card toggle that dims the *other*
   cards on demand (no reflow/scale); default stays all-equal. Define interaction with maximize
   (mutually exclusive). `OPEN_QUESTIONS §4`.
2. ~~**Export / Import → system-state files**~~ — **SHIPPED as v0.11** (scoped to the teach model;
   see §3).
3. **L5 export/import (header buttons repurpose)** — contract approved
   (`ROBOT_DEMO_L5_EXPORT_IMPORT_PROMPT.md`, for DM-4). UI work: (a) relocate teach-model save/load
   into the **Teach tab**; (b) header **Export** chooser — *audit a brain* (mode A) / *demo state*
   (mode B); (c) **Import** branches on `kind` → memory-load confirm + recap (goal #1) and a
   per-episode **reasoning/audit view** (goal #2); demo-state import jumps to `demo_position.beat`.
   Live-only (mock ships representative snapshots). Lands after the backend emits the frames (DM-4+).
3b. ~~**Server panel (live‑server showcase)**~~ — **SHIPPED v0.13** (Server · Seam A / Inter‑brain ·
   Seam B tabs on the Messages card; see §3). Remaining live‑side work: a `datasource.js` update to
   parse real `server_status`/`server_event` frames once DM‑4 emits them (today live shows the
   pending placeholder).
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
- **Subsection sub-card vocabulary (v0.12).** Reusable container: `.subsec` (bordered box),
  `.subsec::before` (per-card accent rail), `.subhdr` (collapsible header) → `.subttl` (caps
  title) + `.subchev` (chevron), `.subbody` (body). Collapse state in the `collapsedSubs` Set
  (keyed `<brain>:<sub>`). The **Resolve** subsection's content classes live inside `.subbody`:
  `.rclause` (spatial clause), `.rgrid` (3×3 narrowing grid), `.rcap` (stage caption), `.rnone`
  (empty/placeholder). **Mapped** in `plan_card_map.png` (`maps/plan_card_map.py`) — companion to
  the orchestrator_card_map (which shows the *Capabilities* section).

## 6. Working conventions (carried)

Critical-design-reviewer posture; restate a plan before implementing; one increment at a
time, each openable; verify headlessly before presenting; **keep the three maps current
with every card change**; v9 stays frozen; tabs/toggles are buttons inside the card body
(never the header). See memories `robot-demo-ui-v10`, `robot-demo-ui-verification`.
