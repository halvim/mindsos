# MindsOS Robot Demo — Prototype Build Plan

**Goal:** a fully working prototype — *everything except the real MindsOS brains* — that runs proper MuJoCo robots with real motion on the Linux server and drives the frozen v9 UI in a browser over the network.

**Companions:** `ROBOT_DEMO_SCENARIO.md` (what the demo does), `ROBOT_DEMO_ARCHITECTURE.md` (client–server rationale), `demo_ui/` (frozen v9 UI + version history).

---

## 0. Scope — AMENDED 2026-06-10: the stub controller is DROPPED

> **Phase 48 shipped (2026-06-09).** The original rationale for the stub controller — L4/L5 unshipped — is gone, and the user decided (2026-06-10) to wire the real brains directly. **Phase C below builds the backend on `IntelligenceLayer` + real capacities, not a stub; Phase F (drop-in swap) is dissolved into Phase C.** The four Seam-B messages survive as the *internal* inter-brain contract (now implemented as MindsOS `interaction.*` capacities). Phases A and B are complete (see `ROBOT_DEMO_STATUS.md` / `ROBOT_DEMO_STATE.md`). The MindsOS-side build (deployment, L2 seeds, L3 catalog, L4 wiring, L5 surfacing) is specified in **`ROBOT_DEMO_MINDSOS_PLAN.md`** — that doc supersedes the Phase C–F rows here where they conflict.

Original text (historical): the stub was hand-written scripted/rule logic speaking the same four inter-brain messages (`query-capabilities`, `dispatch`, `report`, `promote` — Seam B), so MindsOS could replace it without changing sim, motion, protocol, assets, or UI.

---

## 1. Target architecture (what runs where)

```
        LINUX SERVER (old Mac Mini)                          BROWSER (you + participants)
 ┌───────────────────────────────────────────┐       ┌───────────────────────────────────┐
 │  demo-backend  (Python, Docker)            │       │  frozen v9 UI                      │
 │   • MuJoCo sim loop (physics, CPU)         │ WS    │   • 3D view = Three.js + glTF      │
 │   • motion controller (IK, grasp, belt)    │<====> │     meshes, posed from server      │
 │   • STUB controller  ⟵ becomes MindsOS     │ JSON  │   • 2D schematic (as today)        │
 │   • state broadcaster + command intake     │       │   • brain/thinking panels          │
 │  FalkorDB container (idle until Phase 48)  │       │   • order / sort / teach controls  │
 └───────────────────────────────────────────┘       └───────────────────────────────────┘
```

**Key decision — render in the browser, not on the server.** The server steps physics (CPU only, no GL) and streams every body's world transform each frame; the browser holds the robot meshes (glTF) and just sets their transforms. This avoids the old Mac Mini's flaky Linux GL entirely (the wall hit during prototype-zero) and keeps the "open a URL" experience. Confirmed-viable pattern: read `data.xpos`/`data.xquat` per step → WebSocket → Three.js. (Alternative — server-side render + video stream — is rejected: needs working server GL + heavier infra.)

---

## 2. Component inventory & stack

| Component | Tech | Notes |
|---|---|---|
| Sim + physics | `mujoco` (Python) | CPU stepping; no GL needed server-side |
| Motion | Jacobian/IK (e.g. `mink` or hand-rolled) + waypoint state machine | per-capability motion generators |
| Grasp | MuJoCo `equality`/weld activated on **valid contact** | **attach-on-valid-contact** — weld fires only when the gripper genuinely closes on the object (both pads) or the suction cup contacts a graspable face. Credible + reliable; not weld-on-proximity. |
| Containment | attach-on-insertion | cargo welded to a Box when placed inside, so the Box carries it |
| Stub controller | plain Python | scripted decisions; emits Seam-B messages |
| Backend server | FastAPI + `websockets` (or `aiohttp`) | one async loop: step sim → broadcast state → apply commands |
| Frontend | the frozen v9 HTML | swap 3D from self-animation to server-posed meshes |
| Asset export | URDF/STL/OBJ → glTF (per link) | so the browser can render the real robots |
| Packaging | Docker Compose (extends the existing stack) | `falkordb` (idle) + `demo-backend` |

---

## 3. Phase plan

**Phase A — Assets & scene.** Replace the stick-arm `prototype_zero/cell.xml` with real models from MuJoCo Menagerie: **2× Franka Emika Panda** bases; Arm 2 ends in the **Robotiq 2F-85** (jaw); Arm 1 ends in a **suction tip** (small cup geom + weld-on-contact — Menagerie has no suction gripper, so this is a small custom add). Build the cell: two arms, two **vertical 3×3 shelves** set back for clearance, **continuous conveyor**, items (Box/Sheet/Tube). Re-run the reach-partition validation (`layout.py` logic) on the real geometry. Export all link meshes to glTF + a body→mesh manifest for the browser.
*Deliverable:* `sim/cell.xml` (real assets) loads, settles, reach-partition passes; `web/assets/*.glb` + manifest.

