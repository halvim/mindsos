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
  `audit.js` (L5 reasoning/audit — the recorded-chain 7→5 generic-stage collapse, sanitized),
  `datasource.js` (the **mock↔live data-source seam**; live WS client),
  `timeline.js` (**demo-timeline builder** — `buildTimeline()`, change-only ordered transcript; *v0.24*).
- `mock_ws_server.js` — runnable reference WS emitter (replays the 7 beats as live frames;
  `npm i ws && node mock_ws_server.js`). Dev-only; a worked example of the backend contract.
- **`confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md`** — the authoritative server↔browser WS
  protocol for the backend (what to emit for the dashboard to go live).
- **Reference maps** (the part-name vocabulary — keep current with every card change):
  `orchestrator_card_map.png` (brain card, Capabilities section), `plan_card_map.png` (brain card,
  **Plan ▸ Resolve subsection** — `.rsub`/`.rlabel`/`.rclause`/`.rgrid`/`.rcap`),
  `comms_card_map.png` (the **Messages** card — tabbed **Server (Seam A) / Inter-brain (Seam B)**,
  in that order; *shipped v0.13*), `user_card_map.png`, `button_map.png`,
  `header_map.png` (the **header** — title/tags/`#honesty`/`#audit`+`#auditmenu`/`#export`+`#expmenu`/
  transport/`#l5cal` message callout/`#capbanner` + the **beat strip** `#beatnum`/`#beatnarr`/`#tlbtn`;
  *regenerated v0.24*), `timeline_map.png` (the **demo-timeline modal** — `#tlbtn` trigger, `.tlhead`/
  `.tlclose`, `.tlfilters`/`.tlflab`/`.tlpills`/`.tlpill.on`/`.off`, `#tlbody`, `.tlbeat`, `.tlrow`/`.tlsrc`/
  `.tltag`/`.tltext`; *v0.24*).
