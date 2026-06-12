# Robot Demo — UI next-chat prompt

Paste the block below to start the next UI chat. It points at files instead of repeating them.

---

You are continuing the MindsOS Robot Demo dashboard UI (the `demo_ui/` "v10" track; on-screen product
version **v0.14**). Settled decisions are recorded — do NOT re-litigate them. Read the files, then
continue. **This prompt deliberately does not repeat what's in the files; the files are the source of
truth.**

## Read first, in this order
1. `confirmation_docs/ROBOT_DEMO_UI.md` — the canonical UI record. §1 what the dashboard is + the
   **version scheme**, §2 file map, §3 **shipped increments (through v0.14)**, §4 settled design
   decisions, §5 **backlog/next**, §6 working conventions, §7 open items. **Your entry point.**
2. `confirmation_docs/ROBOT_DEMO_IP_SANITIZATION.md` — **policy B (mandatory):** every displayed
   string AND every wire frame shows behavior, never MindsOS implementation/IP. Apply to anything you
   add or render.
3. `confirmation_docs/ROBOT_DEMO_L5_EXPORT_IMPORT_PROMPT.md` — the **locked** backend contract: L5
   export/import (modes A `episode-audit` / B `demo-state`) + the Server `server_status`/`server_event`
   frames + the snapshot JSON schema you build the UI against.
4. `confirmation_docs/ROBOT_DEMO_DM4_L5_EXPORT_COORDINATION.md` — the live **DM-4 ↔ UI** channel.
   Convention: when you read a DM-4 append that needs no reply, append a dated "acknowledged"; write a
   reply when one is needed.
5. `confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md` — the server↔browser protocol (state/pose/message/
   command + the live frames).
6. The reference **maps** in `demo_ui/`: `orchestrator_card_map.png`, `plan_card_map.png`,
   `comms_card_map.png`, `user_card_map.png`, `button_map.png` (regenerate via `demo_ui/maps/*.py`,
   needs `cairosvg`) — the named-part vocabulary. Use them when the user refers to a part; keep them
   current with every mapped-card change.
7. The code: `demo_ui/presentation.html` + sidecars (`graph.js` / `teach.js` / `sections.js` /
   `resolve.js` / `datasource.js`), `demo_ui/mock_ws_server.js`, `demo_ui/HOW_TO_USE.md`.

## Current state (one line)
The mock dashboard is feature-rich through v0.14; the Server feed + the two live-only panels are
mock/placeholder until DM-4 emits frames; DM-4 is building Mode-A export + `server_status` (sanitized).
The live wire-up on your side is a small `datasource.js` change when those land.

## Your task — continue `ROBOT_DEMO_UI.md` §5 backlog, in order. Confirm each increment with the user before building.
1. **L5 reasoning/audit view** (goal #2 — "why did it decide/refuse X"): a NEW visual surface →
   **mockup first** (cairosvg PNG for approval). Render from the snapshot's sanitized `reasoning`
   stages (doc #3); follow policy B (doc #2).
2. **Export chooser** (audit a brain / demo state) + **demo-state restore** (jump to beat) — completes
   the v0.14 L5 scaffold (the header buttons + `#l5msg` already exist; mock snapshots in
   `presentation.html`).
3. **v0.15 focus mode** — manual "solo this card" (§5 item 1; the as-specced auto-spotlight was
   dropped — see §4/§5).
4. **`datasource.js` live wire-up** for `server_status`/`server_event` + the live snapshot, once DM-4
   emits (the coordination file will say when).

## Conventions you must follow (all in `ROBOT_DEMO_UI.md` §6 + the policy doc — not repeated here)
- **Verify headlessly** — no Chromium in the sandbox. The prior chat's jsdom+node harness lived in the
  scratch dir (not committed); rebuild it (inline the sidecars, stub three.js/canvas/rAF/RO/WebSocket,
  bridge the `let`/`const` globals) or ask the user, and **keep an IP-sanitization guard** green. Live
  click/layout + pixels are the user's eyeball, not yours.
- IP sanitization **policy B** on every displayed/wire string.
- **Version scheme:** the on-screen badge = product version; +0.01 per shipped UI increment; `v1.0` =
  live end-to-end. The `_v10` in filenames is inert, not a version.
- Critical-design-reviewer posture; restate a plan before building; one increment at a time, each
  openable/clickable; **show option mockups (cairosvg PNG) for visual/ambiguous choices**.
- Mock path stays byte-identical by default; live behaviour gated behind `?live=`.
- v9 (`presentation_mockup.html`) stays frozen.
- The user runs all git on their Mac (pair-execution: Cowork builds, Mac commits+pushes, Linux gates
  Python). **Never git-mutate from the sandbox.** `demo_ui/node_modules` is git-ignored.

When in doubt, the file is the source of truth — ask the user rather than guessing.