**Phase B — Real movement.** Implement capabilities as motion generators driven by a state machine: `move-to(pose)` (IK), `grip`/`release` (attach-on-valid-contact toggle), `place-at-cell(shelf,r,c)`, `load-into-box(cargo)` (the box-workaround composite: get empty box → pick cargo → place-in-box via attach-on-insertion), `conveyor.advance/reverse/stage`. The cross-belt **handoff is an Orchestrator Plan** assembling these (Arm1 `load-into-box` → conveyor advance across the reach gap → Arm2 grab box → `place-at-cell`). Reach gap = arms can't reach the middle; conveyor moves only on command. Choreograph the scenario beats with *real physics motion*, not scripted teleport. Box scarcity = optional.
*Deliverable:* headless run executes the full can't-grab → boxed-handoff → shelf-place sequence; logs success.

**Phase C — Backend server.** One async service: load sim, run the controller + motion at fixed rate, broadcast state frames (body transforms + current "thinking" events) over WebSocket, accept command messages (order/sort/play/step/teach). Stub controller turns an order into dispatches.
*Deliverable:* `demo-backend` container; `ws://server:PORT` streams state and accepts commands.

**Phase D — Frontend integration (= UI v10, against live data).** Take frozen v9; replace the 3D self-animation with: load glTF meshes once, then on each WS state frame set body transforms; keep the 2D schematic and the brain/thinking panels (now fed by controller events, not the local mock script); wire Order/Sort/Submit/Teach to send WS commands. **New v10 features (built here, not mocked):** (a) per-card **Graph tab** rendering the brain's live FalkorDB subgraph (curated/animated per the P3 script); (b) **teach / inspect / replace / retire** affordances in the Teach tab (Local-scoped); (c) **control-token** model for shared interaction — one driver at a time on a shared sim, request/grant + presenter reclaim + Reset (P6.2 option a); (d) constrain audience input to orders/teach/sort (no arbitrary state).
*Deliverable:* browser opens a URL, shows live sim + live thinking + live graph; any participant can take the wheel and submit an order that actually runs.

**Phase E — Deploy & rehearse.** Docker Compose on the Mac Mini; expose the port (LAN or a tunnel for remote participants); record a clean backup run.
*Deliverable:* one-command start; shareable URL; recorded fallback.

**Phase F — MindsOS drop-in (post-Phase 48).** Replace the stub controller with the real brains behind the same Seam-B interface. No changes to sim/motion/protocol/UI/assets.

---

## 4. Server ↔ frontend protocol (WebSocket JSON)

- **server → browser, `state` (≈30–60 Hz):** `{t, bodies:{name:[x,y,z, qw,qx,qy,qz]}, items:{...}, brains:{mgr,a1,a2,conv:{intent,chain,decision,flags,active}}, beat}` — bodies/items pose the meshes; brains feed the thinking panels (same shape the mock already uses, so the panel code is reused).
- **browser → server, commands:** `place_order(lines)`, `sort(move)`, `play|pause|step|reset`, `teach(skill, blocks)`.
- Transport: one WebSocket; state as JSON first (optimize to binary `Float32Array` only if bandwidth bites). The brain/thinking payload is deliberately the **same schema MindsOS will emit**, so the drop-in is transparent.

---

## 5. Risks & decisions to lock

1. **Asset-to-web pipeline is real work.** Browser rendering needs the Menagerie meshes as glTF + a body→mesh map. Budget a few days; it's the main new task created by the browser-render decision (worth it to dodge server GL).
2. **Grasping reliability.** Use **attach-on-valid-contact** (weld fires only on a genuine closed-gripper/suction contact), not friction grasping (drops on camera) and not weld-on-proximity (looks fake). Containment = attach-on-insertion. Decision: **attach-on-valid-contact for v1.**
2a. **Reach re-validation (P2).** Prototype-zero validated reach for stick-arms + bins. Re-validate on **real Franka Panda kinematics** against the belt *and* all 9 **vertical** shelf cells — the **top row at set-back distance is the likely out-of-reach failure**. Do this first in Phase A before locking geometry.
3. **Suction gripper asset** doesn't exist in Menagerie — small custom tip + weld. Confirm Arm 1 = suction, Arm 2 = jaw still holds with real models.
4. **Old Mac Mini limits.** Physics for 2 arms is light; the 4 brains later are 4 graphs in **one** FalkorDB. Check RAM before Phase 48. No server GL required by this design.
5. **Remote interaction over a video call** needs the WS port reachable (LAN demo, or a tunnel like Cloudflare/ngrok). Decide LAN-only vs tunnel.
6. **This is a multi-week developer build**, not a script. As a non-developer you'll want a developer (or me across sessions) to implement and to run it on demo day. The recorded backup is mandatory.

## Locks — RESOLVED (start Phase A)
- **Arms: Franka Panda ×2** — Arm 1 + custom suction tip, Arm 2 + Robotiq 2F-85 jaw.
- **Grasp: cheat grasp (weld-on-contact) for v1.**
- **Network: decided later** — build LAN-first; choose tunnel vs screen-share near demo day.

All Phase-A inputs are settled; it has no MindsOS dependency and can begin immediately.
