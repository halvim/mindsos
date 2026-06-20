# Robot Demo — UI next-chat prompt

Paste the block below to start the next UI chat. It points at files instead of repeating them.

---

You are continuing the MindsOS Robot Demo dashboard UI (the `demo_ui/` "v10" track; on-screen product
version **v0.24**). Settled decisions are recorded in the files below — do NOT re-litigate them. This prompt
deliberately does not repeat what's in the files; the files are the source of truth. Read first, then continue.

Read first, in this order:
1. `confirmation_docs/ROBOT_DEMO_UI.md` — the canonical UI record. §1 dashboard + version scheme, §2 file map
   (now incl. `timeline.js` + `timeline_map.png`), §3 shipped increments **through v0.24**, §4 settled design
   decisions, §5 backlog/next (items 3d–3g + the deferred v0.25 + the `state.cbeat` wiring), §6 conventions,
   §7 open items. Your entry point.
2. `confirmation_docs/ROBOT_DEMO_UI_BACKEND_COORDINATION.md` — the ACTIVE UI ↔ backend (DM-*) channel,
   **condensed 2026-06-15**: read **SETTLED** (the locked schema/audit/beat-index contracts), **DELIVERED
   FIXTURES**, and **OPEN ITEMS** — those five OPEN ITEMS are your gated/ungated work list. Convention: when
   you read an append that needs no reply, append a dated "acknowledged". (The older
   `ROBOT_DEMO_DM4_L5_EXPORT_COORDINATION.md` is closed history — background only.)
3. `confirmation_docs/ROBOT_DEMO_IP_SANITIZATION.md` — policy B (mandatory): every displayed string AND every
   wire frame shows behavior, never MindsOS implementation/IP. Apply to anything you add/render.
4. `confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md` — the server↔browser protocol.
5. The reference maps in `demo_ui/` (`orchestrator_card_map` / `plan_card_map` / `user_card_map` /
   `button_map` / `header_map` / `timeline_map` .png; regen via `demo_ui/maps/*.py`, needs cairosvg) — the
   named-part vocabulary; keep current with every mapped change. (`.png` live in `demo_ui/`, the `.py`
   generators in `demo_ui/maps/`.)
6. The code: `demo_ui/presentation.html` + sidecars (`graph.js` / `teach.js` / `sections.js` / `resolve.js` /
   `audit.js` / `datasource.js` / `timeline.js`), `demo_ui/mock_ws_server.js`, `demo_ui/HOW_TO_USE.md`.
7. Memories: [[robot-demo-l5-audit-view]] (UI v0.15→v0.24 + the OPEN items + the commit note),
   [[robot-demo-ui-v10]], [[robot-demo-ui-verification]], [[pair-execution-workflow]],
   [[no-sandbox-git-mutations]], [[robot-demo-version-scheme]], [[robot-demo-ip-sanitization]],
   [[mindsos-uncommitted-parked-work-2026-06-11]].

Current state (one line): **v0.24 shipped + committed** (branch `robot-demo-animation`). NOTE: v0.21–v0.24
were **swept into the backend chat's DM-6 commits** (`2dfdeb6` + `2c5dd33`) and pushed — there is no dedicated
UI commit; **do not rewrite that pushed history.** Shipped this run: v0.21 live Plan▸Resolve, v0.22 beat strip
+ accent scrollbar, v0.23 wheel-scroll, v0.24 demo-timeline modal + beat-1 fix (all detailed in §3).

Your task — pick up the work list in the coordination file's **OPEN ITEMS** + ROBOT_DEMO_UI.md §5. The two
things NOT backend-gated (do these first, each confirmed with the user before building):
- **Wire the delivered dead-end fixture into the audit view.** `confirmation_docs/fixtures/
  episode_audit_mgr_deadend.json` is delivered (Manager `dont_know`). Bake it like the v0.20 refusal
  (mgr → [Succeeded, Succeeded, Blocked]; `blame.rationale` = Outcome line; build-time drift-guard;
  no-fabrication). Render rules are in the coordination SETTLED §"Audit view".
- **Redo the demo-timeline story → v0.25.** The v1 story `confirmation_docs/ROBOT_DEMO_TIMELINE_STORY.md`
  was **rejected by the user** — improve it WITH the user first, then encode it: the richer per-section row
  model (per-brain frame `sections:{task,plan,pipeline}` + `resolve` + `caps`; the `timeline.js` builder
  emits one row per *changed* section). See §5 item 3f.
Backend-gated (wire when the coordination file says they've landed): `state.cbeat` (live beat counter +
timeline grouping — one-line `datasource.js` change; §5 3g); recovery fixture #2 + `replan_summary`; per-step
`verification[]`; `server_event` (Seam A live rows); Mode-B demo-state restore.

Conventions (full text in ROBOT_DEMO_UI.md §6 + the policy doc — not repeated here):
- Critical-design-reviewer posture; restate a plan before building; ONE increment at a time, each
  openable/clickable; show option mockups (cairosvg PNG) for visual/ambiguous choices and get approval first.
- IP sanitization policy B on every displayed/wire string.
- Version scheme: on-screen badge = product version; +0.01 per shipped UI increment; v1.0 = live end-to-end.
  Currently **v0.24**.
- Mock path byte-identical by default; live behaviour gated behind `?live=<wsurl>`. v9
  (`presentation_mockup.html`) stays frozen.
- Verify headlessly — no Chromium in the sandbox. The jsdom+node harness is NOT committed (scratch); rebuild
  it (inline the sidecars, stub three.js/canvas/rAF/ResizeObserver/CSS, fake the WebSocket) and keep an
  IP-sanitization guard green. `npm i jsdom` in a scratch dir — NOTE `npm i ws` inside `demo_ui` prunes jsdom,
  so reinstall if you run the harness there.
- Keep the reference maps current with every mapped change.

Git / ship (pair-execution): Cowork builds; the user commits+pushes on the Mac; Linux pulls + tests. NEVER
git-mutate from the Cowork sandbox. Branch = `robot-demo-animation`. The working tree holds OTHER chats'
uncommitted parked work — scope `git add` to your own files **by explicit path**; NEVER `git add -A`. Beware
the shared mount: the coordination file is also edited+pushed by the backend chat (don't fight it), and a
full-file Write over a tracked file can desync (`.fuse_hidden` orphans) — prefer in-place edits. demo_ui
changes have no committed test gate; verification = the headless harness + the user's eyeball.

When in doubt, the file is the source of truth — ask the user rather than guessing.