- `maps/*.py` — the scripts that regenerate the maps (run `python3 maps/<name>.py`;
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
    styled `#cardtip` with the description (the prior tiny `?`-only native title was easy to miss)
    **[superseded 2026-06-13 → scoped to the `.help` icon only; native title dropped]**. jsdom
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

- **v0.15 — L5 reasoning/audit view (goal #2: "why did it decide / refuse X").** A **new visual surface**
  (mockup‑gated, approved): a **modal** (`#l5audit`) over the existing `#maxbackdrop` dimmer — **NOT** a
  card, so the settled 4‑section set is untouched. Renders one episode's **recorded chain** as **5 generic
  sanitized stages** (IP policy B): *Understood request → Chose approach → Planned steps → Executed →
  Outcome* — the 7 chain‑artifact types (HintSet/MappingResult/Plan/Milestone/Pipeline/PipelineRun/
  TaskRun) and capacity/task‑pattern IRIs **never reach the DOM** (the 7→5 collapse + a defensive de‑IRI
  live in pure `audit.js`). **Thin‑v0‑faithful:** empty fields render honestly ("no replans this run",
  "not reached"), never hidden; confidence shown labeled "v0 (uncalibrated)" per the DM‑4 honesty caveat.
  **Two entry points:** a per‑brain **audit button** (magnifier `.auditbtn`) — primary, "audit this brain"
  (mode A) — and importing an `episode‑audit` snapshot via header **Import** (secondary); both open the same
  modal. Left rail = episode list (✓ succeeded / ⊘ blocked, newest‑first, click to select). Close = ×/Esc/
  backdrop. **Header reorder (this increment):** the brain‑card header is now **UX controls (audit,
  maximize) │ 20px gap │ card‑UI (status dot, help)** — `makeMaxBtns` inserts maximize before `.dot`; a
  20px gap (`.dcard .hdrright .dot{margin-left:20px}`) separates the two groups (no divider line).
  **Representative content = the REAL DM‑4 Mode‑A export** (`confirmation_docs/fixtures/episode_audit_mgr.json`
  — Manager × two real order lifecycles, **both `succeeded`**) baked in (`SAMPLE_AUDIT_SNAP`) and chipped
  **"sample export"** — recorded reasoning, **NOT fabricated**. The earlier hand‑authored mock + its
  fabricated `dont_know` were **dropped** per the no‑fabrication rule (option 2): the audit surface must not
  invent the reasoning it exists to authenticate. The **refusal branch renders the same shape** (unit‑tested
  against a synthetic `dont_know`) and lights up when DM‑5/6 ships a **real** refusal fixture — there is no
  real `dont_know` path until then. `?live=` renders the live snapshot; a brain with no exported chain
  (a1/a2/conv offline) shows the honest placeholder. `audit.js` carries an **order‑shape `task_input`
  extractor** + count **pluralization** for the real wire shape; the real wire's **opaque ref tokens**
  (`n1…`) draw the lineage by `iri↔*_ref` equality and never render as text. Verified headlessly **65/65**
  (audit.js stage collapse incl. succeeded + refusal + empty‑honest; de‑IRI; **the real fixture renders
  correctly**; **IP‑sanitization guard** asserting no internal token — and no opaque ref token — in any
  rendered HTML incl. the live modal DOM; jsdom open/row‑click/Esc/backdrop + header‑order). **Maps
  regenerated:** `orchestrator_card_map.png` + `plan_card_map.png` show the new header order + `.auditbtn` +
  the 20px gap. **Pending:** a dedicated `audit_view_map.png` (modal part vocabulary) — deferred until the
  live modal layout is eyeball‑approved, so it maps the final surface.

- **v0.16 — live connection status is data-driven (false-green bugfix).** **Bug:** the honesty tag went
  green on socket **open**, so when the tunnel/proxy (`wss://brains.sanmyaku.com`) accepts the WebSocket
  while the backend is **down**, `onopen` fired → false "● live — connected to brains" with no real data.
  (Reproduced headlessly: socket-open-no-data → green.) **Fix (in `setupLive`):** (1) `open` → amber
  "● connected — waiting for brains…" — an open socket is **not** "live"; green only on the **first real
  frame** (`hello`/`state`/`server_status`/`message`/`pose`). (2) **Heartbeat watchdog** — DM-4 emits
  `server_status` every ~3s; once the first heartbeat is seen the watchdog arms, and if data stalls
  >8s while green it flips to red "● connection lost — no data" (recovers to green when heartbeats
  resume). A backend that never heartbeats (e.g. `mock_ws_server.js`) leaves the watchdog **disarmed** →
  no false reds; it still goes red on socket close. (3) `close`/`error` → red (unchanged). `datasource.js`
  now surfaces `server_status`/`server_event` as events (was `unknown`) — also the first step of the B1
  vitals strip. Verified headlessly **10/10** (refused→red, open-no-data→**amber**, frame→green→drop→red,
  heartbeat→green→stall→red watchdog, recovery→green, no-heartbeat-idle→stays green) + audit regression
  **67/67**. **Remaining live wiring (next):** B1 vitals strip from `server_status`; B2 feed live `state`
  → card renderer; B3 Export `state_snapshot` → download + audit view.

- **v0.17 — live Server vitals strip (B1).** The Server tab (Messages card) now renders its **vitals
  strip from the live `server_status` heartbeat** under `?live=` (was a "producer pending" placeholder).
  Parses the **PB-3 deviated keys**: `sessions[].brain` (count + the brain list), `storage` (== "connected"),
  `state_saved`, `uptime_s` (→ "Xh Ym"/"Xm Ys"), optional `endpoint`. A green **"live"** chip replaces the
  amber "mock" chip. The **event feed below stays the honest placeholder** ("server_event next") until B2c
  is consumed — vitals and feed are separate. No tech/role/capability names rendered (IP policy B; guard
  asserts no `Falkor`/`mindsos_version` leak). `datasource.js` already surfaces the frame (v0.16). Verified
  headlessly **17/17** (the connectivity suite + a B1 scenario: 4 sessions, storage, uptime 1363s→"22m",
  brain list, feed-placeholder-intact, no token leak, tag stays green) + audit **67/67**.
- **B2 — verified ALREADY WIRED (no code change).** DM-4 suspected the live branch "only consumes `pose`";
  it doesn't. Boot runs `show(0)` + the rAF loop (line ~1116), and every live `state` frame runs
  `frame`→`show`→`renderPanels`, which re-renders **all four brain cards** via `mergeBrain` (per-key deep
  merge onto the carried base, so sparse frames don't drop brains). Regression-tested (connectivity
  Scenario H: a contract `state` frame updates `bc_mgr`/`bc_a1` intent + narration, no crash on a sparse
  brain). **So a static-cards symptom live is a `state.brains[id]` shape mismatch (or a scrubbed `FOLLOW`),
  not the UI** — the expected per-brain shape is the WS-contract `{intent, decision, chain, active, flags,
  caps}`. Now **21/21** with Scenario H. **Remaining:** **B3** Export `state_snapshot` → download + audit
  view; then the `server_event` live feed.
- **v0.18 — Export chooser + live snapshot download/open (B3).** The header **Export** is now a chooser
  (`#expmenu`): **Audit a brain** (Orchestrator/Arm 1/Arm 2/Conveyor) or **Demo state**. Live: sends
  `export_state {mode:"episode-audit", scope:<brain>}` or `{mode:"demo-state", scope:"all"}`; mock:
  downloads the matching `.json` from the in-page sample. On a live **`state_snapshot`** reply,
  `handleSnapshot` downloads the JSON and, for `kind:"episode-audit"`, **opens the audit modal** on it
  (`demo-state` downloads only — restore deferred). `datasource.js` now surfaces `state_snapshot` +
  `import_result` (were `unknown`). Menu closes on select / outside-click / Esc. Verified headlessly
  **27/27** connectivity (+ Scenario I episode-audit snapshot → download+opens 5-stage view, no `root`
  leak; Scenario J demo-state → download, modal stays closed) and **73/73** audit (+ chooser: opens, 4
  brain options + demo-state, mock export message). **This completes the DM-4 B1–B3 live wiring** (B2 was
  already wired). Remaining live-side: the `server_event` event feed (when DM-4 emits it) and demo-state
  **restore** (post-DM-6).
- **v0.19 — header redesign (mockup-approved).** (1) **Title** → “Minds**OS** Demo” (`h1` weight 500, `OS` in
  `h1 .osb` weight 800). (2) **Beat chip (`#chapter`) + narration (`#narration`) row removed** (and their
  renderPanels/setupLive writes). (3) **New `#audit` button** — filled **magenta `#c2419a`** (distinct from
  every brain colour + the Play blue) with a magnifier, set apart from Export by a wide gap; its `#auditmenu`
  lists the four brains and **opens the reasoning/audit modal (VIEW)**. (4) **`#export` is DOWNLOAD-only** —
  `#expmenu` ("Download a brain snapshot" / "Demo state") just saves `.json`, never opens a window. In live,
  both Audit and Export send `export_state`; a **`pendingExport` flag (`"view"|"download"`)** tells
  `handleSnapshot` whether the `state_snapshot` reply opens the modal or downloads. (5) **System message =
  option-C callout `#l5cal`** (replaces the tiny `#l5msg` line): permanent reserved height, **severity-colored**
  (`sev-info/-ok/-warn/-error` — rail + icon), `l5msg(text, severity, {persist})`, **auto-clears to idle**
  after ~5 s, with a dismiss `#l5x`; `#l5msg` is now the inner text span. `#capbanner` kept **separate**
  (persistent compat warning — folding it into the auto-clearing callout would let an action message wipe it).
  Verified headlessly **81/81** audit/header (Export=download incl. severity-class set + modal-not-opened;
  Audit=view opens the modal) + **26/26** connectivity (live Audit→`state_snapshot`→modal; live Export→
  download-only). **Map regenerated:** `header_map.png` (v0.19 parts incl. `#audit`/`#auditmenu`/`#l5cal`).

- **v0.20 — real refusal episode wired into the audit view (3c; goal-#2 "why refuse").** The DM-5
  refusal fixture (`confirmation_docs/fixtures/episode_audit_arm1_refusal.json` — suction arm refusing a
  tube, real `dont_know`/`embodiment_gate`, **not fabricated**) is baked into `SAMPLE_AUDIT_SNAP.brains.a1`
  so the **Arm 1** audit button opens it (a2/conv stay honestly empty). Five render fixes in `audit.js`:
  (1) **Stage 4 outcome-driven** — a `dont_know` run renders "not reached · execution did not start
  (blocked before dispatch)", never the old false-green "all completed" (the v0 chain carries a *notional*
  leaf step; success styling now gates on `outcome_classification === "succeeded"`, and a feasibility-gate
  refusal fires before real dispatch). (2) **Stage 5 prefix dedupe** — the sanitized backend `reason`
  already starts "blocked —", so it's used verbatim (capitalized), not double-prefixed. (3) **Stage 5 note
  dedupe** — when `blame.rationale` restates the `dont_know.reason` (it does in the fixture), the "blame:"
  note is dropped (pure repetition); the only non-duplicate note candidates are internal (`chain_level`
  is IP, `blame_score` uncalibrated). (4) **Stage 1 arm-dispatch parser** — `requestText` now handles the
  arm's `task_input.order:{item,target}` (a dispatch, not a user order — DM-5 confirmed) → "tube → r1c1";
  the Manager's `order.lines[]` path is untouched. (5) **`plainLabel` whitespace-gate** — the colon/dot
  split now only fires on a single-token IRI (no whitespace), so a sanitized multi-word phrase
  ("move to r1c1:tube", "place tube") survives intact instead of collapsing to its tail — a **latent
  over-sanitization bug** the IP-guard couldn't catch (it loses content rather than leaking it). Bug-3's
  *label* ("place tube") was fixed upstream by DM-5's re-export (`partition`→`split`), so no UI relabel
  was needed. A **build-time drift-guard** test asserts the baked `a1` block stays byte-equal to the
  `.json` (the inline copy is required because `fetch()` is CORS-blocked under `file://`). **DM-5 then
  delivered an Arm 1 *succeeded* episode folded into the same fixture** (newest-first: refusal "place
  tube" `dont_know` + success "place box" `succeeded`), re-baked so a1's list reads [Blocked, Succeeded]
  — the arm now reads honestly ("succeeds on a right-gripper order, refuses only when it physically
  can't") instead of refusal-only/"broken". Verified headlessly **45/45** (drift guard byte-equal vs the
  2-episode `.json`; refusal stages; the a1 succeeded episode renders as success; mgr no-regression;
  IP-guard on the refusal DOM — no `n1…n20`/`embodiment_gate`/`arm-suction`/`chain_level`, `tube`/
  `gripper` allowed; plainLabel gate). No map change (no mapped card changed).

- **focus mode — BUILT then REMOVED (v0.21, reverted 2026-06-13; badge stays v0.20).** A manual
  "solo this brain" toggle (opacity-fade the other brain cards) was built and verified, then **removed**
  on review: dimming alone added no value over **maximize** (it gave the focused card nothing, and only
  dimmed 3 of 6 siblings, so the focused card didn't even stand out). Options to rescue it (widen the dim
  to all cards / collapse-and-reclaim-space) weren't worth it given maximize already covers "see one card."
  Reverted in full — no `.focusbtn`, no `.faded`, no focus JS. The §7 overlay-precedence question it raised
  is therefore moot. See §4 "decisions changed."
- **v0.20 follow-up fix — hover tooltip scoped to the `.help` icon (2026-06-13).** The per-card hover
  tooltip (`#cardtip`) + `cursor:help` were on the whole `.draghandle` header, so the styled box popped over
  the card on any header hover (user-reported). Now bound to the **`.help` icon only**; the redundant native
  `title` on the help icons was dropped to avoid a double tooltip — `#cardtip` shows the card's `data-desc`
  on `.help` hover. (This supersedes the v0.11 whole-title-bar tooltip.) `orchestrator_card_map.png` +
  `plan_card_map.png` carry the `.help (hover = description)` note. Verified headlessly **8/8** (focus fully
  gone; maximize + tooltip-scope intact) + audit/drift **45/45** re-checked.

- **v0.21 — live Plan ▸ Resolve (3d; the SHIPPED v0.21 — distinct from the reverted focus-mode "v0.21").**
  The live `resolve` frame (WS §5, DM-5 producer green at `98e7c5e`) is wired through `datasource.js`
  (`case 'resolve' → emit`) and lifts Plan▸Resolve off the live "producer pending" placeholder. The wire
  frame is per-brain (no beat key), so live keeps a per-brain `liveResolve` store + per-brain animation
  state (mock stays beat-keyed off `resolveAnim`, untouched). A `liveResolveToRes` adapter injects the
  per-brain accent (from `ACC`, not on the wire) and infers `absolute = (tube == null)`; `resolveInnerHTML`
  is factored so mock + live render through one path. On each arriving `resolve` frame the brain's narrowing
  animates (9→3→1) via `startLiveResolveAnim` (per-brain snap-to-final guard); `clearLiveResolve` on reset.
  `mock_ws_server.js` now emits sanitized `resolve` frames on beat 3 (mgr/a2/a1) for local testing. Verified
  headlessly **34/34** (adapter accent/absolute/null-guard, placeholder→grid, per-brain stepping + snap,
  mock-path regression, string-keyed-cells coercion, datasource resolve surface, e2e vs the spawned mock
  server) + IP-guard on the rendered resolve DOM. No map change.
- **v0.22 — header beat strip (Option C1) + narrow accent scrollbar.** Two changes. (1) A full-width slim
  **beat strip** under the header bar (`#beatstrip`): blue accent rail + an **outlined-blue beat chip**
  (`#beatnum`) + behavior-level **narration** (`#beatnarr`), written each beat in `renderPanels` from the
  state's `title`/`narr`. This re-introduces the narration that v0.19 had removed, now in the header zone
  (chosen layout C1 over inline A/B — full text, no truncation). (2) A **4px per-card-accent scrollbar** on
  the brain-card `.scroll`/`.secbody` regions (thumb = each card's accent at ~42%, ~80% on hover, transparent
  track; WebKit + Firefox `scrollbar-width:thin` + a `body.nofx` solid-accent fallback; scoped to `.dcard`).
  Verified headlessly **17/17** (strip text/idle/narr-only + CSS/HTML presence + IP-clean narration).
- **v0.23 — wheel-scroll over brain cards.** A non-passive `wheel` listener on each brain card scrolls *that
  card's* content (`cardScroller` picks whichever of `.scroll`/`.secbody` overflows) from **anywhere over the
  card** (title bar / tabs / padding included), `preventDefault`-ing so the page doesn't scroll underneath;
  **scroll-chaining at the edges** releases to the page at top/bottom (or no overflow). Handles `deltaMode`
  lines/pages → px. Verified headlessly **17/17** (scroller pick, up/down consume + advance, release at both
  edges, line-mode scaling).
- **v0.24 — demo-timeline modal + beat-strip rework + the beat-1 fix.** A **chronological, change-only
  transcript** of every message + brain section/subsection change, opened from the beat strip. (1) New pure
  sidecar **`timeline.js`** — `buildTimeline()` turns the scripted `frames` (mock) or a live state-diff into
  ordered beat-grouped entries, classifying message sources (User vs Seam B) and mapping decisions to
  sections. (2) `#tlmodal` modal (reuses the audit `#maxbackdrop`/Esc/click-out pattern) with **three filter
  rows** — Sources (Seam A/Seam B/User/the 4 brains), Sections (Task/Plan/Pipeline/Capabilities), Subsections
  (Plan▸Resolve) — toggle pills (`TL_ON` sets) + the rendered transcript (`#tlbody`). (3) The **beat chip is
  now a display-only outlined span**; a **far-right filled-blue `#tlbtn`** (Play-blue, list icon + "Timeline"
  label) opens the modal scrolled to the current beat. (4) **Beat-1 fix:** `datasource.js` + `merge` carry the
  frame's `beat`; the strip uses it (kills the live off-by-one from the idle seed at `states[0]`) and shows
  "Ready · Place an order to begin" on the idle seed; `beats_total` captured from `hello`. All rows render
  existing **behavior-level** strings (IP-guard green); no new wire frames / no new sanitization surface.
  Verified headlessly **44/44** (builder order/change-only/source+section classification, jsdom render +
  pill-toggle filtering, beat-strip fix, IP-guard). **Maps:** new `timeline_map.png` (modal part vocabulary);
  `header_map.png` regenerated (v0.24 — adds the beat strip: `#beatnum` chip + `#beatnarr` + far-right `#tlbtn`).
  - **Backend coordination (open):** the *live* beat counter + timeline beat-grouping need a true storyline-beat
    index. DM-6 confirmed `state.beat` is an advisory per-emit **frame** counter that overshoots `beats_total`,
    so a dedicated **`state.cbeat`** (0-based global beat, advances on true transition) was requested + accepted
    by DM-6 (final name/shape on delivery). Mock-mode is correct; the live counter wires to `cbeat` when it lands.
    See `ROBOT_DEMO_UI_BACKEND_COORDINATION.md`.
  - **`ROBOT_DEMO_TIMELINE_STORY.md`** (full ~55-row timeline content) was drafted for approval but **rejected by
    the user — to be improved in a future chat**; the richer per-section row model (frame `sections:{…}` +
    builder change) it implies is **deferred to v0.26** (renumbered from v0.25, which the audit increment took), not built.

- **v0.25 — two manager fixtures wired into the audit view + `replan_summary` Outcome headline (3c follow-on).**
  The audit modal's Manager (`mgr`) episode list is now **3 curated, distinct episodes** (newest-first), each
  pasted **verbatim** from a delivered fixture (no fabrication): **Blocked** — dead-end
  (`episode_audit_mgr_deadend.json`, `dont_know`; Outcome = `blame.rationale` "no available arm can handle this
  item"); **Succeeded** — recovery (`episode_audit_mgr_recovery.json`, `succeeded` + 1 replan); **Succeeded** —
  clean (`episode_audit_mgr.json` ep[1], sheet — picked over ep[0]/box so the two Succeeded rows aren't visually
  identical to the box reroute). `audit.js` Stage-5 gains a **`replan_summary` precedence**: a non-null
  `replan_summary` becomes the Outcome **headline** (cap-cased) + a **`↻ N replan(s)` badge** (from
  `replans.length`); legacy fixtures lack the field (`null`) and **fall through** to the original ok/`dont_know`
  logic unchanged (null-safe). **INC-8 (wire ≠ contract):** the recovery `verdict` ships `divergence:0.0` (a raw
  v0-uncalibrated float), **not** the contract's `divergence_band ∈ none|minor|major` — so **no band is rendered**
  (decision/count only). Cosmetic Stage-2 fix: a generic `task_pattern_iri:"approach"` renders "Approach selected"
  instead of the tautological "Approach: approach"; a real label ("move to home") is unchanged. **Drift-guard
  upgraded to per-episode deep-equality** (the old whole-block byte guard couldn't survive the 3-file merge): each
  baked `mgr` episode deep-equals its source fixture episode; `a1` untouched. Verified headlessly **43/43** (drift
  guard ×4, list rows/distinctness, dead-end + recovery + clean stages, a1 null-safe regression, IP-guard over all
  5 rendered DOMs — no `embodiment_gate`/`chain_level`/`blame_score`/`divergence`/`n\d+` ref tokens; behavior words
  survive) + all inline scripts parse + `audit.js` `node --check`. No map change (audit modal map still deferred).

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
delta would double-seed); and **focus mode was reframed to a manual "solo this card" toggle, then
DROPPED ENTIRELY (2026-06-13).** The auto-spotlight version was rejected first (reverses the settled
"all cards render identically" call, undefined on 3–4-brain beats); the manual opacity-fade version
was then built (v0.21) and **removed on review** — dimming alone gave the focused card no benefit over
**maximize**, so it earned no place. No focus code remains; maximize is the single-card affordance.

## 5. Backlog / next (deferred, in priority order)

1. ~~**focus mode (manual "solo this card")**~~ — **BUILT then REMOVED 2026-06-13** (see §3 + §4). Opacity-
   fade-others added no value over maximize; reverted in full. Not a backlog item anymore.
2. ~~**Export / Import → system-state files**~~ — **SHIPPED as v0.11** (scoped to the teach model;
   see §3).
3. **L5 export/import (header buttons repurpose)** — contract approved
   (`ROBOT_DEMO_L5_EXPORT_IMPORT_PROMPT.md`, for DM-4). UI work: (a) ~~relocate teach-model save/load
   into the **Teach tab**~~ — **SHIPPED v0.14**; (c) ~~per-episode **reasoning/audit view** (goal #2)~~ —
   **SHIPPED v0.15** (modal, 5 generic sanitized stages; see §3). **Remaining:** (b) header **Export**
   chooser — *audit a brain* (mode A) / *demo state* (mode B); demo-state **restore** (jump to
   `demo_position.beat`) — deferred‑stub until Mode‑B is real (post‑DM‑6, nothing to warm‑restore yet);
   and the goal‑#1 memory‑load **recap** read‑back (lands with the DM‑8 beat‑6 recap). Live import write
   lands after the backend emits the frames (DM‑4+).
3b. ~~**Server panel (live‑server showcase)**~~ — **SHIPPED v0.13** (Server · Seam A / Inter‑brain ·
   Seam B tabs on the Messages card; see §3). Remaining live‑side work: a `datasource.js` update to
   parse real `server_status`/`server_event` frames once DM‑4 emits them (today live shows the
   pending placeholder).
3c. ~~**Wire the REAL refusal episode (goal-#2 "why refuse")**~~ — **SHIPPED v0.20** (see §3). Baked
   `episode_audit_arm1_refusal.json` into Arm 1's audit; fixed Stage 4 false-green, Stage 5 prefix +
   note dedupe, Stage 1 arm-dispatch parser, and the latent `plainLabel` colon over-collapse. Bug-(iii)
   (approach label) was resolved upstream by DM-5's re-export ("place tube"). DM-5 also delivered an a1
   *succeeded* episode (folded into the same fixture) → re-baked so a1 lists [Blocked, Succeeded]. 45/45.
3d. ~~**Live Plan ▸ Resolve**~~ — **SHIPPED v0.21** (see §3): `resolve` in `datasource.js` + per-brain
   `liveResolve` store/animation, mock server emits `resolve` on beat 3. 34/34.
3e. ~~**Header beat strip + narrow accent scrollbar**~~ — **SHIPPED v0.22**; ~~wheel-scroll over brain
   cards~~ — **SHIPPED v0.23**; ~~demo-timeline modal + beat-1 fix~~ — **SHIPPED v0.24** (see §3).
3f. **Demo-timeline content (v0.26, deferred — renumbered from v0.25, now taken by the audit increment).**
   `ROBOT_DEMO_TIMELINE_STORY.md` (full ~55-row story) was drafted but **rejected by the user — improve in a
   future chat**. The richer per-section row model it needs (per-brain frame `sections:{task,plan,pipeline}` +
   `resolve` + `caps`; builder emits one row per *changed* section) is the v0.26 work, gated on an approved
   story. **Fold the `state.cbeat` live wiring (3g) into this increment** (timeline grouping consumes `cbeat`,
   so `timeline.js` is touched once).
3g. **`state.cbeat` wiring (live) — UNBLOCKED 2026-06-15 (DM-6 shipped it on the wire).** Final shape: field
   **`cbeat`** on every `state` frame — 0-based global storyline beat, advances only on a true (titled) beat
   transition, clamped `>= 0`; `beat` stays the advisory frame counter; `beats_total` (in `hello`) is the
   denominator. On wiring: point the beat-strip counter (`cbeat+1 / beats_total`) + timeline beat-grouping at
   `cbeat`. **NOT a one-liner** (INC-6): also make `mock_ws_server.js` emit `cbeat` so the headless e2e can
   exercise it. Bundled into v0.26 (3f). Mock beat-strip already correct via the advisory `state.beat` off-by-one fix.
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
