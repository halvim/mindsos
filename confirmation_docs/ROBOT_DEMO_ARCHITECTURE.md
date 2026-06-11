# MindsOS Robot Demo — Architecture & Runbook (plain-language)

**Companion to `ROBOT_DEMO_SCENARIO.md`.** Written for a non-developer. Covers: what runs where, what's built vs gated, and how to run what exists today.

> **UPDATE 2026-06-10 — the Phase-48 gate is GONE.** L4 (Phase 46–47) and L5 (Phase 48) shipped; Phases 49–50 closed the numbered plan. Everything below that says "blocked until Phase 48" is now unblocked. The stub-controller stage is **dropped** (decision 2026-06-10): the backend wires the real brains directly. Topology decision: **one MindsOS server process, the 4 brains = 4 users/sessions** sharing one Global with per-brain Locals, on the Mac Mini via Docker Compose. The implementation plan is `ROBOT_DEMO_MINDSOS_PLAN.md` — read that for current build state; this doc's tables are kept for the architecture rationale.

---

## 1. The one correction that shapes everything

**MindsOS cannot run in a web browser.** Each brain is a FalkorDB graph database + Python (layers L1–L5). That is server software. MuJoCo (the physics) *can* run in a browser via WebAssembly, but the four minds cannot. So "fully-implemented MindsOS, delivered as a browser link" is a **client–server web app**, not a standalone webpage:

```
            YOUR LINUX SERVER                                EACH PARTICIPANT
 ┌─────────────────────────────────────────┐         ┌──────────────────────────┐
 │  MindsOS minds (Python + FalkorDB)        │        │   Web browser            │
 │   • Manager brain                         │        │   • 3D view of the cell  │
 │   • Arm-1 brain   • Arm-2 brain           │ <────> │   • Order-entry panel    │
 │   • Conveyor brain                        │  web   │   • Live reasoning trace │
 │  MuJoCo physics (the simulated cell)      │ (URL)  │                          │
 │  Web backend (serves the page + state)    │        │   They click; the server │
 └─────────────────────────────────────────┘         │   thinks and replies     │
                                                       └──────────────────────────┘
```

You still get the experience you chose — **share a link, everyone interacts in their browser**. But there is a server doing the thinking, so it is *not* a crash-proof static page. Two consequences:

1. The **recorded backup is mandatory** (a network hiccup or a server stall can't be allowed to sink the meeting).
2. The physics runs **on the server next to the brains** (a brain's "move the arm" capability calls the simulator directly). This is far simpler than running physics in the browser, and the audience can't tell the difference. MuJoCo-WASM is therefore *not* needed for this design.

---

## 2. What is built vs what remains (updated 2026-06-10)

L4 + L5 **have shipped** (Phases 46–48; 49–50 closed the plan). Nothing is gated on MindsOS phases anymore — the remaining work is demo-side build.

| Piece | Status |
|---|---|
| Physical cell (real Franka ×2 + belt + shelves + Box/Sheet/Tube) | **DONE** — Phase A (`sim/cell.xml`), reach re-validated 9/9 cells + forced gap |
| Motion library (46 verified clips + live trajectory generators) | **DONE** — Phase B (`sim/motion.py`; see `ROBOT_DEMO_STATE.md`) |
| MindsOS L4 + L5 | **SHIPPED** (Phases 46–48) |
| Demo backend (sim loop + WebSocket + brain hosting) | Not started — no longer needs a stub controller; wires real brains directly |
| Web frontend v10 (live 3D + thinking panels + graph tab) | Not started (v9 mockup frozen as baseline) |
| Demo-specific MindsOS content (L2 seeds, L3 capacities, L4 wiring, L5 chain surfacing) | Planned — `ROBOT_DEMO_MINDSOS_PLAN.md` |
| Recorded backup of a clean run | Final step |

---

## 3. Prototype-zero — what it proves and how to run it

Prototype-zero is the physical stage with **no intelligence yet**. Its job is to prove the geometry the entire demo depends on: that no single arm can do a job alone, so cooperation is forced by the layout rather than faked in software.

**Result (already run here):**
- The model loads, simulates, and is stable; items rest on the belt.
- Reach-partition checks **all pass**: arms don't overlap, the central gap is reachable by neither, each arm reaches only its own bins. See `prototype_zero/layout.png`.

**To run it yourself (on any machine with Python):**

```
pip install mujoco matplotlib
cd prototype_zero
python3 verify.py     # loads + simulates the cell, prints a stability check
python3 layout.py     # prints the reach validation, writes layout.png
```

To *see it move in 3D* on a machine with a screen (a laptop, not a headless server):

```
pip install mujoco
python3 -m mujoco.viewer --mjcf=cell.xml
```

(That opens MuJoCo's built-in viewer — useful for you to eyeball the cell. It is **not** the presentation; the presentation is the web app in §1.)

---

## 4. Honest scope for a non-developer

- This is a **multi-week software build** (sim + web app + MindsOS integration), not a weekend script. It needs a builder working across sessions — that can be me here, but plan for real engineering time, and ideally a developer who can run and babysit the server on demo day.
- **You will need:** a Linux server that can run Python + FalkorDB, the ability to open a web port (for the URL), and a dry-run rehearsal before any live audience.
- **Lowest-risk demo-day setup:** the live web app for interaction **plus** a pre-recorded clean run cued up to play if anything stalls.

---

## 5. Recommended next steps (updated 2026-06-10)

Steps 1–2 and 4 of the original list are done (Phase A reach validation; the two §5 contracts were frozen 2026-06-05). The stub-server step is dropped. What remains, in order, is the build sequence in **`ROBOT_DEMO_MINDSOS_PLAN.md`**: deploy + bootstrap the 4 brains → demo-specific L2/L3 content → backend service → frontend v10 → rehearse + record backup.

Historical files: `prototype_zero/` (superseded by `sim/`), `demo_ui/presentation_mockup.html` (frozen v9).
