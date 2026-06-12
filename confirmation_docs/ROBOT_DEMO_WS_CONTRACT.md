# Robot Demo — WebSocket contract (backend ↔ v10 dashboard)

**Audience: whoever builds the demo backend (the DM-* track in `ROBOT_DEMO_MINDSOS_PLAN.md`).**
This is the exact wire protocol the live dashboard (`demo_ui/presentation_v10.html`) speaks.
Emit these frames and the UI lights up with zero front-end changes — going live is the
`?live=<wsurl>` switch, nothing else. The brain/thinking payload is deliberately the same
shape the mock already uses (`ROBOT_DEMO_PROTOTYPE_PLAN.md §4`), so the MindsOS drop-in is
transparent.

> Implemented by `demo_ui/datasource_v10.js` (the UI seam) and demonstrated by
> `demo_ui/mock_ws_server.js` (a runnable reference emitter). If this doc and the code ever
> disagree, the code + its tests are authoritative — update this doc.

**Which DM step needs this:**
- **DM-4 (Seam B — BrainBus + `comms.*` + WS)** is the primary owner: it must emit these frames
  and accept these commands. Read the whole doc + `datasource_v10.js` + `mock_ws_server.js`.
- **DM-3 (Seam C — body adapter + live-motion)** only needs **§2.3 `pose`**: the body/item
  transforms its motion produces should be shaped so a `pose` frame is a thin wrapper over them
  (`items[name]=[x,y]` now; reserved `bodies[name]=[x,y,z,qw,qx,qy,qz]` for the 3D robot). Aligning
  here avoids an adapter at DM-4. DM-3 does **not** need the rest of the UI files.

---

## 1. Transport & lifecycle

- **One WebSocket.** JSON text frames both directions. (Binary `Float32Array` pose packing is a
  later optimization if bandwidth bites — not in v1.)
- The browser opens `presentation_v10.html?live=ws://<host>:<port>`. It connects immediately
  and shows **"● connecting to live brains…"**, then **"● live — connected to brains"** on open,
  **"● disconnected"** / **"● live connection error"** otherwise.
- Expected sequence: client connects → **server sends `hello`** → server streams
  `state` / `message` / `pose` frames as the scenario runs → optional `reset`. The browser sends
  `command` frames in response to user actions (order, play/pause, teach…).
- No authentication in v1 (LAN/tunnel demo). If you add auth, do it at the WS handshake; the UI
  doesn't send credentials today.

---

## 2. Server → browser frames

Every message is a JSON object with a `type`. Unknown types are ignored safely.

### 2.1 `hello` (once, on connect)
```json
{ "type":"hello", "scenario":"open-order", "brains":["mgr","a1","a2","conv"], "beats_total":7 }
```
Handshake / metadata. `brains` and `beats_total` are advisory (the UI does not require them yet).

### 2.2 `state` — a cognitive beat snapshot (the main frame)
One `state` frame = one navigable "beat" in the UI. Push one whenever the brains' thinking
advances (NOT at 30–60 Hz — that's `pose`).
```json
{
  "type":"state",
  "t":1718136000000,            // optional epoch ms
  "beat":3,                     // optional integer index (advisory)
  "title":"Cooperative execution",
  "narr":"The brains run the new skill: the belt hands the Box and Tube to Arm 2…",
  "brains":{
    "mgr": {"intent":"Execute placements","chain":5,"decision":"resolve 'Box above Tube' → A2 (r0,c1); dispatch","active":true,"flags":[]},
    "a1":  {"intent":"Place Sheet","chain":5,"decision":"place Sheet @ A1 center ✓","active":true,
            "caps":[["move/grip","primitive"],["handoff-via-belt","learned"],["place-at-cell","learned"]]},
    "a2":  {"intent":"Place Box above Tube","chain":5,"decision":"place Box @ A2(r0,c1) ✓","active":true,
            "caps":[["handoff-via-belt","inherited"]]},
    "conv":{"intent":"Bridge the gap","chain":4,"decision":"advance → stage at x=0.2","active":true}
  },
  "items":{"box1":[0.70,-0.62], "tube1":[0.70,-0.77], "sheet1":[-0.70,-0.77]},  // optional (see pose)
  "eff":{"a1":[-0.70,-0.77], "a2":[0.70,-0.62]},                                 // optional effector targets
  "msgs":[ ["Orchestrator→Arm2","dispatch(place Box @ A2 r0c1)"] ]               // optional (or use `message`)
}
```

**Per-brain object** (`brains[id]`), `id ∈ {mgr,a1,a2,conv}`:

| field | type | consumed by | notes |
|---|---|---|---|
| `intent` | string | intent line (pinned) + Task section | short "what this brain is doing now" |
| `decision` | string | Task / Plan section body | the brain's current decision/result text |
| `chain` | int 0–5 | (reserved) | 6-level chain progress; not rendered as a bar in v10 |
| `active` | bool | card dim state + cell reach ring | **transient — see §3** |
| `flags` | string[] | per-section flag chips | subset of `["gap","learn","promo","gate","fault"]`; **transient — see §3** |
| `caps` | array of `[name, badge]` | Capabilities section | `badge ∈ {"primitive","learned","inherited","GATED","FAULT"}` ("" = no badge) |

### 2.3 `pose` — high-frequency body/item update (optional, for the cell view)
Updates the **current** view without creating a new beat. Send at whatever rate the sim runs.
```json
{ "type":"pose", "t":…, "items":{"box1":[x,y], …}, "eff":{"a1":[x,y]|null,"a2":…} }
```
`items[name] = [x,y]` in the cell's world frame (the 2D schematic / 3D rack mapping the UI
already uses). When the real 3D robot is wired, add `bodies:{name:[x,y,z, qw,qx,qy,qz]}` here for
mesh transforms — the field is reserved; the v10 cell currently consumes `items`/`eff` only.

### 2.4 `message` — Seam-B inter-brain log line
Appended to the inter-brain message panel.
```json
{ "type":"message", "from":"Orchestrator", "to":"Arm1", "text":"query_capabilities()", "t":… }
```
`from`/`to` are brain display names (`Orchestrator|Arm1|Arm2|Conveyor|User|Global|L2|Demonstration`);
the panel colours them by brain. Use these frames for the live BrainBus, or inline `msgs` in a
`state` frame — both render. (Prefer `message` frames; leave `state.msgs` empty.)

### 2.5 `reset`
```json
{ "type":"reset" }
```
Clears the UI back to a single idle state.

---

## 3. Field persistence — IMPORTANT

The UI keeps a **cumulative** state: each `state` frame is merged onto the previous one. The merge
is not uniform, so the backend must know which fields carry forward and which must be re-sent:

- **Carry forward until changed** (persistent): `brains[id].intent` / `chain` / `decision` / `caps`,
  and `items`.
- **Transient — present-or-default every frame**: `brains[id].active` (absent ⇒ `false`),
  `brains[id].flags` (absent ⇒ `[]`), `eff` (absent ⇒ both `null`), `title`, `narr`, `msgs`
  (absent ⇒ `[]`).

So: to keep a brain showing `active`/a flag across beats, **include it in every `state` frame**;
to clear it, simply omit it. `caps`/`intent`/`decision` stick until you send a new value.

---

## 4. Browser → server commands

User actions on the dashboard send:
```json
{ "type":"command", "name":"<name>", "args":{…} }
```

| `name` | args | trigger |
|---|---|---|
| `place_order` | `{lines:[{item, shelf, pos}]}` | User card ▸ **Submit** (the composed order) |
| `play` / `pause` | — | header ▶/⏸ |
| `step` | — | (reserved; header ›) |
| `reset` | — | header ↺ |
| `teach` | `{skill, blocks:[…]}` | Teach ▸ **Capture demonstration** |
| `sort` | `{move}` | (reserved; Sort tab) |

`lines[].pos` is the composed position-builder output: an array of clauses, each either
`{type:"shelf", pos:"<term>"}` or `{type:"rel", rel:"above|below|left|right|under", obj:"Box|Sheet|Tube"}`.
The backend resolves these against the per-arm 3×3 shelf (the resolver in `OPEN_QUESTIONS §3`).

---

## 5. Panels with no live producer yet (currently suppressed in live mode)

Two panels are **illustrative-only** in the mock and are intentionally blanked when `?live=` is on,
because the backend doesn't emit their data yet. When you're ready to make them live, add these
frame types and tell the UI side — they're the natural next producers:

- **Plan ▸ Resolve** (relation narrowing 9→3→1). Future frame, e.g.
  `{type:"resolve", brain, clause, tube, stages:[{cap, cells:{i:"cand|win|out"}}], winner}`
  (mirrors `demo_ui/resolve_v10.js`).
- **Reasoning graph** (per-section subgraph). Future frame carrying nodes/edges with states
  (mirrors `demo_ui/graph_v10.js`).

Until then the live UI shows "live … feed not yet emitted (backend producer pending)" in those
spots — honest, not broken.

---

## 6. Reference emitter + how to try it

`demo_ui/mock_ws_server.js` replays the 7 scripted beats over this exact protocol — read it as a
worked example of the frame shapes, and use it to exercise the UI before the real backend exists:

```
cd demo_ui && npm i ws && node mock_ws_server.js 8765
# then open:  presentation_v10.html?live=ws://localhost:8765
# click ▶ Play (or Submit an order) → beats stream in as live frames
```

Verified headlessly (no browser needed): `datasource_v10.js` unit tests (15/15), a jsdom live-mode
test driving a stub socket (15/15), and an end-to-end test against the spawned mock server over a
real WebSocket (7/7). See `confirmation_docs/ROBOT_DEMO_UI_V10.md` v10.6.

---

## 7. Open items for the backend to decide

- **Pose channel rate & format** — JSON `pose` at sim rate vs binary later; and whether to send
  `bodies` (full 3D transforms) once the real robot view replaces the schematic.
- **Resolve / graph producers** — §5; needed for those two panels to go live.
- **Reconnect / backpressure** — the UI currently does not auto-reconnect or ack; add if the demo
  needs resilience over a tunnel.
- **Authoritative vs advisory `beat`** — the UI derives its own beat index from frame order; decide
  if you also want server-driven beat labels surfaced.
